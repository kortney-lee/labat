"""
Vowels newsroom routes.

Autonomous publication controls + newsroom feeds (RSS + news sitemap).
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Response

from src.labat.services.blog_writer import CONTENT_TYPES, get_queue_status, write_unwritten
from src.labat.services.vowels_newsroom import (
    get_newsroom_blueprint,
    load_vowels_posts,
    render_news_sitemap_xml,
    render_rss_xml,
)

logger = logging.getLogger("vowels.newsroom.routes")
router = APIRouter(prefix="/api/vowels/newsroom", tags=["vowels-newsroom"])

INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN") or "").strip()


def _check_admin(token: str):
    if not INTERNAL_ADMIN_TOKEN:
        return
    if token != INTERNAL_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/health")
async def newsroom_health():
    return {
        "status": "healthy",
        "publication": "vowels.org",
        "mode": "autonomous-newsroom",
        "master_editor": "kortney-otaku",
    }


@router.get("/blueprint")
async def newsroom_blueprint():
    return get_newsroom_blueprint()


@router.get("/content-types")
async def newsroom_content_types():
    return {
        "content_types": CONTENT_TYPES,
        "default": "news-update",
        "supports_sponsored_labeling": True,
    }


@router.get("/queue")
async def newsroom_queue(
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)
    queue = get_queue_status()
    vowels_articles = [a for a in queue["articles"] if a.get("brand") == "vowels"]
    return {
        "brand": "vowels",
        "total": len(vowels_articles),
        "articles": vowels_articles,
        "by_content_type": queue.get("by_content_type", {}),
    }


@router.post("/run-autonomous")
async def run_autonomous_newsroom(
    background_tasks: BackgroundTasks,
    generate_images: bool = True,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    _check_admin(x_admin_token)

    async def _run_cycle():
        try:
            results = await write_unwritten(brand="vowels", generate_images=generate_images)
            logger.info("Vowels autonomous cycle complete: %d articles", len(results))
        except Exception as e:
            logger.error("Vowels autonomous cycle failed: %s", e)

    background_tasks.add_task(_run_cycle)
    return {
        "status": "accepted",
        "brand": "vowels",
        "message": "Autonomous Vowels newsroom cycle started.",
        "master_editor": "Kortney (Otaku)",
    }


@router.get("/rss.xml")
async def vowels_rss():
    posts = load_vowels_posts(limit=200)
    xml = render_rss_xml(posts)
    return Response(content=xml, media_type="application/rss+xml")


@router.get("/news-sitemap.xml")
async def vowels_news_sitemap():
    posts = load_vowels_posts(limit=300)
    xml = render_news_sitemap_xml(posts)
    return Response(content=xml, media_type="application/xml")
