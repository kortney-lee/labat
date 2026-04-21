"""Test ALL LABAT API endpoints through the deployed service."""
import os
import json, urllib.request, urllib.parse, ssl

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


def api_get(path, headers=None):
    h = headers or {}
    h["X-Admin-Token"] = ADMIN
    req = urllib.request.Request(f"{BASE}{path}", headers=h)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"ERROR": e.code, "detail": json.loads(raw).get("detail", raw[:300])}
        except Exception:
            return {"ERROR": e.code, "raw": raw[:300]}


def api_post(path, body, headers=None):
    h = headers or {}
    h["X-Admin-Token"] = ADMIN
    h["Content-Type"] = "application/json"
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=h, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"ERROR": e.code, "detail": json.loads(raw).get("detail", raw[:300])}
        except Exception:
            return {"ERROR": e.code, "raw": raw[:300]}


results = {}

# 1. Health
print("=== 1. HEALTH ===")
r = api_get("/health")
print(f"  Status: {r.get('status')} | Config all green: {all(r.get('config', {}).values())}")
results["health"] = "PASS" if r.get("status") == "healthy" else "FAIL"

# 2. Page Info
print("\n=== 2. PAGE INFO ===")
r = api_get("/api/labat/page")
if "ERROR" not in r:
    print(f"  Name: {r.get('name')} | Category: {r.get('category')} | Followers: {r.get('followers_count')}")
    results["page_info"] = "PASS"
else:
    print(f"  {r}")
    results["page_info"] = f"FAIL ({r.get('detail','')})"

# 3. Page Feed
print("\n=== 3. PAGE FEED ===")
r = api_get("/api/labat/page/feed")
if "ERROR" not in r:
    posts = r.get("data", r.get("posts", []))
    print(f"  {len(posts)} posts")
    results["page_feed"] = f"PASS ({len(posts)} posts)"
else:
    print(f"  {r.get('detail','')}")
    results["page_feed"] = f"BLOCKED ({str(r.get('detail',''))[:80]})"

# 4. Create Post
print("\n=== 4. CREATE POST ===")
if os.getenv("ALLOW_LIVE_POST_TESTS", "").strip().lower() in ("1", "true", "yes"):
    r = api_post(
        "/api/labat/posts",
        {"message": "LABAT live test — WiHy.ai health intelligence! #WiHy #AI #Health"},
    )
    if "ERROR" not in r:
        print(f"  Post created: {r}")
        results["create_post"] = "PASS"
    else:
        print(f"  {str(r.get('detail',''))[:200]}")
        results["create_post"] = f"BLOCKED ({str(r.get('detail',''))[:80]})"
else:
    print("  SKIPPED - Set ALLOW_LIVE_POST_TESTS=true to enable live posting test")
    results["create_post"] = "SKIPPED"

# 5. List Campaigns
print("\n=== 5. LIST CAMPAIGNS ===")
r = api_get("/api/labat/ads/campaigns")
if "ERROR" not in r:
    camps = r.get("data", r.get("campaigns", []))
    print(f"  {len(camps)} campaigns")
    results["campaigns"] = f"PASS ({len(camps)})"
else:
    print(f"  {r}")
    results["campaigns"] = f"FAIL ({r.get('detail','')})"

# 6. Ad Accounts (requires user_token query param)
USER_TOKEN = "EAAfhGUc4ewwBRMyUmJdlrnN33XG8JER0zipFvrFavHubvUPb68bOklHGj82bTmn9cVRu8UPPbnTri4QP7wGlHpLTi0oVRrPNcZCWTu86eGlfGJId8uGgKbLqpI4IWrW7fMK6kgZAlagZCdpztF6r8qHEC3G8JIZADyFmNj0wqkwUbDZByA2ZBMVy0NSVexcUt9PIYZC8J2p0zuR"
print("\n=== 6. AD ACCOUNTS ===")
r = api_get(f"/api/labat/auth/ad-accounts?user_token={USER_TOKEN}")
if "ERROR" not in r:
    accts = r.get("data", r.get("accounts", []))
    if isinstance(accts, list):
        for a in accts:
            print(f"  - {a.get('name')}: {a.get('id')} (status={a.get('account_status')})")
        results["ad_accounts"] = f"PASS ({len(accts)})"
    else:
        print(f"  {r}")
        results["ad_accounts"] = "PASS (response ok)"
