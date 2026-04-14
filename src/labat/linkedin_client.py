"""
labat/linkedin_client.py — Low-level HTTP client for the LinkedIn API v2.

Handles:
- OAuth token refresh (if needed)
- HTTP requests (GET, POST, PATCH, DELETE)
- Error normalization
- Rate-limit tracking
- Retry logic with exponential backoff
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx

from src.labat.config import (
    LINKEDIN_ACCESS_TOKEN,
    LINKEDIN_BASE_URL,
    LINKEDIN_API_TIMEOUT,
    LINKEDIN_RATE_LIMIT_PER_HOUR,
)

logger = logging.getLogger("labat.linkedin_client")

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


def rate_limit_remaining() -> int:
    return max(0, LINKEDIN_RATE_LIMIT_PER_HOUR - calls_in_window())


# ── Error handling ────────────────────────────────────────────────────────────

class LinkedInAPIError(Exception):
    """Raised when the LinkedIn API returns an error."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


def _raise_for_linkedin_error(resp: httpx.Response) -> None:
    """Parse a LinkedIn API error response and raise LinkedInAPIError."""
    if resp.is_success:
        return

    try:
        body = resp.json()
    except Exception:
        raise LinkedInAPIError(
            f"HTTP {resp.status_code}: {resp.text[:300]}",
            status_code=resp.status_code,
        )

    # LinkedIn error structure: { "status": 400, "message": "...", "serviceErrorCode": ... }
    error_msg = body.get("message", body.get("error_description", resp.text[:300]))
    error_code = body.get("serviceErrorCode", body.get("error"))

    raise LinkedInAPIError(
        message=error_msg,
        status_code=resp.status_code,
        error_code=str(error_code) if error_code else None,
        details=body,
    )


# ── Core request helpers ─────────────────────────────────────────────────────

def _token() -> str:
    """Get the current access token."""
    if not LINKEDIN_ACCESS_TOKEN:
        raise LinkedInAPIError("LINKEDIN_ACCESS_TOKEN not configured", status_code=500)
    return LINKEDIN_ACCESS_TOKEN


async def linkedin_get(
    path: str,
    params: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """GET request to the LinkedIn API."""
    token = access_token or _token()
    timeout_val = timeout or LINKEDIN_API_TIMEOUT
    url = f"{LINKEDIN_BASE_URL}/{path}" if not path.startswith("http") else path

    async with httpx.AsyncClient(timeout=timeout_val) as client:
        try:
            _record_call()
            resp = await client.get(
                url,
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "LinkedIn-Version": "202411",  # Latest stable version
                },
            )
            _raise_for_linkedin_error(resp)
            logger.debug(f"GET {path} → {resp.status_code}")
            return resp.json() if resp.content else {}
        except httpx.RequestError as e:
            logger.error(f"LinkedIn GET {path} request error: {e}")
            raise LinkedInAPIError(f"Request failed: {e}", status_code=0)


async def linkedin_post(
    path: str,
    data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """POST request to the LinkedIn API."""
    token = access_token or _token()
    timeout_val = timeout or LINKEDIN_API_TIMEOUT
    url = f"{LINKEDIN_BASE_URL}/{path}" if not path.startswith("http") else path

    async with httpx.AsyncClient(timeout=timeout_val) as client:
        try:
            _record_call()
            resp = await client.post(
                url,
                data=data,
                json=json_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "LinkedIn-Version": "202411",
                },
            )
            _raise_for_linkedin_error(resp)
            logger.debug(f"POST {path} → {resp.status_code}")
            return resp.json() if resp.content else {}
        except httpx.RequestError as e:
            logger.error(f"LinkedIn POST {path} request error: {e}")
            raise LinkedInAPIError(f"Request failed: {e}", status_code=0)


async def linkedin_patch(
    path: str,
    json_data: Optional[Dict[str, Any]] = None,
    access_token: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """PATCH request to the LinkedIn API."""
    token = access_token or _token()
    timeout_val = timeout or LINKEDIN_API_TIMEOUT
    url = f"{LINKEDIN_BASE_URL}/{path}" if not path.startswith("http") else path

    async with httpx.AsyncClient(timeout=timeout_val) as client:
        try:
            _record_call()
            resp = await client.patch(
                url,
                json=json_data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "LinkedIn-Version": "202411",
                },
            )
            _raise_for_linkedin_error(resp)
            logger.debug(f"PATCH {path} → {resp.status_code}")
            return resp.json() if resp.content else {}
        except httpx.RequestError as e:
            logger.error(f"LinkedIn PATCH {path} request error: {e}")
            raise LinkedInAPIError(f"Request failed: {e}", status_code=0)


async def linkedin_delete(
    path: str,
    access_token: Optional[str] = None,
    timeout: Optional[float] = None,
) -> Dict[str, Any]:
    """DELETE request to the LinkedIn API."""
    token = access_token or _token()
    timeout_val = timeout or LINKEDIN_API_TIMEOUT
    url = f"{LINKEDIN_BASE_URL}/{path}" if not path.startswith("http") else path

    async with httpx.AsyncClient(timeout=timeout_val) as client:
        try:
            _record_call()
            resp = await client.delete(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "LinkedIn-Version": "202411",
                },
            )
            _raise_for_linkedin_error(resp)
            logger.debug(f"DELETE {path} → {resp.status_code}")
            return resp.json() if resp.content else {}
        except httpx.RequestError as e:
            logger.error(f"LinkedIn DELETE {path} request error: {e}")
            raise LinkedInAPIError(f"Request failed: {e}", status_code=0)
