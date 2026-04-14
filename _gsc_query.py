"""Pull Google Search Console keyword data for wihy.ai"""
import json
import sys

import google.auth
from googleapiclient.discovery import build

creds, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/webmasters.readonly']
)
service = build('searchconsole', 'v1', credentials=creds)

# List sites first
print("=== SITES ===")
sites = service.sites().list().execute()
for s in sites.get('siteEntry', []):
    perm = s.get('permissionLevel', '?')
    url = s.get('siteUrl', '?')
    print(f"  {perm:20} {url}")

# Try wihy.ai variations
site_url = None
for s in sites.get('siteEntry', []):
    u = s.get('siteUrl', '')
    if 'wihy' in u.lower():
        site_url = u
        break

if not site_url:
    # Try common formats
    for try_url in ['sc-domain:wihy.ai', 'https://wihy.ai/', 'https://www.wihy.ai/']:
        try:
            site_info = service.sites().get(siteUrl=try_url).execute()
            site_url = try_url
            print(f"\nFound site: {site_url}")
            break
        except Exception as e:
            print(f"  Not found: {try_url} ({e})")

if not site_url:
    print("\nERROR: No wihy.ai site found in Search Console.")
    print("Make sure wihy.ai is verified in Search Console for kortney@wihy.ai")
    exit(1)

print(f"\n=== QUERYING: {site_url} ===\n")

# Query 1: Top keywords (last 90 days)
print("=== TOP KEYWORDS (Last 90 days) ===")
print(f"{'Clicks':>8} {'Impr':>8} {'CTR':>7} {'Pos':>6}  Query")
print("-" * 80)

request = {
    'startDate': '2025-01-01',
    'endDate': '2026-04-07',
    'dimensions': ['query'],
    'rowLimit': 50,
    'dataState': 'all'
}

try:
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    for row in response.get('rows', []):
        q = row['keys'][0]
        clicks = row.get('clicks', 0)
        impressions = row.get('impressions', 0)
        ctr = row.get('ctr', 0) * 100
        pos = row.get('position', 0)
        print(f"{clicks:>8} {impressions:>8} {ctr:>6.1f}% {pos:>5.1f}  {q}")
except Exception as e:
    print(f"Error: {e}")

# Query 2: Top pages
print("\n=== TOP PAGES (All time) ===")
print(f"{'Clicks':>8} {'Impr':>8} {'CTR':>7} {'Pos':>6}  Page")
print("-" * 80)

request2 = {
    'startDate': '2025-01-01',
    'endDate': '2026-04-07',
    'dimensions': ['page'],
    'rowLimit': 25,
    'dataState': 'all'
}

try:
    response2 = service.searchanalytics().query(siteUrl=site_url, body=request2).execute()
    for row in response2.get('rows', []):
        page = row['keys'][0].replace('https://wihy.ai', '')
        clicks = row.get('clicks', 0)
        impressions = row.get('impressions', 0)
        ctr = row.get('ctr', 0) * 100
        pos = row.get('position', 0)
        print(f"{clicks:>8} {impressions:>8} {ctr:>6.1f}% {pos:>5.1f}  {page or '/'}")
except Exception as e:
    print(f"Error: {e}")

# Query 3: Keywords for /subscription and /about specifically
for page_filter in ['/subscription', '/about']:
    print(f"\n=== KEYWORDS FOR {page_filter} (Last 90 days) ===")
    print(f"{'Clicks':>8} {'Impr':>8} {'CTR':>7} {'Pos':>6}  Query")
    print("-" * 80)

    request3 = {
        'startDate': '2025-01-01',
        'endDate': '2026-04-07',
        'dimensions': ['query'],
        'dimensionFilterGroups': [{
            'filters': [{
                'dimension': 'page',
                'operator': 'contains',
                'expression': page_filter
            }]
        }],
        'rowLimit': 30,
        'dataState': 'all'
    }

    try:
        response3 = service.searchanalytics().query(siteUrl=site_url, body=request3).execute()
        rows = response3.get('rows', [])
        if not rows:
            print("  (no data)")
        for row in rows:
            q = row['keys'][0]
            clicks = row.get('clicks', 0)
            impressions = row.get('impressions', 0)
            ctr = row.get('ctr', 0) * 100
            pos = row.get('position', 0)
            print(f"{clicks:>8} {impressions:>8} {ctr:>6.1f}% {pos:>5.1f}  {q}")
    except Exception as e:
        print(f"Error: {e}")

