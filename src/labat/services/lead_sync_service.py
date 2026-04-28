"""
labat/services/lead_sync_service.py — Sync Facebook Lead Form submissions to Firestore + email nurture.

Flow:
  1. Pull new leads from Meta Lead Forms (via leads_service)
  2. Check for duplicates against Firestore launch_leads collection
  3. Store new leads in Firestore
  4. Trigger welcome email via launch_nurture_service
  5. Track sync state (last synced timestamp per form)

Called by:
  - Cron endpoint:  POST /api/labat/leads/sync  (periodic pull)
  - Manual trigger: POST /api/labat/leads/sync?form_id=xxx
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("labat.lead_sync")

# Brand mapping: campaign name prefix → brand key (fallback)
_CAMPAIGN_BRAND_HINTS = {
    "cg": "communitygroceries",
    "community": "communitygroceries",
    "wihy": "wihy",
    "vowels": "vowels",
    "trinity": "vowels",
    "whatishealthy": "childrennutrition",
    "children": "childrennutrition",
}

_BOOK_HINTS: Tuple[str, ...] = (
    "book",
    "vowels",
    "what is healthy",
    "whatishealthy",
    "ebook",
)

_BOOK_BRANDS: Set[str] = {"book", "vowels", "vowelsbook", "whatishealthy"}

# Controls whether sync processes all lead products, only book, or only launch.
_PRODUCT_SCOPE = (os.getenv("LEAD_SYNC_PRODUCT_SCOPE", "all") or "all").strip().lower()

# Optional explicit form allow-list for book campaigns (comma-separated form IDs).
_BOOK_FORM_IDS: Set[str] = {
    x.strip() for x in (os.getenv("LEAD_SYNC_BOOK_FORM_IDS", "") or "").split(",") if x.strip()
}

# How to message book leads from paid forms: buy_now|free_book
_BOOK_LEAD_MODE = (os.getenv("BOOK_LEAD_MODE", "buy_now") or "buy_now").strip().lower()

_sync_state_db = None


def _get_firestore():
    global _sync_state_db
    if _sync_state_db is not None:
        return _sync_state_db
    from google.cloud import firestore
    _sync_state_db = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))
    return _sync_state_db


SYNC_STATE_COLLECTION = "lead_sync_state"


async def _get_last_sync(form_id: str) -> Optional[str]:
    """Get the last sync timestamp for a form."""
    db = _get_firestore()
    doc = await db.collection(SYNC_STATE_COLLECTION).document(form_id).get()
    if doc.exists:
        return doc.to_dict().get("last_synced_at")
    return None


async def _set_last_sync(form_id: str, timestamp: str) -> None:
    """Update the last sync timestamp for a form."""
    db = _get_firestore()
    await db.collection(SYNC_STATE_COLLECTION).document(form_id).set({
        "form_id": form_id,
        "last_synced_at": timestamp,
        "updated_at": datetime.now(timezone.utc),
    }, merge=True)


def _guess_brand(lead: Dict[str, Any], form_name: str = "") -> str:
    """Determine brand from lead data or form name."""
    # Check campaign name
    campaign = (lead.get("campaign_name") or lead.get("ad_name") or "").lower()
    for hint, brand in _CAMPAIGN_BRAND_HINTS.items():
        if hint in campaign:
            return brand

    # Check form name
    form_lower = form_name.lower()
    for hint, brand in _CAMPAIGN_BRAND_HINTS.items():
        if hint in form_lower:
            return brand

    return "wihy"  # default


def _is_book_context(lead: Dict[str, Any], form_name: str = "") -> bool:
    """Detect whether this lead should be treated as a book lead."""
    text = " ".join(
        [
            str(lead.get("campaign_name") or ""),
            str(lead.get("ad_name") or ""),
            str(form_name or ""),
        ]
    ).lower()
    return any(hint in text for hint in _BOOK_HINTS)


def _resolve_track(lead: Dict[str, Any], form_name: str, brand_override: Optional[str]) -> Tuple[str, str]:
    """Return (track, brand) where track is launch|book and brand is normalized."""
    if brand_override:
        normalized = brand_override.strip().lower()
        if normalized in _BOOK_BRANDS:
            return "book", "vowels"
        return "launch", normalized

    if _is_book_context(lead, form_name):
        return "book", "vowels"

    return "launch", _guess_brand(lead, form_name)


def _should_process_form(form: Dict[str, Any], product_scope: str) -> bool:
    """Apply coarse form-level scope filtering before lead fetch."""
    if product_scope not in ("book", "launch"):
        return True

    form_id = str(form.get("id") or "").strip()
    form_name = str(form.get("name") or "")
    looks_book = form_id in _BOOK_FORM_IDS if _BOOK_FORM_IDS else _is_book_context({}, form_name)

    if product_scope == "book":
        return looks_book
    return not looks_book


async def sync_leads_from_form(
    form_id: str,
    brand: Optional[str] = None,
    form_name: str = "",
) -> Dict[str, Any]:
    """
    Pull all new leads from a Meta lead form and sync to Firestore + email.

    Returns:
        {"synced": N, "skipped": N, "errors": N, "leads": [...]}
    """
    from src.labat.services.leads_service import get_leads_from_form
    try:

        from src.services.launch_leads_service import save_lead, email_exists

        from src.services.launch_nurture_service import trigger_welcome

    except ImportError:

        save_lead = None

        email_exists = None

        trigger_welcome = None

    # Get last sync timestamp
    last_sync = await _get_last_sync(form_id)

    # Pull leads from Meta
    all_leads: List[Dict[str, Any]] = []
    after_cursor = None

    while True:
        result = await get_leads_from_form(
            form_id=form_id,
            limit=100,
            after=after_cursor,
            since=last_sync,
        )
        leads = result.get("data", [])
        all_leads.extend(leads)

        # Check pagination
        paging = result.get("paging", {})
        cursors = paging.get("cursors", {})
        after_cursor = cursors.get("after")
        if not after_cursor or not paging.get("next"):
            break

    logger.info("Fetched %d leads from form %s (since=%s)", len(all_leads), form_id, last_sync)

    synced = 0
    synced_book = 0
    synced_launch = 0
    skipped = 0
    errors = 0
    synced_leads = []
    latest_timestamp = last_sync

    for lead in all_leads:
        try:
            # Parse field_data
            fields: Dict[str, str] = {}
            for field in lead.get("field_data", []):
                vals = field.get("values", [])
                fields[field["name"]] = vals[0] if vals else ""

            email = fields.get("email", "").lower().strip()
            if not email:
                logger.warning("Lead %s has no email, skipping", lead.get("id"))
                skipped += 1
                continue

            lead_track, lead_brand = _resolve_track(lead, form_name, brand)

            # Apply per-lead scope guard (handles mixed forms safely).
            if _PRODUCT_SCOPE == "book" and lead_track != "book":
                skipped += 1
                continue
            if _PRODUCT_SCOPE == "launch" and lead_track != "launch":
                skipped += 1
                continue

            first_name = fields.get("first_name", "")
            last_name = fields.get("last_name", "")
            full_name = fields.get("full_name", "")
            if full_name and not first_name:
                parts = full_name.strip().split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

            if lead_track == "book":
                from src.services.book_leads_service import email_exists as book_email_exists
                from src.services.book_leads_service import save_lead as save_book_lead
                from src.services.nurture_service import trigger_buy_now, trigger_day0

                if await book_email_exists(email):
                    logger.debug("Book lead already exists (email=%s)", email)
                    skipped += 1
                    continue

                await save_book_lead(
                    email=email,
                    source=(
                        "facebook_book_purchase"
                        if _BOOK_LEAD_MODE == "buy_now"
                        else "facebook_lead_form"
                    ),
                    first_name=first_name,
                    last_name=last_name,
                    utm_source="facebook",
                    utm_campaign=lead.get("campaign_id", ""),
                    utm_medium="paid",
                    utm_content=form_name,
                    fbclid=lead.get("ad_id", ""),
                )
                if _BOOK_LEAD_MODE == "buy_now":
                    await trigger_buy_now(
                        email=email,
                        first_name=first_name,
                        variant=form_name,
                    )
                else:
                    await trigger_day0(
                        email=email,
                        first_name=first_name,
                        variant=form_name,
                    )
                synced_book += 1
            else:
                # Check duplicate
                if await email_exists(email, lead_brand):
                    logger.debug("Lead %s already exists (email=%s, brand=%s)", lead["id"], email, lead_brand)
                    skipped += 1
                    continue

                # Save to Firestore
                await save_lead(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    brand=lead_brand,
                    utm_source="facebook_lead_ad",
                    utm_campaign=lead.get("campaign_id", ""),
                    fbclid=lead.get("ad_id", ""),
                )

                # Trigger welcome email
                await trigger_welcome(email=email, first_name=first_name, brand=lead_brand)
                synced_launch += 1

            synced += 1
            synced_leads.append({
                "email": email,
                "first_name": first_name,
                "brand": lead_brand,
                "track": lead_track,
                "book_mode": _BOOK_LEAD_MODE if lead_track == "book" else None,
                "meta_lead_id": lead.get("id"),
            })
            logger.info(
                "Synced lead: %s (track=%s, brand=%s, meta_id=%s)",
                email,
                lead_track,
                lead_brand,
                lead.get("id"),
            )

            # Track latest timestamp
            created = lead.get("created_time", "")
            if created and (not latest_timestamp or created > latest_timestamp):
                latest_timestamp = created

        except Exception as e:
            errors += 1
            logger.error("Error syncing lead %s: %s", lead.get("id"), e, exc_info=True)

    # Update sync state
    if latest_timestamp and latest_timestamp != last_sync:
        await _set_last_sync(form_id, latest_timestamp)

    return {
        "form_id": form_id,
        "synced": synced,
        "synced_book": synced_book,
        "synced_launch": synced_launch,
        "skipped": skipped,
        "errors": errors,
        "total_fetched": len(all_leads),
        "leads": synced_leads,
    }


async def sync_all_forms(page_id: Optional[str] = None, brand: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync leads from ALL active lead forms on the page.
    Called by the cron job.
    """
    from src.labat.brands import BRAND_PAGE_IDS, get_page_id
    from src.labat.meta_client import MetaAPIError
    from src.labat.services.leads_service import list_lead_forms

    effective_page_id = page_id
    if not effective_page_id:
        if brand:
            effective_page_id = get_page_id(brand)
        elif _PRODUCT_SCOPE == "book":
            effective_page_id = get_page_id("vowels")

    try:
        forms_result = await list_lead_forms(page_id=effective_page_id)
    except MetaAPIError as exc:
        # Some tokens are scoped to WIHY page only. Fall back so cron stays healthy.
        fallback_page = BRAND_PAGE_IDS.get("wihy")
        if effective_page_id and fallback_page and effective_page_id != fallback_page:
            logger.warning(
                "Lead form list failed for page %s (%s); retrying WIHY page %s",
                effective_page_id,
                exc,
                fallback_page,
            )
            forms_result = await list_lead_forms(page_id=fallback_page)
            effective_page_id = fallback_page
        else:
            raise
    forms = forms_result.get("data", [])

    results = []
    total_synced = 0
    total_synced_book = 0
    total_synced_launch = 0
    total_errors = 0

    for form in forms:
        form_id = form["id"]
        form_name = form.get("name", "")
        status = form.get("status", "")

        if status and status.lower() not in ("active", ""):
            logger.debug("Skipping inactive form %s (%s)", form_id, form_name)
            continue

        if not _should_process_form(form, _PRODUCT_SCOPE):
            logger.info("Skipping form %s (%s) due to LEAD_SYNC_PRODUCT_SCOPE=%s", form_id, form_name, _PRODUCT_SCOPE)
            continue

        result = await sync_leads_from_form(
            form_id=form_id,
            brand=brand,
            form_name=form_name,
        )
        results.append(result)
        total_synced += result["synced"]
        total_synced_book += result.get("synced_book", 0)
        total_synced_launch += result.get("synced_launch", 0)
        total_errors += result["errors"]

    logger.info("Lead sync complete: %d forms, %d synced, %d errors", len(results), total_synced, total_errors)

    return {
        "forms_processed": len(results),
        "total_synced": total_synced,
        "total_synced_book": total_synced_book,
        "total_synced_launch": total_synced_launch,
        "total_errors": total_errors,
        "product_scope": _PRODUCT_SCOPE,
        "book_lead_mode": _BOOK_LEAD_MODE,
        "page_id": effective_page_id,
        "results": results,
    }
