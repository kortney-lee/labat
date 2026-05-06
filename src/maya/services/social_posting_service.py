"""
social_posting_service.py — Shania auto-posting cycle.

Periodically generates branded social media content by calling
Shania Graphics' orchestrate-post pipeline, which:
  1. Generates a caption + hashtags via Gemini
  2. Creates a unique AI image via Imagen 4.0
  3. Uploads to GCS
  4. Publishes directly to Facebook and Instagram

Shania owns all social posting. Alex provides SEO signals when called.

LAUNCH MODE (env: SOCIAL_POSTING_LAUNCH_MODE=true)
  Prioritises launch hype topics and increases posting frequency.
  Disable after launch by removing the env var or setting to false.
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

# X (Twitter) posting credentials — same keys used by engagement service
_TWITTER_API_KEY             = (os.getenv("TWITTER_API_KEY", "") or "").strip()
_TWITTER_API_SECRET          = (os.getenv("TWITTER_API_SECRET", "") or "").strip()
_TWITTER_ACCESS_TOKEN        = (os.getenv("TWITTER_ACCESS_TOKEN", "") or "").strip()
_TWITTER_ACCESS_TOKEN_SECRET = (os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "") or "").strip()
X_POSTING_ENABLED = os.getenv("X_POSTING_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")

from src.maya.services.social_template_registry import (
    get_template_driven_brands,
    pick_structured_social_topics,
)

logger = logging.getLogger("shania.social_posting")

SHANIA_GRAPHICS_URL = os.getenv(
    "SHANIA_GRAPHICS_URL",
    "https://wihy-shania-graphics-12913076533.us-central1.run.app",
)
INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()
SOCIAL_POSTING_DISABLED = os.getenv("SOCIAL_POSTING_DISABLED", "true").strip().lower() in ("1", "true", "yes", "on")

# Posting mode:
#   auto        — Shania generates AI images and posts them (legacy, default)
#   bucket-only — Shania ONLY posts pre-approved photos/graphics from the GCS
#                 asset-library bucket (uploaded to asset-library/{brand}/approved/).
#                 No AI image generation. If no approved assets exist, the cycle is skipped.
POSTING_MODE = os.getenv("SHANIA_POSTING_MODE", "auto").strip().lower()
BUCKET_ONLY_MODE = POSTING_MODE == "bucket-only"

# Launch mode: prioritise hype topics, post more often
LAUNCH_MODE = os.getenv("SOCIAL_POSTING_LAUNCH_MODE", "").strip().lower() in ("true", "1", "yes")

# Posting interval: 3 hours in launch mode, 4 hours normal
SOCIAL_POSTING_INTERVAL = int(os.getenv(
    "SHANIA_SOCIAL_POSTING_INTERVAL",
    "10800" if LAUNCH_MODE else "14400",
))

# Posts per cycle: 2 in launch mode, 1 normal (can be overridden by env)
MAX_POSTS_PER_CYCLE = int(os.getenv(
    "SHANIA_MAX_POSTS_PER_CYCLE",
    "2" if LAUNCH_MODE else "1",
))

# Safety guard: skip back-to-back runs (loop + manual trigger overlap)
MIN_RUN_GAP_SECONDS = int(os.getenv(
    "SHANIA_SOCIAL_MIN_RUN_GAP_SECONDS",
    str(max(900, SOCIAL_POSTING_INTERVAL // 2)),
))

# Platforms to publish on
# All active brands use the same default platform set.
# Otaku Lounge is excluded via brand launch controls.
DEFAULT_PLATFORMS = ["facebook", "instagram", "threads"]
BRAND_PLATFORMS: Dict[str, List[str]] = {
    "wihy":               ["facebook", "instagram", "threads"],
    "communitygroceries": ["facebook", "instagram", "threads"],
    "childrennutrition":  ["facebook", "instagram", "threads"],
    "parentingwithchrist": ["facebook", "instagram", "threads"],
    "vowels":             ["facebook", "instagram", "threads"],
}


def _platforms_for_brand(brand: str) -> List[str]:
    """Return the list of platforms a brand should be posted on."""
    return BRAND_PLATFORMS.get(brand, DEFAULT_PLATFORMS)

# ── LAUNCH HYPE topics — higher priority during launch mode ──────────────
LAUNCH_TOPICS: List[Dict[str, str]] = [
    # ── Eden by WIHY launch hype ──
    {"prompt": "Introducing Eden by WIHY — your AI health companion that turns what you think into what you do. Ask any health question, get research-backed answers from 48M+ studies, and walk away with a real plan. wihy.ai", "brand": "wihy"},
    {"prompt": "Eden doesn't just give you information — it gives you decisions. Ask Eden what to eat, scan your food, build a meal plan, and send your grocery list to Instacart in one flow. That's Eden by WIHY. wihy.ai", "brand": "wihy"},
    {"prompt": "Other apps track your calories. Eden by WIHY explains them, connects them to your goals, and tells you exactly what to do next. From thought to action — that's the difference. wihy.ai", "brand": "wihy"},
    {"prompt": "Ask Eden: 'Is this healthy for me?' It scans the barcode, reads the label, detects additives and carcinogens, and tells you what to buy instead. No guesswork. Real science. Eden by WIHY. wihy.ai", "brand": "wihy"},
    {"prompt": "Eden by WIHY builds you a full 7-day meal plan in under 30 seconds — personalized to your goals, your diet, your budget — then turns it into a grocery list you can send straight to Walmart or Instacart. wihy.ai", "brand": "wihy"},
    {"prompt": "Your doctor got 19 hours of nutrition training in medical school. Eden by WIHY was trained on 48 million peer-reviewed research articles. Ask Eden what to eat. wihy.ai", "brand": "wihy"},
    {"prompt": "Eden by WIHY connects three things no other platform does: research, real food, and your actual behavior. Then it turns that into one clear action. Ask Eden. Eat better. Live healthier. wihy.ai", "brand": "wihy"},
    {"prompt": "Stop Googling your health questions and getting 10 conflicting answers. Eden by WIHY gives you one answer — backed by real research — and a plan to act on it. wihy.ai", "brand": "wihy"},
    {"prompt": "Eden isn't another calorie counter. It's a decision engine for your health. It watches your patterns, learns your habits, and tells you exactly what to do next. Eden by WIHY — wihy.ai", "brand": "wihy"},
    {"prompt": "The food industry spends $14 billion a year marketing processed food as healthy. Eden by WIHY was built to fight back — with 48 million research studies and a barcode scanner. wihy.ai", "brand": "wihy"},
    {"prompt": "Scan any food with Eden. It detects hidden sugars, additives, carcinogens, and allergens — then suggests a better option. This is what food transparency actually looks like. Eden by WIHY. wihy.ai", "brand": "wihy"},
    {"prompt": "Eden by WIHY learns your eating habits, cravings, and patterns — then tells you what's coming before it happens. Predictive health coaching that actually knows you. wihy.ai", "brand": "wihy"},
    # ── Cora by Community Groceries launch hype ──
    {"prompt": "Introducing Cora by Community Groceries — your intelligent grocery and pantry companion. Cora builds your grocery list from your meal plan, tracks your pantry, and connects to Instacart, Walmart, and Amazon in one flow. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Most grocery apps are built around transactions. Cora is built around your family. It knows what's in your pantry, builds your list automatically, and gets it to your door without the stress. Plan smarter. Shop easier. Waste less. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora turns your meal plan into a grocery list and sends it straight to Walmart or Instacart. Thought → Grocery List → Checkout. That's Cora by Community Groceries. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "You don't just struggle with what to eat. You struggle with what you already have, what to buy, and how to stay organized. Cora by Community Groceries solves all of it in one place. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Scan your receipt with Cora and it instantly builds your pantry inventory. Know exactly what you have, what you're running low on, and what to buy next. No duplicate purchases. No forgotten ingredients. Cora by Community Groceries. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora builds your grocery list automatically from your meal plan, pantry gaps, budget, and family preferences. No more guessing. No more overbuying. Just smarter, faster shopping. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "The average family wastes $1,500 of food every year. Cora by Community Groceries helps you use what you already have — pantry-first meal suggestions, reorder reminders, and smarter shopping built in. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora by Community Groceries connects your whole household. Shared grocery lists. Shared pantry visibility. Family meal coordination. Everyone on the same page — from planning to purchase. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Every family deserves access to healthy food they can actually afford. Cora uses budget-aware recommendations, pantry-first suggestions, and direct retailer connections to make it happen. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora doesn't just help you shop. It helps you think about food differently — what you have, what you need, what you can cook tonight. Intelligent grocery and pantry management for real households. communitygroceries.com", "brand": "communitygroceries"},
]

# ── Evergreen topics — ongoing educational content ──────────────────────
EVERGREEN_TOPICS: List[Dict[str, str]] = [
    # wihy — superhuman optimization + Eden product tie-ins
    {"prompt": "Do these 5 things every morning and your body will perform like a machine: cold shower, sunlight exposure, protein-first meal, breathwork, movement. Ask Eden by WIHY to build you the exact meal that starts this routine right. wihy.ai", "brand": "wihy"},
    {"prompt": "Your VO2 max is the single best predictor of how long you'll live — better than cholesterol, blood pressure, or any blood test. Eden by WIHY can build you a fitness + nutrition plan to improve it starting today. wihy.ai", "brand": "wihy"},
    {"prompt": "Want to age slower? Zone 2 cardio 150 min/week. Strength training 3x/week. 7+ hours sleep. High protein diet. Ask Eden by WIHY to build the exact meal plan and workout schedule for this protocol. wihy.ai", "brand": "wihy"},
    {"prompt": "Time-restricted eating (8-hour window) activates autophagy — your body literally repairs damaged cells. Eden by WIHY can build your entire fasting schedule and tell you exactly what to eat when you break it. wihy.ai", "brand": "wihy"},
    {"prompt": "Creatine isn't just for bodybuilders. Research shows 5g/day improves memory, reduces brain fog, and protects against neurodegeneration. Eden by WIHY connects supplements to your full health picture. wihy.ai", "brand": "wihy"},
    {"prompt": "Stop counting calories. Start counting protein — 1g per pound of body weight. This single change transforms body composition faster than any diet. Ask Eden by WIHY to build your protein-first meal plan. wihy.ai", "brand": "wihy"},
    {"prompt": "Sauna 4x per week reduces all-cause mortality by 40%. But what you eat before and after the sauna matters just as much. Ask Eden by WIHY what to eat to maximize recovery. wihy.ai", "brand": "wihy"},
    {"prompt": "Your body replaces 330 billion cells every day. Feed it the right raw materials and you become a new, upgraded version of yourself every 90 days. Eden by WIHY tells you exactly what those raw materials are. wihy.ai", "brand": "wihy"},
    {"prompt": "Grip strength predicts all-cause mortality better than blood pressure. The stronger your grip, the longer you live. Eden by WIHY builds you the workout + nutrition protocol to train it. wihy.ai", "brand": "wihy"},
    {"prompt": "10 minutes of cold exposure increases dopamine by 250% for hours. Eden by WIHY connects your daily habits — sleep, food, movement, recovery — into one personalized system. wihy.ai", "brand": "wihy"},
    {"prompt": "Eden by WIHY tracks your eating patterns, learns your cravings, and predicts your habits before they happen. This is what personalized health actually looks like — not a one-size-fits-all app. wihy.ai", "brand": "wihy"},
    {"prompt": "You don't need more health information. You need better decisions. Eden by WIHY takes 48M research studies and turns them into one clear action for YOUR body, YOUR goals, TODAY. wihy.ai", "brand": "wihy"},
    {"prompt": "Eden by WIHY doesn't just scan your food — it explains it, connects it to your goals, and tells you what to buy instead. From barcode to decision in seconds. wihy.ai", "brand": "wihy"},
    {"prompt": "Thought → Plan → Checkout. Ask Eden what to eat. Get a 7-day meal plan. Send your grocery list to Instacart, Walmart, or Amazon. Eden by WIHY closes the loop between knowing and doing. wihy.ai", "brand": "wihy"},
    {"prompt": "Elite athletes sleep 9-10 hours because muscle grows during deep sleep, not in the gym. Ask Eden by WIHY to optimize your nutrition for recovery — what to eat before bed matters more than your protein shake. wihy.ai", "brand": "wihy"},
    # communitygroceries — Cora product features, pantry intelligence, smarter shopping
    {"prompt": "Cora by Community Groceries tracks your pantry automatically. Scan a receipt — Cora logs everything. It tells you what you already have, what you're running low on, and what to reorder. No more buying things you already own. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora builds your grocery list from your meal plan — automatically. It checks your pantry first, skips what you already have, and only lists what you actually need. Smarter. Faster. Less waste. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora connects to Instacart, Walmart, Amazon, and Kroger. Build your list in Cora, send it to your preferred retailer, and your groceries are on the way. Thought → List → Checkout. That's the Cora flow. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Most people don't know what's in their own pantry. Cora does. Receipt scanning, automatic inventory tracking, low stock reminders — Cora makes your household pantry intelligent. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora is budget-aware. It knows your household food budget, suggests meals built around what you already have, and recommends the most cost-effective shopping path. Healthy food doesn't have to be expensive when you shop smarter. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Shared grocery lists. Shared pantry. One household, everyone connected. Cora by Community Groceries keeps the whole family coordinated — from meal planning to the final purchase. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "The average American household wastes $1,500 of food per year. Cora fixes that with pantry-first meal planning, reorder reminders, and smart consumption tracking. Use what you have. Buy only what you need. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora doesn't just help you shop — it helps you organize your food life. Pantry inventory, grocery lists, meal coordination, retailer connections, and household budgeting — all in one intelligent platform. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Food access is a real problem. Cora by Community Groceries is built to make smarter, healthier grocery decisions accessible to every household — regardless of budget, neighborhood, or schedule. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora learns your household. It knows what your family eats, what you always run out of, and what you never finish. Over time, it builds a smarter grocery experience personalized to your actual habits. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "With Cora, your meal plan and your grocery list are the same thing. Plan your week, Cora checks your pantry, builds the list, and sends it to Walmart or Instacart. Dinner is handled. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Cora by Community Groceries is part of a bigger mission: smarter food access for every community. Pantry intelligence, budget-aware shopping, and real-world fulfillment — built for households that need it most. communitygroceries.com", "brand": "communitygroceries"},
    # childrennutrition — picky eaters, kids nutrition tips, making healthy food fun
    {"prompt": "5 proven strategies to get picky eaters to try new foods without a meltdown", "brand": "childrennutrition"},
    {"prompt": "Why your toddler refuses vegetables and the one trick that actually works", "brand": "childrennutrition"},
    {"prompt": "Hidden veggie recipes that even the pickiest kids will eat — parent tested", "brand": "childrennutrition"},
    {"prompt": "The picky eater phase is normal — here's when to worry and when to relax", "brand": "childrennutrition"},
    {"prompt": "How to introduce new foods to kids using the 'food bridge' method", "brand": "childrennutrition"},
    {"prompt": "Healthy school lunch ideas that picky eaters will actually eat", "brand": "childrennutrition"},
    {"prompt": "3 simple swaps to reduce sugar in your child's diet starting today", "brand": "childrennutrition"},
    {"prompt": "Why forcing kids to eat backfires — and what to do instead", "brand": "childrennutrition"},
    {"prompt": "Fun ways to teach kids about nutrition without making food the enemy", "brand": "childrennutrition"},
    {"prompt": "Smoothie hacks for picky eaters: how to sneak in fruits and veggies kids won't notice", "brand": "childrennutrition"},
    # parentingwithchrist — teaching Jesus's way: fasting, discipline, self-control, what the world won't teach
    {"prompt": "Jesus fasted 40 days — why we should teach our children the power and purpose of fasting", "brand": "parentingwithchrist"},
    {"prompt": "The Bible says 'train up a child' — why discipline is an act of love, not punishment", "brand": "parentingwithchrist"},
    {"prompt": "Impulse control: what Jesus modeled when tempted and how to teach it to your kids", "brand": "parentingwithchrist"},
    {"prompt": "The world says 'treat yourself' — Jesus says 'deny yourself.' How to raise kids who understand the difference", "brand": "parentingwithchrist"},
    {"prompt": "Teaching kids delayed gratification through Scripture — a discipline the world has forgotten", "brand": "parentingwithchrist"},
    {"prompt": "Why self-discipline is a fruit of the Spirit and how to nurture it in your children", "brand": "parentingwithchrist"},
    {"prompt": "Jesus woke up early to pray — how to build morning devotion habits with your kids", "brand": "parentingwithchrist"},
    {"prompt": "The lost art of saying 'no' — raising children with boundaries in an anything-goes culture", "brand": "parentingwithchrist"},
    {"prompt": "Fasting isn't just for adults — age-appropriate ways to introduce fasting to your family", "brand": "parentingwithchrist"},
    {"prompt": "Jesus chose 12, not 12,000 — teaching kids quality friendships over social media popularity", "brand": "parentingwithchrist"},
    # vowels — nutrition education, food industry facts, data-driven health truths
    {"prompt": "A bowl of Lucky Charms has 12g of sugar, almost zero protein, and artificial food dyes linked to hyperactivity in children. This is what we're feeding kids for breakfast. The nutrition label doesn't lie — we just don't read it", "brand": "vowels"},
    {"prompt": "Fruit juice is marketed as healthy but a glass of apple juice has as much sugar as a can of Coke — 39g. The fiber was removed. The vitamins are synthetic. Eat the fruit. Skip the juice", "brand": "vowels"},
    {"prompt": "The average American eats 77 grams of sugar per day. The recommended limit is 25g for women and 36g for men. That means most people eat 2-3x the safe amount without realizing it", "brand": "vowels"},
    {"prompt": "Yogurt marketed to kids contains more sugar per ounce than ice cream. GoGurt has 7g of sugar in a single tube. That's a dessert marketed as a health food", "brand": "vowels"},
    {"prompt": "'Whole grain' on the label doesn't mean it's healthy. Many 'whole grain' breads list enriched flour as the first ingredient and contain high fructose corn syrup. Read past the front of the box", "brand": "vowels"},
    {"prompt": "Sports drinks were designed for elite athletes exercising 90+ minutes. Your child playing 30 minutes of soccer doesn't need 34g of sugar and artificial dyes. Water works", "brand": "vowels"},
    {"prompt": "The food industry spends $14 billion per year marketing to consumers. $1.8 billion targets children directly. They spend more selling junk than the government spends teaching nutrition", "brand": "vowels"},
    {"prompt": "Granola bars are the ultimate health food illusion. Most contain as much sugar as a candy bar — just wrapped in oats and marketed with pictures of nature. Check the label", "brand": "vowels"},
    {"prompt": "processed cheese like Kraft Singles is only 51% actual cheese. The rest is water, milk protein concentrate, sodium citrate, and food coloring. It can't legally be called 'cheese' — it's 'cheese product'", "brand": "vowels"},
    {"prompt": "Subway's 'fresh' bread contained azodicarbonamide — the same chemical used to make yoga mats. It was only removed after public outcry. What's still in your 'fresh' food that nobody is talking about?", "brand": "vowels"},
    {"prompt": "Baby food pouches marketed as organic still contain 10-15g of sugar per pouch. Organic cane sugar is still sugar. Your baby's first foods are training their palate to crave sweetness", "brand": "vowels"},
    {"prompt": "The average school lunch in America contains 30% more sodium than recommended. Chicken nuggets, pizza, and chocolate milk — this is institutional nutrition failure, not a balanced meal", "brand": "vowels"},
]

TEMPLATE_DRIVEN_BRANDS = get_template_driven_brands()


def _select_topics(count: int) -> List[Dict[str, str]]:
    """Pick topics for this cycle.

    In launch mode: 75% launch hype, 25% evergreen.
    Normal mode: 100% evergreen (launch topics still mixed in at low rate).
    """
    structured = pick_structured_social_topics(count=count, brands=sorted(TEMPLATE_DRIVEN_BRANDS))
    legacy_launch = [item for item in LAUNCH_TOPICS if item["brand"] not in TEMPLATE_DRIVEN_BRANDS]
    legacy_evergreen = [item for item in EVERGREEN_TOPICS if item["brand"] not in TEMPLATE_DRIVEN_BRANDS]

    if LAUNCH_MODE and LAUNCH_TOPICS:
        n_launch = max(1, int(count * 0.75))
        n_evergreen = count - n_launch
        picks: List[Dict[str, str]] = []

        if structured:
            picks.extend(structured[: min(n_launch, len(structured), count)])

        if len(picks) < n_launch and legacy_launch:
            picks += random.sample(legacy_launch, min(n_launch - len(picks), len(legacy_launch)))

        if n_evergreen > 0:
            picks += random.sample(legacy_evergreen, min(n_evergreen, len(legacy_evergreen)))

        if len(picks) < count and structured:
            remaining_structured = [item for item in structured if item not in picks]
            picks.extend(remaining_structured[: max(0, count - len(picks))])

        return picks[:count]

    # Normal mode — prefer structured template prompts for supported brands.
    picks = structured[: min(count, len(structured))]
    remaining = count - len(picks)

    if remaining > 0 and legacy_evergreen:
        extra = random.sample(legacy_evergreen, min(remaining, len(legacy_evergreen)))
        picks.extend(extra)
        remaining = count - len(picks)

    if remaining > 0 and legacy_launch:
        extra = random.sample(legacy_launch, min(remaining, len(legacy_launch)))
        picks.extend(extra)

    return picks[:count]


async def _post_to_x(client: httpx.AsyncClient, text: str, brand: str) -> bool:
    """Post a tweet to @Wihyai on X using OAuth 1.0a. Returns True on success."""
    if not X_POSTING_ENABLED:
        return False
    if not all([_TWITTER_API_KEY, _TWITTER_API_SECRET, _TWITTER_ACCESS_TOKEN, _TWITTER_ACCESS_TOKEN_SECRET]):
        logger.warning("X posting skipped — Twitter credentials not configured")
        return False

    # Import OAuth helper from engagement service
    try:
        from src.maya.services.engagement_poster_service import _twitter_oauth1_header
    except ImportError:
        logger.error("X posting: could not import OAuth helper")
        return False

    # X hard limit is 280 chars
    tweet = text[:277] + "..." if len(text) > 280 else text

    url = "https://api.twitter.com/2/tweets"
    try:
        auth = _twitter_oauth1_header("POST", url, {})
        r = await client.post(
            url,
            headers={"Authorization": auth, "Content-Type": "application/json"},
            json={"text": tweet},
            timeout=15,
        )
        data = r.json()
        if r.status_code == 201 and data.get("data", {}).get("id"):
            tweet_id = data["data"]["id"]
            logger.info("X post published brand=%s tweet_id=%s text=%s", brand, tweet_id, tweet[:60])
            return True
        logger.warning("X post failed brand=%s status=%d body=%s", brand, r.status_code, str(data)[:200])
        return False
    except Exception as e:
        logger.error("X posting error brand=%s: %s", brand, e)
        return False


class SocialPostingService:
    """Background service that auto-generates social posts on a timer."""

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._cycle_running = False
        self._skipped_runs = 0
        self._total_posts_published = 0
        self._total_errors = 0
        self._last_run: Optional[datetime] = None

    def status(self) -> dict:
        return {
            "running": self._running,
            "posting_disabled": SOCIAL_POSTING_DISABLED,
            "posting_mode": POSTING_MODE,
            "launch_mode": LAUNCH_MODE,
            "brand_platforms": BRAND_PLATFORMS,
            "total_posts_published": self._total_posts_published,
            "total_errors": self._total_errors,
            "skipped_runs": self._skipped_runs,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "interval_seconds": SOCIAL_POSTING_INTERVAL,
            "min_run_gap_seconds": MIN_RUN_GAP_SECONDS,
            "posts_per_cycle": MAX_POSTS_PER_CYCLE,
            "launch_topics": len(LAUNCH_TOPICS),
            "evergreen_topics": len(EVERGREEN_TOPICS),
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "SocialPostingService started (interval=%ds, posts_per_cycle=%d)",
            SOCIAL_POSTING_INTERVAL, MAX_POSTS_PER_CYCLE,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("SocialPostingService stopped")

    async def run_once(self) -> Dict[str, Any]:
        """Run a single posting cycle (callable manually or by the loop)."""
        now = datetime.now(timezone.utc)
        if SOCIAL_POSTING_DISABLED:
            logger.warning("Shania: Skipping cycle because SOCIAL_POSTING_DISABLED is enabled")
            self._skipped_runs += 1
            return {
                "cycle": "social_posting",
                "posts_published": 0,
                "errors": 0,
                "skipped": True,
                "reason": "posting_disabled",
                "timestamp": now.isoformat(),
            }

        if self._cycle_running:
            self._skipped_runs += 1
            logger.warning("Shania: Skipping cycle because another cycle is already running")
            return {
                "cycle": "social_posting",
                "posts_published": 0,
                "errors": 0,
                "skipped": True,
                "reason": "already_running",
                "timestamp": now.isoformat(),
            }

        if self._last_run is not None:
            elapsed = (now - self._last_run).total_seconds()
            if elapsed < MIN_RUN_GAP_SECONDS:
                self._skipped_runs += 1
                logger.warning(
                    "Shania: Skipping cycle due to cooldown (elapsed=%ss < min_gap=%ss)",
                    int(elapsed),
                    MIN_RUN_GAP_SECONDS,
                )
                return {
                    "cycle": "social_posting",
                    "posts_published": 0,
                    "errors": 0,
                    "skipped": True,
                    "reason": "cooldown",
                    "elapsed_seconds": int(elapsed),
                    "min_run_gap_seconds": MIN_RUN_GAP_SECONDS,
                    "timestamp": now.isoformat(),
                }

        self._cycle_running = True
        logger.info(
            "Shania: Starting social posting cycle (mode=%s, launch_mode=%s, brands=%s)",
            POSTING_MODE, LAUNCH_MODE, list(BRAND_PLATFORMS.keys()),
        )
        posted = 0
        errors = 0
        try:
            if BUCKET_ONLY_MODE:
                # Bucket-only: post one pre-approved asset per brand that has any
                async with httpx.AsyncClient(timeout=90.0) as client:
                    for brand in list(BRAND_PLATFORMS.keys())[:MAX_POSTS_PER_CYCLE]:
                        try:
                            resp = await client.post(
                                f"{SHANIA_GRAPHICS_URL}/post-from-approved",
                                json={"brand": brand, "dryRun": False},
                                headers={
                                    "X-Admin-Token": INTERNAL_ADMIN_TOKEN,
                                    "Content-Type": "application/json",
                                },
                            )
                            if resp.status_code == 200:
                                posted += 1
                                logger.info(
                                    "Shania: Posted approved asset for brand=%s", brand,
                                )
                            elif resp.status_code == 404:
                                logger.info(
                                    "Shania: No approved assets for brand=%s — skipping", brand,
                                )
                            else:
                                errors += 1
                                logger.warning(
                                    "Shania: post-from-approved failed brand=%s: %s %s",
                                    brand, resp.status_code, resp.text[:200],
                                )
                        except Exception as e:
                            errors += 1
                            logger.error("Shania: post-from-approved error brand=%s: %s", brand, e)
            else:
                topics = _select_topics(MAX_POSTS_PER_CYCLE)

                async with httpx.AsyncClient(timeout=90.0) as client:
                    for topic in topics:
                        try:
                            platforms = _platforms_for_brand(topic["brand"])
                            if not platforms:
                                logger.info("Skipping brand=%s — no platforms configured", topic["brand"])
                                continue
                            resp = await client.post(
                                f"{SHANIA_GRAPHICS_URL}/orchestrate-post",
                                json={
                                    "prompt": topic["prompt"],
                                    "brand": topic["brand"],
                                    "platforms": platforms,
                                    "dryRun": False,
                                },
                                headers={
                                    "X-Admin-Token": INTERNAL_ADMIN_TOKEN,
                                    "Content-Type": "application/json",
                                },
                            )
                            if resp.status_code == 200:
                                posted += 1
                                logger.info(
                                    "Shania: Published post [%s] brand=%s template=%s platforms=%s",
                                    topic["prompt"][:50], topic["brand"], topic.get("template_key", "legacy"), platforms,
                                )
                                # Also post to X (@Wihyai)
                                resp_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                                x_text = resp_data.get("caption") or resp_data.get("text") or topic["prompt"]
                                await _post_to_x(client, x_text, topic["brand"])
                            else:
                                errors += 1
                                logger.warning(
                                    "Shania: orchestrate-post failed [%s]: %s %s",
                                    topic["prompt"][:50], resp.status_code, resp.text[:200],
                                )
                        except Exception as e:
                            errors += 1
                            logger.error("Shania: Post error [%s]: %s", topic["prompt"][:50], e)

            self._last_run = datetime.now(timezone.utc)
            self._total_posts_published += posted
            self._total_errors += errors

            result = {
                "cycle": "social_posting",
                "posts_published": posted,
                "errors": errors,
                "timestamp": self._last_run.isoformat(),
            }
            logger.info("Shania: Social posting cycle complete — %s", result)
            return result
        finally:
            self._cycle_running = False

    async def _loop(self) -> None:
        await asyncio.sleep(180)  # 3 min initial delay to let services warm up
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error("SocialPostingService loop error: %s", e)
            await asyncio.sleep(SOCIAL_POSTING_INTERVAL)


# Singleton
social_posting_service = SocialPostingService()
