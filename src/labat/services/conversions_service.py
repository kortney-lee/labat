"""
labat/services/conversions_service.py — Meta Conversions API (CAPI).

Sends server-side events (Purchase, Lead, etc.) to Meta for attribution
and ad optimisation.  Meant to be called from your backend alongside or
instead of the browser pixel.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

from src.labat.config import META_AD_ACCOUNT_ID, META_SYSTEM_USER_TOKEN
from src.labat.meta_client import graph_post, MetaAPIError

logger = logging.getLogger("labat.conversions_service")

# Meta pixel ID is typically per-ad-account; read from env for flexibility
import os
META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")


def _pixel() -> str:
    if not META_PIXEL_ID:
        raise MetaAPIError("META_PIXEL_ID not set", status_code=500)
    return META_PIXEL_ID


def _token() -> str:
    if not META_SYSTEM_USER_TOKEN:
        raise MetaAPIError("META_SYSTEM_USER_TOKEN not configured", status_code=500)
    return META_SYSTEM_USER_TOKEN


def hash_pii(value: str) -> str:
    """SHA-256 hash a PII value (lowercase, stripped) per Meta requirements."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


async def send_events(
    events: List[Dict[str, Any]],
    test_event_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a batch of conversion events to Meta Conversions API.

    Each event dict should match the ConversionEvent schema:
      event_name, event_time, action_source, user_data, custom_data, event_id, ...

    user_data values (em, ph, fn, ln, etc.) should already be SHA-256 hashed.
    """
    payload: Dict[str, Any] = {"data": events}
    if test_event_code:
        payload["test_event_code"] = test_event_code

    import json
    result = await graph_post(
        f"{_pixel()}/events",
        data={"data": json.dumps(events), **({"test_event_code": test_event_code} if test_event_code else {})},
        access_token=_token(),
    )
    logger.info(
        "Sent %d conversion events → received=%s",
        len(events),
        result.get("events_received"),
    )
    return result


async def send_single_event(
    event_name: str,
    user_data: Dict[str, Any],
    custom_data: Optional[Dict[str, Any]] = None,
    event_source_url: Optional[str] = None,
    event_id: Optional[str] = None,
    action_source: str = "website",
    test_event_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Convenience wrapper for sending one event."""
    event = {
        "event_name": event_name,
        "event_time": int(time.time()),
        "action_source": action_source,
        "user_data": user_data,
    }
    if custom_data:
        event["custom_data"] = custom_data
    if event_source_url:
        event["event_source_url"] = event_source_url
    if event_id:
        event["event_id"] = event_id

    return await send_events([event], test_event_code=test_event_code)
