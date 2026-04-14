"""
Vowels book ads v6 — proven opt-in headline formulas applied to the book.
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
    ("120243540694060504", "v5 Lose Weight Save Money"),
    ("120243540706480504", "v5 Feed Kids Save Time"),
    ("120243540717200504", "v5 Break Habits Gain Energy"),
    ("120243540726330504", "v5 Eat Real Food Save Health"),
    ("120243540737640504", "v5 Shop Smarter Protect Family"),
    ("120243540749460504", "v5 Prevent Disease Save Family"),
]

# Each ad uses a different proven headline formula
VOWELS_NEW_ADS = [
    {
        # Formula #13: WARNING Do NOT [Action] Before You Read This
        "name": "Vowels v6 - WARNING Do NOT Go Grocery Shopping",
        "title": "WARNING: Do NOT Go Grocery Shopping Before You Read This Free Book",
        "body": (
            "Everything you think is healthy at the grocery store "
            "might be making your family sick and costing you more money. "
            "This free book exposes what the food industry doesnt want you to know "
            "and shows you exactly what to buy instead. "
            "One read will change every grocery trip after it. "
            "Get your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        # Formula #2: How to [Impossible Goal] in [Short Time] Without [Thing You Think You Need]
        "name": "Vowels v6 - How To Feed Family Real Food No Extra Money",
        "title": "How To Feed Your Family Real Food In The Next 7 Days Without Spending More Money",
        "body": (
            "You dont need a bigger grocery budget. "
            "You need to stop buying the foods the industry tricked you into thinking are healthy. "
            "This free book shows you exactly what changed in our food system "
            "and gives you a simple plan to feed your family real food "
            "starting this week without spending an extra dime. "
            "Download free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        # Formula #20: [Number] [Health Foods] You Can Eliminate To [Instant Benefit]
        "name": "Vowels v6 - 10 Health Foods You Can Eliminate",
        "title": "10 'Health' Foods You Can Eliminate To Immediately Start Losing Weight And Saving Money",
        "body": (
            "That granola bar. That fruit juice. That whole wheat bread. "
            "Theyre not what you think they are. "
            "This free book reveals the processed foods hiding behind healthy labels "
            "and shows you what to replace them with "
            "so you lose weight and keep more money in your pocket every week. "
            "Free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        # Formula #4: The Big Lie [Experts] Tell About [Topic] that Could [Harm]
        "name": "Vowels v6 - The Big Lie Food Industry Tells",
        "title": "The Big Lie The Food Industry Tells About Healthy Eating That Could Be Making Your Family Sick",
        "body": (
            "They put 'natural' on the label and charge you more for it. "
            "Meanwhile childhood obesity is at an all time high "
            "and diet related disease is being passed down generation after generation. "
            "This free book pulls back the curtain on what happened to our food "
            "and shows your family how to break the cycle. "
            "Get it free at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
    {
        # Formula #5: [Number] Mistakes Costing You [Resources]
        "name": "Vowels v6 - 5 Mistakes Costing You Health And Money",
        "title": "5 Grocery Mistakes You Dont Know Youre Making That Cost You Hundreds And Your Health Every Month",
        "body": (
            "Youre spending more than you should on food that isnt feeding your body. "
            "This free book breaks down the 5 biggest mistakes families make "
            "at the grocery store every single week "
            "and shows you how to fix them starting on your very next trip. "
            "Your wallet and your waistline will thank you. "
            "Download free at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        # Headline formula: Finally! How to [result] without [fear] in [timeframe] - guaranteed
        "name": "Vowels v6 - Finally Get Healthy Without Dieting",
        "title": "Finally! How To Get Your Family Eating Healthy Without Dieting Or Spending More On Groceries",
        "body": (
            "No calorie counting. No meal kits. No overpriced organic everything. "
            "This free book gives you the truth about what happened to our food "
            "and a simple framework to get your family back to eating real "
            "without changing your budget or your schedule. "
            "Its not a diet book. Its a wake up call. "
            "Get your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_SPREAD,
    },
]


async def pause_ad(client, ad_id, name):
    for attempt in range(3):
        try:
            r = await client.post(f"{BASE}/{ad_id}", data={"status": "PAUSED", "access_token": TOKEN}, timeout=60)
            res = r.json()
            print(f"  {'Paused' if res.get('success') else 'ERROR'}: {name} ({ad_id})")
            return
        except httpx.ReadTimeout:
            print(f"  Timeout attempt {attempt+1}/3 for {name}")
            await asyncio.sleep(2)
    print(f"  FAILED after 3 attempts: {name}")

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
        print("\n=== PAUSING v5 ADS ===\n")
        for ad_id, label in ADS_TO_PAUSE:
            await pause_ad(client, ad_id, label)

        print("\n=== CREATING v6 PROVEN FORMULA ADS ===\n")
        for ad in VOWELS_NEW_ADS:
            cid = await create_creative(client, ad["name"], ad["title"], ad["body"], ad["image"])
            await create_ad(client, ad["name"], creative_id=cid)

        print("\n=== DONE ===")
        print("Formulas used: WARNING Do NOT, How To Without, Eliminate To, Big Lie, Mistakes Costing, Finally!")

asyncio.run(main())
