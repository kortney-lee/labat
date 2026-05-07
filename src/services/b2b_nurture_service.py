"""
B2B Nurture Service
5-email warm-introduction sequence for: bookstores, libraries, podcasts,
blogs, churches, schools.

Tone: personal, informational, no bulk/wholesale talk, no whatishealthy.org links.
Just letting them know the book exists and Kortney is here.

Schedule:
  Day 0:  Why I wrote the book + who it's for
  Day 3:  A little more about what's in it
  Day 7:  What readers are saying
  Day 14: Still here if you're interested
  Day 21: Last note
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
FROM_EMAIL = os.getenv("B2B_FROM_EMAIL", "info@vowels.org")
FROM_NAME  = os.getenv("B2B_FROM_NAME",  "Kortney Lee")
BCC_EMAIL  = os.getenv("BOOK_EMAIL_BCC", "kortney@wihy.ai")

UNSUBSCRIBE_URL      = "https://whatishealthy.org/unsubscribe"

# IngramSpark direct purchase
INGRAM_FEMALE_URL    = "https://shop.ingramspark.com/b/084?params=KdF9tI0DBCGxHsXvFp5EzonT2Vjy0qlWQPnReIEveSF"
INGRAM_MALE_URL      = "https://shop.ingramspark.com/b/084?params=ortH8rLGOSivIH3DLwamRSP1VHE5GqBpHxkPRViMMmp"
COVER_FEMALE_IMG     = "https://image-hub-cloud.lightningsource.com/2011-04-01/Images/front_cover/x200/sku/9798822989481.jpg?viewkey=cbe6f8e435b911f25bba9f623f1beeb0b63fe7797d202afd9ae0389ba174c2fd"
COVER_MALE_IMG       = "https://image-hub-cloud.lightningsource.com/2011-04-01/Images/front_cover/x200/sku/9798822981973.jpg?viewkey=6a6da316aacd73878e33dcdc077f227bfcc0f50c9d3bade6d01aeae2d7eae624"

# Other formats
AMAZON_PAPERBACK_URL = "https://www.amazon.com/dp/B0FJ2494LH"
AMAZON_HARDCOVER_URL = "https://www.amazon.com/dp/B0FJ23J6JQ"
AMAZON_KINDLE_URL    = "https://www.amazon.com/dp/B0DL7Z7NFL"
AMAZON_AUDIBLE_URL   = "https://www.amazon.com/dp/B0GVWM74FR"


# ── Type-specific one-liner context (used in Day 0 only) ─────────────────────

_CONTEXT = {
    "bookstore":  "I thought it might be something worth knowing about for your shelves.",
    "library":    "I thought it might be a good fit for your collection and community programs.",
    "podcast":    "I thought the conversation might resonate with your listeners.",
    "blog":       "I thought your readers might connect with it.",
    "church":     "I thought it might speak to what your community is already paying attention to.",
    "school":     "I thought it might be useful for your health or nutrition program.",
    "other":      "I wanted to put it on your radar.",
}

def _ctx(bt: str) -> str:
    return _CONTEXT.get(bt, _CONTEXT["other"])


# ── Subject lines ─────────────────────────────────────────────────────────────

_SUBJECTS = {
    "bookstore": [
        "A book your customers are already looking for",
        "What readers are saying about What Is Healthy?",
        "Still here if you want to know more",
        "One last note",
        "Signing off",
    ],
    "library": [
        "A book for your community — What Is Healthy?",
        "A little more about What Is Healthy?",
        "What readers are taking away from this book",
        "Still available if you'd like to know more",
        "Last note from me",
    ],
    "podcast": [
        "Podcast guest — What Is Healthy? with Kortney Lee",
        "A few things listeners tend to respond to",
        "What audiences are saying after these conversations",
        "Still interested in booking?",
        "Signing off",
    ],
    "blog": [
        "What Is Healthy? — would love to connect",
        "A few angles your readers might connect with",
        "What other writers have done with the book",
        "Still here if you're interested",
        "Last note from me",
    ],
    "church": [
        "What Is Healthy? — a book for your community",
        "Why this book resonates with faith communities",
        "What readers are saying",
        "Still here if you'd like to connect",
        "Last note from me",
    ],
    "school": [
        "What Is Healthy? — a book for your students and parents",
        "What schools are finding useful about this book",
        "What students and parents are taking away",
        "Still here if you'd like to know more",
        "Last note from me",
    ],
    "other": [
        "What Is Healthy? — wanted to put this on your radar",
        "A little more about the book",
        "What readers are saying",
        "Still here if you're interested",
        "Last note from Kortney",
    ],
}

def _subject(bt: str, day_index: int) -> str:
    return _SUBJECTS.get(bt, _SUBJECTS["other"])[day_index]


# ── Shared components ─────────────────────────────────────────────────────────

def _wrap(content: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;">
{content}
<tr><td style="padding:16px 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:0 0 6px;font-size:13px;line-height:1.6;color:#6b7280;">
You're receiving this because of your interest in <em>What Is Healthy?</em> or a potential partnership with Vowels.</p>
<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;">
<a href="{UNSUBSCRIBE_URL}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
&middot; Kortney Lee &middot; info@vowels.org
</p></td></tr>
</table></td></tr></table></body></html>"""


