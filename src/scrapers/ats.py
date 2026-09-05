"""Hub ATS scraper — SmartRecruiters, Greenhouse, and Lever.

Queries the public (no-auth) job-board APIs of configurable companies
and filters for alternance/apprenticeship offers in Paris / IDF.
"""

from __future__ import annotations

import logging
import re
import time
from html import unescape
from typing import List

from src import config
from src.models import Job
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Pre-compiled regex for matching alternance keywords in text.
_ALT_RE = re.compile(
    "|".join(re.escape(kw) for kw in config.ATS_ALTERNANCE_KEYWORDS),
    re.IGNORECASE,
)

# Pre-compiled regex for matching Paris / IDF in location strings.
_PARIS_RE = re.compile(
    r"paris|île-de-france|ile-de-france|idf|levallois|boulogne|"
    r"la\s*d[ée]fense|neuilly|puteaux|montreuil|nanterre|"
    r"issy|saint-denis|courbevoie|rueil|clichy",
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    clean = re.sub(r"<[^>]+>", " ", text)
    return unescape(clean)


def _is_alternance(title: str, description: str = "") -> bool:
    """Return True if title or description mentions alternance keywords."""
    return bool(_ALT_RE.search(title) or _ALT_RE.search(description))


def _is_paris(location: str) -> bool:
    """Return True if location looks like Paris / Île-de-France."""
    return bool(_PARIS_RE.search(location))


# ======================================================================
# SmartRecruiters
# ======================================================================

class SmartRecruitersScraper(BaseScraper):
    """Fetch alternance offers from SmartRecruiters public posting API."""

    name = "smartrecruiters"

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []

        for company_id in config.SMARTRECRUITERS_COMPANIES:
            company_jobs = self._fetch_company(company_id)
            jobs.extend(company_jobs)
            time.sleep(config.ATS_REQUEST_DELAY)

        logger.info(
            "[smartrecruiters] Fetched %d offers across %d companies.",
            len(jobs),
            len(config.SMARTRECRUITERS_COMPANIES),
        )
        return jobs

    def _fetch_company(self, company_id: str) -> List[Job]:
        """Fetch all alternance postings for one SmartRecruiters company."""
        result: List[Job] = []
        offset = 0
        limit = 100

        while True:
            url = (
                f"https://api.smartrecruiters.com/v1/companies/"
                f"{company_id}/postings"
            )
            params = {
                "limit": limit,
                "offset": offset,
                "country": "fr",
            }

            data = self._get_json(url, params=params)
            if data is None:
                break

            postings = data.get("content", [])
            if not postings:
                break

            for posting in postings:
                job = self._parse_posting(posting, company_id)
                if job:
                    result.append(job)

            total = data.get("totalFound", 0)
            offset += limit
            if offset >= total:
                break

            time.sleep(0.5)

        return result

    @staticmethod
    def _parse_posting(posting: dict, company_id: str) -> Job | None:
        """Parse a SmartRecruiters posting dict into a Job, if relevant."""
        try:
            title = posting.get("name", "")
            location_data = posting.get("location", {})
            city = location_data.get("city", "")
            region = location_data.get("region", "")
            loc_str = f"{city} {region}".strip()

            # Check location relevance.
            if not _is_paris(loc_str):
                return None

            # Build description from job ad sections.
            job_ad = posting.get("jobAd", {})
            sections = job_ad.get("sections", {})
            desc_parts = []
            for section_key in ("jobDescription", "qualifications", "additionalInformation"):
                section = sections.get(section_key, {})
                text = section.get("text", "")
                if text:
                    desc_parts.append(_strip_html(text))
            description = " ".join(desc_parts)

            # Check alternance relevance.
            employment_type = posting.get("typeOfEmployment", {})
            type_label = employment_type.get("label", "").lower()
            type_id = employment_type.get("id", "").lower()

            is_alt_by_type = any(
                kw in type_label or kw in type_id
                for kw in ("apprentice", "alternance", "apprenti")
            )

            if not is_alt_by_type and not _is_alternance(title, description):
                return None

            company_name = posting.get("company", {}).get("name", company_id)
            posting_id = posting.get("id", posting.get("uuid", ""))

            # URL construction.
            ref_url = posting.get("ref", "")
            apply_url = (
                f"https://jobs.smartrecruiters.com/{company_id}/"
                f"{posting_id}"
            )

            return Job(
                id=str(posting_id),
                source="smartrecruiters",
                title=title,
                company=company_name,
                location=city or "Paris",
                url=apply_url,
                created_at=posting.get("releasedDate", ""),
                description=description,
                contract_type="alternance",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[smartrecruiters] Parse error for %s: %s",
                company_id,
                exc,
            )
            return None


# ======================================================================
# Greenhouse
# ======================================================================

class GreenhouseScraper(BaseScraper):
    """Fetch alternance offers from Greenhouse public boards API."""

    name = "greenhouse"

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []

        for board_token in config.GREENHOUSE_COMPANIES:
            company_jobs = self._fetch_board(board_token)
            jobs.extend(company_jobs)
            time.sleep(config.ATS_REQUEST_DELAY)

        logger.info(
            "[greenhouse] Fetched %d offers across %d boards.",
            len(jobs),
            len(config.GREENHOUSE_COMPANIES),
        )
        return jobs

    def _fetch_board(self, board_token: str) -> List[Job]:
        """Fetch all alternance jobs from one Greenhouse board."""
        url = (
            f"https://boards-api.greenhouse.io/v1/boards/"
            f"{board_token}/jobs"
        )
        params = {"content": "true"}

        data = self._get_json(url, params=params)
        if data is None:
            return []

        result: List[Job] = []
        for item in data.get("jobs", []):
            job = self._parse_job(item, board_token)
            if job:
                result.append(job)

        return result

    @staticmethod
    def _parse_job(item: dict, board_token: str) -> Job | None:
        """Parse a Greenhouse job into a Job, if relevant."""
        try:
            title = item.get("title", "")
            location_name = item.get("location", {}).get("name", "")

            # Check location relevance.
            if not _is_paris(location_name):
                return None

            # Build description from content field.
            content_html = item.get("content", "")
            description = _strip_html(content_html) if content_html else ""

            # Check alternance relevance.
            # Also check metadata for employment type.
            is_alt = _is_alternance(title, description)
            for meta in item.get("metadata", []):
                if meta.get("name", "").lower() in (
                    "employment type",
                    "type de contrat",
                ):
                    val = str(meta.get("value", "")).lower()
                    if any(
                        kw in val
                        for kw in ("apprentice", "alternance", "apprenti")
                    ):
                        is_alt = True

            if not is_alt:
                return None

            job_id = str(item.get("id", ""))
            absolute_url = item.get(
                "absolute_url",
                f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}",
            )
            updated_at = item.get("updated_at", "")

            # Infer company from board token (capitalize).
            company = board_token.replace("-", " ").title()

            return Job(
                id=job_id,
                source="greenhouse",
                title=title,
                company=company,
                location=location_name,
                url=absolute_url,
                created_at=updated_at,
                description=description,
                contract_type="alternance",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[greenhouse] Parse error for %s: %s", board_token, exc
            )
            return None


