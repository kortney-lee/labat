"""
Vowels v7 — desire-driven "Struggling to X? This book does it for you" ads.
Added ON TOP of v6 (v6 stays active).
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

VOWELS_NEW_ADS = [
    {
        "name": "Vowels v7 - Struggling To Lose Weight",
        "title": "Struggling To Lose Weight? Read The Free Book That Does The Hard Part For You",
        "body": (
            "You dont need another diet. You dont need another app. "
            "You need to understand why your body is holding onto weight "
            "and what the food industry has been hiding from you. "
            "This free book breaks it all down and gives you a plan "
            "that actually works — without counting a single calorie. "
            "Get your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v7 - Struggling To Feed Kids Right",
        "title": "Struggling To Get Your Kids To Eat Healthy? This Free Book Makes It Easy",
        "body": (
            "Your kids arent picky. Theyre addicted to the same processed food "
            "the industry designed to keep them hooked. "
            "This free book shows you exactly how it happened "
            "and gives you a dead simple way to switch your family to real food "
            "without the fights and without the expense. "
            "Download free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels v7 - Tired Of Being Tired",
        "title": "Tired Of Being Tired? This Free Book Shows You Exactly What To Change",
        "body": (
            "That 2pm crash isnt normal. That brain fog isnt aging. "
            "Its what youve been eating — and nobody told you. "
            "This free book connects the dots between your energy "
            "your grocery list and the habits you didnt know were hurting you. "
            "One read and you will never shop the same way again. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v7 - Spending Too Much On Groceries",
        "title": "Spending Too Much On Groceries And Still Not Eating Healthy? Read This Free Book",
        "body": (
            "You shouldnt have to choose between your wallet and your health. "
            "The problem isnt your budget. Its what the food industry "
            "convinced you to put in your cart. "
            "This free book rewires how you shop "
            "so you spend less and eat better starting this week. "
            "Get it free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels v7 - Worried About Your Family Health",
        "title": "Worried Your Family Is Headed Down The Same Health Path As Your Parents? Read This",
        "body": (
            "Diabetes. High blood pressure. Heart disease. "
            "You watched your parents go through it. "
            "This free book shows you it was never genetics — it was habits. "
            "And it gives you the exact framework to make sure "
            "your kids dont repeat the same cycle. "
            "Download your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v7 - Confused About What Is Actually Healthy",
        "title": "Confused About What Is Actually Healthy? This Free Book Clears It All Up",
        "body": (
            "One day eggs are bad. Next day theyre good. "
            "Fat is evil. No wait fat is fine. "
            "The food industry wants you confused because confused people buy more. "
            "This free book cuts through all of it and tells you the truth "
            "about what to eat what to avoid and why nobody told you sooner. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
]


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
    for attempt in range(3):
        try:
            r = await client.post(f"{BASE}/{AD_ACCOUNT}/adcreatives", data=spec, timeout=60)
            res = r.json()
            if "id" in res:
                print(f"  Creative: {name} -> {res['id']}")
                return res["id"]
            raise Exception(f"Failed: {res}")
        except httpx.ReadTimeout:
            print(f"  Timeout attempt {attempt+1}/3 for creative {name}")
            await asyncio.sleep(2)
    raise Exception(f"Failed after 3 attempts: {name}")

async def create_ad(client, name, creative_id):
    for attempt in range(3):
        try:
            r = await client.post(f"{BASE}/{AD_ACCOUNT}/ads", data={
                "name": name, "adset_id": VOWELS_ADSET,
                "creative": json.dumps({"creative_id": creative_id}),
                "status": "ACTIVE", "access_token": TOKEN,
            }, timeout=60)
            res = r.json()
            if "id" in res:
                print(f"  Ad: {name} -> {res['id']}")
                return res["id"]
            raise Exception(f"Failed: {res}")
        except httpx.ReadTimeout:
            print(f"  Timeout attempt {attempt+1}/3 for ad {name}")
            await asyncio.sleep(2)
    raise Exception(f"Failed after 3 attempts: {name}")

async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        print("\n=== ADDING v7 DESIRE-DRIVEN ADS (v6 stays active) ===\n")
        for ad in VOWELS_NEW_ADS:
            cid = await create_creative(client, ad["name"], ad["title"], ad["body"], ad["image"])
            await create_ad(client, ad["name"], creative_id=cid)

        print("\n=== DONE === 12 total active ads (6 v6 + 6 v7) ===")

asyncio.run(main())
