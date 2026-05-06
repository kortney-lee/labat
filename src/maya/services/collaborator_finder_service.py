"""
maya/services/collaborator_finder_service.py — Find potential collaborators in health/nutrition niche.

Searches Twitter for creators and accounts in the health/wellness space with
meaningful audiences (5K–500K followers). Scores them by engagement ratio and
content relevance, stores candidates in Firestore, and emails a report to
kortney@wihy.ai after each cycle.

Runs every 24 hours via maya_app.py background loop.
Firestore path: collaborators/{brand}/candidates/{user_id}

Required env vars:
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
  GCP_PROJECT          — defaults to "wihy-ai"
  COLLAB_MIN_FOLLOWERS — minimum followers to qualify (default 5000)
  COLLAB_MAX_FOLLOWERS — maximum followers to qualify (default 500000)
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
    _twitter_oauth1_header,
)

logger = logging.getLogger("maya.collaborator_finder")

GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")
COLLAB_MIN_FOLLOWERS = int(os.getenv("COLLAB_MIN_FOLLOWERS", "5000"))
COLLAB_MAX_FOLLOWERS = int(os.getenv("COLLAB_MAX_FOLLOWERS", "500000"))

# Search queries per brand — finds creators already talking about these topics
BRAND_SEARCH_QUERIES: Dict[str, List[str]] = {
    "wihy": [
        "healthy eating tips", "nutrition advice", "meal prep ideas",
        "weight loss nutrition", "gut health tips",
    ],
    "vowels": [
        "evidence based nutrition", "nutrition science", "dietitian advice",
        "metabolic health", "blood sugar control",
    ],
    "communitygroceries": [
        "budget meal prep", "affordable healthy food", "grocery tips",
        "cheap healthy meals", "frugal eating",
    ],
    "childrennutrition": [
        "kids nutrition", "healthy school lunch", "children diet",
        "family nutrition tips", "picky eater help",
    ],
}


def _get_firestore():
    from google.cloud import firestore
    return firestore.AsyncClient(project=GCP_PROJECT)


def _score_collaborator(followers: int, following: int, tweet_count: int, listed: int) -> float:
    """Score collaborator fitness 0–100. Returns 0 if outside follower range."""
    if followers < COLLAB_MIN_FOLLOWERS or followers > COLLAB_MAX_FOLLOWERS:
        return 0.0
    ratio = min(followers / max(following, 1), 20.0)
    authority = min(listed / 100, 10.0)
    activity = min(tweet_count / 1000, 5.0)
    return round(ratio * 4 + authority * 4 + activity * 2, 2)


async def _search_twitter_for_collaborators(
    client: httpx.AsyncClient,
    query: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Search recent tweets for a query. Returns unique authors with follower data."""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        return []

    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": f"{query} lang:en -is:retweet",
        "tweet.fields": "author_id",
        "user.fields": "id,username,name,description,public_metrics,verified,url",
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
        return data.get("includes", {}).get("users", [])
    except Exception as e:
        logger.error("Twitter collaborator search error (%r): %s", query, e)
        return []


async def run_once(brand: str = "all") -> Dict[str, Any]:
    """
    Run one collaborator discovery cycle. Stores candidates in Firestore
    and emails a report. Returns summary.
    """
    brands = list(BRAND_SEARCH_QUERIES.keys()) if brand == "all" else [brand]
    total_new = 0
    top_candidates: List[Dict[str, Any]] = []
    errors: List[str] = []

    db = _get_firestore()

    async with httpx.AsyncClient() as client:
        for b in brands:
            for query in BRAND_SEARCH_QUERIES.get(b, []):
                try:
                    users = await _search_twitter_for_collaborators(client, query)
                    for u in users:
                        metrics = u.get("public_metrics", {})
                        followers = metrics.get("followers_count", 0)
                        following = metrics.get("following_count", 0)
                        tweet_count = metrics.get("tweet_count", 0)
                        listed = metrics.get("listed_count", 0)
                        score = _score_collaborator(followers, following, tweet_count, listed)
                        if score <= 0:
                            continue

                        flat = {
                            "platform": "twitter",
                            "brand": b,
                            "discovery_query": query,
                            "platform_user_id": u.get("id"),
                            "username": u.get("username", ""),
                            "name": u.get("name", ""),
                            "description": u.get("description", ""),
                            "url": u.get("url", ""),
                            "followers_count": followers,
                            "following_count": following,
                            "tweet_count": tweet_count,
                            "listed_count": listed,
                            "verified": u.get("verified", False),
                            "score": score,
                        }

                        ref = (
                            db.collection("collaborators")
                            .document(b)
                            .collection("candidates")
                            .document(str(u.get("id")))
                        )
                        existing = await ref.get()
                        if not existing.exists:
                            await ref.set({
                                **flat,
                                "status": "pending",
                                "outreach_approved": False,
                                "discovered_at": datetime.now(timezone.utc).isoformat(),
                            })
                            total_new += 1
                        else:
                            await ref.update({
                                "score": score,
                                "last_seen": datetime.now(timezone.utc).isoformat(),
                            })

                        top_candidates.append({
                            "brand": b,
                            "username": flat["username"],
                            "followers": followers,
                            "score": score,
                            "description": flat["description"][:120],
                        })

                    await asyncio.sleep(1)

                except Exception as e:
                    msg = f"Collaborator search error brand={b} query={query!r}: {e}"
                    logger.error(msg)
                    errors.append(msg)

    if top_candidates:
        top_candidates.sort(key=lambda x: x["score"], reverse=True)
        await _send_report(top_candidates[:20], total_new)

    result = {
        "brands_scanned": brands,
        "total_new": total_new,
        "top_candidates": top_candidates[:10],
        "errors": errors,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Collaborator discovery complete: %s", result)
    return result


async def _send_report(candidates: List[Dict[str, Any]], total_new: int) -> None:
    """Email top collaborator candidates to kortney@wihy.ai via SendGrid."""
    try:
        from src.labat.services.notify import send_notification
        rows = "\n".join(
            f"• @{c['username']} ({c['brand']}) — {c['followers']:,} followers, score {c['score']}\n"
            f"  {c['description']}"
            for c in candidates
        )
        await send_notification(
            agent="maya-collaborator-finder",
            severity="info",
            title=f"Collaborator Report: {total_new} new candidates found",
            message=rows,
            service="maya",
            details={"candidates": candidates, "total_new": total_new},
        )
    except Exception as e:
        logger.error("Failed to send collaborator report: %s", e)