def _book_covers() -> str:
    """Two purchase cards — email-safe table, no cover image at top."""
    def card(img: str, link: str, label: str) -> str:
        return (
            f'<td width="50%" style="padding:0 6px 0 0;vertical-align:top;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="border:1px solid #e5e7eb;border-radius:8px;">'
            f'<tr><td align="center" style="padding:10px 10px 6px;">'
            f'<a href="{link}" target="_blank">'
            f'<img src="{img}" width="72" alt="What Is Healthy?" style="display:block;border:0;"/>'
            f'</a></td></tr>'
            f'<tr><td style="padding:0 10px 4px;">'
            f'<p style="margin:0;font-size:12px;font-weight:700;color:#111827;">'
            f'What Is Healthy?</p>'
            f'<p style="margin:1px 0 0;font-size:11px;color:#6b7280;font-style:italic;">'
            f'Kortney O. Lee &mdash; {label}</p></td></tr>'
            f'<tr><td align="center" style="padding:6px 10px 10px;">'
            f'<a href="{link}" target="_blank" '
            f'style="display:inline-block;background:#FEBE10;color:#000000;'
            f'font-size:13px;font-weight:700;text-decoration:none;'
            f'padding:7px 18px;border-radius:8px;">Buy Now</a>'
            f'</td></tr></table></td>'
        )
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 8px;">'
        '<tr>'
        + card(COVER_FEMALE_IMG, INGRAM_FEMALE_URL, "Female cover")
        + card(COVER_MALE_IMG,   INGRAM_MALE_URL,   "Male cover")
        + '</tr></table>'
        '<p style="margin:6px 0 0;font-size:13px;line-height:1.7;color:#6b7280;">'
        f'Also on <a href="{AMAZON_PAPERBACK_URL}" style="color:#1e40af;text-decoration:underline;">Amazon Paperback</a>'
        f' &middot; <a href="{AMAZON_HARDCOVER_URL}" style="color:#1e40af;text-decoration:underline;">Hardcover</a>'
        f' &middot; <a href="{AMAZON_KINDLE_URL}" style="color:#1e40af;text-decoration:underline;">Kindle</a>'
        f' &middot; <a href="{AMAZON_AUDIBLE_URL}" style="color:#1e40af;text-decoration:underline;">Audible</a>'
        '</p>'
    )


def _reply_cta(question: str) -> str:
    return (
        '<table width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td style="padding:20px 0 0;border-top:1px solid #f3f4f6;">'
        f'<p style="margin:0;font-size:15px;line-height:1.7;color:#374151;">'
        f'<strong>{question}</strong> Hit reply &mdash; I read every response.</p>'
        '</td></tr></table>'
    )


