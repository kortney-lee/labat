import os
import json
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

admin = (os.getenv("INTERNAL_ADMIN_TOKEN", "") or "").strip()
meta_token = (os.getenv("META_SYSTEM_USER_TOKEN", "") or "").strip()
threads_token = (os.getenv("THREADS_ACCESS_TOKEN", "") or os.getenv("INSTAGRAM_ACCESS_TOKEN", "") or "").strip()

services = [
    "https://wihy-shania-wihy-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cg-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-vowels-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-cn-n4l2vldq3q-uc.a.run.app",
    "https://wihy-shania-pwc-n4l2vldq3q-uc.a.run.app",
]

out = {
    "service_purge": {},
    "direct_graph": {"pages": {}},
    "threads_probe": {},
    "notes": [],
}

session = requests.Session()


def _json(resp):
    ctype = resp.headers.get("content-type", "")
    if "application/json" in ctype:
        try:
            return resp.json()
        except Exception:
            return {}
    return {}


def purge_fb_service(base):
    headers = {"X-Admin-Token": admin}
    deleted = 0
    failed = 0
    rounds = 0
    errors = []
    last_ids = []
    for _ in range(30):
        rounds += 1
        r = session.get(f"{base}/api/labat/page/feed", params={"limit": 100}, headers=headers, timeout=45)
        if r.status_code != 200:
            errors.append(f"feed {r.status_code}: {r.text[:180]}")
            break
        body = _json(r)
        posts = body.get("data", []) if isinstance(body, dict) else []
        ids = [p.get("id") for p in posts if isinstance(p, dict) and p.get("id")]
        last_ids = ids
        if not ids:
            break
        for pid in ids:
            d = session.delete(f"{base}/api/labat/posts/{quote(str(pid), safe='')}", headers=headers, timeout=45)
            if d.status_code == 200:
                deleted += 1
            else:
                failed += 1
                if len(errors) < 5:
                    errors.append(f"delete {pid}: {d.status_code} {d.text[:140]}")
    v = session.get(f"{base}/api/labat/page/feed", params={"limit": 20}, headers=headers, timeout=45)
    vb = _json(v) if v.status_code == 200 else {}
    remain = [p.get("id") for p in vb.get("data", []) if isinstance(vb, dict)] if isinstance(vb, dict) else []
    return {
        "deleted": deleted,
        "failed": failed,
        "rounds": rounds,
        "remaining_count": len(remain),
        "remaining_ids": remain,
        "errors": errors,
    }


def purge_linkedin_service(base):
    headers = {"X-Admin-Token": admin}
    deleted = 0
    failed = 0
    rounds = 0
    errors = []
    for _ in range(20):
        rounds += 1
        r = session.get(f"{base}/api/engagement/linkedin/posts", params={"limit": 100}, headers=headers, timeout=45)
        if r.status_code != 200:
            errors.append(f"list {r.status_code}: {r.text[:180]}")
            break
        body = _json(r)
        posts = body.get("posts", []) if isinstance(body, dict) else []
        ids = []
        for p in posts:
            if isinstance(p, dict):
                pid = p.get("id") or p.get("urn")
                if pid:
                    ids.append(str(pid))
        if not ids:
            break
        for pid in ids:
            d = session.delete(f"{base}/api/engagement/linkedin/posts/{quote(pid, safe='')}", headers=headers, timeout=45)
            if d.status_code == 200:
                deleted += 1
            else:
                failed += 1
                if len(errors) < 5:
                    errors.append(f"delete {pid}: {d.status_code} {d.text[:140]}")
    vr = session.get(f"{base}/api/engagement/linkedin/posts", params={"limit": 100}, headers=headers, timeout=45)
    vb = _json(vr) if vr.status_code == 200 else {}
    remain_posts = vb.get("posts", []) if isinstance(vb, dict) else []
    remain_ids = []
    for p in remain_posts:
        if isinstance(p, dict):
            pid = p.get("id") or p.get("urn")
            if pid:
                remain_ids.append(str(pid))
    return {
        "deleted": deleted,
        "failed": failed,
        "rounds": rounds,
        "remaining_count": len(remain_ids),
        "remaining_ids": remain_ids[:20],
        "errors": errors,
    }


if not admin:
    out["notes"].append("Missing INTERNAL_ADMIN_TOKEN")
else:
    for s in services:
        print(f"Service purge: {s}", flush=True)
        out["service_purge"][s] = {
            "facebook": purge_fb_service(s),
            "linkedin": purge_linkedin_service(s),
        }


# Direct Meta sweep across all pages the token can access
if not meta_token:
    out["notes"].append("Missing META_SYSTEM_USER_TOKEN (direct page sweep skipped)")
