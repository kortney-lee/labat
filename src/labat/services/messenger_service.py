"""
labat/services/messenger_service.py — Messenger send + private replies.

Supports:
  - Sending messages to users who have messaged the Page
  - Private replies to public Page comments (within 7-day window)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.labat.brands import BRAND_PAGE_IDS
from src.labat.config import SHANIA_PAGE_ACCESS_TOKEN
from src.labat.meta_client import graph_post, MetaAPIError


def _shania() -> str:
    """Shania page token — manages Messenger / private replies."""
    if not SHANIA_PAGE_ACCESS_TOKEN:
        raise MetaAPIError("SHANIA_PAGE_ACCESS_TOKEN not configured", status_code=500)
    return SHANIA_PAGE_ACCESS_TOKEN

logger = logging.getLogger("labat.messenger_service")


async def send_message(
    recipient_id: str,
    message_text: str,
    messaging_type: str = "RESPONSE",
    tag: Optional[str] = None,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a message via the Page's Messenger.

    messaging_type:
      RESPONSE    — reply within 24h standard window
      UPDATE      — proactive non-promotional (requires approval)
      MESSAGE_TAG — outside 24h window (requires tag)

    tag examples: CONFIRMED_EVENT_UPDATE, POST_PURCHASE_UPDATE,
                  ACCOUNT_UPDATE, HUMAN_AGENT
    """
    pid = page_id or BRAND_PAGE_IDS["wihy"]
    if not pid:
        raise MetaAPIError("No page_id configured", status_code=400)

    payload: Dict[str, Any] = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "messaging_type": messaging_type,
    }
    if tag:
        payload["tag"] = tag

    result = await graph_post(f"{pid}/messages", json_body=payload, access_token=_shania())
    logger.info("Sent message to %s via Page %s", recipient_id, pid)
    return result


async def send_private_reply(
    comment_id: str,
    message: str,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a private Messenger message to the author of a public comment.
    Only works within Meta's messaging window (typically 7 days).
    """
    pid = page_id or BRAND_PAGE_IDS["wihy"]
    if not pid:
        raise MetaAPIError("No page_id configured", status_code=400)

    payload: Dict[str, Any] = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE",
    }

    result = await graph_post(f"{pid}/messages", json_body=payload, access_token=_shania())
    logger.info("Sent private reply for comment %s via Page %s", comment_id, pid)
    return result
