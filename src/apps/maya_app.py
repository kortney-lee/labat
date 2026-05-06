"""
maya_app.py — Maya: WIHY Community Engagement Agent

Maya owns all engagement — replies, comments, threads, Messenger DMs,
webhook handling, and compliance callbacks. She manages conversations.

Extracted from Shania (who now only handles posting/publishing).

Deploy: gcloud builds submit --config cloudbuild.maya.yaml
Routes:
  /api/engagement/*        — Lead engagement (Twitter, Instagram, social replies)
  /api/labat/comments/*    — Facebook comment moderation & replies
  /api/labat/messenger/*   — Messenger DMs & private replies
  /api/labat/webhooks      — Facebook webhook (page events)
  /api/labat/compliance    — Data deletion callbacks
Auth: X-Admin-Token (INTERNAL_ADMIN_TOKEN secret)
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.labat.config import validate_config

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("maya_app")


async def _run_loop(fn, interval: int, label: str, initial_delay: int = 0) -> None:
    """Generic background loop: run fn() every interval seconds, log errors but keep running."""
    if initial_delay:
        logger.info("maya_app loop [%s] waiting %ds before first run", label, initial_delay)
        await asyncio.sleep(initial_delay)
    while True:
        try:
            result = await fn()
            logger.info("maya_app loop [%s] complete: %s", label, result)
        except Exception as e:
            logger.error("maya_app loop [%s] error: %s", label, e)
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start all Maya background services on boot."""
    import asyncio

    # Thread monitor (replies to engagement threads on Twitter + Threads)
    try:
        from src.maya.services.engagement_poster_service import thread_monitor
        logger.info("maya_app: starting thread monitor")
        await thread_monitor.start()
        app.state.thread_monitor = thread_monitor
    except Exception as e:
        logger.warning("Thread monitor unavailable: %s", e)
        app.state.thread_monitor = None
        try:
            from src.labat.services.notify import send_notification
            await send_notification(
                agent="maya",
                severity="critical",
                title="Maya Thread Monitor Failed to Start",
                message=f"Thread monitor did not start on boot: {e}",
                service="maya",
                details={"error": str(e)},
            )
        except Exception as notify_err:
            logger.warning("Failed to send monitor-start alert: %s", notify_err)

    # Social posting service (auto-generates posts every 4 hours)
    try:
        from src.maya.services.social_posting_service import social_posting_service
        logger.info("maya_app: starting social posting service")
        await social_posting_service.start()
        app.state.social_posting = social_posting_service
    except Exception as e:
        logger.warning("Social posting service unavailable: %s", e)
        app.state.social_posting = None

    # Audience discovery — find target users via hashtags every 6 hours
    try:
        from src.maya.services.audience_discovery_service import run_once as _discovery_run
        app.state.discovery_task = asyncio.create_task(
            _run_loop(_discovery_run, interval=86400, label="audience-discovery", initial_delay=3600)
        )
        logger.info("maya_app: audience discovery loop started (every 24h, first run in 1h)")
    except Exception as e:
        logger.warning("Audience discovery unavailable: %s", e)
        app.state.discovery_task = None

    # Collaborator finder — find creator partners every 24 hours
    try:
        from src.maya.services.collaborator_finder_service import run_once as _collab_run
        app.state.collaborator_task = asyncio.create_task(
            _run_loop(_collab_run, interval=86400, label="collaborator-finder", initial_delay=7200)
        )
        logger.info("maya_app: collaborator finder loop started (every 24h, first run in 2h)")
    except Exception as e:
        logger.warning("Collaborator finder unavailable: %s", e)
        app.state.collaborator_task = None

    # Auto-engage — like and follow discovered users every 2 hours
    try:
        from src.maya.services.auto_engage_service import run_once as _engage_run
        app.state.auto_engage_task = asyncio.create_task(
            _run_loop(_engage_run, interval=7200, label="auto-engage")
        )
        logger.info("maya_app: auto-engage loop started (every 2h)")
    except Exception as e:
        logger.warning("Auto-engage unavailable: %s", e)
        app.state.auto_engage_task = None

    # Twitter Filtered Stream — real-time tweet listener (Bearer token)
    try:
        from src.maya.services.twitter_stream_service import twitter_stream_service
        await twitter_stream_service.start()
        app.state.twitter_stream = twitter_stream_service
        logger.info("maya_app: Twitter Filtered Stream started")
    except Exception as e:
        logger.warning("Twitter stream unavailable: %s", e)
        app.state.twitter_stream = None

    # Twitter Trends — poll every 1 hour
    try:
        from src.maya.services.twitter_trends_service import run_once as _trends_run
        app.state.trends_task = asyncio.create_task(
            _run_loop(_trends_run, interval=3600, label="twitter-trends")
        )
        logger.info("maya_app: Twitter trends loop started (every 1h)")
    except Exception as e:
        logger.warning("Twitter trends unavailable: %s", e)
        app.state.trends_task = None

    status = validate_config()
    logger.info("Maya Facebook config: %s", {
        k: v for k, v in status.items() if k.startswith("shania") or k.startswith("webhook")
    })
    yield

    if getattr(app.state, "thread_monitor", None):
        logger.info("maya_app: stopping thread monitor")
        await app.state.thread_monitor.stop()

    if getattr(app.state, "social_posting", None):
        logger.info("maya_app: stopping social posting service")
        await app.state.social_posting.stop()

    stream = getattr(app.state, "twitter_stream", None)
    if stream:
        await stream.stop()

    for attr in ("discovery_task", "collaborator_task", "auto_engage_task", "trends_task"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass



app = FastAPI(
    title="Maya — WIHY Community Engagement Agent",
    description=(
        "Maya owns all community engagement: replies, comments, thread handling, "
        "Messenger DMs, webhook processing, and compliance callbacks. "
        "Maya manages conversations. Shania publishes. Labat spends."
    ),
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_utf8_charset(request: Request, call_next):
    response = await call_next(request)
    ct = response.headers.get("content-type", "")
    if "application/json" in ct and "charset" not in ct:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


# ── Verbose Request Logger ──
try:
    from src.shared.middleware.request_logger import VerboseRequestLoggerMiddleware
    app.add_middleware(VerboseRequestLoggerMiddleware, service_name="wihy-maya")
    logger.info("Verbose request logger middleware enabled")
except ImportError as e:
    logger.warning(f"Verbose request logger not available: {e}")


# ── Social Engagement (Twitter / Instagram / TikTok — replies & threads) ─────

try:
    from src.maya.routers.engagement_routes import router as engagement_router
    app.include_router(engagement_router)
    logger.info("Social engagement router loaded")
except Exception as e:
    logger.warning("Social engagement router unavailable: %s", e)

# ── Audience Discovery / Collaborator Finder / Auto-Engage ───────────────────

try:
    from src.maya.routers.discovery_routes import router as discovery_router
    app.include_router(discovery_router)
    logger.info("Discovery routes loaded (audience discovery, collaborators, auto-engage)")
except Exception as e:
    logger.warning("Discovery routes unavailable: %s", e)

# ── Twitter Webhook (Account Activity API — Pro tier) ────────────────────────

try:
    from src.maya.routers.twitter_webhook_routes import router as twitter_webhook_router
    app.include_router(twitter_webhook_router)
    logger.info("Twitter webhook routes loaded (CRC + event ingestion)")
except Exception as e:
    logger.warning("Twitter webhook routes unavailable: %s", e)


# ── Facebook Engagement (comments, Messenger, webhooks, compliance) ──────────

from src.labat.routers.comment_routes import router as comment_router
from src.labat.routers.messenger_routes import router as messenger_router
from src.labat.routers.webhook_routes import router as webhook_router
from src.labat.routers.compliance_routes import router as compliance_router

app.include_router(comment_router)
app.include_router(messenger_router)
app.include_router(webhook_router)
app.include_router(compliance_router)

logger.info("Facebook engagement routers loaded (comments, messenger, webhooks, compliance)")


# ── Health & Identity ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    tm = getattr(app.state, "thread_monitor", None)
    sp = getattr(app.state, "social_posting", None)
    return {
        "status": "ok",
        "service": "wihy-maya",
        "agent": "maya",
        "role": "engagement",
        "monitor": tm.status() if tm else "unavailable",
        "social_posting": sp.status() if sp else "unavailable",
        "audience_discovery": "running" if getattr(app.state, "discovery_task", None) and not app.state.discovery_task.done() else "stopped",
        "collaborator_finder": "running" if getattr(app.state, "collaborator_task", None) and not app.state.collaborator_task.done() else "stopped",
        "auto_engage": "running" if getattr(app.state, "auto_engage_task", None) and not app.state.auto_engage_task.done() else "stopped",
        "twitter_stream": getattr(app.state, "twitter_stream", None) and app.state.twitter_stream.status() or "unavailable",
        "twitter_trends": "running" if getattr(app.state, "trends_task", None) and not app.state.trends_task.done() else "stopped",
    }


@app.get("/identity")
async def identity():
    return {
        "agent": "maya",
        "service": "wihy-maya",
        "brand_scope": "all",
        "role": "engagement",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {"service": "wihy-maya", "agent": "maya", "docs": "/docs"}
