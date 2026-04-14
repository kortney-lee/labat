"""
labat/services/trending_service.py - Trending meals fetch helpers.

Fetches user meals data from user.wihy.ai and normalizes payload shape for
Labat Trending consumers.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Any, Optional, Sequence, Tuple

import httpx
from fastapi import HTTPException

logger = logging.getLogger("labat.trending_service")

USER_SERVICE_DIRECT_URL = os.getenv("USER_SERVICE_DIRECT_URL", "https://user.wihy.ai").rstrip("/")
WIHY_ML_CLIENT_ID = os.getenv("WIHY_ML_CLIENT_ID", "wihy_ml_mk1waylw").strip()
WIHY_ML_CLIENT_SECRET = (os.getenv("WIHY_ML_CLIENT_SECRET", "") or "").strip()
LABAT_TRENDING_PROXY_TIMEOUT = float(os.getenv("LABAT_TRENDING_PROXY_TIMEOUT", "30"))


def _extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    if not authorization_header:
        return None
    value = authorization_header.strip()
    if not value.lower().startswith("bearer "):
        return None
    token = value[7:].strip()
    return token or None


def _extract_user_id_from_jwt(authorization_header: Optional[str]) -> Optional[str]:
    """Best-effort user id extraction from JWT payload (without verification)."""
    token = _extract_bearer_token(authorization_header)
    if not token:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    payload_b64 = parts[1]
    pad_len = (4 - (len(payload_b64) % 4)) % 4
    payload_b64 += "=" * pad_len

    try:
        payload_raw = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        return None

    for key in ("user_id", "userId", "id", "sub"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _resolve_user_id(
    user_id: Optional[str],
    authorization_header: Optional[str],
    user_id_header: Optional[str],
) -> Optional[str]:
    if user_id and user_id.strip():
        return user_id.strip()
    if user_id_header and user_id_header.strip():
        return user_id_header.strip()
    return _extract_user_id_from_jwt(authorization_header)


def _coerce_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _normalize_user_meals_payload(raw_payload: Any) -> dict[str, Any]:
    """Normalize upstream response to stable keys used by Trending."""
    if not isinstance(raw_payload, dict):
        return {
            "success": False,
            "templates": [],
            "user_meals": [],
            "count": 0,
            "total": 0,
            "user_meals_count": 0,
            "detail": "Unexpected upstream payload format",
        }

    payload: dict[str, Any] = dict(raw_payload)
    data_block = payload.get("data")
    if isinstance(data_block, dict):
        merged = dict(data_block)
        for key in ("success", "detail", "message", "error"):
            if key in payload and key not in merged:
                merged[key] = payload[key]
        payload = merged

    templates = _coerce_list(payload.get("templates"))
    user_meals = _coerce_list(payload.get("user_meals"))

    count = payload.get("count")
    if not isinstance(count, int):
        count = len(templates)

    total = payload.get("total")
    if not isinstance(total, int):
        total = count

    user_meals_count = payload.get("user_meals_count")
    if not isinstance(user_meals_count, int):
        user_meals_count = len(user_meals)

    normalized: dict[str, Any] = dict(payload)
    normalized["templates"] = templates
    normalized["user_meals"] = user_meals
    normalized["count"] = count
    normalized["total"] = total
    normalized["user_meals_count"] = user_meals_count

    if "success" not in normalized:
        normalized["success"] = True

    return normalized


def _build_headers(
    authorization_header: Optional[str],
    client_id_header: Optional[str],
    client_secret_header: Optional[str],
) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/json",
    }

    if authorization_header:
        headers["Authorization"] = authorization_header

    # Prefer caller-provided credentials when present.
    if client_secret_header:
        headers["X-Client-ID"] = (client_id_header or WIHY_ML_CLIENT_ID).strip()
        headers["X-Client-Secret"] = client_secret_header.strip()
    # Fallback to service credentials.
    elif WIHY_ML_CLIENT_SECRET:
        headers["X-Client-ID"] = WIHY_ML_CLIENT_ID
        headers["X-Client-Secret"] = WIHY_ML_CLIENT_SECRET

    return headers


async def get_user_meals_data(
    user_id: Optional[str],
    query_params: Sequence[Tuple[str, str]],
    authorization_header: Optional[str] = None,
    client_id_header: Optional[str] = None,
    client_secret_header: Optional[str] = None,
    user_id_header: Optional[str] = None,
) -> Any:
    """Fetch and normalize GET user.wihy.ai/api/users/{user_id}/meals."""
    resolved_user_id = _resolve_user_id(
        user_id=user_id,
        authorization_header=authorization_header,
        user_id_header=user_id_header,
    )
    if not resolved_user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing user_id. Provide path/query user_id, X-User-ID, or a Bearer token with user id claim.",
        )

    url = f"{USER_SERVICE_DIRECT_URL}/api/users/{resolved_user_id}/meals"
    headers = _build_headers(
        authorization_header=authorization_header,
        client_id_header=client_id_header,
        client_secret_header=client_secret_header,
    )

    try:
        async with httpx.AsyncClient(timeout=LABAT_TRENDING_PROXY_TIMEOUT) as client:
            resp = await client.get(url, params=list(query_params), headers=headers)
    except httpx.TimeoutException as e:
        logger.error("Trending meals proxy timeout for user %s: %s", resolved_user_id, e)
        raise HTTPException(status_code=504, detail="Trending meals upstream timeout")
    except httpx.RequestError as e:
        logger.error("Trending meals proxy request error for user %s: %s", resolved_user_id, e)
        raise HTTPException(status_code=502, detail="Trending meals upstream unavailable")

    try:
        payload = resp.json()
    except ValueError:
        payload = {
            "success": False,
            "detail": resp.text,
        }

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=payload)

    return _normalize_user_meals_payload(payload)


async def get_user_meals_proxy(
    user_id: Optional[str],
    query_params: Sequence[Tuple[str, str]],
    authorization_header: Optional[str] = None,
    client_id_header: Optional[str] = None,
    client_secret_header: Optional[str] = None,
    user_id_header: Optional[str] = None,
) -> Any:
    """Backward-compatible alias for older call sites."""
    return await get_user_meals_data(
        user_id=user_id,
        query_params=query_params,
        authorization_header=authorization_header,
        client_id_header=client_id_header,
        client_secret_header=client_secret_header,
        user_id_header=user_id_header,
    )


# ── Public templates (no user data) ─────────────────────────────────────────


def _sanitize_template(t: dict[str, Any]) -> dict[str, Any]:
    """Return only public-safe fields from a meal template."""
    return {
        "template_id": t.get("template_id", ""),
        "name": t.get("name", ""),
        "description": t.get("description", ""),
        "category": t.get("category", ""),
        "meal_type": t.get("meal_type", "") or t.get("category", ""),
        "cuisine": t.get("cuisine", ""),
        "difficulty": t.get("difficulty", ""),
        "nutrition": t.get("nutrition", {}),
        "ingredients": t.get("ingredients", []),
        "instructions": t.get("instructions", []),
        "tags": t.get("tags", ""),
        "dietary": t.get("dietary", []),
        "preparation_time": t.get("preparation_time"),
        "cooking_time": t.get("cooking_time"),
        "total_time": t.get("total_time"),
        "servings": t.get("servings"),
        "image_url": t.get("image_url", ""),
        "popularity_rank": t.get("popularity_rank"),
        "source": t.get("source", ""),
        "health_score": t.get("health_score"),
    }


async def get_meal_templates(
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
    client_id_header: Optional[str] = None,
    client_secret_header: Optional[str] = None,
) -> dict[str, Any]:
    """Fetch public meal templates from user.wihy.ai — strips all user data."""
    url = f"{USER_SERVICE_DIRECT_URL}/api/meals/templates"
    headers = _build_headers(
        authorization_header=None,
        client_id_header=client_id_header,
        client_secret_header=client_secret_header,
    )
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if category:
        params["category"] = category

    try:
        async with httpx.AsyncClient(timeout=LABAT_TRENDING_PROXY_TIMEOUT) as client:
            resp = await client.get(url, params=params, headers=headers)
    except httpx.TimeoutException as e:
        logger.error("Meal templates fetch timeout: %s", e)
        raise HTTPException(status_code=504, detail="Meal templates upstream timeout")
    except httpx.RequestError as e:
        logger.error("Meal templates request error: %s", e)
        raise HTTPException(status_code=502, detail="Meal templates upstream unavailable")

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail="Meal templates upstream error")

    try:
        payload = resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Invalid JSON from meal templates upstream")

    templates = _coerce_list(payload.get("templates"))
    sanitized = [_sanitize_template(t) for t in templates]

    return {
        "success": True,
        "templates": sanitized,
        "count": len(sanitized),
        "total": payload.get("total", len(sanitized)),
        "offset": offset,
    }
