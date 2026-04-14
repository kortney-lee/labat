"""Pull Facebook ad copy and creatives for all active campaigns."""
import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
AD_ACCOUNT = os.getenv("META_AD_ACCOUNT_ID", "act_218581359635343")
API_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        # Get all campaigns
        r = await client.get(
            f"{BASE}/{AD_ACCOUNT}/campaigns",
            params={
                "access_token": TOKEN,
                "fields": "name,status,effective_status,objective",
                "limit": 50,
            },
        )
        campaigns = r.json().get("data", [])
        print(f"=== {len(campaigns)} CAMPAIGNS ===\n")

        for c in campaigns:
            status = c.get("effective_status", "?")
            print(f"Campaign: {c['name']}")
            print(f"  ID: {c['id']} | Status: {status} | Obj: {c.get('objective', '?')}")

        # Get all ads with creatives
        print("\n\n=== AD CREATIVES (active/paused) ===\n")
        r2 = await client.get(
            f"{BASE}/{AD_ACCOUNT}/ads",
            params={
                "access_token": TOKEN,
                "fields": "name,status,effective_status,creative{title,body,link_description,call_to_action_type,object_story_spec,thumbnail_url,image_url,asset_feed_spec}",
                "limit": 50,
            },
        )
        ads = r2.json().get("data", [])

        for ad in ads:
            status = ad.get("effective_status", "?")
            print(f"--- Ad: {ad['name']} ---")
            print(f"  Status: {status}")
            creative = ad.get("creative", {})
            if creative.get("title"):
                print(f"  Title: {creative['title']}")
            if creative.get("body"):
                print(f"  Body: {creative['body']}")
            if creative.get("link_description"):
                print(f"  Link Desc: {creative['link_description']}")
            if creative.get("call_to_action_type"):
                print(f"  CTA: {creative['call_to_action_type']}")

            # Check object_story_spec for the actual post copy
            oss = creative.get("object_story_spec", {})
            if oss:
                # Link data
                ld = oss.get("link_data", {})
                if ld:
                    print(f"  Post Message: {ld.get('message', '(none)')}")
                    print(f"  Link Title: {ld.get('name', '(none)')}")
                    print(f"  Link Desc: {ld.get('description', '(none)')}")
                    print(f"  Link: {ld.get('link', '(none)')}")
                    print(f"  CTA: {ld.get('call_to_action', {}).get('type', '(none)')}")

                # Video data
                vd = oss.get("video_data", {})
                if vd:
                    print(f"  Video Message: {vd.get('message', '(none)')}")
                    print(f"  Video Title: {vd.get('title', '(none)')}")
                    print(f"  Video CTA: {vd.get('call_to_action', {}).get('type', '(none)')}")
                    print(f"  Video Link: {vd.get('call_to_action', {}).get('value', {}).get('link', '(none)')}")

            # Asset feed spec (for dynamic creatives)
            afs = creative.get("asset_feed_spec", {})
            if afs:
                bodies = afs.get("bodies", [])
                titles = afs.get("titles", [])
                descs = afs.get("descriptions", [])
                if bodies:
                    print(f"  Dynamic Bodies:")
                    for b in bodies:
                        print(f"    - {b.get('text', '?')}")
                if titles:
                    print(f"  Dynamic Titles:")
                    for t in titles:
                        print(f"    - {t.get('text', '?')}")
                if descs:
                    print(f"  Dynamic Descriptions:")
                    for d in descs:
                        print(f"    - {d.get('text', '?')}")

            print()


asyncio.run(main())
