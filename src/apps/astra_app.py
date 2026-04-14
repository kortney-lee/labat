"""
astra_app.py — Astra: WIHY Discovery & Organic Intelligence Agent

Astra owns discovery: keyword research, trend signals,
SEO cycles, content queue, and organic opportunity scanning.

Mounts the discovery router under /api/astra.

Deploy: gcloud builds submit --config cloudbuild.astra.yaml
Routes:
  /api/astra/*  — Primary discovery endpoints
Auth: X-Admin-Token (INTERNAL_ADMIN_TOKEN secret)
"""

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import asyncio
import logging

from src.alex.services.alex_service import get_alex_service
from src.alex.config import (
    validate_config,
    KEYWORD_DISCOVERY_INTERVAL,
    CONTENT_QUEUE_INTERVAL,
    PAGE_REFRESH_INTERVAL,
    OPPORTUNITY_SCAN_INTERVAL,
    ANALYTICS_INTERVAL,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("astra")

# Background tasks
background_tasks = {}


# ── Background Loops ──────────────────────────────────────────────────────────

async def _run_keyword_discovery():
    await asyncio.sleep(60)
    while True:
        try:
            service = get_alex_service()
            result = await service.run_keyword_discovery()
            logger.info("Keyword discovery result: %s", result)
        except Exception as e:
            logger.error("Keyword discovery failed: %s", e)
        await asyncio.sleep(KEYWORD_DISCOVERY_INTERVAL)


async def _run_content_queue():
    await asyncio.sleep(300)
    while True:
        try:
            service = get_alex_service()
            result = await service.run_content_queue()
            logger.info("Content queue result: %s", result)
        except Exception as e:
            logger.error("Content queue failed: %s", e)
        await asyncio.sleep(CONTENT_QUEUE_INTERVAL)


async def _run_page_refresh():
    await asyncio.sleep(600)
    while True:
        try:
            service = get_alex_service()
            result = await service.run_page_refresh()
            logger.info("Page refresh result: %s", result)
        except Exception as e:
            logger.error("Page refresh failed: %s", e)
        await asyncio.sleep(PAGE_REFRESH_INTERVAL)


async def _run_opportunity_scan():
    await asyncio.sleep(900)
    while True:
        try:
            service = get_alex_service()
            result = await service.run_opportunity_scan()
            logger.info("Opportunity scan result: %s", result)
        except Exception as e:
            logger.error("Opportunity scan failed: %s", e)
        await asyncio.sleep(OPPORTUNITY_SCAN_INTERVAL)


async def _run_analytics_ingestion():
    await asyncio.sleep(120)
    while True:
        try:
            service = get_alex_service()
            result = await service.run_analytics_ingestion()
            logger.info("Analytics ingestion result: %s", result)
        except Exception as e:
            logger.error("Analytics ingestion failed: %s", e)
        await asyncio.sleep(ANALYTICS_INTERVAL)


async def _run_daily_report():
    await asyncio.sleep(1800)
    while True:
        try:
            service = get_alex_service()
            await service.send_report()
            logger.info("Daily Astra report sent")
        except Exception as e:
            logger.error("Daily report failed: %s", e)
        await asyncio.sleep(86400)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    config_status = validate_config()
    logger.info("Astra config validation: %s", config_status)

    if not all(config_status.values()):
        logger.warning("Some Astra config checks failed — cycles may error")

    logger.info("Starting Astra background tasks...")
    background_tasks["keyword_discovery"] = asyncio.create_task(_run_keyword_discovery())
    background_tasks["content_queue"] = asyncio.create_task(_run_content_queue())
    background_tasks["page_refresh"] = asyncio.create_task(_run_page_refresh())
    background_tasks["opportunity_scan"] = asyncio.create_task(_run_opportunity_scan())
    background_tasks["analytics_ingestion"] = asyncio.create_task(_run_analytics_ingestion())
    background_tasks["daily_report"] = asyncio.create_task(_run_daily_report())
    logger.info("Astra: %d background tasks started", len(background_tasks))

    yield

    logger.info("Shutting down Astra...")
    for task_name, task in background_tasks.items():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Cancelled task: %s", task_name)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Astra — WIHY Discovery & Organic Intelligence",
    description=(
        "Astra owns discovery: keyword research, trend signals, "
        "SEO content cycles, and organic opportunity scanning."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Primary routes under /api/astra
from src.alex.routers.alex_routes import router as alex_router
app.include_router(alex_router)


@app.get("/health")
async def health():
    service = get_alex_service()
    return {
        "status": "healthy",
        "service": "wihy-astra",
        "agent": "astra",
        "tasks_running": len(background_tasks),
    }


@app.get("/identity")
async def identity():
    return {
        "agent": "astra",
        "service": "wihy-astra",
        "brand_scope": "all",
        "role": "discovery",
        "version": "2.0.0",
    }


@app.get("/")
async def root():
    return {
        "service": "Astra — Discovery & Organic Intelligence",
        "version": "2.0.0",
        "agent": "astra",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "identity": "/identity",
            "status": "/api/astra/status",
            "report": "/api/astra/report",
            "trigger_keywords": "POST /api/astra/trigger/keywords",
            "trigger_content": "POST /api/astra/trigger/content-queue",
            "trigger_refresh": "POST /api/astra/trigger/page-refresh",
            "trigger_opportunities": "POST /api/astra/trigger/opportunities",
            "trigger_analytics": "POST /api/astra/trigger/analytics",
            "trigger_all": "POST /api/astra/trigger/all",
            "dependencies": "/api/astra/dependencies",
        },
    }
