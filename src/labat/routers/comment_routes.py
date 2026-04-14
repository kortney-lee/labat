"""
labat/routers/comment_routes.py — Comment read / reply / moderation.

GET    /api/labat/comments/:object_id       — list comments
POST   /api/labat/comments/:post_id         — add comment
POST   /api/labat/comments/:id/reply        — reply to comment
POST   /api/labat/comments/:id/hide         — hide/unhide
DELETE /api/labat/comments/:id              — delete comment
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.labat.auth import require_admin
from src.labat.schemas import CreateCommentRequest, CommentResponse, CommentListResponse
from src.labat.services.comment_service import (
    get_comments,
    create_comment,
    reply_to_comment,
    delete_comment,
    hide_comment,
)
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.comment_routes")

router = APIRouter(prefix="/api/labat/comments", tags=["labat-comments"])


@router.get("/{object_id}")
async def list_comments(
    object_id: str,
    limit: int = Query(50, ge=1, le=100),
    after: Optional[str] = Query(None),
    _=Depends(require_admin),
):
    try:
        result = await get_comments(object_id, limit=limit, after=after)
        return result
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/{post_id}")
async def add_comment(post_id: str, body: CreateCommentRequest, _=Depends(require_admin)):
    try:
        return await create_comment(post_id, body.message)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/{comment_id}/reply")
async def reply(comment_id: str, body: CreateCommentRequest, _=Depends(require_admin)):
    try:
        return await reply_to_comment(comment_id, body.message)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/{comment_id}/hide")
async def toggle_hide(
    comment_id: str,
    hidden: bool = Query(True),
    _=Depends(require_admin),
):
    try:
        return await hide_comment(comment_id, is_hidden=hidden)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.delete("/{comment_id}")
async def remove(comment_id: str, _=Depends(require_admin)):
    try:
        return await delete_comment(comment_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
