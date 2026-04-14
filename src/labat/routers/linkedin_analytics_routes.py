"""
labat/routers/linkedin_analytics_routes.py — LinkedIn analytics and reporting (LABAT).

Routes:
  GET /api/labat/linkedin/insights         — Organization insights
  GET /api/labat/linkedin/posts/stats      — Posts with engagement stats
  GET /api/labat/linkedin/posts/:id/stats  — Stats for a single post
  GET /api/labat/linkedin/trends           — Engagement trends
  GET /api/labat/linkedin/followers        — Follower count
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from src.labat.services.linkedin_analytics_service import (
    get_organization_insights,
    get_posts_with_stats,
    get_post_analytics,
    get_engagement_trend,
    get_follower_count,
)
from src.labat.linkedin_client import LinkedInAPIError

logger = logging.getLogger("labat.linkedin_analytics_routes")

router = APIRouter(prefix="/api/labat/linkedin", tags=["LinkedIn Analytics"])


# ── Helper: Verify Admin Token ───────────────────────────────────────────────

async def require_admin_token(x_admin_token: str = Header(None)) -> str:
    """Verify X-Admin-Token header."""
    from src.labat.config import INTERNAL_ADMIN_TOKEN

    token = x_admin_token or ""
    if not token or not INTERNAL_ADMIN_TOKEN or token != INTERNAL_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Token")
    return token


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/insights", summary="Get organization insights")
async def get_org_insights(
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> dict:
    """
    Get high-level LinkedIn organization insights.

    Returns follower count, company info, specialties.
    """
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await get_organization_insights()
        elements = result.get("elements", [])
        if not elements:
            raise HTTPException(status_code=404, detail="Organization not found")

        org = elements[0]
        return {
            "organization_name": org.get("organizationName"),
            "founded_year": org.get("foundedYear"),
            "description": org.get("description"),
            "company_size": org.get("companySize"),
            "industry": org.get("industry"),
            "follower_count": org.get("followerCount", 0),
            "website_url": org.get("websiteUrl"),
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to get org insights: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting org insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to get organization insights")


@router.get("/posts/stats", summary="Get posts with engagement stats")
async def get_posts_analytics(
    limit: int = 20,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> dict:
    """
    Get recent posts with engagement stats.

    Returns:
    - posts: Array of posts with impressions, clicks, comments, shares, likes
    - summary: Aggregate metrics (total impressions, clicks, engagement rate)
    """
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await get_posts_with_stats(limit=limit)
        posts = result.get("posts", [])
        summary = result.get("summary", {})

        return {
            "posts_count": len(posts),
            "posts": [
                {
                    "id": p.get("id"),
                    "text_preview": p.get("text", "")[:100] if p.get("text") else "",
                    "created_at": p.get("createdAt"),
                    "impressions": p.get("impressionCount", 0),
                    "clicks": p.get("clickCount", 0),
                    "comments": p.get("commentCount", 0),
                    "shares": p.get("shareCount", 0),
                    "likes": p.get("likeCount", 0),
                    "engagement": p.get("likeCount", 0) + p.get("commentCount", 0) + p.get("shareCount", 0),
                }
                for p in posts
            ],
            "summary": {
                "total_impressions": summary.get("total_impressions", 0),
                "total_clicks": summary.get("total_clicks", 0),
                "total_engagement": summary.get("total_engagement", 0),
                "avg_impressions_per_post": summary.get("avg_impressions_per_post", 0),
                "avg_engagement_rate": round(summary.get("avg_engagement_rate", 0), 2),
            }
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to get posts analytics: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting posts analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get posts analytics")


@router.get("/posts/{post_id}/stats", summary="Get single post stats")
async def get_post_analytics_endpoint(
    post_id: str,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> dict:
    """Get detailed engagement stats for a single LinkedIn post."""
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await get_post_analytics(post_id)
        return {
            "id": post_id,
            "impressions": result.get("impressionCount", 0),
            "clicks": result.get("clickCount", 0),
            "comments": result.get("commentCount", 0),
            "shares": result.get("shareCount", 0),
            "likes": result.get("likeCount", 0),
            "total_engagement": result.get("engagement", 0),
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to get post analytics: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.get("/trends", summary="Get engagement trends")
async def get_engagement_trends(
    days: int = 7,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> dict:
    """
    Get engagement trends over the past N days.

    Returns daily breakdown of impressions, clicks, comments, shares, likes.
    """
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    try:
        result = await get_engagement_trend(days=days)
        return {
            "period_days": result.get("days", days),
            "daily_stats": result.get("daily_stats", {}),
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to get engagement trends: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting trends: {e}")
        raise HTTPException(status_code=500, detail="Failed to get engagement trends")


@router.get("/followers", summary="Get follower count")
async def get_followers(
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> dict:
    """Get current follower/subscriber count for the LinkedIn organization."""
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await get_follower_count()
        return {
            "follower_count": result.get("follower_count", 0),
            "timestamp": result.get("timestamp"),
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to get follower count: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting follower count: {e}")
        raise HTTPException(status_code=500, detail="Failed to get follower count")
