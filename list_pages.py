"""List all Facebook pages the system user token has access to."""
import requests
import os
import json

token = os.environ["META_SYSTEM_USER_TOKEN"]

# 1. Pages via /me/accounts
print("=" * 60)
print("/me/accounts (pages this token can manage)")
print("=" * 60)
r = requests.get("https://graph.facebook.com/v25.0/me/accounts", params={
    "access_token": token,
    "fields": "id,name,category,fan_count,link,verification_status",
    "limit": 50,
})
data = r.json()
if "data" in data:
    for p in data["data"]:
        print(f"  {p.get('name','?'):40s} | ID: {p['id']:20s} | {p.get('category','?')}")
        print(f"    Fans: {p.get('fan_count','?')}  Link: {p.get('link','?')}")
    print(f"\n  Total: {len(data['data'])} pages")
else:
    print(json.dumps(data, indent=2))

# 2. Business owned pages
print("\n" + "=" * 60)
print("Business 4867231843349033 /owned_pages")
print("=" * 60)
r2 = requests.get("https://graph.facebook.com/v25.0/4867231843349033/owned_pages", params={
    "access_token": token,
    "fields": "id,name,category,fan_count,link,verification_status",
    "limit": 50,
})
data2 = r2.json()
if "data" in data2:
    for p in data2["data"]:
        print(f"  {p.get('name','?'):40s} | ID: {p['id']:20s} | {p.get('category','?')}")
        print(f"    Fans: {p.get('fan_count','?')}  Link: {p.get('link','?')}")
    print(f"\n  Total: {len(data2['data'])} pages")
else:
    print(json.dumps(data2, indent=2))

# 3. Cross-reference with our brands.py
print("\n" + "=" * 60)
print("Cross-reference with src/labat/brands.py")
print("=" * 60)
from src.labat.brands import BRAND_PAGE_IDS, BRAND_DOMAINS

all_api_ids = set()
if "data" in data:
    all_api_ids.update(p["id"] for p in data["data"])
if "data" in data2:
    all_api_ids.update(p["id"] for p in data2["data"])

for brand, page_id in BRAND_PAGE_IDS.items():
    domain = BRAND_DOMAINS.get(brand, "?")
    status = "OK - found in API" if page_id in all_api_ids else "MISSING - not in API!"
    print(f"  {brand:25s} | {page_id} | {domain:30s} | {status}")

# Check for pages in API not in our config
unknown = all_api_ids - set(BRAND_PAGE_IDS.values())
if unknown:
    print(f"\n  Pages in API but NOT in brands.py: {unknown}")
