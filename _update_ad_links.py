"""
Update active Vowels v6 + v7 ads to link to whatishealthy.org with dynamic ?v= param
instead of vowels.org. Keeps the same lead form, just changes the destination URL.
"""
import asyncio, os, json, httpx
from dotenv import load_dotenv
load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
AD_ACCOUNT = os.getenv("META_AD_ACCOUNT_ID", "act_218581359635343")
BASE = f"https://graph.facebook.com/v21.0"

VOWELS_PAGE = "100193518975897"
VOWELS_IG = "17841448164085103"
VOWELS_LEAD_FORM = "1651119505917119"
VOWELS_ADSET = "120243299719930504"
BOOK_WHITE = "10c9358859447d58063fe8864eb4a10e"
BOOK_SPREAD = "d40d9cf9e3c3bbbffe0d1abca0fb8544"

# Map each active ad to its dynamic URL variant and creative details
# We need to create new creatives with updated links, then update each ad
ADS_TO_UPDATE = [
    # v6 ads
    {
        "ad_id": "120243540924860504",
        "name": "Vowels v6 - WARNING Do NOT Go Grocery Shopping",
        "variant": "warning",
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
        "ad_id": "120243540927410504",
        "name": "Vowels v6 - How To Feed Family Real Food No Extra Money",
        "variant": "realfood",
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
        "ad_id": "120243540928380504",
        "name": "Vowels v6 - 10 Health Foods You Can Eliminate",
        "variant": "eliminate",
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
        "ad_id": "120243540929820504",
        "name": "Vowels v6 - The Big Lie Food Industry Tells",
        "variant": "biglie",
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
        "ad_id": "120243540930560504",
        "name": "Vowels v6 - 5 Mistakes Costing You Health And Money",
        "variant": "mistakes",
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
        "ad_id": "120243540931890504",
        "name": "Vowels v6 - Finally Get Healthy Without Dieting",
        "variant": "finally",
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
    # v7 ads
    {
        "ad_id": "120243541063060504",
        "name": "Vowels v7 - Struggling To Lose Weight",
        "variant": "weight",
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
        "ad_id": "120243541067250504",
        "name": "Vowels v7 - Struggling To Feed Kids Right",
        "variant": "kids",
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
        "ad_id": "120243541072430504",
        "name": "Vowels v7 - Tired Of Being Tired",
        "variant": "energy",
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
        "ad_id": "120243541078410504",
        "name": "Vowels v7 - Spending Too Much On Groceries",
        "variant": "groceries",
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
        "ad_id": "120243541083780504",
        "name": "Vowels v7 - Worried About Your Family Health",
        "variant": "family",
        "title": "Worried Your Family Is Headed Down The Same Health Path As Your Parents? Read This",
        "body": (
            "Diabetes. High blood pressure. Heart disease. "
            "You watched your parents go through it. "
            "This free book shows you it was never genetics — it was habits. "
            "And it gives you the exact framework to make sure "
            "your kids dont have to watch you go through the same thing. "
            "Download your free copy at WhatIsHealthy.org"
        ),
        "image": BOOK_WHITE,
    },
    {
        "ad_id": "120243541087720504",
        "name": "Vowels v7 - Confused About What Is Actually Healthy",
        "variant": "confused",
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


async def create_creative_and_update_ad(client, ad):
    link = f"https://whatishealthy.org/?v={ad['variant']}&utm_source=facebook&utm_medium=paid&utm_campaign=vowels_book&utm_content={ad['variant']}"
    spec = {
        "name": ad["name"] + " (dynamic)",
        "object_story_spec": json.dumps({
            "page_id": VOWELS_PAGE, "instagram_user_id": VOWELS_IG,
            "link_data": {
                "message": ad["body"], "name": ad["title"], "image_hash": ad["image"],
                "link": link,
                "call_to_action": {"type": "SIGN_UP", "value": {"lead_gen_form_id": VOWELS_LEAD_FORM, "link": link}},
            },
        }),
        "access_token": TOKEN,
    }
    for attempt in range(3):
        try:
            r = await client.post(f"{BASE}/{AD_ACCOUNT}/adcreatives", data=spec, timeout=60)
            res = r.json()
            if "id" not in res:
                print(f"  ERROR creating creative for {ad['name']}: {res}")
                return
            creative_id = res["id"]
            print(f"  Creative: {ad['name']} -> {creative_id}")

            # Update the ad to use the new creative
            r2 = await client.post(f"{BASE}/{ad['ad_id']}", data={
                "creative": json.dumps({"creative_id": creative_id}),
                "access_token": TOKEN,
            }, timeout=60)
            res2 = r2.json()
            status = "Updated" if res2.get("success") else f"ERROR: {res2}"
            print(f"  {status}: {ad['ad_id']} -> {link}")
            return
        except httpx.ReadTimeout:
            print(f"  Timeout attempt {attempt+1}/3 for {ad['name']}")
            await asyncio.sleep(2)
    print(f"  FAILED after 3 attempts: {ad['name']}")


async def main():
    print(f"\n=== UPDATING {len(ADS_TO_UPDATE)} ADS TO DYNAMIC whatishealthy.org URLS ===\n")
    async with httpx.AsyncClient(timeout=60) as client:
        for ad in ADS_TO_UPDATE:
            await create_creative_and_update_ad(client, ad)

    print("\n=== DONE ===")
    print("All ads now link to whatishealthy.org/?v=<variant>")
    print("Landing page headline auto-matches the ad they clicked")

asyncio.run(main())
