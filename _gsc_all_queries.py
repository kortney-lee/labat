"""
Pull ALL Google Search Console queries for both wihy.ai and communitygroceries.com.
Paginates through the full dataset (GSC max 25k rows/request) and saves to JSON.

Output: data/gsc_all_queries.json
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

import google.auth
from googleapiclient.discovery import build

# ── Auth ──────────────────────────────────────────────────────────────────────
creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
)
service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE = "2024-01-01"
END_DATE   = date.today().isoformat()
ROW_LIMIT  = 25000   # GSC max per request
DELAY      = 0.3     # seconds between paginated requests

SITES = {
    "wihy":  None,
    "cg":    None,
}

# ── Discover site URLs ────────────────────────────────────────────────────────
print("Discovering verified sites...")
sites_resp = service.sites().list().execute()
for s in sites_resp.get("siteEntry", []):
    url = s.get("siteUrl", "")
    perm = s.get("permissionLevel", "")
    print(f"  {perm:<20} {url}")
    if "wihy" in url.lower():
        SITES["wihy"] = url
    if "communitygroceries" in url.lower() or "cg" in url.lower():
        SITES["cg"] = url

# Override with domain properties if not found
for name, candidates in [
    ("wihy", ["sc-domain:wihy.ai", "https://wihy.ai/", "https://ml.wihy.ai/"]),
    ("cg",   ["sc-domain:communitygroceries.com", "https://communitygroceries.com/"]),
]:
    if not SITES[name]:
        for candidate in candidates:
            try:
                service.sites().get(siteUrl=candidate).execute()
                SITES[name] = candidate
                print(f"  Found {name}: {candidate}")
                break
            except Exception:
                pass

print(f"\nUsing sites:")
for name, url in SITES.items():
    print(f"  {name}: {url or 'NOT FOUND'}")


# ── Fetch all rows for a site (paginated) ─────────────────────────────────────
def fetch_all_queries(site_url: str, site_name: str) -> list:
    """Page through GSC and return ALL query rows."""
    if not site_url:
        print(f"  Skipping {site_name} — site URL not found")
        return []

    all_rows = []
    offset = 0
    page = 1

    while True:
        body = {
            "startDate": START_DATE,
            "endDate": END_DATE,
            "dimensions": ["query"],
            "rowLimit": ROW_LIMIT,
            "startRow": offset,
            "dataState": "all",
        }
        try:
            resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        except Exception as e:
            print(f"  Error at page {page}: {e}")
            break

        rows = resp.get("rows", [])
        if not rows:
            break

        for row in rows:
            all_rows.append({
                "query":       row["keys"][0],
                "clicks":      row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr":         round(row.get("ctr", 0) * 100, 2),
                "position":    round(row.get("position", 0), 1),
                "site":        site_name,
            })

        print(f"  Page {page}: {len(rows)} rows (total so far: {len(all_rows)})")

        if len(rows) < ROW_LIMIT:
            break  # Last page

        offset += ROW_LIMIT
        page += 1
        time.sleep(DELAY)

    return all_rows


# ── Fetch both sites ──────────────────────────────────────────────────────────
all_queries = []

for site_name, site_url in SITES.items():
    print(f"\n{'='*60}")
    print(f"Fetching ALL queries for: {site_name} ({site_url})")
    print(f"{'='*60}")
    rows = fetch_all_queries(site_url, site_name)
    all_queries.extend(rows)
    print(f"  Total for {site_name}: {len(rows)} queries")

# ── Deduplicate across sites (keep higher impressions) ────────────────────────
seen = {}
for row in all_queries:
    q = row["query"].strip().lower()
    if q not in seen or row["impressions"] > seen[q]["impressions"]:
        seen[q] = row

deduped = sorted(seen.values(), key=lambda x: x["impressions"], reverse=True)

# ── Stats ─────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"TOTAL unique queries: {len(deduped)}")
print(f"With clicks:         {sum(1 for r in deduped if r['clicks'] > 0)}")
print(f"With 100+ impressions: {sum(1 for r in deduped if r['impressions'] >= 100)}")
print(f"With 1000+ impressions: {sum(1 for r in deduped if r['impressions'] >= 1000)}")
print()

# Top 30 by impressions
print(f"{'Clicks':>7} {'Impr':>8} {'CTR':>6} {'Pos':>5}  Query")
print("-" * 80)
for row in deduped[:30]:
    print(f"{row['clicks']:>7} {row['impressions']:>8} {row['ctr']:>5.1f}% {row['position']:>5.1f}  {row['query'][:70]}")

# ── Save ──────────────────────────────────────────────────────────────────────
out = {
    "pulled_at": date.today().isoformat(),
    "date_range": f"{START_DATE} to {END_DATE}",
    "total": len(deduped),
    "sites": {k: v for k, v in SITES.items() if v},
    "queries": deduped,
}

Path("data").mkdir(exist_ok=True)
Path("data/gsc_all_queries.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nSaved {len(deduped)} queries → data/gsc_all_queries.json")
