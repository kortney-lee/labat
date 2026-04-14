"""
Vowels book ads v4 — dopamine-driven hooks.
Every headline promises something the reader GETS:
Learn, Save, Discover, Protect, Unlock, Get.
"""
import asyncio, os, json, httpx
from dotenv import load_dotenv
load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
AD_ACCOUNT = os.getenv("META_AD_ACCOUNT_ID", "act_218581359635343")
BASE = f"https://graph.facebook.com/v21.0"

VOWELS_ADSET = "120243299719930504"
VOWELS_PAGE = "100193518975897"
VOWELS_IG = "17841448164085103"
VOWELS_LEAD_FORM = "1651119505917119"
BOOK_WHITE = "10c9358859447d58063fe8864eb4a10e"
BOOK_SPREAD = "d40d9cf9e3c3bbbffe0d1abca0fb8544"

ADS_TO_PAUSE = [
    ("120243540471180504", "Break The Cycle"),
    ("120243540472150504", "Why Your Family Keeps Getting Sick"),
    ("120243540473300504", "Body Is A Temple"),
    ("120243540475180504", "1 In 3 Kids Overweight"),
    ("120243540477010504", "This Book Changed How Families Eat"),
    ("120243540477770504", "What We Eat Is Killing Us Slowly"),
]

VOWELS_NEW_ADS = [
    {
        "name": "Vowels v4 - Learn What Changed In Our Food",
        "title": "Learn What Changed In Our Food And How To Protect Your Family",
        "body": (
            "Something shifted in the American diet decades ago "
            "and most families never saw it coming. "
            "This free book shows you exactly what changed "
            "why your family is feeling it now "
            "and the simple shifts that can reverse it. "
            "One read. Thats all it takes to see your grocery store differently forever. "
            "Get your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v4 - Save Your Kids From Repeating Your Habits",
        "title": "Save Your Kids From Repeating The Same Health Mistakes You Inherited",
        "body": (
            "You didnt choose your eating habits. They were handed to you. "
            "Now youre passing them down without realizing it. "
            "This free book shows you how to spot the cycle "
            "and gives your family a clear path to break it. "
            "No diets. No guilt. Just clarity and a fresh start. "
            "Download your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels v4 - Discover Why Healthy Is So Confusing",
        "title": "Discover Why 'Healthy' Is So Confusing And What To Do About It",
        "body": (
            "You try to eat right. You read labels. You buy whats marketed as healthy. "
            "But something still feels off. "
            "Thats not your fault. The system was designed that way. "
            "This free book pulls back the curtain and gives you "
            "the tools to finally make real informed choices for your family. "
            "Get your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v4 - Protect Your Family With This Free Book",
        "title": "Protect Your Family From The Food Industry's Biggest Tricks",
        "body": (
            "The food industry spends billions to shape what healthy looks like. "
            "This free book arms you with the data the tools and the truth "
            "so you can protect your family from the inside out. "
            "Faith meets science. Data meets action. "
            "Thousands of families already have their copy. "
            "Get yours free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels v4 - Get The Book That Breaks The Cycle",
        "title": "Get The Free Book That's Helping Families Break Generational Health Cycles",
        "body": (
            "Diabetes. Obesity. High blood pressure. "
            "These arent just conditions. Theyre patterns "
            "passed down through habits food and environment. "
            "This free book shows you where the cycle started "
            "and gives you the blueprint to end it in your household. "
            "Written by Kortney O. Lee. Backed by millions of data points. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v4 - Unlock What No One Taught You About Food",
        "title": "Unlock What Nobody Ever Taught You About Food, Health, And Your Family",
        "body": (
            "School didnt teach it. Your doctor didnt have time. "
            "And the food industry hoped you would never find out. "
            "This free book covers what no one told you "
            "about how our food changed why were sicker than ever "
            "and what your family can start doing today. "
            "Short. Clear. Eye-opening. "
            "Download free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
]


async def pause_ad(client, ad_id, name):
    r = await client.post(f"{BASE}/{ad_id}", data={"status": "PAUSED", "access_token": TOKEN}, timeout=15)
    res = r.json()
    print(f"  {'Paused' if res.get('success') else 'ERROR'}: {name} ({ad_id})")

async def create_creative(client, name, title, body, image_hash):
    spec = {
        "name": name,
        "object_story_spec": json.dumps({
            "page_id": VOWELS_PAGE, "instagram_user_id": VOWELS_IG,
            "link_data": {
                "message": body, "name": title, "image_hash": image_hash,
                "link": "https://vowels.org/",
                "call_to_action": {"type": "DOWNLOAD", "value": {"lead_gen_form_id": VOWELS_LEAD_FORM, "link": "https://vowels.org/"}},
            },
        }),
        "access_token": TOKEN,
    }
    r = await client.post(f"{BASE}/{AD_ACCOUNT}/adcreatives", data=spec, timeout=30)
    res = r.json()
    if "id" in res:
        print(f"  Creative: {name} -> {res['id']}")
        return res["id"]
    raise Exception(f"Failed: {res}")

async def create_ad(client, name, creative_id):
    r = await client.post(f"{BASE}/{AD_ACCOUNT}/ads", data={
        "name": name, "adset_id": VOWELS_ADSET,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "ACTIVE", "access_token": TOKEN,
    }, timeout=30)
    res = r.json()
    if "id" in res:
        print(f"  Ad: {name} -> {res['id']}")
        return res["id"]
    raise Exception(f"Failed: {res}")

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        print("\n=== PAUSING v3 FACT-BASED ADS ===\n")
        for ad_id, label in ADS_TO_PAUSE:
            await pause_ad(client, ad_id, label)

        print("\n=== CREATING v4 DOPAMINE-DRIVEN ADS ===\n")
        for ad in VOWELS_NEW_ADS:
            cid = await create_creative(client, ad["name"], ad["title"], ad["body"], ad["image"])
            await create_ad(client, ad["name"], creative_id=cid)

        print("\n=== DONE ===")
        print("  Every headline now starts with a REWARD verb:")
        print("    Learn, Save, Discover, Protect, Get, Unlock")

asyncio.run(main())
