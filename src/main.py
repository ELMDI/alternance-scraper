"""Main entry point — orchestrates the full scraping pipeline.

Execution flow:
1. Load configuration (env vars, defaults).
2. Run every scraper in sequence (each isolated by try/except).
3. Merge and deduplicate all collected offers.
4. Run the filtering/scoring pipeline.
5. Check against the SQLite dedup store for truly new offers.
6. Format and send notifications (Telegram primary, Discord fallback).
7. Persist newly-seen offers in the dedup store.
8. Print a summary to stdout.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import List

# Load .env file for local development (no-op in CI).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from src import config
from src.dedup import DedupStore
from src.filters import filter_and_score
from src.models import Job
from src.notifiers.discord import send_discord
from src.notifiers.telegram import send_telegram

# Import all scrapers.
from src.scrapers.ats import ATSHubScraper
from src.scrapers.lba import LBAScraper
from src.scrapers.j1s import J1SScraper
from src.scrapers.wttj import WTTJScraper

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(
        open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
    )],
)
logger = logging.getLogger("alternance-scraper")


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------

def _run_scrapers() -> List[Job]:
    """Execute every scraper and collect all job offers.

    Each scraper is wrapped in a try/except so that one failure does
    not block the others.
    """
    scrapers = [
        WTTJScraper(),
        LBAScraper(),
        J1SScraper(),
        ATSHubScraper(),
    ]

    all_jobs: List[Job] = []
    errors: List[str] = []

    for scraper in scrapers:
        try:
            logger.info("▶ Running scraper: %s", scraper.name)
            jobs = scraper.fetch()
            logger.info(
                "  ✓ %s returned %d offers.", scraper.name, len(jobs)
            )
            all_jobs.extend(jobs)
        except Exception as exc:  # noqa: BLE001
            msg = f"{scraper.name}: {exc}"
            logger.error("  ✗ %s crashed: %s", scraper.name, exc, exc_info=True)
            errors.append(msg)

    if errors:
        logger.warning(
            "Scraper errors (%d): %s", len(errors), "; ".join(errors)
        )

    return all_jobs


def _deduplicate_in_batch(jobs: List[Job]) -> List[Job]:
    """Remove duplicates within the current batch (same URL or title+company)."""
    seen_urls: set[str] = set()
    seen_keys: set[str] = set()
    unique: List[Job] = []

    for job in jobs:
        # Dedup by URL.
        if job.url in seen_urls:
            continue
        seen_urls.add(job.url)

        # Dedup by (normalized title + company).
        key = f"{job.title.lower().strip()}|{job.company.lower().strip()}"
        if key in seen_keys:
            continue
        seen_keys.add(key)

        unique.append(job)

    logger.info(
        "In-batch dedup: %d → %d offers.", len(jobs), len(unique)
    )
    return unique


def _send_notifications(jobs: List[Job]) -> None:
    """Send notifications via Telegram (primary) and Discord (fallback)."""
    if config.DRY_RUN:
        logger.info("[DRY RUN] Would notify %d offers.", len(jobs))
        for job in jobs:
            logger.info(
                "  %s @ %s | %s | %s",
                job.title,
                job.company,
                job.location,
                job.url,
            )
        return

    # Try Telegram first.
    telegram_ok = send_telegram(jobs)

    if not telegram_ok:
        logger.warning(
            "Telegram delivery failed — falling back to Discord."
        )

    # Always try Discord if configured (secondary channel).
    if config.DISCORD_WEBHOOK_URL:
        send_discord(jobs)


def main() -> None:
    """Run the full pipeline."""
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info(
        "Alternance Scraper — run started at %s",
        start_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
    )
    logger.info("=" * 60)

    # Step 1: Scrape all sources.
    raw_jobs = _run_scrapers()
    logger.info("Total raw offers collected: %d", len(raw_jobs))

    if not raw_jobs:
        logger.info("No offers found from any source.")
        _send_notifications([])
        return

    # Step 2: In-batch deduplication (across sources).
    unique_jobs = _deduplicate_in_batch(raw_jobs)

    # Step 3: Filter and score.
    filtered_jobs = filter_and_score(unique_jobs)
    logger.info("Offers after filtering: %d", len(filtered_jobs))

    # Step 4: Cross-run deduplication via SQLite.
    with DedupStore() as store:
        new_jobs = store.filter_new(filtered_jobs)
        logger.info(
            "New offers (not previously seen): %d / %d",
            len(new_jobs),
            len(filtered_jobs),
        )

        # Step 5: Notify.
        _send_notifications(new_jobs)

        # Step 6: Persist.
        if new_jobs:
            store.mark_seen(new_jobs)

        total_seen = store.count()

    # Summary.
    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info("━" * 60)
    logger.info("Pipeline complete in %.1fs", elapsed)
    logger.info("  Raw: %d | Unique: %d | Filtered: %d | New: %d",
                len(raw_jobs), len(unique_jobs), len(filtered_jobs), len(new_jobs))
    logger.info("  Total seen in DB: %d", total_seen)
    logger.info("━" * 60)


if __name__ == "__main__":
    main()
