"""Telegram Bot API notifier.

Sends formatted HTML messages to a Telegram chat via the Bot API.
Automatically splits long messages to respect the 4096-char limit.
"""

from __future__ import annotations

import logging
from typing import List

import requests

from src import config
from src.models import Job

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(jobs: List[Job]) -> bool:
    """Send a formatted digest of *jobs* to the configured Telegram chat.

    Returns ``True`` if all messages were sent successfully.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning(
            "[telegram] Bot token or chat ID not configured — skipping."
        )
        return False

    if not jobs:
        if config.HEARTBEAT_ENABLED:
            return _send_message(
                "✅ <b>Scraping terminé</b> — aucune nouvelle offre "
                "d'alternance aujourd'hui.\n\n"
                "Le prochain scan aura lieu demain matin. 🔄"
            )
        return True

    # Build the full message.
    header = (
        f"🎓 <b>Nouvelles offres d'alternance</b>\n"
        f"📊 {len(jobs)} nouvelle(s) offre(s) trouvée(s)\n"
        f"{'━' * 30}\n\n"
    )

    blocks = [job.to_notification_block() for job in jobs]

    # Split into chunks that fit Telegram's 4096-char limit.
    messages = _split_messages(header, blocks)

    success = True
    for msg in messages:
        if not _send_message(msg):
            success = False

    return success


def _send_message(text: str) -> bool:
    """Send a single message via the Telegram Bot API."""
    url = _API_BASE.format(token=config.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("ok"):
            logger.warning(
                "[telegram] API returned ok=false: %s",
                result.get("description"),
            )
            return False
        logger.debug("[telegram] Message sent successfully.")
        return True
    except requests.RequestException as exc:
        logger.error("[telegram] Failed to send message: %s", exc)
        return False


def _split_messages(
    header: str,
    blocks: List[str],
    max_len: int = config.TELEGRAM_MAX_LENGTH,
) -> List[str]:
    """Split a header + list of blocks into messages under *max_len*.

    Each message after the first gets a continuation header.
    """
    messages: List[str] = []
    current = header
    separator = "\n\n"

    for i, block in enumerate(blocks):
        candidate = current + separator + block
        if len(candidate) > max_len:
            # Flush current message.
            messages.append(current)
            # Start a new message with a continuation header.
            part = len(messages) + 1
            current = (
                f"📋 <b>Suite ({part})</b>\n"
                f"{'━' * 30}\n\n"
                f"{block}"
            )
        else:
            current = candidate

    # Don't forget the last chunk.
    if current:
        messages.append(current)

    return messages
