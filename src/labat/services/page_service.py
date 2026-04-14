"""
labat/services/page_service.py — Facebook Page read operations.

Fetch Page info, feed, and individual post details.
Write operations (create/update/delete posts) are in post_service.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import os

from src.labat.brands import BRAND_PAGE_IDS
from src.labat.meta_client import graph_get, MetaAPIError
from src.labat.services.token_service import get_shania_page_access_token

_BRAND_SCOPE = os.getenv("SHANIA_BRAND_SCOPE", "").strip().lower() or None


def _default_page_id() -> str:
    if _BRAND_SCOPE:
        return BRAND_PAGE_IDS.get(_BRAND_SCOPE, BRAND_PAGE_IDS["wihy"])
    return BRAND_PAGE_IDS["wihy"]


async def _shania(page_id: Optional[str] = None) -> str:
    """Resolve the correct Shania token for the requested page."""
    return await get_shania_page_access_token(page_id)

logger = logging.getLogger("labat.page_service")


async def get_page_info(page_id: Optional[str] = None) -> Dict[str, Any]:
    """Return basic Page metadata (name, category, fan_count, etc.)."""
    pid = page_id or _default_page_id()
    if not pid:
        raise MetaAPIError("No page_id configured", status_code=400)

    return await graph_get(
        pid,
        params={
            "fields": "id,name,category,fan_count,followers_count,link,about,picture"
        },
        access_token=await _shania(pid),
    )


async def get_page_feed(
    page_id: Optional[str] = None,
    limit: int = 25,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch the Page's published post feed."""
    pid = page_id or _default_page_id()
    if not pid:
        raise MetaAPIError("No page_id configured", status_code=400)

    params: Dict[str, Any] = {
        "fields": "id,message,created_time,permalink_url,is_published",
        "limit": min(limit, 100),
    }
    if after:
        params["after"] = after

    # Use published_posts (not /feed) — /feed requires Advanced Access for
    # New Pages Experience; published_posts works with Standard Access.
    return await graph_get(f"{pid}/published_posts", params=params, access_token=await _shania(pid))


async def get_post_detail(post_id: str) -> Dict[str, Any]:
    """Get full details for a single post."""
    return await graph_get(
        post_id,
        params={
            "fields": "id,message,created_time,permalink_url,is_published,"
                      "shares,type,attachments{media_type,url,title}"
        },
        access_token=await _shania(),
    )
