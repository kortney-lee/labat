"""
Post-publish hooks for WIHY blog posts.

After a blog post is published to GCS, these hooks:
1. Submit the URL to search engines via IndexNow (Bing, Yandex, etc.)
2. Queue a social media post via Shania's orchestrate-post endpoint
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger("wihy.post_publish")

# ── Config ────────────────────────────────────────────────────────────────────

SITE_URL = "https://wihy.ai"
INDEXNOW_KEY_FILE = Path(__file__).resolve().parent.parent.parent / "static" / "indexnow-key.txt"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

SHANIA_URL = os.getenv(
    "SHANIA_URL",
    "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app",
)
ADMIN_TOKEN = os.getenv("INTERNAL_ADMIN_TOKEN", "")

# Platforms to auto-post to (can be overridden via env)
AUTO_POST_PLATFORMS = os.getenv("AUTO_POST_PLATFORMS", "facebook,linkedin,threads,instagram").split(",")


# ── IndexNow ──────────────────────────────────────────────────────────────────

def _get_or_create_indexnow_key() -> str:
    """Get the IndexNow key, creating one if it doesn't exist."""
    if INDEXNOW_KEY_FILE.exists():
        return INDEXNOW_KEY_FILE.read_text().strip()

    # Generate a new key (32 hex chars)
    key = secrets.token_hex(16)
    INDEXNOW_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEXNOW_KEY_FILE.write_text(key)
    logger.info("Created IndexNow key file: %s", INDEXNOW_KEY_FILE)
    return key


async def submit_indexnow(url: str) -> bool:
    """Submit a URL to IndexNow for instant indexing by Bing, Yandex, etc."""
    key = _get_or_create_indexnow_key()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                INDEXNOW_ENDPOINT,
                json={
                    "host": "wihy.ai",
                    "key": key,
                    "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY_FILE.name}",
                    "urlList": [url],
                },
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 202):
                logger.info("IndexNow: submitted %s (HTTP %d)", url, resp.status_code)
                return True
            else:
                logger.warning("IndexNow: %s returned HTTP %d: %s", url, resp.status_code, resp.text[:200])
                return False
    except Exception as e:
        logger.warning("IndexNow: failed for %s: %s", url, e)
        return False


async def submit_indexnow_batch(urls: list[str]) -> int:
    """Submit multiple URLs to IndexNow in one request."""
    if not urls:
        return 0
    key = _get_or_create_indexnow_key()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                INDEXNOW_ENDPOINT,
                json={
                    "host": "wihy.ai",
                    "key": key,
                    "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY_FILE.name}",
                    "urlList": urls[:10_000],
                },
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 202):
                logger.info("IndexNow batch: submitted %d URLs (HTTP %d)", len(urls), resp.status_code)
                return len(urls)
            else:
                logger.warning("IndexNow batch: HTTP %d: %s", resp.status_code, resp.text[:200])
                return 0
    except Exception as e:
        logger.warning("IndexNow batch: failed: %s", e)
        return 0


# ── Shania Social Post ───────────────────────────────────────────────────────

async def queue_social_post(
    title: str,
    route_path: str,
    meta_description: str = "",
    hero_image: str = "",
) -> bool:
    """Queue a social media post about a newly published blog post via Shania."""
    if not ADMIN_TOKEN:
        logger.debug("Shania social post skipped: no INTERNAL_ADMIN_TOKEN")
        return False

    post_url = f"{SITE_URL}{route_path}"
    prompt = (
        f"New blog post published: \"{title}\"\n"
        f"URL: {post_url}\n"
        f"Summary: {meta_description}\n\n"
        f"Create an engaging social media post promoting this article. "
        f"Include a call-to-action to read the full article."
    )

    payload = {
        "prompt": prompt,
        "brand": "wihy",
        "platforms": AUTO_POST_PLATFORMS,
        "dryRun": False,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{SHANIA_URL}/orchestrate-post",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Admin-Token": ADMIN_TOKEN,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.info("Shania social post queued for %s → %s", route_path, AUTO_POST_PLATFORMS)
                return True
            else:
                logger.warning("Shania social post failed (HTTP %d): %s", resp.status_code, resp.text[:200])
                return False
    except Exception as e:
        logger.warning("Shania social post failed for %s: %s", route_path, e)
        return False


# ── Combined Hook ─────────────────────────────────────────────────────────────

async def on_post_published(post: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all post-publish hooks for a newly published blog post.

    Args:
        post: The post dict containing slug, title, route_path, meta_description, hero_image, etc.

    Returns:
        Dict with results of each hook.
    """
    slug = post.get("slug", "")
    route_path = post.get("route_path", f"/blog/{slug}")
    full_url = f"{SITE_URL}{route_path}"
    title = post.get("title", slug.replace("-", " ").title())
    meta = post.get("meta_description", "")
    hero = post.get("hero_image", "")

    results: Dict[str, Any] = {}

    # 1. IndexNow — submit for search engine indexing
    results["indexnow"] = await submit_indexnow(full_url)

    # 2. Shania — queue social media post
    results["social"] = await queue_social_post(title, route_path, meta, hero)

    return results
