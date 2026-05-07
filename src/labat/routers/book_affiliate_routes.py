"""
labat/routers/book_affiliate_routes.py

Affiliate-only book promotion endpoints.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from src.labat.auth import require_admin
from src.labat.schemas import BookAffiliatePublishRequest
from src.labat.services.book_affiliate_service import (
    list_book_editions,
    preview_book_post,
    publish_book_post,
)

logger = logging.getLogger("labat.book_affiliate_routes")

router = APIRouter(prefix="/api/labat/book-affiliate", tags=["labat-book-affiliate"])


@router.get("/catalog", dependencies=[Depends(require_admin)])
async def catalog():
    return {
        "count": len(list_book_editions()),
        "editions": list_book_editions(),
    }


@router.get("/preview", dependencies=[Depends(require_admin)])
async def preview(
    asin: str | None = Query(default=None),
    seed: int | None = Query(default=None),
):
    return preview_book_post(asin=asin, seed=seed)


@router.post("/publish", dependencies=[Depends(require_admin)])
async def publish(body: BookAffiliatePublishRequest):
    return await publish_book_post(
        asin=body.asin,
        page_id=body.page_id,
        seed=body.seed,
        dry_run=body.dry_run,
    )
