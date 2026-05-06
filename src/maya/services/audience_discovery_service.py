"""
maya/services/audience_discovery_service.py — Organic audience discovery for WIHY brands.

Scans Twitter and Instagram for users talking about health/nutrition topics
aligned with each WIHY brand. Scores them and stores in Firestore for
auto_engage_service to follow up on.

Runs every 6 hours via maya_app.py background loop.
Firestore path: audience_discovery/{platform}/users/{user_id}

Required env vars:
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
  INSTAGRAM_ACCESS_TOKEN
  INSTAGRAM_BUSINESS_USER_ID  — your IG Business account numeric ID (needed for hashtag search)
  GCP_PROJECT                 — defaults to "wihy-ai"
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.maya.services.engagement_poster_service import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    INSTAGRAM_ACCESS_TOKEN,
    INSTAGRAM_GRAPH_VERSION,
    _twitter_oauth1_header,
)

logger = logging.getLogger("maya.audience_discovery")

GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")
INSTAGRAM_BUSINESS_USER_ID = (os.getenv("INSTAGRAM_BUSINESS_USER_ID", "") or "").strip()

MIN_FOLLOWERS = int(os.getenv("DISCOVERY_MIN_FOLLOWERS", "50"))
MAX_FOLLOWERS = int(os.getenv("DISCOVERY_MAX_FOLLOWERS", "500000"))

# Seed hashtags per brand — top 3 per brand to control API cost
# Full list rotates daily: each run picks 3 randomly so all get covered over time
BRAND_HASHTAGS_POOL: Dict[str, List[str]] = {
    "wihy": [
        "nutrition", "healthyeating", "mealprep", "intermittentfasting",
        "guthealth", "weightloss", "healthylifestyle", "antiinflammatory",
    ],
    "vowels": [
        "nutritionscience", "evidencebasednutrition", "dietitian",
        "metabolichealth", "bloodsugar", "macros",
    ],
    "communitygroceries": [
        "budgetmeals", "affordablefood", "groceryshopping",
        "cheapmeals", "familymeals", "mealplan",
    ],
    "childrennutrition": [
        "kidsnutrition", "healthykids", "lunchbox",
        "parentingnutrition", "schoollunch", "kidfood",
    ],
}
HASHTAGS_PER_BRAND = int(os.getenv("DISCOVERY_HASHTAGS_PER_BRAND", "3"))
MAX_RESULTS_PER_HASHTAG = int(os.getenv("DISCOVERY_MAX_RESULTS", "10"))


def _get_firestore():
    from google.cloud import firestore
    return firestore.AsyncClient(project=GCP_PROJECT)


def _score_user(followers: int, following: int, listed: int, verified: bool) -> float:
    """Score a discovered user 0–100. Returns 0 if outside follower range."""
    if followers < MIN_FOLLOWERS or followers > MAX_FOLLOWERS:
        return 0.0
    ratio = min(followers / max(following, 1), 10.0)
    authority = min(listed / 10, 5.0)
    verified_bonus = 5.0 if verified else 0.0
    return round(ratio * 5 + authority * 3 + verified_bonus, 2)


async def _search_twitter_hashtag(
    client: httpx.AsyncClient,
    hashtag: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Search recent tweets for a hashtag. Returns unique authors with public_metrics."""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        return []

    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": f"#{hashtag} lang:en -is:retweet",
        "tweet.fields": "author_id",
        "user.fields": "id,username,name,description,public_metrics,verified",
        "expansions": "author_id",
        "max_results": str(max(10, min(max_results, 100))),
    }

    try:
        auth_header = _twitter_oauth1_header("GET", url, params)
        r = await client.get(
            url,
            headers={"Authorization": auth_header},
            params=params,
            timeout=20,
        )
        data = r.json()
        users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
        return list(users.values())
    except Exception as e:
        logger.error("Twitter hashtag search error (#%s): %s", hashtag, e)
        return []


