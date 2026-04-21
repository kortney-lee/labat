"""Full LABAT live test with provided token."""
import json
import urllib.request
import ssl
import datetime
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
TOKEN = (
    "EAAfhGUc4ewwBROnm3m7CKSskz48EoU10rCutfHHZBIHGAAbpZBX3Siqwoj2Nr4YoN6BK63cJfdUPHIRN9zZCndVSFIROSHfc2CGBB3X3thDImezvqlJZANXnr7sLzv3Q1Gn8q82oLVaQsoCtMVmvUVBTaA5I5rssnghwF1zAZCkF7MF4ri6USZCOo5Dj3TBQJkkFvZAjZCXDOrxuPYPRiTnCkQh2jZAIG7ZCOVdBDSZBqLWMHOnc1WF21z6OIX1A5DUVPsYfZBsGcPL6vYEFdUw2sLNc7ffZCmrIN3YCZByQZDZD"
)
APP_TOKEN = "2217823522290444|5188a2075129fb4f93b4ef08da0cf3a1"


def graph_get(path, params=None, token=None):
    t = token or TOKEN
    p = params or {}
    p["access_token"] = t
    qs = "&".join(f"{k}={v}" for k, v in p.items())
    url = f"https://graph.facebook.com/v21.0/{path}?{qs}"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"ERROR": e.code, "msg": json.loads(raw).get("error", {}).get("message", "")[:300]}
        except Exception:
            return {"ERROR": e.code, "raw": raw[:300]}


def graph_post(path, body, token=None):
    t = token or TOKEN
    body["access_token"] = t
    data = urllib.parse.urlencode(body).encode()
    url = f"https://graph.facebook.com/v21.0/{path}"
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return {"ERROR": e.code, "msg": json.loads(raw).get("error", {}).get("message", "")[:300]}
        except Exception:
            return {"ERROR": e.code, "raw": raw[:300]}


import urllib.parse

results = {}

# 0. Debug Token
print("=== 0. DEBUG TOKEN ===")
r = graph_get("debug_token", {"input_token": TOKEN}, token=APP_TOKEN)
ti = r.get("data", r)
if "ERROR" not in r:
    print(f"  Type: {ti.get('type')}")
    print(f"  App ID: {ti.get('app_id')}")
    print(f"  Valid: {ti.get('is_valid')}")
    print(f"  User ID: {ti.get('user_id')}")
    print(f"  Scopes: {ti.get('scopes', [])}")
    exp = ti.get("expires_at", 0)
    if exp == 0:
        print("  Expires: NEVER (long-lived)")
    else:
        print(f"  Expires: {datetime.datetime.fromtimestamp(exp)}")
    results["debug_token"] = "PASS"
else:
    print(f"  {r}")
    results["debug_token"] = "FAIL"

# 1. Page Info
print("\n=== 1. PAGE INFO (WiHy.ai) ===")
r = graph_get(PAGE_ID, {"fields": "id,name,category,fan_count,followers_count,about"})
if "ERROR" not in r:
    print(f"  Name: {r.get('name')} | Category: {r.get('category')} | Followers: {r.get('followers_count')}")
    print(f"  About: {str(r.get('about',''))[:100]}")
    results["page_info"] = "PASS"
else:
    print(f"  {r}")
    results["page_info"] = f"FAIL ({r.get('msg','')})"

# 2. Page Feed
print("\n=== 2. PAGE FEED ===")
r = graph_get(f"{PAGE_ID}/feed", {"fields": "id,message,created_time,type", "limit": "5"})
if "ERROR" not in r:
    posts = r.get("data", [])
    print(f"  {len(posts)} posts found")
    for p in posts[:3]:
        msg = str(p.get("message", ""))[:80]
        print(f"    - [{p.get('type','?')}] {msg}")
    results["page_feed"] = f"PASS ({len(posts)} posts)"
else:
    print(f"  BLOCKED: {r.get('msg','')[:150]}")
    results["page_feed"] = "BLOCKED"

# 3. Create Post
print("\n=== 3. CREATE POST ===")
if os.getenv("ALLOW_LIVE_POST_TESTS", "").strip().lower() in ("1", "true", "yes"):
    r = graph_post(
        f"{PAGE_ID}/feed",
        {
            "message": (
                "LABAT live test - WiHy AI health intelligence platform! "
                "#WiHy #HealthTech #AI"
            )
        },
    )
    if "ERROR" not in r:
        post_id = r.get("id", "")
        print(f"  POST CREATED! ID: {post_id}")
        results["create_post"] = f"PASS (id={post_id})"
    else:
        print(f"  {r.get('msg','')[:200]}")
        results["create_post"] = f"BLOCKED ({r.get('msg','')[:80]})"
