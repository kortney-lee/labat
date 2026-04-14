"""
labat/routers/compliance_routes.py — Data deletion callback + status endpoint.

POST /api/labat/compliance/data-deletion         — Meta data deletion callback
GET  /api/labat/compliance/deletion-status        — check deletion status
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from src.labat.schemas import DataDeletionRequest, DataDeletionResponse
from src.labat.services.compliance_service import handle_data_deletion, get_deletion_status

logger = logging.getLogger("labat.compliance_routes")

router = APIRouter(prefix="/api/labat/compliance", tags=["labat-compliance"])


@router.post("/data-deletion", response_model=DataDeletionResponse)
async def data_deletion_callback(request: Request):
    """
    Meta calls this when a user removes the app.
    Parses the signed_request, initiates data deletion, and returns
    a confirmation code + status URL.
    """
    form = await request.form()
    signed_request = form.get("signed_request", "")
    if not signed_request:
        raise HTTPException(status_code=400, detail="Missing signed_request")

    # Build the base URL for the status endpoint
    base_url = str(request.base_url).rstrip("/")

    try:
        status_url, confirmation_code = handle_data_deletion(
            str(signed_request), base_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return DataDeletionResponse(url=status_url, confirmation_code=confirmation_code)


@router.get("/deletion-status")
async def deletion_status(code: str = Query(..., description="Confirmation code")):
    """Check the status of a data deletion request."""
    result = get_deletion_status(code)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown confirmation code")
    return result
