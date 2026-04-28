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
    # ── WIHY AI launch hype ──
    {"prompt": "Coming soon: an AI that actually understands YOUR health. WIHY AI analyzes 48 million research articles so you don't have to. Sign up for early access at wihy.ai", "brand": "wihy"},
    {"prompt": "Tired of generic health advice? WIHY AI builds meal plans, workout routines, and nutrition guidance personalized to YOUR body and goals. Launching soon — join the waitlist at wihy.ai", "brand": "wihy"},
    {"prompt": "What if you had a personal nutritionist, fitness coach, and health researcher in your pocket — powered by AI? That's WIHY. Early access opening soon at wihy.ai", "brand": "wihy"},
    {"prompt": "WIHY AI scans any food product and tells you exactly what's in it — no confusing labels, no marketing tricks, just science. Try it free at wihy.ai when we launch", "brand": "wihy"},
    {"prompt": "We trained our AI on real peer-reviewed research — not influencer opinions. WIHY gives you health answers backed by science. Coming soon to wihy.ai", "brand": "wihy"},
    {"prompt": "Your doctor gets 19 hours of nutrition training in med school. WIHY AI was trained on millions of nutrition studies. Which one do you want planning your meals? Sign up at wihy.ai", "brand": "wihy"},
    {"prompt": "Stop Googling health questions and getting 50 different answers. WIHY AI gives you ONE answer backed by real research. Launching soon — wihy.ai", "brand": "wihy"},
    {"prompt": "Ask WIHY anything: 'What should I eat to lose weight?' 'Is intermittent fasting safe?' 'Build me a workout plan.' Real AI. Real science. Real answers. Coming soon at wihy.ai", "brand": "wihy"},
    {"prompt": "We're building the health app we wished existed. AI-powered meal plans, fitness programs, food scanning, and research — all in one place. Join the movement at wihy.ai", "brand": "wihy"},
    {"prompt": "WIHY is not another calorie counter. It's an AI health platform that learns YOUR body, YOUR goals, and YOUR diet — then gives you a science-backed plan. Launching soon at wihy.ai", "brand": "wihy"},
    {"prompt": "Sneak peek: WIHY AI just generated a full 7-day meal plan with grocery list in under 30 seconds. Personalized. Research-backed. Affordable. This is the future of health. wihy.ai", "brand": "wihy"},
    {"prompt": "The food industry spends $14 billion a year convincing you junk food is fine. We built an AI to fight back with science. WIHY is coming. wihy.ai", "brand": "wihy"},
    # ── Community Groceries launch hype ──
    {"prompt": "Introducing Community Groceries — the smarter way to shop, cook, and eat healthy on any budget. AI-powered meal plans and grocery lists built for real families. Coming soon at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "What if your grocery list was built by AI that knows your budget, your family's allergies, and what's on sale this week? That's Community Groceries. Sign up at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Feeding a family of four for under $100 a week — with balanced, healthy meals. Community Groceries makes it possible with AI-powered meal planning. Launching soon at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "We're tired of meal planning apps that suggest $15 salmon when you're on a $50/week budget. Community Groceries plans meals YOUR wallet can handle. Coming soon at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Scan any product at the store. Community Groceries AI tells you if it's healthy, what to swap it for, and where to find it cheaper. Try it free at communitygroceries.com when we launch", "brand": "communitygroceries"},
    {"prompt": "Meal prep Sunday just got an upgrade. Community Groceries generates a full week of meals + shopping list in seconds — personalized to your family. Launching soon at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "School lunch ideas. Weeknight dinners. Snacks that aren't junk. Community Groceries is the meal planning AI built for busy parents. Join the waitlist at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Stop throwing away food. Community Groceries builds grocery lists that match your meal plan exactly — no waste, no extra trips, no stress. Coming soon at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Every family deserves access to healthy food — regardless of budget. Community Groceries uses AI to make nutritious eating affordable and simple. Launching soon at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Your grandma planned meals by hand. You can let AI do it in 30 seconds. Same love, smarter tools. Community Groceries — coming soon at communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Behind the scenes: we just tested Community Groceries AI with a real family of five. Full week of meals, grocery list, $78 total. This is what we're building. communitygroceries.com", "brand": "communitygroceries"},
    {"prompt": "Healthy eating shouldn't require a nutrition degree or a six-figure salary. Community Groceries makes it dead simple with AI. Join us at communitygroceries.com", "brand": "communitygroceries"},
]

# ── Evergreen topics — ongoing educational content ──────────────────────
EVERGREEN_TOPICS: List[Dict[str, str]] = [
    # wihy — superhuman optimization: biohacking, longevity, peak performance, become the best version of yourself
    {"prompt": "Do these 5 things every morning and your body will perform like a machine: cold shower, sunlight exposure, protein-first meal, breathwork, movement. The superhuman morning routine backed by science", "brand": "wihy"},
    {"prompt": "Walking 10,000 steps a day is good. But adding just 2 minutes of cold water at the end of your shower increases norepinephrine by 530%. Small upgrades, superhuman results", "brand": "wihy"},
    {"prompt": "Your VO2 max is the single best predictor of how long you'll live — better than cholesterol, blood pressure, or any blood test. Here's how to improve it starting today", "brand": "wihy"},
    {"prompt": "Grip strength predicts all-cause mortality better than blood pressure. The stronger your grip, the longer you live. Here's the 5-minute daily protocol to build it", "brand": "wihy"},
    {"prompt": "Want to age slower? Zone 2 cardio 150 minutes per week. Strength training 3x per week. 7+ hours sleep. High protein diet. That's the entire longevity playbook backed by research", "brand": "wihy"},
    {"prompt": "10 minutes of cold exposure increases dopamine by 250% for hours — no caffeine, no supplements, just ice water. This is how you become superhuman without spending a dime", "brand": "wihy"},
    {"prompt": "Time-restricted eating (eating within an 8-hour window) activates autophagy — your body literally repairs damaged cells. This is the closest thing to a biological reset button", "brand": "wihy"},
    {"prompt": "Elite athletes sleep 9-10 hours. Your muscle doesn't grow in the gym — it grows during deep sleep. Here's how to optimize your sleep architecture for maximum recovery", "brand": "wihy"},
    {"prompt": "Sauna 4x per week reduces all-cause mortality by 40%. Heat stress activates heat shock proteins that repair DNA damage. Your gym membership should include the sauna", "brand": "wihy"},
    {"prompt": "The human body produces more electricity than a 120-volt battery. You are literally a biological machine — here's how to optimize your engine with food, movement, and recovery", "brand": "wihy"},
    {"prompt": "Creatine isn't just for bodybuilders. Research shows it improves memory, reduces brain fog, and protects against neurodegeneration. 5g per day — the most studied supplement on earth", "brand": "wihy"},
    {"prompt": "Your mitochondria are the power plants of every cell. Red light therapy, cold exposure, and exercise all increase mitochondrial density. More mitochondria = more energy = superhuman output", "brand": "wihy"},
    {"prompt": "Stop counting calories. Start counting protein. 1g per pound of body weight. This single change transforms body composition faster than any diet ever created", "brand": "wihy"},
    {"prompt": "Grounding — walking barefoot on earth — reduces inflammation markers in clinical studies. Free. Zero side effects. 20 minutes a day. The most underrated health hack that exists", "brand": "wihy"},
    {"prompt": "Your body replaces 330 billion cells every day. Feed it the right raw materials and you literally become a new, upgraded version of yourself every 90 days", "brand": "wihy"},
    # communitygroceries — recipes, easy meals, food that drives commerce and family dinner tables
    {"prompt": "30 Minute Shrimp Tacos: Season shrimp with chili, cumin, garlic. Sear 3 min per side. Serve on warm corn tortillas with shredded cabbage, lime, cilantro, and Greek yogurt. Family dinner done — 320 cal, 25g protein", "brand": "communitygroceries"},
    {"prompt": "One-pot chicken and rice: Brown chicken thighs, add rice, broth, frozen peas, garlic. Cover and simmer 20 minutes. One pan. One cleanup. Feeds a family of four for under $12", "brand": "communitygroceries"},
    {"prompt": "Sheet pan salmon and vegetables: Toss broccoli, sweet potato, and salmon with olive oil and lemon. 400°F for 20 minutes. High omega-3, zero effort, restaurant quality at home", "brand": "communitygroceries"},
    {"prompt": "5-ingredient black bean tacos the kids actually love: canned black beans, taco seasoning, corn tortillas, shredded cheese, salsa. 10 minutes. $6 for the whole family. Meatless Monday winner", "brand": "communitygroceries"},
    {"prompt": "Sunday meal prep that saves your week: Cook 2 lbs ground turkey, a pot of brown rice, and roast a sheet pan of mixed veggies. Mix and match all week. 5 lunches prepped in 90 minutes", "brand": "communitygroceries"},
    {"prompt": "Slow cooker pulled chicken: Chicken breast + salsa + cumin + garlic. 6 hours on low. Shred. Use for tacos, bowls, salads, wraps. One cook, four different meals", "brand": "communitygroceries"},
    {"prompt": "Quick peanut noodles the whole family loves: Cook spaghetti. Toss with peanut butter, soy sauce, lime juice, sesame oil, and sriracha. Top with cucumber and cilantro. 15 minutes. Under $8", "brand": "communitygroceries"},
    {"prompt": "Egg muffin cups — breakfast meal prep: Whisk 12 eggs with spinach, bell pepper, cheese. Pour into muffin tin. Bake 20 min at 375°F. Grab-and-go breakfast for the entire week", "brand": "communitygroceries"},
    {"prompt": "Budget grocery haul under $50 that feeds a family of 4 for a full week: chicken thighs, rice, beans, eggs, frozen veggies, bananas, oats, tortillas, peanut butter, canned tomatoes. Practical. Nutritious. Affordable", "brand": "communitygroceries"},
    {"prompt": "Healthy air fryer chicken tenders: Cut chicken breast into strips. Coat in egg wash then panko + garlic powder. Air fry 400°F 10 min. Crispier than fast food. 28g protein per serving. Kids go crazy for these", "brand": "communitygroceries"},
    {"prompt": "3-ingredient banana oat pancakes: Mash 2 ripe bananas + 1 cup oats + 2 eggs. Blend. Cook like regular pancakes. No flour, no added sugar. Kids think they're getting a treat. You know it's actually healthy", "brand": "communitygroceries"},
    {"prompt": "The $3 lunch that beats any drive-through: Rice + canned black beans + frozen corn + salsa + avocado. Microwave the first three, top with the rest. 15g protein, 8g fiber, and it actually tastes incredible", "brand": "communitygroceries"},
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
