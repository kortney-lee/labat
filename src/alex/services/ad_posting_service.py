"""
ad_posting_service.py — Strategy-driven autonomous ad creation for LABAT.

LEARNING LOOP — Before creating each ad, LABAT:
  1. Pulls ad-level insights from Meta (last 7 days)
  2. Identifies what's working: which brands/stages have best CTR & ROAS
  3. Doubles down on winning combos, avoids angles similar to losers
  4. Adjusts funnel stage weighting (more conversion if awareness already strong)

FIND → CAPTURE → CONVERT funnel from strategy_rules.py:
  FIND (awareness):   Stop the scroll, surface a painful problem.
  CAPTURE (consider): Build trust with proof, mechanism, value.
  CONVERT (convert):  Clear urgency, direct CTA, no hype.

Each brand gets 1 ad every ~5 days, cycling through funnel stages.
The cycle is reactive — if conversion ads are winning, lean harder there.

─── Agent Roles (who does what) ───
  Shania (social_posting_service in maya_app):
    PURPOSE: Organic content that EDUCATES and builds trust.
    POSTS: 2x/day across FB/IG/Threads/LinkedIn(wihy-only).
    TOPICS: Evergreen health tips, nutrition facts, brand awareness.
    VOICE: Informative, helpful, no hard sell.

  LABAT (this service in alex_app):
    PURPOSE: Paid ads that drive FUNNEL ACTIONS — find, capture, convert.
    POSTS: 1 ad per cycle, rotating brands × funnel stages.
    REACTS: Reads insights, learns what works, adjusts next ad.
    VOICE: Persuasive, evidence-first, clear CTA.

  Alex (background_tasks in alex_app):
    PURPOSE: SEO intelligence — keyword discovery, analytics, trends.
    Informs both Shania and LABAT with signal data.

  Maya (engagement_poster_service in maya_app):
    PURPOSE: Community engagement — replies, threads, group posts.
    Monitors: comment threads, group conversations.
    Voice: Helpful, WIHY-branded, RAG-grounded answers.
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from src.alex.config import ALEX_BASE_URL, INTERNAL_ADMIN_TOKEN
from src.labat.services.strategy_rules import (
    _FUNNEL_RULES,
    _PRODUCT_RULES,
)

logger = logging.getLogger("labat.ad_posting")

# ── Configuration ────────────────────────────────────────────────────────────
# 1 ad per cycle. With 5 brands, each brand ≈ 1 ad every 5 cycles.
AD_POSTING_INTERVAL = int(os.getenv("LABAT_AD_POSTING_INTERVAL", "86400"))
AD_POSTS_PER_CYCLE = int(os.getenv("LABAT_AD_POSTS_PER_CYCLE", "1"))
LEAD_ONLY_MODE = os.getenv("LABAT_AD_LEAD_ONLY", "true").strip().lower() == "true"

# Active brands (NO otakulounge)
AD_BRANDS: List[str] = [
    b.strip().lower()
    for b in os.getenv("LABAT_AD_BRANDS", "wihy,communitygroceries").split(",")
    if b.strip()
]

LEAD_FORM_ID_BY_BRAND: Dict[str, str] = {
    "wihy": os.getenv("LABAT_WIHY_LEAD_FORM_ID", "").strip(),
    "communitygroceries": os.getenv("LABAT_CG_LEAD_FORM_ID", "").strip(),
}

LEAD_FORM_NAME_BY_BRAND: Dict[str, str] = {
    "wihy": os.getenv("LABAT_WIHY_LEAD_FORM_NAME", "Wihy Lead Capture - Launch").strip(),
    "communitygroceries": os.getenv("LABAT_CG_LEAD_FORM_NAME", "Communitygroceries Lead Capture - 2").strip(),
}

# Find → Capture → Convert rotation order
FUNNEL_ROTATION: List[str] = ["awareness", "consideration", "conversion"]

# LABAT URL for insights (reads performance data directly from LABAT service)
LABAT_URL = os.getenv("LABAT_URL", "https://wihy-labat-n4l2vldq3q-uc.a.run.app")

# ── Strategic Ad Angles (per brand × funnel stage) ───────────────────────────
# These are DIRECTIONS — not final copy. The orchestrate-photo-ad pipeline
# (Shania + Gemini) generates the actual image + caption from these angles.

BRAND_AD_ANGLES: Dict[str, Dict[str, List[str]]] = {
    "wihy": {
        "awareness": [
            "Expose how food labels hide the truth — hook with a surprising ingredient fact most people miss",
            "Pattern interrupt: your doctor gets 19 hours of nutrition training. WIHY AI has millions of studies",
            "Challenge the myth that eating healthy is complicated — AI makes it simple and personal",
        ],
        "consideration": [
            "Show the product scanning feature — see exactly what's in your food, no marketing spin",
            "Demonstrate AI meal planning that adapts to your body, goals, and budget",
            "How WIHY AI turns complex research into one clear answer you can act on today",
        ],
        "conversion": [
            "Try WIHY AI free — scan any food product and see what's really in it at wihy.ai",
            "Get your personalized 7-day meal plan in 30 seconds — free at wihy.ai",
            "The health app backed by 48 million research articles — free at wihy.ai",
        ],
    },
    "communitygroceries": {
        "awareness": [
            "Families waste $1,500/year on food they throw away — there's a smarter way to plan meals",
            "The struggle of feeding a family healthy food on a real budget — it doesn't have to be this hard",
            "Meal planning shouldn't take hours of prep — AI does it in 30 seconds",
        ],
        "consideration": [
            "See how AI builds a week of balanced meals + grocery list matched to your family's budget",
            "Family of 4, $80/week, nutritious meals — here's what that actually looks like",
            "No more 'what's for dinner?' stress — Community Groceries plans everything for you",
        ],
        "conversion": [
            "Get your family's personalized meal plan + grocery list free at communitygroceries.com",
            "7 days of meals with a smart shopping list — generated in 30 seconds for your family",
            "Stop wasting food and money — get your free AI meal plan at communitygroceries.com",
        ],
    },
    "vowels": {
        "awareness": [
            "The food industry spends $14 billion convincing you junk food is fine — the data tells a different story",
            "48 million research articles distilled into one free book your family needs to read",
            "Most nutrition advice is marketing disguised as science — What Is Healthy? follows the actual data",
        ],
        "consideration": [
            "3 food label tricks you'll never unsee after reading What Is Healthy?",
            "The evidence behind why processed food is making us sick — and what to do about it",
            "From nutrition confusion to clarity: what data-driven health decisions look like",
        ],
        "conversion": [
            "Free download: What Is Healthy? — the data-driven guide to food labels at vowels.org",
            "The book that exposes food marketing tactics — free digital copy at vowels.org",
            "Your family's health shouldn't depend on marketing claims — get the facts free at vowels.org",
        ],
    },
    "childrennutrition": {
        "awareness": [
            "Picky eating is normal — but how you handle it matters more than you think",
            "Hidden veggie tricks that actually work — parent tested, science backed",
            "Why kids reject healthy food and the one research-backed strategy that changes everything",
        ],
        "consideration": [
            "The food bridge method: get picky eaters to try new foods without fights or tears",
            "3 simple sugar swaps that make a real difference in your child's nutrition",
            "School lunch ideas that picky eaters will actually eat — tested by real parents",
        ],
        "conversion": [
            "Free guide: science-backed strategies to transform your picky eater at whatishealthy.org",
            "The picky eater toolkit — proven strategies for every age free at whatishealthy.org",
            "Healthy meals kids will eat — free recipes and complete guides at whatishealthy.org",
        ],
    },
    "parentingwithchrist": {
        "awareness": [
            "Jesus fasted 40 days — are we teaching our children the power and purpose of discipline?",
            "The world says treat yourself. Jesus says deny yourself. Raising kids who know the difference",
            "Self-discipline is a fruit of the Spirit — and it starts with what you model at home",
        ],
        "consideration": [
            "Biblical discipline isn't punishment — it's training your child for the life God intends",
            "Age-appropriate ways to introduce fasting and self-control to your family",
            "Teaching delayed gratification through Scripture — a discipline the world has abandoned",
        ],
        "conversion": [
            "Join parents raising faith-rooted, disciplined children at parentingwithchrist.com",
            "Free Biblical parenting wisdom and practical daily guides at parentingwithchrist.com",
            "Raise kids who follow Jesus in a world that says follow yourself — parentingwithchrist.com",
        ],
    },
}


# ── Performance Learning ─────────────────────────────────────────────────────

def _safe_float(val, default: float = 0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _extract_conversions(actions: list) -> int:
    if not actions:
        return 0
    total = 0
    for a in actions:
        if a.get("action_type") in (
            "purchase", "offsite_conversion.fb_pixel_purchase",
            "lead", "offsite_conversion.fb_pixel_lead",
            "complete_registration", "link_click",
        ):
            total += int(_safe_float(a.get("value", 0)))
    return total


async def _fetch_ad_insights() -> List[Dict[str, Any]]:
    """Pull last 7 days of ad-level insights from LABAT's insights endpoint.
    
    When AD_BRANDS contains a single brand, filters results to only that brand's
    campaigns by matching the campaign name prefix convention:
    "{Brand} - {Funnel} - {Topic} - {Date}"
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{LABAT_URL}/api/labat/insights",
                params={"level": "ad", "date_preset": "last_7d"},
                headers={"X-Admin-Token": INTERNAL_ADMIN_TOKEN},
            )
            if resp.status_code == 200:
                rows = resp.json().get("data", [])
                # Filter to this instance's brand(s) by campaign name prefix
                if len(AD_BRANDS) == 1:
                    brand_key = AD_BRANDS[0].lower()
                    rows = [
                        r for r in rows
                        if (r.get("campaign_name") or "").split(" - ")[0].strip().lower() == brand_key
                    ]
                    logger.info("Filtered insights to brand=%s: %d rows", brand_key, len(rows))
                return rows
            logger.warning("Insights fetch returned %d", resp.status_code)
    except Exception as e:
        logger.warning("Could not fetch insights (will proceed without): %s", e)
    return []


