"""
Create new high-converting ads for CG and Vowels Book campaigns.
- Keeps CG winner ad (120243278546440504 - "Your Weekly Meals In Seconds", $1.09/lead) 
- Pauses all other CG ads
- Pauses all Vowels book ads (wrong WIHY images)
- Creates new CG ads with formula-based copy
- Creates new Vowels book ads with proper book images + formula copy
"""
import asyncio
import os
import json
import httpx
import hashlib
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
AD_ACCOUNT = os.getenv("META_AD_ACCOUNT_ID", "act_218581359635343")
API_VERSION = "v21.0"
BASE = f"https://graph.facebook.com/{API_VERSION}"

# Adset IDs (from performance check)
CG_ADSET = "120243278518860504"
VOWELS_ADSET = "120243299719930504"

# CG winner - keep this one
CG_WINNER_AD_ID = "120243278546440504"

# Page IDs
CG_PAGE = "2051601018287997"
CG_IG = "17841445312259126"
VOWELS_PAGE = "100193518975897"
VOWELS_IG = "17841448164085103"

# Lead form IDs
CG_LEAD_FORM = "941193938505567"
VOWELS_LEAD_FORM = "1651119505917119"

# CG video ID (reuse the winner's video)
CG_VIDEO_ID = "26824262980542426"

# Book images to upload
BOOK_WHITE = r"C:\Users\Kortn\Repo\wihy_ml\static_whatishealthy\book-white.jpg"
BOOK_SPREAD = r"C:\Users\Kortn\Repo\wihy_ml\static_whatishealthy\book-spread.png"

# ──────────────────────────────────────────────────────────────────────
# NEW CG ADS (formula-based copy, keep using video)
# ──────────────────────────────────────────────────────────────────────
CG_NEW_ADS = [
    {
        "name": "CG - Cut Grocery Bill 40% This Week",
        "title": "Cut Your Grocery Bill By 40% This Week",
        "body": (
            "The average family wastes $1,500 a year on food they throw away. "
            "No meal plan. No list. Just impulse buys and leftovers in the trash. "
            "Community Groceries AI builds your family a full week of healthy meals "
            "plus a smart shopping list in 30 seconds. No waste. No stress. "
            "Free at communitygroceries.com"
        ),
    },
    {
        "name": "CG - 3 Grocery Mistakes Costing Hundreds",
        "title": "3 Grocery Mistakes Costing Your Family Hundreds",
        "body": (
            "Buying without a list. Cooking without a plan. Shopping hungry. "
            "These 3 habits waste more money than you think. "
            "Community Groceries AI fixes all 3. Personalized meal plans "
            "plus a grocery list that fits your budget. "
            "Try it free at communitygroceries.com"
        ),
    },
    {
        "name": "CG - Why You Dont Need Hours To Meal Plan",
        "title": "Why You Don't Need Hours To Meal Plan",
        "body": (
            "You dont need a Pinterest board a spreadsheet or 3 hours on Sunday. "
            "Tell Community Groceries your family size budget and dietary needs. "
            "Get a week of meals and a grocery list in 30 seconds. "
            "Balanced. Affordable. Done. Free at communitygroceries.com"
        ),
    },
    {
        "name": "CG - WARNING Dont Go Grocery Shopping Before This",
        "title": "WARNING: Don't Go Grocery Shopping Before Reading This",
        "body": (
            "Every trip to the store without a plan costs your family "
            "an extra $30 to $50 in impulse buys. "
            "Community Groceries AI gives you a personalized meal plan "
            "and exact shopping list before you leave the house. "
            "Family of 4. $80 a week. Healthy meals every night. "
            "Free at communitygroceries.com"
        ),
    },
    {
        "name": "CG - Say Goodbye To Whats For Dinner",
        "title": "Say Goodbye To 'What's For Dinner?'",
        "body": (
            "Say goodbye to the 5pm panic of figuring out what to cook. "
            "Say goodbye to throwing away half the groceries you bought. "
            "Say goodbye to spending more than you need to. "
            "Community Groceries AI plans your meals your list and your budget "
            "in 30 seconds. Free at communitygroceries.com"
        ),
    },
]

