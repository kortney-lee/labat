import os
import asyncio
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()
admin = os.getenv("INTERNAL_ADMIN_TOKEN", "").strip()
base = "https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app"
headers = {"X-Admin-Token": admin}


async def main():
    deleted = 0
    failed = 0
    seen = 0
    async with httpx.AsyncClient(timeout=45.0) as client:
        for round_no in range(1, 21):
            r = await client.get(f"{base}/api/labat/page/feed", params={"limit": 50}, headers=headers)
            if r.status_code != 200:
                print({"round": round_no, "feed_error": r.status_code, "body": r.text[:200]})
                break
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            posts = data.get("data", []) if isinstance(data, dict) else []
            ids = [p.get("id") for p in posts if isinstance(p, dict) and p.get("id")]
            print({"round": round_no, "count": len(ids), "sample_ids": ids[:5]})
            if not ids:
                break

            for pid in ids:
                seen += 1
                d = await client.delete(f"{base}/api/labat/posts/{quote(str(pid), safe='')}", headers=headers)
                if d.status_code == 200:
                    deleted += 1
                else:
                    failed += 1
                    print({"pid": pid, "status": d.status_code, "body": d.text[:180]})

        vr = await client.get(f"{base}/api/labat/page/feed", params={"limit": 20}, headers=headers)
        remaining_ids = []
        if vr.status_code == 200 and vr.headers.get("content-type", "").startswith("application/json"):
            vj = vr.json()
            remaining_ids = [p.get("id") for p in vj.get("data", []) if isinstance(p, dict) and p.get("id")]

    print({"result": {"deleted": deleted, "failed": failed, "seen": seen, "remaining_count": len(remaining_ids), "remaining_ids": remaining_ids}})


asyncio.run(main())
