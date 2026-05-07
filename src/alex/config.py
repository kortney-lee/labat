"""
alex/config.py — ALEX (AI Language Executing X) configuration.

Background service for SEO content generation, keyword discovery,
speaking opportunity scanning, and authority asset building.
"""

import os
import logging

logger = logging.getLogger(__name__)

# ── Internal auth ─────────────────────────────────────────────────────────────

INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()

# ── OpenAI / LLM ─────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ALEX_LLM_MODEL = os.getenv("ALEX_LLM_MODEL", "gpt-4o")
ALEX_LLM_TEMPERATURE = float(os.getenv("ALEX_LLM_TEMPERATURE", "0.5"))

# ── Services integration ─────────────────────────────────────────────────────

SERVICES_URL    = os.getenv("SERVICES_URL", "https://services.wihy.ai")
LABAT_URL       = os.getenv("LABAT_URL", "https://wihy-labat-n4l2vldq3q-uc.a.run.app")
BOOK_SERVICE_URL= os.getenv("BOOK_SERVICE_URL", "https://wihy-ml-book-n4l2vldq3q-uc.a.run.app")
SHANIA_GRAPHICS_URL = os.getenv("SHANIA_GRAPHICS_URL", "https://wihy-shania-graphics-12913076533.us-central1.run.app")
ALEX_BASE_URL = os.getenv("ALEX_BASE_URL", "http://localhost:8080")
ALEX_REPORT_LINK = os.getenv("ALEX_REPORT_LINK", "").strip()
ALEX_REPORT_LINK_WARNING_HOURS = int(os.getenv("ALEX_REPORT_LINK_WARNING_HOURS", "24"))
WIHY_ML_CLIENT_ID = os.getenv("WIHY_ML_CLIENT_ID", "")
WIHY_ML_CLIENT_SECRET = os.getenv("WIHY_ML_CLIENT_SECRET", "")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# ── Brand scope (per-brand instance) ─────────────────────────────────────────

ALEX_BRAND_SCOPE = os.getenv("ALEX_BRAND_SCOPE", "").strip().lower() or None

# Brand-specific SEO domain context for LLM prompts
BRAND_DOMAINS: dict[str, str] = {
    "wihy": (
        "WIHY CORE DOMAINS (discover keywords in these areas):\n"
        "- Processed food ingredients: seed oils, high fructose corn syrup, MSG, "
        "artificial sweeteners, sodium nitrite, BHA/BHT, carrageenan, food dyes\n"
        "- Nutrition: macros, calories, protein, fiber, vitamins, minerals, "
        "gut health, microbiome, anti-inflammatory foods\n"
        "- Fitness: strength training, HIIT, walking, mobility, recovery, "
        "progressive overload, functional fitness\n"
        "- Wellness: sleep, stress, mental health, fasting, hydration, "
        "meal prep, weight management, metabolic health\n"
        "- Health conditions: diabetes, heart disease, inflammation, PCOS, "
        "autoimmune, fatty liver, blood sugar\n"
        "- Products: protein powder, creatine, pre-workout, meal replacement, "
        "energy drinks, supplements, organic food\n"
        "- School wellness: school lunch, child nutrition, kids healthy snacks, "
        "cafeteria food, student wellness programs\n"
    ),
    "communitygroceries": (
        "COMMUNITY GROCERIES CORE DOMAINS (discover keywords in these areas):\n"
        "- Meal planning: weekly meal plans, family dinner ideas, budget meals, "
        "batch cooking, meal prep, one-pot recipes, slow cooker meals\n"
        "- Grocery shopping: grocery list, smart shopping, seasonal produce, "
        "bulk buying, food budget, store deals, coupon strategies\n"
        "- Family nutrition: feeding kids, picky eaters, toddler meals, "
        "school lunch ideas, family-friendly recipes, kid-approved snacks\n"
        "- Food waste: reduce food waste, leftover recipes, food storage tips, "
        "freezer meals, pantry staples, shelf life guide\n"
        "- Budget-friendly health: eating healthy on a budget, cheap protein sources, "
        "affordable superfoods, dollar store healthy finds\n"
        "- Community food: food deserts, community gardens, food banks, "
        "neighborhood grocery cooperatives, local farms\n"
    ),
    "vowels": (
        "VOWELS / WHAT IS HEALTHY BOOK CORE DOMAINS (discover keywords in these areas):\n"
        "- Health literacy: understanding nutrition labels, food marketing myths, "
        "health misinformation, science-based nutrition, evidence-based health\n"
        "- Book topics: what is healthy, food industry secrets, nutrition research, "
        "health education, family health guide, wellness book\n"
        "- Children health education: teaching kids about nutrition, health class, "
        "age-appropriate health education, family wellness activities\n"
        "- Food industry: food lobbying, marketing to children, processed food industry, "
        "food additive regulation, nutrition science vs marketing\n"
        "- Research: PubMed studies, clinical nutrition, peer-reviewed health research, "
        "meta-analysis nutrition, evidence-based diet\n"
    ),
    "childrennutrition": (
        "CHILDREN NUTRITION CORE DOMAINS (discover keywords in these areas):\n"
        "- School meals: school lunch program, cafeteria nutrition, USDA school meals, "
        "National School Lunch Program, school breakfast program\n"
        "- Child dietary needs: growing children nutrition, pediatric nutrition, "
        "childhood obesity prevention, healthy kids meals, toddler nutrition\n"
        "- Student wellness: school wellness policy, physical education nutrition, "
        "student health programs, health education curriculum\n"
        "- Healthy snacks for kids: after-school snacks, healthy lunchbox ideas, "
        "sugar-free kids snacks, nut-free school snacks\n"
        "- Parental guidance: feeding picky eaters, introducing new foods, "
        "meal planning for families, kids cooking classes\n"
    ),
    "parentingwithchrist": (
        "PARENTING WITH CHRIST CORE DOMAINS (discover keywords in these areas):\n"
        "- Faith-based wellness: Christian health stewardship, body as temple, "
        "biblical nutrition, faith and health, spiritual wellness\n"
        "- Family health: Christian family meal planning, church health ministry, "
        "family devotional meals, faith-based parenting health\n"
        "- Community wellness: church wellness programs, faith-based fitness, "
        "Christian cooking groups, church garden ministry\n"
        "- Parenting nutrition: feeding children with faith, gratitude meals, "
        "teaching kids healthy habits, family table fellowship\n"
        "- Ministry: health ministry resources, church kitchen guidelines, "
        "vacation bible school healthy snacks, youth group wellness\n"
    ),
}

