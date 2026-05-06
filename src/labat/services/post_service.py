"""
labat/services/post_service.py — Create, update, delete Page posts.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

import httpx

from src.labat.brands import BRAND_PAGE_IDS
from src.labat.meta_client import graph_get, graph_post, graph_delete, MetaAPIError
from src.labat.services.token_service import get_shania_page_access_token

_BRAND_SCOPE = os.getenv("SHANIA_BRAND_SCOPE", "").strip().lower() or None
_ENFORCE_MODE = (os.getenv("BRAND_ENFORCEMENT_MODE", "warn") or "warn").strip().lower() == "enforce"
_SOCIAL_POSTING_DISABLED = (os.getenv("SOCIAL_POSTING_DISABLED", "false") or "false").strip().lower() in ("1", "true", "yes", "on")


def _default_page_id() -> str:
    """Return the page ID for the brand this instance serves."""
    if _BRAND_SCOPE:
        page_id = BRAND_PAGE_IDS.get(_BRAND_SCOPE)
        if page_id:
            return page_id
        if _ENFORCE_MODE:
            raise MetaAPIError(f"No page configured for SHANIA_BRAND_SCOPE '{_BRAND_SCOPE}'", status_code=400)
        logger.warning("Unknown SHANIA_BRAND_SCOPE '%s'; defaulting to WIHY page in warn mode", _BRAND_SCOPE)
        return BRAND_PAGE_IDS["wihy"]
    return BRAND_PAGE_IDS["wihy"]


def _enforce_brand(page_id: Optional[str]) -> str:
    """Resolve page_id, enforcing brand scope when set.

    If SHANIA_BRAND_SCOPE is configured, callers cannot override
    to a different brand's page — this prevents cross-brand posting.
    """
    default = _default_page_id()
    valid_page_ids = set(BRAND_PAGE_IDS.values())
    if not page_id:
        return default
    if page_id not in valid_page_ids:
        if _ENFORCE_MODE:
            raise MetaAPIError(f"Invalid page_id '{page_id}'", status_code=400)
        logger.warning("Invalid page_id=%s supplied; using default page_id=%s in warn mode", page_id, default)
        return default
    if _BRAND_SCOPE and page_id != default:
        if _ENFORCE_MODE:
            raise MetaAPIError(
                f"Brand-scoped instance '{_BRAND_SCOPE}' rejected page_id '{page_id}'",
                status_code=403,
            )
        logger.warning(
            "Brand-scoped instance (%s) rejected page_id=%s — using %s in warn mode",
            _BRAND_SCOPE, page_id, default,
        )
        return default
    return page_id


async def _shania(page_id: Optional[str] = None) -> str:
    """Resolve the correct Shania token for the requested page."""
    return await get_shania_page_access_token(page_id)

logger = logging.getLogger("labat.post_service")


def _ensure_social_posting_enabled(channel: str) -> None:
    if _SOCIAL_POSTING_DISABLED:
        logger.warning("Blocked %s publish because SOCIAL_POSTING_DISABLED is enabled", channel)
        raise MetaAPIError(
            f"{channel} posting is disabled",
            status_code=403,
        )


def _page_id_from_post_id(post_id: str) -> Optional[str]:
    if "_" not in post_id:
        return None
    return post_id.split("_", 1)[0]


async def create_post(
    message: str,
    link: Optional[str] = None,
    image_url: Optional[str] = None,
    published: bool = True,
    scheduled_publish_time: Optional[int] = None,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish (or schedule) a post on the Page.

    Use ``image_url`` to publish a **photo post** (uploaded via URL).
    Use ``link`` to publish a link-share post.
    """
    _ensure_social_posting_enabled("Facebook")
    pid = _enforce_brand(page_id)

    token = await _shania(pid)

    if image_url:
        # Photo post — upload the image directly so the URL doesn't show
        data: Dict[str, Any] = {"url": image_url, "message": message, "published": str(published).lower()}
        if link:
            # Attach brand website link so Facebook shows brand domain, not GCS
            data["link"] = link
        if scheduled_publish_time:
            data["published"] = "false"
            data["scheduled_publish_time"] = scheduled_publish_time
        result = await graph_post(f"{pid}/photos", data=data, access_token=token)
        logger.info("Created photo post %s on Page %s", result.get("id"), pid)
        return result

    data = {"message": message, "published": str(published).lower()}
    if link:
        data["link"] = link
    if scheduled_publish_time:
        data["published"] = "false"
        data["scheduled_publish_time"] = scheduled_publish_time

    result = await graph_post(f"{pid}/feed", data=data, access_token=token)
    logger.info("Created post %s on Page %s", result.get("id"), pid)
    return result


