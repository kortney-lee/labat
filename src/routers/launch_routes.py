"""
Launch API Routes
POST /api/launch/signup         — Capture email + name for pre-launch
POST /api/launch/nurture-cron   — Process pending drip emails (Cloud Scheduler)
GET  /api/launch/stats          — Signup counts by brand
POST /api/launch/sendgrid-webhook — SendGrid event tracking
"""

import hashlib
import logging
import os
import time

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

from src.services.launch_leads_service import (
    save_lead, email_exists, mark_unsubscribed, record_email_event, get_stats,
)

logger = logging.getLogger(__name__)

ADMIN_TOKEN = os.getenv("INTERNAL_ADMIN_TOKEN", "wihy-admin-token-2026")

router = APIRouter(prefix="/api/launch", tags=["Launch"])


# ── Schemas ───────────────────────────────────────────────────────────────

class LaunchSignupRequest(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    brand: str = "wihy"  # "wihy" or "communitygroceries"
    utm_source: str = ""
    utm_campaign: str = ""
    utm_medium: str = ""
    fbclid: str = ""


class LaunchSignupResponse(BaseModel):
    success: bool
    message: str


# ── Routes ────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=LaunchSignupResponse)
async def launch_signup(req: LaunchSignupRequest):
    """Capture an email for pre-launch updates."""
    email = req.email.lower().strip()
    brand = req.brand.lower().strip()

    if brand not in ("wihy", "communitygroceries"):
        raise HTTPException(status_code=400, detail="Invalid brand. Use 'wihy' or 'communitygroceries'.")

    # Duplicate check
    if await email_exists(email, brand):
        return LaunchSignupResponse(success=True, message="You're already on the list!")

    first_name = req.first_name.strip()
    last_name = req.last_name.strip()

    await save_lead(
        email=email,
        first_name=first_name,
        last_name=last_name,
        brand=brand,
        utm_source=req.utm_source,
        utm_campaign=req.utm_campaign,
        utm_medium=req.utm_medium,
        fbclid=req.fbclid,
    )

    # Send welcome email immediately — best-effort
    try:
        from src.services.launch_nurture_service import trigger_welcome
        await trigger_welcome(email, first_name, brand)
    except Exception as e:
        logger.error("Launch welcome email failed (non-blocking): %s", e)

    # Forward Lead event to LABAT (Meta CAPI) — best-effort
    try:
        from src.labat.services.conversions_service import send_single_event, hash_pii
        brand_name = "WIHY" if brand == "wihy" else "Community Groceries"
        source_url = "https://wihy.ai/" if brand == "wihy" else "https://communitygroceries.com/"
        await send_single_event(
            event_name="Lead",
            user_data={"em": [hash_pii(email)]},
            custom_data={"content_name": f"{brand_name} Pre-Launch Signup"},
            event_source_url=source_url,
            event_id=f"launch-{hashlib.md5(email.encode()).hexdigest()[:12]}-{int(time.time())}",
        )
    except Exception as e:
        logger.warning("CAPI Lead event failed (non-blocking): %s", e)

    return LaunchSignupResponse(success=True, message="You're in! We'll let you know when we launch.")


@router.post("/nurture-cron")
async def nurture_cron(request: Request):
    """Process pending launch nurture emails. Protected by admin token."""
    token = request.headers.get("X-Admin-Token", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from src.services.launch_nurture_service import process_pending_launch_nurture
    sent = await process_pending_launch_nurture()
    return {"processed": sent}


@router.post("/preview-all")
async def preview_all(request: Request):
    """Admin: send every launch nurture template to an address for review."""
    token = request.headers.get("X-Admin-Token", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    to_email = body.get("email", "").strip().lower()
    first_name = body.get("first_name", "Kortney")
    brand = body.get("brand", "wihy").strip().lower()

    if not to_email:
        raise HTTPException(status_code=400, detail="email required")
    if brand not in ("wihy", "communitygroceries"):
        raise HTTPException(
            status_code=400,
            detail="Invalid brand. Use 'wihy' or 'communitygroceries'.",
        )

    from src.services.launch_nurture_service import send_launch_email, LAUNCH_SEQUENCE

    results = {}
    for _stage, days, template_id, subject in LAUNCH_SEQUENCE:
        preview_subject = f"[PREVIEW Day {days}] {subject}"
        sent = await send_launch_email(
            to_email=to_email,
            first_name=first_name,
            template_id=template_id,
            subject=preview_subject,
            brand=brand,
        )
        results[template_id] = sent

    return {
        "status": "ok",
        "sent_to": to_email,
        "brand": brand,
        "results": results,
    }


@router.post("/preview-local")
async def preview_local(request: Request):
    """Admin: render launch templates locally for visual QA (no email send)."""
    token = request.headers.get("X-Admin-Token", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    first_name = str(body.get("first_name", "Kortney")).strip() or "Kortney"
    output_dir = str(body.get("output_dir", "local_previews/launch_templates")).strip()
    keep_active_only = bool(body.get("keep_active_only", False))

    brands_raw = body.get("brands", ["wihy", "communitygroceries"])
    if not isinstance(brands_raw, list):
        raise HTTPException(status_code=400, detail="brands must be a list")

    brands = [str(b).strip().lower() for b in brands_raw if str(b).strip()]
    allowed = {"wihy", "communitygroceries"}
    invalid = [b for b in brands if b not in allowed]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid brand(s): {', '.join(invalid)}. Use 'wihy' or 'communitygroceries'.",
        )

    from src.services.launch_nurture_service import export_launch_templates_local

    files = export_launch_templates_local(
        output_dir=output_dir,
        first_name=first_name,
        brands=brands,
        keep_active_only=keep_active_only,
    )

    return {
        "status": "ok",
        "mode": "active_only" if keep_active_only else "all_templates",
        "output_dir": output_dir,
        "brands": brands,
        "files": files,
    }


@router.get("/stats")
async def launch_stats(request: Request):
    """Return signup stats by brand. Admin only."""
    token = request.headers.get("X-Admin-Token", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return await get_stats()


@router.post("/sendgrid-webhook")
async def sendgrid_webhook(request: Request):
    """Receive SendGrid open/click/unsubscribe events for launch emails."""
    try:
        events = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    for event in events if isinstance(events, list) else [events]:
        email = event.get("email", "")
        event_type = event.get("event", "")
        if not email:
            continue

        if event_type in ("group_unsubscribe", "unsubscribe"):
            try:
                await mark_unsubscribed(email)
            except Exception as e:
                logger.warning("Failed to mark unsubscribed: %s", e)
        else:
            try:
                await record_email_event(email, event_type)
            except Exception as e:
                logger.warning("Failed to record launch email event: %s", e)

    return {"status": "ok"}
