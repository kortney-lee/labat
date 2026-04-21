import os
import json
import asyncio
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()
ADMIN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()
META_TOKEN = (os.getenv("META_SYSTEM_USER_TOKEN", "") or "").strip()
if not ADMIN or not META_TOKEN:
    raise SystemExit("Missing INTERNAL_ADMIN_TOKEN or META_SYSTEM_USER_TOKEN")

SHANIA_SERVICES = [
    "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-vowels-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cn-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-pwc-n4l2vldq3q-uc.a.run.app",
]
H = {"X-Admin-Token": ADMIN}


async def main():
    out = {"facebook": [], "instagram": [], "linkedin": [], "threads": "no delete endpoint discovered"}
    async with httpx.AsyncClient(timeout=35.0) as c:
        pages_r = await c.get("https://graph.facebook.com/v25.0/me/accounts", params={"access_token": META_TOKEN, "fields": "id,name,access_token", "limit": 200})
        pages = pages_r.json().get("data", []) if pages_r.status_code == 200 else []

        for p in pages:
            pid = p.get("id")
            ptoken = p.get("access_token")
            row = {"page_id": pid, "page_name": p.get("name"), "attempted": 0, "deleted": 0, "failed": 0, "remaining_sample": -1, "errors": []}
            if not pid or not ptoken:
                row["errors"].append("missing page token")
                out["facebook"].append(row)
                continue
            lr = await c.get(f"https://graph.facebook.com/v25.0/{pid}/posts", params={"access_token": ptoken, "fields": "id", "limit": 50})
            posts = lr.json().get("data", []) if lr.status_code == 200 and isinstance(lr.json(), dict) else []
            row["attempted"] = len(posts)
            for post in posts:
                post_id = post.get("id")
                if not post_id:
                    continue
                dr = await c.delete(f"https://graph.facebook.com/v25.0/{quote(str(post_id), safe='')}", params={"access_token": ptoken})
                if dr.status_code == 200:
                    row["deleted"] += 1
                else:
                    row["failed"] += 1
                    if len(row["errors"]) < 4:
                        row["errors"].append(f"{post_id} {dr.status_code}: {dr.text[:120]}")
            vr = await c.get(f"https://graph.facebook.com/v25.0/{pid}/posts", params={"access_token": ptoken, "fields": "id", "limit": 10})
            row["remaining_sample"] = len(vr.json().get("data", [])) if vr.status_code == 200 and isinstance(vr.json(), dict) else -1
            out["facebook"].append(row)

            ig_row = {"page_id": pid, "page_name": p.get("name"), "ig_account": None, "attempted": 0, "deleted": 0, "failed": 0, "remaining_sample": -1, "errors": []}
            ir = await c.get(f"https://graph.facebook.com/v25.0/{pid}", params={"access_token": ptoken, "fields": "instagram_business_account"})
            ig = ((ir.json() or {}).get("instagram_business_account") or {}).get("id") if ir.status_code == 200 else None
            ig_row["ig_account"] = ig
            if ig:
                ml = await c.get(f"https://graph.facebook.com/v25.0/{ig}/media", params={"access_token": ptoken, "fields": "id", "limit": 50})
                media = ml.json().get("data", []) if ml.status_code == 200 and isinstance(ml.json(), dict) else []
                ig_row["attempted"] = len(media)
                for m in media:
                    mid = m.get("id")
                    if not mid:
                        continue
                    dr = await c.delete(f"https://graph.facebook.com/v25.0/{quote(str(mid), safe='')}", params={"access_token": ptoken})
                    if dr.status_code == 200:
                        ig_row["deleted"] += 1
                    else:
                        ig_row["failed"] += 1
                        if len(ig_row["errors"]) < 4:
                            ig_row["errors"].append(f"{mid} {dr.status_code}: {dr.text[:120]}")
                mv = await c.get(f"https://graph.facebook.com/v25.0/{ig}/media", params={"access_token": ptoken, "fields": "id", "limit": 10})
                ig_row["remaining_sample"] = len(mv.json().get("data", [])) if mv.status_code == 200 and isinstance(mv.json(), dict) else -1
            else:
                ig_row["errors"].append("no instagram_business_account")
            out["instagram"].append(ig_row)

        for svc in SHANIA_SERVICES:
            lrow = {"service": svc, "attempted": 0, "deleted": 0, "failed": 0, "errors": []}
            lr = await c.get(f"{svc}/api/engagement/linkedin/posts", params={"limit": 100}, headers=H)
            if lr.status_code != 200:
                lrow["errors"].append(f"list {lr.status_code}: {lr.text[:120]}")
                out["linkedin"].append(lrow)
                continue
            posts = lr.json().get("posts", []) if isinstance(lr.json(), dict) else []
            lrow["attempted"] = len(posts)
            for post in posts:
                pid = post.get("id") or post.get("urn")
                if not pid:
                    continue
                dr = await c.delete(f"{svc}/api/engagement/linkedin/posts/{quote(str(pid), safe='')}", headers=H)
                if dr.status_code == 200:
                    lrow["deleted"] += 1
                else:
                    lrow["failed"] += 1
                    if len(lrow["errors"]) < 4:
                        lrow["errors"].append(f"{pid} {dr.status_code}: {dr.text[:120]}")
            out["linkedin"].append(lrow)

    print(json.dumps(out, indent=2))


asyncio.run(main())
