"""
Vowels book ads v5 — outcome-driven dopamine hooks.
Formula: "Learn how to [outcome] + save/get [second benefit] because [book]"
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
    ("120243540514790504", "v4 Learn"),
    ("120243540520280504", "v4 Save"),
    ("120243540526630504", "v4 Discover"),
    ("120243540529540504", "v4 Protect"),
    ("120243540533080504", "v4 Get"),
    ("120243540533950504", "v4 Unlock"),
]

VOWELS_NEW_ADS = [
    {
        "name": "Vowels v5 - Learn To Lose Weight Save Money",
        "title": "Learn How To Lose Weight And Save Money On Groceries With This Free Book",
        "body": (
            "What if the same habits making you gain weight "
            "are the same ones draining your wallet? "
            "This free book shows you why processed food costs more than you think "
            "and how switching to real food can help you drop pounds "
            "and keep more money in your pocket every week. "
            "Get your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v5 - Learn To Feed Kids Healthy Save Time",
        "title": "Learn How To Feed Your Kids Healthier And Save Hours Every Week",
        "body": (
            "Youre not a bad parent. Youre just stuck in a system "
            "that made junk food the easy option. "
            "This free book shows you how to swap convenience for real food "
            "without spending more time or more money. "
            "Your kids eat what you buy. This book changes what you buy. "
            "Download free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels v5 - Learn To Break Bad Habits Gain Energy",
        "title": "Learn How To Break Bad Eating Habits And Get Your Energy Back",
        "body": (
            "Tired all the time? Craving sugar by 2pm? "
            "Those arent just bad days. Theyre bad habits "
            "passed down through generations of processed food. "
            "This free book shows you where those habits started "
            "and gives you a simple framework to replace them "
            "so you wake up with energy instead of brain fog. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v5 - Learn To Eat Real Food Save Your Health",
        "title": "Learn How To Eat Real Food Again And Save Your Family's Health",
        "body": (
            "Your grandparents didnt have a grocery aisle full of chemicals. "
            "Somewhere along the way real food got replaced "
            "and nobody told you what it was costing your body. "
            "This free book traces exactly what changed "
            "and shows your family how to get back to eating real. "
            "No diets. No gimmicks. Just real food. "
            "Get it free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        "name": "Vowels v5 - Learn To Shop Smarter Protect Your Family",
        "title": "Learn How To Shop Smarter And Protect Your Family From Fake Health Food",
        "body": (
            "The grocery store is designed to trick you. "
            "This free book teaches you how to see through it "
            "so you stop wasting money on food that isnt what it claims to be "
            "and start feeding your family what actually works. "
            "One read will change every grocery trip after it. "
            "Download your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "name": "Vowels v5 - Learn To Prevent Disease Save Your Family",
        "title": "Learn How To Prevent The Diseases Your Parents Had Before Its Too Late",
        "body": (
            "Diabetes. Heart disease. High blood pressure. "
            "You watched your parents go through it. "
            "Now this free book shows you how to make sure "
            "your kids dont have to watch you go through the same thing. "
            "Its not genetics. Its habits. And habits can be changed. "
            "Start today. Free at WhatIsHealthy.org"
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
        print("\n=== PAUSING v4 ADS ===\n")
        for ad_id, label in ADS_TO_PAUSE:
            await pause_ad(client, ad_id, label)

        print("\n=== CREATING v5 OUTCOME-DRIVEN ADS ===\n")
        for ad in VOWELS_NEW_ADS:
            cid = await create_creative(client, ad["name"], ad["title"], ad["body"], ad["image"])
            await create_ad(client, ad["name"], creative_id=cid)

        print("\n=== DONE ===")
        print("  Formula: Learn how to [OUTCOME] + [SECOND BENEFIT] because [BOOK]")

asyncio.run(main())
