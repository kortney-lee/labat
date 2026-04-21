import os
import asyncio
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()
admin = os.getenv("INTERNAL_ADMIN_TOKEN", "").strip()
base = "https://wihy-labat-n4l2vldq3q-uc.a.run.app"
headers = {"X-Admin-Token": admin}


async def main():
    deleted = 0
    failed = 0
    seen_ids = {}
    async with httpx.AsyncClient(timeout=45.0) as client:
        for round_no in range(1, 16):
            r = await client.get(f"{base}/api/labat/page/feed", params={"limit": 25}, headers=headers)
            if r.status_code != 200:
                print({"round": round_no, "feed_error": r.status_code, "body": r.text[:200]})
                break
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            posts = data.get("data", []) if isinstance(data, dict) else []
            ids = [p.get("id") for p in posts if p.get("id")]
            print({"round": round_no, "count": len(ids), "ids": ids[:5]})
            if not ids:
                break
            for pid in ids:
                seen_ids[pid] = seen_ids.get(pid, 0) + 1
                d = await client.delete(f"{base}/api/labat/posts/{quote(str(pid), safe='')}", headers=headers)
                if d.status_code == 200:
                    deleted += 1
                else:
                    failed += 1
                    print({"pid": pid, "status": d.status_code, "body": d.text[:180]})

        vr = await client.get(f"{base}/api/labat/page/feed", params={"limit": 25}, headers=headers)
        remaining = []
        if vr.status_code == 200 and vr.headers.get("content-type", "").startswith("application/json"):
            vj = vr.json()
            remaining = [p.get("id") for p in vj.get("data", []) if isinstance(vj, dict)]

    print({"result": {"deleted": deleted, "failed": failed, "remaining": remaining, "seen_ids": seen_ids}})


asyncio.run(main())
