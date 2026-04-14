"""
alex/routers/alex_routes.py — ALEX admin API endpoints.

Exposes status, manual triggers, and content management for the
ALEX background SEO service.
"""

from fastapi import APIRouter, Header, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import json
import httpx
import os

from src.alex.services.alex_service import get_alex_service
from src.alex.config import INTERNAL_ADMIN_TOKEN, SHANIA_GRAPHICS_URL, LABAT_URL, ALEX_BRAND_SCOPE
from src.labat.services.notify import send_notification
from src.labat.services.strategy_rules import (
    get_targeting_preset,
    get_funnel_objective,
    get_product_domain,
    enhance_targeting_for_funnel,
    get_lead_form_preset,
)
from src.labat.brands import (
    BRAND_PAGE_IDS,
    BRAND_DOMAINS,
    normalize_brand as _normalize_brand,
    get_page_id,
    get_instagram_actor_id,
    get_pixel_id,
)

logger = logging.getLogger("alex.routes")

router = APIRouter(prefix="/api/astra", tags=["astra-discovery"])

BRAND_ENFORCEMENT_MODE = os.getenv("BRAND_ENFORCEMENT_MODE", "warn").strip().lower()
KNOWN_BRANDS = set(BRAND_PAGE_IDS.keys())
LEAD_FORM_BRANDS = {"wihy", "communitygroceries", "vowels"}


def _is_enforce_mode() -> bool:
    return BRAND_ENFORCEMENT_MODE == "enforce"


def _resolve_request_brand(raw_brand: Optional[str], endpoint: str) -> str:
    scoped_brand = (ALEX_BRAND_SCOPE or "").strip().lower() or None

    if not raw_brand or not raw_brand.strip():
        if _is_enforce_mode():
            raise HTTPException(status_code=400, detail="brand is required")
        fallback = scoped_brand or "wihy"
        logger.warning("Missing brand on %s; using %s in %s mode", endpoint, fallback, BRAND_ENFORCEMENT_MODE)
        return fallback

    normalized = _normalize_brand(raw_brand, default="")
    if not normalized or normalized not in KNOWN_BRANDS:
        if _is_enforce_mode():
            raise HTTPException(status_code=400, detail=f"Unknown brand: {raw_brand}")
        fallback = scoped_brand or "wihy"
        logger.warning("Unknown brand '%s' on %s; using %s in %s mode", raw_brand, endpoint, fallback, BRAND_ENFORCEMENT_MODE)
        return fallback

    if scoped_brand and normalized != scoped_brand:
        if _is_enforce_mode():
            raise HTTPException(status_code=403, detail=f"Brand '{normalized}' is not allowed for scope '{scoped_brand}'")
        logger.warning("Cross-scope brand '%s' on %s; forcing '%s' in %s mode", normalized, endpoint, scoped_brand, BRAND_ENFORCEMENT_MODE)
        return scoped_brand

    return normalized


def _resolve_page_id_or_fail(brand_key: str) -> str:
    page_id = BRAND_PAGE_IDS.get(brand_key)
    if not page_id:
        raise HTTPException(status_code=400, detail=f"No Facebook page ID configured for brand '{brand_key}'")
    return page_id


def _resolve_landing_url_or_fail(brand_key: str, landing_url: Optional[str]) -> str:
    expected_domain = BRAND_DOMAINS.get(brand_key)
    if not expected_domain:
        raise HTTPException(status_code=400, detail=f"No domain configured for brand '{brand_key}'")
    resolved = (landing_url or f"https://{expected_domain}").strip()
    if expected_domain not in resolved:
        if _is_enforce_mode():
            raise HTTPException(status_code=400, detail=f"landing_url must match brand domain '{expected_domain}'")
        logger.warning("Landing URL '%s' mismatched for brand %s; forcing https://%s in %s mode", resolved, brand_key, expected_domain, BRAND_ENFORCEMENT_MODE)
        return f"https://{expected_domain}"
    return resolved


def _verify_admin(token: Optional[str] = None) -> bool:
    """Verify internal admin token."""
    if not token or token != INTERNAL_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ── Health & Status ───────────────────────────────────────────────────────────

@router.get("/health")
async def alex_health():
    """ALEX service health check."""
    return {"status": "running", "service": "alex-seo-agent"}


@router.get("/status")
async def alex_status(x_admin_token: Optional[str] = Header(None)):
    """Get ALEX status and cycle stats."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        **service.get_status(),
    }


@router.get("/report")
async def alex_report(x_admin_token: Optional[str] = Header(None)):
    """Generate comprehensive ALEX report."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    return await service.generate_report()


# ── Manual Triggers ───────────────────────────────────────────────────────────

