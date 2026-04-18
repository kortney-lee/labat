"""
Launch Nurture Email Service.

Drip campaign for WIHY and Community Groceries pre-launch signups.
Based on the book nurture service pattern with separate branding and
separate sequencing.

Schedule per lead:
  Day 0: welcome             (sent immediately at signup)
  Day 3: feature_preview     (what's coming)
  Day 7: behind_the_scenes   (the mission / why we built this)
  Day 14: countdown          (launch is near)
  Day 21: launch_day         (it's live — go sign up)
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()

APPLE_BADGE_FILENAME = "AppStore_download.png"
GOOGLE_BADGE_FILENAME = "GetItOnGooglePlay_Badge_Web_color_English.png"

EMAIL_FONT_STACK = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
    "'Helvetica Neue',Arial,sans-serif"
)

BODY_STYLE = (
    f"margin:0;padding:0;background:#f5f5f5;font-family:{EMAIL_FONT_STACK};"
)
OUTER_TABLE_STYLE = "background:#f5f5f5;padding:32px 16px;"
CARD_STYLE = (
    "max-width:560px;width:100%;background:#ffffff;border-radius:12px;"
    "overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);"
)
HEADER_CELL_STYLE = "padding:20px 32px;text-align:center;"
FOOTER_CELL_STYLE = "padding:24px 32px;border-top:1px solid #f0f0f0;"
FOOTER_TEXT_STYLE = (
    "margin:0;color:#9ca3af;font-size:12px;line-height:1.6;text-align:center;"
)
CONTENT_CELL_STYLE = "padding:40px 32px 16px;"
BODY_TEXT_STYLE = (
    "margin:0 0 20px;font-size:17px;line-height:1.8;color:#374151;"
)
BODY_END_STYLE = "margin:20px 0 0;font-size:17px;line-height:1.8;color:#374151;"
BODY_SINGLE_STYLE = "margin:0;font-size:17px;line-height:1.8;color:#374151;"
LIST_STYLE = (
    "margin:0 0 24px;padding-left:20px;font-size:16px;line-height:2.2;"
    "color:#374151;"
)
CENTER_ROW_STYLE = "padding:0 32px 16px;text-align:center;"
BOTTOM_ROW_STYLE = "padding:16px 32px 32px;"
BADGE_TABLE_STYLE = "margin:0 auto;"
BADGE_CELL_STYLE = "padding:0 8px 12px;"
APPLE_BADGE_STYLE = "display:block;width:160px;max-width:100%;height:auto;border:0;"
GOOGLE_BADGE_STYLE = (
    "display:block;width:180px;max-width:100%;height:auto;border:0;"
)
WEB_LINK_STYLE = "color:#1e40af;"


BRAND_CONFIG = {
    "wihy": {
        "from_email": "kortney@wihy.ai",
        "from_name": "WIHY",
        "app_name": "WIHY AI",
        "domain": "https://wihy.ai",
        "android_url": (
            "https://play.google.com/store/apps/details?id=com.wihy.app"
        ),
        "ios_url": "https://apps.apple.com/us/app/wihy-ai/id6758858368",
        "accent": "#fa5f06",
        "tagline": "What Is Healthy for You",
        "logo_url": (
            "https://storage.googleapis.com/wihy-web-assets/images/"
            "Logo_wihy.png"
        ),
        "apple_badge_url": (
            "https://storage.googleapis.com/wihy-web-assets/images/badges/"
            f"{APPLE_BADGE_FILENAME}"
        ),
        "google_badge_url": (
            "https://storage.googleapis.com/wihy-web-assets/images/badges/"
            f"{GOOGLE_BADGE_FILENAME}"
        ),
        "unsubscribe_url": "https://wihy.ai/unsubscribe",
        "description": (
            "WIHY helps you understand what's really in your food. "
            "Scan products, capture meals, get answers to your health "
            "questions — all backed by 48M+ research articles and 4.1M+ "
            "products analyzed."
        ),
        "features": [
            "Scan any food product and see what's really inside",
            "AI-powered meal planning that fits YOUR health goals",
            "Ask any health or nutrition question — grounded in real research",
            "Capture what you eat and understand how it affects your body",
        ],
    },
    "communitygroceries": {
        "from_email": "sales@communitygroceries.com",
        "from_name": "Community Groceries",
        "app_name": "Community Groceries",
        "domain": "https://communitygroceries.com",
        "android_url": (
            "https://play.google.com/store/apps/details?"
            "id=app.communitygroceries.mobile"
        ),
        "ios_url": (
            "https://apps.apple.com/us/app/community-groceries/"
            "id6760566970"
        ),
        "accent": "#166534",
        "tagline": "Connecting Families Through Food",
        "logo_url": (
            "https://storage.googleapis.com/cg-web-assets/images/Logo_CG.png"
        ),
        "apple_badge_url": (
            "https://storage.googleapis.com/cg-web-assets/images/badges/"
            f"{APPLE_BADGE_FILENAME}"
        ),
        "google_badge_url": (
            "https://storage.googleapis.com/cg-web-assets/images/badges/"
            f"{GOOGLE_BADGE_FILENAME}"
        ),
        "unsubscribe_url": "https://communitygroceries.com/unsubscribe",
        "description": (
            "Community Groceries connects families through food — affordable "
            "meal plans, smart shopping lists, and recipes built for real "
            "families with real budgets."
        ),
        "features": [
            "Weekly meal plans designed for families",
            "Smart shopping lists that save you money",
            "Recipes your kids will actually eat",
            "Community-powered food tips and local recommendations",
        ],
    },
}

ALL_LAUNCH_TEMPLATES = [
    (0, 0, "welcome", "Welcome to {brand_name}, {first_name}!"),
    (1, 3, "feature_preview", "Here's what's coming, {first_name}"),
    (2, 7, "behind_the_scenes", "Why we're building {brand_name}"),
    (3, 14, "countdown", "{first_name}, we're almost ready"),
    (4, 21, "launch_day", "{brand_name} is LIVE — come check it out!"),
]

LAUNCH_SEQUENCE = [
    (0, 0, "welcome", "Welcome to {brand_name}, {first_name}!"),
    (1, 3, "feature_preview", "Here's what's coming, {first_name}"),
    (2, 14, "countdown", "{first_name}, we're almost ready"),
    (3, 21, "launch_day", "{brand_name} is LIVE — come check it out!"),
]


def _html_join(*lines: str) -> str:
    return "\n".join(lines)


def _paragraph(text: str) -> str:
    return _html_join(
        f'<p style="{BODY_TEXT_STYLE}">',
        text,
        "</p>",
    )


def _paragraph_end(text: str) -> str:
    return _html_join(
        f'<p style="{BODY_END_STYLE}">',
        text,
        "</p>",
    )


def _paragraph_single(text: str) -> str:
    return _html_join(
        f'<p style="{BODY_SINGLE_STYLE}">',
        text,
        "</p>",
    )


def _email_wrap(content: str, brand: str) -> str:
    cfg = BRAND_CONFIG.get(brand, BRAND_CONFIG["wihy"])
    logo = cfg["logo_url"]
    unsub = cfg["unsubscribe_url"]
    name = cfg["from_name"]

    return _html_join(
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="UTF-8"/>',
        (
            '<meta name="viewport" '
            'content="width=device-width,initial-scale=1.0"/>'
        ),
        "</head>",
        f'<body style="{BODY_STYLE}">',
        (
            '<table width="100%" cellpadding="0" cellspacing="0" '
            f'style="{OUTER_TABLE_STYLE}">'
        ),
        '<tr><td align="center">',
        (
            '<table width="560" cellpadding="0" cellspacing="0" '
            f'style="{CARD_STYLE}">'
        ),
        f'<tr><td style="{HEADER_CELL_STYLE}">',
        (
            f'<img src="{logo}" alt="{name}" '
            'style="height:40px;vertical-align:middle;" />'
        ),
        "</td></tr>",
        content,
        f'<tr><td style="{FOOTER_CELL_STYLE}">',
        f'<p style="{FOOTER_TEXT_STYLE}">',
        f'You signed up for launch updates from {name}.<br/>',
        (
            f'<a href="{unsub}" '
            'style="color:#9ca3af;text-decoration:underline;">'
            'Unsubscribe</a>'
        ),
        "</p></td></tr>",
        "</table></td></tr></table></body></html>",
    )


def _cta_button(label: str, url: str, color: str = "#1e40af") -> str:
    return (
        f'<a href="{url}" '
        f'style="display:inline-block;background:{color};color:#ffffff;'
        'font-size:16px;font-weight:700;text-decoration:none;'
        f'padding:14px 32px;border-radius:8px;">{label}</a>'
    )


def _app_download_buttons(brand: str) -> str:
    cfg = BRAND_CONFIG.get(brand, BRAND_CONFIG["wihy"])
    apple_alt = f"Download {cfg['app_name']} on the App Store"
    google_alt = f"Get {cfg['app_name']} on Google Play"

    return _html_join(
        (
            '<table role="presentation" cellpadding="0" cellspacing="0" '
            'border="0" align="center" '
            f'style="{BADGE_TABLE_STYLE}">'
        ),
        "<tr>",
        f'<td align="center" style="{BADGE_CELL_STYLE}">',
        f'<a href="{cfg["ios_url"]}" style="text-decoration:none;">',
        (
            f'<img src="{cfg["apple_badge_url"]}" alt="{apple_alt}" '
            'width="160" '
            f'style="{APPLE_BADGE_STYLE}" />'
        ),
        "</a>",
        "</td>",
        f'<td align="center" style="{BADGE_CELL_STYLE}">',
        f'<a href="{cfg["android_url"]}" style="text-decoration:none;">',
        (
            f'<img src="{cfg["google_badge_url"]}" alt="{google_alt}" '
            'width="180" '
            f'style="{GOOGLE_BADGE_STYLE}" />'
        ),
        "</a>",
        "</td>",
        "</tr>",
        "</table>",
    )


def _render_welcome(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    content = _html_join(
        f'<tr><td style="{CONTENT_CELL_STYLE}">',
        _paragraph(f"Hey {first_name},"),
        _paragraph(
            "Thanks for signing up — you're now on the list for early access "
            f"to <strong>{cfg['from_name']}</strong>."
        ),
        _paragraph(cfg["description"]),
        _paragraph(
            "We'll keep you posted as we get closer to launch. In the "
            "meantime, here's what you can expect from us — no spam, just "
            "real updates."
        ),
        _paragraph_end(f"Talk soon,<br/>The {cfg['from_name']} Team"),
        "</td></tr>",
    )
    return _email_wrap(content, brand)


def _render_feature_preview(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    features_html = "".join(f"<li>{feature}</li>" for feature in cfg["features"])
    content = _html_join(
        f'<tr><td style="{CONTENT_CELL_STYLE}">',
        _paragraph(f"Hey {first_name},"),
        _paragraph(
            "We wanted to give you a sneak peek at what we're building. "
            f"Here's what you'll get when {cfg['from_name']} launches:"
        ),
        f'<ul style="{LIST_STYLE}">',
        features_html,
        "</ul>",
        _paragraph(
            "We're putting the finishing touches on everything now. You'll "
            "be among the first to know when it's ready."
        ),
        _paragraph_end(f"— The {cfg['from_name']} Team"),
        "</td></tr>",
    )
    return _email_wrap(content, brand)


def _render_behind_the_scenes(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    if brand == "wihy":
        mission = (
            "The average doctor gets 19 hours of nutrition training in "
            "medical school. Meanwhile, the food industry spends $14 billion "
            "a year convincing you their products are healthy. We built WIHY "
            "because the system failed you — and the information to fix it "
            "already exists. We just made it usable."
        )
    else:
        mission = (
            "We started Community Groceries because we saw families "
            "struggling — not because they didn't care about eating well, "
            "but because the system makes it hard. Healthy food is "
            "expensive, meal planning takes time, and most apps aren't built "
            "for real families. We're changing that."
        )

    content = _html_join(
        f'<tr><td style="{CONTENT_CELL_STYLE}">',
        _paragraph(f"Hey {first_name},"),
        _paragraph(f"I wanted to share why we're building {cfg['from_name']}"),
        _paragraph(mission),
        _paragraph(
            f"That's what {cfg['from_name']} is about. And you being on this "
            "list means a lot to us."
        ),
        _paragraph_end(f"More soon,<br/>The {cfg['from_name']} Team"),
        "</td></tr>",
    )
    return _email_wrap(content, brand)


def _render_countdown(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    content = _html_join(
        f'<tr><td style="{CONTENT_CELL_STYLE}">',
        _paragraph(f"Hey {first_name},"),
        _paragraph(
            f"We're getting really close now. {cfg['from_name']} is almost "
            "ready to go live."
        ),
        _paragraph(
            "As someone who signed up early, you'll get access before anyone "
            "else. We'll send you a direct link the moment we launch — no "
            "waiting, no waitlist."
        ),
        _paragraph(
            "In the meantime, if you have friends or family who'd be "
            "interested, feel free to send them to our site:"
        ),
        "</td></tr>",
        f'<tr><td style="{CENTER_ROW_STYLE}">',
        _cta_button(
            f"Share {cfg['from_name']}",
            cfg["domain"],
            cfg["accent"],
        ),
        "</td></tr>",
        f'<tr><td style="{BOTTOM_ROW_STYLE}">',
        _paragraph_single("Next email = launch day."),
        _paragraph_end(f"— The {cfg['from_name']} Team"),
        "</td></tr>",
    )
    return _email_wrap(content, brand)


def _render_launch_day(first_name: str, brand: str, **kw) -> str:
    cfg = BRAND_CONFIG[brand]
    web_link = (
        f'{cfg["from_name"]} at '
        f'<a href="{cfg["domain"]}" style="{WEB_LINK_STYLE}">'
        f'{cfg["domain"]}</a>.'
    )
    content = _html_join(
        f'<tr><td style="{CONTENT_CELL_STYLE}">',
        _paragraph(f"{first_name} — it's here."),
        _paragraph(
            f"<strong>{cfg['from_name']}</strong> is officially live. You "
            "signed up early, so here are your direct download links:"
        ),
        "</td></tr>",
        f'<tr><td style="{CENTER_ROW_STYLE}">',
        _app_download_buttons(brand),
        "</td></tr>",
        f'<tr><td style="{BOTTOM_ROW_STYLE}">',
        _paragraph(f"{cfg['tagline']} — and now it's yours to use."),
        _paragraph(f"Prefer web? You can also use {web_link}"),
        _paragraph(
            "Thanks for believing in this before it existed. We built it for "
            "people like you."
        ),
        _paragraph_end(f"Let's go,<br/>The {cfg['from_name']} Team"),
        "</td></tr>",
    )
    return _email_wrap(content, brand)


_RENDERERS = {
    "welcome": _render_welcome,
    "feature_preview": _render_feature_preview,
    "behind_the_scenes": _render_behind_the_scenes,
    "countdown": _render_countdown,
    "launch_day": _render_launch_day,
}


def render_launch_html(
    template_id: str,
    first_name: str,
    brand: str = "wihy",
) -> str:
    """Render launch template HTML without sending email."""
    renderer = _RENDERERS.get(template_id)
    if not renderer:
        raise ValueError(f"Unknown launch template: {template_id}")
    normalized_name = (first_name or "there").strip() or "there"
    return renderer(normalized_name, brand=brand)


def export_launch_templates_local(
    output_dir: str,
    first_name: str = "Kortney",
    brands: Optional[list[str]] = None,
    keep_active_only: bool = False,
) -> dict:
    """Render launch templates to local HTML files for visual review."""
    selected_brands = brands or ["wihy", "communitygroceries"]
    sequence = LAUNCH_SEQUENCE if keep_active_only else ALL_LAUNCH_TEMPLATES

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    results: dict[str, dict[str, str]] = {}

    for brand in selected_brands:
        if brand not in BRAND_CONFIG:
            continue

        brand_dir = out / brand
        brand_dir.mkdir(parents=True, exist_ok=True)

        rendered: dict[str, str] = {}
        for idx, _days, template_id, _subject in sequence:
            html = render_launch_html(
                template_id=template_id,
                first_name=first_name,
                brand=brand,
            )
            filename = f"{idx:02d}_{template_id}.html"
            path = brand_dir / filename
            path.write_text(html, encoding="utf-8")
            rendered[template_id] = str(path)

        results[brand] = rendered

    return results


async def send_launch_email(
    to_email: str,
    first_name: str,
    template_id: str,
    subject: str,
    brand: str = "wihy",
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
    rendered_subject = (
        subject.replace("{first_name}", name).replace(
            "{brand_name}",
            cfg["from_name"],
        )
    )
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
        "custom_args": {
            "template_id": template_id,
            "lead_email": to_email,
            "brand": brand,
        },
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
                logger.info(
                    "Launch email [%s] sent to %s (brand=%s)",
                    template_id,
                    to_email,
                    brand,
                )
                return True

            logger.error(
                "SendGrid launch error %s: %s",
                resp.status_code,
                resp.text,
            )
            return False
        except Exception as exc:
            logger.error("Launch email delivery failed: %s", exc)
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
    from src.services.launch_leads_service import advance_nurture, get_pending_nurture

    pending = await get_pending_nurture(limit=200)
    sent = 0
    for lead in pending:
        stage = lead.get("nurture_stage", 0)
        brand = lead.get("brand", "wihy")
        email = lead["email"]
        first_name = lead.get("first_name", "")

        seq_entry = None
        next_entry = None
        for seq_stage, days, template_id, subject in LAUNCH_SEQUENCE:
            if seq_stage == stage:
                seq_entry = (seq_stage, days, template_id, subject)
            elif seq_stage == stage + 1:
                next_entry = (seq_stage, days, template_id, subject)

        if not seq_entry:
            await advance_nurture(lead["id"], stage)
            continue

        _, _, template_id, subject = seq_entry
        ok = await send_launch_email(
            email,
            first_name,
            template_id,
            subject,
            brand,
        )
        if ok:
            sent += 1
            if next_entry:
                next_stage, next_days, _, _ = next_entry
                signup = lead.get("created_at", datetime.now(timezone.utc))
                if hasattr(signup, "timestamp"):
                    next_at = signup + timedelta(days=next_days)
                else:
                    next_at = datetime.now(timezone.utc) + timedelta(
                        days=next_days - (seq_entry[1] or 0)
                    )
                await advance_nurture(lead["id"], next_stage, next_at)
            else:
                await advance_nurture(lead["id"], stage + 1)

    logger.info("Launch nurture processed: %d emails sent", sent)
    return sent
