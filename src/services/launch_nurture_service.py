"""
Launch Nurture Email Service
Drip campaign for WIHY and Community Groceries pre-launch signups.
Based on the book nurture service pattern — separate sequence, separate branding.

Schedule per lead:
  Day 0: welcome             (sent immediately at signup)
  Day 3: feature_preview     (what's coming)
  Day 7: behind_the_scenes   (the mission / why we built this)
  Day 14: countdown          (launch is near)
  Day 21: launch_day         (it's live — go sign up)
"""

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()

# ── Brand configuration ───────────────────────────────────────────────────────

BRAND_CONFIG = {
    "wihy": {
        "from_email": "kortney@wihy.ai",
        "from_name": "WIHY",
        "domain": "https://wihy.ai",
        "accent": "#fa5f06",
        "tagline": "What Is Healthy for You",
        "logo_url": "https://storage.googleapis.com/wihy-web-assets/images/Logo_wihy.png",
        "unsubscribe_url": "https://wihy.ai/unsubscribe",
        "description": (
            "WIHY helps you understand what's really in your food. "
            "Scan products, track meals, get answers to your health questions — "
            "all backed by 48M+ research articles and 4.1M+ products analyzed."
        ),
        "features": [
            "Scan any food product and see what's really inside",
            "AI-powered meal planning that fits YOUR health goals",
            "Ask any health or nutrition question — grounded in real research",
            "Track what you eat and see how it affects your body",
        ],
    },
    "communitygroceries": {
        "from_email": "sales@communitygroceries.com",
        "from_name": "Community Groceries",
        "domain": "https://communitygroceries.com",
        "accent": "#166534",
        "tagline": "Connecting Families Through Food",
        "logo_url": "https://storage.googleapis.com/cg-web-assets/images/Logo_CG.png",
        "unsubscribe_url": "https://communitygroceries.com/unsubscribe",
        "description": (
            "Community Groceries connects families through food — "
            "affordable meal plans, smart shopping lists, and recipes "
            "built for real families with real budgets."
        ),
        "features": [
            "Weekly meal plans designed for families",
            "Smart shopping lists that save you money",
            "Recipes your kids will actually eat",
            "Community-powered food tips and local recommendations",
        ],
    },
}

# Nurture sequence: (stage, days_after_signup, template_id, subject_template)
LAUNCH_SEQUENCE = [
    (0, 0,  "welcome",            "Welcome to {brand_name}, {first_name}!"),
    (1, 3,  "feature_preview",    "Here's what's coming, {first_name}"),
    (2, 7,  "behind_the_scenes",  "Why we're building {brand_name}"),
    (3, 14, "countdown",          "{first_name}, we're almost ready"),
    (4, 21, "launch_day",         "{brand_name} is LIVE — come check it out!"),
]


# ── Email wrapper ─────────────────────────────────────────────────────────────

def _email_wrap(content: str, brand: str) -> str:
    cfg = BRAND_CONFIG.get(brand, BRAND_CONFIG["wihy"])
    accent = cfg["accent"]
    logo = cfg["logo_url"]
    unsub = cfg["unsubscribe_url"]
    name = cfg["from_name"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<tr><td style="background:{accent};padding:20px 32px;text-align:center;">
<img src="{logo}" alt="{name}" style="height:40px;vertical-align:middle;" />
</td></tr>
{content}
<tr><td style="padding:24px 32px;border-top:1px solid #f0f0f0;">
<p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.6;text-align:center;">
You signed up for launch updates from {name}.<br/>
<a href="{unsub}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a>
</p></td></tr>
</table></td></tr></table></body></html>"""


def _cta_button(label: str, url: str, color: str = "#1e40af") -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;'
        f'font-size:16px;font-weight:700;text-decoration:none;padding:14px 32px;'
        f'border-radius:8px;">{label}</a>'
    )


# ── Template builders ─────────────────────────────────────────────────────────

def _render_welcome(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 16px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Thanks for signing up — you're now on the list for early access to <strong>{cfg['from_name']}</strong>.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
{cfg['description']}</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
We'll keep you posted as we get closer to launch. In the meantime, here's what you can expect from us — no spam, just real updates.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Talk soon,<br/>The {cfg['from_name']} Team</p>
</td></tr>""", brand)


def _render_feature_preview(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    features_html = "".join(f"<li>{f}</li>" for f in cfg["features"])
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 16px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
We wanted to give you a sneak peek at what we're building. Here's what you'll get when {cfg['from_name']} launches:</p>
<ul style="margin:0 0 24px;padding-left:20px;font-size:16px;line-height:2.2;color:#374151;">
{features_html}
</ul>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
We're putting the finishing touches on everything now. You'll be among the first to know when it's ready.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
— The {cfg['from_name']} Team</p>
</td></tr>""", brand)


def _render_behind_the_scenes(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    if brand == "wihy":
        mission = (
            "The average doctor gets 19 hours of nutrition training in medical school. "
            "Meanwhile, the food industry spends $14 billion a year convincing you their products are healthy. "
            "We built WIHY because the system failed you — and the information to fix it already exists. "
            "We just made it usable."
        )
    else:
        mission = (
            "We started Community Groceries because we saw families struggling — "
            "not because they didn't care about eating well, but because the system makes it hard. "
            "Healthy food is expensive, meal planning takes time, and most apps aren't built for real families. "
            "We're changing that."
        )
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 16px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
I wanted to share why we're building {cfg['from_name']}.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
{mission}</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
That's what {cfg['from_name']} is about. And you being on this list means a lot to us.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
More soon,<br/>The {cfg['from_name']} Team</p>
</td></tr>""", brand)


