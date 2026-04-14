"""
moltbook_bot.py — @wihyhealthbot heartbeat service

Runs as a Cloud Run service (min-instances=1) with an infinite background loop.
Every HEARTBEAT_INTERVAL seconds it:
  1. Checks /home for unread notifications / comments on our posts
  2. Replies to unread comments with WIHY-backed evidence
  3. Browses health feed and upvotes good content
  4. Every PUBLISH_EVERY cycles, publishes a new research post

Exposes:
  GET  /health  → liveness probe
  POST /run     → trigger one heartbeat cycle immediately (debug)
"""

import asyncio
import itertools
import json
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager

import httpx
import openai
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.config.models import CHAT_MODEL

load_dotenv()

logger = logging.getLogger("moltbook_bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Config ─────────────────────────────────────────────────────────────────────
MOLTBOOK_API_KEY = (os.getenv("MOLTBOOK_API_KEY", "") or "").strip()
MOLTBOOK_BASE    = "https://www.moltbook.com/api/v1"
WIHY_ASK         = "https://ml.wihy.ai/ask"
SHANIA_GRAPHICS_URL = os.getenv("SHANIA_GRAPHICS_URL", "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app")
INTERNAL_ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()

HEARTBEAT_INTERVAL = int(os.getenv("MOLTBOOK_INTERVAL", "160"))   # seconds between cycles
PUBLISH_EVERY      = int(os.getenv("MOLTBOOK_PUBLISH_EVERY", "8")) # cycles between new posts
COMMENT_DELAY      = 22   # seconds between comments (rate limit 1/20s)

# OpenAI client for tone rewriting
_openai_client: openai.AsyncOpenAI | None = None

def _get_openai() -> openai.AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY") or os.getenv("WIHY_OPENAI_API_KEY"),
        )
    return _openai_client

# WIHY voice — conversational, human, evidence-based
WIHY_TONE_SYSTEM = """You are rewriting health/nutrition content for a social media post.
Rules:
- Sound like a real person sharing what they learned, NOT like an AI or a textbook.
- Write the way someone would talk to a friend — casual, warm, genuine.
- Use short paragraphs. No walls of text.
- Keep the science accurate but explain it simply.
- Don't start with "Did you know" or "Here's what science says" — just dive in.
- Never say "As an AI" or "It's important to note" or "In conclusion".
- No bullet-point lists — use flowing paragraphs.
- Vary your sentence length. Mix short punchy lines with longer ones.
- Show personality — it's okay to say "honestly" or "this surprised me" or "wild, right?"
- End with something actionable or thought-provoking, not a summary.
- Keep it under 600 words.
- Do NOT add citations or source links — those get added separately.
"""

WIHY_REPLY_TONE_SYSTEM = """You are replying to someone's comment on a health-focused social media platform.
Rules:
- Sound like a knowledgeable friend, not a doctor or AI bot.
- Be warm and conversational. Address what they said directly.
- Keep it concise — 2-4 short paragraphs max.
- Back up your points with evidence but explain it casually.
- Never say "As an AI", "Great question!", or "It's important to note".
- Don't lecture. Have a conversation.
- If they shared a personal experience, acknowledge it briefly before sharing info.
- End naturally — no forced conclusions or "hope this helps!" type endings.
- Do NOT add citations or source links — those get added separately.
"""


async def rewrite_in_wihy_tone(raw_text: str, mode: str = "post",
                               comment_context: str = "") -> str:
    """Rewrite raw WIHY research output in a human, conversational tone."""
    if not raw_text or len(raw_text.strip()) < 30:
        return raw_text
    try:
        client = _get_openai()
        system = WIHY_REPLY_TONE_SYSTEM if mode == "reply" else WIHY_TONE_SYSTEM
        user_prompt = raw_text.strip()
        if mode == "reply" and comment_context:
            user_prompt = (f"The person said: \"{comment_context}\"\n\n"
                           f"Raw research to rewrite as a reply:\n{raw_text.strip()}")
        resp = await client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.85,
            max_tokens=800,
        )
        rewritten = resp.choices[0].message.content.strip()
        logger.info(f"Tone rewrite ({mode}): {len(raw_text)} → {len(rewritten)} chars")
        return rewritten
    except Exception as e:
        logger.error(f"Tone rewrite failed, using raw text: {e}")
        return raw_text


