"""
labat/routers/conversions_routes.py — Meta Conversions API (CAPI) endpoints.

POST /api/labat/conversions/events     — send batch of events
POST /api/labat/conversions/event      — send single event
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.labat.auth import require_admin
from src.labat.schemas import ConversionsBatchRequest, ConversionsResponse
from src.labat.services.conversions_service import send_events, send_single_event
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.conversions_routes")

router = APIRouter(prefix="/api/labat/conversions", tags=["labat-conversions"])


@router.post("/events", response_model=ConversionsResponse)
async def send_batch(body: ConversionsBatchRequest, _=Depends(require_admin)):
    try:
        events_data = [e.model_dump() for e in body.events]
        result = await send_events(events_data, test_event_code=body.test_event_code)
        return ConversionsResponse(
            events_received=result.get("events_received", 0),
            messages=result.get("messages", []),
            fbtrace_id=result.get("fbtrace_id"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/event", response_model=ConversionsResponse)
async def send_one(
    event_name: str,
    user_data: dict,
    custom_data: dict | None = None,
    event_source_url: str | None = None,
    event_id: str | None = None,
    action_source: str = "website",
    test_event_code: str | None = None,
    _=Depends(require_admin),
):
    try:
        result = await send_single_event(
            event_name=event_name,
            user_data=user_data,
            custom_data=custom_data,
            event_source_url=event_source_url,
            event_id=event_id,
            action_source=action_source,
            test_event_code=test_event_code,
        )
        return ConversionsResponse(
            events_received=result.get("events_received", 0),
            messages=result.get("messages", []),
            fbtrace_id=result.get("fbtrace_id"),
        )
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