else:
    acc = session.get(
        "https://graph.facebook.com/v25.0/me/accounts",
        params={"access_token": meta_token, "fields": "id,name,access_token", "limit": 200},
        timeout=45,
    )
    if acc.status_code != 200:
        out["notes"].append(f"me/accounts failed: {acc.status_code} {acc.text[:180]}")
    else:
        pages = _json(acc).get("data", [])
        for p in pages:
            if not isinstance(p, dict):
                continue
            page_id = str(p.get("id", ""))
            page_name = p.get("name", "")
            page_token = p.get("access_token", "")
            if not page_id or not page_token:
                continue
            print(f"Direct page sweep: {page_name} ({page_id})", flush=True)
            pdata = {
                "name": page_name,
                "facebook": {"deleted": 0, "failed": 0, "remaining_count": 0, "remaining_ids": [], "errors": []},
                "instagram": {"ig_account": None, "deleted": 0, "failed": 0, "remaining_count": 0, "errors": []},
            }

            # Facebook delete by page token
            for _ in range(30):
                fr = session.get(
                    f"https://graph.facebook.com/v25.0/{page_id}/feed",
                    params={"access_token": page_token, "limit": 100, "fields": "id"},
                    timeout=45,
                )
                if fr.status_code != 200:
                    pdata["facebook"]["errors"].append(f"feed {fr.status_code}: {fr.text[:180]}")
                    break
                fbody = _json(fr)
                posts = fbody.get("data", []) if isinstance(fbody, dict) else []
                ids = [x.get("id") for x in posts if isinstance(x, dict) and x.get("id")]
                if not ids:
                    break
                for pid in ids:
                    dr = session.delete(
                        f"https://graph.facebook.com/v25.0/{pid}",
                        params={"access_token": page_token},
                        timeout=45,
                    )
                    if dr.status_code == 200:
                        dj = _json(dr)
                        if dj.get("success") is True:
                            pdata["facebook"]["deleted"] += 1
                        else:
                            pdata["facebook"]["failed"] += 1
                            if len(pdata["facebook"]["errors"]) < 5:
                                pdata["facebook"]["errors"].append(f"delete {pid}: 200 {dr.text[:140]}")
                    else:
                        pdata["facebook"]["failed"] += 1
                        if len(pdata["facebook"]["errors"]) < 5:
                            pdata["facebook"]["errors"].append(f"delete {pid}: {dr.status_code} {dr.text[:140]}")

            fv = session.get(
                f"https://graph.facebook.com/v25.0/{page_id}/feed",
                params={"access_token": page_token, "limit": 20, "fields": "id"},
                timeout=45,
            )
            if fv.status_code == 200:
                vbody = _json(fv)
                vids = [x.get("id") for x in vbody.get("data", []) if isinstance(vbody, dict) and isinstance(x, dict)]
                pdata["facebook"]["remaining_count"] = len(vids)
                pdata["facebook"]["remaining_ids"] = vids
            else:
                pdata["facebook"]["errors"].append(f"verify {fv.status_code}: {fv.text[:180]}")

            # Instagram delete by page-linked IG account (if any)
            igr = session.get(
                f"https://graph.facebook.com/v25.0/{page_id}",
                params={"access_token": page_token, "fields": "instagram_business_account{id,username}"},
                timeout=45,
            )
            if igr.status_code == 200:
                igb = _json(igr)
                ig = (igb.get("instagram_business_account") or {}) if isinstance(igb, dict) else {}
                ig_id = str(ig.get("id", "")).strip()
                if ig_id:
                    pdata["instagram"]["ig_account"] = {"id": ig_id, "username": ig.get("username")}
                    for _ in range(20):
                        mr = session.get(
                            f"https://graph.facebook.com/v25.0/{ig_id}/media",
                            params={"access_token": page_token, "limit": 100, "fields": "id"},
                            timeout=45,
                        )
                        if mr.status_code != 200:
                            pdata["instagram"]["errors"].append(f"list {mr.status_code}: {mr.text[:180]}")
                            break
                        mb = _json(mr)
                        mids = [x.get("id") for x in mb.get("data", []) if isinstance(x, dict) and x.get("id")]
                        if not mids:
                            break
                        for mid in mids:
                            md = session.delete(
                                f"https://graph.facebook.com/v25.0/{mid}",
                                params={"access_token": page_token},
                                timeout=45,
                            )
                            if md.status_code == 200 and _json(md).get("success") is True:
                                pdata["instagram"]["deleted"] += 1
                            else:
                                pdata["instagram"]["failed"] += 1
                                if len(pdata["instagram"]["errors"]) < 5:
                                    pdata["instagram"]["errors"].append(f"delete {mid}: {md.status_code} {md.text[:140]}")

                    mv = session.get(
                        f"https://graph.facebook.com/v25.0/{ig_id}/media",
                        params={"access_token": page_token, "limit": 20, "fields": "id"},
                        timeout=45,
                    )
                    if mv.status_code == 200:
                        mbody = _json(mv)
                        mids = [x.get("id") for x in mbody.get("data", []) if isinstance(x, dict) and x.get("id")]
                        pdata["instagram"]["remaining_count"] = len(mids)
                    else:
                        pdata["instagram"]["errors"].append(f"verify {mv.status_code}: {mv.text[:180]}")
            else:
                pdata["instagram"]["errors"].append(f"ig lookup {igr.status_code}: {igr.text[:180]}")

            out["direct_graph"]["pages"][page_id] = pdata


# Threads probe
if not threads_token:
    out["threads_probe"] = {"configured": False, "note": "THREADS_ACCESS_TOKEN/INSTAGRAM_ACCESS_TOKEN missing"}
else:
    me = session.get(
        "https://graph.threads.net/v1.0/me",
        params={"access_token": threads_token, "fields": "id,username"},
        timeout=45,
    )
    out["threads_probe"]["configured"] = True
    out["threads_probe"]["me_status"] = me.status_code
    out["threads_probe"]["me_body"] = me.text[:200]
    lst = session.get(
        "https://graph.threads.net/v1.0/me/threads",
        params={"access_token": threads_token, "fields": "id", "limit": 20},
        timeout=45,
    )
    out["threads_probe"]["list_status"] = lst.status_code
    out["threads_probe"]["list_body"] = lst.text[:240]

print("FINAL_REPORT=" + json.dumps(out, separators=(",", ":")))
