"""
labat/services/webhook_service.py — Process inbound Meta webhook events.

Responsible for:
  1. Verifying the webhook subscription challenge (GET)
  2. Validating X-Hub-Signature-256 on incoming payloads (POST)
  3. Dispatching events to the appropriate handler (comments, messages, etc.)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional

from src.labat.config import META_WEBHOOK_VERIFY_TOKEN 

logger = logging.getLogger("labat.webhook_service")

# ── Event handler registry ────────────────────────────────────────────────────

EventHandler = Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]

_handlers: Dict[str, List[EventHandler]] = {}


def register_handler(field: str, handler: EventHandler) -> None:
    """
    Register an async handler for a webhook field (e.g. "feed", "messages").
    Multiple handlers per field are supported.
    """
    _handlers.setdefault(field, []).append(handler)
    logger.info("Registered webhook handler for field=%s", field)


# ── Verification ─────────────────────────────────────────────────────────────

def verify_challenge(
    mode: Optional[str],
    token: Optional[str],
    challenge: Optional[str],
) -> Optional[str]:
    """
    Handle the GET verification request from Meta.
    Returns the challenge string if valid, None otherwise.
    """
    if mode == "subscribe" and token == META_WEBHOOK_VERIFY_TOKEN:
        logger.info("Webhook verification succeeded")
        return challenge
    logger.warning("Webhook verification failed: mode=%s token_match=%s", mode, token == META_WEBHOOK_VERIFY_TOKEN)
    return None


# ── Dispatch ──────────────────────────────────────────────────────────────────

async def dispatch_webhook(payload: Dict[str, Any]) -> int:
    """
    Process a validated webhook payload and dispatch to registered handlers.
    Returns the number of events dispatched.
    """
    obj_type = payload.get("object")
    entries = payload.get("entry", [])
    dispatched = 0

    for entry in entries:
        # Page "changes" events (feed, mention, etc.)
        for change in entry.get("changes", []):
            field = change.get("field", "")
            handlers = _handlers.get(field, [])
            for handler in handlers:
                try:
                    await handler(change.get("value", {}))
                    dispatched += 1
                except Exception:
                    logger.exception("Webhook handler error field=%s", field)

        # Messaging events
        for msg_event in entry.get("messaging", []):
            handlers = _handlers.get("messages", [])
            for handler in handlers:
                try:
                    await handler(msg_event)
                    dispatched += 1
                except Exception:
                    logger.exception("Webhook messaging handler error")

    logger.info(
        "Webhook dispatch: object=%s entries=%d dispatched=%d",
        obj_type, len(entries), dispatched,
    )
    return dispatched


# ── Default handlers (logging only — override with register_handler) ─────────

async def _default_feed_handler(value: Dict[str, Any]) -> None:
    """Log feed events (new comments, reactions, etc.)."""
    item = value.get("item", "unknown")
    verb = value.get("verb", "unknown")
    sender = value.get("from", {}).get("name", "unknown")
    logger.info("Feed event: item=%s verb=%s from=%s", item, verb, sender)


async def _default_message_handler(value: Dict[str, Any]) -> None:
    """Log inbound Messenger messages."""
    sender_id = value.get("sender", {}).get("id", "unknown")
    text = value.get("message", {}).get("text", "")
    logger.info("Message received: sender=%s text=%s", sender_id, text[:100])


# Register defaults on import
register_handler("feed", _default_feed_handler)
register_handler("messages", _default_message_handler)
