"""
Auth client for WIHY ML backend.

Verifies JWT tokens by calling POST https://auth.wihy.ai/api/auth/verify.
Returns the full user object including capabilities, dietaryPreferences,
healthGoals, plan, etc.

NO local in-memory caching — the auth service has its own Redis cache with a
15-minute TTL, so every verify call is fast.  Keeping a local cache would
consume unbounded memory on Cloud Run workers.

Usage
-----
from src.auth.auth_client import verify_token, get_user_from_request

# From a FastAPI dependency:
user = await verify_token(jwt_token)
# user["id"], user["capabilities"], user["dietaryPreferences"], etc.

# From a route handler that has a Request object:
user = await get_user_from_request(request)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

AUTH_URL = os.getenv("AUTH_SERVICE_URL", "https://auth.wihy.ai")
_VERIFY_URL = f"{AUTH_URL}/api/auth/verify"
_TIMEOUT = 5.0          # seconds — auth must be fast
_HTTP_TIMEOUT = httpx.Timeout(_TIMEOUT)


# ── Public API ────────────────────────────────────────────────────────────────

async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token with auth.wihy.ai.

    Returns the full `user` object on success (see spec), or None if the token
    is invalid/expired.  Raises no exceptions — network failures return None
    so requests can gracefully degrade to anonymous.

    The returned dict includes (among others):
        id, email, name, role, plan, status,
        capabilities, dietaryPreferences, healthGoals,
        height, weight, activityLevel, apps, addOns, ...
    """
    if not token or len(token) < 20:
        return None

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.post(
                _VERIFY_URL,
                json={"token": token},
                headers={"Content-Type": "application/json"},
            )
        data = resp.json()
    except Exception as exc:
        logger.warning("auth.wihy.ai verify failed (network): %s", exc)
        return None

    if not data.get("valid") or not data.get("success"):
        logger.debug("Token invalid: %s", data.get("error"))
        return None

    user = data.get("user")
    if not user or not user.get("id"):
        logger.warning("Auth verify response missing user object")
        return None

    # Normalise a few fields so the rest of the app can rely on them
    user.setdefault("isAuthenticated", True)
    user.setdefault("isAnonymous", False)
    user.setdefault("sessionId", data.get("sessionId"))

    logger.debug("Auth verified user=%s plan=%s", user["id"], user.get("plan"))
    return user


async def get_user_from_request(request: Any) -> Optional[Dict[str, Any]]:
    """
    Extract the Bearer token from a FastAPI Request (header or cookie) and
    verify it.  Returns None if unauthenticated.
    """
    token = _extract_token(request)
    if not token:
        return None
    return await verify_token(token)


def _extract_token(request: Any) -> Optional[str]:
    """Pull Bearer token from Authorization header or session_token cookie."""
    # Authorization: Bearer <token>
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()

    # Cookie fallback (web users)
    if hasattr(request, "cookies"):
        tok = request.cookies.get("session_token")
        if tok:
            return tok.strip()

    return None


# ── Helpers used throughout the app ──────────────────────────────────────────

def user_can_access_meal_plans(user: Dict[str, Any]) -> bool:
    """Return True if user's capabilities allow meal plan generation."""
    caps = user.get("capabilities") or {}
    return caps.get("canAccessMealPlans", False)


def user_dietary_prefs(user: Dict[str, Any]) -> list:
    """Return list of dietary preference strings."""
    return user.get("dietaryPreferences") or []


def user_health_goals(user: Dict[str, Any]) -> list:
    """Return list of health goal strings."""
    return user.get("healthGoals") or []


def build_health_context(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a health context dict suitable for passing to MealAIRequest.health_context
    and similar fields, populated from the verified user object.
    """
    return {
        "dietary_preferences": user_dietary_prefs(user),
        "health_goals": user_health_goals(user),
        "height": user.get("height"),
        "weight": user.get("weight"),
        "activity_level": user.get("activityLevel"),
        "gender": user.get("gender"),
        "age": _age_from_dob(user.get("dateOfBirth")),
        "plan": user.get("plan"),
        "capabilities": user.get("capabilities") or {},
    }


def _age_from_dob(dob: Optional[str]) -> Optional[int]:
    if not dob:
        return None
    try:
        from datetime import date
        born = date.fromisoformat(dob[:10])
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except Exception:
        return None
