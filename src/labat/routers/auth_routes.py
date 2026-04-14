"""
labat/routers/auth_routes.py — Token management endpoints.

POST /api/labat/auth/exchange          — short-lived → long-lived token (LABAT app)
POST /api/labat/auth/exchange-shania   — short-lived → long-lived page token (Shania app)
GET  /api/labat/auth/callback          — OAuth redirect callback
GET  /api/labat/auth/pages             — list Page tokens for a user token
GET  /api/labat/auth/debug-token       — inspect a token
GET  /api/labat/auth/ad-accounts       — list ad accounts for a user token
GET  /api/labat/auth/businesses        — list businesses for a user token
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from src.labat.auth import require_admin
from src.labat.schemas import (
    TokenExchangeRequest,
    TokenExchangeResponse,
    PageTokenResponse,
)
from src.labat.services.token_service import (
    exchange_for_long_lived_token,
    exchange_shania_token,
    get_page_tokens,
    debug_token,
    get_ad_accounts,
    get_businesses,
)
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.auth_routes")

router = APIRouter(prefix="/api/labat/auth", tags=["labat-auth"])


@router.get("/callback")
async def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
):
    """OAuth redirect callback. Receives authorization code from Meta."""
    if error:
        logger.warning("OAuth error: %s — %s", error, error_description)
        return JSONResponse(
            status_code=400,
            content={"error": error, "description": error_description},
        )
    if not code:
        return JSONResponse(status_code=400, content={"error": "missing_code"})

    logger.info("OAuth callback received (state=%s)", state)
    # Exchange code for token server-side if needed
    return {"status": "ok", "code_received": True, "state": state}


@router.post("/exchange", response_model=TokenExchangeResponse)
async def token_exchange(
    body: TokenExchangeRequest,
    _=Depends(require_admin),
):
    """Exchange a short-lived user token for a long-lived one (~60 days). Uses LABAT app."""
    try:
        result = await exchange_for_long_lived_token(body.short_lived_token)
        return TokenExchangeResponse(**result)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/exchange-shania")
async def shania_token_exchange(
    body: TokenExchangeRequest,
    _=Depends(require_admin),
):
    """Exchange a short-lived Shania user token for a long-lived one + page tokens.
    Use this after getting a token from Graph API Explorer with the Shania app selected."""
    try:
        result = await exchange_shania_token(body.short_lived_token)
        return result
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/pages")
async def list_page_tokens(
    request: Request,
    user_token: str = Query(..., description="Long-lived user access token"),
    _=Depends(require_admin),
):
    """List all Pages and their tokens for the given user token."""
    try:
        pages = await get_page_tokens(user_token)
        return {"pages": pages}
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/debug-token")
async def inspect_token(
    token: str = Query(..., description="Token to inspect"),
    _=Depends(require_admin),
):
    """Inspect token metadata (scopes, expiry, etc.)."""
    try:
        info = await debug_token(token)
        return {"token_info": info}
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/ad-accounts")
async def list_ad_accounts(
    user_token: str = Query(..., description="Long-lived user access token"),
    _=Depends(require_admin),
):
    """List all ad accounts accessible by the given user token."""
    try:
        accounts = await get_ad_accounts(user_token)
        return {"ad_accounts": accounts}
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/businesses")
async def list_businesses(
    user_token: str = Query(..., description="Long-lived user access token"),
    _=Depends(require_admin),
):
    """List all businesses the user is admin/employee of."""
    try:
        businesses = await get_businesses(user_token)
        return {"businesses": businesses}
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
