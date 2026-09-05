"""1jeune1solution / France Travail scraper (optional — requires OAuth2).

Queries the France Travail ``offresdemploi`` API v2 for apprenticeship
and professional-contract offers in Île-de-France.

This module is **complementary** to La Bonne Alternance (which already
aggregates most France Travail offers). It provides extra coverage with
different search parameters and keyword-based queries.

If the ``FRANCE_TRAVAIL_CLIENT_ID`` and ``FRANCE_TRAVAIL_CLIENT_SECRET``
environment variables are not set, this scraper is gracefully skipped.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

from src import config
from src.models import Job
from src.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)


class J1SScraper(BaseScraper):
    """Fetch alternance offers from the France Travail API (1jeune1solution)."""

    name = "j1s"

    def __init__(self) -> None:
        super().__init__()
        self._access_token: str = ""

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def fetch(self) -> List[Job]:
        # Guard: credentials must be configured.
        if not config.FT_CLIENT_ID or not config.FT_CLIENT_SECRET:
            logger.info(
                "[j1s] France Travail credentials not configured — "
                "skipping this source."
            )
            return []

        # Obtain an OAuth2 access token.
        if not self._authenticate():
            return []

        jobs: List[Job] = []
        seen_ids: set[str] = set()

        # Query each keyword across all IDF departments.
        for keyword in config.SEARCH_KEYWORDS:
            results = self._search(keyword)
            for item in results:
                job = self._parse(item)
                if job and job.id not in seen_ids:
                    seen_ids.add(job.id)
                    jobs.append(job)
            time.sleep(0.5)  # rate-limit courtesy

        logger.info("[j1s] Fetched %d unique offers.", len(jobs))
        return jobs

    # ------------------------------------------------------------------
    # OAuth2
    # ------------------------------------------------------------------

    def _authenticate(self) -> bool:
        """Obtain an access token via client_credentials grant."""
        try:
            resp = self.session.post(
                config.FT_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": config.FT_CLIENT_ID,
                    "client_secret": config.FT_CLIENT_SECRET,
                    "scope": (
                        "api_offresdemploiv2 o2dsoffre"
                    ),
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                params={"realm": "/partenaire"},
                timeout=config.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            token_data = resp.json()
            self._access_token = token_data["access_token"]
            logger.debug("[j1s] OAuth2 token obtained successfully.")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[j1s] OAuth2 authentication failed: %s", exc
            )
            return False

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _search(self, keyword: str) -> list[dict]:
        """Search France Travail offers for *keyword* in IDF."""
        params: dict = {
            "motsCles": keyword,
            "typeContrat": "E2,FS",  # E2=apprentissage, FS=contrat pro
            "departement": ",".join(config.IDF_DEPARTMENTS),
            "range": "0-149",  # max 150 results per query
        }

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
        }

        data = self._get_json(
            config.FT_API_URL,
            params=params,
            headers=headers,
        )
        if data is None:
            return []

        return data.get("resultats", [])

    # ------------------------------------------------------------------
    # Parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse(item: dict) -> Job | None:
        """Convert a France Travail offer dict into a :class:`Job`."""
        try:
            job_id = item.get("id", "")
            title = item.get("intitule", "")
            if not job_id or not title:
                return None

            entreprise = item.get("entreprise", {})
            company = entreprise.get("nom", "Entreprise inconnue")

            lieu = item.get("lieuTravail", {})
            city = lieu.get("libelle", "Île-de-France")
            # Clean up city label (e.g. "75 - PARIS 01" → "Paris")
            if " - " in city:
                city = city.split(" - ", 1)[1].strip().title()

            # Build URL.
            url = (
                f"https://candidat.francetravail.fr/offres/"
                f"recherche/detail/{job_id}"
            )

            description = item.get("description", "")
            contract_label = item.get("typeContratLibelle", "Alternance")
            created_at = item.get("dateCreation", "")

            return Job(
                id=job_id,
                source="j1s",
                title=title,
                company=company,
                location=city,
                url=url,
                created_at=created_at,
                description=description,
                contract_type=contract_label.lower(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[j1s] Failed to parse offer: %s", exc)
            return None
