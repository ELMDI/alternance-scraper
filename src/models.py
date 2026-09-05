"""Normalized data models for job offers across all sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Job:
    """Normalized job offer representation shared by every scraper.

    Attributes:
        id: Unique identifier scoped to the source (e.g. ``wttj:abc123``).
        source: Origin platform tag (``wttj``, ``lba``, ``j1s``,
                ``smartrecruiters``, ``greenhouse``, ``lever``).
        title: Human-readable job title.
        company: Employer name.
        location: City or area string.
        url: Direct URL to the offer page.
        start_date: Detected start date or ``"À vérifier"``.
        created_at: ISO-8601 publication timestamp.
        description: Full-text body used for filtering (may be HTML).
        contract_type: Normalized type (``apprentissage``,
                       ``professionnalisation``, ``alternance``).
        score: Relevance score assigned by the filtering pipeline.
    """

    id: str
    source: str
    title: str
    company: str
    location: str
    url: str
    start_date: str = "À vérifier"
    created_at: str = ""
    description: str = ""
    contract_type: str = "alternance"
    score: int = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def dedup_key(self) -> str:
        """Return a composite key used for deduplication."""
        return f"{self.source}:{self.id}"

    def to_notification_block(self) -> str:
        """Format this job for a Telegram / Discord message (HTML)."""
        return (
            f'🔹 <a href="{self.url}">{_escape_html(self.title)}</a>\n'
            f"🏢 {_escape_html(self.company)} | 📍 {_escape_html(self.location)} "
            f"| 🗓️ Rentrée : {_escape_html(self.start_date)}\n"
            f"🏷️ Source : {self.source.upper()}"
        )

    def to_discord_block(self) -> str:
        """Format this job for a Discord message (Markdown)."""
        return (
            f"🔹 [{self.title}]({self.url})\n"
            f"🏢 {self.company} | 📍 {self.location} "
            f"| 🗓️ Rentrée : {self.start_date}\n"
            f"🏷️ Source : {self.source.upper()}"
        )


def _escape_html(text: str) -> str:
    """Minimal HTML escaping for Telegram HTML parse mode."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
