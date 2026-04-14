"""
labat/services/linkedin_analytics_service.py — LinkedIn engagement and performance analytics.

Used by LABAT to report on:
- Post impressions, clicks, engagement
- Follower growth
- Engagement rates by post and over time
- Company page analytics
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from src.labat.config import LINKEDIN_ORG_ID
from src.labat.linkedin_client import (
    linkedin_get,
    LinkedInAPIError,
)

logger = logging.getLogger("labat.linkedin_analytics_service")


def _get_actor() -> str:
    """Return the organization actor URN."""
    if not LINKEDIN_ORG_ID:
        raise LinkedInAPIError("LINKEDIN_ORG_ID not configured", status_code=500)
    if LINKEDIN_ORG_ID.startswith("urn:li:"):
        return LINKEDIN_ORG_ID
    return f"urn:li:organization:{LINKEDIN_ORG_ID}"


async def get_organization_insights() -> Dict[str, Any]:
    """
    Fetch high-level organization/page insights.

    Returns follower count, engagement metrics, etc.
    """
    org_id = LINKEDIN_ORG_ID
    if not org_id:
        raise LinkedInAPIError("LinkedIn organization reporting requires LINKEDIN_ORG_ID", status_code=400)

    # Strip URN prefix if present
    if org_id.startswith("urn:li:organization:"):
        org_id = org_id.replace("urn:li:organization:", "")

    payload = {
        "q": "organization",
        "organizationIds": [f"urn:li:organization:{org_id}"],
        "fields": [
            "organizationName",
            "foundedYear",
            "description",
            "companySize",
            "industry",
            "specialties",
            "followerCount",
            "universalName",
            "websiteUrl",
        ]
    }

    try:
        result = await linkedin_get("organizations", params=payload)
        logger.info(f"Fetched organization insights")
        return result
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch organization insights: {e}")
        raise


async def get_post_analytics(
    post_id: str,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Get analytics for a single post.

    Available fields:
    - impressionCount
    - clickCount
    - commentCount
    - shareCount
    - likeCount
    - engagement
    """
    default_fields = [
        "id",
        "impressionCount",
        "clickCount",
        "commentCount",
        "shareCount",
        "likeCount",
        "engagement",
    ]
    selected_fields = fields or default_fields

    payload = {
        "ids": [post_id],
        "fields": selected_fields,
    }

    try:
        result = await linkedin_get(f"posts/{post_id}/stats", params=payload)
        logger.info(f"Fetched analytics for post {post_id}")
        return result
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch post analytics {post_id}: {e}")
        raise


async def get_posts_with_stats(
    limit: int = 20,
    fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Fetch the latest posts with engagement stats.

    Returns posts including impressions, clicks, comments, shares, likes.
    """
    actor = _get_actor()
    default_fields = [
        "id",
        "actor",
        "text",
        "createdAt",
        "impressionCount",
        "clickCount",
        "commentCount",
        "shareCount",
        "likeCount",
        "engagement",
    ]
    selected_fields = fields or default_fields

    payload = {
        "creator": actor,
        "q": "statistics",
        "count": limit,
        "fields": selected_fields,
    }

    try:
        result = await linkedin_get("posts", params=payload)
        posts = result.get("elements", [])
        logger.info(f"Fetched {len(posts)} posts with stats")

        # Calculate aggregate engagement
        total_impressions = sum(p.get("impressionCount", 0) for p in posts)
        total_clicks = sum(p.get("clickCount", 0) for p in posts)
        total_engagement = total_clicks + sum(p.get("commentCount", 0) + p.get("shareCount", 0) + p.get("likeCount", 0) for p in posts)

        return {
            "posts": posts,
            "summary": {
                "total_posts": len(posts),
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_engagement": total_engagement,
                "avg_impressions_per_post": total_impressions // len(posts) if posts else 0,
                "avg_engagement_rate": (total_engagement / total_impressions * 100) if total_impressions else 0,
            }
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch posts with stats: {e}")
        raise


async def get_engagement_trend(
    days: int = 7,
) -> Dict[str, Any]:
    """
    Get engagement metrics over the past N days.

    Returns daily breakdown of impressions, clicks, engagement.
    """
    # LinkedIn's reporting API has limited time-series granularity.
    # This uses the posts list to calculate trends.

    try:
        result = await get_posts_with_stats(limit=100)
        posts = result.get("posts", [])

        # Group posts by day
        daily_stats = {}
        for post in posts:
            created_time = post.get("createdAt", 0)
            if created_time:
                # Convert milliseconds to datetime
                dt = datetime.fromtimestamp(created_time / 1000)
                day = dt.strftime("%Y-%m-%d")

                if day not in daily_stats:
                    daily_stats[day] = {
                        "impressions": 0,
                        "clicks": 0,
                        "comments": 0,
                        "shares": 0,
                        "likes": 0,
                    }

                daily_stats[day]["impressions"] += post.get("impressionCount", 0)
                daily_stats[day]["clicks"] += post.get("clickCount", 0)
                daily_stats[day]["comments"] += post.get("commentCount", 0)
                daily_stats[day]["shares"] += post.get("shareCount", 0)
                daily_stats[day]["likes"] += post.get("likeCount", 0)

        logger.info(f"Calculated engagement trend for {len(daily_stats)} days")
        return {
            "days": days,
            "daily_stats": daily_stats,
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch engagement trend: {e}")
        raise


async def get_follower_count() -> Dict[str, Any]:
    """Get current follower/subscriber count for the organization."""
    try:
        result = await get_organization_insights()
        elements = result.get("elements", [{}])
        follower_count = elements[0].get("followerCount", 0)

        logger.info(f"Current follower count: {follower_count}")
        return {
            "follower_count": follower_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch follower count: {e}")
        raise
