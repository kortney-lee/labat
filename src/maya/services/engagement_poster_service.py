"""
engagement_poster_service.py — WIHY engagement engine

Called by the lead-service (auth.wihy.ai) to engage with discovered leads.
For each lead, this service:
  1. Generates a WIHY-toned, RAG-grounded comment using ml.wihy.ai/ask
  2. Posts the comment to the target platform using the platform's API
  3. Returns confirmation + the posted content
  4. Registers the comment with ThreadMonitor, which polls for replies every 5 min
     and auto-posts WIHY responses to replies (up to THREAD_MAX_DEPTH levels deep)

Supported platforms:
  twitter   — Tweet reply via v2 /tweets + thread monitoring
  instagram — Meta Graph API comment (instagram_manage_comments scope)
  facebook  — Meta Graph API comment (pages_manage_engagement scope)
  threads   — Threads Publishing API reply (threads_manage_replies scope)
  tiktok    — TikTok for Developers API comment (tt.user.comment scope)
  generic   — Returns generated text only (client posts it)

Environment variables:
  TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
  TWITTER_BOT_USERNAME       — Twitter handle (e.g. wihyhealthbot), used to exclude self from reply search
  INSTAGRAM_ACCESS_TOKEN     — Long-lived Meta Graph API token with instagram_manage_comments
  FACEBOOK_ACCESS_TOKEN      — Page access token with pages_manage_engagement
  THREADS_ACCESS_TOKEN       — Long-lived token with threads_manage_replies scope
  TIKTOK_ACCESS_TOKEN        — TikTok for Developers access token with tt.user.comment scope
  THREAD_POLL_INTERVAL       — Seconds between reply polls (default: 300)
  THREAD_MAX_DEPTH           — Max reply chain depth (default: 2)
  WIHY_ASK_URL               — Override ml.wihy.ai/ask (default: https://ml.wihy.ai/ask)
"""

import asyncio
import base64
import dataclasses
import hashlib
import hmac
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger("engagement_poster")

WIHY_ASK = os.getenv("WIHY_ASK_URL", "https://ml.wihy.ai/ask")

# Twitter
TWITTER_API_KEY              = (os.getenv("TWITTER_API_KEY", "") or "").strip()
TWITTER_API_SECRET           = (os.getenv("TWITTER_API_SECRET", "") or "").strip()
TWITTER_ACCESS_TOKEN         = (os.getenv("TWITTER_ACCESS_TOKEN", "") or "").strip()
TWITTER_ACCESS_TOKEN_SECRET  = (os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "") or "").strip()
TWITTER_BOT_USERNAME         = (os.getenv("TWITTER_BOT_USERNAME", "") or "").strip()  # e.g. wihyhealthbot

# Instagram (Meta Graph API — long-lived page token with instagram_manage_comments)
INSTAGRAM_ACCESS_TOKEN      = (os.getenv("INSTAGRAM_ACCESS_TOKEN", "") or "").strip()
INSTAGRAM_GRAPH_VERSION      = os.getenv("INSTAGRAM_GRAPH_VERSION", "v19.0")

# Facebook (Meta Graph API — page access token with pages_manage_engagement)
FACEBOOK_ACCESS_TOKEN        = (os.getenv("FACEBOOK_ACCESS_TOKEN", "") or "").strip()
FACEBOOK_GRAPH_VERSION       = os.getenv("FACEBOOK_GRAPH_VERSION", "v19.0")

# TikTok (TikTok for Developers — requires tt.user.comment scope)
TIKTOK_ACCESS_TOKEN          = (os.getenv("TIKTOK_ACCESS_TOKEN", "") or "").strip()

# Threads (Meta Threads Publishing API — requires threads_manage_replies scope)
# Falls back to INSTAGRAM_ACCESS_TOKEN since Threads uses the same IG business account
THREADS_ACCESS_TOKEN         = (os.getenv("THREADS_ACCESS_TOKEN", "") or os.getenv("INSTAGRAM_ACCESS_TOKEN", "") or "").strip()