@router.post("/trigger/keywords")
async def trigger_keyword_discovery(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Manually trigger a keyword discovery cycle."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    background_tasks.add_task(service.run_keyword_discovery)
    return {"status": "started", "task": "keyword_discovery"}


@router.post("/trigger/content-queue")
async def trigger_content_queue(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Manually trigger content queue processing."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    background_tasks.add_task(service.run_content_queue)
    return {"status": "started", "task": "content_queue"}


@router.post("/trigger/page-refresh")
async def trigger_page_refresh(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Manually trigger page refresh cycle."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    background_tasks.add_task(service.run_page_refresh)
    return {"status": "started", "task": "page_refresh"}


@router.post("/trigger/opportunities")
async def trigger_opportunity_scan(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Manually trigger opportunity scan."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    background_tasks.add_task(service.run_opportunity_scan)
    return {"status": "started", "task": "opportunity_scan"}


@router.post("/trigger/analytics")
async def trigger_analytics(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Manually trigger analytics ingestion."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    background_tasks.add_task(service.run_analytics_ingestion)
    return {"status": "started", "task": "analytics_ingestion"}


@router.post("/trigger/all")
async def trigger_all_cycles(
    background_tasks: BackgroundTasks,
    x_admin_token: Optional[str] = Header(None),
):
    """Manually trigger all ALEX cycles."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    background_tasks.add_task(service.run_keyword_discovery)
    background_tasks.add_task(service.run_content_queue)
    background_tasks.add_task(service.run_analytics_ingestion)
    background_tasks.add_task(service.run_opportunity_scan)
    return {"status": "started", "task": "all_cycles"}


# ── Dependency Health ─────────────────────────────────────────────────────────

@router.get("/dependencies")
async def check_dependencies(x_admin_token: Optional[str] = Header(None)):
    """Check health of ALEX's dependent services."""
    _verify_admin(x_admin_token)
    service = get_alex_service()
    health = await service.health_check()
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": health,
    }


@router.get("/realtime-signals")
async def realtime_signals(
    query: str,
    brand: Optional[str] = None,
    limit: int = 8,
    refresh_keywords: bool = False,
    x_admin_token: Optional[str] = Header(None),
):
    """Return near-real-time SEO hashtag/keyword signals for downstream generators."""
    _verify_admin(x_admin_token)
    resolved_brand = _resolve_request_brand(brand, "/api/astra/realtime-signals")
    service = get_alex_service()
    if refresh_keywords:
        try:
            await service.run_keyword_discovery()
        except Exception as e:
            logger.warning("ALEX realtime refresh failed: %s", e)
    return await service.get_realtime_signals(query=query, brand=resolved_brand, limit=limit)


# ── Orchestrated Post: Alex → Shania Graphics → LABAT/Shania Delivery ────────


class OrchestratePostRequest(BaseModel):
    prompt: str = Field(..., description="Content topic or prompt")
    brand: str = Field(..., description="Brand: wihy, vowels, communitygroceries, childrennutrition, parentingwithchrist")
    platforms: List[str] = Field(
        default_factory=lambda: ["facebook", "instagram", "threads"],
        description="Platforms: facebook, instagram, threads, linkedin, twitter, tiktok",
    )
    dry_run: bool = Field(default=False, description="Preview without posting")


@router.post("/orchestrate-post")
async def alex_orchestrate_post(
    body: OrchestratePostRequest,
    x_admin_token: Optional[str] = Header(None),
):
    """
    Alex-initiated post pipeline.

    1. Alex provides SEO signals (keywords, trending hashtags)
    2. Shania Graphics generates content + brand asset
    3. Delivered to platforms: LABAT (Facebook/LinkedIn) or Shania (Twitter/Instagram/TikTok)
    """
    _verify_admin(x_admin_token)
    brand_key = _resolve_request_brand(body.brand, "/api/astra/orchestrate-post")

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{SHANIA_GRAPHICS_URL}/orchestrate-post",
                json={
                    "prompt": body.prompt,
                    "brand": brand_key,
                    "platforms": body.platforms,
                    "dryRun": body.dry_run,
                },
                headers={"X-Admin-Token": INTERNAL_ADMIN_TOKEN or ""},
            )
            if resp.status_code == 200:
                result = resp.json()
                logger.info(
                    "ALEX orchestrated post [%s]: brand=%s, platforms=%s, dry_run=%s",
                    body.prompt[:50], brand_key, body.platforms, body.dry_run,
                )

                # Send approval email when a post is queued for review
                approval_id = result.get("approvalId")
                if approval_id and not body.dry_run:
                    caption_preview = (result.get("caption") or "")[:120]
                    dashboard_url = f"{SHANIA_GRAPHICS_URL}/approval/{approval_id}"
                    try:
                        await send_notification(
                            agent="alex",
                            severity="info",
                            title=f"Content post pending approval — {brand_key}",
                            message=(
                                f"A new {brand_key} post needs your review.\n\n"
                                f"Caption: {caption_preview}…\n\n"
                                f"Review & approve: {dashboard_url}"
                            ),
                            service="shania",
                            details={
                                "approvalId": approval_id,
                                "brand": brand_key,
                                "platforms": body.platforms,
                                "imageUrl": result.get("imageUrl"),
                                "dashboardUrl": dashboard_url,
                            },
                        )
                    except Exception as notify_err:
                        logger.warning("Approval email failed (non-blocking): %s", notify_err)

                return {
                    "status": "ok",
                    "source": "alex",
                    **result,
                }
            else:
                logger.warning("Shania Graphics orchestrate failed: %s %s", resp.status_code, resp.text[:200])
                return {
                    "status": "error",
                    "source": "alex",
                    "shania_status": resp.status_code,
                    "detail": resp.text[:500],
                }
        except Exception as e:
            logger.error("ALEX orchestrate-post failed: %s", e)
            raise HTTPException(status_code=502, detail=f"Shania Graphics unreachable: {e}")


# ── Orchestrated Photo Ad: Alex → Shania Image → LABAT Meta Ad Creative ──────


class OrchestratePhotoAdRequest(BaseModel):
    topic: str = Field(..., description="Product/topic to create photo ad for")
    brand: str = Field(..., description="Brand key")
    funnel_stage: str = Field(
        default="conversion",
        description="Funnel stage: awareness, consideration, conversion. Defaults to conversion (sales-focused).",
    )
    landing_url: Optional[str] = Field(
        None,
        description="Landing page URL for the ad CTA. Auto-detected from brand if omitted.",
    )
    ad_copy: Optional[str] = Field(None, description="Custom ad copy / primary text. If omitted, uses Shania's AI-generated caption.")
    headline: Optional[str] = Field(None, description="Ad headline shown below the image (max 40 chars). Defaults to brand name.")
    cta_type: str = Field(default="LEARN_MORE", description="Call-to-action button: LEARN_MORE, SHOP_NOW, SIGN_UP, SUBSCRIBE")
    campaign_id: Optional[str] = Field(None, description="Existing Meta campaign ID. Auto-created if omitted.")
    adset_id: Optional[str] = Field(None, description="Existing Meta ad set ID. Auto-created if omitted.")
    daily_budget: int = Field(default=500, description="Daily budget in cents — default $5/day")
    bid_strategy: str = Field(
        default="auto",
        description="Bid strategy: auto (picks best for funnel), LOWEST_COST_WITHOUT_CAP, COST_CAP, LOWEST_COST_WITH_BID_CAP",
    )
    bid_amount: Optional[int] = Field(None, description="Bid/cost cap in cents. For COST_CAP: max cost per result. For BID_CAP: max bid per auction.")
    output_size: str = Field(default="ad_landscape", description="Image size: ad_landscape (1200x628), feed_square (1080x1080), story_vertical (1080x1920)")
    dry_run: bool = Field(default=False, description="Preview pipeline without uploading to Meta")


@router.post("/orchestrate-photo-ad")
async def alex_orchestrate_photo_ad(
    body: OrchestratePhotoAdRequest,
    x_admin_token: Optional[str] = Header(None),
):
    """
    Full photo-ad pipeline: Alex trends → Shania photo + copy → LABAT Meta ad creative.

    1. Alex discovers trending signals (keywords, hashtags)
    2. Shania generates branded photo + copy via RAG + Gemini + Imagen/template
    3. LABAT creates Meta ad creative with image + copy + CTA
    4. Auto-creates campaign + adset with correct objective/targeting if not provided
    5. Creates the ad under the adset — PAUSED, ready to activate
    """
    _verify_admin(x_admin_token)
    brand_key = _resolve_request_brand(body.brand, "/api/astra/orchestrate-photo-ad")
    landing_url = _resolve_landing_url_or_fail(brand_key, body.landing_url or get_product_domain(brand_key))

    results: Dict[str, Any] = {
        "brand": brand_key,
        "topic": body.topic,
        "funnel_stage": body.funnel_stage,
        "landing_url": landing_url,
        "image": {},
        "creative": {},
        "ad": {},
    }

    # ─── Step 1: Generate photo + copy via Shania ──────────────────────
    logger.info("Photo-ad pipeline: generating image for '%s' [%s]", body.topic, brand_key)
    async with httpx.AsyncClient(timeout=120.0) as client:
        admin_headers = {"X-Admin-Token": INTERNAL_ADMIN_TOKEN or ""}

        try:
            resp = await client.post(
                f"{SHANIA_GRAPHICS_URL}/generate-post",
                json={
                    "prompt": body.topic,
                    "brand": brand_key,
                    "outputSize": body.output_size,
                },
                headers=admin_headers,
            )
            if resp.status_code != 200:
                logger.error("Shania generate-post failed: %s %s", resp.status_code, resp.text[:200])
                results["status"] = "failed"
                results["error"] = f"Shania image generation failed: {resp.text[:200]}"
                return results

            shania_data = resp.json()
            image_url = shania_data.get("imageUrl")
            caption = shania_data.get("caption", "")
            hashtags = shania_data.get("hashtags", [])

            results["image"] = {
                "imageUrl": image_url,
                "caption": caption,
                "hashtags": hashtags,
                "templateId": shania_data.get("templateId"),
                "approvalId": shania_data.get("approvalId"),
            }
            logger.info("Photo-ad pipeline: image generated — %s", image_url)

            if not image_url:
                results["status"] = "failed"
                results["error"] = "Shania returned no imageUrl — image may have failed to upload to GCS."
                return results

        except Exception as e:
            logger.error("Photo-ad pipeline: Shania unreachable — %s", e)
            results["status"] = "failed"
            results["error"] = f"Shania unreachable: {e}"
            return results

    # ─── Build ad copy ─────────────────────────────────────────────────
    if body.ad_copy:
        full_message = body.ad_copy
    elif caption:
        tag_str = " ".join(hashtags) if hashtags else ""
        full_message = f"{caption}\n\n{tag_str}".strip()
    else:
        results["status"] = "failed"
        results["error"] = "No ad copy: provide ad_copy or ensure Shania returns a caption."
        return results

    if body.dry_run:
        results["status"] = "dry_run"
        results["ad_copy_preview"] = full_message
        return results

    # ─── Step 2: Auto-create campaign + adset if not provided ──────────
    funnel_cfg = get_funnel_objective(body.funnel_stage)
    today = datetime.utcnow().strftime("%Y%m%d")

    # Resolve bid strategy: bid (COST_CAP) when we know who converts,
    # paid/budget (LOWEST_COST) when discovering.
    bid_strategy = body.bid_strategy
    bid_amount = body.bid_amount
    if bid_strategy == "auto":
        if body.funnel_stage == "conversion":
            # We KNOW this audience converts (Engaged Shoppers + interests) → bid
            bid_strategy = "COST_CAP"
            bid_amount = bid_amount or 1000          # $10 cost cap per purchase
        else:
            # Awareness & consideration → let Meta spend budget to discover
            bid_strategy = "LOWEST_COST_WITHOUT_CAP"
            bid_amount = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        admin_headers = {"X-Admin-Token": INTERNAL_ADMIN_TOKEN or ""}
        campaign_id = body.campaign_id
        adset_id = body.adset_id

        if not campaign_id:
            try:
                camp_name = f"{brand_key.title()} - {body.funnel_stage.title()} - {body.topic[:40]} - {today}"
                camp_payload: Dict[str, Any] = {
                    "name": camp_name,
                    "objective": funnel_cfg["campaign_objective"],
                    "status": "PAUSED",
                    "daily_budget": body.daily_budget,
                    "bid_strategy": bid_strategy,
                }
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/campaigns",
                    json=camp_payload,
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    campaign_id = resp.json().get("id")
                    results["auto_campaign"] = {
                        "id": campaign_id,
                        "name": camp_name,
                        "objective": funnel_cfg["campaign_objective"],
                    }
                    logger.info("Photo-ad pipeline: auto-created campaign %s (%s)", campaign_id, funnel_cfg["campaign_objective"])
                else:
                    logger.error("Auto-campaign creation failed: %s %s", resp.status_code, resp.text[:200])
                    results["status"] = "failed"
                    results["error"] = f"Auto-campaign creation failed: {resp.text[:200]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Auto-campaign creation error: {e}"
                return results

        if not adset_id and campaign_id:
            try:
                targeting_preset = enhance_targeting_for_funnel(
                    get_targeting_preset(brand_key), body.funnel_stage,
                )
                adset_name = f"{brand_key.title()} - {body.funnel_stage.title()} - {today}"
                adset_payload: Dict[str, Any] = {
                    "campaign_id": campaign_id,
                    "name": adset_name,
                    "status": "PAUSED",
                    "optimization_goal": funnel_cfg["optimization_goal"],
                    "billing_event": funnel_cfg["billing_event"],
                    "targeting": targeting_preset,
                    "funnel_stage": body.funnel_stage,
                    "product": brand_key,
                }
                # Only set destination_type for non-awareness campaigns
                # Meta rejects destination_type on OUTCOME_AWARENESS
                if body.funnel_stage != "awareness":
                    adset_payload["destination_type"] = "WEBSITE"
                if bid_amount:
                    adset_payload["bid_amount"] = bid_amount
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/adsets",
                    json=adset_payload,
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    adset_id = resp.json().get("id")
                    results["auto_adset"] = {
                        "id": adset_id,
                        "name": adset_name,
                        "optimization_goal": funnel_cfg["optimization_goal"],
                        "targeting_preset": brand_key,
                    }
                    logger.info("Photo-ad pipeline: auto-created adset %s", adset_id)
                else:
                    logger.error("Auto-adset creation failed: %s %s", resp.status_code, resp.text[:200])
                    results["status"] = "failed"
                    results["error"] = f"Auto-adset creation failed: {resp.text[:200]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Auto-adset creation error: {e}"
                return results

        # ─── Step 3: Create ad creative with image + copy ──────────────
        page_id = _resolve_page_id_or_fail(brand_key)
        ig_actor_id = get_instagram_actor_id(brand_key)
        ad_headline = body.headline or brand_key.replace("communitygroceries", "Community Groceries").title()

        try:
            story_spec: Dict[str, Any] = {
                "page_id": page_id,
            "link_data": {
                    "message": full_message,
                    "link": landing_url,
                    "picture": image_url,
                    "name": ad_headline,
                    "call_to_action": {
                        "type": body.cta_type,
                        "value": {"link": landing_url},
                    },
                },
            }
            if ig_actor_id:
                story_spec["instagram_user_id"] = ig_actor_id
            creative_payload: Dict[str, Any] = {
                "name": f"{brand_key.title()} Photo Ad - {body.topic[:30]} - {today}",
                "object_story_spec": story_spec,
            }
            resp = await client.post(
                f"{LABAT_URL}/api/labat/ads/creatives",
                json=creative_payload,
                headers=admin_headers,
            )
            if resp.status_code == 200:
                creative_data = resp.json()
                creative_id = creative_data.get("id")
                results["creative"] = creative_data
                logger.info("Photo-ad pipeline: creative created — id=%s", creative_id)
            else:
                results["status"] = "failed"
                results["creative"] = {"error": f"LABAT returned {resp.status_code}: {resp.text[:200]}"}
                results["error"] = "Ad creative creation failed."
                return results
        except Exception as e:
            results["status"] = "failed"
            results["creative"] = {"error": str(e)}
            results["error"] = f"Ad creative creation error: {e}"
            return results

        # ─── Step 4: Create ad under adset ─────────────────────────────
        if creative_id and adset_id:
            try:
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/ads",
                    json={
                        "adset_id": adset_id,
                        "name": f"{brand_key.title()} Photo Ad - {today}",
                        "creative_id": creative_id,
                        "status": "PAUSED",
                    },
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    results["ad"] = resp.json()
                    logger.info("Photo-ad pipeline: ad created — id=%s", resp.json().get("id"))
                else:
                    results["ad"] = {"error": f"LABAT returned {resp.status_code}: {resp.text[:200]}"}
            except Exception as e:
                results["ad"] = {"error": str(e)}

    # ─── Notification ──────────────────────────────────────────────────
    try:
        await send_notification(
            agent="alex",
            severity="info",
            title=f"Photo ad created — {body.topic}",
            message=(
                f"Photo ad pipeline complete for {brand_key}.\n\n"
                f"Image: {image_url}\n"
                f"Creative: {results.get('creative', {}).get('id', 'N/A')}\n"
                f"Ad: {results.get('ad', {}).get('id', 'N/A')}\n"
                f"Landing: {landing_url}\n"
                f"Funnel: {body.funnel_stage} → {funnel_cfg['campaign_objective']}"
            ),
            service="labat",
            details={
                "brand": brand_key,
                "topic": body.topic,
                "funnel_stage": body.funnel_stage,
                "campaign_objective": funnel_cfg["campaign_objective"],
                "optimization_goal": funnel_cfg["optimization_goal"],
                "daily_budget": f"${body.daily_budget / 100:.2f}/day",
                "bid_strategy": bid_strategy,
                "bid_amount": f"${bid_amount / 100:.2f}" if bid_amount else "none (lowest cost)",
                "landing_url": landing_url,
                "cta_type": body.cta_type,
                "ad_copy": full_message[:500],
                "headline": ad_headline,
                "image_url": image_url,
                "image_size": body.output_size,
                "targeting_preset": get_targeting_preset(brand_key),
                "campaign_id": campaign_id,
                "adset_id": adset_id,
                "creative_id": results.get("creative", {}).get("id"),
                "ad_id": results.get("ad", {}).get("id"),
                "ad_status": "PAUSED — activate when ready",
            },
        )
    except Exception as e:
        logger.warning("Photo ad notification failed (non-blocking): %s", e)

    results["status"] = "completed"
    logger.info("Photo-ad pipeline finished for '%s'", body.topic)
    return results


# ── Orchestrated Video Ad: LABAT Video Upload → Meta Ad Creative ─────────────


class OrchestrateVideoAdRequest(BaseModel):
    video_url: str = Field(..., description="Public URL to the video file (GCS, etc.)")
    brand: str = Field(..., description="Brand key")
    funnel_stage: str = Field(default="awareness", description="Funnel stage: awareness, consideration, conversion")
    landing_url: Optional[str] = Field(None, description="Landing page URL. Auto-detected from brand if omitted.")
    ad_copy: str = Field(..., description="Primary text / ad copy shown above the video")
    headline: Optional[str] = Field(None, description="Ad headline (max 40 chars). Defaults to brand name.")
    cta_type: str = Field(default="LEARN_MORE", description="CTA button: LEARN_MORE, SHOP_NOW, SIGN_UP, SUBSCRIBE")
    campaign_id: Optional[str] = Field(None, description="Existing Meta campaign ID. Auto-created if omitted.")
    adset_id: Optional[str] = Field(None, description="Existing Meta ad set ID. Auto-created if omitted.")
    daily_budget: int = Field(default=500, description="Daily budget in cents — default $5/day")
    bid_strategy: str = Field(default="auto", description="Bid strategy: auto, LOWEST_COST_WITHOUT_CAP, COST_CAP")
    bid_amount: Optional[int] = Field(None, description="Bid/cost cap in cents")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL. Meta auto-generates if omitted.")
    video_name: Optional[str] = Field(None, description="Name for the uploaded video in Meta. Auto-generated if omitted.")
    dry_run: bool = Field(default=False, description="Preview pipeline without uploading to Meta")


@router.post("/orchestrate-video-ad")
async def alex_orchestrate_video_ad(
    body: OrchestrateVideoAdRequest,
    x_admin_token: Optional[str] = Header(None),
):
    """
    Full video-ad pipeline: Upload video → LABAT Meta campaign + ad creative.

    1. Upload video to Meta ad account via LABAT
    2. Auto-create campaign + adset with correct objective/targeting if not provided
    3. Create video ad creative with copy + CTA
    4. Create ad under adset — PAUSED, ready to activate
    """
    _verify_admin(x_admin_token)
    brand_key = _resolve_request_brand(body.brand, "/api/astra/orchestrate-video-ad")
    landing_url = _resolve_landing_url_or_fail(brand_key, body.landing_url or get_product_domain(brand_key))
    today = datetime.utcnow().strftime("%Y%m%d")

    results: Dict[str, Any] = {
        "brand": brand_key,
        "video_url": body.video_url,
        "funnel_stage": body.funnel_stage,
        "landing_url": landing_url,
        "video": {},
        "creative": {},
        "ad": {},
    }

    if body.dry_run:
        results["status"] = "dry_run"
        results["ad_copy_preview"] = body.ad_copy
        return results

    async with httpx.AsyncClient(timeout=120.0) as client:
        admin_headers = {"X-Admin-Token": INTERNAL_ADMIN_TOKEN or ""}

        # ─── Step 1: Upload video to Meta ad account ───────────────────
        video_name = body.video_name or f"{brand_key.title()} Video - {today}"
        logger.info("Video-ad pipeline: uploading video for %s", brand_key)
        try:
            resp = await client.post(
                f"{LABAT_URL}/api/labat/ads/videos",
                json={
                    "file_url": body.video_url,
                    "name": video_name,
                    "title": video_name,
                },
                headers=admin_headers,
                timeout=180.0,
            )
            if resp.status_code == 200:
                video_data = resp.json()
                video_id = video_data.get("id")
                results["video"] = video_data
                logger.info("Video-ad pipeline: video uploaded — id=%s", video_id)
            else:
                results["status"] = "failed"
                results["error"] = f"Video upload failed: {resp.text[:300]}"
                return results
        except Exception as e:
            results["status"] = "failed"
            results["error"] = f"Video upload error: {e}"
            return results

        if not video_id:
            results["status"] = "failed"
            results["error"] = "Video upload returned no ID"
            return results

        # ─── Step 2: Auto-create campaign + adset if not provided ──────
        funnel_cfg = get_funnel_objective(body.funnel_stage)

        bid_strategy = body.bid_strategy
        bid_amount = body.bid_amount
        if bid_strategy == "auto":
            if body.funnel_stage == "conversion":
                bid_strategy = "COST_CAP"
                bid_amount = bid_amount or 1000
            else:
                bid_strategy = "LOWEST_COST_WITHOUT_CAP"
                bid_amount = None

        campaign_id = body.campaign_id
        adset_id = body.adset_id

        if not campaign_id:
            try:
                camp_name = f"{brand_key.title()} - {body.funnel_stage.title()} Video - {today}"
                camp_payload: Dict[str, Any] = {
                    "name": camp_name,
                    "objective": funnel_cfg["campaign_objective"],
                    "status": "PAUSED",
                    "daily_budget": body.daily_budget,
                    "bid_strategy": bid_strategy,
                }
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/campaigns",
                    json=camp_payload,
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    campaign_id = resp.json().get("id")
                    results["auto_campaign"] = {"id": campaign_id, "name": camp_name}
                    logger.info("Video-ad pipeline: campaign %s created", campaign_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Campaign creation failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Campaign creation error: {e}"
                return results

        if not adset_id and campaign_id:
            try:
                targeting_preset = enhance_targeting_for_funnel(
                    get_targeting_preset(brand_key), body.funnel_stage,
                )
                adset_name = f"{brand_key.title()} - {body.funnel_stage.title()} Video - {today}"
                adset_payload: Dict[str, Any] = {
                    "campaign_id": campaign_id,
                    "name": adset_name,
                    "status": "PAUSED",
                    "optimization_goal": funnel_cfg["optimization_goal"],
                    "billing_event": funnel_cfg["billing_event"],
                    "targeting": targeting_preset,
                    "funnel_stage": body.funnel_stage,
                    "product": brand_key,
                }
                if body.funnel_stage != "awareness":
                    adset_payload["destination_type"] = "WEBSITE"
                if bid_amount:
                    adset_payload["bid_amount"] = bid_amount
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/adsets",
                    json=adset_payload,
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    adset_id = resp.json().get("id")
                    results["auto_adset"] = {"id": adset_id, "name": adset_name}
                    logger.info("Video-ad pipeline: adset %s created", adset_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Adset creation failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Adset creation error: {e}"
                return results

        # ─── Step 3: Create video ad creative ──────────────────────────
        page_id = _resolve_page_id_or_fail(brand_key)
        ig_actor_id = get_instagram_actor_id(brand_key)
        ad_headline = body.headline or brand_key.replace("communitygroceries", "Community Groceries").title()
        creative_id = None

        try:
            video_data_spec: Dict[str, Any] = {
                "video_id": video_id,
                "message": body.ad_copy,
                "title": ad_headline,
                "call_to_action": {
                    "type": body.cta_type,
                    "value": {"link": landing_url},
                },
            }
            if body.thumbnail_url:
                video_data_spec["image_url"] = body.thumbnail_url

            story_spec: Dict[str, Any] = {
                "page_id": page_id,
                "video_data": video_data_spec,
            }
            if ig_actor_id:
                story_spec["instagram_user_id"] = ig_actor_id
            creative_payload: Dict[str, Any] = {
                "name": f"{brand_key.title()} Video Ad - {today}",
                "object_story_spec": story_spec,
            }
            resp = await client.post(
                f"{LABAT_URL}/api/labat/ads/creatives",
                json=creative_payload,
                headers=admin_headers,
            )
            if resp.status_code == 200:
                creative_data = resp.json()
                creative_id = creative_data.get("id")
                results["creative"] = creative_data
                logger.info("Video-ad pipeline: creative %s created", creative_id)
            else:
                results["status"] = "failed"
                results["creative"] = {"error": resp.text[:300]}
                results["error"] = "Video ad creative creation failed."
                return results
        except Exception as e:
            results["status"] = "failed"
            results["creative"] = {"error": str(e)}
            results["error"] = f"Creative creation error: {e}"
            return results

        # ─── Step 4: Create ad under adset ─────────────────────────────
        if creative_id and adset_id:
            try:
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/ads",
                    json={
                        "adset_id": adset_id,
                        "name": f"{brand_key.title()} Video Ad - {today}",
                        "creative_id": creative_id,
                        "status": "PAUSED",
                    },
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    results["ad"] = resp.json()
                    logger.info("Video-ad pipeline: ad %s created", resp.json().get("id"))
                else:
                    results["ad"] = {"error": resp.text[:300]}
            except Exception as e:
                results["ad"] = {"error": str(e)}

    # ─── Notification ──────────────────────────────────────────────────
    try:
        await send_notification(
            agent="alex",
            severity="info",
            title=f"Video ad created — {brand_key}",
            message=(
                f"Video ad pipeline complete for {brand_key}.\n\n"
                f"Video: {body.video_url}\n"
                f"Creative: {results.get('creative', {}).get('id', 'N/A')}\n"
                f"Ad: {results.get('ad', {}).get('id', 'N/A')}\n"
                f"Landing: {landing_url}\n"
                f"Funnel: {body.funnel_stage}"
            ),
            service="labat",
            details={
                "brand": brand_key,
                "funnel_stage": body.funnel_stage,
                "video_url": body.video_url,
                "video_id": video_id,
                "landing_url": landing_url,
                "campaign_id": campaign_id,
                "adset_id": adset_id,
                "creative_id": creative_id,
                "ad_id": results.get("ad", {}).get("id"),
            },
        )
    except Exception as e:
        logger.warning("Video ad notification failed (non-blocking): %s", e)

    results["status"] = "completed"
    logger.info("Video-ad pipeline finished for %s", brand_key)
    return results


# ── Orchestrate Lead Ad Pipeline ─────────────────────────────────────────────

class OrchestrateLeadAdRequest(BaseModel):
    brand: str = Field(..., description="Brand key: wihy, communitygroceries, vowels")
    video_url: Optional[str] = Field(None, description="Video URL for video lead ad. Omit for image-only.")
    image_url: Optional[str] = Field(None, description="Image URL for the ad creative.")
    ad_copy: str = Field(..., description="Primary ad text shown above the creative")
    headline: Optional[str] = Field(None, description="Ad headline. Defaults to brand name.")
    cta_type: str = Field(default="SIGN_UP", description="CTA button: SIGN_UP, LEARN_MORE, SUBSCRIBE")
    privacy_policy_url: Optional[str] = Field(None, description="Privacy policy URL for lead form. Auto-detected from brand.")
    thank_you_url: Optional[str] = Field(None, description="Thank-you page URL. Auto-detected from brand.")
    form_name: Optional[str] = Field(None, description="Lead form name. Auto-generated if omitted.")
    lead_form_id: Optional[str] = Field(None, description="Existing lead form ID. Skips form creation if provided.")
    campaign_id: Optional[str] = Field(None, description="Existing campaign ID. Auto-created if omitted.")
    adset_id: Optional[str] = Field(None, description="Existing adset ID. Auto-created if omitted.")
    daily_budget: int = Field(default=2500, description="Daily budget in cents — default $25/day")
    dry_run: bool = Field(default=False, description="Preview pipeline without making API calls")


@router.post("/orchestrate-lead-ad")
async def alex_orchestrate_lead_ad(
    body: OrchestrateLeadAdRequest,
    x_admin_token: Optional[str] = Header(None),
):
    """
    Full lead-ad pipeline:
    1. Create lead form on Facebook Page (email + first_name + last_name)
    2. Create OUTCOME_LEADS campaign
    3. Create LEAD_GENERATION adset with lead form attached
    4. Create ad creative (video or image)
    5. Create ad — PAUSED, ready to activate

    Leads are synced to Firestore + email via POST /api/labat/leads/sync
    """
    _verify_admin(x_admin_token)
    brand_key = _resolve_request_brand(body.brand, "/api/astra/orchestrate-lead-ad")
    if brand_key not in LEAD_FORM_BRANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Lead form ads are only allowed for brands: {sorted(LEAD_FORM_BRANDS)}",
        )
    today = datetime.utcnow().strftime("%Y%m%d")
    page_id = _resolve_page_id_or_fail(brand_key)
    ig_actor_id = get_instagram_actor_id(brand_key)

    # Brand-specific defaults — use centralized domain map
    _domain = BRAND_DOMAINS.get(brand_key)
    if not _domain:
        raise HTTPException(status_code=400, detail=f"No domain configured for brand '{brand_key}'")
    landing_url = f"https://{_domain}"
    privacy_url = body.privacy_policy_url or f"{landing_url}/privacy"
    thank_you_url = body.thank_you_url or landing_url

    results: Dict[str, Any] = {
        "brand": brand_key,
        "page_id": page_id,
        "status": "in_progress",
    }

    if body.dry_run:
        results["status"] = "dry_run"
        results["plan"] = {
            "lead_form": f"Create form on page {page_id}",
            "campaign": "OUTCOME_LEADS campaign",
            "adset": "LEAD_GENERATION optimization",
            "creative": "video" if body.video_url else "image",
            "ad_copy_preview": body.ad_copy,
        }
        return results

    async with httpx.AsyncClient(timeout=120.0) as client:
        admin_headers = {"X-Admin-Token": INTERNAL_ADMIN_TOKEN or ""}

        # ─── Pre-check: validate reused adset shape for lead ads ───────
        if body.adset_id:
            try:
                resp = await client.get(
                    f"{LABAT_URL}/api/labat/ads/adsets/{body.adset_id}",
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    adset_data = resp.json()
                    opt_goal = adset_data.get("optimization_goal", "")
                    dest_type = adset_data.get("destination_type", "")
                    if opt_goal != "LEAD_GENERATION":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Reused adset {body.adset_id} has optimization_goal='{opt_goal}'; lead ads require 'LEAD_GENERATION'",
                        )
                    if dest_type and dest_type != "ON_AD":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Reused adset {body.adset_id} has destination_type='{dest_type}'; lead ads require 'ON_AD'",
                        )
                else:
                    logger.warning("Could not fetch adset %s for validation: %s", body.adset_id, resp.status_code)
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("Adset shape pre-check failed (non-blocking): %s", e)

        # ─── Step 1: Create lead form ──────────────────────────────────
        lead_form_id = body.lead_form_id
        if not lead_form_id:
            form_name = body.form_name or f"{brand_key.title()} Lead Capture - {today}"
            try:
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/leads/forms",
                    json={
                        "page_id": page_id,
                        "name": form_name,
                        "privacy_policy_url": privacy_url,
                        "thank_you_url": thank_you_url,
                        "questions": get_lead_form_preset(brand_key),
                    },
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    form_data = resp.json()
                    lead_form_id = form_data.get("id")
                    results["lead_form"] = {"id": lead_form_id, "name": form_name}
                    logger.info("Lead-ad pipeline: form %s created", lead_form_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Lead form creation failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Lead form creation error: {e}"
                return results

        # ─── Step 2: Create OUTCOME_LEADS campaign ─────────────────────
        campaign_id = body.campaign_id
        if not campaign_id:
            try:
                camp_name = f"{brand_key.title()} - Lead Gen - {today}"
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/campaigns",
                    json={
                        "name": camp_name,
                        "objective": "OUTCOME_LEADS",
                        "status": "PAUSED",
                        "daily_budget": body.daily_budget,
                        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    },
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    campaign_id = resp.json().get("id")
                    results["campaign"] = {"id": campaign_id, "name": camp_name}
                    logger.info("Lead-ad pipeline: campaign %s created", campaign_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Campaign creation failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Campaign error: {e}"
                return results

        # ─── Step 3: Create LEAD_GENERATION adset ──────────────────────
        adset_id = body.adset_id
        if not adset_id and campaign_id:
            try:
                targeting_preset = enhance_targeting_for_funnel(
                    get_targeting_preset(brand_key), "awareness",
                )
                targeting_preset["targeting_automation"] = {"advantage_audience": 1}
                adset_name = f"{brand_key.title()} - Lead Gen Adset - {today}"
                adset_payload: Dict[str, Any] = {
                    "campaign_id": campaign_id,
                    "name": adset_name,
                    "status": "PAUSED",
                    "optimization_goal": "LEAD_GENERATION",
                    "billing_event": "IMPRESSIONS",
                    "targeting": targeting_preset,
                    "destination_type": "ON_AD",
                    "promoted_object": {
                        "page_id": page_id,
                    },
                }
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/adsets",
                    json=adset_payload,
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    adset_id = resp.json().get("id")
                    results["adset"] = {"id": adset_id, "name": adset_name}
                    logger.info("Lead-ad pipeline: adset %s created", adset_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Adset creation failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Adset error: {e}"
                return results

        # ─── Step 4: Create ad creative ────────────────────────────────
        ad_headline = body.headline or brand_key.replace("communitygroceries", "Community Groceries").title()
        creative_id = None
        video_id = None

        # Upload video if provided
        if body.video_url:
            try:
                video_name = f"{brand_key.title()} Lead Video - {today}"
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/videos",
                    json={
                        "file_url": body.video_url,
                        "name": video_name,
                        "title": video_name,
                    },
                    headers=admin_headers,
                    timeout=180.0,
                )
                if resp.status_code == 200:
                    video_id = resp.json().get("id")
                    results["video"] = {"id": video_id}
                    logger.info("Lead-ad pipeline: video %s uploaded", video_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Video upload failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Video upload error: {e}"
                return results

        try:
            if video_id:
                video_data_spec: Dict[str, Any] = {
                    "video_id": video_id,
                    "message": body.ad_copy,
                    "title": ad_headline,
                    "call_to_action": {
                        "type": body.cta_type,
                        "value": {"link": landing_url, "lead_gen_form_id": lead_form_id},
                    },
                }
                if body.image_url:
                    video_data_spec["image_url"] = body.image_url
                creative_spec = {"page_id": page_id, "video_data": video_data_spec}
                if ig_actor_id:
                    creative_spec["instagram_user_id"] = ig_actor_id
            else:
                link_data_spec: Dict[str, Any] = {
                    "message": body.ad_copy,
                    "name": ad_headline,
                    "link": landing_url,
                    "call_to_action": {
                        "type": body.cta_type,
                        "value": {"link": landing_url, "lead_gen_form_id": lead_form_id},
                    },
                }
                if body.image_url:
                    link_data_spec["picture"] = body.image_url
                creative_spec = {"page_id": page_id, "link_data": link_data_spec}
                if ig_actor_id:
                    creative_spec["instagram_user_id"] = ig_actor_id

            creative_payload = {
                "name": f"{brand_key.title()} Lead Ad Creative - {today}",
                "object_story_spec": creative_spec,
            }
            resp = await client.post(
                f"{LABAT_URL}/api/labat/ads/creatives",
                json=creative_payload,
                headers=admin_headers,
            )
            if resp.status_code == 200:
                creative_data = resp.json()
                creative_id = creative_data.get("id")
                results["creative"] = creative_data
                logger.info("Lead-ad pipeline: creative %s created", creative_id)
            else:
                results["status"] = "failed"
                results["error"] = f"Creative creation failed: {resp.text[:300]}"
                return results
        except Exception as e:
            results["status"] = "failed"
            results["error"] = f"Creative error: {e}"
            return results

        # ─── Step 5: Create ad ─────────────────────────────────────────
        if creative_id and adset_id:
            try:
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/ads",
                    json={
                        "adset_id": adset_id,
                        "name": f"{brand_key.title()} Lead Ad - {today}",
                        "creative_id": creative_id,
                        "status": "PAUSED",
                    },
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    results["ad"] = resp.json()
                    logger.info("Lead-ad pipeline: ad %s created", resp.json().get("id"))
                else:
                    results["ad"] = {"error": resp.text[:300]}
            except Exception as e:
                results["ad"] = {"error": str(e)}

    # ─── Notification ──────────────────────────────────────────────────
    try:
        await send_notification(
            agent="alex",
            severity="info",
            title=f"Lead ad created — {brand_key}",
            message=(
                f"Lead ad pipeline complete for {brand_key}.\n\n"
                f"Lead Form: {lead_form_id}\n"
                f"Campaign: {campaign_id}\n"
                f"Adset: {adset_id}\n"
                f"Creative: {creative_id}\n"
                f"Ad: {results.get('ad', {}).get('id', 'N/A')}\n\n"
                f"Sync leads with: POST /api/labat/leads/sync?form_id={lead_form_id}"
            ),
            service="labat",
            details={
                "brand": brand_key,
                "lead_form_id": lead_form_id,
                "campaign_id": campaign_id,
                "adset_id": adset_id,
                "creative_id": creative_id,
                "ad_id": results.get("ad", {}).get("id"),
            },
        )
    except Exception as e:
        logger.warning("Lead ad notification failed (non-blocking): %s", e)

    results["status"] = "completed"
    results["sync_endpoint"] = f"POST /api/labat/leads/sync?form_id={lead_form_id}"
    logger.info("Lead-ad pipeline finished for %s", brand_key)
    return results


# ── Orchestrate Website Conversion Ad Pipeline ──────────────────────────────

class OrchestrateWebsiteAdRequest(BaseModel):
    brand: str = Field(..., description="Brand key: wihy, communitygroceries")
    video_url: Optional[str] = Field(None, description="Video URL for video ad. Omit for image-only.")
    image_url: Optional[str] = Field(None, description="Image URL for the ad creative.")
    ad_copy: str = Field(..., description="Primary ad text shown above the creative")
    headline: Optional[str] = Field(None, description="Ad headline. Defaults to brand name.")
    description: Optional[str] = Field(None, description="Ad description (shown below headline).")
    cta_type: str = Field(default="SIGN_UP", description="CTA button: SIGN_UP, LEARN_MORE, SUBSCRIBE")
    landing_url: Optional[str] = Field(None, description="Landing page URL. Auto-detected from brand domain.")
    campaign_id: Optional[str] = Field(None, description="Existing campaign ID. Auto-created if omitted.")
    adset_id: Optional[str] = Field(None, description="Existing adset ID. Auto-created if omitted.")
    daily_budget: int = Field(default=2500, description="Daily budget in cents — default $25/day")
    conversion_event: str = Field(default="Lead", description="Pixel event to optimize for: Lead, CompleteRegistration, etc.")
    advantage_audience: int = Field(default=1, description="Enable Advantage+ audience (1=on, 0=off)")
    dry_run: bool = Field(default=False, description="Preview pipeline without making API calls")


WEBSITE_AD_BRANDS = {"wihy", "communitygroceries"}


@router.post("/orchestrate-website-ad")
async def alex_orchestrate_website_ad(
    body: OrchestrateWebsiteAdRequest,
    x_admin_token: Optional[str] = Header(None),
):
    """
    Full website-conversion ad pipeline (for pre-launch signup capture):
    1. Create OUTCOME_LEADS campaign
    2. Create OFFSITE_CONVERSIONS adset (optimises for pixel Lead event)
    3. Create ad creative linking to landing page
    4. Create ad — PAUSED, ready to activate

    The landing page must have:
    - Meta Pixel installed (fires PageView)
    - fbq('track', 'Lead') on signup form submit
    - Server-side CAPI Lead event from /api/launch/signup
    """
    _verify_admin(x_admin_token)
    brand_key = _resolve_request_brand(body.brand, "/api/astra/orchestrate-website-ad")
    if brand_key not in WEBSITE_AD_BRANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Website ads are only allowed for brands: {sorted(WEBSITE_AD_BRANDS)}",
        )

    today = datetime.utcnow().strftime("%Y%m%d")
    page_id = _resolve_page_id_or_fail(brand_key)
    ig_actor_id = get_instagram_actor_id(brand_key)

    # Brand-specific defaults
    _domain = BRAND_DOMAINS.get(brand_key)
    if not _domain:
        raise HTTPException(status_code=400, detail=f"No domain configured for brand '{brand_key}'")
    landing_url = body.landing_url or f"https://{_domain}"

    # Get pixel ID for the brand
    try:
        pixel_id = get_pixel_id(brand_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    results: Dict[str, Any] = {
        "brand": brand_key,
        "page_id": page_id,
        "pixel_id": pixel_id,
        "landing_url": landing_url,
        "conversion_event": body.conversion_event,
        "status": "in_progress",
    }

    if body.dry_run:
        results["status"] = "dry_run"
        results["plan"] = {
            "campaign": "OUTCOME_LEADS campaign",
            "adset": f"OFFSITE_CONVERSIONS → pixel {body.conversion_event} event",
            "destination": "WEBSITE",
            "creative": "video" if body.video_url else "image",
            "landing_url": landing_url,
            "daily_budget_cents": body.daily_budget,
            "advantage_audience": body.advantage_audience,
            "ad_copy_preview": body.ad_copy,
        }
        return results

    async with httpx.AsyncClient(timeout=120.0) as client:
        admin_headers = {"X-Admin-Token": INTERNAL_ADMIN_TOKEN or ""}

        # ─── Pre-check: validate reused adset shape ────────────────────
        if body.adset_id:
            try:
                resp = await client.get(
                    f"{LABAT_URL}/api/labat/ads/adsets/{body.adset_id}",
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    adset_data = resp.json()
                    opt_goal = adset_data.get("optimization_goal", "")
                    dest_type = adset_data.get("destination_type", "")
                    if opt_goal != "OFFSITE_CONVERSIONS":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Reused adset {body.adset_id} has optimization_goal='{opt_goal}'; website ads require 'OFFSITE_CONVERSIONS'",
                        )
                    if dest_type and dest_type != "WEBSITE":
                        raise HTTPException(
                            status_code=400,
                            detail=f"Reused adset {body.adset_id} has destination_type='{dest_type}'; website ads require 'WEBSITE'",
                        )
                else:
                    logger.warning("Could not fetch adset %s for validation: %s", body.adset_id, resp.status_code)
            except HTTPException:
                raise
            except Exception as e:
                logger.warning("Adset shape pre-check failed (non-blocking): %s", e)

        # ─── Step 1: Create OUTCOME_LEADS campaign ─────────────────────
        campaign_id = body.campaign_id
        if not campaign_id:
            try:
                camp_name = f"{brand_key.title()} - Website Leads - {today}"
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/campaigns",
                    json={
                        "name": camp_name,
                        "objective": "OUTCOME_LEADS",
                        "status": "PAUSED",
                        "daily_budget": body.daily_budget,
                        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                    },
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    campaign_id = resp.json().get("id")
                    results["campaign"] = {"id": campaign_id, "name": camp_name}
                    logger.info("Website-ad pipeline: campaign %s created", campaign_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Campaign creation failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Campaign error: {e}"
                return results

        # ─── Step 2: Create OFFSITE_CONVERSIONS adset ──────────────────
        adset_id = body.adset_id
        if not adset_id and campaign_id:
            try:
                targeting_preset = enhance_targeting_for_funnel(
                    get_targeting_preset(brand_key), "consideration",
                )
                targeting_preset["targeting_automation"] = {
                    "advantage_audience": body.advantage_audience
                }
                adset_name = f"{brand_key.title()} - Website Leads Adset - {today}"
                adset_payload: Dict[str, Any] = {
                    "campaign_id": campaign_id,
                    "name": adset_name,
                    "status": "PAUSED",
                    "optimization_goal": "OFFSITE_CONVERSIONS",
                    "billing_event": "IMPRESSIONS",
                    "targeting": targeting_preset,
                    "destination_type": "WEBSITE",
                    "promoted_object": {
                        "pixel_id": pixel_id,
                        "custom_event_type": body.conversion_event.upper(),
                    },
                }
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/adsets",
                    json=adset_payload,
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    adset_id = resp.json().get("id")
                    results["adset"] = {"id": adset_id, "name": adset_name}
                    logger.info("Website-ad pipeline: adset %s created", adset_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Adset creation failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Adset error: {e}"
                return results

        # ─── Step 3: Create ad creative ────────────────────────────────
        ad_headline = body.headline or brand_key.replace("communitygroceries", "Community Groceries").title()
        creative_id = None
        video_id = None

        # Upload video if provided
        if body.video_url:
            try:
                video_name = f"{brand_key.title()} Website Video - {today}"
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/videos",
                    json={
                        "file_url": body.video_url,
                        "name": video_name,
                        "title": video_name,
                    },
                    headers=admin_headers,
                    timeout=180.0,
                )
                if resp.status_code == 200:
                    video_id = resp.json().get("id")
                    results["video"] = {"id": video_id}
                    logger.info("Website-ad pipeline: video %s uploaded", video_id)
                else:
                    results["status"] = "failed"
                    results["error"] = f"Video upload failed: {resp.text[:300]}"
                    return results
            except Exception as e:
                results["status"] = "failed"
                results["error"] = f"Video upload error: {e}"
                return results

        try:
            cta_value: Dict[str, Any] = {"link": landing_url}
            if video_id:
                video_data_spec: Dict[str, Any] = {
                    "video_id": video_id,
                    "message": body.ad_copy,
                    "title": ad_headline,
                    "call_to_action": {"type": body.cta_type, "value": cta_value},
                }
                if body.image_url:
                    video_data_spec["image_url"] = body.image_url
                creative_spec: Dict[str, Any] = {"page_id": page_id, "video_data": video_data_spec}
                if ig_actor_id:
                    creative_spec["instagram_user_id"] = ig_actor_id
            else:
                link_data_spec: Dict[str, Any] = {
                    "message": body.ad_copy,
                    "name": ad_headline,
                    "link": landing_url,
                    "call_to_action": {"type": body.cta_type, "value": cta_value},
                }
                if body.description:
                    link_data_spec["description"] = body.description
                if body.image_url:
                    link_data_spec["picture"] = body.image_url
                creative_spec = {"page_id": page_id, "link_data": link_data_spec}
                if ig_actor_id:
                    creative_spec["instagram_user_id"] = ig_actor_id

            creative_payload = {
                "name": f"{brand_key.title()} Website Ad Creative - {today}",
                "object_story_spec": creative_spec,
            }
            resp = await client.post(
                f"{LABAT_URL}/api/labat/ads/creatives",
                json=creative_payload,
                headers=admin_headers,
            )
            if resp.status_code == 200:
                creative_data = resp.json()
                creative_id = creative_data.get("id")
                results["creative"] = creative_data
                logger.info("Website-ad pipeline: creative %s created", creative_id)
            else:
                results["status"] = "failed"
                results["error"] = f"Creative creation failed: {resp.text[:300]}"
                return results
        except Exception as e:
            results["status"] = "failed"
            results["error"] = f"Creative error: {e}"
            return results

        # ─── Step 4: Create ad ─────────────────────────────────────────
        if creative_id and adset_id:
            try:
                resp = await client.post(
                    f"{LABAT_URL}/api/labat/ads/ads",
                    json={
                        "adset_id": adset_id,
                        "name": f"{brand_key.title()} Website Ad - {today}",
                        "creative_id": creative_id,
                        "status": "PAUSED",
                    },
                    headers=admin_headers,
                )
                if resp.status_code == 200:
                    results["ad"] = resp.json()
                    logger.info("Website-ad pipeline: ad %s created", resp.json().get("id"))
                else:
                    results["ad"] = {"error": resp.text[:300]}
            except Exception as e:
                results["ad"] = {"error": str(e)}

    # ─── Notification ──────────────────────────────────────────────────
    try:
        await send_notification(
            agent="alex",
            severity="info",
            title=f"Website conversion ad created — {brand_key}",
            message=(
                f"Website conversion ad pipeline complete for {brand_key}.\n\n"
                f"Landing URL: {landing_url}\n"
                f"Pixel: {pixel_id}\n"
                f"Conversion Event: {body.conversion_event}\n"
                f"Campaign: {campaign_id}\n"
                f"Adset: {adset_id}\n"
                f"Creative: {creative_id}\n"
                f"Ad: {results.get('ad', {}).get('id', 'N/A')}\n\n"
                f"Advantage+ Audience: {'ON' if body.advantage_audience else 'OFF'}"
            ),
            service="labat",
            details={
                "brand": brand_key,
                "landing_url": landing_url,
                "pixel_id": pixel_id,
                "conversion_event": body.conversion_event,
                "campaign_id": campaign_id,
                "adset_id": adset_id,
                "creative_id": creative_id,
                "ad_id": results.get("ad", {}).get("id"),
            },
        )
    except Exception as e:
        logger.warning("Website ad notification failed (non-blocking): %s", e)

    results["status"] = "completed"
    logger.info("Website-ad pipeline finished for %s", brand_key)
    return results
