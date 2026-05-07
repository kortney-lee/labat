"""
Book API Routes
POST /api/book/leads          — Capture email, send book
POST /api/book/checkout        — Create Stripe checkout session
POST /api/book/stripe-webhook  — Stripe webhook (purchase events)
GET  /api/book/stats           — Lead count (internal)
"""

import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone

import httpx

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr

from src.services.book_leads_service import (
    save_lead, email_exists, mark_purchased, mark_unsubscribed,
    record_email_event, get_funnel_stats, get_lead_data,
)
from src.services.book_stripe_service import create_checkout_session

logger = logging.getLogger(__name__)

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

router = APIRouter(prefix="/api/book", tags=["Book"])

META_PIXEL_ID = os.getenv("META_PIXEL_ID", "")


# ── Schemas ───────────────────────────────────────────────────────────────

class LeadRequest(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    source: str = ""
    utm_source: str = ""
    utm_campaign: str = ""
    utm_content: str = ""    # should be variant name: weight|kids|energy|groceries|etc.
    utm_medium: str = ""
    fbclid: str = ""
    referral_url: str = ""   # article/page they came from


class NewsletterSignupRequest(BaseModel):
    """Vowels.org newsletter subscriber."""
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    topic: str = "general"      # health topic: weight|kids|energy|groceries|general|etc.
    referral_url: str = ""      # article URL that drove the signup
    utm_source: str = ""
    utm_campaign: str = ""
    utm_medium: str = ""


class B2BLeadRequest(BaseModel):
    """Business lead — bookstore, library, podcast, blog, etc."""
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    company_name: str = ""
    business_type: str = "other"   # bookstore|library|podcast|blog|church|school|other
    message: str = ""              # what they asked about / why they're reaching out
    utm_source: str = ""
    utm_medium: str = ""


class LeadResponse(BaseModel):
    success: bool
    message: str


class CheckoutRequest(BaseModel):
    product: str = "hardcover"
    email: str | None = None


class CheckoutResponse(BaseModel):
    url: str
    session_id: str


# ── Routes ────────────────────────────────────────────────────────────────

@router.get("/pixel-config")
async def pixel_config():
    """Return Meta Pixel ID for client-side initialization."""
    return {"pixel_id": META_PIXEL_ID or None}


@router.post("/leads", response_model=LeadResponse)
async def capture_lead(req: LeadRequest):
    """Capture an email lead and send the free book."""
    email = req.email.lower().strip()

    # Check for duplicate
    already = await email_exists(email)
    if already:
        return LeadResponse(success=True, message="You're already signed up! Check your download page.")

    # Save lead
    first_name = req.first_name.strip()
    last_name = req.last_name.strip()
    raw_source = (req.source or req.utm_source or "").strip().lower()
    if "communitygroceries" in raw_source:
        lead_source = "communitygroceries"
    elif "wihy" in raw_source:
        lead_source = "wihy"
    elif "whatishealthy" in raw_source:
        lead_source = "whatishealthy"
    else:
        lead_source = raw_source or "whatishealthy"
    # Resolve topic: utm_content should be variant name (weight/kids/energy/etc.)
    # If it's a generic ad group name, classify_lead will fall back to "general"
    from src.services.book_leads_service import VALID_TOPICS
    raw_topic = req.utm_content.strip().lower()
    lead_topic = raw_topic if raw_topic in VALID_TOPICS else "general"

    await save_lead(
        email, source=lead_source, first_name=first_name, last_name=last_name,
        utm_source=req.utm_source, utm_campaign=req.utm_campaign,
        utm_content=req.utm_content, utm_medium=req.utm_medium,
        fbclid=req.fbclid, lead_topic=lead_topic,
        referral_url=req.referral_url,
    )

    # Trigger Day 0 nurture email — best-effort
    try:
        from src.services.nurture_service import trigger_day0
        await trigger_day0(email, first_name, variant=lead_topic)
    except Exception as e:
        logger.error(f"Nurture Day 0 trigger failed (non-blocking): {e}")

    # Forward Lead event to LABAT (Meta CAPI) — best-effort
    try:
        from src.labat.services.conversions_service import send_single_event, hash_pii
        await send_single_event(
            event_name="Lead",
            user_data={"em": [hash_pii(email)]},
            custom_data={"content_name": "What Is Healthy? Free eBook"},
            event_source_url="https://whatishealthy.org/",
            event_id=f"lead-{hashlib.md5(email.encode()).hexdigest()[:12]}-{int(time.time())}",
        )
    except Exception as e:
        logger.warning(f"CAPI Lead event failed (non-blocking): {e}")

    return LeadResponse(success=True, message="Your free copy is ready!")


# ── Vowels Newsletter Signup ──────────────────────────────────────────────────

@router.post("/newsletter-signup", response_model=LeadResponse)
async def vowels_newsletter_signup(req: NewsletterSignupRequest):
    """
    Vowels.org newsletter subscriber signup.
    topic field drives which sequence they receive (weight|kids|energy|general|etc.)
    referral_url captures which article brought them here.
    """
    email = req.email.lower().strip()
    already = await email_exists(email)
    if already:
        return LeadResponse(success=True, message="You're already subscribed!")

    topic = req.topic.strip().lower()
    from src.services.book_leads_service import VALID_TOPICS
    if topic not in VALID_TOPICS:
        topic = "general"

    await save_lead(
        email,
        source="vowels-newsletter",
        first_name=req.first_name.strip(),
        last_name=req.last_name.strip(),
        utm_source=req.utm_source,
        utm_campaign=req.utm_campaign,
        utm_medium=req.utm_medium,
        lead_topic=topic,
        referral_url=req.referral_url,
    )

    try:
        from src.services.nurture_service import trigger_day0
        await trigger_day0(email, req.first_name.strip(), variant=topic)
    except Exception as e:
        logger.error(f"Newsletter nurture Day 0 failed (non-blocking): {e}")

    return LeadResponse(success=True, message="Welcome to Vowels!")


# ── B2B Lead Intake ───────────────────────────────────────────────────────────

@router.post("/b2b-lead", response_model=LeadResponse)
async def b2b_lead(req: B2BLeadRequest):
    """
    B2B lead intake — bookstore, library, podcast, blog, church, school.
    Triggers a separate B2B nurture sequence, not the consumer book sequence.
    """
    email = req.email.lower().strip()
    already = await email_exists(email)
    if already:
        return LeadResponse(success=True, message="We already have your info — we'll be in touch!")

    btype = req.business_type.strip().lower()
    from src.services.book_leads_service import B2B_TYPES
    if btype not in B2B_TYPES:
        btype = "other"

    await save_lead(
        email,
        source="b2b-intake",
        first_name=req.first_name.strip(),
        last_name=req.last_name.strip(),
        utm_source=req.utm_source,
        utm_medium=req.utm_medium,
        business_type=btype,
        company_name=req.company_name.strip(),
        message=req.message.strip()[:1000],
    )

    # Trigger B2B Day 0 email
    try:
        from src.services.b2b_nurture_service import trigger_b2b_day0
        await trigger_b2b_day0(email, req.first_name.strip(), btype, req.company_name.strip())
    except Exception as e:
        logger.error(f"B2B nurture Day 0 failed (non-blocking): {e}")

    return LeadResponse(success=True, message="Thanks — we'll be in touch within 24 hours!")


class VerifyEmailRequest(BaseModel):
    email: EmailStr


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest):
    """Check if an email is a confirmed lead. Used by confirm-download page."""
    email = req.email.lower().strip()
    found = await email_exists(email)
    if not found:
        raise HTTPException(status_code=404, detail="Email not found")
    lead = await get_lead_data(email)
    first_name = (lead or {}).get("first_name", "") if lead else ""
    return {"verified": True, "first_name": first_name}


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(req: CheckoutRequest):
    """Create a Stripe Checkout Session for the hardcover book."""
    try:
        session = await create_checkout_session(email=req.email)
        return CheckoutResponse(**session)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events for purchase tracking."""
    import stripe
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning(f"Webhook signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Stripe uses dot-separated event names (e.g., checkout.session.completed).
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = getattr(session, "customer_email", None)
        if not email:
            customer_details = getattr(session, "customer_details", None)
            if customer_details:
                if isinstance(customer_details, dict):
                    email = customer_details.get("email")
                else:
                    email = getattr(customer_details, "email", None)

        cover_type = "unknown"
        try:
            metadata = getattr(session, "metadata", None)
            if isinstance(metadata, dict):
                cover_type = metadata.get("cover_type", "unknown")
            elif metadata is not None:
                cover_type = metadata["cover_type"] if "cover_type" in metadata else "unknown"
        except Exception:
            cover_type = "unknown"

        amount = getattr(session, "amount_total", 0) or 0

        logger.info(f"Purchase completed: email={email}, cover={cover_type}, amount={amount}")

        if email:
            await mark_purchased(email)

        # Forward Purchase event to LABAT (Meta CAPI) — best-effort
        try:
            from src.labat.services.conversions_service import send_single_event, hash_pii
            user_data = {}
            if email:
                user_data["em"] = [hash_pii(email)]
                # Fetch lead record for fbclid and names
                lead = await get_lead_data(email)
                if lead:
                    fn = lead.get("first_name", "")
                    ln = lead.get("last_name", "")
                    fbclid = lead.get("fbclid", "")
                    if fn:
                        user_data["fn"] = [hash_pii(fn)]
                    if ln:
                        user_data["ln"] = [hash_pii(ln)]
                    if fbclid:
                        user_data["fbc"] = f"fb.1.{int(time.time())}.{fbclid}"
            await send_single_event(
                event_name="Purchase",
                user_data=user_data,
                custom_data={
                    "currency": "USD",
                    "value": amount / 100 if amount else 24.99,
                    "content_name": f"What Is Healthy? Physical Copy ({cover_type})",
                    "content_type": "product",
                },
                event_source_url="https://whatishealthy.org/thank-you.html",
                event_id=event["id"],
            )
            logger.info("CAPI Purchase event sent for %s", email)
        except Exception as e:
            logger.warning(f"CAPI event forwarding failed (non-blocking): {e}")

    else:
        logger.info("Unhandled Stripe event type: %s", event.get("type"))

    return {"status": "ok"}


# ── OTO Conversion Tracking ──────────────────────────────────────────────

_ALLOWED_OTO_EVENTS = {"ViewContent", "InitiateCheckout", "Lead"}


class TrackRequest(BaseModel):
    event_name: str
    content_name: str = "OTO Page"
    value: float | None = None
    currency: str = "USD"
    email: str = ""


@router.post("/track")
async def track_oto_event(req: TrackRequest):
    """Fire a server-side CAPI event for OTO funnel tracking."""
    if req.event_name not in _ALLOWED_OTO_EVENTS:
        raise HTTPException(status_code=400, detail="Invalid event name")

    custom_data: dict = {"content_name": req.content_name}
    if req.value is not None:
        custom_data["value"] = req.value
        custom_data["currency"] = req.currency

    try:
        from src.labat.services.conversions_service import send_single_event, hash_pii
        user_data = {}
        email = req.email.strip().lower()
        if email:
            user_data["em"] = [hash_pii(email)]
            lead = await get_lead_data(email)
            if lead:
                fn = lead.get("first_name", "")
                ln = lead.get("last_name", "")
                fbclid = lead.get("fbclid", "")
                if fn:
                    user_data["fn"] = [hash_pii(fn)]
                if ln:
                    user_data["ln"] = [hash_pii(ln)]
                if fbclid:
                    user_data["fbc"] = f"fb.1.{int(time.time())}.{fbclid}"
        await send_single_event(
            event_name=req.event_name,
            user_data=user_data,
            custom_data=custom_data,
            event_source_url="https://whatishealthy.org/oto.html",
            event_id=f"oto-{req.event_name.lower()}-{int(time.time())}",
        )
        logger.info("CAPI OTO event sent: %s", req.event_name)
    except Exception as e:
        logger.warning(f"CAPI OTO event failed (non-blocking): {e}")

    return {"status": "ok", "event": req.event_name}


@router.get("/stats")
async def stats(request: Request):
    """Lead count and funnel stats — internal use only."""
    admin_token = os.getenv("INTERNAL_ADMIN_TOKEN", "")
    req_token = request.headers.get("x-admin-token", "")
    detailed = req_token and (not admin_token or req_token == admin_token)
    if detailed:
        return await get_funnel_stats()
    from src.services.book_leads_service import get_lead_count
    count = await get_lead_count()
    return {"leads": count}


@router.post("/nurture-cron")
async def nurture_cron(request: Request):
    """Process pending nurture emails. Called by Cloud Scheduler."""
    admin_token = os.getenv("INTERNAL_ADMIN_TOKEN", "")
    req_token = request.headers.get("x-admin-token", "")
    if admin_token and req_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from src.services.nurture_service import process_pending_nurture
    from src.services.b2b_nurture_service import process_pending_b2b_nurture, process_outreach_leads
    consumer_result  = await process_pending_nurture()
    b2b_result       = await process_pending_b2b_nurture()
    outreach_result  = await process_outreach_leads(batch=100)
    return {"status": "ok", "consumer": consumer_result, "b2b": b2b_result, "outreach": outreach_result}


@router.post("/preview-all")
async def preview_all(request: Request):
    """Admin: send all 7 nurture emails to a given address for review."""
    admin_token = os.getenv("INTERNAL_ADMIN_TOKEN", "")
    req_token = request.headers.get("x-admin-token", "")
    if admin_token and req_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    to_email = body.get("email", "").strip().lower()
    first_name = body.get("first_name", "Kortney")
    variant = body.get("variant", "weight")
    if not to_email:
        raise HTTPException(status_code=400, detail="email required")

    from src.services.nurture_service import send_nurture_email, NURTURE_SEQUENCE
    results = {}
    for stage, days, template_id, subject in NURTURE_SEQUENCE:
        preview_subject = f"[PREVIEW Day {days}] {subject}"
        sent = await send_nurture_email(to_email, first_name, template_id, preview_subject, variant=variant)
        results[template_id] = sent

    return {"status": "ok", "sent_to": to_email, "results": results}


# ── B2B Preview (test emails, no DB write) ────────────────────────────────────

_B2B_TYPES_ALL = ["bookstore", "library", "podcast", "blog", "church", "school"]


@router.post("/admin/preview-b2b")
async def preview_b2b(request: Request):
    """
    Admin: send Day 0 B2B test emails for all business types (or a subset)
    to a specified address. No lead is saved to the database.

    Body (JSON):
      { "to_email": "you@example.com",
        "first_name": "Kortney",
        "company_name": "Test Co",
        "types": ["bookstore","podcast"]   // optional — omit for all 6
      }
    """
    admin_token = os.getenv("INTERNAL_ADMIN_TOKEN", "")
    req_token = request.headers.get("x-admin-token", "")
    if admin_token and req_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.json()
    to_email = body.get("to_email", "").strip()
    first_name = body.get("first_name", "Kortney").strip()
    company_name = body.get("company_name", "").strip()
    types = body.get("types") or _B2B_TYPES_ALL

    if not to_email:
        raise HTTPException(status_code=400, detail="to_email required")

    from src.services.b2b_nurture_service import _render_b2b_day0, _get, _send

    results = []
    for bt in types:
        subject = _get(bt)["d0_subject"]
        html = _render_b2b_day0(first_name, bt, company_name)
        sent = await _send(to_email, f"[{bt.upper()} TEST] {subject}", html)
        results.append({"type": bt, "subject": subject, "sent": sent})

    return {"to": to_email, "sent": len([r for r in results if r["sent"]]), "results": results}


# ── Unsubscribe ───────────────────────────────────────────────────────────

class ResendRequest(BaseModel):
    email: EmailStr


@router.post("/resend")
async def resend_day0(req: ResendRequest, request: Request):
    """Admin: reset a lead to stage 0 and re-send the Day 0 email."""
    admin_token = os.getenv("INTERNAL_ADMIN_TOKEN", "")
    req_token = request.headers.get("x-admin-token", "")
    if admin_token and req_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    email = req.email.lower().strip()
    exists = await email_exists(email)
    if not exists:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Reset nurture state and re-trigger Day 0
    from src.services.book_leads_service import _get_firestore, COLLECTION
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email).limit(1)
    first_name = ""
    async for doc in query.stream():
        data = doc.to_dict()
        first_name = data.get("first_name", "")
        now = datetime.now(timezone.utc)
        await doc.reference.update({
            "sequence_status": "active",
            "nurture_stage": 0,
            "nurture_next_at": now,
        })
        break

    from src.services.nurture_service import trigger_day0
    sent = await trigger_day0(email, first_name)
    return {"status": "ok", "email": email, "sent": sent}


class UnsubscribeRequest(BaseModel):
    email: EmailStr


# ── B2B Admin Seeding ─────────────────────────────────────────────────────────

class B2BSeedEntry(BaseModel):
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    company_name: str = ""
    business_type: str = "other"
    message: str = ""


class B2BSeedRequest(BaseModel):
    leads: list[B2BSeedEntry]


@router.post("/admin/seed-b2b")
async def seed_b2b_leads(req: B2BSeedRequest, request: Request):
    """
    Admin: bulk-add B2B leads and trigger Day 0 email for each.
    Skips duplicates already in the system.
    """
    admin_token = os.getenv("INTERNAL_ADMIN_TOKEN", "")
    req_token = request.headers.get("x-admin-token", "")
    if admin_token and req_token != admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    from src.services.book_leads_service import save_lead
    from src.services.b2b_nurture_service import trigger_b2b_day0

    results = []
    for entry in req.leads:
        email = entry.email.lower().strip()
        already = await email_exists(email)
        if already:
            results.append({"email": email, "status": "duplicate"})
            continue

        btype = (entry.business_type or "other").strip().lower()
        try:
            await save_lead(
                email=email,
                source="b2b_admin_seed",
                first_name=entry.first_name.strip(),
                last_name=entry.last_name.strip(),
                business_type=btype,
                company_name=entry.company_name.strip(),
                message=entry.message.strip(),
            )
            sent = await trigger_b2b_day0(email, entry.first_name.strip(), btype, entry.company_name.strip())
            results.append({"email": email, "status": "added", "day0_sent": sent})
            logger.info("B2B seed: added %s (%s / %s)", email, btype, entry.company_name)
        except Exception as e:
            logger.error("B2B seed error for %s: %s", email, e)
            results.append({"email": email, "status": "error", "detail": str(e)})

    added = sum(1 for r in results if r["status"] == "added")
    skipped = sum(1 for r in results if r["status"] == "duplicate")
    errors = sum(1 for r in results if r["status"] == "error")
    return {"added": added, "skipped": skipped, "errors": errors, "results": results}


@router.post("/unsubscribe")
async def unsubscribe(req: UnsubscribeRequest):
    """Unsubscribe an email from the nurture sequence."""
    found = await mark_unsubscribed(req.email)
    if not found:
        return {"status": "ok", "message": "If that email exists, it has been unsubscribed."}
    return {"status": "ok", "message": "You've been unsubscribed. You won't receive any more emails from us."}


# ── Meta Leadgen Webhook ──────────────────────────────────────────────────

# Map ad IDs to landing page variants for dynamic email content
_AD_ID_TO_VARIANT = {
    # v6 ads (April 2026 qualifying campaign)
    "120243540924860504": "warning",
    "120243540927410504": "realfood",
    "120243540928380504": "eliminate",
    "120243540929820504": "biglie",
    "120243540930560504": "mistakes",
    "120243540931890504": "finally",
    # v7 ads
    "120243541063060504": "weight",
    "120243541067250504": "kids",
    "120243541072430504": "energy",
    "120243541078410504": "groceries",
    "120243541083780504": "family",
    "120243541087720504": "confused",
    # April 2026 qualifying campaign — new ad IDs (generic, no variant differentiation)
    # TODO: split into variant-specific ad sets and add IDs here
    "120243541002540504": "general",
    "120243541005360504": "general",
}
# NOTE: For proper variant segmentation on web-form leads (not Meta native forms),
# Facebook ads must include utm_content=weight|kids|energy|groceries|family|confused
# in their tracking URL template. Current campaign uses generic ad group names.

META_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN", "")


async def _retrieve_meta_lead(leadgen_id: str) -> dict:
    """Retrieve lead field data from Meta Lead Retrieval API."""
    if not META_TOKEN:
        logger.error("META_SYSTEM_USER_TOKEN not set — cannot retrieve lead")
        return {}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://graph.facebook.com/v21.0/{leadgen_id}",
            params={"access_token": META_TOKEN},
        )
        if resp.status_code != 200:
            logger.error(f"Meta lead retrieval failed: {resp.status_code} {resp.text}")
            return {}
        data = resp.json()
        result = {}
        for field in data.get("field_data", []):
            name = field.get("name", "")
            values = field.get("values", [])
            if values:
                result[name] = values[0]
        return result


@router.get("/meta-lead-webhook")
async def meta_webhook_verify(request: Request):
    """Meta webhook verification (hub.challenge handshake)."""
    mode = request.query_params.get("hub.mode", "")
    token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")
    verify_token = os.getenv("META_WEBHOOK_VERIFY_TOKEN", os.getenv("INTERNAL_ADMIN_TOKEN", ""))
    if mode == "subscribe" and token and token == verify_token:
        logger.info("Meta webhook verified")
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/meta-lead-webhook")
async def meta_webhook_event(request: Request):
    """Receive Meta leadgen webhook events — sync FB leads to Firestore."""
    import httpx as _httpx  # noqa: already imported at module level
    body = await request.json()
    entries = body.get("entry", [])
    processed = 0

    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            if change.get("field") != "leadgen":
                continue
            value = change.get("value", {})
            leadgen_id = value.get("leadgen_id")
            ad_id = str(value.get("ad_id", ""))
            if not leadgen_id:
                continue

            # Retrieve lead data from Meta
            lead_data = await _retrieve_meta_lead(str(leadgen_id))
            if not lead_data:
                logger.warning(f"Could not retrieve Meta lead {leadgen_id}")
                continue

            email = lead_data.get("email", "").lower().strip()
            first_name = lead_data.get("first_name", lead_data.get("full_name", "").split()[0] if lead_data.get("full_name") else "")
            if not email:
                continue

            # Check duplicate
            if await email_exists(email):
                continue

            # Map ad_id to variant
            variant = _AD_ID_TO_VARIANT.get(ad_id, "")

            # Save lead
            await save_lead(
                email=email, source="facebook_lead_form",
                first_name=first_name,
                utm_source="facebook", utm_medium="paid",
                utm_campaign="vowels_book", utm_content=variant,
            )

            # Trigger Day 0 nurture
            try:
                from src.services.nurture_service import trigger_day0
                await trigger_day0(email, first_name, variant=variant)
            except Exception as e:
                logger.error(f"Meta lead nurture Day 0 failed: {e}")

            # Forward Lead event to LABAT (Meta CAPI) — best-effort
            try:
                from src.labat.services.conversions_service import send_single_event, hash_pii
                await send_single_event(
                    event_name="Lead",
                    user_data={"em": [hash_pii(email)]},
                    custom_data={"content_name": "What Is Healthy? Free eBook", "lead_source": "facebook_lead_form"},
                    event_source_url="https://whatishealthy.org/",
                    event_id=f"meta-lead-{leadgen_id}",
                )
            except Exception as e:
                logger.warning(f"CAPI Lead event for Meta lead failed: {e}")

            processed += 1
            logger.info(f"Meta lead synced: {email} variant={variant}")

    return {"status": "ok", "processed": processed}


# ── SendGrid Event Webhook ───────────────────────────────────────────────

@router.post("/sendgrid-webhook")
async def sendgrid_webhook(request: Request):
    """Receive SendGrid open/click/unsubscribe events and record them."""
    try:
        events = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if not isinstance(events, list):
        return {"status": "ok", "processed": 0}

    _HANDLED = {"open", "click", "unsubscribe", "group_unsubscribe", "bounce", "blocked", "dropped", "spamreport"}
    processed = 0
    for event in events:
        email = event.get("email", "")
        event_type = event.get("event", "")
        template_id = event.get("template_id", event.get("category", ""))
        if not email or event_type not in _HANDLED:
            continue
        if "unsubscribe" in event_type:
            mapped = "unsubscribe"
        else:
            mapped = event_type
        try:
            await record_email_event(email, mapped, template_id)
            processed += 1
        except Exception as e:
            logger.warning(f"Failed to record SendGrid event {event_type} for {email}: {e}")

    return {"status": "ok", "processed": processed}
