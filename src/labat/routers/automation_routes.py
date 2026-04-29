"""
labat/routers/automation_routes.py — LABAT Automation endpoints.

Cloud Scheduler hits /api/labat/automation/cron every hour.
Individual tasks can also be triggered manually.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from src.labat.auth import require_admin
from src.labat.services.automation_service import (
    auto_pause_underperformers,
    auto_scale_winners,
    ab_creative_rotation,
    run_full_cycle,
)
from src.labat.services.blog_writer import write_unwritten

logger = logging.getLogger("labat.automation_routes")

router = APIRouter(prefix="/api/labat/automation", tags=["labat-automation"])

# Brand scope for this instance (set via env per deployment)
_BRAND_SCOPE = (os.getenv("LABAT_BRAND_SCOPE", "all") or "all").strip().lower()


def _effective_brand() -> str | None:
    """Return the brand to filter on, or None for account-wide."""
    return _BRAND_SCOPE if _BRAND_SCOPE != "all" else None


@router.post("/cron")
async def automation_cron(
    background_tasks: BackgroundTasks,
    dry_run: bool = Query(False),
    _=Depends(require_admin),
):
    """
    Main cron entry point — called by Cloud Scheduler every hour.
    Runs the full automation cycle: health check → auto-pause → auto-scale → A/B rotation → report.
    """
    async def _run():
        try:
            result = await run_full_cycle(dry_run=dry_run, brand=_effective_brand())
            logger.info("Automation cron completed (brand=%s): %s", _BRAND_SCOPE, result.get("elapsed_seconds", "?"))
        except Exception as e:
            logger.error("Automation cron failed (brand=%s): %s", _BRAND_SCOPE, e)

    background_tasks.add_task(_run)
    return {"status": "automation_cycle_started", "dry_run": dry_run, "brand_scope": _BRAND_SCOPE}


@router.post("/vowels-newsroom-cron")
async def vowels_newsroom_cron(
    background_tasks: BackgroundTasks,
    generate_images: bool = Query(True),
    _=Depends(require_admin),
):
    """
    Autonomous Vowels publication cycle.
    Intended for Cloud Scheduler (no human interaction required).
    """

    async def _run_newsroom():
        try:
            results = await write_unwritten(brand="vowels", generate_images=generate_images)
            logger.info("Vowels newsroom cron completed: %d items", len(results))
        except Exception as e:
            logger.error("Vowels newsroom cron failed: %s", e)

    background_tasks.add_task(_run_newsroom)
    return {
        "status": "vowels_newsroom_cycle_started",
        "brand": "vowels",
        "generate_images": generate_images,
    }


@router.post("/pause")
async def trigger_auto_pause(
    date_preset: str = Query("last_7d"),
    dry_run: bool = Query(False),
    _=Depends(require_admin),
):
    """Manually trigger auto-pause of underperforming adsets."""
    try:
        return await auto_pause_underperformers(date_preset=date_preset, dry_run=dry_run, brand=_effective_brand())
    except Exception as e:
        logger.error("Auto-pause failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scale")
async def trigger_auto_scale(
    date_preset: str = Query("last_7d"),
    dry_run: bool = Query(False),
    _=Depends(require_admin),
):
    """Manually trigger auto-scale of winning adsets."""
    try:
        return await auto_scale_winners(date_preset=date_preset, dry_run=dry_run, brand=_effective_brand())
    except Exception as e:
        logger.error("Auto-scale failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ab-rotation")
async def trigger_ab_rotation(
    date_preset: str = Query("last_7d"),
    dry_run: bool = Query(False),
    _=Depends(require_admin),
):
    """Manually trigger A/B creative rotation."""
    try:
        return await ab_creative_rotation(date_preset=date_preset, dry_run=dry_run, brand=_effective_brand())
    except Exception as e:
        logger.error("A/B rotation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def automation_status(_=Depends(require_admin)):
    """Show current automation thresholds and configuration."""
    from src.labat.services.automation_service import (
        PAUSE_SPEND_THRESHOLD, PAUSE_MIN_IMPRESSIONS, PAUSE_CTR_FLOOR,
        SCALE_ROAS_THRESHOLD, SCALE_MIN_CONVERSIONS, SCALE_MAX_INCREASE_PCT,
        SCALE_BUDGET_CEILING, AB_MIN_IMPRESSIONS, AB_WIN_MARGIN,
    )
    return {
        "auto_pause": {
            "spend_threshold_usd": PAUSE_SPEND_THRESHOLD,
            "min_impressions": PAUSE_MIN_IMPRESSIONS,
            "ctr_floor_pct": PAUSE_CTR_FLOOR,
        },
        "auto_scale": {
            "roas_threshold": SCALE_ROAS_THRESHOLD,
            "min_conversions": SCALE_MIN_CONVERSIONS,
            "max_increase_pct": SCALE_MAX_INCREASE_PCT,
            "budget_ceiling_usd": SCALE_BUDGET_CEILING / 100,
        },
        "ab_rotation": {
            "min_impressions_per_ad": AB_MIN_IMPRESSIONS,
            "win_margin": AB_WIN_MARGIN,
        },
    }
