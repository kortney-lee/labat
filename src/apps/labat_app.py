"""
labat_app.py — WIHY LABAT Service

Lead Automation, Business Ads & Targeting.
Meta/Facebook automation: ads, Page publishing, comments, webhooks, Messenger.

Cloud Run: wihy-labat
Routes:  /api/labat/*
Auth:    X-Admin-Token (INTERNAL_ADMIN_TOKEN secret)
Deploy:  gcloud builds submit --config cloudbuild.labat.yaml
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.labat.config import validate_config

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("labat_app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    status = validate_config()
    logger.info("LABAT service starting — config status: %s", status)
    yield
    logger.info("LABAT service shutting down")


app = FastAPI(
    title="WIHY LABAT Service",
    description=(
        "Lead Automation, Business Ads & Targeting — "
        "LABAT spends money to make money: ad campaigns, budgets, creatives, "
        "spend tracking, ROAS, revenue, lead capture from paid ads, conversions API. "
        "Shania handles engagement. LABAT handles the money."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
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

# ── Verbose Request Logger ──
try:
    from src.shared.middleware.request_logger import VerboseRequestLoggerMiddleware
    app.add_middleware(VerboseRequestLoggerMiddleware, service_name="wihy-labat")
    logger.info("Verbose request logger middleware enabled")
except ImportError as e:
    logger.warning(f"Verbose request logger not available: {e}")


@app.middleware("http")
async def enforce_utf8_charset(request: Request, call_next):
    response = await call_next(request)
    ct = response.headers.get("content-type", "")
    if "application/json" in ct and "charset" not in ct:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


# ── Telemetry ─────────────────────────────────────────────────────────────────

try:
    from src.shared.monitoring import setup_telemetry
    setup_telemetry(app, service_name="wihy-labat")
except ImportError:
    logger.warning("Telemetry not available")


# ── Routers ───────────────────────────────────────────────────────────────────

from src.labat.routers.auth_routes import router as auth_router
from src.labat.routers.ads_routes import router as ads_router
from src.labat.routers.creative_routes import router as creative_router
from src.labat.routers.insights_routes import router as insights_router
from src.labat.routers.conversions_routes import router as conversions_router
from src.labat.routers.leads_routes import router as leads_router
from src.labat.routers.ai_routes import router as ai_router
from src.labat.routers.post_routes import router as post_router
from src.labat.routers.blog_routes import router as blog_router
from src.labat.routers.trending_routes import router as trending_router
from src.labat.routers.master_agent_routes import router as master_agent_router
from src.labat.routers.automation_routes import router as automation_router
from src.labat.routers.rules_routes import router as rules_router
from src.labat.routers.vowels_newsroom_routes import router as vowels_newsroom_router
from src.labat.routers.book_affiliate_routes import router as book_affiliate_router
from src.labat.routers.amazon_ads_routes import router as amazon_ads_router

app.include_router(auth_router)
app.include_router(ads_router)
app.include_router(creative_router)
app.include_router(insights_router)
app.include_router(conversions_router)
app.include_router(leads_router)
app.include_router(ai_router)
app.include_router(post_router)
app.include_router(blog_router)
app.include_router(trending_router)
app.include_router(master_agent_router)
app.include_router(automation_router)
app.include_router(rules_router)
app.include_router(vowels_newsroom_router)
app.include_router(book_affiliate_router)
app.include_router(amazon_ads_router)

logger.info("All LABAT routers loaded (including master agent + automation + rules)")

# ── LinkedIn Analytics (LABAT reporting) ──────────────────────────────────────

try:
    from src.labat.routers.linkedin_analytics_routes import router as linkedin_analytics_router
    app.include_router(linkedin_analytics_router)
    logger.info("LinkedIn analytics router loaded")
except Exception as e:
    logger.warning("LinkedIn analytics router unavailable: %s", e)

# ── Optional routers (non-critical) ──────────────────────────────────────────

for _name, _import_path, _alias in [
    ("webhook", "src.labat.routers.webhook_routes", "webhook_router"),
    ("comment", "src.labat.routers.comment_routes", "comment_router"),
    ("messenger", "src.labat.routers.messenger_routes", "messenger_router"),
    ("page", "src.labat.routers.page_routes", "page_router"),
    ("content", "src.labat.routers.content_routes", "content_router"),
    ("compliance", "src.labat.routers.compliance_routes", "compliance_router"),
    ("linkedin_posting", "src.labat.routers.linkedin_posting_routes", "linkedin_posting_router"),
]:
    try:
        import importlib
        _mod = importlib.import_module(_import_path)
        app.include_router(_mod.router)
        logger.info("%s router loaded", _name)
    except Exception as e:
        logger.warning("%s router unavailable: %s", _name, e)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "service": "wihy-labat",
        "config": validate_config(),
    }


@app.get("/identity", tags=["Health"])
async def identity():
    return {
        "agent": "labat",
        "service": "wihy-labat",
        "brand_scope": os.getenv("LABAT_BRAND_SCOPE", "all"),
        "role": "paid-media",
        "version": "1.1.0",
    }


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "wihy-labat",
        "description": "Lead Automation, Business Ads & Targeting",
        "routes": [
            "/api/labat/auth/*",
            "/api/labat/ads/*",
            "/api/labat/creatives/*",
            "/api/labat/insights/*",
            "/api/labat/conversions/*",
            "/api/labat/leads/*",
            "/api/labat/ai/*",
            "/api/labat/posts/*",
            "/api/labat/trending/*",
            "/api/labat/automation/*",
            "/api/labat/book-affiliate/*",
            "/api/labat/amazon-ads/*",
            "/api/labat/linkedin/*",
            "/api/labat/page/*",
            "/api/labat/comments/*",
            "/api/labat/messenger/*",
            "/api/labat/webhooks",
            "/api/labat/compliance/*",
            "/api/otaku/master/*",
            "/api/kortney/blog/*",
            "/api/vowels/newsroom/*",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
