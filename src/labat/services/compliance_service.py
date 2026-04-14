"""
labat/services/compliance_service.py — Data deletion callback & privacy compliance.

Meta requires a data deletion callback URL.  When a user removes your app,
Meta sends a signed request, and LABAT must respond with a confirmation code
and status URL.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from src.labat.config import META_APP_SECRET, SHANIA_APP_SECRET

logger = logging.getLogger("labat.compliance_service")

# In-memory store (swap for a DB in production)
_deletion_requests: Dict[str, Dict[str, Any]] = {}


def parse_signed_request(signed_request: str) -> Optional[Dict[str, Any]]:
    """
    Parse and verify a Meta signed_request.
    Tries Shania app secret first (page data deletion), then LABAT app secret.
    Returns the decoded payload or None if invalid.
    """
    # Try Shania secret first (page-related callbacks come from Shania app)
    for secret in filter(None, [SHANIA_APP_SECRET, META_APP_SECRET]):
        result = _try_parse_signed_request(signed_request, secret)
        if result is not None:
            return result
    logger.error("Signed request verification failed with all app secrets")
    return None


def _try_parse_signed_request(signed_request: str, app_secret: str) -> Optional[Dict[str, Any]]:
    """Attempt to verify and parse a signed_request using the given app secret."""
    if not app_secret:
        return None

    try:
        sig_encoded, payload_encoded = signed_request.split(".", 1)
    except ValueError:
        logger.warning("Malformed signed_request")
        return None

    # Pad base64
    def _b64_pad(s: str) -> str:
        return s + "=" * (4 - len(s) % 4) if len(s) % 4 else s

    try:
        sig = base64.urlsafe_b64decode(_b64_pad(sig_encoded))
        payload_bytes = base64.urlsafe_b64decode(_b64_pad(payload_encoded))
        payload = json.loads(payload_bytes)
    except Exception as e:
        logger.warning("Failed to decode signed_request: %s", e)
        return None

    expected_sig = hmac.new(
        app_secret.encode(),
        payload_encoded.encode(),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(sig, expected_sig):
        return None

    return payload


def handle_data_deletion(signed_request: str, status_url_base: str) -> Tuple[str, str]:
    """
    Process a data-deletion callback from Meta.
    Returns (status_url, confirmation_code).
    """
    payload = parse_signed_request(signed_request)
    if not payload:
        raise ValueError("Invalid signed request")

    user_id = payload.get("user_id", "unknown")
    confirmation_code = uuid.uuid4().hex[:12]

    _deletion_requests[confirmation_code] = {
        "user_id": user_id,
        "status": "pending",
        "requested_at": payload.get("issued_at"),
    }

    logger.info(
        "Data deletion request: user_id=%s confirmation=%s",
        user_id, confirmation_code,
    )

    status_url = f"{status_url_base}/api/labat/compliance/deletion-status?code={confirmation_code}"
    return status_url, confirmation_code


def get_deletion_status(confirmation_code: str) -> Optional[Dict[str, Any]]:
    """Check the status of a data deletion request."""
    return _deletion_requests.get(confirmation_code)
