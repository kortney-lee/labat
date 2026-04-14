"""
labat/meta_client.py — Low-level HTTP client for the Meta Graph API.

All service modules use this client so that auth headers, rate-limit
tracking, error normalisation and retry logic live in one place.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, Optional

import httpx

from src.labat.config import (
    META_APP_SECRET,
    META_GRAPH_BASE_URL,
    META_API_TIMEOUT,
    META_INSIGHTS_TIMEOUT,
    SHANIA_PAGE_ACCESS_TOKEN,
    META_SYSTEM_USER_TOKEN,
)

logger = logging.getLogger("labat.meta_client")

# ── Lightweight in-memory rate-limit tracker ──────────────────────────────────

_call_timestamps: list[float] = []
_RATE_WINDOW = 3600  # 1 hour


def _record_call() -> None:
    now = time.monotonic()
    _call_timestamps.append(now)
    # prune entries older than window
    cutoff = now - _RATE_WINDOW
    while _call_timestamps and _call_timestamps[0] < cutoff:
        _call_timestamps.pop(0)


def calls_in_window() -> int:
    cutoff = time.monotonic() - _RATE_WINDOW
    while _call_timestamps and _call_timestamps[0] < cutoff:
        _call_timestamps.pop(0)
    return len(_call_timestamps)


# ── Error handling ────────────────────────────────────────────────────────────

class MetaAPIError(Exception):
    """Raised when the Graph API returns an error payload."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        error_code: Optional[int] = None,
        error_subcode: Optional[int] = None,
        fbtrace_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.error_subcode = error_subcode
        self.fbtrace_id = fbtrace_id

    def __str__(self) -> str:
        parts = [self.args[0] if self.args else "Unknown Meta API error"]
        if self.error_code:
            parts.append(f"code={self.error_code}")
        if self.error_subcode:
            parts.append(f"subcode={self.error_subcode}")
        if self.fbtrace_id:
            parts.append(f"fbtrace={self.fbtrace_id}")
        return " | ".join(parts)


def _raise_for_meta_error(resp: httpx.Response) -> None:
    """Parse a Graph API error response and raise MetaAPIError."""
    if resp.is_success:
        return
    logger.error("Meta API error %d: %s", resp.status_code, resp.text[:500])
    try:
        body = resp.json()
    except Exception:
        raise MetaAPIError(
            f"HTTP {resp.status_code}: {resp.text[:300]}",
            status_code=resp.status_code,
        )
    err = body.get("error", {})
    msg = err.get("message", resp.text[:300])
    user_msg = err.get("error_user_msg")
    if user_msg:
        msg = f"{msg} — {user_msg}"
    raise MetaAPIError(
        message=msg,
        status_code=resp.status_code,
        error_code=err.get("code"),
        error_subcode=err.get("error_subcode"),
        fbtrace_id=err.get("fbtrace_id"),
    )


# ── Core request helpers ─────────────────────────────────────────────────────

async def graph_get(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """GET request to the Graph API."""
    token = access_token or SHANIA_PAGE_ACCESS_TOKEN or META_SYSTEM_USER_TOKEN
    if not token:
        raise MetaAPIError("No access token configured", status_code=401)

    url = f"{META_GRAPH_BASE_URL}/{path.lstrip('/')}"
    params = dict(params or {})
    params["access_token"] = token

    _record_call()
    async with httpx.AsyncClient(timeout=timeout or META_API_TIMEOUT) as client:
        resp = await client.get(url, params=params)
    _raise_for_meta_error(resp)
    return resp.json()


async def graph_post(
    path: str,
    data: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """POST request to the Graph API."""
    token = access_token or SHANIA_PAGE_ACCESS_TOKEN or META_SYSTEM_USER_TOKEN
    if not token:
        raise MetaAPIError("No access token configured", status_code=401)

    url = f"{META_GRAPH_BASE_URL}/{path.lstrip('/')}"
    _record_call()

    async with httpx.AsyncClient(timeout=timeout or META_API_TIMEOUT) as client:
        if json_body is not None:
            json_body["access_token"] = token
            resp = await client.post(url, json=json_body)
        else:
            data = dict(data or {})
            data["access_token"] = token
            resp = await client.post(url, data=data)

    _raise_for_meta_error(resp)
    return resp.json()


async def graph_delete(
    path: str,
    access_token: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """DELETE request to the Graph API."""
    token = access_token or SHANIA_PAGE_ACCESS_TOKEN or META_SYSTEM_USER_TOKEN
    if not token:
        raise MetaAPIError("No access token configured", status_code=401)

    url = f"{META_GRAPH_BASE_URL}/{path.lstrip('/')}"
    _record_call()

    async with httpx.AsyncClient(timeout=timeout or META_API_TIMEOUT) as client:
        resp = await client.delete(url, params={"access_token": token})

    _raise_for_meta_error(resp)
    return resp.json()


# ── Webhook signature verification ───────────────────────────────────────────

def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Validate the X-Hub-Signature-256 header from Meta webhooks.
    Returns True if the signature is valid.
    """
    if not META_APP_SECRET:
        logger.warning("META_APP_SECRET not set — cannot verify webhook signatures")
        return False

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        META_APP_SECRET.encode(),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header[7:]  # strip "sha256="
    return hmac.compare_digest(expected, received)
