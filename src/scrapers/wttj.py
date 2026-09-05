"""Welcome to the Jungle scraper via their public Algolia search API."""

from __future__ import annotations

import logging
from typing import List

from src import config
from src.models import Job
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

_ALGOLIA_MULTI_URL = (
    f"https://{config.WTTJ_ALGOLIA_APP_ID}-dsn.algolia.net"
    "/1/indexes/*/queries"
)


class WTTJScraper(BaseScraper):
    """Fetch apprenticeship offers from Welcome to the Jungle (WTTJ).

    Uses the public Algolia search endpoint with WTTJ's public
    application ID and search-only API key.
    """

    name = "wttj"

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []
        seen_ids: set[str] = set()

        for keyword in config.SEARCH_KEYWORDS:
            hits = self._search(keyword)
            for hit in hits:
                obj_id = hit.get("objectID", "")
                if obj_id in seen_ids:
                    continue
                seen_ids.add(obj_id)

                job = self._parse_hit(hit)
                if job:
                    jobs.append(job)

        logger.info("[wttj] Fetched %d unique offers.", len(jobs))
        return jobs

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _search(self, keyword: str) -> list[dict]:
        """Run one Algolia multi-query search for *keyword*."""
        headers = {
            "x-algolia-application-id": config.WTTJ_ALGOLIA_APP_ID,
            "x-algolia-api-key": config.WTTJ_ALGOLIA_API_KEY,
            "Content-Type": "application/json",
        }

        filters = (
            "website.reference:wttj_fr "
            "AND contract_type:apprenticeship"
        )

        payload = {
            "requests": [
                {
                    "indexName": config.WTTJ_ALGOLIA_INDEX,
                    "params": (
                        f"query={keyword}"
                        f"&hitsPerPage={config.WTTJ_HITS_PER_PAGE}"
                        f"&page=0"
                        f"&filters={filters}"
                        f"&aroundLatLng={config.PARIS_LAT},{config.PARIS_LON}"
                        f"&aroundRadius={config.SEARCH_RADIUS_KM * 1000}"
                    ),
                }
            ]
        }

        data = self._post_json(_ALGOLIA_MULTI_URL, json_body=payload, headers=headers)
        if not data or "results" not in data:
            logger.warning("[wttj] No results for keyword '%s'.", keyword)
            return []

        return data["results"][0].get("hits", [])

    @staticmethod
    def _parse_hit(hit: dict) -> Job | None:
        """Convert a raw Algolia hit into a :class:`Job`."""
        try:
            org = hit.get("organization") or hit.get("company") or {}
            org_slug = org.get("slug", "")
            job_slug = hit.get("slug", "")
            title = hit.get("name", "")
            company = org.get("name", "Unknown")

            # Location — prefer first office city.
            offices = hit.get("offices", [])
            office = hit.get("office", {})
            if offices:
                city = offices[0].get("city", "Paris")
            elif office:
                city = office.get("city", "Paris")
            else:
                city = "Paris"

            url = (
                f"https://www.welcometothejungle.com/fr/"
                f"companies/{org_slug}/jobs/{job_slug}"
            )

            # Build description from available text fields.
            description = " ".join(
                filter(None, [
                    hit.get("profile", ""),
                    hit.get("description", ""),
                ])
            )

            return Job(
                id=hit.get("objectID", job_slug),
                source="wttj",
                title=title,
                company=company,
                location=city,
                url=url,
                created_at=hit.get("published_at", ""),
                description=description,
                contract_type="apprentissage",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[wttj] Failed to parse hit: %s", exc)
            return None
