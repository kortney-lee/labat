"""
labat/routers/amazon_ads_routes.py

Amazon Ads API scaffolding routes.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.labat.auth import require_admin
from src.labat.config import AMAZON_ADS_CLIENT_ID, AMAZON_ADS_CLIENT_SECRET
from src.labat.schemas import AmazonSPCampaignCreateRequest
from src.labat.services import amazon_ads_service
from src.labat.services.amazon_ads_service import AmazonAdsAPIError

logger = logging.getLogger("labat.amazon_ads_routes")

router = APIRouter(prefix="/api/labat/amazon-ads", tags=["labat-amazon-ads"])

_REDIRECT_URI = "https://labat.wihy.ai/api/labat/amazon-ads/callback"
_TOKEN_URL = "https://api.amazon.com/auth/o2/token"


@router.get("/callback", include_in_schema=False)
async def oauth_callback(
    code: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
):
    """
    Receives the Amazon OAuth authorization code and exchanges it for a refresh token.
    Visit /api/labat/amazon-ads/authorize to begin the flow.
    """
    if error:
        return HTMLResponse(
            f"<h2>Amazon OAuth Error</h2><pre>{error}: {error_description}</pre>",
            status_code=400,
        )
    if not code:
        return HTMLResponse("<h2>No code received from Amazon.</h2>", status_code=400)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _REDIRECT_URI,
                "client_id": AMAZON_ADS_CLIENT_ID,
                "client_secret": AMAZON_ADS_CLIENT_SECRET,
            },
        )

    if not resp.is_success:
        return HTMLResponse(
            f"<h2>Token exchange failed ({resp.status_code})</h2><pre>{resp.text}</pre>",
            status_code=502,
        )

    data = resp.json()
    refresh_token = data.get("refresh_token", "")
    access_token = data.get("access_token", "")

    html = f"""<!DOCTYPE html>
<html>
<head><title>Amazon Ads OAuth Complete</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:40px auto;padding:0 20px}}
code{{background:#f4f4f4;padding:4px 8px;border-radius:4px;word-break:break-all;display:block;margin:8px 0}}
.step{{background:#e8f5e9;border-left:4px solid #4caf50;padding:12px 16px;margin:16px 0}}
</style></head>
<body>
<h1>Amazon Ads OAuth - Complete</h1>
<div class="step"><strong>Step 1 done.</strong> Copy your refresh token below and give it to the agent.</div>

<h3>Refresh Token</h3>
<code id="rt">{refresh_token}</code>

<h3>Next: run this gcloud command (or paste the refresh token in chat)</h3>
<code>gcloud run services update wihy-labat --region us-central1 --project wihy-ai --update-env-vars "AMAZON_ADS_REFRESH_TOKEN={refresh_token}"</code>

<h3>Then get your profile ID</h3>
<code>curl -H "Authorization: Bearer {access_token}" -H "Amazon-Advertising-API-ClientId: {AMAZON_ADS_CLIENT_ID}" https://advertising-api.amazon.com/v2/profiles</code>

<p><em>Access token is one-time and short-lived. Use the refresh token to get new ones via the service.</em></p>
</body></html>"""

    return HTMLResponse(html)


@router.get("/authorize", include_in_schema=False)
async def oauth_authorize():
    """Redirects browser to Amazon authorization page to start the OAuth flow."""
    from fastapi.responses import RedirectResponse
    import urllib.parse

    params = urllib.parse.urlencode({
        "client_id": AMAZON_ADS_CLIENT_ID,
        "scope": "advertising::campaign_management",
        "response_type": "code",
        "redirect_uri": _REDIRECT_URI,
    })
    return RedirectResponse(f"https://www.amazon.com/ap/oa?{params}")


@router.get("/health", dependencies=[Depends(require_admin)])
async def health():
    return await amazon_ads_service.get_health()


@router.get("/profiles", dependencies=[Depends(require_admin)])
async def profiles():
    try:
        return await amazon_ads_service.list_profiles()
    except AmazonAdsAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/campaigns/sp", dependencies=[Depends(require_admin)])
async def list_sp_campaigns(
    state_filter: Optional[str] = Query(default=None),
    profile_id: Optional[str] = Query(default=None),
):
    try:
        return await amazon_ads_service.list_sp_campaigns(
            state_filter=state_filter,
            scope_profile_id=profile_id,
        )
    except AmazonAdsAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/campaigns/sp", dependencies=[Depends(require_admin)])
async def create_sp_campaign(body: AmazonSPCampaignCreateRequest):
    try:
        return await amazon_ads_service.create_sp_campaign(
            campaign=body.campaign,
            scope_profile_id=body.profile_id,
        )
    except AmazonAdsAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
