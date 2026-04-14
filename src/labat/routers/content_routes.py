"""
labat/routers/content_routes.py — Content & keyword CRUD API.

Serves /api/content/keywords (the endpoint Alex and Kortney use).
Deployed on the Master Agent service at labat.wihy.ai.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from src.labat.services.keyword_store import (
    add_keyword,
    bulk_add_keywords,
    get_keywords_for_topic,
    list_keywords,
    update_keyword_status,
)
from src.labat.services.page_store import (
    add_page,
    get_page,
    list_pages,
    refresh_page,
)
from src.labat.services.opportunity_store import (
    add_opportunity,
    list_opportunities,
)

logger = logging.getLogger("wihy.content_routes")

router = APIRouter(prefix="/api/content", tags=["content"])

INTERNAL_ADMIN_TOKEN: str = ""  # set at import time from env

import os

INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN") or "").strip()


def _check_admin(token: str):
    if not INTERNAL_ADMIN_TOKEN:
        return  # no token configured — allow (dev mode)
    if token != INTERNAL_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


# ── Schemas ───────────────────────────────────────────────────────────────────


class KeywordCreate(BaseModel):
    keyword: str
    brand: str = "wihy"
    source: str = "manual"
    intent: str = "informational"
    priority_score: int = Field(5, ge=1, le=10)
    suggested_page_type: str = "topic"
    discovered_by: str = "api"


class BulkKeywordCreate(BaseModel):
    keywords: list[KeywordCreate]


class KeywordStatusUpdate(BaseModel):
    status: str


# ── Routes ────────────────────────────────────────────────────────────────────


@router.get("/keywords")
async def get_keywords(
    status: Optional[str] = None,
    min_priority: int = 0,
    limit: int = 200,
    brand: Optional[str] = None,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """List keywords with optional filters."""
    _check_admin(x_admin_token)
    return list_keywords(status=status, min_priority=min_priority, limit=limit, brand=brand)


@router.post("/keywords")
async def create_keyword(
    body: KeywordCreate,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Add a single keyword."""
    _check_admin(x_admin_token)
    return add_keyword(body.model_dump())


@router.post("/keywords/bulk")
async def create_keywords_bulk(
    body: BulkKeywordCreate,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Add multiple keywords at once."""
    _check_admin(x_admin_token)
    return bulk_add_keywords([k.model_dump() for k in body.keywords])


@router.post("/keywords/{keyword_id}/status")
async def set_keyword_status(
    keyword_id: str,
    body: KeywordStatusUpdate,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Update keyword status (pending, used, page_generated, etc.)."""
    _check_admin(x_admin_token)
    result = update_keyword_status(keyword_id, body.status)
    if not result:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return result


@router.get("/keywords/for-topic")
async def keywords_for_topic(
    topic: str,
    brand: str = "wihy",
    limit: int = 12,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Get keywords relevant to a specific topic (used by Kortney before writing)."""
    _check_admin(x_admin_token)
    return {"topic": topic, "brand": brand, "keywords": get_keywords_for_topic(topic, brand, limit)}


# ── Page Routes ───────────────────────────────────────────────────────────────


class PageCreate(BaseModel):
    slug: str
    title: str = ""
    page_type: str = "topic"
    content: str = ""
    meta_description: str = ""
    status: str = "draft"
    source_keyword: str = ""
    generated_by: str = "api"


class PageRefresh(BaseModel):
    new_title: Optional[str] = None
    new_meta_description: Optional[str] = None
    content_additions: Optional[str] = None
    improvement_notes: Optional[str] = None


@router.get("/pages")
async def get_pages(
    status: Optional[str] = None,
    limit: int = 50,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)
    return list_pages(status=status, limit=limit)


@router.get("/pages/{slug}")
async def get_page_by_slug(
    slug: str,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)
    page = get_page(slug)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return page


@router.post("/pages")
async def create_page(
    body: PageCreate,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)
    return add_page(body.model_dump())


@router.post("/pages/{slug}/refresh")
async def refresh_page_route(
    slug: str,
    body: PageRefresh,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)
    result = refresh_page(slug, body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Page not found")
    return result


# ── Opportunity Routes ────────────────────────────────────────────────────────


class OpportunityCreate(BaseModel):
    title: str
    type: str = "conference"
    organization: str = ""
    fit_score: int = Field(5, ge=1, le=10)
    suggested_talk_title: str = ""
    pitch_summary: str = ""
    notes: str = ""
    status: str = "new"
    discovered_by: str = "api"


@router.get("/opportunities")
async def get_opportunities(
    status: Optional[str] = None,
    limit: int = 100,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)
    return list_opportunities(status=status, limit=limit)


@router.post("/opportunities")
async def create_opportunity(
    body: OpportunityCreate,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)
    return add_opportunity(body.model_dump())
