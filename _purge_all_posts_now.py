import asyncio
import os
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()
admin = os.getenv("INTERNAL_ADMIN_TOKEN", "").strip()
if not admin:
    raise SystemExit("Missing INTERNAL_ADMIN_TOKEN in environment")

services = [
    "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-vowels-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cn-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-pwc-n4l2vldq3q-uc.a.run.app",
]

headers = {"X-Admin-Token": admin}


async def purge_facebook(client: httpx.AsyncClient, base: str):
    deleted = 0
    failed = 0
    rounds = 0
    while rounds < 30:
        rounds += 1
        r = await client.get(
            f"{base}/api/labat/page/feed",
            params={"limit": 100},
            headers=headers,
        )
        if r.status_code != 200:
            return {"deleted": deleted, "failed": failed, "error": f"feed {r.status_code}: {r.text[:120]}"}
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        posts = data.get("data", []) if isinstance(data, dict) else []
        if not posts:
            break
        print(f"  facebook round {rounds}: deleting {len(posts)}", flush=True)
        for post in posts:
            pid = post.get("id")
            if not pid:
                continue
            d = await client.delete(
                f"{base}/api/labat/posts/{quote(str(pid), safe='')}",
                headers=headers,
            )
            if d.status_code == 200:
                deleted += 1
            else:
                failed += 1
    return {"deleted": deleted, "failed": failed, "rounds": rounds}


async def purge_linkedin(client: httpx.AsyncClient, base: str):
    deleted = 0
    failed = 0
    total = 0
    r = await client.get(
        f"{base}/api/engagement/linkedin/posts",
        params={"limit": 100},
        headers=headers,
    )
    if r.status_code != 200:
        return {"deleted": 0, "failed": 0, "total": 0, "error": f"list {r.status_code}: {r.text[:120]}"}
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    posts = body.get("posts", []) if isinstance(body, dict) else []
    print(f"  linkedin listed: {len(posts)}", flush=True)
    for post in posts:
        pid = post.get("id") or post.get("urn")
        if not pid:
            continue
        total += 1
        d = await client.delete(
            f"{base}/api/engagement/linkedin/posts/{quote(str(pid), safe='')}",
            headers=headers,
        )
        if d.status_code == 200:
            deleted += 1
        else:
            failed += 1
    return {"deleted": deleted, "failed": failed, "total": total}


async def main():
    summary = {}
    async with httpx.AsyncClient(timeout=45.0) as client:
        for base in services:
            print(f"== {base} ==", flush=True)
            fb = await purge_facebook(client, base)
            li = await purge_linkedin(client, base)
            summary[base] = {"facebook": fb, "linkedin": li}
            print(f"  summary: {summary[base]}", flush=True)
    print("FINAL:", summary, flush=True)


asyncio.run(main())
