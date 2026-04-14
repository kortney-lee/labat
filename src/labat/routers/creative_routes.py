"""
labat/routers/creative_routes.py — Ad creative CRUD endpoints.

POST   /api/labat/creatives       — create
GET    /api/labat/creatives       — list
GET    /api/labat/creatives/:id   — get
DELETE /api/labat/creatives/:id   — delete
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from src.labat.auth import require_admin
from src.labat.schemas import CreateCreativeRequest, CreativeResponse
from src.labat.services.creative_service import (
    create_creative,
    get_creative,
    list_creatives,
    delete_creative,
)
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.creative_routes")

router = APIRouter(prefix="/api/labat/creatives", tags=["labat-creatives"])


@router.post("", response_model=CreativeResponse)
async def create(body: CreateCreativeRequest, _=Depends(require_admin)):
    try:
        result = await create_creative(
            name=body.name,
            object_story_spec=body.object_story_spec,
            url_tags=body.url_tags,
        )
        return CreativeResponse(id=result["id"], name=body.name)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("")
async def list_all(limit: int = Query(50, ge=1, le=200), _=Depends(require_admin)):
    try:
        return await list_creatives(limit=limit)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/{creative_id}", response_model=CreativeResponse)
async def get(creative_id: str, _=Depends(require_admin)):
    try:
        data = await get_creative(creative_id)
        return CreativeResponse(**data)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.delete("/{creative_id}")
async def delete(creative_id: str, _=Depends(require_admin)):
    try:
        return await delete_creative(creative_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
