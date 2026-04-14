"""
labat/config.py — Configuration for the LABAT Meta/Facebook integration.

All sensitive values are read from environment variables (set via Cloud Run
secrets or .env locally).
"""

import os
import logging

logger = logging.getLogger(__name__)

# ── Meta Graph API ────────────────────────────────────────────────────────────

META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v21.0")
META_GRAPH_BASE_URL = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"

# ── Shania app — Page management (posts, feed, comments, messenger) ───────────
# App ID: 982695521085427

SHANIA_APP_ID = os.getenv("SHANIA_APP_ID", "")
SHANIA_APP_SECRET = os.getenv("SHANIA_APP_SECRET", "").strip()
SHANIA_PAGE_ACCESS_TOKEN = os.getenv("SHANIA_PAGE_ACCESS_TOKEN", "").strip()
SHANIA_LONG_LIVED_USER_TOKEN = os.getenv("SHANIA_LONG_LIVED_USER_TOKEN", "").strip()

# ── LABAT app — Ads, campaigns, insights, conversions ────────────────────────
# App ID: 2217823522290444

META_APP_ID = os.getenv("META_APP_ID", "")        # LABAT app
META_APP_SECRET = os.getenv("META_APP_SECRET", "")  # LABAT app

# Page identity — per-brand page IDs are in src.labat.brands (loaded from env vars)
# META_PAGE_ID removed — use brands.get_page_id(brand) instead

# Legacy — kept for backward compat; prefer SHANIA_PAGE_ACCESS_TOKEN
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "")

# System user (server-to-server ads automation via LABAT app)
META_SYSTEM_USER_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN", "")

# Ad account
META_AD_ACCOUNT_ID = os.getenv("META_AD_ACCOUNT_ID", "")  # format: act_123456789
META_BUSINESS_ID = os.getenv("META_BUSINESS_ID", "")

# ── Webhook ───────────────────────────────────────────────────────────────────

META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "").strip()

# ── Internal auth (same pattern as engagement service) ────────────────────────

INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()

# ── Timeouts ──────────────────────────────────────────────────────────────────

META_API_TIMEOUT = float(os.getenv("META_API_TIMEOUT", "30"))
META_INSIGHTS_TIMEOUT = float(os.getenv("META_INSIGHTS_TIMEOUT", "60"))

# ── LinkedIn API (Shania posting + LABAT analytics) ──────────────────────────
# Access token generated from LinkedIn Developer Portal (no OAuth redirect).
# https://www.linkedin.com/developers/apps → Auth → Generate Access Token

LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()

# Organization / company page ID (numeric, from admin dashboard URL)
LINKEDIN_ORG_ID = os.getenv("LINKEDIN_ORG_ID", "").strip()

LINKEDIN_API_VERSION = "v2"
LINKEDIN_BASE_URL = f"https://api.linkedin.com/{LINKEDIN_API_VERSION}"

LINKEDIN_API_TIMEOUT = float(os.getenv("LINKEDIN_API_TIMEOUT", "30"))

# ── Rate limit defaults ──────────────────────────────────────────────────────

# Meta Marketing API: ~200 calls/hour for standard access
ADS_RATE_LIMIT_PER_HOUR = int(os.getenv("ADS_RATE_LIMIT_PER_HOUR", "180"))
PAGE_RATE_LIMIT_PER_HOUR = int(os.getenv("PAGE_RATE_LIMIT_PER_HOUR", "4700"))

# LinkedIn API: 300 calls/hour (Developer Standard access)
LINKEDIN_RATE_LIMIT_PER_HOUR = int(os.getenv("LINKEDIN_RATE_LIMIT_PER_HOUR", "280"))

# ── Gemini (intelligence & content engine) ──────────────────────────────────

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")).strip()
INTELLIGENCE_MODEL = os.getenv("LABAT_INTELLIGENCE_MODEL", "gemini-2.5-flash")
CONTENT_MODEL = os.getenv("LABAT_CONTENT_MODEL", "gemini-2.5-flash")

# ── OpenAI (legacy fallback) ─────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def validate_config() -> dict:
    """Return a dict of config readiness checks (key → bool)."""
    from src.labat.brands import BRAND_PAGE_IDS
    return {
        "shania_app": bool(SHANIA_APP_ID and SHANIA_APP_SECRET),
        "shania_page_token": bool(SHANIA_PAGE_ACCESS_TOKEN),
        "labat_app": bool(META_APP_ID and META_APP_SECRET),
        "system_user": bool(META_SYSTEM_USER_TOKEN),
        "ad_account": bool(META_AD_ACCOUNT_ID),
        "brand_pages": all(BRAND_PAGE_IDS.values()),
        "webhook": bool(META_WEBHOOK_VERIFY_TOKEN),
        "admin_auth": bool(INTERNAL_ADMIN_TOKEN),
        "gemini": bool(GEMINI_API_KEY),
        "linkedin": bool(LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORG_ID),
    }
