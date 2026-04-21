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
    async with httpx.AsyncClient(timeout=45.0) as client:
        r = await client.get(f"{base}/api/labat/page/feed", params={"limit": 5}, headers=headers)
        print({"feed_status": r.status_code})
        if r.status_code != 200:
            print(r.text[:500])
            return
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        posts = data.get("data", []) if isinstance(data, dict) else []
        print({"posts": len(posts), "ids": [p.get("id") for p in posts]})
        if not posts:
            return
        pid = posts[0].get("id")
        d = await client.delete(f"{base}/api/labat/posts/{quote(str(pid), safe='')}", headers=headers)
        print({"delete_status": d.status_code, "pid": pid, "delete_body": d.text[:500]})


asyncio.run(main())
