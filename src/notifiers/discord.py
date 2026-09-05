"""Discord webhook notifier (fallback).

Sends formatted messages to a Discord channel via a webhook URL.
Used as a backup when Telegram delivery fails or as a secondary
notification channel.
"""

from __future__ import annotations

import logging
from typing import List

import requests

from src import config
from src.models import Job

logger = logging.getLogger(__name__)

# Discord webhook messages can be up to 2000 characters.
_DISCORD_MAX_LENGTH = 2000


def send_discord(jobs: List[Job]) -> bool:
    """Send a formatted digest of *jobs* to the configured Discord webhook.

    Returns ``True`` if all messages were sent successfully.
    """
    if not config.DISCORD_WEBHOOK_URL:
        logger.warning(
            "[discord] Webhook URL not configured — skipping."
        )
        return False

    if not jobs:
        if config.HEARTBEAT_ENABLED:
            return _send_message(
                "✅ **Scraping terminé** — aucune nouvelle offre "
                "d'alternance aujourd'hui.\n\n"
                "Le prochain scan aura lieu demain matin. 🔄"
            )
        return True

    # Build the full message.
    header = (
        f"🎓 **Nouvelles offres d'alternance**\n"
        f"📊 {len(jobs)} nouvelle(s) offre(s) trouvée(s)\n"
        f"{'━' * 30}\n\n"
    )

    blocks = [job.to_discord_block() for job in jobs]

    # Split into chunks that fit Discord's 2000-char limit.
    messages = _split_messages(header, blocks)

    success = True
    for msg in messages:
        if not _send_message(msg):
            success = False

    return success


def _send_message(content: str) -> bool:
    """Send a single message to the Discord webhook."""
    payload = {"content": content}

    try:
        resp = requests.post(
            config.DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=config.HTTP_TIMEOUT,
        )
        # Discord returns 204 No Content on success.
        if resp.status_code not in (200, 204):
            logger.warning(
                "[discord] Webhook returned HTTP %d: %s",
                resp.status_code,
                resp.text[:200],
            )
            return False
        logger.debug("[discord] Message sent successfully.")
        return True
    except requests.RequestException as exc:
        logger.error("[discord] Failed to send message: %s", exc)
        return False


def _split_messages(
    header: str,
    blocks: List[str],
    max_len: int = _DISCORD_MAX_LENGTH,
) -> List[str]:
    """Split a header + list of blocks into messages under *max_len*."""
    messages: List[str] = []
    current = header
    separator = "\n\n"

    for block in blocks:
        candidate = current + separator + block
        if len(candidate) > max_len:
            messages.append(current)
            part = len(messages) + 1
            current = (
                f"📋 **Suite ({part})**\n"
                f"{'━' * 30}\n\n"
                f"{block}"
            )
        else:
            current = candidate

    if current:
        messages.append(current)

    return messages
