"""
Delete all Instagram posts (media) across all brand IG accounts.
Uses DELETE /{ig-media-id} via Graph API — only works for app-created media.
"""
import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN", "").strip()
if not TOKEN:
    raise SystemExit("META_SYSTEM_USER_TOKEN not set")

BASE = "https://graph.facebook.com/v25.0"

BRANDS = {
    "wihy":               "17841478427607771",
    "vowels":             "17841448164085103",
    "communitygroceries": "17841445312259126",
    "childrennutrition":  "17841470986083057",
    "parentingwithchrist":"17841466415337829",
}


async def get_media_ids(client: httpx.AsyncClient, ig_id: str) -> list[str]:
    ids = []
    url = f"{BASE}/{ig_id}/media"
    params = {"fields": "id,timestamp", "limit": 50, "access_token": TOKEN}
    while url:
        r = await client.get(url, params=params, timeout=30)
        j = r.json()
        if r.status_code != 200:
            print(f"  [feed error {r.status_code}] {j}")
            break
        for item in j.get("data", []):
            ids.append(item["id"])
        cursor = (j.get("paging") or {}).get("cursors", {}).get("after")
        next_url = (j.get("paging") or {}).get("next")
        url = next_url if next_url else None
        params = {}  # next URL already has params
    return ids


async def delete_media(client: httpx.AsyncClient, media_id: str) -> dict:
    r = await client.delete(
        f"{BASE}/{media_id}",
        params={"access_token": TOKEN},
        timeout=30,
    )
    return {"id": media_id, "status": r.status_code, "body": r.text[:200]}


async def main():
    async with httpx.AsyncClient() as client:
        for brand, ig_id in BRANDS.items():
            print(f"\n=== {brand} (IG: {ig_id}) ===")
            ids = await get_media_ids(client, ig_id)
            print(f"  Found {len(ids)} media items")
            if not ids:
                continue

            deleted = 0
            failed = 0
            for mid in ids:
                result = await delete_media(client, mid)
                if result["status"] == 200:
                    deleted += 1
                else:
                    failed += 1
                    print(f"  FAIL: {result}")

            print(f"  Result: deleted={deleted}, failed={failed}")

    print("\nDone.")


asyncio.run(main())
