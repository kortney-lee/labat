"""
shania_app.py — Shania: WIHY Publishing & Posting Agent

Shania owns posting and publishing — Facebook Page posts, LinkedIn posts,
and scheduled social content. She publishes. Maya engages. Labat spends.

Deploy: gcloud builds submit --config cloudbuild.shania.yaml
Routes:
  /api/labat/page/*   — Facebook Page info & feed
  /api/labat/posts/*  — Facebook Page posts (publish, edit, delete)
  /api/labat/linkedin/* — LinkedIn posting
Auth: X-Admin-Token (INTERNAL_ADMIN_TOKEN secret)

NOTE: Engagement routes (comments, Messenger, webhooks, compliance, social
      engagement) have been migrated to Maya (maya_app.py / wihy-maya).
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
logger = logging.getLogger("shania_app")

SHANIA_BRAND_SCOPE = os.getenv("SHANIA_BRAND_SCOPE", "").strip().lower() or None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate config on boot for posting service."""
    status = validate_config()
    logger.info("Shania Facebook config: %s", {
        k: v for k, v in status.items() if k.startswith("shania")
    })
    yield


app = FastAPI(
    title="Shania — WIHY Publishing & Posting Agent",
    description=(
        "Shania owns publishing: Facebook Page posts, LinkedIn posts, "
        "and scheduled social content. "
        "Shania publishes. Maya engages. Labat spends."
    ),
    version="2.1.0",
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
    app.add_middleware(VerboseRequestLoggerMiddleware, service_name="wihy-shania")
    logger.info("Verbose request logger middleware enabled")
except ImportError as e:
    logger.warning(f"Verbose request logger not available: {e}")


# ── Facebook Page Publishing (Shania app credentials) ────────────────────────

from src.labat.routers.page_routes import router as page_router
from src.labat.routers.post_routes import router as post_router

app.include_router(page_router)
app.include_router(post_router)

logger.info("Facebook page publishing routers loaded (page, posts)")

# ── LinkedIn Posting (Shania using LinkedIn API) ───────────────────────────

try:
    from src.labat.routers.linkedin_posting_routes import router as linkedin_posting_router
    app.include_router(linkedin_posting_router)
    logger.info("LinkedIn posting router loaded")
except Exception as e:
    logger.warning("LinkedIn posting router unavailable: %s", e)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    full_config = validate_config()
    required_keys = ["shania_app", "shania_page_token", "admin_auth", "linkedin"]
    required_config = {k: full_config.get(k, False) for k in required_keys}
    return {
        "status": "ok",
        "service": "wihy-shania",
        "agent": "shania",
        "role": "posting",
        "facebook": full_config,
        "readiness": {
            "required": required_config,
            "required_ready": all(required_config.values()),
            "required_ready_count": sum(1 for v in required_config.values() if v),
            "required_total": len(required_config),
        },
    }


@app.get("/identity")
async def identity():
    return {
        "agent": "shania",
        "service": "wihy-shania",
        "brand_scope": SHANIA_BRAND_SCOPE or "all",
        "role": "posting",
        "version": "2.1.0",
    }


@app.get("/")
async def root():
    return {"service": "wihy-shania", "agent": "shania", "docs": "/docs"}

