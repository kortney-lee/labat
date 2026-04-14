"""
labat/auth.py — Authentication for LABAT endpoints.

Accepts either:
  - X-Admin-Token header (internal admin tools)
  - X-Client-ID + X-Client-Secret headers (frontend apps like wihy.ai)

Brand enforcement:
  - LABAT_BRAND_SCOPE env var restricts which brands this instance serves.
  - When set to a specific brand (wihy, cg, vowels), cross-brand requests get 403.
  - When set to "all" (default), all brands are accepted.
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from fastapi import HTTPException, Request

from src.labat.config import INTERNAL_ADMIN_TOKEN

logger = logging.getLogger("labat.auth")

WIHY_ML_CLIENT_SECRET = (os.getenv("WIHY_ML_CLIENT_SECRET", "") or "").strip()
OAUTH_FRONTEND_CLIENT_SECRET = (os.getenv("OAUTH_FRONTEND_CLIENT_SECRET", "") or "").strip()

# Brand scope for this Labat instance (set per deployment)
LABAT_BRAND_SCOPE = (os.getenv("LABAT_BRAND_SCOPE", "all") or "all").strip().lower()
VALID_BRANDS = {"wihy", "cg", "communitygroceries", "vowels", "childrennutrition", "parentingwithchrist", "all"}

# Secrets that grant access when sent via X-Client-Secret header
_VALID_SECRETS = [
    s for s in [WIHY_ML_CLIENT_SECRET, OAUTH_FRONTEND_CLIENT_SECRET] if s
]


def require_admin(request: Request) -> None:
    """FastAPI dependency that enforces auth on LABAT routes.

    Accepts admin token OR client credentials (X-Client-Secret).
    """
    admin_token = (request.headers.get("X-Admin-Token") or "").strip()
    client_secret = (request.headers.get("X-Client-Secret") or "").strip()

    # No secrets configured — dev mode
    if not INTERNAL_ADMIN_TOKEN and not _VALID_SECRETS:
        logger.warning("No auth secrets set — LABAT routes are open (dev mode)")
        return

    # Check admin token
    if admin_token and INTERNAL_ADMIN_TOKEN and secrets.compare_digest(admin_token, INTERNAL_ADMIN_TOKEN):
        return

    # Check client secret against all known valid secrets
    if client_secret:
        for valid in _VALID_SECRETS:
            if secrets.compare_digest(client_secret, valid):
                return

    raise HTTPException(status_code=401, detail="Unauthorized")


def enforce_brand(brand: Optional[str]) -> str:
    """Validate brand against this instance's scope.

    Returns the validated brand string.
    Raises 400 for unknown brands, 403 for out-of-scope brands.
    """
    if not brand:
        if LABAT_BRAND_SCOPE != "all":
            # Instance is brand-scoped — use it as default
            return LABAT_BRAND_SCOPE
        raise HTTPException(
            status_code=400,
            detail="Brand is required. Valid brands: wihy, cg, vowels",
        )

    brand = brand.strip().lower()
    if brand not in VALID_BRANDS or brand == "all":
        raise HTTPException(
            status_code=400,
            detail=f"Unknown brand '{brand}'. Valid brands: wihy, cg, communitygroceries, vowels, childrennutrition, parentingwithchrist",
        )

    if LABAT_BRAND_SCOPE != "all" and brand != LABAT_BRAND_SCOPE:
        logger.warning(
            "Brand scope violation: instance=%s, requested=%s",
            LABAT_BRAND_SCOPE, brand,
        )
        raise HTTPException(
            status_code=403,
            detail=f"This service only handles brand '{LABAT_BRAND_SCOPE}', got '{brand}'",
        )

    return brand
