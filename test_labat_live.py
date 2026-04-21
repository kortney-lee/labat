"""Quick live test of all LABAT endpoints against WiHy.ai page."""
import json
import urllib.request
import ssl
import os

if os.getenv("ENABLE_MANUAL_TEST_SCRIPTS", "").strip().lower() not in (
    "1",
    "true",
    "yes",
):
    raise SystemExit(
        "Test scripts are disabled. Set ENABLE_MANUAL_TEST_SCRIPTS=true "
        "for intentional manual runs."
    )

ctx = ssl.create_default_context()
BASE = "https://wihy-labat-n4l2vldq3q-uc.a.run.app"
ADMIN = "wihy-admin-token-2026"
PAGE_ID = "937763702752161"
LONG_TOKEN = (
    "EAAfhGUc4ewwBRNQtbd6fZBZBxRBf16HYhNUpRCx4M1Ctj4GuwgsY1XV2IinyrZCsgE93F8Xk45jXrjWsZBjr4AijlsSSY5ha8JBPegn9v5nGaJ5fnbZCMXAnsgOeuS8TWZBZAeFGAouwqqj2xEc9eXsOTPC2j9pZBxab9WZBwc8dt5QBKYmuZCAiaIDjz7NWUX1wkwwo0c69I3WArevavaSXVx6AwZD"
)


def get(path):
    req = urllib.request.Request(f"{BASE}{path}", headers={"X-Admin-Token": ADMIN})
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"ERROR": e.code, "detail": json.loads(raw).get("detail", "")[:300]}
        except Exception:
            return {"ERROR": e.code, "raw": raw[:300]}


def post(path, body):
    data = json.dumps(body).encode()
    hdrs = {"X-Admin-Token": ADMIN, "Content-Type": "application/json"}
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=hdrs, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"ERROR": e.code, "detail": json.loads(raw).get("detail", "")[:300]}
        except Exception:
            return {"ERROR": e.code, "raw": raw[:300]}


results = {}

# 1. Page Info
print("=== 1. PAGE INFO (WiHy.ai) ===")
r = get(f"/api/labat/page?page_id={PAGE_ID}")
if "ERROR" not in r:
    print(f"  OK - Name: {r.get('name')} | Category: {r.get('category')} | Followers: {r.get('followers_count')}")
    results["page_info"] = "PASS"
else:
    print(f"  FAIL - {r}")
    results["page_info"] = "FAIL"

# 2. Page Feed
print("\n=== 2. PAGE FEED ===")
r = get(f"/api/labat/page/feed?page_id={PAGE_ID}&limit=3")
if "ERROR" not in r:
    print(f"  OK - {len(r.get('data', []))} posts")
    results["page_feed"] = "PASS"
else:
    print(f"  BLOCKED - {str(r.get('detail',''))[:150]}")
    results["page_feed"] = "BLOCKED (needs pages_read_engagement)"

# 3. Create Post
print("\n=== 3. CREATE POST ===")
if os.getenv("ALLOW_LIVE_POST_TESTS", "").strip().lower() in ("1", "true", "yes"):
    r = post("/api/labat/posts", {
        "message": "LABAT automation test - WiHy AI health intelligence platform #WiHy #HealthTech",
        "page_id": PAGE_ID,
    })
    if "ERROR" not in r:
        post_id = r.get("id", "")
        print(f"  OK - Post created: {post_id}")
        results["create_post"] = f"PASS (id={post_id})"
    else:
        print(f"  RESULT - {json.dumps(r)[:300]}")
        results["create_post"] = f"FAIL/BLOCKED ({r.get('detail','')[:100]})"
else:
    print("  SKIPPED - Set ALLOW_LIVE_POST_TESTS=true to enable live posting test")
    results["create_post"] = "SKIPPED"

# 4. List Campaigns
print("\n=== 4. LIST CAMPAIGNS ===")
r = get("/api/labat/ads/campaigns?limit=3")
if "ERROR" not in r:
    campaigns = r.get("data", r.get("campaigns", []))
    print(f"  OK - {len(campaigns) if isinstance(campaigns, list) else '?'} campaigns")
    results["list_campaigns"] = "PASS"
else:
    print(f"  RESULT - {json.dumps(r)[:300]}")
    results["list_campaigns"] = f"FAIL ({r.get('detail','')[:100]})"

# 5. Ad Accounts
print("\n=== 5. AD ACCOUNTS ===")
r = get(f"/api/labat/auth/ad-accounts?user_token={LONG_TOKEN}")
if "ERROR" not in r:
    accts = r.get("ad_accounts", [])
    for a in accts:
        print(f"  - {a.get('name')}: {a.get('ad_account_id')}")
    results["ad_accounts"] = f"PASS ({len(accts)} accounts)"
else:
    print(f"  RESULT - {json.dumps(r)[:300]}")
    results["ad_accounts"] = "FAIL"

# 6. Businesses
print("\n=== 6. BUSINESSES ===")
r = get(f"/api/labat/auth/businesses?user_token={LONG_TOKEN}")
if "ERROR" not in r:
    biz = r.get("businesses", [])
    for b in biz:
        print(f"  - {b.get('name')}: {b.get('id')}")
    results["businesses"] = f"PASS ({len(biz)} businesses)"
else:
    print(f"  RESULT - {json.dumps(r)[:300]}")
    results["businesses"] = "FAIL"

# 7. Debug Token
print("\n=== 7. DEBUG TOKEN ===")
r = get(f"/api/labat/auth/debug-token?token={LONG_TOKEN}")
if "ERROR" not in r:
    ti = r.get("token_info", {})
    print(f"  App ID: {ti.get('app_id')} | Type: {ti.get('type')} | Valid: {ti.get('is_valid')}")
    print(f"  Scopes: {ti.get('scopes', [])}")
    results["debug_token"] = "PASS"
else:
    print(f"  RESULT - {json.dumps(r)[:300]}")
    results["debug_token"] = "FAIL"

# 8. Page Insights
print("\n=== 8. PAGE INSIGHTS ===")
r = get(f"/api/labat/insights/page?page_id={PAGE_ID}")
if "ERROR" not in r:
    print(f"  OK - Got insights data")
    results["page_insights"] = "PASS"
else:
    print(f"  RESULT - {str(r.get('detail',''))[:200]}")
    results["page_insights"] = f"BLOCKED ({str(r.get('detail',''))[:80]})"

# 9. Webhook verify
print("\n=== 9. WEBHOOK VERIFY ===")
try:
    wreq = urllib.request.Request(
        f"{BASE}/api/labat/webhooks?hub.mode=subscribe&hub.verify_token=PzGMcD_mMLIdyvuWEuPWRItSWI0aqxQCeqiEiw0QR-E&hub.challenge=live_test_ok",
        headers={"X-Admin-Token": ADMIN},
    )
    wresp = urllib.request.urlopen(wreq, context=ctx)
    wbody = wresp.read().decode()
    if wbody.strip() == "live_test_ok":
        print(f"  OK - Challenge returned: {wbody.strip()}")
        results["webhook"] = "PASS"
    else:
        print(f"  Unexpected response: {wbody[:100]}")
        results["webhook"] = "FAIL"
except urllib.error.HTTPError as e:
    print(f"  FAIL - HTTP {e.code}")
    results["webhook"] = "FAIL"

# Summary
print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)
for k, v in results.items():
    status = "PASS" if "PASS" in str(v) else ("BLOCKED" if "BLOCKED" in str(v) else "FAIL")
    icon = {"PASS": "+", "BLOCKED": "~", "FAIL": "X"}[status]
    print(f"  [{icon}] {k}: {v}")