else:
    print("  SKIPPED - Set ALLOW_LIVE_POST_TESTS=true to enable live posting test")
    results["create_post"] = "SKIPPED"

# 4. Page Insights
print("\n=== 4. PAGE INSIGHTS ===")
r = graph_get(f"{PAGE_ID}/insights", {"metric": "page_impressions,page_engaged_users", "period": "day"})
if "ERROR" not in r:
    metrics = r.get("data", [])
    print(f"  {len(metrics)} metrics returned")
    for m in metrics[:3]:
        print(f"    - {m.get('name')}: {m.get('values', [{}])[0].get('value', '?')}")
    results["page_insights"] = "PASS"
else:
    print(f"  {r.get('msg','')[:200]}")
    results["page_insights"] = f"BLOCKED ({r.get('msg','')[:80]})"

# 5. Ad Accounts
print("\n=== 5. AD ACCOUNTS ===")
r = graph_get("me/adaccounts", {"fields": "id,name,account_status,currency"})
if "ERROR" not in r:
    accts = r.get("data", [])
    for a in accts:
        print(f"  - {a.get('name')}: {a.get('id')} (status={a.get('account_status')})")
    results["ad_accounts"] = f"PASS ({len(accts)} accounts)"
else:
    print(f"  {r}")
    results["ad_accounts"] = "FAIL"

# 6. List Campaigns
print("\n=== 6. LIST CAMPAIGNS ===")
if results.get("ad_accounts", "").startswith("PASS"):
    r = graph_get("act_1075556919305762/campaigns", {"fields": "id,name,status,objective", "limit": "10"})
    if "ERROR" not in r:
        camps = r.get("data", [])
        print(f"  {len(camps)} campaigns")
        for c in camps[:5]:
            print(f"    - {c.get('name')}: {c.get('status')} ({c.get('objective')})")
        results["campaigns"] = f"PASS ({len(camps)})"
    else:
        print(f"  {r.get('msg','')[:200]}")
        results["campaigns"] = f"BLOCKED ({r.get('msg','')[:80]})"
else:
    print("  Skipped (no ad accounts)")
    results["campaigns"] = "SKIPPED"

# 7. Conversations (Messenger)
print("\n=== 7. MESSENGER CONVERSATIONS ===")
r = graph_get(f"{PAGE_ID}/conversations", {"fields": "id,updated_time,participants"})
if "ERROR" not in r:
    convos = r.get("data", [])
    print(f"  {len(convos)} conversations")
    results["messenger"] = f"PASS ({len(convos)} convos)"
else:
    print(f"  {r.get('msg','')[:200]}")
    results["messenger"] = f"BLOCKED ({r.get('msg','')[:80]})"

# 8. Leads (leadgen forms)
print("\n=== 8. LEAD FORMS ===")
r = graph_get(f"{PAGE_ID}/leadgen_forms", {"fields": "id,name,status"})
if "ERROR" not in r:
    forms = r.get("data", [])
    print(f"  {len(forms)} lead forms")
    results["leads"] = f"PASS ({len(forms)} forms)"
else:
    print(f"  {r.get('msg','')[:200]}")
    results["leads"] = f"BLOCKED ({r.get('msg','')[:80]})"

# 9. Webhook
print("\n=== 9. WEBHOOK VERIFY ===")
try:
    wreq = urllib.request.Request(
        f"{BASE}/api/labat/webhooks?hub.mode=subscribe&hub.verify_token=PzGMcD_mMLIdyvuWEuPWRItSWI0aqxQCeqiEiw0QR-E&hub.challenge=full_test_ok",
    )
    wresp = urllib.request.urlopen(wreq, context=ctx)
    wbody = wresp.read().decode()
    print(f"  Challenge: {wbody.strip()}")
    results["webhook"] = "PASS"
except urllib.error.HTTPError as e:
    print(f"  FAIL - HTTP {e.code}")
    results["webhook"] = "FAIL"

# Summary
print("\n" + "=" * 60)
print("FULL TEST SUMMARY")
print("=" * 60)
for k, v in results.items():
    if "PASS" in str(v):
        icon = "PASS"
    elif "BLOCKED" in str(v):
        icon = "BLKD"
    else:
        icon = "FAIL"
    print(f"  [{icon}] {k}: {v}")

passed = sum(1 for v in results.values() if "PASS" in str(v))
blocked = sum(1 for v in results.values() if "BLOCKED" in str(v))
failed = sum(1 for v in results.values() if "FAIL" in str(v) and "BLOCKED" not in str(v))
print(f"\n  {passed} passed / {blocked} blocked / {failed} failed")
