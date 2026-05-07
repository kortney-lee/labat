"""
B2B Nurture Service
Email sequences for business leads: bookstores, libraries, podcasts, blogs, churches, schools.

Each business type gets a tailored sequence focused on:
  - Wholesale / bulk ordering
  - Library acquisition & program support
  - Podcast / media kit & booking
  - Blog / content partnership

Sequences are shorter (5 emails) and more direct than the consumer sequence.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
FROM_EMAIL = os.getenv("B2B_FROM_EMAIL", "partnerships@vowels.org")
FROM_NAME  = os.getenv("B2B_FROM_NAME",  "Kortney Lee — What Is Healthy?")
BCC_EMAIL  = os.getenv("BOOK_EMAIL_BCC", "kortney@wihy.ai")
UNSUBSCRIBE_URL = "https://whatishealthy.org/unsubscribe"

WHOLESALE_URL  = "https://whatishealthy.org/wholesale"
MEDIA_KIT_URL  = "https://whatishealthy.org/media-kit"
LIBRARY_URL    = "https://whatishealthy.org/libraries"
BOOK_IMAGE_URL = "https://storage.googleapis.com/wihy-web-assets/images/book-green.jpg"


# ── Copy by business type ─────────────────────────────────────────────────────

_COPY = {
    "bookstore": {
        "greeting": "thanks for your interest in carrying What Is Healthy?",
        "context": "We work with independent bookstores across the country and would love to get the book on your shelves.",
        "offer": "Wholesale pricing is available for orders of 10+ copies, with standard terms and returnable options.",
        "cta_label": "View Wholesale Info",
        "cta_url": WHOLESALE_URL,
        "subject_d0": "Wholesale info for What Is Healthy?",
        "subject_d3": "A few things bookstore owners have asked us",
        "subject_d7": "Still interested in carrying the book?",
    },
    "library": {
        "greeting": "thanks for your interest in What Is Healthy? for your library",
        "context": "We actively support library acquisitions and can provide review copies, author Q&A sessions, and program support.",
        "offer": "Libraries receive special pricing and we can support reading group guides, community health programs, and author events.",
        "cta_label": "Library Acquisition Info",
        "cta_url": LIBRARY_URL,
        "subject_d0": "What Is Healthy? — library acquisition info",
        "subject_d3": "What other libraries have done with the book",
        "subject_d7": "Happy to help with your acquisition request",
    },
    "podcast": {
        "greeting": "thanks for reaching out about having me on your podcast",
        "context": "I'd love to talk about what the research shows about the food system, label deception, and what families can actually do about it.",
        "offer": "I'm available for interviews and can work around your schedule. Media kit and talking points are available.",
        "cta_label": "View Media Kit",
        "cta_url": MEDIA_KIT_URL,
        "subject_d0": "Podcast booking — What Is Healthy?",
        "subject_d3": "Topics I can cover on your show",
        "subject_d7": "Still interested in booking?",
    },
    "blog": {
        "greeting": "thanks for your interest in covering What Is Healthy?",
        "context": "I'd be glad to provide a review copy, an exclusive excerpt, or an interview for your readers.",
        "offer": "Review copies are available digitally or in print. I'm also open to guest posts on food, health, and the food industry.",
        "cta_label": "Request a Review Copy",
        "cta_url": MEDIA_KIT_URL,
        "subject_d0": "Review copy / interview — What Is Healthy?",
        "subject_d3": "Angles your readers tend to respond to",
        "subject_d7": "Still interested in covering the book?",
    },
    "church": {
        "greeting": "thanks for reaching out about What Is Healthy?",
        "context": "The book has been used in church wellness programs, small group studies, and community health events. We love supporting faith communities doing this work.",
        "offer": "Bulk pricing is available for group studies, and I'm available to speak at health-focused church events.",
        "cta_label": "Bulk Order & Speaking Info",
        "cta_url": WHOLESALE_URL,
        "subject_d0": "What Is Healthy? — church & community group info",
        "subject_d3": "How other faith communities have used the book",
        "subject_d7": "Happy to answer any questions",
    },
    "school": {
        "greeting": "thanks for reaching out about What Is Healthy? for your school",
        "context": "We support school nutrition programs, health classes, and parent education events with curriculum-aligned resources.",
        "offer": "Classroom and program pricing is available, and I'm available for student assemblies and parent workshops.",
        "cta_label": "School Program Info",
        "cta_url": LIBRARY_URL,
        "subject_d0": "What Is Healthy? — school program info",
        "subject_d3": "What other schools have done with the book",
        "subject_d7": "Happy to support your program",
    },
    "other": {
        "greeting": "thanks for reaching out",
        "context": "We'd love to learn more about how you're thinking about the book and how we might work together.",
        "offer": "Whether you're interested in bulk orders, a speaking engagement, or a content partnership, we're open to the conversation.",
        "cta_label": "Learn More",
        "cta_url": WHOLESALE_URL,
        "subject_d0": "What Is Healthy? — partnership inquiry",
        "subject_d3": "A few ways we work with partners",
        "subject_d7": "Still interested in connecting?",
    },
}


def _get_copy(business_type: str) -> dict:
    return _COPY.get(business_type, _COPY["other"])


# ── Email templates ───────────────────────────────────────────────────────────

def _wrap(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;">
{content}
<tr><td style="padding:16px 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:12px;color:#9ca3af;line-height:1.6;">
<a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
&middot; Sent by Vowels &middot; What Is Healthy?
</p></td></tr>
</table></td></tr></table></body></html>"""


