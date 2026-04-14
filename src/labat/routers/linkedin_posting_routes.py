"""
labat/routers/linkedin_posting_routes.py — LinkedIn content posting endpoints (Shania).

Routes:
  POST   /api/engagement/linkedin/posts         — Create or schedule a post
  PATCH  /api/engagement/linkedin/posts/:id    — Update post text
  DELETE /api/engagement/linkedin/posts/:id    — Delete a post
  GET    /api/engagement/linkedin/posts/:id    — Get post metadata
  GET    /api/engagement/linkedin/posts        — List recent posts
"""

from __future__ import annotations

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Body
from pydantic import BaseModel, Field

from src.shared.auth.auth_client import verify_token
from src.labat.services.linkedin_posting_service import (
    create_post,
    schedule_post,
    update_post,
    delete_post,
    get_post,
    list_posts,
    get_post_stats,
)
from src.labat.linkedin_client import LinkedInAPIError

logger = logging.getLogger("labat.linkedin_posting_routes")

router = APIRouter(prefix="/api/engagement/linkedin", tags=["LinkedIn"])


# ── Request/Response Models ──────────────────────────────────────────────────

class PostCreateRequest(BaseModel):
    """Create or schedule a LinkedIn post."""
    message: str = Field(..., min_length=1, max_length=3000, description="Post content")
    schedule_hours_from_now: Optional[int] = Field(
        None, ge=1, le=8760, description="Hours from now to schedule (optional)"
    )


class PostUpdateRequest(BaseModel):
    """Update an existing post."""
    message: str = Field(..., min_length=1, max_length=3000, description="New post content")


class PostResponse(BaseModel):
    """Response for post creation/update."""
    id: str
    message_preview: str
    scheduled: bool
    scheduled_time: Optional[int] = None


class PostMetadata(BaseModel):
    """Post metadata."""
    id: str
    text: Optional[str] = None
    created_at: Optional[int] = None
    lifecycle_state: Optional[str] = None


class PostStatsResponse(BaseModel):
    """Post engagement stats."""
    id: str
    impressions: int = 0
    clicks: int = 0
    comments: int = 0
    shares: int = 0
    likes: int = 0
    total_engagement: int = 0


# ── Helper: Verify Admin Token ───────────────────────────────────────────────

async def require_admin_token(x_admin_token: str = Header(None)) -> str:
    """Verify X-Admin-Token header."""
    from src.labat.config import INTERNAL_ADMIN_TOKEN

    token = x_admin_token or ""
    if not token or not INTERNAL_ADMIN_TOKEN or token != INTERNAL_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Token")
    return token


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/posts", response_model=PostResponse, summary="Create or schedule a LinkedIn post")
async def create_or_schedule_post(
    req: PostCreateRequest,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> PostResponse:
    """
    Create and immediately publish a LinkedIn post, or schedule it for later.

    If `schedule_hours_from_now` is provided, the post will be scheduled.
    Otherwise, it's published immediately.
    """
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        if req.schedule_hours_from_now:
            result = await schedule_post(
                req.message,
                hours_from_now=req.schedule_hours_from_now,
            )
        else:
            result = await create_post(req.message)

        return PostResponse(**result)
    except LinkedInAPIError as e:
        logger.error(f"Failed to create post: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating post: {e}")
        raise HTTPException(status_code=500, detail="Failed to create post")


@router.patch("/posts/{post_id}", response_model=PostResponse, summary="Update post text")
async def update_linkedin_post(
    post_id: str,
    req: PostUpdateRequest,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> PostResponse:
    """Update the text content of an existing LinkedIn post."""
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await update_post(post_id, req.message)
        return PostResponse(
            id=post_id,
            message_preview=req.message[:100],
            scheduled=False,
        )
    except LinkedInAPIError as e:
        logger.error(f"Failed to update post: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating post: {e}")
        raise HTTPException(status_code=500, detail="Failed to update post")


@router.delete("/posts/{post_id}", summary="Delete a LinkedIn post")
async def delete_linkedin_post(
    post_id: str,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> dict:
    """Delete a LinkedIn post."""
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        await delete_post(post_id)
        return {"id": post_id, "deleted": True}
    except LinkedInAPIError as e:
        logger.error(f"Failed to delete post: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error deleting post: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete post")


@router.get("/posts/{post_id}", response_model=PostMetadata, summary="Get post metadata")
async def get_linkedin_post(
    post_id: str,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> PostMetadata:
    """Fetch metadata for a specific LinkedIn post."""
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await get_post(post_id)
        return PostMetadata(
            id=post_id,
            text=result.get("text"),
            created_at=result.get("createdAt"),
            lifecycle_state=result.get("lifecycleState"),
        )
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch post: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.get("/posts", summary="List recent posts")
async def list_linkedin_posts(
    limit: int = 20,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> dict:
    """List recent LinkedIn posts."""
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await list_posts(limit=limit)
        return {
            "posts": result.get("elements", []),
            "total": len(result.get("elements", [])),
        }
    except LinkedInAPIError as e:
        logger.error(f"Failed to list posts: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))


@router.get("/posts/{post_id}/stats", response_model=PostStatsResponse, summary="Get post engagement stats")
async def get_linkedin_post_stats(
    post_id: str,
    admin_token: str = Header(None, alias="X-Admin-Token"),
) -> PostStatsResponse:
    """Get engagement stats for a LinkedIn post."""
    try:
        await require_admin_token(admin_token)
    except HTTPException:
        raise

    try:
        result = await get_post_stats(post_id)
        return PostStatsResponse(
            id=post_id,
            impressions=result.get("impressionCount", 0),
            clicks=result.get("clickCount", 0),
            comments=result.get("commentCount", 0),
            shares=result.get("shareCount", 0),
            likes=result.get("likeCount", 0),
            total_engagement=result.get("engagement", 0),
        )
    except LinkedInAPIError as e:
        logger.error(f"Failed to fetch post stats: {e}")
        raise HTTPException(status_code=e.status_code or 500, detail=str(e))