async def update_post(post_id: str, message: str) -> Dict[str, Any]:
    """Edit the text of an existing post."""
    _ensure_social_posting_enabled("Facebook")
    result = await graph_post(
        post_id,
        data={"message": message},
        access_token=await _shania(_page_id_from_post_id(post_id)),
    )
    logger.info("Updated post %s", post_id)
    return result


async def delete_post(post_id: str) -> Dict[str, Any]:
    """Delete a post."""
    result = await graph_delete(post_id, access_token=await _shania(_page_id_from_post_id(post_id)))
    logger.info("Deleted post %s", post_id)
    return result


async def get_post(post_id: str) -> Dict[str, Any]:
    """Read a single post with basic fields."""
    return await graph_get(
        post_id,
        params={"fields": "id,message,created_time,permalink_url,is_published"},
        access_token=await _shania(_page_id_from_post_id(post_id)),
    )


async def create_video_post(
    description: str,
    file_url: str,
    title: Optional[str] = None,
    published: bool = True,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish a video to a Facebook Page via file_url (public URL to the video)."""
    _ensure_social_posting_enabled("Facebook")
    pid = _enforce_brand(page_id)

    data: Dict[str, Any] = {
        "file_url": file_url,
        "description": description,
        "published": str(published).lower(),
    }
    if title:
        data["title"] = title

    result = await graph_post(
        f"{pid}/videos", data=data, access_token=await _shania(pid), timeout=120,
    )
    logger.info("Created video post %s on Page %s", result.get("id"), pid)
    return result


async def create_instagram_video(
    caption: str,
    video_url: str,
    media_type: str = "REELS",
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish a video/reel on Instagram via the Page-linked Instagram business account."""
    _ensure_social_posting_enabled("Instagram")
    pid = _enforce_brand(page_id)

    token = await _shania(pid)
    page = await graph_get(
        pid,
        params={"fields": "instagram_business_account"},
        access_token=token,
    )
    ig_account = (page.get("instagram_business_account") or {}).get("id")
    if not ig_account:
        raise MetaAPIError(
            "No instagram_business_account linked to this Facebook Page",
            status_code=400,
        )

    creation = await graph_post(
        f"{ig_account}/media",
        data={"video_url": video_url, "caption": caption, "media_type": media_type},
        access_token=token,
        timeout=120,
    )
    creation_id = creation.get("id")
    if not creation_id:
        raise MetaAPIError("Instagram video creation failed", status_code=502)

    # Video processing takes time — poll until ready
    import asyncio
    for _attempt in range(30):
        await asyncio.sleep(5)
        status_resp = await graph_get(
            creation_id,
            params={"fields": "status_code"},
            access_token=token,
        )
        status_code = status_resp.get("status_code")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise MetaAPIError("Instagram video processing failed", status_code=502)
        logger.info("IG video %s status: %s (attempt %d)", creation_id, status_code, _attempt + 1)
    else:
        raise MetaAPIError("Instagram video processing timed out", status_code=504)

    published = await graph_post(
        f"{ig_account}/media_publish",
        data={"creation_id": creation_id},
        access_token=token,
    )
    published["creation_id"] = creation_id
    logger.info("Published Instagram video %s via IG account %s", published.get("id"), ig_account)
    return published


async def create_instagram_post(
    caption: str,
    image_url: str,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish an Instagram image post via the Page-linked Instagram business account."""
    _ensure_social_posting_enabled("Instagram")
    pid = _enforce_brand(page_id)

    token = await _shania(pid)
    page = await graph_get(
        pid,
        params={"fields": "instagram_business_account"},
        access_token=token,
    )
    ig_account = (page.get("instagram_business_account") or {}).get("id")
    if not ig_account:
        raise MetaAPIError(
            "No instagram_business_account linked to this Facebook Page",
            status_code=400,
        )

    creation = await graph_post(
        f"{ig_account}/media",
        data={"image_url": image_url, "caption": caption},
        access_token=token,
    )
    creation_id = creation.get("id")
    if not creation_id:
        raise MetaAPIError("Instagram media creation failed", status_code=502)

    # Poll until the media container is ready (Instagram must fetch & process the image)
    import asyncio
    for _attempt in range(20):
        await asyncio.sleep(2)
        status_resp = await graph_get(
            creation_id,
            params={"fields": "status_code"},
            access_token=token,
        )
        status_code = status_resp.get("status_code")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise MetaAPIError("Instagram image processing failed", status_code=502)
        logger.info("IG image %s status: %s (attempt %d)", creation_id, status_code, _attempt + 1)
    else:
        raise MetaAPIError("Instagram image processing timed out", status_code=504)

    published = await graph_post(
        f"{ig_account}/media_publish",
        data={"creation_id": creation_id},
        access_token=token,
    )
    published["creation_id"] = creation_id
    logger.info("Published Instagram media %s via IG account %s", published.get("id"), ig_account)
    return published


async def create_threads_post(
    text: str,
    image_url: Optional[str] = None,
    link_attachment: Optional[str] = None,
    page_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Publish a post on Threads via the Threads Publishing API.

    Threads API (graph.threads.net) requires the Instagram/Threads user
    access token — NOT the Facebook Page token.  The token is read from
    THREADS_ACCESS_TOKEN or INSTAGRAM_ACCESS_TOKEN env vars.

    Supports:
      - Text-only posts
      - Image posts (text + image_url)
      - Link posts (text + link_attachment)
    """
    _ensure_social_posting_enabled("Threads")
    # Threads uses a user-level IG/Threads token, not the Page token
    threads_token = (
        os.getenv("THREADS_ACCESS_TOKEN", "")
        or os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        or ""
    ).strip()
    if not threads_token:
        raise MetaAPIError(
            "THREADS_ACCESS_TOKEN / INSTAGRAM_ACCESS_TOKEN not configured",
            status_code=500,
        )

    # Use "me" as the Threads user (token determines which account)
    ig_account = "me"

    # Step 1: Create the Threads media container
    threads_api = "https://graph.threads.net/v1.0"
    container_data: Dict[str, Any] = {
        "text": text,
        "media_type": "TEXT",
        "access_token": threads_token,
    }
    if image_url:
        container_data["media_type"] = "IMAGE"
        container_data["image_url"] = image_url
    if link_attachment:
        container_data["link_attachment"] = link_attachment

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{threads_api}/{ig_account}/threads",
            data=container_data,
        )
    if not resp.is_success:
        raise MetaAPIError(
            f"Threads container creation failed: {resp.text[:300]}",
            status_code=resp.status_code,
        )
    container = resp.json()
    container_id = container.get("id")
    if not container_id:
        raise MetaAPIError("Threads container creation returned no ID", status_code=502)

    # Step 2: Poll until the container is ready (Threads must fetch & process the image)
    import asyncio
    for _attempt in range(15):
        await asyncio.sleep(2)
        async with httpx.AsyncClient(timeout=15.0) as client:
            status_resp = await client.get(
                f"{threads_api}/{container_id}",
                params={"fields": "status", "access_token": threads_token},
            )
        if status_resp.is_success:
            status_data = status_resp.json()
            status_code = status_data.get("status")
            if status_code == "FINISHED":
                break
            if status_code == "ERROR":
                raise MetaAPIError(
                    f"Threads media processing failed: {status_data}",
                    status_code=502,
                )
            logger.info("Threads container %s status: %s (attempt %d)", container_id, status_code, _attempt + 1)
        else:
            logger.warning("Threads status poll failed: %s", status_resp.text[:200])
    else:
        raise MetaAPIError("Threads media processing timed out", status_code=504)

    # Step 3: Publish the container
    async with httpx.AsyncClient(timeout=30.0) as client:
        pub_resp = await client.post(
            f"{threads_api}/{ig_account}/threads_publish",
            data={"creation_id": container_id, "access_token": threads_token},
        )
    if not pub_resp.is_success:
        raise MetaAPIError(
            f"Threads publish failed: {pub_resp.text[:300]}",
            status_code=pub_resp.status_code,
        )
    published = pub_resp.json()
    published["creation_id"] = container_id
    logger.info("Published Threads post %s via IG account %s", published.get("id"), ig_account)
    return published