def _sig(short: bool = False) -> str:
    if short:
        return '<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">— Kortney</p>'
    return (
        '<p style="margin:0;font-size:16px;line-height:1.8;color:#374151;">'
        'Talk soon,<br/><strong>Kortney Lee</strong><br/>'
        '<span style="font-size:14px;color:#6b7280;">'
        'Author, <em>What Is Healthy?</em></span></p>'
    )


# ── Email templates ───────────────────────────────────────────────────────────

def _render_b2b_day0(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    bt = business_type or "other"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My name is Kortney Lee and I wrote a book called <em>What Is Healthy?</em> I wanted to reach
out personally because {_ctx(bt)}</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
My grandmother was one of the most vibrant people I knew. She was also someone who spent years
living with type 2 diabetes, high blood pressure, and cancer &mdash; three chronic illnesses at
once. She died from the cancer. I spent a long time thinking about whether that was inevitable.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The research I found while writing this book suggests it wasn&rsquo;t. 60% of Americans have at
least one chronic illness. 51% have two or more. These aren&rsquo;t just individual health
failures &mdash; they&rsquo;re a system that was never designed to help most people be well.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
<em>What Is Healthy?</em> is a 264-page, research-backed look at the food industry, label
deception, and what people can realistically do about it &mdash; written for a general audience,
not a medical one. Not a diet book. Just an honest conversation about why this is hard and what
the research actually shows.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
The book &mdash; two cover options:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would love to hear what you think.")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">
{_sig()}
</td></tr>""")


def _render_b2b_day3(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Following up on my note from a few days ago &mdash; wanted to share a little more about what&rsquo;s
in the book.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
The readers who connect with it most are adults 30&ndash;65 who are frustrated with conflicting
health advice and want a research-backed, agenda-free perspective. It covers the food industry,
what&rsquo;s actually in ultra-processed food, how to read a label, the psychology of why
changing eating habits is hard, and what people across different income levels can realistically
do about it.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
It resonates strongly with families, faith communities, and people who feel like the system
hasn&rsquo;t been built with their health in mind. Which, the research suggests, is most people.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
Just wanted to put a little more context behind my last email.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
<p style="margin:20px 0 10px;font-size:15px;font-weight:600;color:#374151;">
Pick up a copy:</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Any questions? I'm happy to talk.")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">
{_sig()}
</td></tr>""")


def _render_b2b_day7(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
A few things readers have shared after finishing the book:</p>
<table width="100%" cellpadding="16" cellspacing="0" style="margin:0 0 20px;background:#f9fafb;border-left:3px solid #e5e7eb;border-radius:0 4px 4px 0;">
<tr><td>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#374151;font-style:italic;">
&ldquo;I went straight to the store and started reading labels differently.&rdquo;</p>
<p style="margin:0 0 12px;font-size:15px;line-height:1.8;color:#374151;font-style:italic;">
&ldquo;I bought copies for my whole family.&rdquo;</p>
<p style="margin:0;font-size:15px;line-height:1.8;color:#374151;font-style:italic;">
&ldquo;This is the book I keep sending people.&rdquo;</p>
</td></tr></table>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
I wrote it for people who are paying attention but don&rsquo;t have the time or money to make
wellness a full-time job. That&rsquo;s most people. I think that&rsquo;s who you work with too.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_reply_cta("Would love to connect if the timing is right.")}
</td></tr>
<tr><td style="padding:20px 40px 32px;">
{_sig()}
</td></tr>""")


def _render_b2b_day14(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 24px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Just checking in &mdash; no pressure at all.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
If you&rsquo;ve had a chance to look at the book and there&rsquo;s something I can help
with &mdash; a conversation, a copy to review, anything &mdash; just hit reply and I&rsquo;m here.</p>
<p style="margin:0 0 0;font-size:16px;line-height:1.85;color:#374151;">
And if the timing just isn&rsquo;t right, that&rsquo;s okay too. No pressure.</p>
</td></tr>
<tr><td style="padding:0 40px 24px;border-top:1px solid #e5e7eb;">
{_book_covers()}
</td></tr>
<tr><td style="padding:20px 40px 32px;border-top:1px solid #e5e7eb;">
{_sig()}
</td></tr>""")


