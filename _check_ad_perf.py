"""Get per-ad performance for CG and Vowels campaigns."""
import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
BASE = "https://graph.facebook.com/v21.0"

CG_CAMPAIGN = "120243278517510504"
VOWELS_CAMPAIGN = "120243298860640504"


def get_leads(actions):
    if not actions:
        return 0
    for a in actions:
        if a["action_type"] == "lead":
            return int(a["value"])
    return 0


async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        for label, campaign_id in [
            ("CG Lead Gen", CG_CAMPAIGN),
            ("Vowels Book", VOWELS_CAMPAIGN),
        ]:
            r = await c.get(
                f"{BASE}/{campaign_id}/ads",
                params={
                    "access_token": TOKEN,
                    "fields": "name,id,effective_status,insights.date_preset(last_7d){impressions,clicks,reach,spend,ctr,actions}",
                    "limit": 20,
                },
            )
            data = r.json().get("data", [])
            print(f"\n=== {label} ({len(data)} ads) ===\n")
            for ad in data:
                ins = (
                    ad.get("insights", {}).get("data", [{}])[0]
                    if ad.get("insights")
                    else {}
                )
                leads = get_leads(ins.get("actions"))
                spend = ins.get("spend", "0")
                ctr = ins.get("ctr", "0")
                reach = ins.get("reach", "0")
                impressions = ins.get("impressions", "0")
                cpl = f"${float(spend) / leads:.2f}" if leads > 0 else "N/A"
                print(f"  [{ad['effective_status']}] {ad['name']}")
                print(
                    f"    ID: {ad['id']} | Spend: ${spend} | Leads: {leads} | CPL: {cpl} | CTR: {ctr}% | Reach: {reach} | Impr: {impressions}"
                )
                print()

        # Also get adset IDs for creating new ads
        print("\n=== ADSET IDs ===\n")
        for label, campaign_id in [
            ("CG", CG_CAMPAIGN),
            ("Vowels", VOWELS_CAMPAIGN),
        ]:
            r = await c.get(
                f"{BASE}/{campaign_id}/adsets",
                params={
                    "access_token": TOKEN,
                    "fields": "name,id,effective_status",
                    "limit": 10,
                },
            )
            for adset in r.json().get("data", []):
                print(
                    f"  [{label}] {adset['name']} | ID: {adset['id']} | Status: {adset['effective_status']}"
                )


asyncio.run(main())