def _score_ad(row: Dict[str, Any]) -> Dict[str, Any]:
    """Score a single ad row from Meta insights."""
    ctr = _safe_float(row.get("ctr"))
    spend = _safe_float(row.get("spend"))
    impressions = int(_safe_float(row.get("impressions")))
    clicks = int(_safe_float(row.get("clicks")))
    conversions = _extract_conversions(row.get("actions", []))
    roas_list = row.get("purchase_roas") or row.get("website_purchase_roas")
    roas = _safe_float(roas_list[0].get("value", 0) if isinstance(roas_list, list) and roas_list else roas_list)

    # Composite score: conversions matter most, then CTR, then ROAS
    score = conversions * 100 + ctr * 10 + roas * 5

    # Extract brand from campaign name (e.g. "Wihy - Awareness - ...")
    campaign_name = (row.get("campaign_name") or "").lower()
    brand = "unknown"
    for b in AD_BRANDS:
        if b in campaign_name or b.replace("communitygroceries", "community") in campaign_name:
            brand = b
            break

    # Extract funnel stage from campaign name
    stage = "awareness"
    for s in FUNNEL_ROTATION:
        if s in campaign_name:
            stage = s
            break

    return {
        "brand": brand,
        "stage": stage,
        "score": score,
        "ctr": ctr,
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "roas": roas,
        "is_winner": ctr >= 1.0 or conversions >= 1,
        "is_loser": spend >= 10 and conversions == 0 and impressions >= 1000,
    }


