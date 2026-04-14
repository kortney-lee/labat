"""
engagement_routes.py — Engagement API for the lead-service

The lead-service (auth.wihy.ai/services/lead-service) calls these endpoints
to engage discovered leads with WIHY-toned, RAG-grounded comments.

Authentication: X-Admin-Token header (same token as INTERNAL_ADMIN_TOKEN secret)

Endpoints:
  POST /api/engagement/engage     — generate + post a comment to a lead's post
  POST /api/engagement/engage/batch — engage multiple leads in one call
  GET  /api/engagement/preview    — generate comment text without posting (dry-run)
  GET  /api/engagement/health     — liveness check
"""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from src.maya.services.engagement_poster_service import engage_lead, thread_monitor
from src.maya.services.social_posting_service import social_posting_service

logger = logging.getLogger("engagement_routes")

ENGAGEMENT_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()

router = APIRouter(prefix="/api/engagement", tags=["engagement"])


# ── Auth ──────────────────────────────────────────────────────────────────────

def _require_admin(request: Request) -> None:
    token = (
        request.headers.get("X-Admin-Token")
        or request.headers.get("X-Client-Secret")
        or ""
    ).strip()
    if not ENGAGEMENT_ADMIN_TOKEN:
        logger.warning("INTERNAL_ADMIN_TOKEN not set — engagement routes are open (dev mode)")
        return
    if not token or token != ENGAGEMENT_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Request / Response schemas ────────────────────────────────────────────────

class EngageRequest(BaseModel):
    """
    Payload sent by the lead-service to engage a discovered lead.

    Field notes:
      platform:     One of "twitter", "instagram", "facebook", "tiktok", "generic"
      action:       "comment" = reply to a post; "reply" = reply to a comment under your post
      target_id:    Platform post/comment ID to reply to.
                    Twitter format: tweet ID string (e.g. "1234567890123456789")
                    Others: platform-native post ID (content returned for client to post)
      post_content: Original post/comment text — used to personalize the WIHY response
      topic:        Clean topic keyword for WIHY RAG query
                    Examples: "weight loss intermittent fasting", "gut health probiotics"
                    Tip: strip usernames, platform noise, keep health keywords
      lead_id:      UUID from lead-service leads table — passed through for tracking
      author:       Original poster's username/handle (optional, for logging)
      dry_run:      If true, generate and return comment text but do NOT post to platform
    """
    platform: str = Field(..., description="twitter | instagram | facebook | tiktok | generic")
    action: str = Field("comment", description="comment | reply")
    target_id: str = Field(..., description="Platform post/comment ID to reply to")
    post_content: str = Field("", description="Original post text (used to personalize response)")
    topic: str = Field(..., description="Clean health topic for WIHY RAG query")
    lead_id: Optional[str] = Field(None, description="Lead UUID from lead-service")
    author: Optional[str] = Field(None, description="Original poster username")
    conversation_tweet_id: Optional[str] = Field(None, description="Twitter conversation root tweet ID — enables thread monitoring")
    dry_run: bool = Field(False, description="Generate content without posting")


class EngageResponse(BaseModel):
    success: bool
    platform: str
    action: str
    content: str
    platform_post_id: Optional[str] = None
    lead_id: Optional[str] = None
    dry_run: bool = False
    error: Optional[str] = None


class BatchEngageRequest(BaseModel):
    leads: List[EngageRequest] = Field(..., description="Up to 10 leads per batch (enforced at runtime)")


class BatchEngageResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    results: List[EngageResponse]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/health")
async def engagement_health():
    """Liveness check — no auth required."""
    return {
        "status": "ok",
        "service": "wihy-shania",
        "agent": "shania",
        "monitor": thread_monitor.status(),
    }


@router.get("/monitor", dependencies=[Depends(_require_admin)])
async def engagement_monitor_status():
    """Return current thread monitor stats: tracked threads, auto-replies sent, last poll time."""
    return thread_monitor.status()


@router.get("/social-posting", dependencies=[Depends(_require_admin)])
async def social_posting_status():
    """Return social posting service status."""
    return social_posting_service.status()


@router.post("/trigger/social-posting", dependencies=[Depends(_require_admin)])
async def trigger_social_posting():
    """Manually trigger a social posting cycle."""
    result = await social_posting_service.run_once()
    return {"status": "ok", **result}


@router.post("/engage", response_model=EngageResponse)
async def engage_single(
    body: EngageRequest,
    request: Request,
    _auth=Depends(_require_admin),
):
    """
    Generate a WIHY-toned comment and post it to the lead's post.

    The lead-service calls this after scoring a lead ≥ 50.
    Pass `dry_run: true` to preview the generated comment without posting.
    """
    logger.info(
        f"Engage request: platform={body.platform} action={body.action} "
        f"lead={body.lead_id} topic={body.topic!r} dry_run={body.dry_run}"
    )
    result = await engage_lead(
        platform=body.platform,
        action=body.action,
        target_id=body.target_id,
        post_content=body.post_content,
        topic=body.topic,
        lead_id=body.lead_id,
        author=body.author,
        dry_run=body.dry_run,
        conversation_tweet_id=body.conversation_tweet_id,
    )
    return EngageResponse(**result)


@router.post("/engage/batch", response_model=BatchEngageResponse)
async def engage_batch(
    body: BatchEngageRequest,
    request: Request,
    _auth=Depends(_require_admin),
):
    """
    Engage up to 10 leads in a single call.
    Each lead is processed independently; partial failures are reported per-lead.

    The lead-service can call this after each GHL push cycle with the
    newly qualified leads that have a post URL to engage.
    """
    import asyncio
    if len(body.leads) > 10:
        raise HTTPException(status_code=422, detail="Maximum 10 leads per batch")

    async def _process(lead: EngageRequest) -> EngageResponse:
        try:
            result = await engage_lead(
                platform=lead.platform,
                action=lead.action,
                target_id=lead.target_id,
                post_content=lead.post_content,
                topic=lead.topic,
                lead_id=lead.lead_id,
                author=lead.author,
                dry_run=lead.dry_run,
                conversation_tweet_id=lead.conversation_tweet_id,
            )
            return EngageResponse(**result)
        except Exception as e:
            logger.error(f"Batch engage error for lead={lead.lead_id}: {e}")
            return EngageResponse(
                success=False,
                platform=lead.platform,
                action=lead.action,
                content="",
                lead_id=lead.lead_id,
                error=str(e),
            )

    results = await asyncio.gather(*[_process(lead) for lead in body.leads])
    succeeded = sum(1 for r in results if r.success)
    return BatchEngageResponse(
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=list(results),
    )


@router.get("/preview")
async def preview_comment(
    platform: str,
    topic: str,
    post_content: str = "",
    request: Request = None,
    _auth=Depends(_require_admin),
):
    """
    Preview the comment WIHY would generate for a given topic/platform/post.
    Does NOT post to the platform. Useful for QA from the lead-service dashboard.

    Query params:
      platform:     twitter | generic
      topic:        Health topic keyword
      post_content: Original post text (optional, improves personalization)
    """
    result = await engage_lead(
        platform=platform,
        action="comment",
        target_id="preview",
        post_content=post_content,
        topic=topic,
        dry_run=True,
    )
    return {
        "platform": platform,
        "topic": topic,
        "content": result.get("content", ""),
        "success": result.get("success", False),
        "error": result.get("error"),
    }
