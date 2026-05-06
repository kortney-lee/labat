"""
maya/services/twitter_stream_service.py — Twitter v2 Filtered Stream listener.

Connects to the Twitter Filtered Stream API using Bearer Token auth.
Sets up rules for brand mentions and health keyword discovery, then
streams matching tweets in real-time and routes them to engagement
or audience discovery pipelines.

Stream rules managed:
  mention         — tweets mentioning @wihyhealthbot → immediate engagement
  discovery_wihy  — health/nutrition keywords → WIHY audience signals
  discovery_vowels— nutrition science keywords → Vowels audience signals
  discovery_cg    — budget food keywords → Community Groceries signals
  discovery_cn    — kids nutrition keywords → Children Nutrition signals
  trends          — broad trending health signals → trend tracking

On match:
  mention tags    → engage_lead() queued as background task
  discovery_*     → stored in audience_discovery Firestore
  trends          → stored in twitter_trends Firestore collection

Reconnects automatically with exponential backoff on disconnect.

Required env vars:
  TWITTER_BEARER_TOKEN  — App-only bearer token (already in GCP Secret Manager)
  TWITTER_BOT_USERNAME  — e.g. wihyhealthbot (for mention detection)
  GCP_PROJECT           — defaults to "wihy-ai"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("maya.twitter_stream")

TWITTER_BEARER_TOKEN = (os.getenv("TWITTER_BEARER_TOKEN", "") or "").strip()
TWITTER_BOT_USERNAME = (os.getenv("TWITTER_BOT_USERNAME", "wihyhealthbot") or "wihyhealthbot").strip()
GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")

STREAM_URL = "https://api.twitter.com/2/tweets/search/stream"
RULES_URL  = "https://api.twitter.com/2/tweets/search/stream/rules"

# Reconnect: start at 1s, double each attempt, cap at 5 minutes
_BACKOFF_START = 1
_BACKOFF_MAX   = 300

# Stream rules — tag → Firestore routing
STREAM_RULES: List[Dict[str, str]] = [
    {
        "value": f"@{TWITTER_BOT_USERNAME} -is:retweet",
        "tag": "mention",
    },
    {
        "value": "(nutrition OR \"healthy eating\" OR \"meal prep\" OR \"gut health\" OR intermittentfasting) lang:en -is:retweet -is:reply",
        "tag": "discovery_wihy",
    },
    {
        "value": "(\"evidence based nutrition\" OR dietitian OR \"metabolic health\" OR \"blood sugar\" OR macros) lang:en -is:retweet -is:reply",
        "tag": "discovery_vowels",
    },
    {
        "value": "(\"budget meal\" OR \"affordable food\" OR \"cheap healthy\" OR \"grocery tips\" OR \"meal plan budget\") lang:en -is:retweet -is:reply",
        "tag": "discovery_cg",
    },
    {
        "value": "(\"kids nutrition\" OR \"children diet\" OR \"school lunch\" OR \"picky eater\" OR \"kids healthy\") lang:en -is:retweet -is:reply",
        "tag": "discovery_cn",
    },
]

# Brand mapping for discovery tags
_TAG_TO_BRAND = {
    "discovery_wihy":   "wihy",
    "discovery_vowels": "vowels",
    "discovery_cg":     "communitygroceries",
    "discovery_cn":     "childrennutrition",
}


def _get_firestore():
    from google.cloud import firestore
    return firestore.AsyncClient(project=GCP_PROJECT)


def _bearer_headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}


# ── Rule management ───────────────────────────────────────────────────────────

async def _get_existing_rules(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    r = await client.get(RULES_URL, headers=_bearer_headers(), timeout=15)
    return r.json().get("data") or []


async def _delete_rules(client: httpx.AsyncClient, rule_ids: List[str]) -> None:
    if not rule_ids:
        return
    await client.post(
        RULES_URL,
        headers=_bearer_headers(),
        json={"delete": {"ids": rule_ids}},
        timeout=15,
    )
    logger.info("Deleted %d existing stream rules", len(rule_ids))


async def _add_rules(client: httpx.AsyncClient) -> None:
    payload = {"add": [{"value": r["value"], "tag": r["tag"]} for r in STREAM_RULES]}
    r = await client.post(RULES_URL, headers=_bearer_headers(), json=payload, timeout=15)
    data = r.json()
    if "errors" in data:
        logger.warning("Stream rule errors: %s", data["errors"])
    added = len((data.get("data") or []))
    logger.info("Added %d stream rules", added)


async def sync_rules(client: httpx.AsyncClient) -> None:
    """Replace existing stream rules with current STREAM_RULES list."""
    existing = await _get_existing_rules(client)
    if existing:
        await _delete_rules(client, [r["id"] for r in existing])
    await _add_rules(client)
    logger.info("Stream rules synced: %s", [r["tag"] for r in STREAM_RULES])


# ── Event routing ─────────────────────────────────────────────────────────────

async def _handle_mention(tweet_id: str, text: str, author_id: str) -> None:
    """Queue a mention for engagement via engage_lead."""
    try:
        from src.maya.services.engagement_poster_service import engage_lead
        asyncio.ensure_future(engage_lead(
            platform="twitter",
            action="reply",
            target_id=tweet_id,
            post_content=text,
            topic="health nutrition wellness",
            lead_id=None,
            author=author_id,
            conversation_tweet_id=tweet_id,
        ))
        logger.info("Mention queued for engagement: tweet_id=%s", tweet_id)
    except Exception as e:
        logger.error("Failed to queue mention engagement: %s", e)


async def _handle_discovery(
    db,
    tag: str,
    tweet: Dict[str, Any],
    user: Optional[Dict[str, Any]],
) -> None:
    """Store discovered user in Firestore audience_discovery collection."""
    if not user:
        return
    brand = _TAG_TO_BRAND.get(tag, "wihy")
    user_id = user.get("id")
    if not user_id:
        return

    metrics = user.get("public_metrics", {})
    followers = metrics.get("followers_count", 0)
    following = metrics.get("following_count", 1) or 1

    if followers < 50 or followers > 500_000:
        return

    ratio = min(followers / following, 10.0)
    score = round(ratio * 5, 2)

    ref = (
        db.collection("audience_discovery")
        .document("twitter")
        .collection("users")
        .document(str(user_id))
    )
    existing = await ref.get()
    if existing.exists:
        return

    await ref.set({
        "platform": "twitter",
        "brand": brand,
        "discovery_source": f"stream:{tag}",
        "platform_user_id": user_id,
        "username": user.get("username", ""),
        "name": user.get("name", ""),
        "description": user.get("description", ""),
        "followers_count": followers,
        "friends_count": following,
        "score": score,
        "engaged": False,
        "followed": False,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.debug("Discovered @%s via stream tag=%s brand=%s", user.get("username"), tag, brand)


async def _route_event(db, event: Dict[str, Any]) -> None:
    """Route a matched stream event to the appropriate handler."""
    tweet = event.get("data", {})
    tweet_id = tweet.get("id", "")
    text = tweet.get("text", "")
    author_id = tweet.get("author_id", "")

    # Extract author user object from expansions
    users = {u["id"]: u for u in event.get("includes", {}).get("users", [])}
    author = users.get(author_id)

    matching_rules = event.get("matching_rules", [])
    tags = {r.get("tag", "") for r in matching_rules}

    for tag in tags:
        if tag == "mention":
            await _handle_mention(tweet_id, text, author_id)
        elif tag.startswith("discovery_"):
            await _handle_discovery(db, tag, tweet, author)


# ── Stream connection ─────────────────────────────────────────────────────────

class TwitterStreamService:
    """
    Background service that connects to Twitter Filtered Stream API and
    processes matching tweets in real-time.
    """

    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._connected = False
        self._total_received = 0
        self._last_event: Optional[str] = None
        self._reconnect_count = 0

    def status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "connected": self._connected,
            "total_received": self._total_received,
            "reconnect_count": self._reconnect_count,
            "last_event": self._last_event,
            "rules": [r["tag"] for r in STREAM_RULES],
        }

    async def start(self) -> None:
        if not TWITTER_BEARER_TOKEN:
            logger.warning("TWITTER_BEARER_TOKEN not set — stream service disabled")
            return
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("TwitterStreamService started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("TwitterStreamService stopped")

    async def _run(self) -> None:
        backoff = _BACKOFF_START
        db = _get_firestore()
        rules_synced = False

        while self._running:
            try:
                # Sync rules once on first connect, not on every reconnect
                if not rules_synced:
                    async with httpx.AsyncClient() as setup_client:
                        try:
                            await sync_rules(setup_client)
                            rules_synced = True
                        except Exception as e:
                            logger.error("Failed to sync stream rules: %s", e)

                await self._connect_and_stream(db)
                backoff = _BACKOFF_START  # reset on clean disconnect
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Stream error (reconnecting in %ds): %s", backoff, e)
                self._connected = False
                self._reconnect_count += 1
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _connect_and_stream(self, db) -> None:
        params = {
            "tweet.fields": "author_id,text,created_at",
            "user.fields": "id,username,name,description,public_metrics",
            "expansions": "author_id",
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                STREAM_URL,
                headers=_bearer_headers(),
                params=params,
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(f"Stream returned {response.status_code}: {body[:200]}")

                self._connected = True
                logger.info("Connected to Twitter Filtered Stream")

                async for line in response.aiter_lines():
                    if not self._running:
                        break
                    if not line.strip():
                        continue  # heartbeat keepalive
                    try:
                        event = json.loads(line)
                        self._total_received += 1
                        self._last_event = datetime.now(timezone.utc).isoformat()
                        asyncio.ensure_future(_route_event(db, event))
                    except json.JSONDecodeError:
                        logger.debug("Non-JSON stream line: %s", line[:100])


# Module-level singleton
twitter_stream_service = TwitterStreamService()