def _learn_from_insights(insights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze recent ad performance and return learning signals.

    Returns:
      - winning_brands: brands with best performance (lean into these)
      - winning_stages: funnel stages that are converting (do more of these)
      - losing_combos: brand+stage combos to avoid
      - recommendation: what to do next
    """
    if not insights:
        return {"has_data": False, "recommendation": "no_data_yet"}

    scored = [_score_ad(row) for row in insights]
    winners = [s for s in scored if s["is_winner"]]
    losers = [s for s in scored if s["is_loser"]]

    # Count wins per brand
    brand_wins: Dict[str, int] = {}
    stage_wins: Dict[str, int] = {}
    for w in winners:
        brand_wins[w["brand"]] = brand_wins.get(w["brand"], 0) + 1
        stage_wins[w["stage"]] = stage_wins.get(w["stage"], 0) + 1

    # Losing combos to avoid
    losing_combos = set()
    for l in losers:
        losing_combos.add(f"{l['brand']}:{l['stage']}")

    # Best performing brand
    winning_brands = sorted(brand_wins.keys(), key=lambda b: brand_wins[b], reverse=True)
    winning_stages = sorted(stage_wins.keys(), key=lambda s: stage_wins[s], reverse=True)

    # Total spend and return
    total_spend = sum(s["spend"] for s in scored)
    total_conversions = sum(s["conversions"] for s in scored)
    avg_ctr = sum(s["ctr"] for s in scored) / max(len(scored), 1)

    recommendation = "balanced"
    if winning_stages and winning_stages[0] == "conversion" and total_conversions >= 3:
        recommendation = "double_down_conversion"
    elif winning_stages and winning_stages[0] == "awareness" and avg_ctr >= 2.0:
        recommendation = "move_to_consideration"
    elif total_spend >= 50 and total_conversions == 0:
        recommendation = "reset_angles"

    return {
        "has_data": True,
        "winning_brands": winning_brands[:3],
        "winning_stages": winning_stages,
        "losing_combos": list(losing_combos),
        "total_spend": total_spend,
        "total_conversions": total_conversions,
        "avg_ctr": round(avg_ctr, 2),
        "winners_count": len(winners),
        "losers_count": len(losers),
        "recommendation": recommendation,
    }


class AdPostingService:
    """Strategy-driven ad creation with performance learning.

    Before each ad creation cycle:
      1. Fetches ad insights (last 7 days)
      2. Scores winners and losers by brand × funnel stage
      3. Adjusts next brand/stage selection based on what's working
      4. Creates the ad with the winning angle direction

    Rotates brands round-robin but skips losing combos and favors winners.
    """

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._total_ads_created = 0
        self._total_errors = 0
        self._last_run: Optional[datetime] = None
        self._last_learnings: Optional[Dict[str, Any]] = None
        # Funnel rotation: each brand's position in awareness→consideration→conversion
        self._brand_funnel_index: Dict[str, int] = {b: 0 for b in AD_BRANDS}
        self._brand_index = 0

    def _next_brand_and_stage(
        self, learnings: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Pick next brand and funnel stage, adjusted by performance data.

        Logic:
          - Default: round-robin brand, rotating funnel stage
          - If learnings show a losing combo: skip it
          - If recommendation is 'double_down_conversion': force conversion stage
          - If recommendation is 'move_to_consideration': force consideration
          - If recommendation is 'reset_angles': stay with awareness (rebuild)
        """
        attempts = 0
        while attempts < len(AD_BRANDS) * len(FUNNEL_ROTATION):
            brand = AD_BRANDS[self._brand_index % len(AD_BRANDS)]
            funnel_idx = self._brand_funnel_index.get(brand, 0)
            stage = FUNNEL_ROTATION[funnel_idx % len(FUNNEL_ROTATION)]

            # Apply learning overrides
            if learnings and learnings.get("has_data"):
                rec = learnings.get("recommendation", "balanced")
                if rec == "double_down_conversion":
                    stage = "conversion"
                elif rec == "move_to_consideration":
                    stage = "consideration"
                elif rec == "reset_angles":
                    stage = "awareness"

                # Skip known losing combos
                combo = f"{brand}:{stage}"
                if combo in learnings.get("losing_combos", []):
                    # Advance and try next
                    self._brand_funnel_index[brand] = (funnel_idx + 1) % len(FUNNEL_ROTATION)
                    self._brand_index = (self._brand_index + 1) % len(AD_BRANDS)
                    attempts += 1
                    continue

            # Advance pointers for next call
            self._brand_funnel_index[brand] = (funnel_idx + 1) % len(FUNNEL_ROTATION)
            self._brand_index = (self._brand_index + 1) % len(AD_BRANDS)
            return brand, stage

        # Fallback: just pick next in line
        brand = AD_BRANDS[self._brand_index % len(AD_BRANDS)]
        self._brand_index = (self._brand_index + 1) % len(AD_BRANDS)
        return brand, "awareness"

    def _pick_angle(self, brand: str, stage: str) -> str:
        """Select a random ad angle for this brand × funnel stage."""
        angles = BRAND_AD_ANGLES.get(brand, {}).get(stage, [])
        if angles:
            return random.choice(angles)
        # Fallback: build from strategy_rules
        rules = _PRODUCT_RULES.get(brand, _PRODUCT_RULES["wihy"])
        funnel = _FUNNEL_RULES.get(stage, _FUNNEL_RULES["awareness"])
        return (
            f"{funnel['goal']} "
            f"Promote {rules['name']} ({rules['positioning']}). "
            f"Core offer: {rules['offer']}. "
            f"Angle: {random.choice(funnel['angles'])}"
        )

    async def _activate_entities(
        self, client: httpx.AsyncClient, result: dict
    ) -> None:
        """Activate campaign, adset, and ad after creation."""
        labat_base = os.getenv("LABAT_BASE_URL", "https://wihy-labat-n4l2vldq3q-uc.a.run.app")
        headers = {"X-Admin-Token": INTERNAL_ADMIN_TOKEN, "Content-Type": "application/json"}
        for entity, id_key in [
            ("campaigns", "campaign_id"),
            ("adsets", "adset_id"),
            ("ads", "ad_id"),
        ]:
            entity_id = result.get(id_key)
            if not entity_id:
                continue
            try:
                r = await client.put(
                    f"{labat_base}/api/labat/ads/{entity}/{entity_id}",
                    json={"status": "ACTIVE"},
                    headers=headers,
                    timeout=30,
                )
                if r.status_code == 200:
                    logger.info("Activated %s %s", entity, entity_id)
                else:
                    logger.warning("Failed to activate %s %s: %d %s", entity, entity_id, r.status_code, r.text[:200])
            except Exception as e:
                logger.warning("Activation error %s %s: %s", entity, entity_id, e)

    def status(self) -> dict:
        next_brand = AD_BRANDS[self._brand_index % len(AD_BRANDS)]
        next_stage = FUNNEL_ROTATION[
            self._brand_funnel_index.get(next_brand, 0) % len(FUNNEL_ROTATION)
        ]
        return {
            "running": self._running,
            "strategy": "find_capture_convert",
            "learning": "reactive",
            "total_ads_created": self._total_ads_created,
            "total_errors": self._total_errors,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_learnings": self._last_learnings,
            "interval_seconds": AD_POSTING_INTERVAL,
            "ads_per_cycle": AD_POSTS_PER_CYCLE,
            "active_brands": AD_BRANDS,
            "funnel_rotation": FUNNEL_ROTATION,
            "next_brand": next_brand,
            "next_stage": next_stage,
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(
            "AdPostingService started — strategy=find→capture→convert (reactive), "
            "interval=%ds, ads_per_cycle=%d, brands=%s",
            AD_POSTING_INTERVAL, AD_POSTS_PER_CYCLE, AD_BRANDS,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AdPostingService stopped")

    async def run_once(self) -> Dict[str, Any]:
        """Run a single ad creation cycle with learning."""
        # ── Step 1: Learn from recent performance ──
        insights_data = await _fetch_ad_insights()
        learnings = _learn_from_insights(insights_data)
        self._last_learnings = learnings

        if learnings.get("has_data"):
            logger.info(
                "LABAT learning: recommendation=%s, winners=%d, losers=%d, "
                "avg_ctr=%.2f%%, spend=$%.2f, conversions=%d",
                learnings["recommendation"], learnings["winners_count"],
                learnings["losers_count"], learnings["avg_ctr"],
                learnings["total_spend"], learnings["total_conversions"],
            )
        else:
            logger.info("LABAT: No performance data yet — using default rotation")

        # ── Step 2: Create ads using learned strategy ──
        results: List[Dict[str, Any]] = []

        for _ in range(AD_POSTS_PER_CYCLE):
            brand, stage = self._next_brand_and_stage(learnings)
            angle = self._pick_angle(brand, stage)

            logger.info(
                "LABAT [%s/%s]: Creating ad — %s", stage, brand, angle[:80],
            )

            result: Dict[str, Any] = {
                "brand": brand,
                "funnel_stage": stage,
                "angle": angle[:80],
                "informed_by": learnings.get("recommendation", "default"),
            }

            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    endpoint = "/api/astra/orchestrate-lead-ad" if LEAD_ONLY_MODE else "/api/astra/orchestrate-photo-ad"
                    payload: Dict[str, Any]
                    if LEAD_ONLY_MODE:
                        payload = {
                            "brand": brand,
                            "ad_copy": angle,
                            "headline": _PRODUCT_RULES.get(brand, {}).get("name", brand.title()),
                            "cta_type": "SIGN_UP",
                            "daily_budget": 2500,  # $25/day
                            "dry_run": False,
                            "form_name": LEAD_FORM_NAME_BY_BRAND.get(brand, f"{brand.title()} Lead Capture"),
                        }
                        lead_form_id = LEAD_FORM_ID_BY_BRAND.get(brand)
                        if lead_form_id:
                            payload["lead_form_id"] = lead_form_id
                    else:
                        payload = {
                            "topic": angle,
                            "brand": brand,
                            "funnel_stage": stage,
                            "daily_budget": 500,  # $5/day
                            "dry_run": False,
                        }

                    resp = await client.post(
                        f"{ALEX_BASE_URL}{endpoint}",
                        json=payload,
                        headers={
                            "X-Admin-Token": INTERNAL_ADMIN_TOKEN,
                            "Content-Type": "application/json",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("status") == "completed":
                            self._total_ads_created += 1
                            result["status"] = "created"
                            result["campaign_id"] = data.get("campaign", {}).get("id") or data.get("auto_campaign", {}).get("id")
                            result["adset_id"] = data.get("adset", {}).get("id") or data.get("auto_adset", {}).get("id")
                            result["ad_id"] = data.get("ad", {}).get("id")
                            result["lead_form_id"] = data.get("lead_form", {}).get("id")
                            logger.info("LABAT [%s/%s]: Ad created — %s", stage, brand, result)

                            # Auto-activate campaign, adset, and ad
                            await self._activate_entities(client, result)
                        else:
                            self._total_errors += 1
                            result["status"] = "pipeline_error"
                            result["error"] = data.get("error", "unknown")
                    else:
                        self._total_errors += 1
                        result["status"] = "http_error"
                        result["error"] = f"{resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                self._total_errors += 1
                result["status"] = "exception"
                result["error"] = str(e)
                logger.error("LABAT [%s/%s]: Exception — %s", stage, brand, e)

            results.append(result)

        self._last_run = datetime.now(timezone.utc)
        summary = {
            "cycle": "ad_creation",
            "strategy": "find_capture_convert",
            "learnings": learnings,
            "results": results,
            "timestamp": self._last_run.isoformat(),
        }
        logger.info("LABAT: Cycle complete — %s", summary)
        return summary

    async def _loop(self) -> None:
        await asyncio.sleep(600)  # 10 min warmup
        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error("AdPostingService loop error: %s", e)
            await asyncio.sleep(AD_POSTING_INTERVAL)


# Singleton
ad_posting_service = AdPostingService()
