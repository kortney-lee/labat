"""
apps/alex_app.py — ALEX (AI Language Executing X) FastAPI application.

Independent Cloud Run service that runs autonomous SEO cycles:
keyword discovery, content generation, page refresh, opportunity
scanning, and analytics ingestion — all on configurable intervals.

Deployed separately via cloudbuild.alex.yaml.
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
import os

from src.alex.routers.alex_routes import router as alex_router
from src.alex.services.alex_service import get_alex_service
from src.alex.services.ad_posting_service import ad_posting_service
from src.alex.config import (
    validate_config,
    KEYWORD_DISCOVERY_INTERVAL,
    CONTENT_QUEUE_INTERVAL,
    PAGE_REFRESH_INTERVAL,
    OPPORTUNITY_SCAN_INTERVAL,
    ANALYTICS_INTERVAL,
    ALEX_BRAND_SCOPE,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("alex")

# Background tasks
background_tasks = {}


# ── Background Loops ──────────────────────────────────────────────────────────

async def _run_keyword_discovery():
    """Keyword discovery cycle — every 6 hours by default."""
    await asyncio.sleep(60)  # Initial delay to let services warm up
    while True:
        try:
            service = get_alex_service()
            result = await service.run_keyword_discovery()
            logger.info("Keyword discovery result: %s", result)
        except Exception as e:
            logger.error("Keyword discovery failed: %s", e)
        await asyncio.sleep(KEYWORD_DISCOVERY_INTERVAL)


async def _run_content_queue():
    """Content queue processing — every 4 hours by default."""
    await asyncio.sleep(300)  # 5 min initial delay (after keywords)
    while True:
        try:
            service = get_alex_service()
            result = await service.run_content_queue()
            logger.info("Content queue result: %s", result)
        except Exception as e:
            logger.error("Content queue failed: %s", e)
        await asyncio.sleep(CONTENT_QUEUE_INTERVAL)


async def _run_page_refresh():
    """Page refresh cycle — every 24 hours by default."""
    await asyncio.sleep(600)  # 10 min initial delay
    while True:
        try:
            service = get_alex_service()
            result = await service.run_page_refresh()
            logger.info("Page refresh result: %s", result)
        except Exception as e:
            logger.error("Page refresh failed: %s", e)
        await asyncio.sleep(PAGE_REFRESH_INTERVAL)


async def _run_opportunity_scan():
    """Opportunity scan — every 24 hours by default."""
    await asyncio.sleep(900)  # 15 min initial delay
    while True:
        try:
            service = get_alex_service()
            result = await service.run_opportunity_scan()
            logger.info("Opportunity scan result: %s", result)
        except Exception as e:
            logger.error("Opportunity scan failed: %s", e)
        await asyncio.sleep(OPPORTUNITY_SCAN_INTERVAL)


async def _run_analytics_ingestion():
    """Analytics ingestion — every 1 hour by default."""
    await asyncio.sleep(120)  # 2 min initial delay
    while True:
        try:
            service = get_alex_service()
            result = await service.run_analytics_ingestion()
            logger.info("Analytics ingestion result: %s", result)
        except Exception as e:
            logger.error("Analytics ingestion failed: %s", e)
        await asyncio.sleep(ANALYTICS_INTERVAL)


async def _run_daily_report():
    """Send a daily summary report."""
    await asyncio.sleep(1800)  # 30 min initial delay
    while True:
        try:
            service = get_alex_service()
            await service.send_report()
            logger.info("Daily ALEX report sent")
        except Exception as e:
            logger.error("Daily report failed: %s", e)
        await asyncio.sleep(86400)  # 24 hours


async def _run_twitter_trends():
    """Poll Twitter trends every hour and store in Firestore for keyword discovery."""
    await asyncio.sleep(180)  # 3 min initial delay
    while True:
        try:
            from src.maya.services.twitter_trends_service import run_once
            result = await run_once()
            logger.info("Twitter trends fetched: %d health-relevant trends", result.get("total_health_trends", 0))
        except Exception as e:
            logger.error("Twitter trends fetch failed: %s", e)
        await asyncio.sleep(3600)  # 1 hour


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of ALEX background tasks."""
    # Validate config on startup
    config_status = validate_config()
    logger.info("ALEX config validation: %s", config_status)

    if not all(config_status.values()):
        logger.warning("Some ALEX config checks failed — cycles may error")

    # Start background tasks
    logger.info("Starting ALEX background tasks...")
    background_tasks["keyword_discovery"] = asyncio.create_task(_run_keyword_discovery())
    background_tasks["content_queue"] = asyncio.create_task(_run_content_queue())
    background_tasks["page_refresh"] = asyncio.create_task(_run_page_refresh())
    background_tasks["opportunity_scan"] = asyncio.create_task(_run_opportunity_scan())
    background_tasks["analytics_ingestion"] = asyncio.create_task(_run_analytics_ingestion())
    background_tasks["daily_report"] = asyncio.create_task(_run_daily_report())
    background_tasks["twitter_trends"] = asyncio.create_task(_run_twitter_trends())
    logger.info("ALEX: %d background tasks started", len(background_tasks))

    # Start autonomous ad creation (LABAT photo ads) only when explicitly enabled.
    ad_posting_enabled = os.getenv("AD_POSTING_ENABLED", "false").strip().lower() == "true"
    if ad_posting_enabled:
        try:
            await ad_posting_service.start()
            app.state.ad_posting = ad_posting_service
            logger.info("ALEX: Ad posting service started")
        except Exception as e:
            logger.warning("Ad posting service unavailable: %s", e)
            app.state.ad_posting = None
    else:
        app.state.ad_posting = None
        logger.info("ALEX: Ad posting service disabled (AD_POSTING_ENABLED=false)")

    yield  # App running

    # Cleanup on shutdown
    logger.info("Shutting down ALEX...")
    if getattr(app.state, "ad_posting", None):
        await app.state.ad_posting.stop()
    for task_name, task in background_tasks.items():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Cancelled task: %s", task_name)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="WIHY ALEX — AI Language Executing X",
    description="Autonomous SEO, content generation, and knowledge expansion service",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routes
app.include_router(alex_router)


@app.get("/health")
async def health():
    """ALEX health check."""
    service = get_alex_service()
    status = service.get_status()
    ap = getattr(app.state, "ad_posting", None)
    return {
        "status": "healthy",
        "service": "alex-seo-agent",
        "tasks_running": len(background_tasks),
        "ad_posting": ap.status() if ap else "unavailable",
    }


@app.get("/identity")
async def identity():
    """Service identity for routing verification."""
    return {
        "agent": "astra",
        "service": "wihy-astra",
        "brand_scope": ALEX_BRAND_SCOPE or "all",
        "role": "discovery",
        "version": "2.0.0",
        "legacy_name": "alex",
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Astra — Discovery & Organic Intelligence (formerly ALEX)",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "status": "/api/alex/status",
            "report": "/api/alex/report",
            "trigger_keywords": "POST /api/alex/trigger/keywords",
            "trigger_content": "POST /api/alex/trigger/content-queue",
            "trigger_refresh": "POST /api/alex/trigger/page-refresh",
            "trigger_opportunities": "POST /api/alex/trigger/opportunities",
            "trigger_analytics": "POST /api/alex/trigger/analytics",
            "trigger_all": "POST /api/alex/trigger/all",
            "dependencies": "/api/alex/dependencies",
        },
    }