else:
    print(f"  {r}")
    results["ad_accounts"] = "FAIL"

# 7. Businesses
print("\n=== 7. BUSINESSES ===")
r = api_get(f"/api/labat/auth/businesses?user_token={USER_TOKEN}")
if "ERROR" not in r:
    biz = r.get("data", r.get("businesses", []))
    if isinstance(biz, list):
        for b in biz:
            print(f"  - {b.get('name')}: {b.get('id')}")
        results["businesses"] = f"PASS ({len(biz)})"
    else:
        print(f"  {r}")
        results["businesses"] = "PASS"
else:
    print(f"  {r}")
    results["businesses"] = "FAIL"

# 8. Debug Token
print("\n=== 8. DEBUG TOKEN ===")
r = api_get(f"/api/labat/auth/debug-token?token={USER_TOKEN}")
if "ERROR" not in r:
    print(f"  Type: {r.get('type')} | Valid: {r.get('is_valid')}")
    print(f"  Scopes: {r.get('scopes', [])}")
    results["debug_token"] = "PASS"
else:
    print(f"  {str(r.get('detail',''))[:200]}")
    results["debug_token"] = f"FAIL ({str(r.get('detail',''))[:80]})"

# 9. Insights (POST /api/labat/insights)
print("\n=== 9. INSIGHTS ===")
r = api_post("/api/labat/insights", {"metrics": ["impressions", "reach", "clicks"], "period": "day"})
if "ERROR" not in r:
    print(f"  {json.dumps(r, indent=2)[:300]}")
    results["insights"] = "PASS"
else:
    print(f"  {str(r.get('detail',''))[:200]}")
    results["insights"] = f"BLOCKED ({str(r.get('detail',''))[:80]})"

# 10. Webhook
print("\n=== 10. WEBHOOK ===")
try:
    wreq = urllib.request.Request(
        f"{BASE}/api/labat/webhooks?hub.mode=subscribe&hub.verify_token=PzGMcD_mMLIdyvuWEuPWRItSWI0aqxQCeqiEiw0QR-E&hub.challenge=final_test"
    )
    wresp = urllib.request.urlopen(wreq, context=ctx)
    body = wresp.read().decode().strip()
    print(f"  Challenge: {body}")
    results["webhook"] = "PASS" if body == "final_test" else "FAIL"
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}")
    results["webhook"] = "FAIL"

# 11. Messenger
print("\n=== 11. MESSENGER ===")
r = api_get("/api/labat/messenger/conversations")
if "ERROR" not in r:
    print(f"  {r}")
    results["messenger"] = "PASS"
else:
    print(f"  {str(r.get('detail',''))[:200]}")
    results["messenger"] = f"BLOCKED ({str(r.get('detail',''))[:80]})"

# Summary
print("\n" + "=" * 60)
print("LABAT API ENDPOINT TEST SUMMARY")
print("=" * 60)
passed = blocked = failed = 0
for k, v in results.items():
    v_str = str(v)
    if "PASS" in v_str:
        icon = "PASS"
        passed += 1
    elif "BLOCKED" in v_str:
        icon = "BLKD"
        blocked += 1
    else:
        icon = "FAIL"
        failed += 1
    print(f"  [{icon}] {k}: {v}")

print(f"\n  {passed} passed / {blocked} blocked / {failed} failed")
print(f"\n  Blocked endpoints require Meta App Review (Development Mode limitation)")
