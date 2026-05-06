"""
maya/services/auto_engage_service.py — Like and follow discovered users on Twitter.

Pulls unengaged users from the audience_discovery Firestore collection,
likes their most recent tweet, follows their account, and marks them as
engaged. Enforces conservative daily limits to stay well below Twitter's
platform caps and avoid spam triggers.

Runs every 2 hours via maya_app.py background loop.

Required env vars:
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
  TWITTER_MY_USER_ID     — your bot account's numeric user ID (required for follow/like)
  GCP_PROJECT            — defaults to "wihy-ai"

Optional env vars:
  AUTO_ENGAGE_MAX_FOLLOWS_DAY — daily follow cap (default 50, Twitter hard cap 400)
  AUTO_ENGAGE_MAX_LIKES_DAY   — daily like cap (default 200, Twitter hard cap 1000)
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.maya.services.engagement_poster_service import (
    TWITTER_API_KEY,
    TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN,
    TWITTER_ACCESS_TOKEN_SECRET,
    _twitter_oauth1_header,
)

logger = logging.getLogger("maya.auto_engage")

GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")
TWITTER_MY_USER_ID = (os.getenv("TWITTER_MY_USER_ID", "") or "").strip()

TWITTER_MAX_FOLLOWS_PER_DAY = int(os.getenv("AUTO_ENGAGE_MAX_FOLLOWS_DAY", "50"))
TWITTER_MAX_LIKES_PER_DAY = int(os.getenv("AUTO_ENGAGE_MAX_LIKES_DAY", "200"))

# In-memory daily counters — reset automatically at midnight UTC
_daily: Dict[str, Any] = {"date": None, "follows": 0, "likes": 0}


def _get_firestore():
    from google.cloud import firestore
    return firestore.AsyncClient(project=GCP_PROJECT)


def _reset_daily_if_needed() -> None:
    today = date.today().isoformat()
    if _daily["date"] != today:
        _daily.update({"date": today, "follows": 0, "likes": 0})


def _twitter_ready() -> bool:
    return all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET])


async def _get_latest_tweet_id(client: httpx.AsyncClient, user_id: str) -> Optional[str]:
    """Return the most recent tweet ID for a Twitter user, or None."""
    url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {"max_results": "5", "tweet.fields": "id"}
    try:
        auth = _twitter_oauth1_header("GET", url, params)
        r = await client.get(url, headers={"Authorization": auth}, params=params, timeout=15)
        tweets = r.json().get("data", [])
        return tweets[0]["id"] if tweets else None
    except Exception as e:
        logger.error("Failed to fetch tweets for user %s: %s", user_id, e)
        return None


async def _twitter_like(client: httpx.AsyncClient, tweet_id: str) -> bool:
    """Like a tweet. Returns True on success."""
    if not TWITTER_MY_USER_ID:
        logger.warning("TWITTER_MY_USER_ID not set — skipping like")
        return False
    url = f"https://api.twitter.com/2/users/{TWITTER_MY_USER_ID}/likes"
    try:
        auth = _twitter_oauth1_header("POST", url, {})
        r = await client.post(
            url,
            headers={"Authorization": auth, "Content-Type": "application/json"},
            json={"tweet_id": tweet_id},
            timeout=15,
        )
        return r.json().get("data", {}).get("liked", False)
    except Exception as e:
        logger.error("Twitter like error tweet=%s: %s", tweet_id, e)
        return False


async def _twitter_follow(client: httpx.AsyncClient, target_user_id: str) -> bool:
    """Follow a user. Returns True on success."""
    if not TWITTER_MY_USER_ID:
        logger.warning("TWITTER_MY_USER_ID not set — skipping follow")
        return False
    url = f"https://api.twitter.com/2/users/{TWITTER_MY_USER_ID}/following"
    try:
        auth = _twitter_oauth1_header("POST", url, {})
        r = await client.post(
            url,
            headers={"Authorization": auth, "Content-Type": "application/json"},
            json={"target_user_id": target_user_id},
            timeout=15,
        )
        return r.json().get("data", {}).get("following", False)
    except Exception as e:
        logger.error("Twitter follow error user=%s: %s", target_user_id, e)
        return False


async def run_once() -> Dict[str, Any]:
    """
    Run one auto-engage cycle. Pulls top-scored unengaged users from Firestore,
    likes their latest tweet and follows them on Twitter.
    """
    _reset_daily_if_needed()

    if not _twitter_ready():
        logger.warning("Auto-engage: Twitter credentials not configured, skipping")
        return {"skipped": "twitter_credentials_missing", "follows": 0, "likes": 0}

    follows_remaining = TWITTER_MAX_FOLLOWS_PER_DAY - _daily["follows"]
    likes_remaining = TWITTER_MAX_LIKES_PER_DAY - _daily["likes"]

    if follows_remaining <= 0 and likes_remaining <= 0:
        logger.info("Auto-engage: daily rate limits reached")
        return {
            "skipped": "daily_limit_reached",
            "follows": 0,
            "likes": 0,
            "daily_totals": dict(_daily),
        }

    db = _get_firestore()
    follows_done = 0
    likes_done = 0
    errors: List[str] = []

    try:
        query = (
            db.collection_group("users")
            .where("platform", "==", "twitter")
            .where("engaged", "==", False)
            .order_by("score", direction="DESCENDING")
            .limit(follows_remaining + likes_remaining)
        )
        docs = await query.get()
    except Exception as e:
        logger.error("Firestore query failed in auto-engage: %s", e)
        return {"error": str(e), "follows": 0, "likes": 0}

    async with httpx.AsyncClient() as client:
        for doc in docs:
            data = doc.to_dict()
            user_id = str(data.get("platform_user_id", ""))
            username = data.get("username", user_id)
            if not user_id:
                continue

            liked = False
            followed = False

            if likes_remaining > 0:
                tweet_id = await _get_latest_tweet_id(client, user_id)
                if tweet_id:
                    liked = await _twitter_like(client, tweet_id)
                    if liked:
                        likes_done += 1
                        _daily["likes"] += 1
                        likes_remaining -= 1

            if follows_remaining > 0:
                followed = await _twitter_follow(client, user_id)
                if followed:
                    follows_done += 1
                    _daily["follows"] += 1
                    follows_remaining -= 1

            if liked or followed:
                try:
                    await doc.reference.update({
                        "engaged": True,
                        "followed": followed,
                        "liked": liked,
                        "engaged_at": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    errors.append(f"Firestore update failed for {username}: {e}")

                logger.info("Auto-engaged @%s — liked=%s followed=%s", username, liked, followed)

            if follows_remaining <= 0 and likes_remaining <= 0:
                break

            await asyncio.sleep(0.5)  # gentle pacing

    result = {
        "follows": follows_done,
        "likes": likes_done,
        "daily_totals": {"follows": _daily["follows"], "likes": _daily["likes"]},
        "limits": {"follows": TWITTER_MAX_FOLLOWS_PER_DAY, "likes": TWITTER_MAX_LIKES_PER_DAY},
        "errors": errors,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Auto-engage complete: %s", result)
    return result


def daily_status() -> Dict[str, Any]:
    """Return current daily counter state without running a cycle."""
    _reset_daily_if_needed()
    return {
        "today": _daily.get("date"),
        "follows_today": _daily.get("follows", 0),
        "likes_today": _daily.get("likes", 0),
        "follows_remaining": max(0, TWITTER_MAX_FOLLOWS_PER_DAY - _daily.get("follows", 0)),
        "likes_remaining": max(0, TWITTER_MAX_LIKES_PER_DAY - _daily.get("likes", 0)),
        "limits": {
            "follows_per_day": TWITTER_MAX_FOLLOWS_PER_DAY,
            "likes_per_day": TWITTER_MAX_LIKES_PER_DAY,
        },
    }
