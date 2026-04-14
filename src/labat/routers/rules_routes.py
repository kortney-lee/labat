"""
labat/routers/rules_routes.py — Meta Automated Rules CRUD endpoints.

All endpoints require admin auth.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.labat.auth import require_admin
from src.labat.schemas import CreateAdRuleRequest, UpdateAdRuleRequest
from src.labat.services import ads_service
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.rules_routes")

router = APIRouter(prefix="/api/labat/rules", tags=["labat-rules"])


@router.get("/", dependencies=[Depends(require_admin)])
async def list_rules():
    """List all automated rules on the ad account."""
    try:
        return await ads_service.list_ad_rules()
    except MetaAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/", dependencies=[Depends(require_admin)])
async def create_rule(body: CreateAdRuleRequest):
    """Create a new automated rule."""
    try:
        return await ads_service.create_ad_rule(
            name=body.name,
            evaluation_spec=body.evaluation_spec,
            execution_spec=body.execution_spec,
            schedule_spec=body.schedule_spec,
            status=body.status,
        )
    except MetaAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/safety-defaults", dependencies=[Depends(require_admin)])
async def create_safety_defaults():
    """Create a set of sensible default safety rules."""
    try:
        return await ads_service.create_safety_rules()
    except MetaAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{rule_id}", dependencies=[Depends(require_admin)])
async def get_rule(rule_id: str):
    """Get a specific automated rule."""
    try:
        return await ads_service.get_ad_rule(rule_id)
    except MetaAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{rule_id}", dependencies=[Depends(require_admin)])
async def update_rule(rule_id: str, body: UpdateAdRuleRequest):
    """Update an automated rule."""
    try:
        fields = body.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields provided")
        return await ads_service.update_ad_rule(rule_id, **fields)
    except MetaAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.delete("/{rule_id}", dependencies=[Depends(require_admin)])
async def delete_rule(rule_id: str):
    """Delete an automated rule."""
    try:
        return await ads_service.delete_ad_rule(rule_id)
    except MetaAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
