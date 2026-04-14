"""
labat/services/linkedin_posting_service.py — Post, schedule, and manage LinkedIn content.

Used by Shania to post company/organizational updates to LinkedIn.
Handles:
- Creating text posts
- Scheduling posts for future publish
- Editing post text
- Deleting posts
- Fetching post metadata
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from src.labat.config import LINKEDIN_ORG_ID
from src.labat.linkedin_client import (
    linkedin_post,
    linkedin_patch,
    linkedin_delete,
    linkedin_get,
    LinkedInAPIError,
)

logger = logging.getLogger("labat.linkedin_posting_service")


def _get_actor() -> str:
    """Return the organization actor URN."""
    if not LINKEDIN_ORG_ID:
        raise LinkedInAPIError("LINKEDIN_ORG_ID not configured", status_code=500)
    if LINKEDIN_ORG_ID.startswith("urn:li:"):
        return LINKEDIN_ORG_ID
    return f"urn:li:organization:{LINKEDIN_ORG_ID}"


async def create_post(
    message: str,
    scheduled_publish_time: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a LinkedIn post.

    If scheduled_publish_time is provided, the post will be scheduled for that Unix timestamp.
    Otherwise, publishes immediately.

    Returns the post URN and ID.
    """
    actor = _get_actor()

    # Build the post payload
    payload: Dict[str, Any] = {
        "actor": actor,
        "content": {
            "media": []
        },
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetAudiences": []
        },
        "text": {
            "text": message
        }
    }

    # If scheduled, add lifecycleState
    if scheduled_publish_time:
        payload["lifecycleState"] = "DRAFT"
        # LinkedIn expects publishedAt in the payload
        payload["publishedAt"] = scheduled_publish_time * 1000  # Convert to milliseconds

    # LinkedIn endpoint for creating posts
    result = await linkedin_post(
        "posts",
        json_data=payload,
    )

    post_id = result.get("id")
    post_urn = result.get("id")

    logger.info(
        f"Created LinkedIn post {'(scheduled)' if scheduled_publish_time else '(published)'}: {post_id}"
    )

    return {
        "id": post_id,
        "urn": post_urn,
        "message_preview": message[:100],
        "scheduled": bool(scheduled_publish_time),
        "scheduled_time": scheduled_publish_time,
    }


async def schedule_post(
    message: str,
    publish_at: Optional[datetime] = None,
    hours_from_now: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Schedule a LinkedIn post for future publishing.

    Either provide publish_at (datetime) or hours_from_now (int).
    """
    if not publish_at and not hours_from_now:
        raise ValueError("Must provide either publish_at or hours_from_now")

    if hours_from_now:
        publish_at = datetime.utcnow() + timedelta(hours=hours_from_now)

    # Convert to Unix timestamp
    timestamp = int(publish_at.timestamp())

    return await create_post(message, scheduled_publish_time=timestamp)


async def update_post(post_id: str, message: str) -> Dict[str, Any]:
    """
    Update the text of an existing LinkedIn post.

    Note: LinkedIn API only allows editing text; not all fields can be modified.
    """
    payload = {
        "text": {
            "text": message
        }
    }

    try:
        result = await linkedin_patch(f"posts/{post_id}", json_data=payload)
        logger.info(f"Updated LinkedIn post: {post_id}")
        return result
    except LinkedInAPIError as e:
        logger.error(f"Failed to update post {post_id}: {e}")
        raise


async def delete_post(post_id: str) -> Dict[str, Any]:
    """Delete a LinkedIn post."""
    try:
        result = await linkedin_delete(f"posts/{post_id}")
        logger.info(f"Deleted LinkedIn post: {post_id}")
        return result
    except LinkedInAPIError as e:
        logger.error(f"Failed to delete post {post_id}: {e}")
        raise


async def get_post(post_id: str) -> Dict[str, Any]:
    """Fetch metadata and details for a LinkedIn post."""
    payload = {
        "ids": [post_id],
        "fields": [
            "id",
            "actor",
            "text",
            "createdAt",
            "lifecycleState",
            "visibility",
        ]
    }

    try:
        result = await linkedin_get(
            f"posts/{post_id}",
            params=payload,
        )
        logger.info(f"Fetched LinkedIn post: {post_id}")
        return result
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch post {post_id}: {e}")
        raise


async def list_posts(
    limit: int = 20,
    start: int = 0,
) -> Dict[str, Any]:
    """List recent posts from the organization."""
    actor = _get_actor()

    payload = {
        "creator": actor,
        "q": "posts",
        "count": limit,
        "start": start,
        "fields": [
            "id",
            "actor",
            "text",
            "createdAt",
            "lifecycleState",
            "visibility",
        ]
    }

    try:
        result = await linkedin_get("posts", params=payload)
        logger.info(f"Listed {len(result.get('elements', []))} LinkedIn posts")
        return result
    except LinkedInAPIError as e:
        logger.error(f"Failed to list posts: {e}")
        raise


async def get_post_stats(post_id: str) -> Dict[str, Any]:
    """
    Fetch engagement stats for a post.

    Returns impressions, clicks, comments, shares, likes.
    """
    payload = {
        "ids": [post_id],
        "fields": [
            "id",
            "impressionCount",
            "clickCount",
            "commentCount",
            "shareCount",
            "likeCount",
            "engagement",
        ]
    }

    try:
        result = await linkedin_get(f"posts/{post_id}/stats", params=payload)
        logger.info(f"Fetched stats for LinkedIn post: {post_id}")
        return result
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch post stats {post_id}: {e}")
        raise
