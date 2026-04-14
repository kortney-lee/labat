"""
labat/routers/insights_routes.py — Ad + content insights endpoints.

POST /api/labat/insights                    — query ad insights (flexible)
GET  /api/labat/insights/summary            — account-level ad summary
GET  /api/labat/insights/campaign/:id       — single campaign insights
GET  /api/labat/insights/blog/performance   — blog performance snapshot
GET  /api/labat/insights/blog               — blog article listing
GET  /api/labat/insights/content            — content pipeline status
GET  /api/labat/insights/articles           — detailed article analytics
GET  /api/labat/insights/topics             — topic taxonomy with article counts
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.labat.auth import require_admin
from src.labat.schemas import InsightsRequest, InsightsResponse
from src.labat.services.insights_service import (
    get_insights,
    get_campaign_insights,
    get_account_summary,
)
from src.labat.services.content_insights_service import (
    get_blog_performance,
    get_blog_overview,
    get_content_insights,
    get_articles_insights,
    get_topic_taxonomy,
)
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.insights_routes")

router = APIRouter(prefix="/api/labat/insights", tags=["labat-insights"])


@router.post("", response_model=InsightsResponse)
async def query_insights(body: InsightsRequest, _=Depends(require_admin)):
    try:
        result = await get_insights(
            object_id=body.object_id,
            level=body.level,
            date_preset=body.date_preset,
            fields=body.fields,
            time_increment=body.time_increment,
            limit=body.limit,
        )
        return InsightsResponse(
            data=result.get("data", []),
            paging=result.get("paging"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/summary")
async def account_summary(
    date_preset: str = Query("last_30d"),
    _=Depends(require_admin),
):
    try:
        return await get_account_summary(date_preset=date_preset)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/campaign/{campaign_id}")
async def campaign_insights(
    campaign_id: str,
    date_preset: str = Query("last_7d"),
    _=Depends(require_admin),
):
    try:
        return await get_campaign_insights(campaign_id, date_preset=date_preset)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


# ── Content / Blog Insights ──────────────────────────────────────────────────


@router.get("/blog/performance")
async def blog_performance(
    brand: str = Query("wihy"),
    period: str = Query("30d"),
    _=Depends(require_admin),
):
    """Blog performance snapshot: article counts, word counts, queue status."""
    try:
        return await get_blog_performance(brand, period)
    except Exception as e:
        logger.error("blog/performance failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/blog")
async def blog_overview(
    brand: str = Query("wihy"),
    period: str = Query("30d"),
    page_type: Optional[str] = Query(None, description="Filter by page type: topic, comparison, alternative, guide, trending, meals"),
    _=Depends(require_admin),
):
    """Blog listing with articles published in the given period, optionally filtered by page_type."""
    try:
        return await get_blog_overview(brand, period, page_type=page_type)
    except Exception as e:
        logger.error("blog overview failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content")
async def content_pipeline(
    brand: str = Query("wihy"),
    period: str = Query("30d"),
    _=Depends(require_admin),
):
    """Content pipeline status: keywords, editorial queue, published counts."""
    try:
        return await get_content_insights(brand, period)
    except Exception as e:
        logger.error("content insights failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles")
async def articles_detail(
    brand: str = Query("wihy"),
    period: str = Query("30d"),
    _=Depends(require_admin),
):
    """Detailed per-article analytics with SEO keywords and citation counts."""
    try:
        return await get_articles_insights(brand, period)
    except Exception as e:
        logger.error("articles insights failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/topics")
async def topic_taxonomy(
    brand: str = Query("wihy"),
    _=Depends(require_admin),
):
    """Topic taxonomy with published article counts per topic hub."""
    try:
        return await get_topic_taxonomy(brand)
    except Exception as e:
        logger.error("topic taxonomy failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
