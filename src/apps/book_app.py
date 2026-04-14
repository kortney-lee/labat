"""
WIHY Book Service
Cloud Run: wihy-ml-book
Routes: /api/book/*

Handles email lead capture, book delivery, and Stripe checkout
for the What Is Healthy? landing page.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.config import (
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS,
    DEFAULT_PORT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WIHY Book Service starting up")
    yield
    logger.info("WIHY Book Service shutting down")


app = FastAPI(
    title="WIHY Book Service",
    description="Lead capture, email delivery, and Stripe checkout for What Is Healthy?",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# CORS — allow whatishealthy.web.app and local dev
book_origins = CORS_ORIGINS + [
    "https://whatishealthy.web.app",
    "https://whatishealthy.firebaseapp.com",
    "https://whatishealthy.org",
    "https://communitygroceries.com",
    "https://wihy.ai",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=book_origins,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)


# ── Middleware ────────────────────────────────────────────────────────────

try:
    from src.middleware.request_logger import VerboseRequestLoggerMiddleware
    app.add_middleware(VerboseRequestLoggerMiddleware, service_name="wihy-ml-book")
except ImportError:
    pass


@app.middleware("http")
async def enforce_utf8_charset(request: Request, call_next):
    response = await call_next(request)
    ct = response.headers.get("content-type", "")
    if "application/json" in ct and "charset" not in ct:
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


try:
    from src.monitoring import setup_telemetry
    setup_telemetry(app, service_name="wihy-ml-book")
except ImportError:
    pass


# ── Routers ───────────────────────────────────────────────────────────────

try:
    from src.routers.book_routes import router as book_router
    app.include_router(book_router)
    logger.info("Book routes loaded: /api/book/*")
except Exception as e:
    logger.error(f"Book routes failed to load: {e}", exc_info=True)

try:
    from src.routers.launch_routes import router as launch_router
    app.include_router(launch_router)
    logger.info("Launch routes loaded: /api/launch/*")
except Exception as e:
    logger.error(f"Launch routes failed to load: {e}", exc_info=True)


# ── Static Files (serve landing page + assets) ───────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static_whatishealthy")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    logger.info(f"Serving static files from {STATIC_DIR}")


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy", "service": "wihy-ml-book"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", str(DEFAULT_PORT))))
