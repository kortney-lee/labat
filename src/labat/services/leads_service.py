"""
labat/services/leads_service.py — Facebook Lead Ads capture.

Fetch lead gen forms attached to the Page, pull submitted leads,
and retrieve individual lead details.  LABAT (system user token)
owns all lead data — leads come from ads, not page engagement.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.labat.brands import BRAND_PAGE_IDS
from src.labat.config import (
    META_AD_ACCOUNT_ID,
    META_SYSTEM_USER_TOKEN,
    SHANIA_PAGE_ACCESS_TOKEN,
)
from src.labat.meta_client import graph_get, graph_post, MetaAPIError

logger = logging.getLogger("labat.leads_service")


def _token() -> str:
    """LABAT system user token — owns lead data."""
    if not META_SYSTEM_USER_TOKEN:
        raise MetaAPIError("META_SYSTEM_USER_TOKEN not configured for leads", status_code=500)
    return META_SYSTEM_USER_TOKEN


def _page_token() -> str:
    """Shania page token — needed to list forms attached to the page."""
    if not SHANIA_PAGE_ACCESS_TOKEN:
        raise MetaAPIError("SHANIA_PAGE_ACCESS_TOKEN not configured", status_code=500)
    return SHANIA_PAGE_ACCESS_TOKEN


# ── Lead Gen Forms ────────────────────────────────────────────────────────────

async def list_lead_forms(
    page_id: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """
    List all lead gen forms attached to the Page.
    Forms are created in Ads Manager under a Lead Generation campaign.
    """
    pid = page_id or BRAND_PAGE_IDS["wihy"]
    if not pid:
        raise MetaAPIError("No page_id configured", status_code=400)

    return await graph_get(
        f"{pid}/leadgen_forms",
        params={
            "fields": "id,name,status,created_time,leads_count,organic_leads_count,"
                      "ad_id,campaign_id,questions",
            "limit": min(limit, 100),
        },
        access_token=_page_token(),
    )


async def get_lead_form(form_id: str) -> Dict[str, Any]:
    """Get full details for a specific lead gen form including questions."""
    return await graph_get(
        form_id,
        params={
            "fields": "id,name,status,created_time,leads_count,organic_leads_count,"
                      "privacy_policy_url,follow_up_action_url,questions,context_card,"
                      "thank_you_page,locale"
        },
        access_token=_page_token(),
    )


# ── Leads (submissions) ───────────────────────────────────────────────────────

async def get_leads_from_form(
    form_id: str,
    limit: int = 50,
    after: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch lead submissions for a form.

    since / until: ISO 8601 timestamps for filtering (e.g. "2026-03-01T00:00:00")
    after: pagination cursor from paging.cursors.after
    """
    params: Dict[str, Any] = {
        "fields": "id,created_time,ad_id,ad_name,adset_id,campaign_id,form_id,field_data",
        "limit": min(limit, 100),
    }
    if after:
        params["after"] = after
    if since:
        params["filtering"] = f'[{{"field":"time_created","operator":"GREATER_THAN","value":"{since}"}}]'
    if until:
        params["filtering"] = f'[{{"field":"time_created","operator":"LESS_THAN","value":"{until}"}}]'

    result = await graph_get(f"{form_id}/leads", params=params, access_token=_token())
    logger.info("Fetched leads from form %s — count: %d", form_id, len(result.get("data", [])))
    return result


async def get_lead(lead_id: str) -> Dict[str, Any]:
    """Get full details for a single lead submission."""
    result = await graph_get(
        lead_id,
        params={
            "fields": "id,created_time,ad_id,ad_name,adset_id,campaign_id,"
                      "form_id,field_data,retailer_item_id,is_organic"
        },
        access_token=_token(),
    )
    # Parse field_data into a clean dict for easy consumption
    parsed: Dict[str, str] = {}
    for field in result.get("field_data", []):
        values = field.get("values", [])
        parsed[field["name"]] = values[0] if len(values) == 1 else values
    result["parsed_fields"] = parsed
    return result


async def get_leads_from_ad(
    ad_id: str,
    limit: int = 50,
    after: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch leads directly from a specific ad."""
    params: Dict[str, Any] = {
        "fields": "id,created_time,ad_id,form_id,field_data",
        "limit": min(limit, 100),
    }
    if after:
        params["after"] = after

    result = await graph_get(f"{ad_id}/leads", params=params, access_token=_token())
    logger.info("Fetched leads from ad %s — count: %d", ad_id, len(result.get("data", [])))
    return result


# ── Lead Cost Summary ─────────────────────────────────────────────────────────

async def get_lead_cost_summary(
    campaign_id: Optional[str] = None,
    date_preset: str = "last_30d",
) -> Dict[str, Any]:
    """
    Return cost-per-lead and total lead count from ad insights.
    Pulls from the ad account (or a specific campaign) via LABAT system token.
    """
    from src.labat.config import META_AD_ACCOUNT_ID
    parent = campaign_id or META_AD_ACCOUNT_ID
    if not parent:
        raise MetaAPIError("No campaign_id or META_AD_ACCOUNT_ID configured", status_code=400)

    level = "campaign" if campaign_id else "account"

    return await graph_get(
        f"{parent}/insights",
        params={
            "level": level,
            "date_preset": date_preset,
            "fields": "campaign_name,spend,impressions,clicks,actions,cost_per_action_type",
        },
        access_token=_token(),
    )


# ── Lead Gen TOS ──────────────────────────────────────────────────────────────

async def accept_leadgen_tos(page_id: str) -> Dict[str, Any]:
    """Accept Facebook Lead Ads Terms of Service for a page."""
    result = await graph_post(
        f"{page_id}/leadgen_tos",
        data={},
        access_token=_token(),
    )
    logger.info("Accepted Lead Gen TOS for page %s: %s", page_id, result)
    return result


async def get_leadgen_tos(page_id: str) -> Dict[str, Any]:
    """Check Lead Gen TOS status for a page."""
    return await graph_get(
        f"{page_id}/leadgen_tos",
        params={"fields": "status"},
        access_token=_token(),
    )


# ── Lead Form Creation ────────────────────────────────────────────────────────

async def create_lead_form(
    page_id: str,
    name: str,
    questions: list[dict[str, str]],
    privacy_policy_url: str,
    thank_you_url: str | None = None,
    context_card: dict[str, Any] | None = None,
    follow_up_action_url: str | None = None,
) -> Dict[str, Any]:
    """
    Create a lead gen form on a Facebook Page.

    questions example:
        [{"type": "EMAIL"}, {"type": "FIRST_NAME"}, {"type": "LAST_NAME"}]
    Supported types: EMAIL, FIRST_NAME, LAST_NAME, FULL_NAME, PHONE, CITY, STATE, ZIP, etc.
    """
    import json

    data: Dict[str, Any] = {
        "name": name,
        "questions": json.dumps(questions),
        "privacy_policy": json.dumps({"url": privacy_policy_url}),
    }
    if follow_up_action_url:
        data["follow_up_action_url"] = follow_up_action_url
    if thank_you_url:
        data["thank_you_page"] = json.dumps({
            "title": "Thank You!",
            "body": "We'll be in touch soon. Check your email for updates.",
            "button_type": "VIEW_WEBSITE",
            "website_url": thank_you_url,
            "button_text": "Visit Website",
        })
    if context_card:
        data["context_card"] = json.dumps(context_card)

    result = await graph_post(
        f"{page_id}/leadgen_forms",
        data=data,
        access_token=_token(),  # system user token — has cross-page access
    )
    logger.info("Created lead form %s: %s", result.get("id"), name)
    return result
