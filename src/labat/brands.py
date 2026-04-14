"""
Centralized brand-to-page mapping for all WIHY brands.

Single source of truth -- import from here instead of hardcoding page IDs.
Each brand owns its own Facebook page. Never cross brands.

See also: shania/src/config/brand.ts (TypeScript equivalent)
"""

from __future__ import annotations

import os
from typing import Dict, Optional


# Brand -> Facebook Page ID (loaded from env vars, with hardcoded fallbacks for local dev)
# .strip() guards against trailing whitespace/newlines in Secret Manager values
BRAND_PAGE_IDS: Dict[str, str] = {
    "wihy": os.getenv("META_PAGE_ID_WIHY", "937763702752161").strip(),
    "vowels": os.getenv("META_PAGE_ID_VOWELS", "100193518975897").strip(),
    "communitygroceries": os.getenv("META_PAGE_ID_COMMUNITYGROCERIES", "2051601018287997").strip(),
    "childrennutrition": os.getenv("META_PAGE_ID_CHILDRENNUTRITION", "269598952893508").strip(),
    "parentingwithchrist": os.getenv("META_PAGE_ID_PARENTINGWITHCHRIST", "329626030226536").strip(),
}

# Brand -> Instagram Actor ID (page-backed IG accounts for ad creatives)
# CG and Otaku use real IG business account IDs; others use page-backed IDs
BRAND_INSTAGRAM_IDS: Dict[str, str] = {
    "wihy": os.getenv("META_IG_ID_WIHY", "17841478427607771").strip(),
    "vowels": os.getenv("META_IG_ID_VOWELS", "17841448164085103").strip(),
    "communitygroceries": os.getenv("META_IG_ID_COMMUNITYGROCERIES", "17841445312259126").strip(),
    "childrennutrition": os.getenv("META_IG_ID_CHILDRENNUTRITION", "17841470986083057").strip(),
    "parentingwithchrist": os.getenv("META_IG_ID_PARENTINGWITHCHRIST", "17841466415337829").strip(),
}

# Brand -> Business Asset Group ID (Meta Business Manager grouping)
BRAND_ASSET_GROUP_IDS: Dict[str, str] = {
    "wihy": os.getenv("META_ASSET_GROUP_WIHY", "1070737106120589"),
    "vowels": os.getenv("META_ASSET_GROUP_VOWELS", "1095437846983151"),
    "communitygroceries": os.getenv("META_ASSET_GROUP_CG", "1103795412808795"),
}

# Reverse: Page ID -> brand key
PAGE_BRAND_MAP: Dict[str, str] = {v: k for k, v in BRAND_PAGE_IDS.items()}

# Brand -> domain
BRAND_DOMAINS: Dict[str, str] = {
    "wihy": "wihy.ai",
    "vowels": "vowels.org",
    "communitygroceries": "communitygroceries.com",
    "childrennutrition": "whatishealthy.org",
    "parentingwithchrist": "parentingwithchrist.com",
}

# Alias -> canonical brand key
_BRAND_ALIASES: Dict[str, str] = {
    "wihy": "wihy",
    "vowels": "vowels",
    "trinity": "vowels",
    "book": "vowels",
    "vowelsbook": "vowels",
    "communitygroceries": "communitygroceries",
    "cg": "communitygroceries",
    "community groceries": "communitygroceries",
    "community-groceries": "communitygroceries",
    "childrennutrition": "childrennutrition",
    "childrens-nutrition": "childrennutrition",
    "children": "childrennutrition",
    "whatishealthy": "childrennutrition",
    "what-is-healthy": "childrennutrition",
    "parentingwithchrist": "parentingwithchrist",
    "parenting": "parentingwithchrist",
    "pwc": "parentingwithchrist",
}


def normalize_brand(brand: Optional[str], default: str = "wihy") -> str:
    """Resolve any brand alias to its canonical key."""
    if not brand:
        return default
    return _BRAND_ALIASES.get(brand.strip().lower(), default)


def get_page_id(brand: Optional[str]) -> str:
    """Get the Facebook Page ID for a brand (with alias resolution).

    Raises ValueError if the brand resolves to an unknown key.
    """
    key = normalize_brand(brand)
    page_id = BRAND_PAGE_IDS.get(key)
    if not page_id:
        raise ValueError(f"No Facebook page ID for brand '{brand}' (resolved: '{key}')")
    return page_id


def get_instagram_actor_id(brand: Optional[str]) -> Optional[str]:
    """Get the Instagram Actor ID for a brand (for ad creatives)."""
    key = normalize_brand(brand)
    return BRAND_INSTAGRAM_IDS.get(key)


# Brand -> Meta Pixel ID (for conversion tracking / website ads)
# All brands share one pixel on the ad account; override per-brand via env vars.
_DEFAULT_PIXEL = os.getenv("META_PIXEL_ID", "")
BRAND_PIXEL_IDS: Dict[str, str] = {
    "wihy": os.getenv("META_PIXEL_ID_WIHY", _DEFAULT_PIXEL).strip(),
    "communitygroceries": os.getenv("META_PIXEL_ID_CG", _DEFAULT_PIXEL).strip(),
}


def get_pixel_id(brand: Optional[str]) -> str:
    """Get the Meta Pixel ID for a brand.

    Raises ValueError if no pixel is configured.
    """
    key = normalize_brand(brand)
    pixel_id = BRAND_PIXEL_IDS.get(key, _DEFAULT_PIXEL)
    if not pixel_id:
        raise ValueError(f"No Meta Pixel ID configured for brand '{brand}' (resolved: '{key}')")
    return pixel_id


def get_asset_group_id(brand: Optional[str]) -> Optional[str]:
    """Get the Business Asset Group ID for a brand."""
    key = normalize_brand(brand)
    return BRAND_ASSET_GROUP_IDS.get(key)


def get_brand_for_page(page_id: str) -> Optional[str]:
    """Get the canonical brand key for a Facebook Page ID."""
    return PAGE_BRAND_MAP.get(page_id)