# ======================================================================
# Lever
# ======================================================================

class LeverScraper(BaseScraper):
    """Fetch alternance offers from Lever public postings API.

    Tries both the US (``api.lever.co``) and EU (``api.eu.lever.co``)
    endpoints since French companies may be hosted on either.
    """

    name = "lever"

    _BASE_URLS = [
        "https://api.lever.co/v0/postings",
        "https://api.eu.lever.co/v0/postings",
    ]

    def fetch(self) -> List[Job]:
        jobs: List[Job] = []

        for company_slug in config.LEVER_COMPANIES:
            company_jobs = self._fetch_company(company_slug)
            jobs.extend(company_jobs)
            time.sleep(config.ATS_REQUEST_DELAY)

        logger.info(
            "[lever] Fetched %d offers across %d companies.",
            len(jobs),
            len(config.LEVER_COMPANIES),
        )
        return jobs

    def _fetch_company(self, company_slug: str) -> List[Job]:
        """Fetch all alternance postings for one Lever company."""
        for base_url in self._BASE_URLS:
            url = f"{base_url}/{company_slug}"
            params = {"mode": "json"}

            data = self._get_json(url, params=params)
            if data is not None and isinstance(data, list):
                # Found the right endpoint.
                result: List[Job] = []
                for posting in data:
                    job = self._parse_posting(posting, company_slug)
                    if job:
                        result.append(job)
                return result

        logger.debug(
            "[lever] No data found for %s on US or EU endpoints.",
            company_slug,
        )
        return []

    @staticmethod
    def _parse_posting(posting: dict, company_slug: str) -> Job | None:
        """Parse a Lever posting into a Job, if relevant."""
        try:
            title = posting.get("text", "")
            categories = posting.get("categories", {})
            location = categories.get("location", "")
            commitment = categories.get("commitment", "")

            # Check location relevance.
            if not _is_paris(location):
                return None

            # Check alternance relevance via title, commitment, or description.
            desc_html = posting.get("description", "")
            additional_html = posting.get("additional", "")
            lists_html = " ".join(
                lst.get("content", "")
                for lst in posting.get("lists", [])
            )
            full_desc = _strip_html(
                f"{desc_html} {additional_html} {lists_html}"
            )

            is_alt = _is_alternance(title, full_desc) or _is_alternance(
                commitment
            )
            if not is_alt:
                return None

            posting_id = posting.get("id", "")
            hosted_url = posting.get(
                "hostedUrl",
                f"https://jobs.lever.co/{company_slug}/{posting_id}",
            )

            # created_at in Lever is a Unix timestamp in milliseconds.
            created_ms = posting.get("createdAt", 0)
            created_at = ""
            if created_ms:
                from datetime import datetime, timezone

                created_at = datetime.fromtimestamp(
                    created_ms / 1000, tz=timezone.utc
                ).isoformat()

            company = company_slug.replace("-", " ").title()

            return Job(
                id=str(posting_id),
                source="lever",
                title=title,
                company=company,
                location=location,
                url=hosted_url,
                created_at=created_at,
                description=full_desc,
                contract_type=commitment.lower() or "alternance",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[lever] Parse error for %s: %s", company_slug, exc
            )
            return None


# ======================================================================
# Unified ATS Hub entry point
# ======================================================================

class ATSHubScraper(BaseScraper):
    """Meta-scraper that runs all three ATS scrapers."""

    name = "ats_hub"

    def fetch(self) -> List[Job]:
        all_jobs: List[Job] = []

        scrapers = [
            SmartRecruitersScraper(),
            GreenhouseScraper(),
            LeverScraper(),
        ]

        for scraper in scrapers:
            try:
                jobs = scraper.fetch()
                all_jobs.extend(jobs)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "[ats_hub] %s scraper crashed: %s",
                    scraper.name,
                    exc,
                    exc_info=True,
                )

        logger.info(
            "[ats_hub] Total: %d offers from all ATS sources.",
            len(all_jobs),
        )
        return all_jobs