def _cta(label: str, url: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0"><tr>'
        f'<td bgcolor="#1e40af" style="border-radius:5px;">'
        f'<a href="{url}" style="display:block;padding:12px 24px;color:#ffffff;'
        f'font-size:15px;font-weight:600;text-decoration:none;">{label}</a>'
        f'</td></tr></table>'
    )


def _render_b2b_day0(first_name: str, business_type: str, company_name: str) -> str:
    c = _get_copy(business_type)
    name = first_name or "there"
    company = f" at {company_name}" if company_name else ""
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['greeting'].capitalize()}{company}.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['context']}</p>
</td></tr>
<tr><td align="center" style="padding:0 40px 24px;">
<img src="{BOOK_IMAGE_URL}" width="120" alt="What Is Healthy?" style="display:block;margin:0 auto;border:0;" />
</td></tr>
<tr><td style="padding:0 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
{c['offer']}</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Hit reply and tell me a bit more about what you're looking for — or click below to see our options:</p>
{_cta(c['cta_label'], c['cta_url'])}
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>Kortney Lee<br/>
<span style="font-size:14px;color:#6b7280;">Author, What Is Healthy?</span></p>
</td></tr>""")


def _render_b2b_followup(first_name: str, business_type: str, company_name: str) -> str:
    c = _get_copy(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Just following up on my email from a few days ago about <strong>What Is Healthy?</strong></p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
A few things people in your position tend to ask us:</p>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<table width="100%" cellpadding="16" cellspacing="0" bgcolor="#f9fafb"
       style="border-left:3px solid #e5e7eb;font-size:15px;line-height:1.8;color:#374151;">
<tr><td>
<p style="margin:0 0 10px;"><strong>What does the book actually cover?</strong><br/>
264 pages on the food industry, label deception, ultra-processed food, sugar,
community health, psychology of change, and what the research says about what
works. Written for a general audience — not a textbook.</p>
<p style="margin:0 0 10px;"><strong>Who reads it?</strong><br/>
Primarily adults 30–65 who are frustrated with conflicting health advice and want
a research-backed, agenda-free perspective. Strong resonance with families,
faith communities, and health-conscious individuals.</p>
<p style="margin:0;"><strong>Is there a digital version?</strong><br/>
Yes — Kindle and Audible are both available. For bulk digital orders, contact us directly.</p>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<p style="margin:20px 0 16px;font-size:16px;line-height:1.8;color:#374151;">
{_cta(c['cta_label'], c['cta_url'])}</p>
</td></tr>
<tr><td style="padding:16px 40px 32px;border-top:1px solid #e5e7eb;">
<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">
Talk soon,<br/>Kortney</p>
</td></tr>""")


