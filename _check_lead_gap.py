"""
_check_lead_gap.py — Compare Meta Lead Ads vs Firestore to find unsynced leads.

Shows:
  1. All active lead gen forms and their lead counts (from Meta)
  2. How many are in Firestore launch_leads
  3. The gap (leads that exist in Meta but haven't been synced/emailed)

Usage:
  python _check_lead_gap.py              # check gap
  python _check_lead_gap.py --sync       # also trigger sync via API (requires LABAT_URL)
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

# ── Config ────────────────────────────────────────────────────────────────────

GCP_PROJECT = os.getenv("GCP_PROJECT", "wihy-ai")
LABAT_URL = os.getenv("LABAT_URL", "https://ml.wihy.ai").rstrip("/")
ADMIN_TOKEN = os.getenv("INTERNAL_ADMIN_TOKEN", "").strip()

# Meta tokens (for direct graph calls)
META_SYSTEM_USER_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN", "").strip()
SHANIA_PAGE_ACCESS_TOKEN = os.getenv("SHANIA_PAGE_ACCESS_TOKEN", "").strip()

GRAPH = "https://graph.facebook.com/v21.0"


# ── Meta helpers ──────────────────────────────────────────────────────────────


def _page_token() -> str:
    t = SHANIA_PAGE_ACCESS_TOKEN or META_SYSTEM_USER_TOKEN
    if not t:
        print("ERROR: SHANIA_PAGE_ACCESS_TOKEN or META_SYSTEM_USER_TOKEN not set")
        sys.exit(1)
    return t


def _sys_token() -> str:
    t = META_SYSTEM_USER_TOKEN
    if not t:
        print("ERROR: META_SYSTEM_USER_TOKEN not set")
        sys.exit(1)
    return t


def meta_get(path: str, params: Dict) -> Dict:
    url = f"{GRAPH}/{path}"
    try:
        resp = httpx.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"  Meta API error {path}: {e.response.status_code} {e.response.text[:300]}")
        return {}
    except Exception as e:
        print(f"  Meta request error {path}: {e}")
        return {}


def get_all_lead_forms(page_id: str) -> List[Dict]:
    """Get all lead gen forms for a page with lead counts."""
    params = {
        "fields": "id,name,status,leads_count,organic_leads_count,created_time",
        "limit": 100,
        "access_token": _page_token(),
    }
    forms = []
    after = None
    while True:
        if after:
            params["after"] = after
        result = meta_get(f"{page_id}/leadgen_forms", params)
        data = result.get("data", [])
        forms.extend(data)
        paging = result.get("paging", {})
        cursor = paging.get("cursors", {}).get("after")
        if not cursor or not paging.get("next"):
            break
        after = cursor
    return forms


def get_leads_count_from_form(form_id: str) -> int:
    """Get total lead count for a form directly."""
    params = {
        "fields": "id",
        "limit": 1,
        "summary": "true",
        "access_token": _sys_token(),
    }
    result = meta_get(f"{form_id}/leads", params)
    # summary.total_count if available
    summary = result.get("summary", {})
    if "total_count" in summary:
        return summary["total_count"]
    # Fall back to counting data
    return len(result.get("data", []))


def get_all_leads_from_form(form_id: str) -> List[Dict]:
    """Page through ALL leads for a form."""
    params = {
        "fields": "id,created_time,field_data",
        "limit": 100,
        "access_token": _sys_token(),
    }
    all_leads = []
    after = None
    while True:
        if after:
            params["after"] = after
        result = meta_get(f"{form_id}/leads", params)
        data = result.get("data", [])
        all_leads.extend(data)
        paging = result.get("paging", {})
        cursor = paging.get("cursors", {}).get("after")
        if not cursor or not paging.get("next"):
            break
        after = cursor
    return all_leads


# ── Firestore helpers ─────────────────────────────────────────────────────────


def _get_firestore():
    try:
        from google.cloud import firestore
        return firestore.Client(project=GCP_PROJECT)
    except Exception as e:
        print(f"ERROR: Cannot connect to Firestore: {e}")
        sys.exit(1)


def get_all_firestore_emails(collection: str) -> set:
    """Return set of all emails in a Firestore collection."""
    db = _get_firestore()
    emails = set()
    for doc in db.collection(collection).stream():
        d = doc.to_dict()
        if d.get("email"):
            emails.add(d["email"].lower().strip())
    return emails


def get_firestore_count(collection: str) -> int:
    db = _get_firestore()
    return sum(1 for _ in db.collection(collection).stream())


# ── Sync via API ──────────────────────────────────────────────────────────────


def trigger_sync(form_id: str = None) -> Dict:
    """Hit the labat sync endpoint to pull leads from Meta → Firestore → email."""
    if not ADMIN_TOKEN:
        print("  ERROR: INTERNAL_ADMIN_TOKEN not set — cannot trigger sync")
        return {}
    url = f"{LABAT_URL}/api/labat/leads/sync"
    params = {}
    if form_id:
        params["form_id"] = form_id
    try:
        resp = httpx.post(
            url,
            params=params,
            headers={"X-Admin-Token": ADMIN_TOKEN},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        print(f"  Sync API error: {e.response.status_code} {e.response.text[:400]}")
        return {}
    except Exception as e:
        print(f"  Sync request error: {e}")
        return {}


# ── Page IDs ──────────────────────────────────────────────────────────────────


def get_page_ids() -> Dict[str, str]:
    """Read page IDs from env (same as brands.py)."""
    ids = {}
    for brand, env_var in [
        ("wihy",                 "META_PAGE_ID_WIHY"),
        ("communitygroceries",   "META_PAGE_ID_COMMUNITYGROCERIES"),
        ("vowels",               "META_PAGE_ID_VOWELS"),
        ("childrennutrition",    "META_PAGE_ID_CHILDRENNUTRITION"),
        ("parentingwithchrist",  "META_PAGE_ID_PARENTINGWITHCHRIST"),
    ]:
        val = os.getenv(env_var, "").strip()
        if val:
            ids[brand] = val
    # Hardcoded fallbacks
    if "wihy" not in ids:
        ids["wihy"] = "937763702752161"
    return ids


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Check Meta lead gap vs Firestore")
    parser.add_argument("--sync", action="store_true", help="Trigger sync after reporting gap")
    parser.add_argument("--full", action="store_true", help="Pull every lead email from Meta to compare (slower)")
    args = parser.parse_args()

    page_ids = get_page_ids()
    print(f"\nPage IDs found: {list(page_ids.keys())}")

    # Get Firestore email sets
    print("\nLoading Firestore launch_leads...")
    try:
        fs_launch_emails = get_all_firestore_emails("launch_leads")
        fs_launch_count = len(fs_launch_emails)
    except Exception as e:
        print(f"  Error: {e}")
        fs_launch_emails = set()
        fs_launch_count = 0

    print(f"  launch_leads in Firestore: {fs_launch_count}")

    print("\nLoading Firestore book_leads...")
    try:
        fs_book_emails = get_all_firestore_emails("book_leads")
        fs_book_count = len(fs_book_emails)
    except Exception as e:
        print(f"  Error: {e}")
        fs_book_emails = set()
        fs_book_count = 0

    print(f"  book_leads in Firestore:   {fs_book_count}")

    all_meta_leads = 0
    unsynced_total = 0
    forms_with_gap = []

    for brand, page_id in page_ids.items():
        print(f"\n{'='*60}")
        print(f"PAGE: {brand} ({page_id})")
        print(f"{'='*60}")

        forms = get_all_lead_forms(page_id)
        if not forms:
            print("  No lead forms found (check page token / permissions)")
            continue

        print(f"  Lead forms found: {len(forms)}")

        for form in forms:
            fid = form["id"]
            fname = form.get("name", "?")
            status = form.get("status", "?")
            meta_count = form.get("leads_count", 0) or 0
            organic = form.get("organic_leads_count", 0) or 0
            created = str(form.get("created_time", "?"))[:10]
            all_meta_leads += meta_count

            print(f"\n  [{status}] {fname}")
            print(f"    form_id:     {fid}")
            print(f"    created:     {created}")
            print(f"    Meta leads:  {meta_count}  (organic: {organic})")

            if meta_count == 0:
                print(f"    Gap:         0 (no leads yet)")
                continue

            if args.full and meta_count > 0:
                # Pull all leads and compare emails
                leads = get_all_leads_from_form(fid)
                meta_emails = set()
                for lead in leads:
                    for field in lead.get("field_data", []):
                        if field.get("name") == "email":
                            vals = field.get("values", [])
                            if vals:
                                meta_emails.add(vals[0].lower().strip())
                not_in_fs = meta_emails - fs_launch_emails - fs_book_emails
                print(f"    Emails found in Meta: {len(meta_emails)}")
                print(f"    Not in Firestore:     {len(not_in_fs)}")
                if not_in_fs:
                    print(f"    Unsynced emails:")
                    for em in sorted(not_in_fs):
                        print(f"      {em}")
                    unsynced_total += len(not_in_fs)
                    forms_with_gap.append({"form_id": fid, "name": fname, "unsynced": len(not_in_fs)})
            else:
                # Estimate gap from counts (fast path)
                est_in_fs = sum(
                    1 for e in fs_launch_emails | fs_book_emails
                    if e  # rough — we can't know which Firestore leads came from which form
                )
                print(f"    (use --full to get exact email-level diff)")

    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Total leads in Meta (all forms): {all_meta_leads}")
    print(f"  In Firestore (launch_leads):     {fs_launch_count}")
    print(f"  In Firestore (book_leads):       {fs_book_count}")
    print(f"  In Firestore (total):            {fs_launch_count + fs_book_count}")
    gap = all_meta_leads - (fs_launch_count + fs_book_count)
    print(f"  Estimated gap (not emailed):     {gap}")

    if args.full and forms_with_gap:
        print(f"\n  Forms with unsynced leads ({len(forms_with_gap)}):")
        for f in forms_with_gap:
            print(f"    [{f['unsynced']} missing] {f['name']} ({f['form_id']})")

    if args.sync:
        print(f"\n{'='*60}")
        print("TRIGGERING SYNC via API")
        print(f"{'='*60}")
        print(f"  POST {LABAT_URL}/api/labat/leads/sync")
        result = trigger_sync()
        if result:
            print(f"  Forms processed: {result.get('forms_processed', '?')}")
            print(f"  Total synced:    {result.get('total_synced', '?')}")
            print(f"  Total errors:    {result.get('total_errors', '?')}")
            for r in result.get("results", []):
                if r.get("synced", 0) > 0 or r.get("errors", 0) > 0:
                    print(f"    form {r.get('form_id')}: synced={r.get('synced')} skipped={r.get('skipped')} errors={r.get('errors')}")
        else:
            print("  No result returned — check LABAT_URL and INTERNAL_ADMIN_TOKEN")


if __name__ == "__main__":
    main()
