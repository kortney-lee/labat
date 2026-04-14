"""
Launch Leads Service
Stores email captures from WIHY and Community Groceries pre-launch landing pages.
Uses Firestore — separate collection from book leads.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_db = None


def _get_firestore():
    global _db
    if _db is not None:
        return _db
    try:
        from google.cloud import firestore
        _db = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))
        logger.info("Firestore client initialized for launch leads")
        return _db
    except Exception as e:
        logger.error(f"Firestore init failed: {e}")
        raise


COLLECTION = "launch_leads"


async def save_lead(
    email: str,
    first_name: str = "",
    last_name: str = "",
    brand: str = "wihy",
    utm_source: str = "",
    utm_campaign: str = "",
    utm_medium: str = "",
    fbclid: str = "",
) -> dict:
    """Store a launch signup. Returns the created document data."""
    db = _get_firestore()
    now = datetime.now(timezone.utc)
    doc_data: Dict[str, Any] = {
        "email": email.lower().strip(),
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "brand": brand,
        "nurture_stage": 0,
        "nurture_next_at": now,
        "sequence_status": "active",
        "created_at": now,
    }
    if utm_source:
        doc_data["utm_source"] = utm_source
    if utm_campaign:
        doc_data["utm_campaign"] = utm_campaign
    if utm_medium:
        doc_data["utm_medium"] = utm_medium
    if fbclid:
        doc_data["fbclid"] = fbclid

    doc_ref = db.collection(COLLECTION).document()
    await doc_ref.set(doc_data)
    logger.info("Launch lead saved: %s (brand=%s)", email, brand)
    return {**doc_data, "id": doc_ref.id, "created_at": now.isoformat()}


async def email_exists(email: str, brand: str) -> bool:
    """Check if email already signed up for this brand's launch."""
    db = _get_firestore()
    query = (
        db.collection(COLLECTION)
        .where("email", "==", email.lower().strip())
        .where("brand", "==", brand)
        .limit(1)
    )
    docs = [doc async for doc in query.stream()]
    return len(docs) > 0


async def get_pending_nurture(limit: int = 100) -> List[Dict[str, Any]]:
    """Get leads due for their next nurture email."""
    db = _get_firestore()
    now = datetime.now(timezone.utc)
    query = (
        db.collection(COLLECTION)
        .where("sequence_status", "==", "active")
        .where("nurture_next_at", "<=", now)
        .limit(limit)
    )
    results = []
    async for doc in query.stream():
        data = doc.to_dict()
        data["id"] = doc.id
        results.append(data)
    return results


async def advance_nurture(doc_id: str, next_stage: int, next_at: Optional[datetime] = None) -> None:
    """Advance a lead to the next nurture stage."""
    db = _get_firestore()
    update: Dict[str, Any] = {"nurture_stage": next_stage}
    if next_at:
        update["nurture_next_at"] = next_at
    else:
        update["sequence_status"] = "completed"
    await db.collection(COLLECTION).document(doc_id).update(update)


async def mark_unsubscribed(email: str) -> None:
    """Mark a lead as unsubscribed."""
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip())
    async for doc in query.stream():
        await doc.reference.update({
            "sequence_status": "unsubscribed",
            "unsubscribed_at": datetime.now(timezone.utc),
        })


async def get_stats() -> Dict[str, Any]:
    """Return signup counts grouped by brand."""
    db = _get_firestore()
    stats: Dict[str, int] = {}
    async for doc in db.collection(COLLECTION).stream():
        brand = doc.to_dict().get("brand", "unknown")
        stats[brand] = stats.get(brand, 0) + 1
    return {"total": sum(stats.values()), "by_brand": stats}


async def record_email_event(email: str, event: str) -> None:
    """Record a SendGrid event (open, click, etc.) on the lead."""
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
    async for doc in query.stream():
        events = doc.to_dict().get("email_events", [])
        events.append({"event": event, "at": datetime.now(timezone.utc).isoformat()})
        await doc.reference.update({"email_events": events})
        break