async def _search_instagram_hashtag(
    client: httpx.AsyncClient,
    hashtag: str,
) -> List[Dict[str, Any]]:
    """
    Search Instagram for recent posts with a hashtag via Meta Graph API.
    Returns simplified user records (IG limits user data on hashtag results).
    Requires INSTAGRAM_BUSINESS_USER_ID and INSTAGRAM_ACCESS_TOKEN.
    """
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_BUSINESS_USER_ID:
        return []

    base = f"https://graph.facebook.com/{INSTAGRAM_GRAPH_VERSION}"

    try:
        r = await client.get(
            f"{base}/ig_hashtag_search",
            params={
                "user_id": INSTAGRAM_BUSINESS_USER_ID,
                "q": hashtag,
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=15,
        )
        hashtag_data = r.json().get("data", [])
        if not hashtag_data:
            return []
        hashtag_id = hashtag_data[0].get("id")
        if not hashtag_id:
            return []

        r2 = await client.get(
            f"{base}/{hashtag_id}/recent_media",
            params={
                "user_id": INSTAGRAM_BUSINESS_USER_ID,
                "fields": "id,username,timestamp,like_count,comments_count",
                "access_token": INSTAGRAM_ACCESS_TOKEN,
            },
            timeout=15,
        )
        posts = r2.json().get("data", [])
        seen = set()
        results = []
        for p in posts:
            username = p.get("username", "")
            if not username or username in seen:
                continue
            seen.add(username)
            results.append({
                "platform_user_id": username,
                "username": username,
                "platform_post_id": p.get("id"),
                "like_count": p.get("like_count", 0),
                "comments_count": p.get("comments_count", 0),
                "timestamp": p.get("timestamp"),
            })
        return results
    except Exception as e:
        logger.error("Instagram hashtag search error (#%s): %s", hashtag, e)
        return []


async def _upsert_user(
    db,
    platform: str,
    user_id: str,
    data: Dict[str, Any],
) -> bool:
    """Store user in Firestore. Returns True if new, False if already known."""
    ref = (
        db.collection("audience_discovery")
        .document(platform)
        .collection("users")
        .document(str(user_id))
    )
    existing = await ref.get()
    if existing.exists:
        return False
    await ref.set({
        **data,
        "engaged": False,
        "followed": False,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    })
    return True


async def run_once(brand: str = "all") -> Dict[str, Any]:
    """
    Run one discovery cycle. Picks HASHTAGS_PER_BRAND hashtags randomly per brand
    to rotate coverage while keeping API costs low (~$0.03/run vs $0.50+ before).
    brand: "all" | "wihy" | "vowels" | "communitygroceries" | "childrennutrition"
    """
    import random
    brands = list(BRAND_HASHTAGS_POOL.keys()) if brand == "all" else [brand]
    total_scanned = 0
    total_new = 0
    errors: List[str] = []

    db = _get_firestore()

    async with httpx.AsyncClient() as client:
        for b in brands:
            pool = BRAND_HASHTAGS_POOL.get(b, [])
            tags = random.sample(pool, min(HASHTAGS_PER_BRAND, len(pool)))
            for tag in tags:
                try:
                    # Twitter
                    for u in await _search_twitter_hashtag(client, tag):
                        metrics = u.get("public_metrics", {})
                        followers = metrics.get("followers_count", 0)
                        following = metrics.get("following_count", 0)
                        listed = metrics.get("listed_count", 0)
                        verified = u.get("verified", False)
                        score = _score_user(followers, following, listed, verified)
                        total_scanned += 1
                        if score > 0:
                            is_new = await _upsert_user(
                                db,
                                "twitter",
                                u["id"],
                                {
                                    "platform": "twitter",
                                    "brand": b,
                                    "discovery_hashtag": tag,
                                    "platform_user_id": u.get("id"),
                                    "username": u.get("username", ""),
                                    "name": u.get("name", ""),
                                    "description": u.get("description", ""),
                                    "followers_count": followers,
                                    "friends_count": following,
                                    "listed_count": listed,
                                    "verified": verified,
                                    "score": score,
                                },
                            )
                            if is_new:
                                total_new += 1

                    # Instagram
                    for u in await _search_instagram_hashtag(client, tag):
                        total_scanned += 1
                        is_new = await _upsert_user(
                            db,
                            "instagram",
                            u["platform_user_id"],
                            {
                                "platform": "instagram",
                                "brand": b,
                                "discovery_hashtag": tag,
                                "score": 50.0,
                                **u,
                            },
                        )
                        if is_new:
                            total_new += 1

                    await asyncio.sleep(1)  # gentle rate limit between hashtags

                except Exception as e:
                    msg = f"Discovery error brand={b} tag=#{tag}: {e}"
                    logger.error(msg)
                    errors.append(msg)

    result = {
        "brands_scanned": brands,
        "total_scanned": total_scanned,
        "total_new": total_new,
        "errors": errors,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Audience discovery complete: %s", result)
    return result
