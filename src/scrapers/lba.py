"""La Bonne Alternance scraper (API publique beta.gouv.fr).

Queries the official LBA endpoint which aggregates:
- France Travail (Pôle Emploi) apprenticeship offers  (``peJobs``)
- Direct employer postings via the Matcha portal       (``matchas``)

The ``lbaCompanies`` predictive suggestions are deliberately ignored
because they are not concrete job postings.
"""

from __future__ import annotations

import logging
import time
from typing import List

from src import config
from src.models import Job
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class LBAScraper(BaseScraper):
    """Fetch apprenticeship offers from La Bonne Alternance."""

    name = "lba"

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        seen_ids: set[str] = set()

        # Batch ROME codes to avoid overlong queries / timeouts.
        batches = _chunked(config.ROME_CODES, config.LBA_ROME_BATCH_SIZE)

        for batch_idx, rome_batch in enumerate(batches):
            if batch_idx > 0:
                time.sleep(1.0)  # polite delay between batches

            romes_str = ",".join(rome_batch)
            logger.debug("[lba] Querying ROME batch: %s", romes_str)

            params: dict = {
                "caller": config.LBA_CALLER,
                "romes": romes_str,
                "latitude": str(config.PARIS_LAT),
                "longitude": str(config.PARIS_LON),
                "radius": str(config.SEARCH_RADIUS_KM),
                "sources": "offres,matcha",
            }

            headers: dict = {}
            if config.LBA_API_KEY:
                headers["Authorization"] = f"Bearer {config.LBA_API_KEY}"

            data = self._get_json(
                config.LBA_BASE_URL,
                params=params,
                headers=headers if headers else None,
            )
            if data is None:
                continue

            # Parse France Travail offers (peJobs).
            for item in data.get("peJobs", []):
                job = self._parse_pe_job(item)
                if job and job.id not in seen_ids:
                    seen_ids.add(job.id)
                    jobs.append(job)

            # Parse Matcha direct postings.
            for item in data.get("matchas", []):
                job = self._parse_matcha(item)
                if job and job.id not in seen_ids:
                    seen_ids.add(job.id)
                    jobs.append(job)

        logger.info("[lba] Fetched %d unique offers.", len(jobs))
        return jobs

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_pe_job(item: dict) -> Job | None:
        """Parse a France Travail offer from the ``peJobs`` array."""
        try:
            place = item.get("place", {})
            company_info = item.get("company", {})

            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            company = company_info.get("name", "Entreprise inconnue")
            city = place.get("city", "Paris")
            url = item.get("url", "")
            description = item.get("description", "")
            contract_type = item.get("contractType", "alternance")
            created_at = item.get("createdAt", "")

            if not job_id or not title:
                return None

            return Job(
                id=job_id,
                source="lba",
                title=title,
                company=company,
                location=city,
                url=url,
                created_at=created_at,
                description=description,
                contract_type=contract_type.lower(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[lba] Failed to parse peJob: %s", exc)
            return None

    @staticmethod
    def _parse_matcha(item: dict) -> Job | None:
        """Parse a direct employer posting from the ``matchas`` array."""
        try:
            place = item.get("place", {})
            company_info = item.get("company", {})

            job_id = str(item.get("id", ""))
            title = item.get("title", "")
            company = company_info.get("name", "Entreprise inconnue")
            city = place.get("city", "Paris")
            url = item.get("url", "")
            description = item.get("description", "")
            contract_type = item.get("contractType", "alternance")

            if not job_id or not title:
                return None

            return Job(
                id=job_id,
                source="lba",
                title=title,
                company=company,
                location=city,
                url=url,
                description=description,
                contract_type=contract_type.lower(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[lba] Failed to parse matcha: %s", exc)
            return None


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _chunked(lst: list, size: int) -> list[list]:
    """Split *lst* into sublists of at most *size* elements."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]