# Thread monitor — how often to poll for new replies (seconds)
THREAD_POLL_INTERVAL         = int(os.getenv("THREAD_POLL_INTERVAL", "300"))  # 5 min default
THREAD_MAX_DEPTH             = int(os.getenv("THREAD_MAX_DEPTH", "2"))        # don't chain > 2 deep

# Max comment length per platform
_MAX_LEN = {
    "twitter":   270,
    "instagram": 2200,
    "facebook":  8000,
    "threads":   500,
    "tiktok":    150,
    "generic":   2000,
}

# ── WIHY voice generation ─────────────────────────────────────────────────────

def _strip_list_response(text: str) -> str:
    """Discard responses that are paper lists, not narrative synthesis."""
    s = text.strip()
    if s.startswith("Here are") or s.startswith("1.") or "research articles I found" in s:
        return ""
    return s


async def _query_wihy_for_comment(
    client: httpx.AsyncClient,
    post_content: str,
    topic: str,
    platform: str,
) -> dict:
    """
    Generate a WIHY-toned comment for the lead's post.
    Uses two passes:
      Pass 1 — direct evidence response to the post topic
      Pass 2 — environmental/processing/sourcing angle (if relevant)
    Returns {"message": str, "citations": list}
    """
    # Pass 1: direct response tailored to what the person actually said
    trimmed_post = post_content[:300].strip() if post_content else topic
    payload1 = {
        "message": (
            f"Someone posted: \"{trimmed_post}\"\n\n"
            f"What does current research say about {topic}? "
            f"Give a helpful, evidence-backed response that addresses their situation directly. "
            f"Be conversational, not clinical."
        ),
        "session_id": str(uuid.uuid4()),
        "source_site": f"engagement-{platform}",
    }
    # Pass 2: actionable/nuanced angle
    payload2 = {
        "message": (
            f"What are the most important nuances, common misconceptions, or environmental "
            f"and processing concerns related to {topic} that people often overlook? "
            f"Keep it practical and evidence-based."
        ),
        "session_id": str(uuid.uuid4()),
        "source_site": f"engagement-{platform}",
    }

    data1: dict = {}
    data2: dict = {}
    try:
        r1 = await client.post(WIHY_ASK, json=payload1, timeout=60)
        data1 = r1.json()
    except Exception as e:
        logger.error(f"WIHY pass 1 failed: {e}")

    try:
        r2 = await client.post(WIHY_ASK, json=payload2, timeout=60)
        data2 = r2.json()
    except Exception as e:
        logger.error(f"WIHY pass 2 failed: {e}")

    msg1 = _strip_list_response(data1.get("message") or "")
    msg2 = _strip_list_response(data2.get("message") or "")

    # Merge: include pass 2 only if it adds distinct value
    if msg2 and len(msg2) > 80 and msg2.strip() != msg1.strip():
        combined = msg1
        if combined:
            combined += "\n\n" + msg2
        else:
            combined = msg2
    else:
        combined = msg1 or msg2

    # Dedup citations
    citations = (data1.get("citations") or []) + (data2.get("citations") or [])
    seen: set = set()
    deduped = []
    for c in citations:
        key = c.get("pmcid") or c.get("title", "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    return {"message": combined, "citations": deduped}


def _format_comment(wihy: dict, platform: str, author: Optional[str] = None) -> str:
    """Format a WIHY response into a platform-appropriate comment."""
    message = (wihy.get("message") or "").strip()
    citations = wihy.get("citations") or []
    max_len = _MAX_LEN.get(platform, 1500)

    if not message:
        message = "The evidence on this topic is nuanced — worth a deeper look."

    if platform == "twitter":
        # Twitter: short, punchy, WIHY attribution, stay under 270
        core = message[:200].rstrip()
        if not core.endswith((".", "!", "?")):
            core = core.rsplit(" ", 1)[0] + "…"
        return f"{core}\n\n— WIHY health research | wihy.ai"

    if platform == "tiktok":
        # TikTok: max 150 chars, no markdown, no links
        core = message[:120].rstrip()
        if not core.endswith((".", "!", "?")):
            core = core.rsplit(" ", 1)[0] + "…"
        return f"{core} via wihy.ai"

    if platform in ("instagram", "facebook"):
        # Instagram/Facebook: plain text (no markdown), hashtags, short citation list
        lines = []
        lines.append(message[:1500] if len(message) > 1500 else message)
        if citations:
            lines.append("")
            lines.append("Sources:")
            for c in citations[:2]:
                pmcid  = c.get("pmcid", "")
                ctitle = c.get("title", "")[:80]
                url    = f"ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""
                line   = f"• {ctitle}"
                if url:
                    line += f" – {url}"
                lines.append(line)
        lines.append("")
        lines.append("Powered by WIHY – evidence-based health | wihy.ai")
        lines.append("#healthresearch #nutrition #wellness #WIHY")
        comment = "\n".join(lines)
        return comment[:max_len]

    # Generic — plain text format
    lines = []
    lines.append(message[:1800] if len(message) > 1800 else message)

    if citations:
        lines.append("")
        lines.append("Sources:")
        for c in citations[:3]:
            pmcid  = c.get("pmcid", "")
            ctitle = c.get("title", "")[:100]
            url    = f"ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""
            line   = f"• {ctitle}"
            if url:
                line += f" – {url}"
            lines.append(line)

    lines.append("")
    lines.append("Powered by WIHY – evidence-based health | wihy.ai")

    comment = "\n".join(lines)
    return comment[:max_len]


# ── Twitter posting ───────────────────────────────────────────────────────────

def _twitter_oauth1_header(method: str, url: str, params: dict) -> str:
    """Build OAuth 1.0a Authorization header for Twitter v2."""
    oauth_params = {
        "oauth_consumer_key":     TWITTER_API_KEY,
        "oauth_nonce":            uuid.uuid4().hex,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp":        str(int(time.time())),
        "oauth_token":            TWITTER_ACCESS_TOKEN,
        "oauth_version":          "1.0",
    }
    # Signature base string
    all_params = {**oauth_params, **params}
    sorted_params = "&".join(
        f"{quote(k, safe='')}={quote(str(v), safe='')}"
        for k, v in sorted(all_params.items())
    )
    base = f"{method.upper()}&{quote(url, safe='')}&{quote(sorted_params, safe='')}"
    signing_key = f"{quote(TWITTER_API_SECRET, safe='')}&{quote(TWITTER_ACCESS_TOKEN_SECRET, safe='')}"
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = sig
    header_parts = ", ".join(
        f'{quote(k, safe="")}="{quote(str(v), safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


async def _post_twitter_reply(
    client: httpx.AsyncClient,
    tweet_id: str,
    text: str,
) -> dict:
    """Reply to a tweet via Twitter v2 API with OAuth 1.0a."""
    if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
        logger.warning("Twitter credentials not configured")
        return {"success": False, "error": "Twitter not configured"}

    url = "https://api.twitter.com/2/tweets"
    payload = {"text": text, "reply": {"in_reply_to_tweet_id": tweet_id}}
    try:
        auth_header = _twitter_oauth1_header("POST", url, {})
        r = await client.post(
            url,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        data = r.json()
        if "data" in data and "id" in data["data"]:
            return {"success": True, "platform_post_id": data["data"]["id"]}
        errors = data.get("errors") or data.get("detail", "Unknown error")
        return {"success": False, "error": str(errors)}
    except Exception as e:
        logger.error(f"Twitter reply error: {e}")
        return {"success": False, "error": str(e)}


# ── Instagram posting ─────────────────────────────────────────────────────────

async def _post_instagram_comment(
    client: httpx.AsyncClient,
    media_id: str,     # Instagram media object ID (the post ID)
    text: str,
) -> dict:
    """
    Post a comment on an Instagram media object via the Meta Graph API.
    Requires a long-lived token with instagram_manage_comments permission.
    media_id is the IG media object ID (NOT the post URL shortcode).
    """
    if not INSTAGRAM_ACCESS_TOKEN:
        logger.warning("Instagram credentials not configured")
        return {"success": False, "error": "Instagram not configured"}
    try:
        r = await client.post(
            f"https://graph.facebook.com/{INSTAGRAM_GRAPH_VERSION}/{media_id}/comments",
            params={"access_token": INSTAGRAM_ACCESS_TOKEN},
            json={"message": text},
            timeout=20,
        )
        data = r.json()
        if "id" in data:
            return {"success": True, "platform_post_id": data["id"]}
        error = data.get("error", {}).get("message", str(data))
        logger.error(f"Instagram comment error: {error}")
        return {"success": False, "error": error}
    except Exception as e:
        logger.error(f"Instagram comment exception: {e}")
        return {"success": False, "error": str(e)}


# ── Facebook posting ──────────────────────────────────────────────────────────

async def _post_facebook_comment(
    client: httpx.AsyncClient,
    object_id: str,    # Facebook post/comment ID
    text: str,
) -> dict:
    """
    Post a comment on a Facebook post or comment via the Meta Graph API.
    Requires a page access token with pages_manage_engagement permission.
    """
    if not FACEBOOK_ACCESS_TOKEN:
        logger.warning("Facebook credentials not configured")
        return {"success": False, "error": "Facebook not configured"}
    try:
        r = await client.post(
            f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}/{object_id}/comments",
            params={"access_token": FACEBOOK_ACCESS_TOKEN},
            json={"message": text},
            timeout=20,
        )
        data = r.json()
        if "id" in data:
            return {"success": True, "platform_post_id": data["id"]}
        error = data.get("error", {}).get("message", str(data))
        logger.error(f"Facebook comment error: {error}")
        return {"success": False, "error": error}
    except Exception as e:
        logger.error(f"Facebook comment exception: {e}")
        return {"success": False, "error": str(e)}


# ── TikTok posting ────────────────────────────────────────────────────────────

async def _post_tiktok_comment(
    client: httpx.AsyncClient,
    video_id: str,
    text: str,
) -> dict:
    """
    Post a comment on a TikTok video via the TikTok for Developers API.
    Requires tt.user.comment scope and a valid access token.
    """
    if not TIKTOK_ACCESS_TOKEN:
        logger.warning("TikTok credentials not configured")
        return {"success": False, "error": "TikTok not configured"}
    try:
        r = await client.post(
            "https://open.tiktokapis.com/v2/comment/post/",
            headers={
                "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"video_id": video_id, "text": text[:150]},  # TikTok comment max 150 chars
            timeout=20,
        )
        data = r.json()
        comment_id = (data.get("data") or {}).get("comment_id")
        if comment_id:
            return {"success": True, "platform_post_id": str(comment_id)}
        error = (data.get("error") or {}).get("message") or str(data)
        logger.error(f"TikTok comment error: {error}")
        return {"success": False, "error": error}
    except Exception as e:
        logger.error(f"TikTok comment exception: {e}")
        return {"success": False, "error": str(e)}


# ── Threads posting ───────────────────────────────────────────────────────────

async def _post_threads_reply(
    client: httpx.AsyncClient,
    reply_to_id: str,   # Threads media ID to reply to
    text: str,
) -> dict:
    """
    Post a reply on Threads via the Threads Publishing API.
    Requires a long-lived token with threads_manage_replies permission.
    reply_to_id is the Threads media ID of the post/reply to respond to.
    """
    if not THREADS_ACCESS_TOKEN:
        logger.warning("Threads credentials not configured")
        return {"success": False, "error": "Threads not configured"}
    try:
        threads_api = "https://graph.threads.net/v1.0"

        # Step 1: Create reply container
        r = await client.post(
            f"{threads_api}/me/threads",
            data={
                "text": text[:500],
                "media_type": "TEXT",
                "reply_to_id": reply_to_id,
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=20,
        )
        data = r.json()
        container_id = data.get("id")
        if not container_id:
            error = (data.get("error") or {}).get("message") or str(data)
            logger.error(f"Threads reply container error: {error}")
            return {"success": False, "error": error}

        # Step 2: Publish the reply container
        pub = await client.post(
            f"{threads_api}/me/threads_publish",
            data={
                "creation_id": container_id,
                "access_token": THREADS_ACCESS_TOKEN,
            },
            timeout=20,
        )
        pub_data = pub.json()
        post_id = pub_data.get("id")
        if post_id:
            return {"success": True, "platform_post_id": post_id}
        error = (pub_data.get("error") or {}).get("message") or str(pub_data)
        logger.error(f"Threads reply publish error: {error}")
        return {"success": False, "error": error}
    except Exception as e:
        logger.error(f"Threads reply exception: {e}")
        return {"success": False, "error": str(e)}


# ── Thread Monitor ────────────────────────────────────────────────────────────


@dataclasses.dataclass
class _TrackedThread:
    platform: str
    our_comment_id: str    # ID of the comment WE posted
    topic: str
    lead_id: Optional[str]
    depth: int             # How many levels deep we've already replied
    conversation_tweet_id: Optional[str]  # Twitter: root tweet of the conversation
    seen_reply_ids: set = dataclasses.field(default_factory=set)
    tracked_at: datetime = dataclasses.field(default_factory=lambda: datetime.now(timezone.utc))


class ThreadMonitor:
    """
    Background service that polls platforms for replies to comments WIHY has posted,
    then auto-generates and posts WIHY replies to those replies.

    Tracks in memory (resets on restart). Thread tracking is registered via track().
    Poll loop runs every THREAD_POLL_INTERVAL seconds (default 5 min).
    Will not reply deeper than THREAD_MAX_DEPTH levels (default 2).
    """

    def __init__(self) -> None:
        self._threads: dict[str, _TrackedThread] = {}   # key: "{platform}:{our_comment_id}"
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._total_auto_replies = 0
        self._last_poll: Optional[datetime] = None

    # ── Public API ─────────────────────────────────────────────────────────────

    def track(
        self,
        platform: str,
        our_comment_id: str,
        topic: str,
        lead_id: Optional[str] = None,
        conversation_tweet_id: Optional[str] = None,
        depth: int = 1,
    ) -> None:
        """Register a comment we've posted so the monitor can watch for replies."""
        key = f"{platform}:{our_comment_id}"
        self._threads[key] = _TrackedThread(
            platform=platform,
            our_comment_id=our_comment_id,
            topic=topic,
            lead_id=lead_id,
            depth=depth,
            conversation_tweet_id=conversation_tweet_id,
        )
        logger.info(f"ThreadMonitor tracking {key} topic={topic!r} depth={depth}")

    def status(self) -> dict:
        return {
            "running": self._running,
            "tracked_threads": len(self._threads),
            "total_auto_replies": self._total_auto_replies,
            "last_poll": self._last_poll.isoformat() if self._last_poll else None,
            "poll_interval_seconds": THREAD_POLL_INTERVAL,
            "max_depth": THREAD_MAX_DEPTH,
        }

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"ThreadMonitor started (interval={THREAD_POLL_INTERVAL}s, max_depth={THREAD_MAX_DEPTH})")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ThreadMonitor stopped")

    # ── Poll loop ───────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._poll_once()
            except Exception as e:
                logger.error(f"ThreadMonitor poll error: {e}")
            await asyncio.sleep(THREAD_POLL_INTERVAL)

    async def _poll_once(self) -> None:
        self._last_poll = datetime.now(timezone.utc)
        if not self._threads:
            return
        logger.info(f"ThreadMonitor polling {len(self._threads)} threads...")
        to_remove = []
        async with httpx.AsyncClient() as client:
            for key, thread in list(self._threads.items()):
                try:
                    if thread.platform == "twitter":
                        new_replies = await self._get_twitter_replies(client, thread)
                    else:
                        continue  # Instagram/Facebook/TikTok: no reply API available

                    for reply in new_replies:
                        reply_id = reply["id"]
                        if reply_id in thread.seen_reply_ids:
                            continue
                        thread.seen_reply_ids.add(reply_id)
                        if thread.depth >= THREAD_MAX_DEPTH:
                            logger.info(f"ThreadMonitor: max depth {THREAD_MAX_DEPTH} reached for {key}, skipping reply")
                            continue
                        await self._handle_reply(client, thread, reply)

                    # Prune threads older than 7 days
                    age = (datetime.now(timezone.utc) - thread.tracked_at).days
                    if age >= 7:
                        to_remove.append(key)

                except Exception as e:
                    logger.error(f"ThreadMonitor error for {key}: {e}")

        for key in to_remove:
            del self._threads[key]
            logger.info(f"ThreadMonitor pruned old thread {key}")

    # ── Twitter reply fetching ──────────────────────────────────────────────────

    async def _get_twitter_replies(
        self,
        client: httpx.AsyncClient,
        thread: _TrackedThread,
    ) -> list:
        """
        Fetch replies to our tweet using the recent search API.
        Searches for tweets in same conversation that are NOT from our account.
        Returns list of {"id": str, "body": str, "author": str}
        """
        if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET]):
            return []
        tweet_id = thread.conversation_tweet_id or thread.our_comment_id
        # Build query: replies in this conversation, not from our bot
        query = f"in_reply_to_tweet_id:{tweet_id}"
        if TWITTER_BOT_USERNAME:
            query += f" -from:{TWITTER_BOT_USERNAME}"
        try:
            url = "https://api.twitter.com/2/tweets/search/recent"
            params = {
                "query": query,
                "tweet.fields": "text,author_id,id",
                "max_results": 10,
            }
            auth_header = _twitter_oauth1_header("GET", url, params)
            r = await client.get(
                url,
                headers={"Authorization": auth_header},
                params=params,
                timeout=15,
            )
            data = r.json()
            tweets = data.get("data") or []
            return [
                {
                    "id": t["id"],
                    "body": t.get("text", ""),
                    "author": t.get("author_id", ""),
                }
                for t in tweets
            ]
        except Exception as e:
            logger.error(f"Twitter replies fetch error: {e}")
            return []

    # ── Auto-reply handler ──────────────────────────────────────────────────────

    async def _handle_reply(
        self,
        client: httpx.AsyncClient,
        thread: _TrackedThread,
        reply: dict,
    ) -> None:
        """Generate a WIHY response to a reply and post it."""
        reply_body = reply.get("body", "")
        reply_id = reply["id"]
        logger.info(
            f"ThreadMonitor auto-replying to {thread.platform}:{reply_id} "
            f"(depth {thread.depth+1}) topic={thread.topic!r}"
        )
        wihy = await _query_wihy_for_comment(client, reply_body, thread.topic, thread.platform)
        comment_text = _format_comment(wihy, thread.platform)
        if not comment_text.strip():
            logger.warning(f"ThreadMonitor: WIHY returned empty reply for {reply_id}")
            return

        if thread.platform == "twitter":
            post_result = await _post_twitter_reply(client, reply_id, comment_text)
        else:
            return

        if post_result.get("success"):
            self._total_auto_replies += 1
            new_comment_id = post_result.get("platform_post_id")
            logger.info(f"ThreadMonitor posted auto-reply {new_comment_id} to {reply_id}")
            # Track the new reply for deeper monitoring (up to max depth)
            if new_comment_id and thread.depth + 1 < THREAD_MAX_DEPTH:
                self.track(
                    platform=thread.platform,
                    our_comment_id=new_comment_id,
                    topic=thread.topic,
                    lead_id=thread.lead_id,
                    conversation_tweet_id=thread.conversation_tweet_id,
                    depth=thread.depth + 1,
                )
        else:
            logger.error(f"ThreadMonitor auto-reply failed for {reply_id}: {post_result.get('error')}")


# Module-level singleton — imported by shania_app.py and engagement_routes.py
thread_monitor = ThreadMonitor()


# ── Main entry point ──────────────────────────────────────────────────────────

async def engage_lead(
    platform: str,
    action: str,
    target_id: str,
    post_content: str,
    topic: str,
    lead_id: Optional[str] = None,
    author: Optional[str] = None,
    dry_run: bool = False,
    conversation_tweet_id: Optional[str] = None,
) -> dict:
    """
    Generate a WIHY-toned comment and post it to the platform.

    Args:
        platform:     "twitter" | "instagram" | "facebook" | "tiktok" | "generic"
        action:       "comment" (on a post) | "reply" (to a comment)
        target_id:    Platform post/comment ID to reply to.
                      Twitter: tweet ID string
                      Instagram: media object ID
                      Facebook: post or comment object ID
                      TikTok: video ID
        post_content: The original post/comment text — used to personalize response
        topic:        Clean topic string for WIHY query, e.g. "intermittent fasting weight loss"
        lead_id:      Optional lead UUID from lead-service (passed through for tracking)
        author:       Original poster's username (for logging)
        dry_run:      If True, generate content but don't post
        conversation_tweet_id: Twitter conversation root tweet ID — for thread monitoring

    Returns:
        {
            "success": bool,
            "platform": str,
            "action": str,
            "content": str,
            "platform_post_id": str,
            "lead_id": str,
            "dry_run": bool,
            "error": str
        }
    """
    platform = (platform or "generic").lower()
    result = {
        "success": False,
        "platform": platform,
        "action": action,
        "content": "",
        "platform_post_id": None,
        "lead_id": lead_id,
        "dry_run": dry_run,
    }

    async with httpx.AsyncClient() as client:
        # Step 1: Generate WIHY response
        logger.info(f"Generating WIHY comment for lead={lead_id} platform={platform} topic={topic!r}")
        wihy = await _query_wihy_for_comment(client, post_content, topic, platform)
        comment_text = _format_comment(wihy, platform, author)

        if not comment_text.strip():
            result["error"] = "WIHY returned empty response"
            return result

        result["content"] = comment_text
        logger.info(f"Generated {len(comment_text)}ch comment for lead={lead_id}")

        if dry_run:
            result["success"] = True
            result["dry_run"] = True
            return result

        # Step 2: Post to platform
        if platform == "twitter":
            post_result = await _post_twitter_reply(client, target_id, comment_text)
        elif platform == "instagram":
            post_result = await _post_instagram_comment(client, target_id, comment_text)
        elif platform == "facebook":
            post_result = await _post_facebook_comment(client, target_id, comment_text)
        elif platform == "threads":
            post_result = await _post_threads_reply(client, target_id, comment_text)
        elif platform == "tiktok":
            post_result = await _post_tiktok_comment(client, target_id, comment_text)
        else:
            # Generic / unrecognised — return content only
            post_result = {"success": True, "platform_post_id": None, "note": "content_only"}

        result.update(post_result)

        if result.get("success"):
            logger.info(f"Posted to {platform}: post_id={result.get('platform_post_id')} lead={lead_id}")

            # Step 3: Register with thread monitor (Twitter only — has reply API)
            our_id = result.get("platform_post_id")
            if our_id and platform == "twitter":
                _conv_id = conversation_tweet_id or target_id
                thread_monitor.track(
                    platform=platform,
                    our_comment_id=our_id,
                    topic=topic,
                    lead_id=lead_id,
                    conversation_tweet_id=_conv_id,
                    depth=1,
                )
        else:
            logger.error(f"Post failed for lead={lead_id}: {result.get('error')}")

    return result