def _render_b2b_day21(first_name: str, business_type: str, company_name: str) -> str:
    name = first_name or "there"
    return _wrap(f"""
<tr><td style="padding:40px 40px 32px;">
<p style="margin:0 0 20px;font-size:16px;line-height:1.8;color:#374151;">Hey {name},</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
Last note from me &mdash; I don&rsquo;t want to fill your inbox.</p>
<p style="margin:0 0 16px;font-size:16px;line-height:1.85;color:#374151;">
If the timing wasn&rsquo;t right or things got busy, no problem at all. The book is there
whenever it makes sense, and so am I.</p>
<p style="margin:0 0 20px;font-size:16px;line-height:1.85;color:#374151;">
info@vowels.org &mdash; reach out any time.</p>
{_book_covers()}
</td></tr>
<tr><td style="padding:0 40px 32px;border-top:1px solid #e5e7eb;">
{_sig(short=True)}
</td></tr>""")


_B2B_SEQUENCE = [
    (0,  0,  "b2b_day0",  lambda bt: _subject(bt, 0), _render_b2b_day0),
    (1,  3,  "b2b_day3",  lambda bt: _subject(bt, 1), _render_b2b_day3),
    (2,  7,  "b2b_day7",  lambda bt: _subject(bt, 2), _render_b2b_day7),
    (3,  14, "b2b_day14", lambda bt: _subject(bt, 3), _render_b2b_day14),
    (4,  21, "b2b_day21", lambda bt: _subject(bt, 4), _render_b2b_day21),
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
    subject = _subject(bt, 0)
    return await _send(email, subject, html)


# ── outreach_leads collection handler ────────────────────────────────────────

_SLUG_TO_BTYPE = {
    "libraries":           "library",
    "bookstores":          "bookstore",
    "christian_blogs":     "blog",
    "book_review_blogs":   "blog",
    "christian_podcasts":  "podcast",
    "book_review_podcasts":"podcast",
}

# Maps nurture_stage → (template_id, render_fn, day_index)
_OUTREACH_STAGES = [
    (0, "outreach_day0",  _render_b2b_day0,  0),
    (1, "outreach_day3",  _render_b2b_day3,  1),
    (2, "outreach_day7",  _render_b2b_day7,  2),
    (3, "outreach_day14", _render_b2b_day14, 3),
    (4, "outreach_day21", _render_b2b_day21, 4),
]
_OUTREACH_DELAYS = [0, 3, 7, 14, 21]


async def process_outreach_leads(batch: int = 100) -> dict:
    """
    Cron: send emails to outreach_leads collection.
    - Stage 0 (new): reads remarketing_status='new', sends Day 0
    - Stage 1-4: reads nurture_next_at <= now, sends follow-up
    Returns counts of sent/skipped/errors.
    """
    from datetime import datetime, timezone, timedelta
    from google.cloud import firestore

    db  = firestore.AsyncClient(project=os.getenv("GCP_PROJECT", "wihy-ai"))
    now = datetime.now(timezone.utc)
    sent = skipped = errors = 0
    COLL = "outreach_leads"

    # ── Day 0: new leads not yet contacted ────────────────────────────────────
    new_query = (
        db.collection(COLL)
        .where("remarketing_status", "==", "new")
        .where("sequence_status", "==", "active")
        .limit(batch)
    )
    async for doc in new_query.stream():
        d = doc.to_dict()
        if d.get("do_not_contact") or d.get("sendgrid_suppressed") or d.get("unsubscribed"):
            skipped += 1
            continue
        email      = d.get("email", "")
        first_name = d.get("first_name", "")
        slug       = d.get("target_slug", "other")
        bt         = _SLUG_TO_BTYPE.get(slug, "other")
        company    = d.get("company_name", "")
        try:
            html    = _render_b2b_day0(first_name, bt, company)
            subject = _subject(bt, 0)
            ok      = await _send(email, subject, html)
            update  = {
                "remarketing_status": "contacted",
                "nurture_stage": 1,
                "nurture_next_at": now + timedelta(days=3),
                "outreach_day0_sent_at": now,
            }
            await doc.reference.update(update)
            sent += 1 if ok else 0
            errors += 0 if ok else 1
        except Exception as e:
            logger.error("Outreach Day0 error %s: %s", email, e)
            errors += 1

    # ── Day 1-4: follow-up emails due ─────────────────────────────────────────
    followup_query = (
        db.collection(COLL)
        .where("remarketing_status", "==", "contacted")
        .where("sequence_status",    "==", "active")
        .where("nurture_next_at",    "<=", now)
        .limit(batch)
    )
    async for doc in followup_query.stream():
        d = doc.to_dict()
        if d.get("do_not_contact") or d.get("sendgrid_suppressed") or d.get("unsubscribed"):
            skipped += 1
            continue
        stage      = d.get("nurture_stage", 1)
        if stage >= len(_OUTREACH_STAGES):
            await doc.reference.update({"sequence_status": "completed"})
            continue
        _, tmpl_id, render_fn, day_idx = _OUTREACH_STAGES[stage]
        email      = d.get("email", "")
        first_name = d.get("first_name", "")
        slug       = d.get("target_slug", "other")
        bt         = _SLUG_TO_BTYPE.get(slug, "other")
        company    = d.get("company_name", "")
        try:
            html    = render_fn(first_name, bt, company)
            subject = _subject(bt, day_idx)
            ok      = await _send(email, subject, html)
            next_stage = stage + 1
            update: dict = {
                "nurture_stage": next_stage,
                f"{tmpl_id}_sent_at": now,
            }
            if next_stage < len(_OUTREACH_STAGES):
                update["nurture_next_at"] = now + timedelta(days=_OUTREACH_DELAYS[next_stage])
            else:
                update["sequence_status"] = "completed"
            await doc.reference.update(update)
            sent += 1 if ok else 0
            errors += 0 if ok else 1
        except Exception as e:
            logger.error("Outreach followup error %s: %s", email, e)
            errors += 1

    return {"sent": sent, "skipped": skipped, "errors": errors, "ran_at": now.isoformat()}


async def process_pending_b2b_nurture() -> dict:
    """Cron: send pending B2B nurture emails."""
    from datetime import datetime, timezone, timedelta
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

        _, days, template_id, subject_fn, render_fn = _B2B_SEQUENCE[stage]
        email       = d.get("email", "")
        first_name  = d.get("first_name", "")
        business_type = d.get("business_type", "other")
        company_name  = d.get("company_name", "")

        try:
            html    = render_fn(first_name, business_type, company_name)
            subject = subject_fn(business_type)
            ok      = await _send(email, subject, html)

            next_stage = stage + 1
            update: dict = {
                "nurture_stage": next_stage,
                f"nurture_{template_id}_sent_at": now,
            }
            if next_stage < len(_B2B_SEQUENCE):
                update["nurture_next_at"] = now + timedelta(days=_B2B_SEQUENCE[next_stage][1])
                update["sequence_status"] = "active"
            else:
                update["sequence_status"] = "completed"

            await doc.reference.update(update)
            sent += 1 if ok else 0
            errors += 0 if ok else 1
        except Exception as e:
            logger.error("B2B nurture error for %s: %s", email, e)
            errors += 1

    return {"sent": sent, "skipped": skipped, "errors": errors, "ran_at": now.isoformat()}