# Brand display names for LLM prompts
BRAND_DISPLAY_NAMES: dict[str, str] = {
    "wihy": "WIHY (What Is Healthy for You)",
    "communitygroceries": "Community Groceries",
    "vowels": "Vowels / What Is Healthy (the book)",
    "childrennutrition": "Children Nutrition",
    "parentingwithchrist": "Parenting With Christ",
}

# Brand site URLs for CTAs
BRAND_SITE_URLS: dict[str, str] = {
    "wihy": "wihy.ai",
    "communitygroceries": "communitygroceries.com",
    "vowels": "vowelsbook.com",
    "childrennutrition": "childrennutrition.org",
    "parentingwithchrist": "parentingwithchrist.com",
}

# Trend source toggles
ENABLE_GOOGLE_TRENDS = os.getenv("ALEX_ENABLE_GOOGLE_TRENDS", "true").lower() == "true"
ENABLE_REDDIT_TRENDS = os.getenv("ALEX_ENABLE_REDDIT_TRENDS", "true").lower() == "true"
ENABLE_X_TRENDS = os.getenv("ALEX_ENABLE_X_TRENDS", "false").lower() == "true"

# Hashtag tier defaults (high/mid/niche)
HASHTAG_TIER_HIGH_COUNT = int(os.getenv("ALEX_HASHTAG_TIER_HIGH", "5"))
HASHTAG_TIER_MID_COUNT = int(os.getenv("ALEX_HASHTAG_TIER_MID", "7"))
HASHTAG_TIER_NICHE_COUNT = int(os.getenv("ALEX_HASHTAG_TIER_NICHE", "5"))

# ── Background task intervals (seconds) ──────────────────────────────────────

# Keyword discovery: scan search console + user queries for new keywords
KEYWORD_DISCOVERY_INTERVAL = int(os.getenv("ALEX_KEYWORD_INTERVAL", "21600"))  # 6 hours

# Page refresh: check for stale/underperforming pages and regenerate
PAGE_REFRESH_INTERVAL = int(os.getenv("ALEX_PAGE_REFRESH_INTERVAL", "86400"))  # 24 hours

# Opportunity scan: find speaking/partnership opportunities
OPPORTUNITY_SCAN_INTERVAL = int(os.getenv("ALEX_OPPORTUNITY_INTERVAL", "86400"))  # 24 hours

# Analytics ingestion: pull page performance metrics
ANALYTICS_INTERVAL = int(os.getenv("ALEX_ANALYTICS_INTERVAL", "3600"))  # 1 hour

# Content queue processing: generate drafts for queued keywords
CONTENT_QUEUE_INTERVAL = int(os.getenv("ALEX_CONTENT_QUEUE_INTERVAL", "14400"))  # 4 hours

# ── Thresholds ────────────────────────────────────────────────────────────────

# Pages with CTR below this are candidates for refresh
PAGE_CTR_REFRESH_THRESHOLD = float(os.getenv("ALEX_CTR_THRESHOLD", "0.02"))  # 2%

# Minimum priority score for a keyword to auto-generate a page
AUTO_GENERATE_MIN_PRIORITY = int(os.getenv("ALEX_AUTO_GEN_MIN_PRIORITY", "7"))

# Max pages to generate per content queue cycle
MAX_PAGES_PER_CYCLE = int(os.getenv("ALEX_MAX_PAGES_PER_CYCLE", "3"))

# Max keywords to discover per cycle
MAX_KEYWORDS_PER_CYCLE = int(os.getenv("ALEX_MAX_KEYWORDS_PER_CYCLE", "10"))

# ── Auth service (notifications) ─────────────────────────────────────────────

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "https://auth.wihy.ai")

# ── Peer services (for health monitoring) ─────────────────────────────────────

PEER_SERVICES = {
    "wihy-ml": {
        "url": os.getenv("WIHY_ML_URL", "https://ml.wihy.ai"),
        "health_endpoint": "/health",
    },
    "services": {
        "url": os.getenv("SERVICES_URL", "https://services.wihy.ai"),
        "health_endpoint": "/health",
    },
}

# ── Agent identity ────────────────────────────────────────────────────────────

ALEX_AGENT_ID = "alex-seo-agent"
ALEX_AGENT_NAME = "ALEX"
ALEX_AGENT_VERSION = "1.0.0"

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config() -> dict:
    """Check ALEX service configuration readiness."""
    checks = {
        "internal_admin_token": bool(INTERNAL_ADMIN_TOKEN),
        "openai_api_key": bool(OPENAI_API_KEY),
        "services_url": bool(SERVICES_URL),
        "client_credentials": bool(WIHY_ML_CLIENT_ID and WIHY_ML_CLIENT_SECRET),
    }

    for check_name, ok in checks.items():
        if not ok:
            logger.warning("ALEX config check FAILED: %s", check_name)
        else:
            logger.info("ALEX config check OK: %s", check_name)

    return checks
