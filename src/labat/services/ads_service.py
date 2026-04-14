"""
labat/services/ads_service.py — Campaign, AdSet, and Ad CRUD via Marketing API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import os

from src.labat.config import META_AD_ACCOUNT_ID, META_SYSTEM_USER_TOKEN
from src.labat.meta_client import graph_get, graph_post, graph_delete, MetaAPIError
from src.labat.services.notify import send_notification as _notify
from src.labat.services.strategy_rules import (
    get_targeting_preset,
    get_funnel_objective,
)

logger = logging.getLogger("labat.ads_service")


def _acct() -> str:
    if not META_AD_ACCOUNT_ID:
        raise MetaAPIError("META_AD_ACCOUNT_ID not configured", status_code=500)
    return META_AD_ACCOUNT_ID


def _token() -> str:
    if not META_SYSTEM_USER_TOKEN:
        raise MetaAPIError("META_SYSTEM_USER_TOKEN not configured for ads", status_code=500)
    return META_SYSTEM_USER_TOKEN


# ── Campaigns ─────────────────────────────────────────────────────────────────

async def get_account_info() -> Dict[str, Any]:
    return await graph_get(
        _acct(),
        params={
            "fields": "id,name,account_id,account_status,currency,timezone_name,"
                      "disable_reason,funding_source,business_name,owner"
        },
        access_token=_token(),
    )


async def create_campaign(
    name: str,
    objective: str,
    status: str = "PAUSED",
    daily_budget: Optional[int] = None,
    lifetime_budget: Optional[int] = None,
    bid_strategy: str = "LOWEST_COST_WITHOUT_CAP",
    special_ad_categories: Optional[List[str]] = None,
    campaign_budget_optimization: Optional[bool] = None,
    is_adset_budget_sharing_enabled: Optional[bool] = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "name": name,
        "objective": objective,
        "status": status,
        "bid_strategy": bid_strategy,
    }
    import json
    data["special_ad_categories"] = json.dumps(special_ad_categories or [])
    if daily_budget is not None:
        data["daily_budget"] = daily_budget
    if lifetime_budget is not None:
        data["lifetime_budget"] = lifetime_budget
    if campaign_budget_optimization is not None:
        data["campaign_budget_optimization"] = "true" if campaign_budget_optimization else "false"
    if is_adset_budget_sharing_enabled is not None:
        data["is_adset_budget_sharing_enabled"] = "true" if is_adset_budget_sharing_enabled else "false"
    elif campaign_budget_optimization is None:
        # Meta now requires this field when not using CBO
        data["is_adset_budget_sharing_enabled"] = "false"

    result = await graph_post(
        f"{_acct()}/campaigns", data=data, access_token=_token()
    )
    campaign_id = result.get("id")
    logger.info("Created campaign %s: %s", campaign_id, name)
    import asyncio
    asyncio.ensure_future(_notify(
        agent="labat",
        severity="info",
        title=f"New Campaign Created: {name}",
        message=f"Campaign '{name}' created with status {status}.",
        service="labat",
        details={
            "campaign_id": campaign_id,
            "objective": objective,
            "status": status,
            "daily_budget_cents": daily_budget,
        },
    ))
    return result


async def get_campaign(campaign_id: str) -> Dict[str, Any]:
    return await graph_get(
        campaign_id,
        params={
            "fields": "id,name,objective,status,daily_budget,lifetime_budget,"
                      "bid_strategy,created_time,updated_time,"
                      "insights.date_preset(last_30d){spend,impressions,clicks,"
                      "cpc,cpm,ctr,reach,actions,cost_per_result,purchase_roas,"
                      "website_purchase_roas,cost_per_action_type}"
        },
        access_token=_token(),
    )


async def list_campaigns(limit: int = 50) -> Dict[str, Any]:
    return await graph_get(
        f"{_acct()}/campaigns",
        params={
            "fields": "id,name,objective,status,daily_budget,lifetime_budget,bid_strategy,"
                      "created_time,"
                      "insights.date_preset(last_30d){spend,impressions,clicks,cpc,ctr,"
                      "reach,purchase_roas,cost_per_result}",
            "limit": min(limit, 200),
        },
        access_token=_token(),
    )


async def update_campaign(campaign_id: str, **fields: Any) -> Dict[str, Any]:
    allowed = {"name", "status", "daily_budget", "lifetime_budget", "bid_strategy",
               "campaign_budget_optimization"}
    data = {}
    for k, v in fields.items():
        if k in allowed and v is not None:
            if k == "campaign_budget_optimization":
                data[k] = "true" if v else "false"
            else:
                data[k] = v
    if not data:
        raise MetaAPIError("No valid fields to update", status_code=400)
    return await graph_post(campaign_id, data=data, access_token=_token())


async def delete_campaign(campaign_id: str) -> Dict[str, Any]:
    return await graph_delete(campaign_id, access_token=_token())


# ── Ad Sets ───────────────────────────────────────────────────────────────────

async def create_adset(
    campaign_id: str,
    name: str,
    status: str = "PAUSED",
    daily_budget: Optional[int] = None,
    lifetime_budget: Optional[int] = None,
    billing_event: str = "IMPRESSIONS",
    optimization_goal: str = "LINK_CLICKS",
    bid_amount: Optional[int] = None,
    targeting: Optional[Dict[str, Any]] = None,
    destination_type: Optional[str] = None,
    promoted_object: Optional[Dict[str, Any]] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    product: Optional[str] = None,
    funnel_stage: Optional[str] = None,
) -> Dict[str, Any]:
    # Auto-inject targeting preset when targeting is empty and product is known
    if (not targeting) and product:
        targeting = get_targeting_preset(product)
        logger.info("Auto-injected targeting preset for product=%s", product)

    # Auto-set optimization_goal from funnel stage when explicitly provided
    if funnel_stage:
        funnel_cfg = get_funnel_objective(funnel_stage)
        optimization_goal = funnel_cfg["optimization_goal"]
        billing_event = funnel_cfg["billing_event"]
        logger.info("Funnel stage=%s → optimization_goal=%s", funnel_stage, optimization_goal)

    # Auto-inject promoted_object with Pixel ID for conversion-optimised adsets
    if not promoted_object and optimization_goal == "OFFSITE_CONVERSIONS":
        pixel_id = os.getenv("META_PIXEL_ID", "")
        if pixel_id:
            promoted_object = {"pixel_id": pixel_id, "custom_event_type": "PURCHASE"}
            logger.info("Auto-injected promoted_object with pixel_id=%s", pixel_id)

    data: Dict[str, Any] = {
        "campaign_id": campaign_id,
        "name": name,
        "status": status,
        "billing_event": billing_event,
        "optimization_goal": optimization_goal,
    }
    if daily_budget is not None:
        data["daily_budget"] = daily_budget
    if lifetime_budget is not None:
        data["lifetime_budget"] = lifetime_budget
    if bid_amount is not None:
        data["bid_amount"] = bid_amount
    if targeting:
        import json
        # Meta requires advantage_audience flag on all adsets (v19.0+)
        if "targeting_automation" not in targeting:
            targeting["targeting_automation"] = {"advantage_audience": 0}
        data["targeting"] = json.dumps(targeting)
    if destination_type:
        data["destination_type"] = destination_type
    if promoted_object:
        import json
        data["promoted_object"] = json.dumps(promoted_object)
    if start_time:
        data["start_time"] = start_time
    if end_time:
        data["end_time"] = end_time

    result = await graph_post(
        f"{_acct()}/adsets", data=data, access_token=_token()
    )
    logger.info("Created ad set %s: %s", result.get("id"), name)
    return result


async def get_adset(adset_id: str) -> Dict[str, Any]:
    return await graph_get(
        adset_id,
        params={
            "fields": "id,name,campaign_id,status,daily_budget,lifetime_budget,"
                      "billing_event,optimization_goal,destination_type,targeting,created_time"
        },
        access_token=_token(),
    )


async def list_adsets(campaign_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    parent = campaign_id or _acct()
    edge = "adsets" if campaign_id else "adsets"
    return await graph_get(
        f"{parent}/{edge}",
        params={
            "fields": "id,name,campaign_id,status,daily_budget,optimization_goal,created_time",
            "limit": min(limit, 200),
        },
        access_token=_token(),
    )


async def update_adset(adset_id: str, **fields: Any) -> Dict[str, Any]:
    allowed = {"name", "status", "daily_budget", "lifetime_budget", "bid_amount", "targeting"}
    data = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not data:
        raise MetaAPIError("No valid fields to update", status_code=400)
    if "targeting" in data and isinstance(data["targeting"], dict):
        import json
        data["targeting"] = json.dumps(data["targeting"])
    return await graph_post(adset_id, data=data, access_token=_token())


async def delete_adset(adset_id: str) -> Dict[str, Any]:
    return await graph_delete(adset_id, access_token=_token())


# ── Ads ───────────────────────────────────────────────────────────────────────

async def create_ad(
    adset_id: str,
    name: str,
    creative_id: str,
    status: str = "PAUSED",
) -> Dict[str, Any]:
    import json
    data: Dict[str, Any] = {
        "adset_id": adset_id,
        "name": name,
        "status": status,
        "creative": json.dumps({"creative_id": creative_id}),
    }
    result = await graph_post(
        f"{_acct()}/ads", data=data, access_token=_token()
    )
    logger.info("Created ad %s: %s", result.get("id"), name)
    return result


async def get_ad(ad_id: str) -> Dict[str, Any]:
    return await graph_get(
        ad_id,
        params={
            "fields": "id,name,adset_id,status,creative{id,name,object_story_spec},"
                      "created_time,updated_time"
        },
        access_token=_token(),
    )


async def list_ads(adset_id: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    parent = adset_id or _acct()
    return await graph_get(
        f"{parent}/ads",
        params={
            "fields": "id,name,adset_id,status,creative{id,name},created_time",
            "limit": min(limit, 200),
        },
        access_token=_token(),
    )


async def update_ad(ad_id: str, **fields: Any) -> Dict[str, Any]:
    allowed = {"name", "status", "creative_id"}
    data = {}
    for k, v in fields.items():
        if k in allowed and v is not None:
            if k == "creative_id":
                import json
                data["creative"] = json.dumps({"creative_id": v})
            else:
                data[k] = v
    if not data:
        raise MetaAPIError("No valid fields to update", status_code=400)
    return await graph_post(ad_id, data=data, access_token=_token())


async def delete_ad(ad_id: str) -> Dict[str, Any]:
    return await graph_delete(ad_id, access_token=_token())


# ── Ad Creatives ──────────────────────────────────────────────────────────────

async def create_creative(
    name: str,
    object_story_spec: Optional[Dict[str, Any]] = None,
    object_story_id: Optional[str] = None,
    url_tags: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an ad creative. Use object_story_id for existing posts, or object_story_spec for new ad content."""
    import json
    json_body: Dict[str, Any] = {"name": name}
    if object_story_id:
        json_body["object_story_id"] = object_story_id
    elif object_story_spec:
        json_body["object_story_spec"] = object_story_spec
    if url_tags:
        json_body["url_tags"] = url_tags

    logger.info("Creating ad creative: endpoint=%s/adcreatives, data_keys=%s", _acct(), list(json_body.keys()))
    if object_story_spec:
        logger.info("object_story_spec: %s", json.dumps(object_story_spec)[:500])

    result = await graph_post(
        f"{_acct()}/adcreatives", json_body=json_body, access_token=_token()
    )
    logger.info("Created ad creative %s: %s", result.get("id"), name)
    return result


