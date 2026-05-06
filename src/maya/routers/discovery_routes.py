"""
maya/routers/discovery_routes.py — Audience discovery, collaborator management, and auto-engage endpoints.

Auth: X-Admin-Token header (INTERNAL_ADMIN_TOKEN)

Endpoints:
  POST /api/engagement/discover                 — trigger audience discovery cycle
  GET  /api/engagement/discover/preview         — dry-run: show who would be found for a hashtag
  POST /api/engagement/collaborators/find       — trigger collaborator search cycle
  GET  /api/engagement/collaborators            — list top collaborator candidates from Firestore
  POST /api/engagement/auto-engage/run          — trigger one auto-engage cycle
  GET  /api/engagement/auto-engage/status       — show daily follow/like counters and limits
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request

logger = logging.getLogger("discovery_routes")

ADMIN_TOKEN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()
router = APIRouter(prefix="/api/engagement", tags=["discovery"])


def _require_admin(request: Request) -> None:
    token = (request.headers.get("X-Admin-Token") or "").strip()
    if ADMIN_TOKEN and token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Audience Discovery ────────────────────────────────────────────────────────

@router.post("/discover")
async def trigger_discovery(
    brand: str = Query("all", description="Brand to scan: all | wihy | vowels | communitygroceries | childrennutrition"),
    _: None = Depends(_require_admin),
):
    """Run one audience discovery cycle and store new users in Firestore."""
    from src.maya.services.audience_discovery_service import run_once
    return await run_once(brand=brand)


@router.get("/discover/preview")
async def preview_discovery(
    hashtag: str = Query("nutrition", description="Hashtag to search (no # prefix)"),
    brand: str = Query("wihy"),
    _: None = Depends(_require_admin),
):
    """Dry-run: show Twitter users who would be discovered for a hashtag, without storing."""
    import httpx
    from src.maya.services.audience_discovery_service import _search_twitter_hashtag, _score_user

    async with httpx.AsyncClient() as client:
        users = await _search_twitter_hashtag(client, hashtag, max_results=10)

    results = []
    for u in users:
        m = u.get("public_metrics", {})
        score = _score_user(
            m.get("followers_count", 0),
            m.get("following_count", 0),
            m.get("listed_count", 0),
            u.get("verified", False),
        )
        results.append({
            "username": u.get("username"),
            "name": u.get("name"),
            "followers": m.get("followers_count", 0),
            "description": (u.get("description") or "")[:120],
            "score": score,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"hashtag": hashtag, "brand": brand, "preview": results}


# ── Collaborator Finder ───────────────────────────────────────────────────────

@router.post("/collaborators/find")
async def trigger_collaborator_search(
    brand: str = Query("all", description="Brand to search for: all | wihy | vowels | communitygroceries | childrennutrition"),
    _: None = Depends(_require_admin),
):
    """Run one collaborator discovery cycle and store candidates in Firestore."""
    from src.maya.services.collaborator_finder_service import run_once
    return await run_once(brand=brand)


@router.get("/collaborators")
async def list_collaborators(
    brand: str = Query("all"),
    limit: int = Query(20, le=100),
    _: None = Depends(_require_admin),
):
    """List top-scored collaborator candidates from Firestore."""
    from google.cloud import firestore
    db = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))

    all_brands = ["wihy", "vowels", "communitygroceries", "childrennutrition"]
    brands = all_brands if brand == "all" else [brand]
    candidates = []

    for b in brands:
        docs = await (
            db.collection("collaborators")
            .document(b)
            .collection("candidates")
            .order_by("score", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .get()
        )
        for doc in docs:
            candidates.append(doc.to_dict())

    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    return {"total": len(candidates), "candidates": candidates[:limit]}


# ── Auto-Engage ───────────────────────────────────────────────────────────────

@router.post("/auto-engage/run")
async def trigger_auto_engage(_: None = Depends(_require_admin)):
    """Run one auto-engage cycle: like and follow top unengaged users from Firestore."""
    from src.maya.services.auto_engage_service import run_once
    return await run_once()


@router.get("/auto-engage/status")
async def auto_engage_status(_: None = Depends(_require_admin)):
    """Return today's follow/like counts and remaining budget."""
    from src.maya.services.auto_engage_service import daily_status
    return daily_status()
