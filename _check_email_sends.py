"""
_check_email_sends.py — Verify email delivery and open rates for leads.

Checks two lead sources:
  1. launch_leads (Meta Lead Ads / WIHY/CG signups)
  2. book_leads   (whatishealthy.org book funnel)

For each lead, queries the SendGrid Activity API to show:
  - Whether an email was delivered
  - Whether they opened it
  - Whether they clicked

Usage:
  python _check_email_sends.py                  # last 7 days, all sources
  python _check_email_sends.py --days 30        # last 30 days
  python _check_email_sends.py --source book    # book leads only
  python _check_email_sends.py --source launch  # launch/Meta leads only
  python _check_email_sends.py --email foo@bar.com  # single email lookup
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

import httpx

# ── Config ────────────────────────────────────────────────────────────────────

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "").strip()
GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")

SENDGRID_ACTIVITY_URL = "https://api.sendgrid.com/v3/messages"
SENDGRID_STATS_URL = "https://api.sendgrid.com/v3/stats"

# Emails to skip (test/internal entries)
TEST_PATTERNS = (
    "example.com",
    "test@",
    "firebase-test",
    "iam-verify",
    "test-verify",
    "test-nurture",
)

# ── SendGrid helpers ──────────────────────────────────────────────────────────


def _sg_headers() -> Dict[str, str]:
    if not SENDGRID_API_KEY:
        print("ERROR: SENDGRID_API_KEY not set. Export it before running.")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }


def get_messages_for_email(email: str, days: int = 7) -> List[Dict]:
    """
    Query SendGrid Email Activity Feed for a specific email address.
    Returns list of message records with events (delivered, open, click, bounce).

    NOTE: Requires SendGrid Email Activity Feed add-on (free tier has 3-day history).
    """
    query = f"to_email='{email}'"
    params = {"query": query, "limit": 100}
    try:
        resp = httpx.get(
            SENDGRID_ACTIVITY_URL,
            headers=_sg_headers(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("messages", [])
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return [{"_error": "activity_feed_not_enabled"}]
        if e.response.status_code == 429:
            print(f"  [rate limited] sleeping 5s then retrying {email}")
            time.sleep(5)
            try:
                resp2 = httpx.get(
                    SENDGRID_ACTIVITY_URL,
                    headers=_sg_headers(),
                    params=params,
                    timeout=15,
                )
                resp2.raise_for_status()
                return resp2.json().get("messages", [])
            except Exception:
                return []
        print(f"  SendGrid error for {email}: {e.response.status_code} {e.response.text[:200]}")
        return []
    except Exception as e:
        print(f"  Request error for {email}: {e}")
        return []


def get_overall_stats(days: int = 7) -> List[Dict]:
    """Get overall account stats (all sends, opens, clicks) for the past N days."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        resp = httpx.get(
            SENDGRID_STATS_URL,
            headers=_sg_headers(),
            params={"start_date": start, "end_date": end, "aggregated_by": "day"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  Stats error: {e}")
        return []


# ── Firestore helpers ─────────────────────────────────────────────────────────


def _get_firestore():
    try:
        from google.cloud import firestore
        return firestore.Client(project=GCP_PROJECT)
    except Exception as e:
        print(f"ERROR: Cannot connect to Firestore: {e}")
        sys.exit(1)


def get_recent_launch_leads(days: int = 7, limit: int = 200) -> List[Dict]:
    """Pull recent launch_leads (Meta Lead Ads / app signups)."""
    try:
        db = _get_firestore()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = (
            db.collection("launch_leads")
            .where("created_at", ">=", cutoff)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )
        results = []
        for doc in query.stream():
            d = doc.to_dict()
            d["id"] = doc.id
            d["_source"] = "launch"
            results.append(d)
        return results
    except Exception as e:
        print(f"  launch_leads query error: {e}")
        return []


def get_recent_book_leads(days: int = 7, limit: int = 200) -> List[Dict]:
    """Pull recent book_leads (whatishealthy.org signups)."""
    try:
        db = _get_firestore()
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = (
            db.collection("book_leads")
            .where("created_at", ">=", cutoff)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )
        results = []
        for doc in query.stream():
            d = doc.to_dict()
            d["id"] = doc.id
            d["_source"] = "book"
            results.append(d)
        return results
    except Exception as e:
        print(f"  book_leads query error: {e}")
        return []


# ── Display helpers ───────────────────────────────────────────────────────────


def _summarize_messages(messages: List[Dict]) -> Dict:
    """Collapse raw message list into a summary dict."""
    if not messages:
        return {
            "sent": False, "delivered": False, "opened": False,
            "clicked": False, "bounced": False, "count": 0,
        }
    if messages[0].get("_error") == "activity_feed_not_enabled":
        return {"_no_activity_feed": True}

    summary = {
        "sent": False, "delivered": False, "opened": False,
        "clicked": False, "bounced": False, "count": len(messages),
    }
    for msg in messages:
        status = (msg.get("status") or "").lower()
        if status in ("delivered", "opened", "clicked"):
            summary["sent"] = True
            summary["delivered"] = True
        if status == "processed":
            summary["sent"] = True
        if status == "opened":
            summary["opened"] = True
        if status == "clicked":
            summary["opened"] = True
            summary["clicked"] = True
        if status in ("bounced", "blocked", "spam_report"):
            summary["bounced"] = True

        for event in msg.get("events", []):
            etype = event.get("event_name", "").lower()
            if etype in ("processed", "delivered"):
                summary["sent"] = True
                if etype == "delivered":
                    summary["delivered"] = True
            if etype == "open":
                summary["opened"] = True
                summary["delivered"] = True
            if etype == "click":
                summary["clicked"] = True
                summary["opened"] = True

    return summary


def _fmt_date(val) -> str:
    if val is None:
        return "?"
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d %H:%M")
    return str(val)[:16]


def _is_test(email: str) -> bool:
    return any(p in email for p in TEST_PATTERNS)


# ── Aggregate stats ───────────────────────────────────────────────────────────


def print_aggregate_stats(days: int):
    print(f"\n{'='*60}")
    print(f"SENDGRID AGGREGATE STATS — last {days} days")
    print(f"{'='*60}")

    data = get_overall_stats(days)
    if not data:
        print("  No data returned from SendGrid stats API.")
        return

    totals = {
        "requests": 0, "delivered": 0, "opens": 0, "unique_opens": 0,
        "clicks": 0, "unique_clicks": 0, "bounces": 0, "spam_reports": 0,
    }
    for day in data:
        for entry in day.get("stats", []):
            metrics = entry.get("metrics", {})
            for k in totals:
                totals[k] += metrics.get(k, 0)

    delivery_rate = totals["delivered"] / totals["requests"] * 100 if totals["requests"] else 0
    open_rate = totals["unique_opens"] / totals["delivered"] * 100 if totals["delivered"] else 0
    click_rate = totals["unique_clicks"] / totals["unique_opens"] * 100 if totals["unique_opens"] else 0

    print(f"  Sent (requests): {totals['requests']}")
    print(f"  Delivered:       {totals['delivered']}  ({delivery_rate:.1f}%)")
    print(f"  Opens (unique):  {totals['unique_opens']}  ({open_rate:.1f}% of delivered)")
    print(f"  Clicks (unique): {totals['unique_clicks']}  ({click_rate:.1f}% of openers)")
    print(f"  Bounces:         {totals['bounces']}")
    print(f"  Spam reports:    {totals['spam_reports']}")


# ── Per-lead email check ──────────────────────────────────────────────────────


def check_lead_emails(leads: List[Dict], days: int):
    """For each lead, check SendGrid for email send/open status."""
    if not leads:
        print("  (no leads found in this range)")
        return

    # Split test vs real
    real_leads = [l for l in leads if not _is_test(l.get("email", ""))]
    test_leads = [l for l in leads if _is_test(l.get("email", ""))]
    if test_leads:
        emails_str = ", ".join(l["email"] for l in test_leads)
        print(f"  (skipping {len(test_leads)} test entries: {emails_str})")

    if not real_leads:
        print("  (no real leads to check)")
        return

    activity_feed_available = None
    not_sent = []
    sent_not_opened = []
    opened = []

    for lead in real_leads:
        email = lead.get("email", "")
        if not email:
            continue
        created = _fmt_date(lead.get("created_at"))
        stage = lead.get("nurture_stage", 0)
        brand = lead.get("brand") or lead.get("source", "?")

        messages = get_messages_for_email(email, days)
        time.sleep(0.7)  # respect SendGrid rate limit (~100 req/min)
        summary = _summarize_messages(messages)

        if activity_feed_available is None:
            activity_feed_available = not summary.get("_no_activity_feed")

        row = {
            "email": email,
            "created": created,
            "stage": stage,
            "brand": brand,
            "summary": summary,
        }

        if summary.get("_no_activity_feed"):
            pass  # can't check per-email
        elif not summary.get("sent"):
            not_sent.append(row)
        elif summary.get("opened"):
            opened.append(row)
        else:
            sent_not_opened.append(row)

    if activity_feed_available is False:
        print("  ⚠️  SendGrid Email Activity Feed is not enabled for this account.")
        print("  ⚠️  Per-lead tracking requires the Activity Feed add-on.")
        print("  ⚠️  Aggregate stats above are still accurate.")
        return

    total = len(real_leads)
    n_sent = len(sent_not_opened) + len(opened)
    pct = lambda n: f"({n/total*100:.0f}%)" if total else ""

    print(f"\n  Total real leads: {total}")
    print(f"  Email sent:       {n_sent} {pct(n_sent)}")
    print(f"  Opened:           {len(opened)} {pct(len(opened))}")
    print(f"  Sent, not opened: {len(sent_not_opened)} {pct(len(sent_not_opened))}")
    print(f"  NOT sent:         {len(not_sent)} {pct(len(not_sent))}")

    if not_sent:
        print(f"\n  ── LEADS WITH NO EMAIL SENT ({len(not_sent)}) ──")
        for r in not_sent:
            print(f"    {r['created']}  {r['email']:<40}  stage={r['stage']}  brand={r['brand']}")

    if opened:
        print(f"\n  ── LEADS WHO OPENED ({len(opened)}) ──")
        for r in opened:
            s = r["summary"]
            flags = []
            if s.get("clicked"):
                flags.append("CLICKED")
            extra = f"  [{', '.join(flags)}]" if flags else ""
            print(f"    {r['created']}  {r['email']:<40}  msgs={s['count']}{extra}")

    if sent_not_opened:
        print(f"\n  ── SENT BUT NOT OPENED ({len(sent_not_opened)}) ──")
        for r in sent_not_opened:
            print(f"    {r['created']}  {r['email']:<40}  stage={r['stage']}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Check email sends + opens for leads")
    parser.add_argument("--days", type=int, default=7, help="Days of history (default: 7)")
    parser.add_argument("--source", choices=["book", "launch", "all"], default="all")
    parser.add_argument("--email", type=str, default=None, help="Check a single email address")
    args = parser.parse_args()

    if args.email:
        print(f"\nChecking SendGrid activity for: {args.email}")
        messages = get_messages_for_email(args.email, args.days)
        summary = _summarize_messages(messages)
        if summary.get("_no_activity_feed"):
            print("Status: ⚠️  Activity Feed not enabled")
        else:
            sent = summary.get("sent")
            opened = summary.get("opened")
            clicked = summary.get("clicked")
            bounced = summary.get("bounced")
            flags = []
            if sent:
                flags.append("SENT")
            if opened:
                flags.append("OPENED")
            if clicked:
                flags.append("CLICKED")
            if bounced:
                flags.append("BOUNCED")
            if not sent:
                flags.append("NOT SENT")
            print(f"Status: {' | '.join(flags)}")
        print(f"Messages found: {len(messages)}")
        for msg in messages:
            ts = str(msg.get("last_event_time", msg.get("created_at", "?")))[:16]
            subject = msg.get("subject", "(no subject)")
            status = msg.get("status", "?")
            print(f"  [{ts}] {status:<20} {subject[:60]}")
        return

    # Aggregate stats first (no rate limit concern)
    print_aggregate_stats(args.days)

    # Per-lead breakdown
    if args.source in ("launch", "all"):
        leads = get_recent_launch_leads(args.days)
        print(f"\n{'='*60}")
        print(f"LAUNCH LEADS (Meta Lead Ads / app signups) — {len(leads)} in last {args.days}d")
        print(f"{'='*60}")
        check_lead_emails(leads, args.days)

    if args.source in ("book", "all"):
        leads = get_recent_book_leads(args.days)
        print(f"\n{'='*60}")
        print(f"BOOK LEADS (whatishealthy.org) — {len(leads)} in last {args.days}d")
        print(f"{'='*60}")
        check_lead_emails(leads, args.days)


if __name__ == "__main__":
    main()
