"""Scoring and filtering pipeline for job offers.

Two-stage approach:
1. **Hard exclusion** — drop any offer whose title or description matches
   a negative pattern (e.g. "bac+5 obligatoire", "stage 6 mois").
2. **Positive scoring** — award points for signals that match the ESSEC
   BBA 3rd-year profile (education level, contract type, start date,
   domain keywords).
"""

from __future__ import annotations

import logging
import re
from typing import List, Sequence

from src import config
from src.models import Job

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase and strip accents for loose matching."""
    return text.lower()


def _contains_any(text: str, patterns: Sequence[str]) -> bool:
    """Return ``True`` if *text* contains any of the *patterns*."""
    normed = _normalize(text)
    return any(p in normed for p in patterns)


# ------------------------------------------------------------------
# Stage 1 — Hard exclusion
# ------------------------------------------------------------------

def _is_excluded(job: Job) -> bool:
    """Return ``True`` if the job must be discarded."""
    combined = _normalize(f"{job.title} {job.description}")

    # Check for explicit exclusion patterns.
    for pattern in config.NEGATIVE_PATTERNS:
        if pattern.lower() in combined:
            logger.debug(
                "EXCLUDED '%s' at %s — matched negative pattern '%s'",
                job.title,
                job.company,
                pattern,
            )
            return True

    # Exclude non-alternance contract types that slipped through scrapers.
    title_lower = _normalize(job.title)
    contract_lower = _normalize(job.contract_type)

    # If the contract type is explicitly "CDI" or "CDD" (and not alternance),
    # exclude — unless the title still mentions alternance.
    if contract_lower in ("cdi", "cdd", "stage", "internship"):
        if not _contains_any(
            title_lower,
            ["alternance", "apprenti", "apprentissage", "contrat pro"],
        ):
            logger.debug(
                "EXCLUDED '%s' at %s — contract type is '%s'",
                job.title,
                job.company,
                job.contract_type,
            )
            return True

    return False


# ------------------------------------------------------------------
# Stage 2 — Positive scoring
# ------------------------------------------------------------------

def _score(job: Job) -> int:
    """Compute a relevance score for *job*."""
    combined = _normalize(f"{job.title} {job.description}")
    points = 0

    for pattern, weight in config.POSITIVE_PATTERNS.items():
        if pattern.lower() in combined:
            points += weight

    # Bonus: title contains a target keyword.
    title_lower = _normalize(job.title)
    for kw in config.SEARCH_KEYWORDS:
        if kw.lower() in title_lower:
            points += 2
            break  # only count once

    return points


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def detect_start_date(text: str) -> str:
    """Try to extract a start date from *text*.

    Returns a human-readable date string or ``"À vérifier"``.
    """
    normed = _normalize(text)

    # Look for explicit month + year patterns.
    month_patterns = [
        (r"septembre\s*2027", "Septembre 2027"),
        (r"sept\.?\s*2027", "Septembre 2027"),
        (r"rentr[ée]e\s*2027", "Rentrée 2027"),
        (r"octobre\s*2027", "Octobre 2027"),
        (r"janvier\s*2028", "Janvier 2028"),
        (r"2027[\s/-]2028", "2027-2028"),
        # Generic year
        (r"septembre\s*\d{4}", None),  # capture dynamically
    ]

    for pattern, label in month_patterns:
        match = re.search(pattern, normed)
        if match:
            if label:
                return label
            return match.group(0).capitalize()

    return "À vérifier"


def filter_and_score(jobs: Sequence[Job]) -> List[Job]:
    """Run the full filtering pipeline on a list of raw jobs.

    Returns a list of accepted jobs sorted by descending score.
    """
    accepted: List[Job] = []

    for job in jobs:
        # Stage 1: hard exclusion.
        if _is_excluded(job):
            continue

        # Stage 2: scoring.
        job.score = _score(job)

        if job.score < config.MIN_SCORE:
            logger.debug(
                "DROPPED '%s' at %s — score %d < min %d",
                job.title,
                job.company,
                job.score,
                config.MIN_SCORE,
            )
            continue

        # Detect start date from description if still default.
        if job.start_date == "À vérifier":
            job.start_date = detect_start_date(
                f"{job.title} {job.description}"
            )

        accepted.append(job)

    # Sort by score descending, then by title alphabetically.
    accepted.sort(key=lambda j: (-j.score, j.title))

    logger.info(
        "Filter pipeline: %d in → %d excluded → %d accepted",
        len(jobs),
        len(jobs) - len(accepted),
        len(accepted),
    )
    return accepted
