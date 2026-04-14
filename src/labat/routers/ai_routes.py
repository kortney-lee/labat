"""
labat/routers/ai_routes.py — Gemini-powered AI endpoints for LABAT.

Exposes the intelligence layer (campaign analysis, audience targeting,
budget optimization) and content generation (ad copy, posts, outreach,
replies, content calendars).

All endpoints require X-Admin-Token authentication.
"""

from __future__ import annotations

import logging
import time
import os
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.labat.auth import require_admin
from src.labat.schemas import (
    GenerateAdCopyRequest,
    GeneratePostsRequest,
    GenerateOutreachRequest,
    GenerateReplyRequest,
    ContentCalendarRequest,
    AnalyzeCampaignsRequest,
    AudienceRecommendationRequest,
    OptimizeCreativesRequest,
    OptimizeBudgetRequest,
    DigestRequest,
)
from src.labat.brands import normalize_brand, BRAND_PAGE_IDS

logger = logging.getLogger("labat.ai_routes")

router = APIRouter(
    prefix="/api/labat/ai",
    tags=["AI Intelligence"],
    dependencies=[Depends(require_admin)],
)

BRAND_ENFORCEMENT_MODE = os.getenv("BRAND_ENFORCEMENT_MODE", "warn").strip().lower()
LABAT_BRAND_SCOPE = (os.getenv("LABAT_BRAND_SCOPE", "") or "").strip().lower() or None


def _is_enforce_mode() -> bool:
    return BRAND_ENFORCEMENT_MODE == "enforce"


def _resolve_product_brand(raw_product: str, endpoint: str) -> str:
    scoped = None if LABAT_BRAND_SCOPE in (None, "", "all") else LABAT_BRAND_SCOPE
    normalized = normalize_brand(raw_product, default="")

    if not normalized or normalized not in BRAND_PAGE_IDS:
        if _is_enforce_mode():
            raise HTTPException(status_code=400, detail=f"Unknown brand/product '{raw_product}'")
        fallback = scoped or "wihy"
        logger.warning("Unknown product '%s' on %s; using %s in %s mode", raw_product, endpoint, fallback, BRAND_ENFORCEMENT_MODE)
        return fallback

    if scoped and normalized != scoped:
        if _is_enforce_mode():
            raise HTTPException(status_code=403, detail=f"Brand '{normalized}' is not allowed for LABAT scope '{scoped}'")
        logger.warning("Cross-scope product '%s' on %s; forcing %s in %s mode", normalized, endpoint, scoped, BRAND_ENFORCEMENT_MODE)
        return scoped

    return normalized


def _timed_response(data: Any, start: float) -> Dict[str, Any]:
    elapsed_ms = int((time.time() - start) * 1000)
    if isinstance(data, dict):
        data["processing_time_ms"] = elapsed_ms
        return data
    return {"result": data, "processing_time_ms": elapsed_ms}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Content Generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/generate/ad-copy", summary="Generate ad copy variants")
async def generate_ad_copy(req: GenerateAdCopyRequest):
    """Generate multiple ad copy variants for Meta Ads A/B testing."""
    from src.labat.services.content_service import generate_ad_copy as gen

    t0 = time.time()
    product = _resolve_product_brand(req.product, "/api/labat/ai/generate/ad-copy")
    result = await gen(
        product_description=req.product_description,
        target_audience=req.target_audience,
        campaign_goal=req.campaign_goal,
        num_variants=req.num_variants,
        tone=req.tone,
        product=product,
        funnel_stage=req.funnel_stage,
    )
    return _timed_response(result, t0)


@router.post("/generate/posts", summary="Generate social media posts")
async def generate_posts(req: GeneratePostsRequest):
    """Generate engaging social media posts for a given topic."""
    from src.labat.services.content_service import generate_posts as gen

    t0 = time.time()
    product = _resolve_product_brand(req.product, "/api/labat/ai/generate/posts")
    result = await gen(
        topic=req.topic,
        platform=req.platform,
        num_posts=req.num_posts,
        content_pillar=req.content_pillar,
        product=product,
        funnel_stage=req.funnel_stage,
    )
    return _timed_response(result, t0)


