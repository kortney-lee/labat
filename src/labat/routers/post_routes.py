"""
labat/routers/post_routes.py — CRUD for Page posts.

POST   /api/labat/posts          — create post
PUT    /api/labat/posts/:id      — update post
DELETE /api/labat/posts/:id      — delete post
GET    /api/labat/posts/:id      — read post
"""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException

from src.labat.auth import require_admin
from src.labat.schemas import (
    CreatePostRequest,
    UpdatePostRequest,
    PostResponse,
    CreateInstagramPostRequest,
    InstagramPostResponse,
    CreateVideoPostRequest,
    VideoPostResponse,
    CreateInstagramVideoRequest,
    CreateThreadsPostRequest,
    ThreadsPostResponse,
)
from src.labat.services.post_service import (
    create_post,
    update_post,
    delete_post,
    get_post,
    create_instagram_post,
    create_video_post,
    create_instagram_video,
    create_threads_post,
)
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.post_routes")

router = APIRouter(prefix="/api/labat/posts", tags=["labat-posts"])


_BLOCKED_TEST_PATTERNS = [
    r"\blabat\s+automation\s+test\b",
    r"\blabat\s+live\s+test\b",
    r"\bhealth\s+intelligence\s+platform\b",
    r"#wihy\s+#healthtech",
]


def _looks_like_test_content(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(
        re.search(pattern, lowered)
        for pattern in _BLOCKED_TEST_PATTERNS
    )


def _reject_test_content(text: str | None, field_name: str) -> None:
    if _looks_like_test_content(text):
        logger.warning(
            "Blocked test-like social content in field=%s: %s",
            field_name,
            (text or "")[:140],
        )
        raise HTTPException(
            status_code=400,
            detail=(
                "Blocked test content. Live publishing endpoints do not "
                "accept automation-test messages."
            ),
        )


@router.post("", response_model=PostResponse)
async def create(body: CreatePostRequest, _=Depends(require_admin)):
    try:
        _reject_test_content(body.message, "message")
        result = await create_post(
            message=body.message,
            page_id=body.page_id,
            link=body.link,
            image_url=body.image_url,
            published=body.published,
            scheduled_publish_time=body.scheduled_publish_time,
        )
        return PostResponse(
            id=result["id"],
            message=body.message,
            is_published=body.published,
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/instagram", response_model=InstagramPostResponse)
async def create_ig(
    body: CreateInstagramPostRequest,
    _=Depends(require_admin),
):
    try:
        _reject_test_content(body.caption, "caption")
        result = await create_instagram_post(
            caption=body.caption,
            image_url=body.image_url,
            page_id=body.page_id,
        )
        return InstagramPostResponse(
            id=result["id"],
            creation_id=result.get("creation_id"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/{post_id}", response_model=PostResponse)
async def read(post_id: str, _=Depends(require_admin)):
    try:
        data = await get_post(post_id)
        return PostResponse(
            id=data["id"],
            message=data.get("message"),
            created_time=data.get("created_time"),
            permalink_url=data.get("permalink_url"),
            is_published=data.get("is_published", True),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.put("/{post_id}")
async def update(
    post_id: str,
    body: UpdatePostRequest,
    _=Depends(require_admin),
):
    try:
        if body.message is None:
            raise HTTPException(status_code=400, detail="Nothing to update")
        _reject_test_content(body.message, "message")
        return await update_post(post_id, body.message)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/video", response_model=VideoPostResponse)
async def create_video(body: CreateVideoPostRequest, _=Depends(require_admin)):
    try:
        _reject_test_content(body.description, "description")
        result = await create_video_post(
            description=body.description,
            file_url=body.file_url,
            title=body.title,
            published=body.published,
            page_id=body.page_id,
        )
        return VideoPostResponse(id=result["id"])
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/instagram/video", response_model=InstagramPostResponse)
async def create_ig_video(
    body: CreateInstagramVideoRequest,
    _=Depends(require_admin),
):
    try:
        _reject_test_content(body.caption, "caption")
        result = await create_instagram_video(
            caption=body.caption,
            video_url=body.video_url,
            media_type=body.media_type,
            page_id=body.page_id,
        )
        return InstagramPostResponse(
            id=result["id"],
            creation_id=result.get("creation_id"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/threads", response_model=ThreadsPostResponse)
async def create_threads(
    body: CreateThreadsPostRequest,
    _=Depends(require_admin),
):
    try:
        _reject_test_content(body.text, "text")
        result = await create_threads_post(
            text=body.text,
            image_url=body.image_url,
            link_attachment=body.link_attachment,
            page_id=body.page_id,
        )
        return ThreadsPostResponse(
            id=result["id"],
            creation_id=result.get("creation_id"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Threads posting error: {e}",
        )


@router.delete("/{post_id}")
async def delete(post_id: str, _=Depends(require_admin)):
    try:
        return await delete_post(post_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
