"""
maya/services/twitter_trends_service.py — Twitter Trends API poller.

Fetches worldwide and US trending topics every hour using the Twitter v1.1
Trends API (Elevated access, OAuth 1.0a). Filters for health-relevant trends
and stores them in Firestore for two consumers:

  Maya  — uses trends as content topics for social posts
  Alex  — picks up trends as SEO keyword signals for content generation

Firestore path: twitter_trends/{woeid}/snapshots/{timestamp}
Latest trends: twitter_trends/{woeid}/latest (single doc, always overwritten)

WOEIDs used:
  1         — Worldwide
  23424977  — United States
  2391279   — Los Angeles
  2459115   — New York City

Health filter: trends that contain any keyword in HEALTH_KEYWORDS are flagged
as relevant and surfaced to Alex's keyword discovery pipeline.

Required env vars:
  TWITTER_API_KEY, TWITTER_API_SECRET
  TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
  GCP_PROJECT — defaults to "wihy-ai"
"""

from __future__ import annotations

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
    _twitter_oauth1_header,
)

logger = logging.getLogger("maya.twitter_trends")

GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")

TRENDS_URL = "https://api.twitter.com/1.1/trends/place.json"

# WOEIDs to poll — worldwide first for broadest signal
WOEIDS: List[Dict[str, Any]] = [
    {"id": 1,        "name": "worldwide"},
    {"id": 23424977, "name": "united_states"},
    {"id": 2459115,  "name": "new_york"},
    {"id": 2391279,  "name": "los_angeles"},
]

# Terms that flag a trend as health-relevant
HEALTH_KEYWORDS = {
    "health", "nutrition", "diet", "food", "eat", "eating", "weight",
    "fitness", "workout", "exercise", "protein", "sugar", "calories",
    "meal", "recipe", "gut", "inflammation", "diabetes", "obesity",
    "vitamin", "supplement", "organic", "vegan", "keto", "fasting",
    "wellness", "mental health", "sleep", "stress", "immune",
    "cancer", "heart", "blood", "cholesterol", "metabolism",
}


def _get_firestore():
    from google.cloud import firestore
    return firestore.AsyncClient(project=GCP_PROJECT)


def _is_health_relevant(trend_name: str) -> bool:
    lower = trend_name.lower()
    return any(kw in lower for kw in HEALTH_KEYWORDS)


async def _fetch_trends(client: httpx.AsyncClient, woeid: int) -> List[Dict[str, Any]]:
    """Fetch trends for a WOEID via Twitter v1.1 API with OAuth 1.0a."""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        return []

    params = {"id": str(woeid)}
    url = TRENDS_URL

    try:
        auth = _twitter_oauth1_header("GET", url, params)
        r = await client.get(
            url,
            headers={"Authorization": auth},
            params=params,
            timeout=15,
        )
        data = r.json()
        if isinstance(data, list) and data:
            return data[0].get("trends", [])
        return []
    except Exception as e:
        logger.error("Trends fetch error woeid=%d: %s", woeid, e)
        return []


async def run_once() -> Dict[str, Any]:
    """
    Poll trends for all WOEIDs, flag health-relevant trends,
    and store results in Firestore. Returns summary.
    """
    db = _get_firestore()
    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    total_health = 0
    all_health_trends: List[Dict[str, Any]] = []
    errors: List[str] = []

    async with httpx.AsyncClient() as client:
        for geo in WOEIDS:
            woeid = geo["id"]
            geo_name = geo["name"]

            try:
                raw_trends = await _fetch_trends(client, woeid)
                if not raw_trends:
                    continue

                processed = []
                health_trends = []

                for t in raw_trends:
                    name = t.get("name", "")
                    relevant = _is_health_relevant(name)
                    entry = {
                        "name": name,
                        "tweet_volume": t.get("tweet_volume"),
                        "url": t.get("url", ""),
                        "health_relevant": relevant,
                        "woeid": woeid,
                        "geo": geo_name,
                        "fetched_at": timestamp,
                    }
                    processed.append(entry)
                    if relevant:
                        health_trends.append(entry)
                        all_health_trends.append(entry)
                        total_health += 1

                # Store snapshot
                snapshot_ref = (
                    db.collection("twitter_trends")
                    .document(str(woeid))
                    .collection("snapshots")
                    .document(timestamp.replace(":", "-").replace(".", "-"))
                )
                await snapshot_ref.set({
                    "woeid": woeid,
                    "geo": geo_name,
                    "trends": processed,
                    "health_trend_count": len(health_trends),
                    "fetched_at": timestamp,
                })

                # Overwrite latest doc — always the most recent snapshot
                latest_ref = db.collection("twitter_trends").document(str(woeid))
                await latest_ref.set({
                    "woeid": woeid,
                    "geo": geo_name,
                    "trends": processed,
                    "health_trends": health_trends,
                    "health_trend_count": len(health_trends),
                    "total_trends": len(processed),
                    "updated_at": timestamp,
                })

                logger.info(
                    "Trends fetched geo=%s total=%d health=%d",
                    geo_name, len(processed), len(health_trends)
                )

            except Exception as e:
                msg = f"Trend store error geo={geo_name}: {e}"
                logger.error(msg)
                errors.append(msg)

    result = {
        "geos_polled": [g["name"] for g in WOEIDS],
        "total_health_trends": total_health,
        "top_health_trends": sorted(
            all_health_trends,
            key=lambda x: x.get("tweet_volume") or 0,
            reverse=True,
        )[:10],
        "errors": errors,
        "ran_at": timestamp,
    }
    logger.info("Trends poll complete: %d health-relevant trends found", total_health)
    return result


async def get_latest_health_trends(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Read the latest health-relevant trends from Firestore.
    Used by Alex for SEO keyword signals and Maya for content topic selection.
    """
    db = _get_firestore()
    seen: set = set()
    trends: List[Dict[str, Any]] = []

    for geo in WOEIDS:
        try:
            doc = await db.collection("twitter_trends").document(str(geo["id"])).get()
            if not doc.exists:
                continue
            for t in doc.to_dict().get("health_trends", []):
                name = t.get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    trends.append(t)
        except Exception as e:
            logger.error("Failed to read trends for woeid=%d: %s", geo["id"], e)

    return sorted(trends, key=lambda x: x.get("tweet_volume") or 0, reverse=True)[:limit]
