"""
labat/routers/page_routes.py — Page info and feed.

GET /api/labat/page               — Page info
GET /api/labat/page/feed          — Page feed (paginated)
GET /api/labat/page/posts/:id     — Single post detail
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.labat.auth import require_admin
from src.labat.services.page_service import get_page_info, get_page_feed, get_post_detail
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.page_routes")

router = APIRouter(prefix="/api/labat/page", tags=["labat-page"])


@router.get("")
async def page_info(
    page_id: Optional[str] = Query(None),
    _=Depends(require_admin),
):
    try:
        return await get_page_info(page_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/feed")
async def page_feed(
    page_id: Optional[str] = Query(None),
    limit: int = Query(25, ge=1, le=100),
    after: Optional[str] = Query(None),
    _=Depends(require_admin),
):
    try:
        return await get_page_feed(page_id, limit=limit, after=after)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/posts/{post_id}")
async def post_detail(
    post_id: str,
    _=Depends(require_admin),
):
    try:
        return await get_post_detail(post_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
