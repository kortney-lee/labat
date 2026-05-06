"""
maya/routers/twitter_webhook_routes.py — Twitter Account Activity API webhook handler.

Handles Twitter's push-based real-time event delivery (requires Pro tier).
Twitter sends events here for: mentions, DMs, follows, likes, retweets.

Endpoints:
  GET  /api/engagement/twitter/webhook  — CRC challenge (one-time webhook verification)
  POST /api/engagement/twitter/webhook  — Event ingestion (HMAC-SHA256 signed)

ONE-TIME SETUP (after upgrading to Twitter Pro):
  1. Register the webhook URL with Twitter:
       curl -X POST "https://api.twitter.com/1.1/account_activity/all/prod/webhooks.json" \
         --data "url=https://wihy-maya-12913076533.us-central1.run.app/api/engagement/twitter/webhook"
         -H "Authorization: Bearer <TWITTER_BEARER_TOKEN>"
  2. Subscribe your account:
       curl -X POST "https://api.twitter.com/1.1/account_activity/all/prod/subscriptions.json" \
         -H "Authorization: OAuth ..."   (user-context OAuth 1.0a)

Events handled:
  tweet_create_events   — replies/mentions → engagement pipeline
  follow_events         — new followers → audience discovery record
  direct_message_events — DMs → logged to Firestore (manual review)
  favorite_events       — likes on our tweets → logged

Required env vars:
  TWITTER_API_SECRET  — Consumer secret, used to verify HMAC-SHA256 signature
  TWITTER_BEARER_TOKEN — Bearer token for response signing
  GCP_PROJECT          — defaults to "wihy-ai"
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response

logger = logging.getLogger("twitter_webhook")

TWITTER_API_SECRET  = (os.getenv("TWITTER_API_SECRET", "") or "").strip()
TWITTER_BEARER_TOKEN = (os.getenv("TWITTER_BEARER_TOKEN", "") or "").strip()
GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")

router = APIRouter(prefix="/api/engagement/twitter", tags=["twitter-webhook"])


# ── CRC Challenge ─────────────────────────────────────────────────────────────

@router.get("/webhook")
async def crc_challenge(crc_token: str = Query(...)):
    """
    Twitter Account Activity API CRC challenge.
    Twitter calls this once when registering the webhook URL.
    Must respond with HMAC-SHA256 of the crc_token signed with consumer secret.
    """
    if not TWITTER_API_SECRET:
        raise HTTPException(status_code=500, detail="TWITTER_API_SECRET not configured")

    digest = hmac.new(
        TWITTER_API_SECRET.encode("utf-8"),
        crc_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    response_token = "sha256=" + base64.b64encode(digest).decode("utf-8")
    return {"response_token": response_token}


# ── Signature Verification ────────────────────────────────────────────────────

def _verify_signature(body: bytes, signature_header: str) -> bool:
    """Verify Twitter's HMAC-SHA256 payload signature."""
    if not TWITTER_API_SECRET or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + base64.b64encode(
        hmac.new(TWITTER_API_SECRET.encode(), body, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(expected, signature_header)


# ── Event Handlers ────────────────────────────────────────────────────────────

async def _handle_tweet_create(events: list) -> None:
    """Route incoming tweets/mentions to engagement pipeline."""
    try:
        from src.maya.services.engagement_poster_service import engage_lead
        import asyncio
        for tweet in events:
            tweet_id = tweet.get("id_str", "")
            text = tweet.get("text", "")
            user = tweet.get("user", {})
            username = user.get("screen_name", "")
            if not tweet_id or not text:
                continue
            logger.info("AAA mention from @%s tweet=%s", username, tweet_id)
            asyncio.ensure_future(engage_lead(
                platform="twitter",
                action="reply",
                target_id=tweet_id,
                post_content=text,
                topic="health nutrition wellness",
                lead_id=None,
                author=username,
                conversation_tweet_id=tweet_id,
            ))
    except Exception as e:
        logger.error("tweet_create_events handler error: %s", e)


async def _handle_follow(events: list) -> None:
    """Record new followers in Firestore audience_discovery."""
    from google.cloud import firestore
    db = firestore.AsyncClient(project=GCP_PROJECT)
    now = datetime.now(timezone.utc).isoformat()

    for event in events:
        user = event.get("source", {})
        user_id = user.get("id_str", "")
        if not user_id:
            continue
        ref = (
            db.collection("audience_discovery")
            .document("twitter")
            .collection("users")
            .document(user_id)
        )
        existing = await ref.get()
        if existing.exists:
            await ref.update({"followed_us": True, "followed_us_at": now})
        else:
            await ref.set({
                "platform": "twitter",
                "brand": "wihy",
                "discovery_source": "account_activity:follow",
                "platform_user_id": user_id,
                "username": user.get("screen_name", ""),
                "name": user.get("name", ""),
                "followers_count": user.get("followers_count", 0),
                "friends_count": user.get("friends_count", 0),
                "score": 60.0,  # following us = high intent
                "engaged": False,
                "followed": False,
                "followed_us": True,
                "discovered_at": now,
                "followed_us_at": now,
            })
        logger.info("New follower recorded: @%s", user.get("screen_name"))


async def _handle_dm(events: list) -> None:
    """Log incoming DMs to Firestore for manual review."""
    from google.cloud import firestore
    db = firestore.AsyncClient(project=GCP_PROJECT)
    now = datetime.now(timezone.utc).isoformat()

    for event in events:
        msg_data = event.get("message_create", {})
        sender_id = msg_data.get("sender_id", "")
        text = msg_data.get("message_data", {}).get("text", "")
        dm_id = event.get("id", "")

        if not sender_id or not dm_id:
            continue

        await (
            db.collection("twitter_dms")
            .document(dm_id)
            .set({
                "dm_id": dm_id,
                "sender_id": sender_id,
                "text": text,
                "received_at": now,
                "reviewed": False,
            })
        )
        logger.info("DM logged from user_id=%s (manual review needed)", sender_id)


# ── Main Webhook Handler ──────────────────────────────────────────────────────

@router.post("/webhook")
async def receive_events(request: Request, background_tasks: BackgroundTasks):
    """
    Receive and route Twitter Account Activity API events.
    Verifies HMAC-SHA256 signature before processing.
    """
    body = await request.body()
    signature = request.headers.get("x-twitter-webhooks-signature", "")

    if TWITTER_API_SECRET and not _verify_signature(body, signature):
        logger.warning("Twitter webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload: Dict[str, Any] = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Route events by type
    if "tweet_create_events" in payload:
        background_tasks.add_task(_handle_tweet_create, payload["tweet_create_events"])

    if "follow_events" in payload:
        background_tasks.add_task(_handle_follow, payload["follow_events"])

    if "direct_message_events" in payload:
        background_tasks.add_task(_handle_dm, payload["direct_message_events"])

    if "favorite_events" in payload:
        logger.info("Received %d favorite events", len(payload["favorite_events"]))

    return Response(status_code=200)


# ── Status Endpoint ───────────────────────────────────────────────────────────

@router.get("/webhook/status")
async def webhook_status():
    """Report whether the webhook handler is configured and ready."""
    return {
        "endpoint": "/api/engagement/twitter/webhook",
        "crc_ready": bool(TWITTER_API_SECRET),
        "signature_verification": bool(TWITTER_API_SECRET),
        "note": "Account Activity API requires Twitter Pro tier. Register webhook URL once upgraded.",
        "events_handled": [
            "tweet_create_events",
            "follow_events",
            "direct_message_events",
            "favorite_events",
        ],
    }