# ──────────────────────────────────────────────────────────────────────
# NEW VOWELS BOOK ADS (formula-based, using actual book images)
# ──────────────────────────────────────────────────────────────────────
VOWELS_NEW_ADS = [
    {
        "name": "Vowels Book - Big Lie Food Industry Tells About Health",
        "title": "The Big Lie The Food Industry Tells About 'Healthy'",
        "body": (
            "Low fat. All natural. Heart healthy. "
            "These labels are designed to sell not to inform. "
            "The food industry spends $14 billion a year shaping what healthy looks like. "
            "This free book exposes 12 marketing tactics they use on your family "
            "and gives you a 10-second label test that cuts through all of it. "
            "Download your free copy now."
        ),
        "image": "book-white",
    },
    {
        "name": "Vowels Book - 5 Warning Signs Your Food Isnt Healthy",
        "title": "5 Warning Signs Your 'Healthy' Food Isn't Healthy",
        "body": (
            "Natural flavor can contain over 100 chemical compounds. "
            "No added sugar doesnt mean no sugar. "
            "Made with real fruit can mean 2% juice. "
            "Your family deserves the truth. "
            "This free book reveals the 5 red flags hiding on every label "
            "and what to buy instead. Download your free copy now."
        ),
        "image": "book-spread",
    },
    {
        "name": "Vowels Book - Truth About Food Labels Nobody Wants You To Read",
        "title": "The Truth About Food Labels Nobody Wants You To Read",
        "body": (
            "In 1970 the average packaged food had 5 ingredients. "
            "Today it has 30 plus most engineered in a lab. "
            "The food industry changed what we eat and hid it behind clever marketing. "
            "This free award-winning book traces the root cause using data "
            "most people have never seen. Get your copy now."
        ),
        "image": "book-white",
    },
    {
        "name": "Vowels Book - What Parents Must Know About Kids Nutrition",
        "title": "What Every Parent Must Know About Their Kids' Food",
        "body": (
            "Research shows food preferences are set before age 5. "
            "But food companies spend $1.8 billion a year marketing junk food to children. "
            "What if the eating patterns you grew up with "
            "are the same ones shaping your kids today? "
            "This free book traces the data from grocery shelf to health crisis. "
            "Download your free copy."
        ),
        "image": "book-spread",
    },
    {
        "name": "Vowels Book - When Did We Stop Eating Real Food",
        "title": "When Did We Stop Eating Real Food?",
        "body": (
            "In 1970 less than 5% of children were obese. Today its over 20%. "
            "What shifted? Its not willpower. Its not genetics. "
            "Researchers traced it to a change that started decades ago "
            "in how our food is made and who profits. "
            "This free book follows the data to the root cause. "
            "The story will change how you shop. Get your free copy now."
        ),
        "image": "book-white",
    },
    {
        "name": "Vowels Book - Find Out How To See Through Food Marketing",
        "title": "Find Out How You Can See Through Every Food Label",
        "body": (
            "The food industry spends more on advertising than the government "
            "spends on nutrition education. By a factor of 100 to 1. "
            "That's why healthy is so confusing. "
            "This free book gives you the data the tools and the 10 second test "
            "to make real informed choices for your family. "
            "Download your free copy now."
        ),
        "image": "book-spread",
    },
]


async def upload_image(client: httpx.AsyncClient, image_path: str) -> str:
    """Upload an image to the ad account and return its hash."""
    filename = Path(image_path).name
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    r = await client.post(
        f"{BASE}/{AD_ACCOUNT}/adimages",
        data={"access_token": TOKEN},
        files={"filename": (filename, image_bytes, "image/jpeg" if filename.endswith(".jpg") else "image/png")},
        timeout=60,
    )
    result = r.json()
    if "images" in result:
        img_data = list(result["images"].values())[0]
        print(f"  Uploaded {filename}: hash={img_data['hash']}")
        return img_data["hash"]
    else:
        print(f"  ERROR uploading {filename}: {json.dumps(result, indent=2)}")
        raise Exception(f"Image upload failed: {result}")


async def create_ad_creative(
    client: httpx.AsyncClient,
    name: str,
    page_id: str,
    ig_user_id: str,
    title: str,
    body: str,
    image_hash: str,
    link: str,
    lead_form_id: str,
    cta_type: str = "DOWNLOAD",
) -> str:
    """Create an ad creative with image + lead form."""
    creative_spec = {
        "name": name,
        "object_story_spec": json.dumps({
            "page_id": page_id,
            "instagram_user_id": ig_user_id,
            "link_data": {
                "message": body,
                "name": title,
                "image_hash": image_hash,
                "link": link,
                "call_to_action": {
                    "type": cta_type,
                    "value": {
                        "lead_gen_form_id": lead_form_id,
                        "link": link,
                    },
                },
            },
        }),
        "access_token": TOKEN,
    }

    r = await client.post(f"{BASE}/{AD_ACCOUNT}/adcreatives", data=creative_spec, timeout=30)
    result = r.json()
    if "id" in result:
        print(f"  Creative created: {name} -> {result['id']}")
        return result["id"]
    else:
        print(f"  ERROR creating creative {name}: {json.dumps(result, indent=2)}")
        raise Exception(f"Creative creation failed: {result}")


async def create_cg_video_creative(
    client: httpx.AsyncClient,
    name: str,
    title: str,
    body: str,
    video_id: str,
    image_hash: str,
) -> str:
    """Create a CG video ad creative with lead form."""
    creative_spec = {
        "name": name,
        "object_story_spec": json.dumps({
            "page_id": CG_PAGE,
            "instagram_user_id": CG_IG,
            "video_data": {
                "video_id": video_id,
                "title": title,
                "message": body,
                "image_hash": image_hash,
                "call_to_action": {
                    "type": "SIGN_UP",
                    "value": {
                        "lead_gen_form_id": CG_LEAD_FORM,
                        "link": "https://communitygroceries.com/",
                    },
                },
            },
        }),
        "access_token": TOKEN,
    }

    r = await client.post(f"{BASE}/{AD_ACCOUNT}/adcreatives", data=creative_spec, timeout=30)
    result = r.json()
    if "id" in result:
        print(f"  Creative created: {name} -> {result['id']}")
        return result["id"]
    else:
        print(f"  ERROR creating creative {name}: {json.dumps(result, indent=2)}")
        raise Exception(f"Creative creation failed: {result}")