@router.post("/generate/outreach", summary="Generate outreach messaging")
async def generate_outreach(req: GenerateOutreachRequest):
    """Generate personalized outreach messages for different audiences."""
    from src.labat.services.content_service import generate_outreach as gen

    t0 = time.time()
    result = await gen(
        recipient_type=req.recipient_type,
        context=req.context,
        goal=req.goal,
        num_variants=req.num_variants,
    )
    return _timed_response(result, t0)


@router.post("/generate/reply", summary="Generate comment reply")
async def generate_reply(req: GenerateReplyRequest):
    """Generate a contextual reply to a social media comment."""
    from src.labat.services.content_service import generate_reply as gen

    t0 = time.time()
    reply = await gen(
        comment_text=req.comment_text,
        post_context=req.post_context,
        sentiment=req.sentiment,
    )
    return {"reply": reply, "processing_time_ms": int((time.time() - t0) * 1000)}


@router.post("/generate/calendar", summary="Generate content calendar")
async def generate_calendar(req: ContentCalendarRequest):
    """Generate a content calendar for social media planning."""
    from src.labat.services.content_service import generate_content_calendar as gen

    t0 = time.time()
    result = await gen(
        weeks=req.weeks,
        focus_areas=req.focus_areas,
        existing_content=req.existing_content,
    )
    return _timed_response(result, t0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Intelligence & Optimization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/analyze/campaigns", summary="Analyze campaign performance")
async def analyze_campaigns(req: AnalyzeCampaignsRequest):
    """Feed campaign insights data to Gemini for analysis and optimization recs."""
    from src.labat.services.intelligence_service import analyze_campaigns as analyze

    t0 = time.time()
    product = _resolve_product_brand(req.product, "/api/labat/ai/analyze/campaigns")
    result = await analyze(
        insights_data=req.insights_data,
        product=product,
        funnel_stage=req.funnel_stage,
    )
    return _timed_response(result, t0)


@router.post("/analyze/audiences", summary="Recommend audience segments")
async def recommend_audiences(req: AudienceRecommendationRequest):
    """Get AI-powered audience targeting recommendations."""
    from src.labat.services.intelligence_service import recommend_audiences as rec

    t0 = time.time()
    product = _resolve_product_brand(req.product, "/api/labat/ai/analyze/audiences")
    result = await rec(
        campaign_context=req.campaign_context,
        performance_data=req.performance_data,
        product=product,
        funnel_stage=req.funnel_stage,
    )
    return _timed_response(result, t0)


@router.post("/analyze/creatives", summary="Optimize ad creatives")
async def optimize_creatives(req: OptimizeCreativesRequest):
    """Analyze creative performance and get optimization recommendations."""
    from src.labat.services.intelligence_service import optimize_creatives as opt

    t0 = time.time()
    product = _resolve_product_brand(req.product, "/api/labat/ai/analyze/creatives")
    result = await opt(
        creative_performance=req.creative_performance,
        product=product,
        funnel_stage=req.funnel_stage,
    )
    return _timed_response(result, t0)


@router.post("/analyze/budget", summary="Optimize budget allocation")
async def optimize_budget(req: OptimizeBudgetRequest):
    """Get AI-powered budget allocation recommendations."""
    from src.labat.services.intelligence_service import optimize_budget as opt

    t0 = time.time()
    product = _resolve_product_brand(req.product, "/api/labat/ai/analyze/budget")
    result = await opt(
        performance_data=req.performance_data,
        total_daily_budget=req.total_daily_budget,
        product=product,
        funnel_stage=req.funnel_stage,
    )
    return _timed_response(result, t0)


@router.post("/analyze/digest", summary="Generate performance digest")
async def generate_digest(req: DigestRequest):
    """Generate an executive performance digest in natural language."""
    from src.labat.services.intelligence_service import generate_digest as gen

    t0 = time.time()
    digest = await gen(
        performance_data=req.performance_data,
        period=req.period,
    )
    return {"digest": digest, "period": req.period,
            "processing_time_ms": int((time.time() - t0) * 1000)}
