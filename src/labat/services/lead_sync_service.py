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
from typing import Any, Dict, List, Optional

logger = logging.getLogger("labat.lead_sync")

# Import centralized brand mapping
from src.labat.brands import PAGE_BRAND_MAP as _PAGE_BRAND_MAP

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

            lead_brand = brand or _guess_brand(lead, form_name)

            # Check duplicate
            if await email_exists(email, lead_brand):
                logger.debug("Lead %s already exists (email=%s, brand=%s)", lead["id"], email, lead_brand)
                skipped += 1
                continue

            first_name = fields.get("first_name", "")
            last_name = fields.get("last_name", "")
            full_name = fields.get("full_name", "")
            if full_name and not first_name:
                parts = full_name.strip().split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

            # Save to Firestore
            saved = await save_lead(
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

            synced += 1
            synced_leads.append({
                "email": email,
                "first_name": first_name,
                "brand": lead_brand,
                "meta_lead_id": lead.get("id"),
            })
            logger.info("Synced lead: %s (brand=%s, meta_id=%s)", email, lead_brand, lead.get("id"))

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
        "skipped": skipped,
        "errors": errors,
        "total_fetched": len(all_leads),
        "leads": synced_leads,
    }


async def sync_all_forms(page_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Sync leads from ALL active lead forms on the page.
    Called by the cron job.
    """
    from src.labat.services.leads_service import list_lead_forms

    forms_result = await list_lead_forms(page_id=page_id)
    forms = forms_result.get("data", [])

    results = []
    total_synced = 0
    total_errors = 0

    for form in forms:
        form_id = form["id"]
        form_name = form.get("name", "")
        status = form.get("status", "")

        if status and status.lower() not in ("active", ""):
            logger.debug("Skipping inactive form %s (%s)", form_id, form_name)
            continue

        result = await sync_leads_from_form(
            form_id=form_id,
            form_name=form_name,
        )
        results.append(result)
        total_synced += result["synced"]
        total_errors += result["errors"]

    logger.info("Lead sync complete: %d forms, %d synced, %d errors", len(results), total_synced, total_errors)

    return {
        "forms_processed": len(results),
        "total_synced": total_synced,
        "total_errors": total_errors,
        "results": results,
    }
