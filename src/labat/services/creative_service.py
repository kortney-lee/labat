"""
labat/services/creative_service.py — Ad creative CRUD via Marketing API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.labat.config import META_AD_ACCOUNT_ID, META_SYSTEM_USER_TOKEN
from src.labat.meta_client import graph_get, graph_post, graph_delete, MetaAPIError

logger = logging.getLogger("labat.creative_service")


def _acct() -> str:
    if not META_AD_ACCOUNT_ID:
        raise MetaAPIError("META_AD_ACCOUNT_ID not configured", status_code=500)
    return META_AD_ACCOUNT_ID


def _token() -> str:
    if not META_SYSTEM_USER_TOKEN:
        raise MetaAPIError("META_SYSTEM_USER_TOKEN not configured", status_code=500)
    return META_SYSTEM_USER_TOKEN


async def create_creative(
    name: str,
    object_story_spec: Optional[Dict[str, Any]] = None,
    url_tags: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an ad creative under the ad account."""
    import json

    data: Dict[str, Any] = {"name": name}
    if object_story_spec:
        data["object_story_spec"] = json.dumps(object_story_spec)
    if url_tags:
        data["url_tags"] = url_tags

    result = await graph_post(
        f"{_acct()}/adcreatives", data=data, access_token=_token()
    )
    logger.info("Created creative %s: %s", result.get("id"), name)
    return result


async def get_creative(creative_id: str) -> Dict[str, Any]:
    return await graph_get(
        creative_id,
        params={
            "fields": "id,name,status,object_story_spec,url_tags,thumbnail_url"
        },
        access_token=_token(),
    )


async def list_creatives(limit: int = 50) -> Dict[str, Any]:
    return await graph_get(
        f"{_acct()}/adcreatives",
        params={
            "fields": "id,name,status,thumbnail_url",
            "limit": min(limit, 200),
        },
        access_token=_token(),
    )


async def delete_creative(creative_id: str) -> Dict[str, Any]:
    return await graph_delete(creative_id, access_token=_token())
