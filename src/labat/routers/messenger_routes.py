"""
labat/routers/messenger_routes.py — Messenger send + private reply endpoints.

POST /api/labat/messenger/send          — send a message
POST /api/labat/messenger/private-reply — reply privately to a comment
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.labat.auth import require_admin
from src.labat.schemas import SendMessageRequest, PrivateReplyRequest, MessageResponse
from src.labat.services.messenger_service import send_message, send_private_reply
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.messenger_routes")

router = APIRouter(prefix="/api/labat/messenger", tags=["labat-messenger"])


@router.post("/send", response_model=MessageResponse)
async def send(body: SendMessageRequest, _=Depends(require_admin)):
    try:
        result = await send_message(
            recipient_id=body.recipient_id,
            message_text=body.message_text,
            messaging_type=body.messaging_type,
            tag=body.tag,
        )
        return MessageResponse(
            recipient_id=body.recipient_id,
            message_id=result.get("message_id"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/private-reply", response_model=MessageResponse)
async def private_reply(body: PrivateReplyRequest, _=Depends(require_admin)):
    try:
        result = await send_private_reply(
            comment_id=body.comment_id,
            message=body.message,
        )
        return MessageResponse(
            recipient_id=body.comment_id,
            message_id=result.get("message_id"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
