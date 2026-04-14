"""
labat/routers/trending_routes.py - Trending meals endpoints.

Exposes a Labat endpoint that fetches user meal payloads from user.wihy.ai,
then returns normalized data for Trending page rendering.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from src.shared.auth.auth_client import verify_token
from src.labat.auth import require_admin
from src.labat.services.trending_service import get_user_meals_data, get_meal_templates

logger = logging.getLogger("labat.trending_routes")

router = APIRouter(prefix="/api/labat/trending", tags=["labat-trending"])


async def require_trending_access(request: Request) -> None:
    """Allow LABAT admin credentials or a valid Bearer JWT for this route."""
    try:
        require_admin(request)
        return
    except HTTPException as exc:
        if exc.status_code != 401:
            raise

    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        user = await verify_token(token)
        if user and user.get("id"):
            request.state.auth_user_id = str(user["id"])
            return

    raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/users/{user_id}/meals")
async def proxy_user_meals(
    user_id: str,
    request: Request,
    _=Depends(require_trending_access),
) -> Any:
    """Fetch user.wihy.ai meals endpoint for Trending rendering (explicit user id)."""
    try:
        return await get_user_meals_data(
            user_id=user_id,
            query_params=list(request.query_params.multi_items()),
            authorization_header=request.headers.get("Authorization"),
            client_id_header=request.headers.get("X-Client-ID"),
            client_secret_header=request.headers.get("X-Client-Secret"),
            user_id_header=request.headers.get("X-User-ID"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in trending meals proxy for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail="Failed to fetch trending meals")


@router.get("/meals")
async def proxy_user_meals_without_path_user(
    request: Request,
    user_id: Optional[str] = Query(None, description="Optional user id. If omitted, inferred from X-User-ID or Bearer token."),
    _=Depends(require_trending_access),
) -> Any:
    """Fetch meals without requiring user id in the path first."""
    auth_user_id = getattr(request.state, "auth_user_id", None)
    try:
        return await get_user_meals_data(
            user_id=user_id or auth_user_id,
            query_params=list(request.query_params.multi_items()),
            authorization_header=request.headers.get("Authorization"),
            client_id_header=request.headers.get("X-Client-ID"),
            client_secret_header=request.headers.get("X-Client-Secret"),
            user_id_header=request.headers.get("X-User-ID"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in trending meals fetch: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch trending meals")


@router.get("/templates")
async def public_meal_templates(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = Query(None, description="Filter by meal category: breakfast, lunch, dinner, snack"),
) -> Any:
    """Public meal templates — no user data, no auth required. Safe for SEO crawlers."""
    try:
        return await get_meal_templates(
            limit=limit,
            offset=offset,
            category=category,
            client_id_header=request.headers.get("X-Client-ID"),
            client_secret_header=request.headers.get("X-Client-Secret"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in meal templates fetch: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch meal templates")
