"""
Book Leads Service
Stores email captures from the What Is Healthy? landing page.
Uses Firestore for simplicity — no separate SQL instance needed.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firestore thin wrapper — keeps everything in one collection
# ---------------------------------------------------------------------------

_db = None


def _get_firestore():
    global _db
    if _db is not None:
        return _db

    try:
        from google.cloud import firestore
        _db = firestore.AsyncClient(
            project=os.getenv("GCP_PROJECT", "wihy-ai"),
        )
        logger.info("Firestore client initialized for book leads")
        return _db
    except Exception as e:
        logger.error(f"Firestore init failed: {e}")
        raise


COLLECTION = "book_leads"


async def save_lead(
    email: str, source: str = "whatishealthy", first_name: str = "", last_name: str = "",
    utm_source: str = "", utm_campaign: str = "", utm_content: str = "",
    utm_medium: str = "", fbclid: str = "",
) -> dict:
    """Store an email lead. Returns the created document data."""
    db = _get_firestore()
    now = datetime.now(timezone.utc)
    doc_data = {
        "email": email.lower().strip(),
        "first_name": first_name,
        "last_name": last_name,
        "source": source,
        "lead_tag": "book_free",
        "funnel_stage": "captured",
        "sequence_status": "active",
        "nurture_stage": 0,
        "nurture_next_at": now,
        "created_at": now,
        "delivered": False,
        "paperback_purchased": False,
    }
    if utm_source:
        doc_data["utm_source"] = utm_source
    if utm_campaign:
        doc_data["utm_campaign"] = utm_campaign
    if utm_content:
        doc_data["utm_content"] = utm_content
    if utm_medium:
        doc_data["utm_medium"] = utm_medium
    if fbclid:
        doc_data["fbclid"] = fbclid
    doc_ref = db.collection(COLLECTION).document()
    await doc_ref.set(doc_data)
    logger.info(f"Lead saved: {email} (source={source})")
    return {**doc_data, "id": doc_ref.id, "created_at": now.isoformat()}


async def email_exists(email: str) -> bool:
    """Check if an email is already captured."""
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
    docs = [doc async for doc in query.stream()]
    return len(docs) > 0


async def mark_delivered(email: str) -> None:
    """Mark a lead as book-delivered."""
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
    async for doc in query.stream():
        await doc.reference.update({
            "delivered": True,
            "delivered_at": datetime.now(timezone.utc),
            "funnel_stage": "lead_magnet_delivered",
            "sequence_status": "active",
        })
        break


async def mark_purchased(email: str) -> None:
    """Mark a lead as having purchased the paperback."""
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
    async for doc in query.stream():
        await doc.reference.update({
            "paperback_purchased": True,
            "purchased_at": datetime.now(timezone.utc),
            "funnel_stage": "purchased",
            "sequence_status": "buyer",
        })
        logger.info(f"Marked purchased: {email}")
        break


async def get_lead_data(email: str) -> Optional[Dict[str, Any]]:
    """Retrieve lead document data by email. Returns None if not found."""
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
    async for doc in query.stream():
        return doc.to_dict()
    return None


async def mark_unsubscribed(email: str) -> bool:
    """Mark a lead as unsubscribed — stops nurture emails."""
    db = _get_firestore()
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
    async for doc in query.stream():
        await doc.reference.update({
            "sequence_status": "unsubscribed",
            "unsubscribed_at": datetime.now(timezone.utc),
        })
        logger.info(f"Unsubscribed: {email}")
        return True
    return False


async def record_email_event(email: str, event_type: str, template_id: str = "") -> None:
    """Record a SendGrid email event (open, click, etc.) on the lead document."""
    db = _get_firestore()
    now = datetime.now(timezone.utc)
    query = db.collection(COLLECTION).where("email", "==", email.lower().strip()).limit(1)
    async for doc in query.stream():
        from google.cloud.firestore import ArrayUnion
        update: dict = {}
        if event_type == "open":
            update["last_opened_at"] = now
            update["opens"] = ArrayUnion([{"at": now, "template": template_id}])
        elif event_type == "click":
            update["last_clicked_at"] = now
            update["clicks"] = ArrayUnion([{"at": now, "template": template_id}])
        elif event_type == "unsubscribe":
            update["sequence_status"] = "unsubscribed"
            update["unsubscribed_at"] = now
        if update:
            await doc.reference.update(update)
        break


async def get_lead_count() -> int:
    """Get total number of leads."""
    db = _get_firestore()
    count = 0
    async for _ in db.collection(COLLECTION).stream():
        count += 1
    return count


async def get_funnel_stats() -> dict:
    """Get funnel stats across all leads."""
    db = _get_firestore()
    stats = {
        "total_leads": 0,
        "active": 0,
        "completed": 0,
        "unsubscribed": 0,
        "buyers": 0,
        "opened_any": 0,
        "clicked_any": 0,
        "by_stage": {str(i): 0 for i in range(6)},
    }
    async for doc in db.collection(COLLECTION).stream():
        data = doc.to_dict()
        stats["total_leads"] += 1
        status = data.get("sequence_status", "active")
        if status == "active":
            stats["active"] += 1
        elif status == "completed":
            stats["completed"] += 1
        elif status == "unsubscribed":
            stats["unsubscribed"] += 1
        elif status == "buyer":
            stats["buyers"] += 1
        if data.get("last_opened_at"):
            stats["opened_any"] += 1
        if data.get("last_clicked_at"):
            stats["clicked_any"] += 1
        stage = str(data.get("nurture_stage", 0))
        if stage in stats["by_stage"]:
            stats["by_stage"][stage] += 1
    return stats
