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
    """Record a SendGrid email event (open, click, bounce, etc.) on the lead document."""
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
        elif event_type in ("bounce", "blocked"):
            update["sequence_status"] = "bounced"
            update["bounced_at"] = now
            update["bounce_template"] = template_id
            logger.info(f"Lead bounced — stopping nurture: {email}")
        elif event_type == "dropped":
            update["sequence_status"] = "dropped"
            update["dropped_at"] = now
            logger.info(f"Lead dropped by SendGrid — stopping nurture: {email}")
        elif event_type == "spamreport":
            update["sequence_status"] = "spam"
            update["spam_at"] = now
            logger.warning(f"Spam report received — stopping nurture: {email}")
        if update:
            await doc.reference.update(update)
        break


async def mark_send_failed(doc_ref, failure_count: int) -> None:
    """Increment send failure count; after 3 consecutive failures stop the sequence."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    if failure_count >= 3:
        await doc_ref.update({
            "sequence_status": "failed",
            "failed_at": now,
            "send_failure_count": failure_count,
        })
        logger.warning(f"Lead send_failure_count={failure_count} — marked failed, stopping nurture")
    else:
        # Exponential backoff: retry after 1h, 4h, then give up
        backoff_hours = 2 ** failure_count  # 2h, 4h
        await doc_ref.update({
            "send_failure_count": failure_count,
            "last_send_failed_at": now,
            "nurture_next_at": now + timedelta(hours=backoff_hours),
        })


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


async def get_book_leads_report(days: int = 7) -> Dict[str, Any]:
    """
    Return a structured book-lead performance report for use in daily digest emails.

        Includes:
      - Total leads all-time + last N days
            - Per-form breakdown (grouped by utm_content; falls back to source for web leads)
            - Per-source breakdown (whatishealthy/wihy/communitygroceries/facebook/etc.)
      - Funnel stage counts
      - SendGrid aggregate email engagement (sent/opens/clicks) for last N days
    """
    import httpx as _httpx
    from datetime import timedelta

    db = _get_firestore()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    total = 0
    total_recent = 0
    delivered = 0
    purchased = 0
    by_form: Dict[str, Dict[str, Any]] = {}
    by_source: Dict[str, Dict[str, Any]] = {}
    by_stage: Dict[str, int] = {}

    async for doc in db.collection(COLLECTION).stream():
        d = doc.to_dict() or {}
        total += 1

        created_at = d.get("created_at")
        is_recent = False
        if created_at:
            # Firestore returns datetime objects; handle both aware and naive
            ca = created_at if hasattr(created_at, "tzinfo") and created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
            if ca >= cutoff:
                is_recent = True
                total_recent += 1

        if d.get("delivered"):
            delivered += 1
        if d.get("paperback_purchased"):
            purchased += 1

        stage_key = d.get("funnel_stage") or d.get("sequence_status") or "unknown"
        by_stage[stage_key] = by_stage.get(stage_key, 0) + 1

        lead_source = (d.get("source") or d.get("utm_source") or "unknown").strip() or "unknown"
        form_name = (d.get("utm_content") or "").strip()
        if not form_name:
            form_name = f"web:{lead_source}"
        if form_name not in by_form:
            by_form[form_name] = {"total": 0, "recent": 0, "delivered": 0, "purchased": 0}
        by_form[form_name]["total"] += 1
        if is_recent:
            by_form[form_name]["recent"] += 1
        if d.get("delivered"):
            by_form[form_name]["delivered"] += 1
        if d.get("paperback_purchased"):
            by_form[form_name]["purchased"] += 1

        if lead_source not in by_source:
            by_source[lead_source] = {"total": 0, "recent": 0, "delivered": 0, "purchased": 0}
        by_source[lead_source]["total"] += 1
        if is_recent:
            by_source[lead_source]["recent"] += 1
        if d.get("delivered"):
            by_source[lead_source]["delivered"] += 1
        if d.get("paperback_purchased"):
            by_source[lead_source]["purchased"] += 1

    # Sort forms by total leads descending
    by_form_sorted = dict(sorted(by_form.items(), key=lambda x: x[1]["total"], reverse=True))
    by_source_sorted = dict(sorted(by_source.items(), key=lambda x: x[1]["total"], reverse=True))

    # SendGrid aggregate stats for last N days
    sg_key = os.getenv("SENDGRID_API_KEY", "").strip()
    email_engagement: Dict[str, Any] = {}
    if sg_key:
        try:
            start_date = (now - timedelta(days=days)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            async with _httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(
                    "https://api.sendgrid.com/v3/stats",
                    headers={"Authorization": f"Bearer {sg_key}"},
                    params={"start_date": start_date, "end_date": end_date, "aggregated_by": "day"},
                )
            if r.status_code == 200:
                totals: Dict[str, int] = {
                    "requests": 0, "delivered": 0, "unique_opens": 0,
                    "unique_clicks": 0, "bounces": 0,
                }
                for day_entry in r.json():
                    for entry in day_entry.get("stats", []):
                        m = entry.get("metrics", {})
                        for k in totals:
                            totals[k] += m.get(k, 0)
                sent = totals["requests"]
                dlvd = totals["delivered"]
                opens = totals["unique_opens"]
                clicks = totals["unique_clicks"]
                email_engagement = {
                    "period_days": days,
                    "emails_sent": sent,
                    "delivered": dlvd,
                    "delivery_rate_pct": round(dlvd / sent * 100, 1) if sent else 0,
                    "unique_opens": opens,
                    "open_rate_pct": round(opens / dlvd * 100, 1) if dlvd else 0,
                    "unique_clicks": clicks,
                    "click_rate_pct": round(clicks / opens * 100, 1) if opens else 0,
                    "bounces": totals["bounces"],
                }
            else:
                email_engagement = {"error": f"SendGrid {r.status_code}"}
        except Exception as exc:
            email_engagement = {"error": str(exc)}
    else:
        email_engagement = {"error": "SENDGRID_API_KEY not configured"}

    return {
        "generated_at": now.strftime("%B %d, %Y at %H:%M UTC"),
        "period_days": days,
        "total_book_leads": total,
        f"new_leads_last_{days}d": total_recent,
        "total_delivered": delivered,
        "total_purchased": purchased,
        "conversion_rate_pct": round(purchased / total * 100, 1) if total else 0,
        "by_form": by_form_sorted,
        "by_source": by_source_sorted,
        "by_funnel_stage": dict(sorted(by_stage.items(), key=lambda x: x[1], reverse=True)),
        "email_engagement": email_engagement,
    }
