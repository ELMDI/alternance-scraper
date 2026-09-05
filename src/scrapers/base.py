"""Abstract base class for all scrapers."""

from __future__ import annotations

import abc
import logging
from typing import List

import requests

from src import config
from src.models import Job

logger = logging.getLogger(__name__)


class BaseScraper(abc.ABC):
    """Common interface and utilities for every job-source scraper."""

    name: str = "base"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
        })

    # ------------------------------------------------------------------
    # Abstract
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def fetch(self) -> List[Job]:
        """Fetch all matching job offers from this source.

        Implementations must return a list of :class:`Job` objects with
        at least ``id``, ``source``, ``title``, ``company``, ``location``,
        and ``url`` populated.
        """

    # ------------------------------------------------------------------
    # Helpers available to all subclasses
    # ------------------------------------------------------------------

    def _get_json(
        self,
        url: str,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int | None = None,
    ) -> dict | list | None:
        """Perform a GET request and return parsed JSON, or ``None`` on error."""
        try:
            resp = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout or config.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.warning(
                "[%s] GET %s failed: %s", self.name, url, exc
            )
            return None

    def _post_json(
        self,
        url: str,
        json_body: dict | None = None,
        headers: dict | None = None,
        timeout: int | None = None,
    ) -> dict | list | None:
        """Perform a POST request and return parsed JSON, or ``None`` on error."""
        try:
            resp = self.session.post(
                url,
                json=json_body,
                headers=headers,
                timeout=timeout or config.HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            logger.warning(
                "[%s] POST %s failed: %s", self.name, url, exc
            )
            return None
