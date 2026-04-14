"""
labat/routers/webhook_routes.py — Meta webhook verification + event ingestion.

GET  /api/labat/webhooks          — verification challenge (Meta subscription setup)
POST /api/labat/webhooks          — receive webhook events
POST /api/labat/deauthorize       — user deauthorization callback
POST /api/labat/data-deletion     — user data deletion request callback
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, HTTPException, Query, Request, Response

from src.labat.meta_client import verify_webhook_signature
from src.labat.services.webhook_service import verify_challenge, dispatch_webhook

logger = logging.getLogger("labat.webhook_routes")

router = APIRouter(prefix="/api/labat", tags=["labat-webhooks"])


@router.get("/webhooks")
async def webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Handle the GET verification request from Meta when setting up a webhook subscription.
    Must return the challenge value as plain text.
    """
    challenge = verify_challenge(hub_mode, hub_verify_token, hub_challenge)
    if challenge is None:
        raise HTTPException(status_code=403, detail="Verification failed")
    return Response(content=challenge, media_type="text/plain")


@router.post("/webhooks")
async def webhook_receive(request: Request):
    """
    Receive and dispatch webhook events from Meta.
    Validates X-Hub-Signature-256 before processing.
    """
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_webhook_signature(body_bytes, signature):
        logger.warning("Webhook signature validation failed")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    dispatched = await dispatch_webhook(payload)
    logger.info("Webhook processed: %d events dispatched", dispatched)

    # Meta expects 200 OK quickly; do not block on slow handlers
    return {"status": "ok", "dispatched": dispatched}


@router.post("/deauthorize")
async def deauthorize_callback(request: Request):
    """
    Called by Meta when a user deauthorizes the app.
    Logs the event for auditing.
    """
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_webhook_signature(body_bytes, signature):
        logger.warning("Deauthorize callback: invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    user_id = payload.get("uid") or payload.get("user_id")
    logger.info("User deauthorized app: user_id=%s", user_id)
    return {"status": "ok"}


@router.post("/data-deletion")
async def data_deletion_callback(request: Request):
    """
    Called by Meta when a user requests data deletion.
    Returns a confirmation code and status URL per Meta requirements.
    """
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_webhook_signature(body_bytes, signature):
        logger.warning("Data deletion callback: invalid signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    user_id = payload.get("uid") or payload.get("user_id")
    confirmation_code = hashlib.sha256(
        f"{user_id}-{int(time.time())}".encode()
    ).hexdigest()[:12]

    logger.info(
        "Data deletion requested: user_id=%s, confirmation=%s",
        user_id,
        confirmation_code,
    )

    # Meta requires: url (status check page) + confirmation_code
    return {
        "url": f"https://ml.wihy.ai/api/labat/data-deletion/status?code={confirmation_code}",
        "confirmation_code": confirmation_code,
    }


@router.get("/data-deletion/status")
async def data_deletion_status(code: str = Query(...)):
    """Status check page for data deletion requests."""
    return {
        "confirmation_code": code,
        "status": "complete",
        "message": "LABAT does not store personal user data. Deletion is automatic.",
    }