async def list_creatives(limit: int = 50) -> Dict[str, Any]:
    return await graph_get(
        f"{_acct()}/adcreatives",
        params={
            "fields": "id,name,status,object_story_spec,created_time",
            "limit": min(limit, 200),
        },
        access_token=_token(),
    )


# ── Ad Videos ─────────────────────────────────────────────────────────────────

async def upload_ad_video(
    file_url: str,
    name: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload a video to the ad account from a public URL."""
    data: Dict[str, Any] = {
        "file_url": file_url,
        "name": name,
    }
    if title:
        data["title"] = title

    result = await graph_post(
        f"{_acct()}/advideos", data=data, access_token=_token(), timeout=120,
    )
    logger.info("Uploaded ad video %s: %s", result.get("id"), name)
    return result


async def list_ad_videos(limit: int = 50) -> Dict[str, Any]:
    return await graph_get(
        f"{_acct()}/advideos",
        params={
            "fields": "id,title,length,created_time,updated_time,"
                      "thumbnails,status",
            "limit": min(limit, 100),
        },
        access_token=_token(),
    )


async def get_ad_video(video_id: str) -> Dict[str, Any]:
    return await graph_get(
        video_id,
        params={
            "fields": "id,title,length,created_time,updated_time,"
                      "thumbnails,status,source"
        },
        access_token=_token(),
    )


# ── Pixels ────────────────────────────────────────────────────────────────────

async def create_pixel(name: str) -> Dict[str, Any]:
    """Create a new Meta Pixel on the ad account."""
    result = await graph_post(
        f"{_acct()}/adspixels",
        data={"name": name},
        access_token=_token(),
    )
    logger.info("Created pixel %s: %s", result.get("id"), name)
    return result


async def list_pixels() -> Dict[str, Any]:
    """List all pixels on the ad account."""
    return await graph_get(
        f"{_acct()}/adspixels",
        params={
            "fields": "id,name,code,creation_time,last_fired_time,"
                      "is_created_by_app,owner_ad_account",
        },
        access_token=_token(),
    )


async def get_pixel(pixel_id: str) -> Dict[str, Any]:
    """Get a specific pixel by ID."""
    return await graph_get(
        pixel_id,
        params={
            "fields": "id,name,code,creation_time,last_fired_time,"
                      "is_created_by_app,owner_ad_account",
        },
        access_token=_token(),
    )


# ── Automated Rules ──────────────────────────────────────────────────────────

async def create_ad_rule(
    name: str,
    evaluation_spec: Dict[str, Any],
    execution_spec: Dict[str, Any],
    schedule_spec: Optional[Dict[str, Any]] = None,
    status: str = "ENABLED",
) -> Dict[str, Any]:
    """Create a Meta Automated Rule on the ad account.

    evaluation_spec example:
      {"evaluation_type": "SCHEDULE", "filters": [
        {"field": "spent", "value": "10", "operator": "GREATER_THAN"},
        {"field": "result", "value": "0", "operator": "EQUAL"}
      ]}
    execution_spec example:
      {"execution_type": "PAUSE"}
    schedule_spec example:
      {"schedule_type": "SEMI_HOURLY"}
    """
    import json
    data: Dict[str, Any] = {
        "name": name,
        "evaluation_spec": json.dumps(evaluation_spec),
        "execution_spec": json.dumps(execution_spec),
        "status": status,
    }
    if schedule_spec:
        data["schedule_spec"] = json.dumps(schedule_spec)

    result = await graph_post(
        f"{_acct()}/adrules_library", data=data, access_token=_token()
    )
    logger.info("Created ad rule %s: %s", result.get("id"), name)
    return result


async def list_ad_rules() -> Dict[str, Any]:
    """List all automated rules on the ad account."""
    return await graph_get(
        f"{_acct()}/adrules_library",
        params={
            "fields": "id,name,status,evaluation_spec,execution_spec,"
                      "schedule_spec,created_time,updated_time",
        },
        access_token=_token(),
    )


async def get_ad_rule(rule_id: str) -> Dict[str, Any]:
    """Get a specific automated rule."""
    return await graph_get(
        rule_id,
        params={
            "fields": "id,name,status,evaluation_spec,execution_spec,"
                      "schedule_spec,created_time,updated_time,results",
        },
        access_token=_token(),
    )


async def update_ad_rule(rule_id: str, **fields: Any) -> Dict[str, Any]:
    """Update an automated rule (name, status, evaluation_spec, execution_spec, schedule_spec)."""
    import json
    allowed = {"name", "status", "evaluation_spec", "execution_spec", "schedule_spec"}
    data = {}
    for k, v in fields.items():
        if k in allowed and v is not None:
            if k in ("evaluation_spec", "execution_spec", "schedule_spec") and isinstance(v, dict):
                data[k] = json.dumps(v)
            else:
                data[k] = v
    if not data:
        raise MetaAPIError("No valid fields to update", status_code=400)
    return await graph_post(rule_id, data=data, access_token=_token())


async def delete_ad_rule(rule_id: str) -> Dict[str, Any]:
    """Delete an automated rule."""
    return await graph_delete(rule_id, access_token=_token())


async def create_safety_rules(pixel_id: str = "") -> List[Dict[str, Any]]:
    """Create a set of default safety rules for the ad account.

    Rules:
    1. Pause adset if spend > $15 with 0 link clicks (last 3 days)
    2. Pause adset if spend > $30 with 0 link clicks (last 7 days)
    """
    results = []

    # Rule 1: Pause if high spend, zero clicks (short window)
    r1 = await create_ad_rule(
        name="Safety: Pause zero-click adsets ($15+ / 3 days)",
        evaluation_spec={
            "evaluation_type": "SCHEDULE",
            "filters": [
                {"field": "entity_type", "value": "ADSET", "operator": "EQUAL"},
                {"field": "spent", "value": "1500", "operator": "GREATER_THAN"},
                {"field": "clicks", "value": "0", "operator": "EQUAL"},
                {"field": "time_preset", "value": "LAST_3_DAYS", "operator": "EQUAL"},
            ],
        },
        execution_spec={"execution_type": "PAUSE"},
        schedule_spec={"schedule_type": "SEMI_HOURLY"},
    )
    results.append({"rule": "pause_zero_clicks_3d", **r1})

    # Rule 2: Pause if high spend, zero clicks (longer window)
    r2 = await create_ad_rule(
        name="Safety: Pause zero-click adsets ($30+ / 7 days)",
        evaluation_spec={
            "evaluation_type": "SCHEDULE",
            "filters": [
                {"field": "entity_type", "value": "ADSET", "operator": "EQUAL"},
                {"field": "spent", "value": "3000", "operator": "GREATER_THAN"},
                {"field": "clicks", "value": "0", "operator": "EQUAL"},
                {"field": "time_preset", "value": "LAST_7_DAYS", "operator": "EQUAL"},
            ],
        },
        execution_spec={"execution_type": "PAUSE"},
        schedule_spec={"schedule_type": "SEMI_HOURLY"},
    )
    results.append({"rule": "pause_zero_clicks_7d", **r2})

    logger.info("Created %d safety rules", len(results))
    return results