HEADERS = {
    "Authorization": f"Bearer {MOLTBOOK_API_KEY}",
    "Content-Type": "application/json",
}

# Rotating topics for autonomous posts
TOPICS = itertools.cycle([
    "omega-3 fatty acids and heart disease",
    "intermittent fasting and insulin resistance",
    "coffee and cardiovascular health",
    "vitamin D deficiency and immune function",
    "gut microbiome and mental health",
    "sleep deprivation and metabolic syndrome",
    "ultra-processed foods and cancer risk",
    "resistance training and longevity",
    "Mediterranean diet and cognitive decline",
    "berberine vs metformin blood sugar",
    "magnesium deficiency and anxiety",
    "creatine benefits beyond muscle building",
    "seed oils and inflammation",
    "alcohol and breast cancer risk",
    "high protein diet and kidney function",
    "red meat and colorectal cancer",
    "exercise and depression treatment",
    "sugar and non-alcoholic fatty liver disease",
    "statins and muscle damage",
    "time-restricted eating and weight loss",
])

# ── Number-word solver (identical to moltbook_first_post.py) ───────────────────
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
ONES = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
        "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
        "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
        "eighteen": 18, "nineteen": 19}
ALL_NUMS = {**TENS, **ONES, "hundred": 100}


def solve_challenge(challenge_text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", challenge_text).lower()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    blob = re.sub(r"\s+", "", cleaned)

    found = []
    occupied = [False] * len(blob)
    for word in sorted(ALL_NUMS.keys(), key=len, reverse=True):
        start = 0
        while True:
            idx = blob.find(word, start)
            if idx == -1:
                break
            span = range(idx, idx + len(word))
            if not any(occupied[i] for i in span):
                found.append((idx, ALL_NUMS[word], word))
                for i in span:
                    occupied[i] = True
            start = idx + 1
    found.sort()

    if not found:
        digits = re.findall(r"\b(\d+(?:\.\d+)?)\b", cleaned)
        if len(digits) < 2:
            raise ValueError(f"No numbers found: {cleaned[:80]}")
        found_vals = [float(d) for d in digits[:2]]
    else:
        values_raw = [v for _, v, _ in found]
        values_merged = []
        i = 0
        while i < len(values_raw):
            v = values_raw[i]
            if v in TENS.values() and i + 1 < len(values_raw) and values_raw[i + 1] in ONES.values():
                values_merged.append(v + values_raw[i + 1])
                i += 2
            else:
                values_merged.append(v)
                i += 1
        found_vals = values_merged

    if len(found_vals) < 2:
        raise ValueError(f"Need 2+ numbers, got: {found_vals}")

    a, b = float(found_vals[0]), float(found_vals[1])

    add_kw = ["add", "plus", "more", "gain", "increase", "total", "combined",
              "together", "velocity", "speed", "new", "accelerat"]
    sub_kw = ["slow", "less", "minus", "subtract", "decrease", "reduce",
              "drop", "lost", "fewer", "remain", "lose", "deceler"]
    mul_kw = ["times", "multiply", "multiplied", "double", "triple"]
    div_kw = ["divide", "divided", "split", "half", "quarter"]

    op = "add"
    for w in sub_kw:
        if w in cleaned:
            op = "sub"; break
    for w in mul_kw:
        if w in cleaned:
            op = "mul"; break
    for w in div_kw:
        if w in cleaned:
            op = "div"; break
    for w in add_kw:
        if w in cleaned:
            op = "add"; break

    result = {"add": a + b, "sub": a - b, "mul": a * b, "div": a / b if b else 0}[op]
    return f"{result:.2f}"


# ── Moltbook API helpers ───────────────────────────────────────────────────────

async def _post(client: httpx.AsyncClient, url: str, payload: dict, retry_on_429: bool = True) -> dict:
    r = await client.post(url, headers=HEADERS, json=payload, timeout=30)
    data = r.json()
    if r.status_code == 429 and retry_on_429:
        wait = data.get("retry_after_seconds", 30) + 2
        logger.info(f"Rate limited — waiting {wait}s")
        await asyncio.sleep(wait)
        r = await client.post(url, headers=HEADERS, json=payload, timeout=30)
        data = r.json()
    return data


async def _get(client: httpx.AsyncClient, url: str, params: dict = None) -> dict:
    r = await client.get(url, headers=HEADERS, params=params or {}, timeout=30)
    return r.json()


async def verify_content(client: httpx.AsyncClient, verification: dict) -> bool:
    code = verification.get("verification_code") or verification.get("code", "")
    text = verification.get("challenge_text") or verification.get("challenge", "")
    if not code or not text:
        logger.warning(f"Missing verification fields: {verification}")
        return False
    try:
        answer = solve_challenge(text)
    except Exception as e:
        logger.error(f"Solver error: {e}")
        return False
    result = await _post(client, f"{MOLTBOOK_BASE}/verify",
                         {"verification_code": code, "answer": answer})
    ok = result.get("success", False)
    logger.info(f"Verification {'OK' if ok else 'FAILED'}: {answer} → {result.get('message', '')}")
    return ok


# ── WIHY API ──────────────────────────────────────────────────────────────────

def _strip_list_response(text: str) -> str:
    """Discard responses that are numbered paper lists, not narrative synthesis."""
    s = text.strip()
    if s.startswith("Here are") or s.startswith("1.") or "research articles I found" in s:
        return ""
    return s


async def query_wihy(client: httpx.AsyncClient, topic: str) -> dict:
    """Two-pass query: synthesis first, then environmental/processing angle."""
    # Pass 1: synthesis — original formula that returns narrative response
    payload1 = {
        "message": f"What does science say about {topic}? What are the key findings?",
        "session_id": str(uuid.uuid4()),
        "source_site": "moltbook",
    }
    # Pass 2: environmental and processing angle
    payload2 = {
        "message": (
            f"What does the research say about environmental impact and food processing "
            f"concerns related to {topic}? Include carbon footprint of different sources, "
            f"farming practices, how processing degrades nutrient quality, and sourcing "
            f"differences that affect health outcomes."
        ),
        "session_id": str(uuid.uuid4()),
        "source_site": "moltbook",
    }
    try:
        r1 = await client.post(WIHY_ASK, json=payload1, timeout=60)
        data1 = r1.json()
    except Exception as e:
        logger.error(f"WIHY query 1 failed: {e}")
        data1 = {}
    try:
        r2 = await client.post(WIHY_ASK, json=payload2, timeout=60)
        data2 = r2.json()
    except Exception as e:
        logger.error(f"WIHY query 2 failed: {e}")
        data2 = {}

    msg1 = _strip_list_response(data1.get("message") or "")
    msg2 = _strip_list_response(data2.get("message") or "")
    if msg2 and len(msg2) > 80 and msg2 not in msg1:
        combined_message = msg1 + "\n\n**Environmental & Processing Concerns:**\n" + msg2
    else:
        combined_message = msg1 or msg2

    citations = (data1.get("citations") or []) + (data2.get("citations") or [])
    seen = set()
    deduped = []
    for c in citations:
        key = c.get("pmcid") or c.get("title", "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    return {"message": combined_message, "citations": deduped}


async def query_wihy_comment(client: httpx.AsyncClient, comment_body: str) -> dict:
    """Query WIHY with a user comment as-is, no research template wrapping."""
    payload = {
        "message": comment_body,
        "session_id": str(uuid.uuid4()),
        "source_site": "moltbook",
    }
    try:
        r = await client.post(WIHY_ASK, json=payload, timeout=60)
        data = r.json()
    except Exception as e:
        logger.error(f"WIHY comment query failed: {e}")
        data = {}
    return {
        "message": _strip_list_response(data.get("message") or ""),
        "citations": data.get("citations") or [],
    }


def _format_reply(wihy: dict, prefix: str = "") -> str:
    message = wihy.get("message", "").strip()
    citations = wihy.get("citations", [])
    lines = []
    if prefix:
        lines.append(prefix)
        lines.append("")
    lines.append(message[:800] if message else "The evidence on this is mixed.")
    if citations:
        lines.append("")
        for c in citations[:2]:
            pmcid = c.get("pmcid", "")
            ctitle = c.get("title", "")
            url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""
            cite = f"- {ctitle[:100]}"
            if url:
                cite += f" [{pmcid}]({url})"
            lines.append(cite)
    lines.append("")
    lines.append("_Source: WIHY health research — https://wihy.ai_")
    return "\n".join(lines)


def _append_citations(text: str, citations: list) -> str:
    """Append citation links and WIHY source tag to rewritten text."""
    lines = [text.strip()]
    if citations:
        lines.append("")
        for c in citations[:2]:
            pmcid = c.get("pmcid", "")
            ctitle = c.get("title", "")
            url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else ""
            cite = f"- {ctitle[:100]}"
            if url:
                cite += f" [{pmcid}]({url})"
            lines.append(cite)
    lines.append("")
    lines.append("_Source: WIHY health research — https://wihy.ai_")
    return "\n".join(lines)


# Title templates — rotate to avoid repetition
_TITLE_TEMPLATES = [
    "The research on {topic} is more complicated than you think",
    "What studies actually show about {topic}",
    "The environmental and health case for rethinking {topic}",
    "Hidden findings: what the science says about {topic}",
    "Beyond the basics: new research on {topic}",
]
_title_idx = 0


def _format_post(topic: str, wihy: dict) -> tuple[str, str]:
    global _title_idx
    words = topic.split()[:5]
    title_topic = " ".join(w.capitalize() for w in words)
    template = _TITLE_TEMPLATES[_title_idx % len(_TITLE_TEMPLATES)]
    _title_idx += 1
    title = template.format(topic=title_topic)
    content = _format_reply(wihy)
    return title, content


# ── Core actions ──────────────────────────────────────────────────────────────

async def publish_post(client: httpx.AsyncClient, topic: str) -> bool:
    logger.info(f"Publishing post: {topic}")
    wihy = await query_wihy(client, topic)
    if not wihy.get("message"):
        logger.warning("WIHY returned empty, skipping post")
        return False

    # Rewrite in human tone before formatting
    wihy["message"] = await rewrite_in_wihy_tone(wihy["message"], mode="post")
    title, content = _format_post(topic, wihy)

    # Cross-post to our research bot page (fire-and-forget)
    try:
        citations_payload = []
        for c in (wihy.get("citations") or [])[:5]:
            pmcid = c.get("pmcid", "")
            citations_payload.append({
                "title": c.get("title", "")[:200],
                "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else "",
                "source": c.get("journal", ""),
                "year": c.get("year"),
            })
        research_payload = {
            "title": title,
            "body": wihy["message"],
            "topic": topic.split()[0] if topic else "general",
            "citations": citations_payload,
            "author": "wihyhealthbot",
            "brand": "wihy",
        }
        headers = {"Content-Type": "application/json"}
        if INTERNAL_ADMIN_TOKEN:
            headers["X-Admin-Token"] = INTERNAL_ADMIN_TOKEN
        await client.post(
            f"{SHANIA_GRAPHICS_URL}/research-bot/posts",
            json=research_payload,
            headers=headers,
            timeout=15,
        )
        logger.info(f"Cross-posted to research bot: {title}")
    except Exception as e:
        logger.warning(f"Research bot cross-post failed (non-fatal): {e}")

    for submolt in ("health", "general"):
        result = await _post(client, f"{MOLTBOOK_BASE}/posts",
                             {"submolt_name": submolt, "title": title[:300], "content": content})
        if result.get("success"):
            post_data = result.get("post") or result
            verification = post_data.get("verification") or result.get("verification")
            if verification:
                await verify_content(client, verification)
            logger.info(f"Post published: {title}")
            return True
        logger.warning(f"Post failed on submolt={submolt}: {str(result)[:100]}")
    return False


async def post_comment(client: httpx.AsyncClient, post_id: str, content: str,
                       parent_id: str = None) -> bool:
    payload = {"content": content}
    if parent_id:
        payload["parent_id"] = parent_id

    result = await _post(client, f"{MOLTBOOK_BASE}/posts/{post_id}/comments", payload)
    if not result.get("success"):
        logger.warning(f"Comment failed on post {post_id}: {str(result)[:100]}")
        return False

    # Comments also need verification
    comment_data = result.get("comment") or result
    verification = comment_data.get("verification") or result.get("verification")
    if verification:
        await verify_content(client, verification)

    logger.info(f"Comment posted on {post_id}")
    return True


async def reply_to_comments(client: httpx.AsyncClient, home: dict) -> int:
    """Reply to unread comments on our posts. Returns number of replies sent."""
    replied = 0

    # /home returns activity_on_your_posts: [{post_id, new_notification_count, ...}]
    activity = home.get("activity_on_your_posts") or []
    posts_with_comments = [a for a in activity if a.get("new_notification_count", 0) > 0]

    for post_activity in posts_with_comments[:3]:  # cap at 3 posts per cycle
        post_id = post_activity.get("post_id")
        if not post_id:
            continue

        # Fetch the actual comments
        try:
            comments_resp = await _get(client, f"{MOLTBOOK_BASE}/posts/{post_id}/comments",
                                       {"sort": "new", "limit": 20})
        except Exception as e:
            logger.error(f"Failed to fetch comments for {post_id}: {e}")
            continue

        comments = comments_resp.get("comments") or []
        for comment in comments[:5]:  # cap at 5 comments per post
            comment_id     = comment.get("id")
            author         = (comment.get("author") or {}).get("name", "unknown")
            body           = (comment.get("content") or "").strip()
            existing_replies = comment.get("replies") or []

            # Skip our own comments and already-replied threads
            if author == "wihyhealthbot":
                continue
            # In-memory guard: prevents duplicate replies across rapid back-to-back cycles
            if comment_id in _replied_comment_ids:
                continue
            if any((r.get("author") or {}).get("name") == "wihyhealthbot"
                   for r in existing_replies):
                _replied_comment_ids.add(comment_id)  # sync state with what's on server
                continue
            if not body:
                continue

            logger.info(f"Replying to @{author} on post {post_id}: '{body[:60]}'")
            # Send the comment as a natural query — don't wrap in a
            # research template (that causes garbled echo-back queries).
            wihy = await query_wihy_comment(client, body[:300])
            # Rewrite in human tone, then append citations
            rewritten = await rewrite_in_wihy_tone(
                wihy.get("message", ""), mode="reply", comment_context=body[:200]
            )
            reply = _append_citations(
                f"@{author} {rewritten}", wihy.get("citations", [])
            )

            await asyncio.sleep(COMMENT_DELAY)
            ok = await post_comment(client, post_id, reply, parent_id=comment_id)
            if ok:
                replied += 1
                _replied_comment_ids.add(comment_id)  # mark immediately so next cycle skips it

        # Mark notifications read for this post
        try:
            await client.post(f"{MOLTBOOK_BASE}/notifications/read-by-post/{post_id}",
                              headers=HEADERS, timeout=10)
        except Exception:
            pass

    return replied


async def engage_feed(client: httpx.AsyncClient) -> int:
    """Upvote a few posts from the health feed. Returns upvote count."""
    feed = await _get(client, f"{MOLTBOOK_BASE}/posts",
                      {"submolt": "health", "sort": "hot", "limit": 20})
    posts = feed.get("posts") or feed.get("data") or []
    upvoted = 0
    count = 0
    for post in posts:
        if count >= 3:
            break
        pid = post.get("id")
        if not pid or pid in _upvoted_post_ids:
            continue  # already upvoted this run — skip
        try:
            r = await client.post(f"{MOLTBOOK_BASE}/posts/{pid}/upvote",
                                  headers=HEADERS, timeout=10)
            if r.status_code in (200, 201):
                upvoted += 1
                count += 1
                _upvoted_post_ids.add(pid)
        except Exception:
            pass
        await asyncio.sleep(1)
    return upvoted


# ── In-memory dedup state ────────────────────────────────────────────────────
# Persist for the lifetime of the Cloud Run instance (reset on redeploy only)
_replied_comment_ids: set = set()   # comment IDs we've already replied to
_upvoted_post_ids: set = set()      # post IDs we've already upvoted this run

# ── Heartbeat loop ─────────────────────────────────────────────────────────────

_cycle_count = 0


async def run_heartbeat() -> dict:
    global _cycle_count
    _cycle_count += 1
    cycle = _cycle_count
    logger.info(f"── Heartbeat cycle {cycle} ──")
    summary = {"cycle": cycle, "replies": 0, "upvotes": 0, "posted": False}

    async with httpx.AsyncClient() as client:
        # 1. Check home dashboard
        try:
            home = await _get(client, f"{MOLTBOOK_BASE}/home")
        except Exception as e:
            logger.error(f"GET /home failed: {e}")
            home = {}

        logger.info(f"Home keys: {list(home.keys())}")

        # 2. Reply to any pending comments
        try:
            summary["replies"] = await reply_to_comments(client, home)
        except Exception as e:
            logger.error(f"reply_to_comments error: {e}")

        # 3. Engage with feed (upvotes)
        try:
            summary["upvotes"] = await engage_feed(client)
        except Exception as e:
            logger.error(f"engage_feed error: {e}")

        # 4. Publish new post every N cycles
        if cycle % PUBLISH_EVERY == 0:
            topic = next(TOPICS)
            try:
                summary["posted"] = await publish_post(client, topic)
            except Exception as e:
                logger.error(f"publish_post error: {e}")

    logger.info(f"Cycle {cycle} done: {summary}")
    return summary


async def heartbeat_loop():
    logger.info(f"Heartbeat loop started. interval={HEARTBEAT_INTERVAL}s publish_every={PUBLISH_EVERY}")
    while True:
        try:
            await run_heartbeat()
        except Exception as e:
            logger.error(f"Heartbeat crashed: {e}", exc_info=True)
        await asyncio.sleep(HEARTBEAT_INTERVAL)


# ── FastAPI app ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(heartbeat_loop())
    logger.info("Moltbook bot started")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="WIHY Moltbook Bot", lifespan=lifespan)

# ── Verbose Request Logger ──
try:
    from src.middleware.request_logger import VerboseRequestLoggerMiddleware
    app.add_middleware(VerboseRequestLoggerMiddleware, service_name="wihy-moltbook-bot")
except ImportError:
    pass


@app.get("/health")
def health():
    return {"status": "running", "cycle": _cycle_count}


@app.post("/run")
async def trigger_run():
    """Trigger one heartbeat cycle immediately (debug)."""
    result = await run_heartbeat()
    return JSONResponse(result)
