"""
labat/services/token_service.py — Meta OAuth token management.

Handles short-lived → long-lived token exchange, Page token retrieval,
and token inspection.  System-user tokens are static and set via env vars.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.labat.brands import BRAND_PAGE_IDS
from src.labat.config import (
    META_APP_ID, META_APP_SECRET,
    SHANIA_APP_ID, SHANIA_APP_SECRET,
    SHANIA_PAGE_ACCESS_TOKEN,
    SHANIA_LONG_LIVED_USER_TOKEN,
)
from src.labat.meta_client import graph_get, MetaAPIError

logger = logging.getLogger("labat.token_service")


async def get_shania_page_access_token(page_id: Optional[str] = None) -> str:
    """Return the correct Shania page token for the requested page."""
    pid = page_id or BRAND_PAGE_IDS["wihy"]
    if not pid:
        raise MetaAPIError("No page_id provided and no default brand page set", status_code=400)

    if pid == BRAND_PAGE_IDS["wihy"] and SHANIA_PAGE_ACCESS_TOKEN:
        return SHANIA_PAGE_ACCESS_TOKEN

    if not SHANIA_LONG_LIVED_USER_TOKEN:
        raise MetaAPIError(
            "SHANIA_LONG_LIVED_USER_TOKEN not configured for non-default page access",
            status_code=500,
        )

    result = await get_page_token(SHANIA_LONG_LIVED_USER_TOKEN, pid)
    return result["access_token"]


async def exchange_for_long_lived_token(short_lived_token: str) -> Dict[str, Any]:
    """Exchange a short-lived LABAT user token for a long-lived one (~60 days)."""
    if not META_APP_ID or not META_APP_SECRET:
        raise MetaAPIError("META_APP_ID / META_APP_SECRET not configured", status_code=500)

    result = await graph_get(
        "oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": META_APP_ID,
            "client_secret": META_APP_SECRET,
            "fb_exchange_token": short_lived_token,
        },
        access_token=short_lived_token,
    )
    return {
        "access_token": result["access_token"],
        "token_type": result.get("token_type", "bearer"),
        "expires_in": result.get("expires_in"),
    }


async def exchange_shania_token(short_lived_token: str) -> Dict[str, Any]:
    """Exchange a short-lived Shania user token for a long-lived one.
    Use this when generating a new Shania page access token.
    """
    if not SHANIA_APP_ID or not SHANIA_APP_SECRET:
        raise MetaAPIError("SHANIA_APP_ID / SHANIA_APP_SECRET not configured", status_code=500)

    result = await graph_get(
        "oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": SHANIA_APP_ID,
            "client_secret": SHANIA_APP_SECRET,
            "fb_exchange_token": short_lived_token,
        },
        access_token=short_lived_token,
    )
    long_lived = result["access_token"]

    # Then get the never-expiring Page token from the long-lived user token
    pages = await get_page_tokens(long_lived)
    return {
        "long_lived_user_token": long_lived,
        "expires_in": result.get("expires_in"),
        "pages": pages,
        "note": "Use the page access_token for SHANIA_PAGE_ACCESS_TOKEN secret",
    }


async def get_page_tokens(user_access_token: str) -> List[Dict[str, Any]]:
    """
    Fetch Page access tokens for all Pages the user manages.
    Each Page token is long-lived when derived from a long-lived user token.
    """
    result = await graph_get(
        "me/accounts",
        params={"fields": "id,name,access_token,tasks"},
        access_token=user_access_token,
    )
    pages = []
    for page in result.get("data", []):
        pages.append({
            "page_id": page["id"],
            "page_name": page.get("name", ""),
            "access_token": page["access_token"],
            "permissions": page.get("tasks", []),
        })
    return pages


async def get_page_token(user_access_token: str, page_id: Optional[str] = None) -> Dict[str, Any]:
    """Get token for a specific Page (defaults to wihy brand page)."""
    pid = page_id or BRAND_PAGE_IDS["wihy"]
    if not pid:
        raise MetaAPIError("No page_id provided and no default brand page set", status_code=400)

    result = await graph_get(
        f"{pid}",
        params={"fields": "id,name,access_token"},
        access_token=user_access_token,
    )
    return {
        "page_id": result["id"],
        "page_name": result.get("name", ""),
        "access_token": result["access_token"],
        "permissions": [],
    }


async def debug_token(token: str) -> Dict[str, Any]:
    """Inspect a token's metadata (scopes, expiry, app_id, etc.)."""
    if not META_APP_ID or not META_APP_SECRET:
        raise MetaAPIError("App credentials not configured", status_code=500)

    app_token = f"{META_APP_ID}|{META_APP_SECRET}"
    result = await graph_get(
        "debug_token",
        params={"input_token": token},
        access_token=app_token,
    )
    return result.get("data", {})


async def get_ad_accounts(user_access_token: str) -> List[Dict[str, Any]]:
    """Fetch all ad accounts the user has access to."""
    result = await graph_get(
        "me/adaccounts",
        params={"fields": "id,name,account_status,currency,timezone_name,business"},
        access_token=user_access_token,
    )
    accounts = []
    for acct in result.get("data", []):
        accounts.append({
            "ad_account_id": acct["id"],
            "name": acct.get("name", ""),
            "account_status": acct.get("account_status"),
            "currency": acct.get("currency"),
            "timezone": acct.get("timezone_name"),
            "business": acct.get("business"),
        })
    return accounts


async def get_businesses(user_access_token: str) -> List[Dict[str, Any]]:
    """Fetch all businesses the user is an admin/employee of."""
    result = await graph_get(
        "me/businesses",
        params={"fields": "id,name,verification_status,created_time"},
        access_token=user_access_token,
    )
    businesses = []
    for biz in result.get("data", []):
        businesses.append({
            "business_id": biz["id"],
            "name": biz.get("name", ""),
            "verification_status": biz.get("verification_status"),
            "created_time": biz.get("created_time"),
        })
    return businesses
