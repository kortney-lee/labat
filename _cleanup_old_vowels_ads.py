"""Delete old paused Vowels ads (v1-v5 + originals) to free up adset space."""
import asyncio, os, httpx
from dotenv import load_dotenv
load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
BASE = "https://graph.facebook.com/v21.0"

# All paused ads to DELETE (originals + v1 through v5)
PAUSED_ADS = [
    # Original 10 (wrong WIHY images)
    "120243299720930504", "120243312880850504", "120243312879620504",
    "120243299728050504", "120243312878470504", "120243312873630504",
    "120243312875540504", "120243299724210504", "120243299722340504",
    "120243299727010504",
    # v1
    "120243540166120504", "120243540168920504", "120243540171200504",
    "120243540172350504", "120243540173610504", "120243540174980504",
    # v2
    "120243540398630504", "120243540399790504", "120243540401400504",
    "120243540402990504", "120243540405900504", "120243540407720504",
    # v3
    "120243540471180504", "120243540472150504", "120243540473300504",
    "120243540475180504", "120243540477010504", "120243540477770504",
    # v4
    "120243540514790504", "120243540520280504", "120243540526630504",
    "120243540529540504", "120243540533080504", "120243540533950504",
    # v5
    "120243540694060504", "120243540706480504", "120243540717200504",
    "120243540726330504", "120243540737640504", "120243540749460504",
]

async def delete_ad(client, ad_id):
    for attempt in range(3):
        try:
            r = await client.delete(f"{BASE}/{ad_id}", params={"access_token": TOKEN}, timeout=60)
            res = r.json()
            status = "Deleted" if res.get("success") else f"ERROR: {res}"
            print(f"  {status}: {ad_id}")
            return
        except httpx.ReadTimeout:
            print(f"  Timeout {attempt+1}/3: {ad_id}")
            await asyncio.sleep(2)
    print(f"  FAILED: {ad_id}")

async def main():
    print(f"\n=== DELETING {len(PAUSED_ADS)} OLD PAUSED ADS ===\n")
    async with httpx.AsyncClient(timeout=60) as client:
        for ad_id in PAUSED_ADS:
            await delete_ad(client, ad_id)
    print(f"\n=== DONE — freed {len(PAUSED_ADS)} slots ===")

asyncio.run(main())
