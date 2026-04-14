import json
import urllib.request

url = "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app/generate-hero-image"
payload = json.dumps({
    "topic": "high protein meal prep",
    "brand": "communitygroceries",
    "slug": "test-hero-check"
}).encode()

req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
try:
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.load(resp)
    print("status:", resp.status)
    print("keys:", list(data.keys()))
    if data.get("url"):
        print("url:", data["url"][:150])
    if data.get("imageBase64"):
        print("base64 length:", len(data["imageBase64"]))
    if not data.get("url") and not data.get("imageBase64"):
        print("response:", json.dumps(data)[:500])
except urllib.error.HTTPError as he:
    body = he.read().decode("utf-8", errors="replace")[:500]
    print("HTTP ERROR:", he.code, he.reason)
    print("Body:", body)
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:300])