def _render_countdown(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 16px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Hey {first_name},</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
We're getting really close now. {cfg['from_name']} is almost ready to go live.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
As someone who signed up early, you'll get access before anyone else. We'll send you a direct link the moment we launch — no waiting, no waitlist.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
In the meantime, if you have friends or family who'd be interested, feel free to send them to our site:</p>
</td></tr>
<tr><td style="padding:0 32px 16px;text-align:center;">
{_cta_button(f"Share {cfg['from_name']}", cfg['domain'], cfg['accent'])}
</td></tr>
<tr><td style="padding:16px 32px 32px;">
<p style="margin:0;font-size:17px;line-height:1.8;color:#374151;">
Next email = launch day.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
— The {cfg['from_name']} Team</p>
</td></tr>""", brand)


def _render_launch_day(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    return _email_wrap(f"""
<tr><td style="padding:40px 32px 16px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
{first_name} — it's here.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
<strong>{cfg['from_name']}</strong> is officially live. You signed up early, so here's your direct access:</p>
</td></tr>
<tr><td style="padding:0 32px 16px;text-align:center;">
{_cta_button(f"Go to {cfg['from_name']}", cfg['domain'], cfg['accent'])}
</td></tr>
<tr><td style="padding:16px 32px 32px;">
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
{cfg['tagline']} — and now it's yours to use.</p>
<p style="margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;">
Thanks for believing in this before it existed. We built it for people like you.</p>
<p style="margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;">
Let's go,<br/>The {cfg['from_name']} Team</p>
</td></tr>""", brand)


# Template renderer lookup
_RENDERERS = {
    "welcome": _render_welcome,
    "feature_preview": _render_feature_preview,
    "behind_the_scenes": _render_behind_the_scenes,
    "countdown": _render_countdown,
    "launch_day": _render_launch_day,
}


# ── Sending ───────────────────────────────────────────────────────────────────

async def send_launch_email(
    to_email: str, first_name: str, template_id: str,
    subject: str, brand: str = "wihy",
) -> bool:
    """Send a single launch nurture email via SendGrid."""
    if not SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping launch email")
        return False

    renderer = _RENDERERS.get(template_id)
    if not renderer:
        logger.error("Unknown launch template: %s", template_id)
        return False

    cfg = BRAND_CONFIG.get(brand, BRAND_CONFIG["wihy"])
    name = first_name or "there"
    rendered_subject = subject.replace("{first_name}", name).replace("{brand_name}", cfg["from_name"])
    html_body = renderer(name, brand=brand)

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": cfg["from_email"], "name": cfg["from_name"]},
        "subject": rendered_subject,
        "content": [{"type": "text/html", "value": html_body}],
        "tracking_settings": {
            "click_tracking": {"enable": True, "enable_text": False},
            "open_tracking": {"enable": True},
        },
        "categories": ["launch_nurture", template_id, brand],
        "custom_args": {"template_id": template_id, "lead_email": to_email, "brand": brand},
    }

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201, 202):
                logger.info("Launch email [%s] sent to %s (brand=%s)", template_id, to_email, brand)
                return True
            else:
                logger.error("SendGrid launch error %s: %s", resp.status_code, resp.text)
                return False
        except Exception as e:
            logger.error("Launch email delivery failed: %s", e)
            return False


async def trigger_welcome(email: str, first_name: str, brand: str) -> bool:
    """Send the Day 0 welcome email immediately."""
    return await send_launch_email(
        to_email=email,
        first_name=first_name,
        template_id="welcome",
        subject="Welcome to {brand_name}, {first_name}!",
        brand=brand,
    )


async def process_pending_launch_nurture() -> int:
    """Process all pending launch nurture emails. Called by cron."""
    from src.services.launch_leads_service import get_pending_nurture, advance_nurture

    pending = await get_pending_nurture(limit=200)
    sent = 0
    for lead in pending:
        stage = lead.get("nurture_stage", 0)
        brand = lead.get("brand", "wihy")
        email = lead["email"]
        first_name = lead.get("first_name", "")

        # Find the next email in the sequence
        seq_entry = None
        next_entry = None
        for s, _days, tid, subj in LAUNCH_SEQUENCE:
            if s == stage:
                seq_entry = (s, _days, tid, subj)
            elif s == stage + 1:
                next_entry = (s, _days, tid, subj)

        if not seq_entry:
            # Already completed — mark done
            await advance_nurture(lead["id"], stage)
            continue

        _, _, template_id, subject = seq_entry
        ok = await send_launch_email(email, first_name, template_id, subject, brand)
        if ok:
            sent += 1
            if next_entry:
                next_stage, next_days, _, _ = next_entry
                # Schedule the next email based on days offset from signup
                signup = lead.get("created_at", datetime.now(timezone.utc))
                if hasattr(signup, 'timestamp'):
                    next_at = signup + timedelta(days=next_days)
                else:
                    next_at = datetime.now(timezone.utc) + timedelta(days=next_days - (seq_entry[1] or 0))
                await advance_nurture(lead["id"], next_stage, next_at)
            else:
                # Last email — mark completed
                await advance_nurture(lead["id"], stage + 1)

    logger.info("Launch nurture processed: %d emails sent", sent)
    return sent
