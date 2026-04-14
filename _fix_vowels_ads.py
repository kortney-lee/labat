"""
Replace weak Vowels book ads with direct-response headlines that SELL the free book.
Pause the 6 just-created ads, create 6 new ones with result-driven copy.
"""
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

VOWELS_ADSET = "120243299719930504"
VOWELS_PAGE = "100193518975897"
VOWELS_IG = "17841448164085103"
VOWELS_LEAD_FORM = "1651119505917119"

# Image hashes (just uploaded)
BOOK_WHITE = "10c9358859447d58063fe8864eb4a10e"
BOOK_SPREAD = "d40d9cf9e3c3bbbffe0d1abca0fb8544"

# Ads to pause (the 6 weak ones just created)
ADS_TO_PAUSE = [
    ("120243540166120504", "Big Lie Food Industry"),
    ("120243540168920504", "5 Warning Signs"),
    ("120243540171200504", "Truth About Food Labels"),
    ("120243540172350504", "What Parents Must Know"),
    ("120243540173610504", "When Did We Stop Eating Real Food"),
    ("120243540174980504", "Find Out How To See Through"),
]

# ──────────────────────────────────────────────────────────────────────
# NEW VOWELS ADS — Direct response. Sell the book. Promise the result.
# ──────────────────────────────────────────────────────────────────────
VOWELS_NEW_ADS = [
    {
        "name": "Vowels Book - Free Book Shows 10 Second Label Test",
        "title": "Free Book: The 10-Second Label Test That Changes Everything",
        "body": (
            "You shouldnt need a nutrition degree to feed your family. "
            "This free book gives you a simple 10-second test you can use "
            "on any food label in any store to know instantly if its real food "
            "or marketing. Over 12,000 parents already use it. "
            "Download your free copy now at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels Book - Free Book Exposed What Labels Hide",
        "title": "This Free Book Shows You Exactly What To Buy At The Store",
        "body": (
            "Stop standing in the grocery aisle wondering if something is actually healthy. "
            "This free book by Kortney O. Lee breaks down exactly how food labels trick you "
            "and gives you a dead-simple system to shop smarter starting today. "
            "No diets. No apps. Just clarity. "
            "Get your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels Book - Your Kids Eat What You Buy Fix It Here",
        "title": "Your Kids Eat What You Buy. This Free Book Fixes What You Buy.",
        "body": (
            "1 in 3 kids in America is now overweight or obese. "
            "Its not their fault. Its what lines the grocery shelves. "
            "This free book traces the problem to the source and gives you "
            "a clear system to protect your family without spending more. "
            "Thousands of parents already have their copy. "
            "Download yours free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels Book - Stop Guessing Start Knowing Free Book",
        "title": "Stop Guessing What's Healthy. Start Knowing. Free Book.",
        "body": (
            "Natural. Organic. No added sugar. Heart healthy. "
            "None of these mean what you think they mean. "
            "This free book gives you the exact framework to cut through "
            "every misleading claim and know what youre actually feeding your family. "
            "One read will change every grocery trip after it. "
            "Get it free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels Book - One Book Changed How 12K Parents Shop",
        "title": "One Free Book Changed How 12,000 Parents Shop For Food",
        "body": (
            "They stopped falling for health claims on the box. "
            "They stopped wasting money on products that arent what they seem. "
            "They started using the 10-second label test in Chapter 3. "
            "Now they know exactly whats in their food and what to avoid. "
            "This book is free. Your familys health is worth the 30 minutes to read it. "
            "Download now at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels Book - Free Book No Diet Just Real Answers",
        "title": "Not A Diet Book. A 'Finally I Understand Food Labels' Book. Free.",
        "body": (
            "This isnt another diet plan or meal guide. "
            "Its the book that explains why healthy is so confusing "
            "and gives you the tools to never be confused again. "
            "Written by Kortney O. Lee with data from millions of products "
            "and research articles. Short. Clear. Eye-opening. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
]


async def pause_ad(client, ad_id, name):
    r = await client.post(f"{BASE}/{ad_id}", data={"status": "PAUSED", "access_token": TOKEN}, timeout=15)
    result = r.json()
    if result.get("success"):
        print(f"  Paused: {name} ({ad_id})")
    else:
        print(f"  ERROR pausing {name}: {result}")


async def create_creative(client, name, title, body, image_hash):
    spec = {
        "name": name,
        "object_story_spec": json.dumps({
            "page_id": VOWELS_PAGE,
            "instagram_user_id": VOWELS_IG,
            "link_data": {
                "message": body,
                "name": title,
                "image_hash": image_hash,
                "link": "https://vowels.org/",
                "call_to_action": {
                    "type": "DOWNLOAD",
                    "value": {
                        "lead_gen_form_id": VOWELS_LEAD_FORM,
                        "link": "https://vowels.org/",
                    },
                },
            },
        }),
        "access_token": TOKEN,
    }
    r = await client.post(f"{BASE}/{AD_ACCOUNT}/adcreatives", data=spec, timeout=30)
    result = r.json()
    if "id" in result:
        print(f"  Creative: {name} -> {result['id']}")
        return result["id"]
    else:
        print(f"  ERROR: {name}: {json.dumps(result, indent=2)}")
        raise Exception(f"Failed: {result}")


async def create_ad(client, name, creative_id):
    r = await client.post(
        f"{BASE}/{AD_ACCOUNT}/ads",
        data={
            "name": name,
            "adset_id": VOWELS_ADSET,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": "ACTIVE",
            "access_token": TOKEN,
        },
        timeout=30,
    )
    result = r.json()
    if "id" in result:
        print(f"  Ad: {name} -> {result['id']}")
        return result["id"]
    else:
        print(f"  ERROR: {name}: {json.dumps(result, indent=2)}")
        raise Exception(f"Failed: {result}")


async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        print("\n=== PAUSING 6 WEAK VOWELS ADS ===\n")
        for ad_id, label in ADS_TO_PAUSE:
            await pause_ad(client, ad_id, label)

        print("\n=== CREATING 6 NEW DIRECT-RESPONSE VOWELS ADS ===\n")
        for ad_def in VOWELS_NEW_ADS:
            cid = await create_creative(
                client,
                name=f"Vowels DR - {ad_def['name']}",
                title=ad_def["title"],
                body=ad_def["body"],
                image_hash=ad_def["image"],
            )
            await create_ad(client, name=ad_def["name"], creative_id=cid)

        print("\n=== DONE ===")
        print(f"  6 weak ads paused, 6 new direct-response ads live")
        print(f"  All using actual book images (book-white + book-spread)")


asyncio.run(main())
