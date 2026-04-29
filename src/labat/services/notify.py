"""
labat/services/notify.py — Shared notification helper for all WIHY agents.

Sends email notifications directly via SendGrid to kortney@wihy.ai.
Campaign strategy details (targeting, copy, funnel, budget) are included
in a clean HTML email.

Usage (any agent):
    from src.labat.services.notify import send_notification

    await send_notification(
        agent="alex",
        severity="info",
        title="Photo ad created — Trinity Book",
        message="Photo ad pipeline complete for vowels.",
        service="labat",
        details={"campaign_id": "120243213143990272", ...},
    )
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("wihy.notify")

_SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
_FROM_EMAIL = os.getenv("NOTIFICATION_FROM_EMAIL", "noreply@wihy.ai")
_FROM_NAME = os.getenv("NOTIFICATION_FROM_NAME", "WIHY Agents")
_TO_EMAIL = os.getenv("NOTIFICATION_TO_EMAIL", "kortney@wihy.ai")
_TIMEOUT = 15.0


_SEVERITY_COLORS = {
    "critical": ("#dc2626", "#fef2f2", "#991b1b"),
    "warning":  ("#d97706", "#fffbeb", "#92400e"),
    "info":     ("#2563eb", "#eff6ff", "#1e40af"),
    "success":  ("#16a34a", "#f0fdf4", "#166534"),
}


def _severity_badge(severity: str) -> str:
    bg, _, _ = _SEVERITY_COLORS.get(severity, ("#6b7280", "#f9fafb", "#374151"))
    return (
        f'<span style="display:inline-block;padding:4px 14px;border-radius:20px;'
        f'background:{bg};color:#fff;font-size:11px;font-weight:700;'
        f'letter-spacing:0.5px;text-transform:uppercase;">{severity}</span>'
    )


def _format_value(val: Any, _depth: int = 0) -> str:
    """Render a detail value as styled HTML.

    - Flat dicts  -> mini key-value table
    - Lists       -> bullet list (or mini table if list-of-dicts)
    - Primitives  -> styled text / link
    - Deep nests (>3) -> fall back to <pre> JSON
    """
    if isinstance(val, dict):
        # Keep nested status/service objects readable as tables.
        # Only fall back to JSON for very deep structures.
        if _depth > 2 or not val:
            formatted = json.dumps(val, indent=2, default=str)
            return (
                f'<pre style="margin:0;padding:10px 12px;background:#f8fafc;'
                f'border:1px solid #e2e8f0;border-radius:6px;font-family:'
                f"'SF Mono',Menlo,Consolas,monospace;font-size:12px;"
                f'line-height:1.5;white-space:pre-wrap;word-break:break-word;'
                f'color:#334155;">{formatted}</pre>'
            )
        rows = ""
        for k, v in val.items():
            label = k.replace("_", " ").title()
            rows += (
                f'<tr>'
                f'<td style="padding:6px 12px;color:#64748b;font-size:12px;'
                f'font-weight:600;vertical-align:top;white-space:nowrap;width:150px;">{label}</td>'
                f'<td style="padding:6px 12px;font-size:13px;">{_format_value(v, _depth + 1)}</td>'
                f'</tr>'
            )
        return (
            f'<table style="width:100%;border-collapse:collapse;margin:4px 0;'
            f'border:1px solid #e2e8f0;border-radius:6px;overflow:hidden;'
            f'background:#f8fafc;">{rows}</table>'
        )
    if isinstance(val, list):
        if not val:
            return '<span style="color:#94a3b8;">—</span>'
        items = "".join(
            f'<li style="padding:2px 0;color:#334155;font-size:13px;">'
            f'{_format_value(v, _depth + 1)}</li>'
            for v in val
        )
        return f'<ul style="margin:4px 0;padding-left:20px;">{items}</ul>'
    text = str(val) if val is not None else "—"
    if text.startswith("http"):
        return f'<a href="{text}" style="color:#2563eb;text-decoration:none;">{text}</a>'
    # Style status keywords
    if text.lower() in ("healthy", "running", "ok", "success"):
        return (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:10px;'
            f'background:#dcfce7;color:#166534;font-size:12px;font-weight:600;">{text}</span>'
        )
    if text.lower() in ("unhealthy", "error", "down", "failed"):
        return (
            f'<span style="display:inline-block;padding:2px 10px;border-radius:10px;'
            f'background:#fef2f2;color:#991b1b;font-size:12px;font-weight:600;">{text}</span>'
        )
    return f'<span style="color:#1e293b;">{text}</span>'


def _details_table(details: Dict[str, Any]) -> str:
    if not details:
        return ""
    rows = ""
    for key, val in details.items():
        label = key.replace("_", " ").title()
        rows += (
            f'<tr>'
            f'<td style="padding:10px 16px;border-bottom:1px solid #f1f5f9;'
            f'font-weight:600;color:#64748b;vertical-align:top;white-space:nowrap;'
            f'font-size:13px;width:140px;">{label}</td>'
            f'<td style="padding:10px 16px;border-bottom:1px solid #f1f5f9;'
            f'font-size:14px;">{_format_value(val)}</td>'
            f'</tr>'
        )
    return (
        f'<table style="width:100%;border-collapse:collapse;margin-top:20px;'
        f'border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
        f'<tr><td colspan="2" style="padding:12px 16px;background:#f8fafc;'
        f'font-weight:700;color:#0f172a;font-size:13px;letter-spacing:0.3px;'
        f'text-transform:uppercase;border-bottom:1px solid #e2e8f0;">'
        f'Details</td></tr>'
        f'{rows}</table>'
    )


def _build_html(agent: str, severity: str, title: str, message: str, service: str, details: Dict[str, Any]) -> str:
    timestamp = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")
    details_html = _details_table(details)
    message_html = message.replace("\n", "<br/>")
    _, banner_bg, banner_text = _SEVERITY_COLORS.get(severity, ("#6b7280", "#f9fafb", "#374151"))

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 16px;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0,0,0,0.07),0 2px 4px -2px rgba(0,0,0,0.05);">

    <!-- Header -->
    <tr><td style="padding:20px 32px;background:#0f172a;">
        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td><span style="color:#ffffff;font-size:16px;font-weight:700;letter-spacing:-0.3px;">WIHY</span>
                <span style="color:#64748b;font-size:14px;font-weight:400;"> &middot; Agent Notification</span></td>
            <td align="right"><span style="color:#94a3b8;font-size:12px;">{timestamp}</span></td>
        </tr></table>
    </td></tr>

    <!-- Severity banner -->
    <tr><td style="padding:16px 32px;background:{banner_bg};border-bottom:1px solid #e2e8f0;">
        <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td>{_severity_badge(severity)}</td>
            <td align="right">
                <span style="color:{banner_text};font-size:12px;font-weight:600;">{agent.upper()}</span>
                <span style="color:#94a3b8;font-size:12px;"> &rarr; {service}</span>
            </td>
        </tr></table>
    </td></tr>

    <!-- Body -->
    <tr><td style="padding:28px 32px;">
        <h1 style="margin:0 0 16px;color:#0f172a;font-size:22px;font-weight:700;line-height:1.3;letter-spacing:-0.3px;">{title}</h1>
        <p style="margin:0 0 24px;color:#475569;font-size:15px;line-height:1.75;">{message_html}</p>
        {details_html}
    </td></tr>

    <!-- Footer -->
    <tr><td style="padding:16px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;text-align:center;">
        <span style="color:#94a3b8;font-size:11px;">Sent by WIHY Agent System &middot; Do not reply</span>
    </td></tr>

</table></td></tr></table></body></html>"""


