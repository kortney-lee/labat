"""
labat/services/amazon_ads_service.py

Amazon Ads API scaffolding for LABAT.
This provides auth + minimal campaign endpoints to extend later with optimization logic.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from src.labat.config import (
    AMAZON_ADS_API_TIMEOUT,
    AMAZON_ADS_CLIENT_ID,
    AMAZON_ADS_CLIENT_SECRET,
    AMAZON_ADS_REFRESH_TOKEN,
    AMAZON_ADS_REGION,
    AMAZON_ADS_SCOPE_PROFILE_ID,
)

logger = logging.getLogger("labat.amazon_ads")

_REGION_HOSTS = {
    "na": "https://advertising-api.amazon.com",
    "eu": "https://advertising-api-eu.amazon.com",
    "fe": "https://advertising-api-fe.amazon.com",
}

_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


class AmazonAdsAPIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


def _base_url() -> str:
    return _REGION_HOSTS.get(AMAZON_ADS_REGION, _REGION_HOSTS["na"])


def _require_creds() -> None:
    if not AMAZON_ADS_CLIENT_ID or not AMAZON_ADS_CLIENT_SECRET or not AMAZON_ADS_REFRESH_TOKEN:
        raise AmazonAdsAPIError(
            "Amazon Ads credentials are not configured",
            status_code=500,
        )


async def get_access_token() -> str:
    _require_creds()

    data = {
        "grant_type": "refresh_token",
        "refresh_token": AMAZON_ADS_REFRESH_TOKEN,
        "client_id": AMAZON_ADS_CLIENT_ID,
        "client_secret": AMAZON_ADS_CLIENT_SECRET,
    }

    async with httpx.AsyncClient(timeout=AMAZON_ADS_API_TIMEOUT) as client:
        response = await client.post(_TOKEN_URL, data=data)

    if not response.is_success:
        raise AmazonAdsAPIError(
            f"Failed to refresh Amazon Ads access token: {response.text[:300]}",
            status_code=response.status_code,
        )

    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise AmazonAdsAPIError("Amazon Ads token response missing access_token", status_code=502)
    return token


async def _request(
    method: str,
    path: str,
    *,
    scope_profile_id: Optional[str] = None,
    json_body: Optional[Dict[str, Any]] = None,
    query: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    access_token = await get_access_token()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Amazon-Advertising-API-ClientId": AMAZON_ADS_CLIENT_ID,
        "Content-Type": "application/json",
    }

    profile_id = (scope_profile_id or AMAZON_ADS_SCOPE_PROFILE_ID or "").strip()
    if profile_id:
        headers["Amazon-Advertising-API-Scope"] = profile_id

    url = f"{_base_url()}{path}"

    async with httpx.AsyncClient(timeout=AMAZON_ADS_API_TIMEOUT) as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_body,
            params=query,
        )

    if not response.is_success:
        raise AmazonAdsAPIError(
            f"Amazon Ads API error {response.status_code}: {response.text[:500]}",
            status_code=response.status_code,
        )

    if not response.content:
        return {"ok": True}

    body = response.json()
    if isinstance(body, list):
        return {"data": body}
    if isinstance(body, dict):
        return body
    return {"data": body}


async def get_health() -> Dict[str, Any]:
    configured = bool(
        AMAZON_ADS_CLIENT_ID and AMAZON_ADS_CLIENT_SECRET and AMAZON_ADS_REFRESH_TOKEN
    )
    return {
        "configured": configured,
        "region": AMAZON_ADS_REGION,
        "base_url": _base_url(),
        "scope_profile_id": bool(AMAZON_ADS_SCOPE_PROFILE_ID),
    }


async def list_profiles() -> Dict[str, Any]:
    return await _request("GET", "/v2/profiles")


async def list_sp_campaigns(
    state_filter: Optional[str] = None,
    scope_profile_id: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if state_filter:
        payload["stateFilter"] = {
            "include": [state_filter],
        }

    return await _request(
        "POST",
        "/sp/campaigns/list",
        scope_profile_id=scope_profile_id,
        json_body=payload,
    )


async def create_sp_campaign(
    campaign: Dict[str, Any],
    scope_profile_id: Optional[str] = None,
) -> Dict[str, Any]:
    # Amazon Sponsored Products create endpoint accepts an array.
    payload = [campaign]
    return await _request(
        "POST",
        "/sp/campaigns",
        scope_profile_id=scope_profile_id,
        json_body=payload,
    )
