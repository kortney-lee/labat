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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start engagement thread monitor on boot."""
    # Thread monitor (replies to engagement threads)
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
