"""
Replace 6 Vowels book ads with copy that reflects the FULL book scope:
- Breaking generational health cycles
- Body as a temple / faith-based health
- Why we're sick as a society (not just labels)
- Transformation, not just information
- Fasting, habits, community, kids
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

BOOK_WHITE = "10c9358859447d58063fe8864eb4a10e"
BOOK_SPREAD = "d40d9cf9e3c3bbbffe0d1abca0fb8544"

# Pause the 6 "direct response" ads that were still just about labels
ADS_TO_PAUSE = [
    ("120243540398630504", "Free Book Shows 10 Second Label Test"),
    ("120243540399790504", "Free Book Exposed What Labels Hide"),
    ("120243540401400504", "Your Kids Eat What You Buy"),
    ("120243540402990504", "Stop Guessing Start Knowing"),
    ("120243540405900504", "One Book Changed How 12K Parents Shop"),
    ("120243540407720504", "Free Book No Diet Just Real Answers"),
]

# ──────────────────────────────────────────────────────────────────────
# FULL-SCOPE BOOK ADS — sells the transformation, not just label tricks
# ──────────────────────────────────────────────────────────────────────
VOWELS_NEW_ADS = [
    {
        "name": "Vowels - Break The Cycle Your Family Passed Down",
        "title": "Break The Health Cycle Your Family Passed Down To You",
        "body": (
            "The habits making your family sick didnt start with you. "
            "They were inherited. Passed down with love but without intention. "
            "Takeout became normal. Soda became water. Shortcuts became tradition. "
            "This free book traces how we got here and gives you the tools "
            "to break the cycle for the next generation. "
            "Its not a diet book. Its a wake-up call. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels - Why Your Family Keeps Getting Sick",
        "title": "Why Your Family Keeps Getting Sick — And How To Stop It",
        "body": (
            "Type 2 diabetes. High blood pressure. Obesity. Heart disease. "
            "We call them conditions. But theyre consequences. "
            "Consequences of a food system designed for profit not for health. "
            "This free book follows the data back to the root cause "
            "and shows you exactly what changed in the American diet "
            "and what your family can do about it starting today. "
            "Download your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels - Your Body Is A Temple Stop Poisoning It",
        "title": "Your Body Is A Temple. This Book Shows You How To Treat It Like One.",
        "body": (
            "You cant heal a body you keep filling with things that harm it. "
            "Fasting. Real food. Intentional living. "
            "This isnt about a trend. Its about returning to what scripture "
            "and science both agree on: your body deserves better. "
            "This free book connects faith health and family "
            "in a way you wont find anywhere else. "
            "Get your copy free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels - 1 In 3 Kids Overweight Not Their Fault",
        "title": "1 In 3 Kids Is Now Overweight. It's Not Their Fault. It's Ours.",
        "body": (
            "In 1970 less than 5 percent of children were obese. Today its over 20 percent. "
            "This didnt happen by accident. "
            "The food industry spends 1.8 billion a year marketing junk food to kids. "
            "Meanwhile we pass down the same habits our parents gave us "
            "without ever asking where they came from. "
            "This free book traces the crisis to its source "
            "and gives families a real path forward. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels - This Book Changed How Families Eat",
        "title": "This Free Book Changed How Thousands Of Families Eat, Shop, And Live",
        "body": (
            "Its not a cookbook. Its not a diet plan. "
            "Its the book that finally explains why healthy is so confusing "
            "and what you can do about it for your family. "
            "From the food industry to fasting. "
            "From generational habits to grocery aisles. "
            "From data to faith. "
            "Written by Kortney O. Lee with data from millions of products "
            "and research articles. Short. Clear. Life-changing. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels - What We Eat Is Killing Us Slowly",
        "title": "What We Eat Is Killing Us Slowly. This Book Shows You Why — And How To Stop.",
        "body": (
            "60 percent of what Americans eat is ultra-processed. "
            "Our kids are sicker than any generation before them. "
            "And the food industry is spending billions to make sure "
            "you dont connect the dots. "
            "This free book connects them for you. "
            "Backed by research. Rooted in faith. Written for families. "
            "One read will change how you see every meal after it. "
            "Get it free at WhatIsHealthy.org"
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
        print("\n=== PAUSING 6 LABEL-FOCUSED ADS ===\n")
        for ad_id, label in ADS_TO_PAUSE:
            await pause_ad(client, ad_id, label)

        print("\n=== CREATING 6 FULL-SCOPE BOOK ADS ===\n")
        for ad_def in VOWELS_NEW_ADS:
            cid = await create_creative(
                client,
                name=f"Vowels v3 - {ad_def['name']}",
                title=ad_def["title"],
                body=ad_def["body"],
                image_hash=ad_def["image"],
            )
            await create_ad(client, name=ad_def["name"], creative_id=cid)

        print("\n=== DONE ===")
        print("  Paused 6 label-only ads")
        print("  Created 6 full-scope ads covering:")
        print("    - Breaking generational health cycles")
        print("    - Root cause of chronic disease")
        print("    - Body as a temple / faith + science")
        print("    - Childhood obesity crisis")
        print("    - Full transformation (not just labels)")
        print("    - Food industry + data + family action")


asyncio.run(main())
