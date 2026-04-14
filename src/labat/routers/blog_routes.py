"""
labat/routers/blog_routes.py — Kortney blog writer API routes.

Mounted on the Master Agent at /api/kortney/blog/*.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel, Field

from src.labat.services.blog_writer import (
    get_queue_status,
    write_and_publish,
    write_all_pending,
    write_unwritten,
    patch_existing_articles_topic_slug,
    TOPIC_TAXONOMY,
)

logger = logging.getLogger("kortney.blog_routes")

router = APIRouter(prefix="/api/kortney/blog", tags=["kortney-blog"])

INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN") or "").strip()


def _check_admin(token: str):
    if not INTERNAL_ADMIN_TOKEN:
        return
    if token != INTERNAL_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


# ── Schemas ──────────────────────────────────────────────────────────────────

class WriteRequest(BaseModel):
    slug: str
    generate_image: bool = True


class WriteAllRequest(BaseModel):
    generate_images: bool = True


class WriteUnwrittenRequest(BaseModel):
    brand: str = "wihy"
    generate_images: bool = True


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def blog_health():
    """Kortney blog writer health check."""
    return {"status": "healthy", "agent": "kortney", "service": "blog_writer"}


@router.get("/queue")
async def blog_queue(
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Return the editorial queue with status."""
    _check_admin(x_admin_token)
    return get_queue_status()


@router.post("/write")
async def write_single(
    body: WriteRequest,
    background_tasks: BackgroundTasks,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Write and publish a single blog article by slug. Runs in background."""
    _check_admin(x_admin_token)

    # Validate slug exists in queue
    queue = get_queue_status()
    slugs = [a["slug"] for a in queue["articles"]]
    if body.slug not in slugs:
        raise HTTPException(
            status_code=404,
            detail=f"Slug '{body.slug}' not in editorial queue. Available: {slugs}",
        )

    async def _do_write():
        try:
            result = await write_and_publish(body.slug, generate_image=body.generate_image)
            logger.info("KORTNEY: Finished writing '%s': %s", body.slug, result)
        except Exception as e:
            logger.error("KORTNEY: Failed to write '%s': %s", body.slug, e)

    background_tasks.add_task(_do_write)
    return {
        "status": "accepted",
        "slug": body.slug,
        "message": f"Kortney is writing '{body.slug}' — this takes 1-2 minutes.",
    }


@router.post("/write-all")
async def write_all(
    body: WriteAllRequest,
    background_tasks: BackgroundTasks,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Write and publish ALL articles in the queue. Runs in background."""
    _check_admin(x_admin_token)

    async def _do_write_all():
        try:
            results = await write_all_pending(generate_images=body.generate_images)
            logger.info("KORTNEY: Finished writing all — %d results", len(results))
        except Exception as e:
            logger.error("KORTNEY: write-all failed: %s", e)

    background_tasks.add_task(_do_write_all)
    queue = get_queue_status()
    return {
        "status": "accepted",
        "total": queue["total"],
        "wihy": queue["wihy"],
        "communitygroceries": queue["communitygroceries"],
        "message": f"Kortney is writing all {queue['total']} articles — this may take 15-20 minutes.",
    }


@router.post("/write-unwritten")
async def write_unwritten_articles(
    body: WriteUnwrittenRequest,
    background_tasks: BackgroundTasks,
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Write only articles not yet published. Skips already-published slugs."""
    _check_admin(x_admin_token)

    async def _do_write():
        try:
            results = await write_unwritten(
                brand=body.brand, generate_images=body.generate_images
            )
            logger.info("KORTNEY: Finished writing unwritten — %d results", len(results))
        except Exception as e:
            logger.error("KORTNEY: write-unwritten failed: %s", e)

    background_tasks.add_task(_do_write)
    return {
        "status": "accepted",
        "brand": body.brand,
        "message": f"Kortney is writing unwritten {body.brand} articles in the background.",
    }


@router.post("/patch-topics")
async def patch_topics(
    brand: str = "wihy",
    x_admin_token: str = Header("", alias="X-Admin-Token"),
):
    """Patch existing published articles to add topic_slug from queue."""
    _check_admin(x_admin_token)
    patched = patch_existing_articles_topic_slug(brand)
    return {"patched": patched, "count": len(patched)}


@router.get("/topics")
async def list_topics():
    """Return the 10 launch topic taxonomy (public, no auth needed)."""
    return {"topics": TOPIC_TAXONOMY, "count": len(TOPIC_TAXONOMY)}
