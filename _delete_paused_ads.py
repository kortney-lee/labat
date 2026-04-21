"""Delete all paused (loser) ads from the ad account."""
import asyncio, os, httpx
from dotenv import load_dotenv

load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
BASE = "https://graph.facebook.com/v21.0"
ACCOUNT = "act_218581359635343"


async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        # Use the same filtering approach that worked in _pause_bad_ads.py
        # but include PAUSED and all other non-active statuses
        all_ads = []
        for status_filter in [
            '["ACTIVE"]',
            '["PAUSED"]',
            '["ADSET_PAUSED"]',
            '["CAMPAIGN_PAUSED"]',
            '["DISAPPROVED"]',
            '["PENDING_REVIEW"]',
            '["WITH_ISSUES"]',
        ]:
            r = await c.get(
                f"{BASE}/{ACCOUNT}/ads",
                params={
                    "access_token": TOKEN,
                    "fields": "name,id,effective_status,status",
                    "limit": 200,
                    "filtering": f'[{{"field":"effective_status","operator":"IN","value":{status_filter}}}]',
                },
            )
            data = r.json()
            if data.get("error"):
                print(f"  {status_filter}: error - {data['error']['message']}")
                continue
            ads = data.get("data", [])
            if ads:
                print(f"  {status_filter}: {len(ads)} ads")
            all_ads.extend(ads)

        print(f"\nTotal found: {len(all_ads)} ads")
        active = [a for a in all_ads if a["effective_status"] == "ACTIVE"]
        losers = [a for a in all_ads if a["effective_status"] != "ACTIVE"]

        print(f"Active (keep): {len(active)}")
        for a in active:
            print(f"  ✅ {a['name']}")

        print(f"\nNon-active (delete): {len(losers)}")
        for a in losers:
            print(f"  ❌ {a['effective_status']:20s} | {a['name']} ({a['id']})")

        if losers:
            confirm = input(f"\nDelete {len(losers)} ads? (y/n): ")
            if confirm.lower() == "y":
                for ad in losers:
                    r2 = await c.delete(f"{BASE}/{ad['id']}", params={"access_token": TOKEN})
                    result = r2.json()
                    status = "DELETED" if result.get("success") else f"ERROR: {result}"
                    print(f"  {status} | {ad['name']}")
                print(f"\nDone. Deleted {len(losers)} ads.")
            else:
                print("Aborted.")
        else:
            print("Nothing to delete.")
        print(f"Total ads: {len(all_ads)}\n")

        active = [a for a in all_ads if a["effective_status"] == "ACTIVE"]
        losers = [a for a in all_ads if a["effective_status"] != "ACTIVE"]

        print(f"=== ACTIVE ({len(active)}) ===")
        for a in active:
            print(f"  KEEP | {a['name']} ({a['id']})")

        print(f"\n=== DELETING ({len(losers)}) ===")
        for ad in losers:
            r2 = await c.delete(f"{BASE}/{ad['id']}", params={"access_token": TOKEN})
            result = r2.json()
            status = "DELETED" if result.get("success") else f"ERROR: {result}"
            print(f"  {status} | {ad['effective_status']:20s} | {ad['name']} ({ad['id']})")

        print(f"\nDone. Kept {len(active)}, deleted {len(losers)}.")


asyncio.run(main())
