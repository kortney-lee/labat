#!/usr/bin/env python
"""
_run_brb_email_campaign.py

Send a personalized outreach campaign to Book Review Blogs leads from an XLSX file.

Default behavior is DRY RUN (no emails sent).
Use --send to actually send emails.

Example:
  python _run_brb_email_campaign.py \
    --xlsx email_assets/Leads/BookReviewBlogs_BRB.xlsx \
    --subject "Would you review What Is Healthy?" \
    --html-file email_assets/templates/brb_outreach.html \
    --send
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import pandas as pd

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
SENDGRID_SUPPRESSION_ENDPOINTS = {
    "global_unsubscribe": "https://api.sendgrid.com/v3/asm/suppressions/global",
    "unsubscribes": "https://api.sendgrid.com/v3/suppression/unsubscribes",
    "bounces": "https://api.sendgrid.com/v3/suppression/bounces",
    "blocks": "https://api.sendgrid.com/v3/suppression/blocks",
    "spam_reports": "https://api.sendgrid.com/v3/suppression/spam_reports",
    "invalid_emails": "https://api.sendgrid.com/v3/suppression/invalid_emails",
}
DEFAULT_XLSX = "email_assets/Leads/BookReviewBlogs_BRB.xlsx"
DEFAULT_HTML = "email_assets/templates/brb_outreach.html"
DEFAULT_TEXT = "email_assets/templates/brb_outreach.txt"
DEFAULT_SUBJECT = "Quick review request: What Is Healthy?"
DEFAULT_CAMPAIGN_TAG = "book_outreach"
DEFAULT_FROM_EMAIL = "info@vowels.org"
DEFAULT_FROM_NAME = "Vowels Editorial Team"
DEFAULT_BATCH_SIZE = 50
DEFAULT_SLEEP_SECONDS = 0.2

SEGMENT_CAMPAIGNS = {
    "book_review_blogs": {
        "subject": "Review request for your readers: What Is Healthy?",
        "html_file": "email_assets/templates/brb_outreach.html",
        "text_file": "email_assets/templates/brb_outreach.txt",
        "campaign_tag": "book_review_blogs_outreach",
    },
    "book_review_podcasts": {
        "subject": "Podcast fit: a practical food and health conversation",
        "html_file": "email_assets/templates/brp_outreach.html",
        "text_file": "email_assets/templates/brp_outreach.txt",
        "campaign_tag": "book_review_podcasts_outreach",
    },
    "bookstores": {
        "subject": "Bookstore title consideration: What Is Healthy?",
        "html_file": "email_assets/templates/bs_outreach.html",
        "text_file": "email_assets/templates/bs_outreach.txt",
        "campaign_tag": "bookstores_outreach",
    },
    "christian_blogs": {
        "subject": "Faith-centered review opportunity: What Is Healthy?",
        "html_file": "email_assets/templates/chrb_outreach.html",
        "text_file": "email_assets/templates/chrb_outreach.txt",
        "campaign_tag": "christian_blogs_outreach",
    },
    "christian_podcasts": {
        "subject": "Faith and wellness podcast opportunity",
        "html_file": "email_assets/templates/chrp_outreach.html",
        "text_file": "email_assets/templates/chrp_outreach.txt",
        "campaign_tag": "christian_podcasts_outreach",
    },
    "libraries": {
        "subject": "Library collection request: What Is Healthy?",
        "html_file": "email_assets/templates/l_outreach.html",
        "text_file": "email_assets/templates/l_outreach.txt",
        "campaign_tag": "libraries_outreach",
    },
}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Lead:
    email: str
    first_name: str


@dataclass
class SendResult:
    email: str
    first_name: str
    status: str
    detail: str


def _derive_target_from_filename(path: Path) -> tuple[str, str, str]:
    """Infer human target name/slug/source code from an input list filename."""
    stem = path.stem.strip()
    if not stem:
        return "General Outreach", "general_outreach", "general"

    parts = stem.split("_")
    base = parts[0]
    source_code = parts[-1].lower() if len(parts) > 1 else "general"

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", base)
    words = re.sub(r"[_\-]+", " ", words)
    words = re.sub(r"\s+", " ", words).strip()

    target_name = words.title() if words else "General Outreach"
    target_slug = re.sub(r"[^a-z0-9]+", "_", words.lower()).strip("_") or "general_outreach"
    return target_name, target_slug, source_code


def _safe_doc_id(email: str, target_slug: str) -> str:
    safe_email = re.sub(r"[^a-z0-9]+", "_", email.lower()).strip("_")
    return f"{safe_email}__{target_slug}"


def _get_firestore_client(project: str):
    try:
        from google.cloud import firestore
    except Exception as exc:
        raise RuntimeError(
            "google-cloud-firestore is required for DB sync. "
            "Install with: pip install google-cloud-firestore"
        ) from exc
    return firestore.Client(project=project)


def _resolve_sendgrid_key(gcp_project: str) -> str:
    """Return SendGrid API key: env var first, then GCP Secret Manager."""
    key = os.getenv("SENDGRID_API_KEY", "").strip()
    if key:
        return key
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        candidate_names = ["SENDGRID_API_KEY", "sendgrid-api-key"]
        for secret_name in candidate_names:
            name = f"projects/{gcp_project}/secrets/{secret_name}/versions/latest"
            try:
                response = client.access_secret_version(request={"name": name})
                key = response.payload.data.decode("utf-8").strip()
                if key:
                    print(f"SendGrid API key resolved from GCP Secret Manager ({secret_name}).")
                    return key
            except Exception:
                continue
        print("WARN: SENDGRID_API_KEY secret not found in expected names.")
        return ""
    except Exception as exc:
        print(f"WARN: Could not fetch SENDGRID_API_KEY from Secret Manager: {exc}")
        return ""


def _upsert_lead_record(
    db,
    collection: str,
    lead: Lead,
    *,
    target_name: str,
    target_slug: str,
    source_code: str,
    source_file: str,
    campaign_tag: str,
    sendgrid_reasons: Optional[set[str]] = None,
) -> tuple[bool, str]:
    """Write lead to DB and return True if lead is unsubscribed/do-not-contact."""
    now = datetime.now(timezone.utc)
    doc_id = _safe_doc_id(lead.email, target_slug)
    doc_ref = db.collection(collection).document(doc_id)
    snap = doc_ref.get()
    existing = snap.to_dict() if snap.exists else {}
    sendgrid_reasons = sorted(sendgrid_reasons or [])
    sendgrid_blocked = len(sendgrid_reasons) > 0

    blocked = bool(
        sendgrid_blocked
        or existing.get("unsubscribed")
        or existing.get("do_not_contact")
        or existing.get("sequence_status") == "unsubscribed"
    )

    doc_data = {
        "email": lead.email,
        "first_name": lead.first_name,
        "lead_type": "publisher_outreach",
        "brand": "vowels",
        "product": "what_is_healthy",
        "target_conversation": target_name,
        "target_slug": target_slug,
        "source_code": source_code,
        "source_file": source_file,
        "campaign_tag": campaign_tag,
        "sequence_status": "unsubscribed" if sendgrid_blocked else existing.get("sequence_status", "active"),
        "unsubscribed": bool(existing.get("unsubscribed", False) or sendgrid_blocked),
        "do_not_contact": bool(existing.get("do_not_contact", False) or sendgrid_blocked),
        "remarketing_status": existing.get("remarketing_status", "new"),
        "remarketing_tags": sorted(
            set((existing.get("remarketing_tags") or []) + [target_slug, campaign_tag, "book_outreach"])
        ),
        "sendgrid_suppressed": sendgrid_blocked,
        "sendgrid_suppression_reasons": sendgrid_reasons,
        "sendgrid_checked_at": now,
        "last_seen_at": now,
    }
    if sendgrid_blocked:
        doc_data["unsubscribed_at"] = now
    if not snap.exists:
        doc_data["created_at"] = now

    doc_ref.set(doc_data, merge=True)
    if sendgrid_blocked:
        return True, f"sendgrid:{','.join(sendgrid_reasons)}"
    if existing.get("unsubscribed") or existing.get("do_not_contact"):
        return True, "db_flagged_do_not_contact"
    return blocked, "db_flagged_do_not_contact" if blocked else "eligible"


def _record_send_outcome(db, collection: str, lead: Lead, target_slug: str, sent: bool) -> None:
    now = datetime.now(timezone.utc)
    doc_id = _safe_doc_id(lead.email, target_slug)
    doc_ref = db.collection(collection).document(doc_id)
    update = {
        "last_email_attempt_at": now,
        "last_email_status": "sent" if sent else "failed",
    }
    if sent:
        update["emails_sent_count"] = int((doc_ref.get().to_dict() or {}).get("emails_sent_count", 0)) + 1
    doc_ref.set(update, merge=True)


def _read_leads(path: Path) -> List[Lead]:
    if not path.exists():
        raise FileNotFoundError(f"Lead file not found: {path}")

    df = pd.read_excel(path)
    cols = {c.strip().upper(): c for c in df.columns}

    email_col = cols.get("EMAIL ADDRESS") or cols.get("EMAIL")
    first_col = cols.get("FIRST NAME") or cols.get("FIRST_NAME")

    if not email_col:
        raise ValueError("Could not find an email column (expected 'EMAIL ADDRESS' or 'EMAIL').")

    if not first_col:
        first_col = email_col

    leads: List[Lead] = []
    seen = set()

    for _, row in df.iterrows():
        raw_email = str(row.get(email_col, "") or "").strip().lower()
        raw_first = str(row.get(first_col, "") or "").strip()

        if not raw_email or raw_email in seen:
            continue
        if not EMAIL_RE.match(raw_email):
            continue

        first_name = raw_first if raw_first and raw_first != raw_email else "there"
        leads.append(Lead(email=raw_email, first_name=first_name))
        seen.add(raw_email)

    return leads


def _read_template(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return fallback


def _render(content: str, lead: Lead) -> str:
    return (
        content.replace("{{first_name}}", lead.first_name)
        .replace("{{email}}", lead.email)
    )


def _build_payload(
    lead: Lead,
    subject: str,
    from_email: str,
    from_name: str,
    html_template: str,
    text_template: str,
    campaign_tag: str,
    source_code: str,
    target_slug: str,
) -> Dict:
    html = _render(html_template, lead)
    text = _render(text_template, lead)

    return {
        "from": {"email": from_email, "name": from_name},
        "personalizations": [
            {
                "to": [{"email": lead.email, "name": lead.first_name}],
                "custom_args": {
                    "campaign": campaign_tag,
                    "source": source_code,
                    "target": target_slug,
                    "lead_email": lead.email,
                },
            }
        ],
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text},
            {"type": "text/html", "value": html},
        ],
        "categories": ["book_outreach", campaign_tag],
    }


def _send_one(client: httpx.Client, api_key: str, payload: Dict) -> tuple[bool, str]:
    r = client.post(
        SENDGRID_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if 200 <= r.status_code < 300:
        return True, f"accepted:{r.status_code}"
    return False, f"error:{r.status_code}:{r.text[:180]}"


def _sg_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _fetch_sendgrid_suppressions(api_key: str) -> Dict[str, set[str]]:
    """Fetch suppression lists from SendGrid and return email -> set(reasons)."""
    reasons_by_email: Dict[str, set[str]] = {}
    page_size = 500

    with httpx.Client(timeout=30) as client:
        for reason, url in SENDGRID_SUPPRESSION_ENDPOINTS.items():
            offset = 0
            while True:
                r = client.get(
                    url,
                    headers=_sg_headers(api_key),
                    params={"limit": page_size, "offset": offset},
                )
                if r.status_code >= 400:
                    print(f"WARN: SendGrid suppression fetch failed for {reason}: {r.status_code}")
                    break

                payload = r.json()
                if isinstance(payload, dict):
                    rows = payload.get("result") or payload.get("recipients") or []
                else:
                    rows = payload

                if not isinstance(rows, list) or not rows:
                    break

                for row in rows:
                    email = str((row or {}).get("email", "") or "").strip().lower()
                    if not email:
                        continue
                    if email not in reasons_by_email:
                        reasons_by_email[email] = set()
                    reasons_by_email[email].add(reason)

                if len(rows) < page_size:
                    break
                offset += page_size

    return reasons_by_email


def _write_report(path: Path, rows: List[SendResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["email", "first_name", "status", "detail"])
        for r in rows:
            writer.writerow([r.email, r.first_name, r.status, r.detail])


def _resolve_segment_campaign(target_slug: str) -> Dict[str, str]:
    cfg = SEGMENT_CAMPAIGNS.get(target_slug)
    if cfg:
        return cfg
    return {
        "subject": DEFAULT_SUBJECT,
        "html_file": DEFAULT_HTML,
        "text_file": DEFAULT_TEXT,
        "campaign_tag": DEFAULT_CAMPAIGN_TAG,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Send BRB email campaign from XLSX leads")
    parser.add_argument("--xlsx", default=DEFAULT_XLSX, help="Path to XLSX lead file")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT, help="Email subject")
    parser.add_argument("--html-file", default=DEFAULT_HTML, help="HTML template path")
    parser.add_argument("--text-file", default=DEFAULT_TEXT, help="Text template path")
    parser.add_argument("--from-email", default=DEFAULT_FROM_EMAIL, help="Verified sender email")
    parser.add_argument("--from-name", default=DEFAULT_FROM_NAME, help="Sender display name")
    parser.add_argument("--campaign-tag", default=DEFAULT_CAMPAIGN_TAG, help="Campaign tag for SendGrid categories/custom_args")
    parser.add_argument("--gcp-project", default=os.getenv("GCP_PROJECT", "wihy-ai"), help="GCP project for Firestore")
    parser.add_argument("--db-collection", default="outreach_leads", help="Firestore collection for outreach lead records")
    parser.add_argument("--no-db", action="store_true", help="Skip writing leads to Firestore")
    parser.add_argument("--db-on-dry-run", action="store_true", help="Deprecated: DB sync is now always on by default (kept for backwards compat)")
    parser.add_argument("--sync-db-only", action="store_true", help="Sync leads to DB only, no email send")
    parser.add_argument("--no-sendgrid-truth", action="store_true", help="Do not pull suppression flags from SendGrid")
    parser.add_argument("--limit", type=int, default=0, help="Optional send cap for testing")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Progress logging interval")
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP_SECONDS, help="Delay between sends")
    parser.add_argument("--send", action="store_true", help="Actually send emails (default is dry run)")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx)

    leads = _read_leads(xlsx_path)
    if args.limit > 0:
        leads = leads[: args.limit]

    target_name, target_slug, source_code = _derive_target_from_filename(xlsx_path)

    segment_cfg = _resolve_segment_campaign(target_slug)
    selected_subject = segment_cfg["subject"] if args.subject == DEFAULT_SUBJECT else args.subject
    selected_campaign_tag = segment_cfg["campaign_tag"] if args.campaign_tag == DEFAULT_CAMPAIGN_TAG else args.campaign_tag
    html_path = Path(segment_cfg["html_file"]) if args.html_file == DEFAULT_HTML else Path(args.html_file)
    text_path = Path(segment_cfg["text_file"]) if args.text_file == DEFAULT_TEXT else Path(args.text_file)

    if args.from_email != DEFAULT_FROM_EMAIL:
        print(f"WARN: Overriding from-email to {DEFAULT_FROM_EMAIL} for Vowels campaigns.")
    from_email = DEFAULT_FROM_EMAIL
    from_name = args.from_name if args.from_name else DEFAULT_FROM_NAME

    html_template = _read_template(
        html_path,
        """<p>Hi {{first_name}},</p><p>Would you be open to reviewing our book <strong>What Is Healthy?</strong> for your audience?</p><p>If yes, reply and we will send the review copy details right away.</p><p>Thank you,<br/>Vowels Editorial Team</p>""",
    )
    text_template = _read_template(
        text_path,
        "Hi {{first_name}},\n\nWould you be open to reviewing our book 'What Is Healthy?' for your audience?\n\nIf yes, reply and we will send the review copy details right away.\n\nThank you,\nVowels Editorial Team",
    )

    print(f"Loaded leads: {len(leads)} from {xlsx_path}")
    print(f"Target conversation: {target_name} ({target_slug})")
    print(f"Mode: {'SEND' if args.send else 'DRY RUN'}")
    print(f"Subject: {selected_subject}")
    print(f"Campaign tag: {selected_campaign_tag}")
    print(f"Template HTML: {html_path}")
    print(f"Sender: {from_email}")

    results: List[SendResult] = []
    eligible_leads: List[Lead] = []

    # Resolve API key only when it will be used (suppression fetch or live send)
    needs_key = not args.no_sendgrid_truth or args.send
    api_key = _resolve_sendgrid_key(args.gcp_project) if needs_key else os.getenv("SENDGRID_API_KEY", "").strip()
    sg_truth: Dict[str, set[str]] = {}
    if not args.no_sendgrid_truth and api_key:
        sg_truth = _fetch_sendgrid_suppressions(api_key)
        print(f"SendGrid source-of-truth loaded: suppressed={len(sg_truth)}")
    elif args.no_sendgrid_truth:
        print("SendGrid source-of-truth skipped (--no-sendgrid-truth)")
    else:
        print("SendGrid source-of-truth skipped (API key unavailable)")

    db = None
    should_db_sync = not args.no_db
    if should_db_sync:
        db = _get_firestore_client(args.gcp_project)
        blocked_count = 0
        for lead in leads:
            blocked, reason = _upsert_lead_record(
                db,
                args.db_collection,
                lead,
                target_name=target_name,
                target_slug=target_slug,
                source_code=source_code,
                source_file=xlsx_path.name,
                campaign_tag=selected_campaign_tag,
                sendgrid_reasons=sg_truth.get(lead.email, set()),
            )
            if blocked:
                blocked_count += 1
                results.append(SendResult(lead.email, lead.first_name, "skipped_unsubscribed", reason))
                continue
            eligible_leads.append(lead)
        print(f"DB sync complete: upserted={len(leads)} blocked={blocked_count} eligible={len(eligible_leads)}")
    else:
        for lead in leads:
            reasons = sg_truth.get(lead.email, set())
            if reasons:
                results.append(SendResult(lead.email, lead.first_name, "skipped_unsubscribed", f"sendgrid:{','.join(sorted(reasons))}"))
            else:
                eligible_leads.append(lead)
        if args.no_db:
            print("DB sync skipped (--no-db)")

    if args.sync_db_only:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report = Path("email_assets/reports") / f"brb_campaign_db_sync_{timestamp}.csv"
        for lead in eligible_leads:
            results.append(SendResult(lead.email, lead.first_name, "db_synced", "not_sent"))
        _write_report(report, results)
        print(f"DB sync-only complete. Report: {report}")
        return 0

    if not args.send:
        for lead in eligible_leads:
            results.append(SendResult(lead.email, lead.first_name, "dry_run", "not_sent"))
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        report = Path("email_assets/reports") / f"brb_campaign_dry_run_{timestamp}.csv"
        _write_report(report, results)
        print(f"Dry run complete. Report: {report}")
        return 0

    if not api_key:
        print("ERROR: SENDGRID_API_KEY is not set.")
        return 1

    sent = 0
    failed = 0

    with httpx.Client() as client:
        for idx, lead in enumerate(eligible_leads, start=1):
            payload = _build_payload(
                lead=lead,
                subject=selected_subject,
                from_email=from_email,
                from_name=from_name,
                html_template=html_template,
                text_template=text_template,
                campaign_tag=selected_campaign_tag,
                source_code=source_code,
                target_slug=target_slug,
            )
            ok, detail = _send_one(client, api_key, payload)
            if ok:
                sent += 1
                results.append(SendResult(lead.email, lead.first_name, "sent", detail))
            else:
                failed += 1
                results.append(SendResult(lead.email, lead.first_name, "failed", detail))

            if db is not None:
                _record_send_outcome(db, args.db_collection, lead, target_slug, ok)

            if idx % max(args.batch_size, 1) == 0:
                print(f"Progress: {idx}/{len(eligible_leads)} | sent={sent} failed={failed}")

            if args.sleep > 0:
                time.sleep(args.sleep)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report = Path("email_assets/reports") / f"brb_campaign_send_{timestamp}.csv"
    _write_report(report, results)

    print(f"Done. sent={sent} failed={failed}")
    print(f"Report: {report}")

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
