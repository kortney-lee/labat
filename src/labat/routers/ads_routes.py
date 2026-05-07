"""
labat/routers/ads_routes.py — Campaign / AdSet / Ad CRUD endpoints.

All endpoints require admin auth.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.labat.auth import require_admin
from src.labat.schemas import (
    CreateCampaignRequest, UpdateCampaignRequest, CampaignResponse,
    CreateAdSetRequest, UpdateAdSetRequest, AdSetResponse,
    CreateAdRequest, UpdateAdRequest, AdResponse,
    CreateCreativeRequest, CreativeResponse,
    UploadAdVideoRequest, AdVideoResponse,
    CreatePixelRequest, PixelResponse,
)
from src.labat.services import ads_service
from src.labat.meta_client import MetaAPIError

logger = logging.getLogger("labat.ads_routes")

router = APIRouter(prefix="/api/labat/ads", tags=["labat-ads"])


@router.get("/account")
async def get_account_info(_=Depends(require_admin)):
    try:
        return await ads_service.get_account_info()
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


# ── Campaigns ─────────────────────────────────────────────────────────────────

@router.post("/campaigns", response_model=CampaignResponse)
async def create_campaign(body: CreateCampaignRequest, _=Depends(require_admin)):
    try:
        result = await ads_service.create_campaign(
            name=body.name,
            objective=body.objective.value,
            status=body.status.value,
            daily_budget=body.daily_budget,
            lifetime_budget=body.lifetime_budget,
            bid_strategy=body.bid_strategy.value,
            special_ad_categories=body.special_ad_categories,
            campaign_budget_optimization=body.campaign_budget_optimization,
        )
        return CampaignResponse(id=result["id"], name=body.name, objective=body.objective.value, status=body.status.value)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/campaigns")
async def list_campaigns(limit: int = Query(50, ge=1, le=200), _=Depends(require_admin)):
    try:
        return await ads_service.list_campaigns(limit=limit)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: str, _=Depends(require_admin)):
    try:
        data = await ads_service.get_campaign(campaign_id)
        return CampaignResponse(**data)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.put("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, body: UpdateCampaignRequest, _=Depends(require_admin)):
    try:
        fields = body.model_dump(exclude_none=True)
        # Convert enums to values
        for k, v in fields.items():
            if hasattr(v, "value"):
                fields[k] = v.value
        return await ads_service.update_campaign(campaign_id, **fields)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, _=Depends(require_admin)):
    try:
        return await ads_service.delete_campaign(campaign_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


# ── Ad Sets ───────────────────────────────────────────────────────────────────

@router.post("/adsets", response_model=AdSetResponse)
async def create_adset(body: CreateAdSetRequest, _=Depends(require_admin)):
    try:
        result = await ads_service.create_adset(
            campaign_id=body.campaign_id,
            name=body.name,
            status=body.status.value,
            daily_budget=body.daily_budget,
            lifetime_budget=body.lifetime_budget,
            billing_event=body.billing_event,
            optimization_goal=body.optimization_goal,
            bid_amount=body.bid_amount,
            targeting=body.targeting,
            destination_type=body.destination_type,
            promoted_object=body.promoted_object,
            start_time=body.start_time,
            end_time=body.end_time,
            product=body.product,
            funnel_stage=body.funnel_stage,
        )
        return AdSetResponse(id=result["id"], name=body.name, campaign_id=body.campaign_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/adsets")
async def list_adsets(
    campaign_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _=Depends(require_admin),
):
    try:
        return await ads_service.list_adsets(campaign_id=campaign_id, limit=limit)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/adsets/{adset_id}", response_model=AdSetResponse)
async def get_adset(adset_id: str, _=Depends(require_admin)):
    try:
        data = await ads_service.get_adset(adset_id)
        return AdSetResponse(**data)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.put("/adsets/{adset_id}")
async def update_adset(adset_id: str, body: UpdateAdSetRequest, _=Depends(require_admin)):
    try:
        fields = body.model_dump(exclude_none=True)
        for k, v in fields.items():
            if hasattr(v, "value"):
                fields[k] = v.value
        return await ads_service.update_adset(adset_id, **fields)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.delete("/adsets/{adset_id}")
async def delete_adset(adset_id: str, _=Depends(require_admin)):
    try:
        return await ads_service.delete_adset(adset_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


# ── Ads ───────────────────────────────────────────────────────────────────────

@router.post("/ads", response_model=AdResponse)
async def create_ad(body: CreateAdRequest, _=Depends(require_admin)):
    try:
        result = await ads_service.create_ad(
            adset_id=body.adset_id,
            name=body.name,
            creative_id=body.creative_id,
            status=body.status.value,
        )
        return AdResponse(id=result["id"], name=body.name, adset_id=body.adset_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/ads")
async def list_ads(
    adset_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    _=Depends(require_admin),
):
    try:
        return await ads_service.list_ads(adset_id=adset_id, limit=limit)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/ads/{ad_id}", response_model=AdResponse)
async def get_ad(ad_id: str, _=Depends(require_admin)):
    try:
        data = await ads_service.get_ad(ad_id)
        return AdResponse(**data)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.put("/ads/{ad_id}")
async def update_ad(ad_id: str, body: UpdateAdRequest, _=Depends(require_admin)):
    try:
        fields = body.model_dump(exclude_none=True)
        for k, v in fields.items():
            if hasattr(v, "value"):
                fields[k] = v.value
        return await ads_service.update_ad(ad_id, **fields)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.delete("/ads/{ad_id}")
async def delete_ad(ad_id: str, _=Depends(require_admin)):
    try:
        return await ads_service.delete_ad(ad_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


# ── Ad Creatives ──────────────────────────────────────────────────────────────

@router.post("/creatives", response_model=CreativeResponse)
async def create_creative(body: CreateCreativeRequest, _=Depends(require_admin)):
    try:
        result = await ads_service.create_creative(
            name=body.name,
            object_story_spec=body.object_story_spec,
            object_story_id=body.object_story_id,
            url_tags=body.url_tags,
            variant=body.variant,
        )
        return CreativeResponse(id=result["id"], name=body.name)
    except MetaAPIError as e:
        detail = str(e)
        if e.error_code:
            detail += f" (code={e.error_code}, subcode={e.error_subcode})"
        raise HTTPException(status_code=e.status_code or 502, detail=detail)


@router.get("/creatives")
async def list_creatives(limit: int = Query(50, ge=1, le=200), _=Depends(require_admin)):
    try:
        return await ads_service.list_creatives(limit=limit)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.post("/creatives/patch-utm-tags")
async def patch_utm_tags_on_live_ads(_=Depends(require_admin)):
    """
    One-time: iterate all active ad creatives, infer variant from name,
    and set url_tags with proper utm_content. Safe to re-run (idempotent).
    """
    from src.labat.services.ads_service import _infer_variant, _book_utm_tags
    from src.labat.meta_client import graph_post

    creatives = await ads_service.list_creatives(limit=200)
    patched, skipped, errors = [], [], []

    for c in creatives.get("data", []):
        cid = c.get("id", "")
        name = c.get("name", "")
        existing_tags = c.get("url_tags", "")

        # Skip if already has utm_content set correctly
        if "utm_content=" in existing_tags and "utm_content=general" not in existing_tags:
            skipped.append({"id": cid, "name": name, "reason": "already has utm_content"})
            continue

        variant = _infer_variant(name)
        if not variant:
            skipped.append({"id": cid, "name": name, "reason": "no variant inferred"})
            continue

        new_tags = _book_utm_tags(variant)
        try:
            await graph_post(cid, data={"url_tags": new_tags}, access_token=ads_service._token())
            patched.append({"id": cid, "name": name, "variant": variant, "url_tags": new_tags})
        except Exception as e:
            errors.append({"id": cid, "name": name, "error": str(e)})

    return {"patched": len(patched), "skipped": len(skipped), "errors": len(errors),
            "details": {"patched": patched, "skipped": skipped, "errors": errors}}


# ── Ad Videos ─────────────────────────────────────────────────────────────────

@router.post("/videos", response_model=AdVideoResponse)
async def upload_video(body: UploadAdVideoRequest, _=Depends(require_admin)):
    try:
        result = await ads_service.upload_ad_video(
            file_url=body.file_url,
            name=body.name,
            title=body.title,
        )
        return AdVideoResponse(id=result["id"], name=body.name, title=body.title)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/videos")
async def list_videos(limit: int = Query(50, ge=1, le=200), _=Depends(require_admin)):
    try:
        return await ads_service.list_ad_videos(limit=limit)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/videos/{video_id}")
async def get_video(video_id: str, _=Depends(require_admin)):
    try:
        return await ads_service.get_ad_video(video_id)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


# ── Pixels ────────────────────────────────────────────────────────────────────

@router.post("/pixels", response_model=PixelResponse)
async def create_pixel(body: CreatePixelRequest, _=Depends(require_admin)):
    try:
        result = await ads_service.create_pixel(name=body.name)
        return PixelResponse(id=result["id"], name=body.name)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/pixels")
async def list_pixels(_=Depends(require_admin)):
    try:
        return await ads_service.list_pixels()
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))


@router.get("/pixels/{pixel_id}", response_model=PixelResponse)
async def get_pixel(pixel_id: str, _=Depends(require_admin)):
    try:
        data = await ads_service.get_pixel(pixel_id)
        return PixelResponse(**data)
    except MetaAPIError as e:
        raise HTTPException(status_code=e.status_code or 502, detail=str(e))