def _render_b2b_last(first_name: str, business_type: str, company_name: str) -> str:
    c = _get_copy(business_type)
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 32px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
Last note from me on this — I don't want to clutter your inbox.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">
If the timing wasn't right or things got busy, no problem at all. We're here whenever
it makes sense. Just hit reply or visit the link below.</p>
{_cta(c['cta_label'], c['cta_url'])}
<p style="margin:24px 0 0;font-size:16px;line-height:1.8;color:#374151;">
All the best,<br/>Kortney</p>
</td></tr>""")


_B2B_SEQUENCE = [
    (0, 0,  "b2b_day0",      lambda bt: _get_copy(bt)["subject_d0"]),
    (1, 3,  "b2b_followup",  lambda bt: _get_copy(bt)["subject_d3"]),
    (2, 7,  "b2b_last",      lambda bt: _get_copy(bt)["subject_d7"]),
]


# ── Sending ───────────────────────────────────────────────────────────────────

async def _send(to_email: str, subject: str, html: str) -> bool:
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping B2B email")
        return False
    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
        "categories": ["b2b-nurture"],
    }
    if BCC_EMAIL and BCC_EMAIL.lower() != to_email.lower():
        payload["personalizations"][0]["bcc"] = [{"email": BCC_EMAIL}]
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {SENDGRID_API_KEY}", "Content-Type": "application/json"},
            )
        if r.status_code in (200, 201, 202):
            logger.info("B2B email sent: %s subject=%r", to_email, subject)
            return True
        logger.error("B2B SendGrid error %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        logger.error("B2B email send failed: %s", e)
    return False


async def trigger_b2b_day0(
    email: str, first_name: str, business_type: str, company_name: str = ""
) -> bool:
    """Send Day 0 B2B email immediately on lead capture."""
    bt = business_type or "other"
    html = _render_b2b_day0(first_name, bt, company_name)
    subject = _get_copy(bt)["subject_d0"]
    return await _send(email, subject, html)


async def process_pending_b2b_nurture() -> dict:
    """
    Cron: send pending B2B nurture emails.
    Reads book_leads where lead_type='b2b' and sequence_status='active'.
    """
    from datetime import datetime, timezone
    from google.cloud import firestore

    db = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))
    now = datetime.now(timezone.utc)
    sent = skipped = errors = 0

    query = (
        db.collection("book_leads")
        .where("lead_type", "==", "b2b")
        .where("sequence_status", "==", "active")
        .where("nurture_next_at", "<=", now)
        .limit(50)
    )

    async for doc in query.stream():
        d = doc.to_dict()
        stage = d.get("nurture_stage", 0)
        if stage >= len(_B2B_SEQUENCE):
            await doc.reference.update({"sequence_status": "completed"})
            continue

        _, days, template_id, subject_fn = _B2B_SEQUENCE[stage]
        email = d.get("email", "")
        first_name = d.get("first_name", "")
        business_type = d.get("business_type", "other")
        company_name = d.get("company_name", "")

        try:
            if template_id == "b2b_day0":
                html = _render_b2b_day0(first_name, business_type, company_name)
            elif template_id == "b2b_followup":
                html = _render_b2b_followup(first_name, business_type, company_name)
            else:
                html = _render_b2b_last(first_name, business_type, company_name)

            subject = subject_fn(business_type)
            ok = await _send(email, subject, html)

            from datetime import timedelta
            next_stage = stage + 1
            next_days = _B2B_SEQUENCE[next_stage][1] if next_stage < len(_B2B_SEQUENCE) else None
            update: dict = {
                "nurture_stage": next_stage,
                f"nurture_{template_id}_sent_at": now,
            }
            if next_days is not None:
                update["nurture_next_at"] = now + timedelta(days=next_days)
                update["sequence_status"] = "active"
            else:
                update["sequence_status"] = "completed"

            await doc.reference.update(update)
            if ok:
                sent += 1
            else:
                errors += 1
        except Exception as e:
            logger.error("B2B nurture error for %s: %s", email, e)
            errors += 1

    return {"sent": sent, "skipped": skipped, "errors": errors, "ran_at": now.isoformat()}
