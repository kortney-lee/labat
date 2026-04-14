"""
labat/services/comment_service.py — Read and reply to comments on Page posts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.labat.config import SHANIA_PAGE_ACCESS_TOKEN
from src.labat.meta_client import graph_get, graph_post, graph_delete, MetaAPIError


def _shania() -> str:
    """Shania page token — manages comment engagement."""
    if not SHANIA_PAGE_ACCESS_TOKEN:
        raise MetaAPIError("SHANIA_PAGE_ACCESS_TOKEN not configured", status_code=500)
    return SHANIA_PAGE_ACCESS_TOKEN

logger = logging.getLogger("labat.comment_service")


async def get_comments(
    object_id: str,
    limit: int = 50,
    after: Optional[str] = None,
    order: str = "reverse_chronological",
) -> Dict[str, Any]:
    """
    Fetch comments on a post (or a comment's replies).
    object_id: post ID or comment ID.
    """
    params: Dict[str, Any] = {
        "fields": "id,message,from{id,name},created_time,can_reply_privately,comment_count",
        "limit": min(limit, 100),
        "order": order,
    }
    if after:
        params["after"] = after

    return await graph_get(f"{object_id}/comments", params=params, access_token=_shania())


async def reply_to_comment(comment_id: str, message: str) -> Dict[str, Any]:
    """Post a public reply to a comment (as the Page)."""
    result = await graph_post(f"{comment_id}/comments", data={"message": message}, access_token=_shania())
    logger.info("Replied to comment %s → %s", comment_id, result.get("id"))
    return result


async def create_comment(post_id: str, message: str) -> Dict[str, Any]:
    """Post a top-level comment on a Page post (as the Page)."""
    result = await graph_post(f"{post_id}/comments", data={"message": message}, access_token=_shania())
    logger.info("Commented on post %s → %s", post_id, result.get("id"))
    return result


async def delete_comment(comment_id: str) -> Dict[str, Any]:
    """Delete a comment the Page owns."""
    result = await graph_delete(comment_id, access_token=_shania())
    logger.info("Deleted comment %s", comment_id)
    return result


async def hide_comment(comment_id: str, is_hidden: bool = True) -> Dict[str, Any]:
    """Hide or unhide a comment (moderation)."""
    result = await graph_post(comment_id, data={"is_hidden": str(is_hidden).lower()}, access_token=_shania())
    logger.info("Set comment %s hidden=%s", comment_id, is_hidden)
    return result