async def create_ad(
    client: httpx.AsyncClient,
    name: str,
    adset_id: str,
    creative_id: str,
    status: str = "ACTIVE",
) -> str:
    """Create an ad under an adset."""
    r = await client.post(
        f"{BASE}/{AD_ACCOUNT}/ads",
        data={
            "name": name,
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": status,
            "access_token": TOKEN,
        },
        timeout=30,
    )
    result = r.json()
    if "id" in result:
        print(f"  Ad created: {name} -> {result['id']}")
        return result["id"]
    else:
        print(f"  ERROR creating ad {name}: {json.dumps(result, indent=2)}")
        raise Exception(f"Ad creation failed: {result}")


async def pause_ad(client: httpx.AsyncClient, ad_id: str, ad_name: str):
    """Pause an ad."""
    r = await client.post(
        f"{BASE}/{ad_id}",
        data={"status": "PAUSED", "access_token": TOKEN},
        timeout=15,
    )
    result = r.json()
    if result.get("success"):
        print(f"  Paused: {ad_name} ({ad_id})")
    else:
        print(f"  ERROR pausing {ad_name}: {result}")


async def main():
    async with httpx.AsyncClient(timeout=60) as client:
        # ─── Step 1: Upload book images ───
        print("\n=== UPLOADING BOOK IMAGES ===\n")
        book_white_hash = await upload_image(client, BOOK_WHITE)
        book_spread_hash = await upload_image(client, BOOK_SPREAD)
        image_hashes = {
            "book-white": book_white_hash,
            "book-spread": book_spread_hash,
        }

        # ─── Step 2: Pause old CG ads (except winner) ───
        print("\n=== PAUSING OLD CG ADS (keeping winner) ===\n")
        r = await client.get(
            f"{BASE}/120243278517510504/ads",
            params={
                "access_token": TOKEN,
                "fields": "name,id,effective_status",
                "limit": 20,
            },
        )
        for ad in r.json().get("data", []):
            if ad["id"] != CG_WINNER_AD_ID and ad.get("effective_status") != "PAUSED":
                await pause_ad(client, ad["id"], ad["name"])
            elif ad["id"] == CG_WINNER_AD_ID:
                print(f"  KEEPING WINNER: {ad['name']} ({ad['id']})")

        # ─── Step 3: Pause ALL old Vowels book ads ───
        print("\n=== PAUSING ALL OLD VOWELS BOOK ADS ===\n")
        r = await client.get(
            f"{BASE}/120243298860640504/ads",
            params={
                "access_token": TOKEN,
                "fields": "name,id,effective_status",
                "limit": 20,
            },
        )
        for ad in r.json().get("data", []):
            if ad.get("effective_status") != "PAUSED":
                await pause_ad(client, ad["id"], ad["name"])

        # ─── Step 4: Create new CG ads ───
        print("\n=== CREATING NEW CG ADS ===\n")
        # Get CG video thumbnail hash (reuse from winner)
        cg_image_hash = "4271098f478e7d6743d6cb503ccb3830"  # existing CG logo hash

        for ad_def in CG_NEW_ADS:
            creative_id = await create_cg_video_creative(
                client,
                name=f"CG Creative - {ad_def['name']}",
                title=ad_def["title"],
                body=ad_def["body"],
                video_id=CG_VIDEO_ID,
                image_hash=cg_image_hash,
            )
            await create_ad(
                client,
                name=ad_def["name"],
                adset_id=CG_ADSET,
                creative_id=creative_id,
                status="ACTIVE",
            )

        # ─── Step 5: Create new Vowels book ads ───
        print("\n=== CREATING NEW VOWELS BOOK ADS ===\n")
        for ad_def in VOWELS_NEW_ADS:
            img_hash = image_hashes[ad_def["image"]]
            creative_id = await create_ad_creative(
                client,
                name=f"Vowels Creative - {ad_def['name']}",
                page_id=VOWELS_PAGE,
                ig_user_id=VOWELS_IG,
                title=ad_def["title"],
                body=ad_def["body"],
                image_hash=img_hash,
                link="https://vowels.org/",
                lead_form_id=VOWELS_LEAD_FORM,
                cta_type="DOWNLOAD",
            )
            await create_ad(
                client,
                name=ad_def["name"],
                adset_id=VOWELS_ADSET,
                creative_id=creative_id,
                status="ACTIVE",
            )

        print("\n=== DONE ===")
        print(f"  CG: 1 winner kept + {len(CG_NEW_ADS)} new ads created")
        print(f"  Vowels: All old paused + {len(VOWELS_NEW_ADS)} new ads with real book images")
        print("  Note: Campaigns are currently PAUSED. Unpause when ready to run.")


asyncio.run(main())
