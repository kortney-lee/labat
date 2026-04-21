import os
import json
import asyncio
from urllib.parse import quote

import httpx
from dotenv import load_dotenv

load_dotenv()

ADMIN = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()
META_TOKEN = (os.getenv("META_SYSTEM_USER_TOKEN", "") or "").strip()

if not ADMIN:
    raise SystemExit("Missing INTERNAL_ADMIN_TOKEN")
if not META_TOKEN:
    raise SystemExit("Missing META_SYSTEM_USER_TOKEN")

SHANIA_SERVICES = [
    "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-vowels-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cn-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-pwc-n4l2vldq3q-uc.a.run.app",
]

HEADERS = {"X-Admin-Token": ADMIN}


async def get_pages(c):
    r = await c.get(
        "https://graph.facebook.com/v25.0/me/accounts",
        params={"access_token": META_TOKEN, "fields": "id,name,access_token", "limit": 200},
    )
    if r.status_code != 200:
        return [], f"me/accounts {r.status_code}: {r.text[:200]}"
    return r.json().get("data", []), None


async def list_all_ids(c, path, token, cap=500):
    ids = []
    after = None
    while len(ids) < cap:
        params = {"access_token": token, "fields": "id", "limit": 100}
        if after:
            params["after"] = after
        r = await c.get(f"https://graph.facebook.com/v25.0/{path}", params=params)
        if r.status_code != 200:
            return ids, f"list {path} {r.status_code}: {r.text[:180]}"
        j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        data = j.get("data", []) if isinstance(j, dict) else []
        if not data:
            break
        ids.extend([x.get("id") for x in data if x.get("id")])
        paging = j.get("paging", {}) if isinstance(j, dict) else {}
        cursors = paging.get("cursors", {}) if isinstance(paging, dict) else {}
        after = cursors.get("after") if isinstance(cursors, dict) else None
        if not after:
            break
    # unique preserve order
    uniq = list(dict.fromkeys(ids))
    return uniq, None


async def purge_fb(c, page):
    pid = page.get("id")
    token = page.get("access_token")
    out = {"page_id": pid, "page_name": page.get("name"), "listed": 0, "deleted": 0, "failed": 0, "remaining": -1, "errors": []}
    if not pid or not token:
        out["errors"].append("missing page token")
        return out
    ids, err = await list_all_ids(c, f"{pid}/posts", token, cap=1000)
    out["listed"] = len(ids)
    if err:
        out["errors"].append(err)
    for post_id in ids:
        d = await c.delete(f"https://graph.facebook.com/v25.0/{quote(str(post_id), safe='')}", params={"access_token": token})
        if d.status_code == 200:
            out["deleted"] += 1
        else:
            out["failed"] += 1
            if len(out["errors"]) < 6:
                out["errors"].append(f"delete {post_id} {d.status_code}: {d.text[:140]}")
    remain_ids, verr = await list_all_ids(c, f"{pid}/posts", token, cap=20)
    out["remaining"] = len(remain_ids)
    if verr:
        out["errors"].append(verr)
    return out


async def purge_ig(c, page):
    pid = page.get("id")
    token = page.get("access_token")
    out = {"page_id": pid, "page_name": page.get("name"), "ig_account": None, "listed": 0, "deleted": 0, "failed": 0, "remaining": -1, "errors": []}
    if not pid or not token:
        out["errors"].append("missing page token")
        return out
    r = await c.get(f"https://graph.facebook.com/v25.0/{pid}", params={"access_token": token, "fields": "instagram_business_account"})
    if r.status_code != 200:
        out["errors"].append(f"ig link {r.status_code}: {r.text[:180]}")
        return out
    ig = ((r.json() or {}).get("instagram_business_account") or {}).get("id")
    out["ig_account"] = ig
    if not ig:
        out["errors"].append("no instagram_business_account")
        return out
    ids, err = await list_all_ids(c, f"{ig}/media", token, cap=1000)
    out["listed"] = len(ids)
    if err:
        out["errors"].append(err)
    for media_id in ids:
        d = await c.delete(f"https://graph.facebook.com/v25.0/{quote(str(media_id), safe='')}", params={"access_token": token})
        if d.status_code == 200:
            out["deleted"] += 1
        else:
            out["failed"] += 1
            if len(out["errors"]) < 6:
                out["errors"].append(f"delete media {media_id} {d.status_code}: {d.text[:140]}")
    remain_ids, verr = await list_all_ids(c, f"{ig}/media", token, cap=20)
    out["remaining"] = len(remain_ids)
    if verr:
        out["errors"].append(verr)
    return out


async def purge_li(c, base):
    out = {"service": base, "listed": 0, "deleted": 0, "failed": 0, "errors": []}
    r = await c.get(f"{base}/api/engagement/linkedin/posts", params={"limit": 200}, headers=HEADERS)
    if r.status_code != 200:
        out["errors"].append(f"list {r.status_code}: {r.text[:180]}")
        return out
    posts = r.json().get("posts", []) if isinstance(r.json(), dict) else []
    out["listed"] = len(posts)
    for p in posts:
        post_id = p.get("id") or p.get("urn")
        if not post_id:
            continue
        d = await c.delete(f"{base}/api/engagement/linkedin/posts/{quote(str(post_id), safe='')}", headers=HEADERS)
        if d.status_code == 200:
            out["deleted"] += 1
        else:
            out["failed"] += 1
            if len(out["errors"]) < 6:
                out["errors"].append(f"delete {post_id} {d.status_code}: {d.text[:140]}")
    return out


async def main():
    report = {"facebook": [], "instagram": [], "linkedin": [], "threads": {"status": "no delete API in current service routes"}}
    async with httpx.AsyncClient(timeout=45.0) as c:
        pages, page_err = await get_pages(c)
        if page_err:
            report["facebook_error"] = page_err
            report["instagram_error"] = page_err
        else:
            for p in pages:
                report["facebook"].append(await purge_fb(c, p))
            for p in pages:
                report["instagram"].append(await purge_ig(c, p))
        for svc in SHANIA_SERVICES:
            report["linkedin"].append(await purge_li(c, svc))
    print(json.dumps(report, indent=2))


asyncio.run(main())
