"""
labat/services/insights_service.py — Pull ad insights from the Marketing API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.labat.config import (
    META_AD_ACCOUNT_ID,
    META_SYSTEM_USER_TOKEN,
    META_INSIGHTS_TIMEOUT,
)
from src.labat.meta_client import graph_get, MetaAPIError

logger = logging.getLogger("labat.insights_service")


def _acct() -> str:
    if not META_AD_ACCOUNT_ID:
        raise MetaAPIError("META_AD_ACCOUNT_ID not configured", status_code=500)
    return META_AD_ACCOUNT_ID


def _token() -> str:
    if not META_SYSTEM_USER_TOKEN:
        raise MetaAPIError("META_SYSTEM_USER_TOKEN not configured", status_code=500)
    return META_SYSTEM_USER_TOKEN


async def get_insights(
    object_id: Optional[str] = None,
    level: str = "campaign",
    date_preset: str = "last_7d",
    fields: Optional[List[str]] = None,
    time_increment: Optional[int] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Fetch ad insights at the given level.

    object_id: campaign/adset/ad ID — or None to use the ad account.
    level: account | campaign | adset | ad
    date_preset: today | yesterday | last_7d | last_30d | lifetime | ...
    fields: list of metric fields (defaults to common set)
    time_increment: 1=daily breakdown, 7=weekly, etc.
    """
    parent = object_id or _acct()
    default_fields = [
        "campaign_name", "adset_name",
        "impressions", "clicks", "reach", "spend",
        "cpc", "cpm", "ctr",
        "actions", "cost_per_action_type",
        "purchase_roas", "website_purchase_roas",
        "cost_per_result", "conversions", "conversion_values",
    ]
    selected_fields = fields or default_fields

    params: Dict[str, Any] = {
        "level": level,
        "date_preset": date_preset,
        "fields": ",".join(selected_fields),
        "limit": min(limit, 500),
    }
    if time_increment is not None:
        params["time_increment"] = time_increment

    return await graph_get(
        f"{parent}/insights",
        params=params,
        access_token=_token(),
        timeout=META_INSIGHTS_TIMEOUT,
    )


async def get_campaign_insights(campaign_id: str, date_preset: str = "last_7d") -> Dict[str, Any]:
    """Convenience: get insights for one campaign."""
    return await get_insights(
        object_id=campaign_id,
        level="campaign",
        date_preset=date_preset,
    )


async def get_account_summary(date_preset: str = "last_30d") -> Dict[str, Any]:
    """Account-level spend and revenue summary across all campaigns."""
    return await get_insights(
        level="account",
        date_preset=date_preset,
        fields=[
            "impressions", "clicks", "reach", "spend",
            "cpc", "cpm", "ctr",
            "actions", "cost_per_action_type",
            "purchase_roas", "website_purchase_roas",
            "cost_per_result", "conversions", "conversion_values",
        ],
    )


# ── Brand-Scoped Insights ─────────────────────────────────────────────────────

# Campaign naming convention: "{Brand} - {Funnel} - {Topic} - {Date}"
# Brand is always the first token before " - ".

_BRAND_ALIASES = {
    "cg": "communitygroceries",
    "community": "communitygroceries",
    "community groceries": "communitygroceries",
    "trinity": "vowels",
    "book": "vowels",
    "whatishealthy": "childrennutrition",
    "children": "childrennutrition",
    "parenting": "parentingwithchrist",
    "pwc": "parentingwithchrist",
}


def _extract_brand_from_campaign(campaign_name: str) -> str:
    """Extract brand key from campaign name (first token before ' - ')."""
    if not campaign_name:
        return ""
    raw = campaign_name.split(" - ")[0].strip().lower()
    return _BRAND_ALIASES.get(raw, raw)


def _row_matches_brand(row: Dict[str, Any], brand: str) -> bool:
    """Check if an insights row belongs to a brand by campaign name prefix."""
    campaign_name = row.get("campaign_name", "")
    extracted = _extract_brand_from_campaign(campaign_name)
    return extracted == brand.lower()


async def get_insights_by_brand(
    brand: str,
    level: str = "campaign",
    date_preset: str = "last_7d",
    fields: Optional[List[str]] = None,
    time_increment: Optional[int] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """
    Fetch ad insights filtered to a single brand.

    Calls the account-wide get_insights() then filters rows where
    campaign_name starts with the brand prefix (e.g. "Wihy - ...").

    Returns the same structure as get_insights() but with only matching rows.
    """
    # Ensure campaign_name is in the fields so we can filter
    default_fields = fields or [
        "campaign_name", "adset_name",
        "impressions", "clicks", "reach", "spend",
        "cpc", "cpm", "ctr",
        "actions", "cost_per_action_type",
        "purchase_roas", "website_purchase_roas",
        "cost_per_result", "conversions", "conversion_values",
    ]
    if "campaign_name" not in default_fields:
        default_fields = ["campaign_name"] + list(default_fields)

    result = await get_insights(
        level=level,
        date_preset=date_preset,
        fields=default_fields,
        time_increment=time_increment,
        limit=limit,
    )

    all_rows = result.get("data", [])
    filtered = [row for row in all_rows if _row_matches_brand(row, brand)]

    logger.info(
        "Brand filter: brand=%s, total_rows=%d, matched=%d",
        brand, len(all_rows), len(filtered),
    )

    return {"data": filtered}