# Query 4: Keywords by click — what's driving traffic now
print("\n=== TOP CONVERTING KEYWORDS (clicks > 0, sorted by clicks) ===")
print(f"{'Clicks':>8} {'Impr':>8} {'CTR':>7} {'Pos':>6}  Query")
print("-" * 80)

request4 = {
    'startDate': '2025-01-01',
    'endDate': '2026-04-07',
    'dimensions': ['query'],
    'rowLimit': 100,
    'dataState': 'all'
}

try:
    response4 = service.searchanalytics().query(siteUrl=site_url, body=request4).execute()
    clicked = [r for r in response4.get('rows', []) if r.get('clicks', 0) > 0]
    clicked.sort(key=lambda x: x['clicks'], reverse=True)
    for row in clicked[:40]:
        q = row['keys'][0]
        clicks = row.get('clicks', 0)
        impressions = row.get('impressions', 0)
        ctr = row.get('ctr', 0) * 100
        pos = row.get('position', 0)
        print(f"{clicks:>8} {impressions:>8} {ctr:>6.1f}% {pos:>5.1f}  {q}")
except Exception as e:
    print(f"Error: {e}")

# === COMMUNITY GROCERIES ===
cg_url = 'https://communitygroceries.com/'
print("\n\n" + "=" * 80)
print("=== COMMUNITY GROCERIES — communitygroceries.com ===")
print("=" * 80)

print("\n=== CG TOP KEYWORDS (All time) ===")
print(f"{'Clicks':>8} {'Impr':>8} {'CTR':>7} {'Pos':>6}  Query")
print("-" * 80)

cg_req = {
    'startDate': '2025-01-01',
    'endDate': '2026-04-07',
    'dimensions': ['query'],
    'rowLimit': 50,
    'dataState': 'all'
}

try:
    cg_resp = service.searchanalytics().query(siteUrl=cg_url, body=cg_req).execute()
    for row in cg_resp.get('rows', []):
        q = row['keys'][0]
        clicks = row.get('clicks', 0)
        impressions = row.get('impressions', 0)
        ctr = row.get('ctr', 0) * 100
        pos = row.get('position', 0)
        print(f"{clicks:>8} {impressions:>8} {ctr:>6.1f}% {pos:>5.1f}  {q}")
    if not cg_resp.get('rows'):
        print("  (no data)")
except Exception as e:
    print(f"CG Error: {e}")

print("\n=== CG TOP PAGES (All time) ===")
print(f"{'Clicks':>8} {'Impr':>8} {'CTR':>7} {'Pos':>6}  Page")
print("-" * 80)

cg_req2 = {
    'startDate': '2025-01-01',
    'endDate': '2026-04-07',
    'dimensions': ['page'],
    'rowLimit': 25,
    'dataState': 'all'
}

try:
    cg_resp2 = service.searchanalytics().query(siteUrl=cg_url, body=cg_req2).execute()
    for row in cg_resp2.get('rows', []):
        page = row['keys'][0].replace('https://communitygroceries.com', '')
        clicks = row.get('clicks', 0)
        impressions = row.get('impressions', 0)
        ctr = row.get('ctr', 0) * 100
        pos = row.get('position', 0)
        print(f"{clicks:>8} {impressions:>8} {ctr:>6.1f}% {pos:>5.1f}  {page or '/'}")
    if not cg_resp2.get('rows'):
        print("  (no data)")
except Exception as e:
    print(f"CG Error: {e}")