async def send_notification(
    agent: str,
    severity: str,
    title: str,
    message: str,
    service: str,
    channels: Optional[List[str]] = None,
    recipient: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send an email notification via SendGrid to kortney@wihy.ai.

    Returns True if SendGrid accepted (2xx), False otherwise.
    Never raises — logs on failure.
    """
    if not _SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — notification skipped: %s", title)
        return False

    to_email = _TO_EMAIL
    if recipient and recipient.get("email"):
        to_email = recipient["email"]

    html_body = _build_html(agent, severity, title, message, service, details or {})
    subject = f"[{severity.upper()}] {title}"

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": _FROM_EMAIL, "name": _FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
        "categories": ["agent-notification", agent, service],
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.post(
                _SENDGRID_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {_SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
        if r.status_code in (200, 201, 202):
            logger.info("Notification emailed to %s: %s", to_email, title)
            return True
        logger.error("SendGrid error %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as exc:
        logger.error("SendGrid unreachable: %s", exc)
        return False


async def send_report(report_data: Dict[str, Any]) -> bool:
    """
    Send master-agent report digest via SendGrid email.

    Returns True on 2xx, False otherwise. Never raises.
    """
    title = report_data.get("title", "Master Agent Report")
    agent = report_data.get("agent", "master-agent")
    summary = report_data.get("summary", "")

    return await send_notification(
        agent=agent,
        severity="info",
        title=title,
        message=summary or json.dumps(report_data, indent=2, default=str)[:2000],
        service="master-agent",
        details=report_data,
    )
