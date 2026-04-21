"""Get per-ad performance across ALL campaigns."""
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
BASE = "https://graph.facebook.com/v21.0"
ACCOUNT = "act_218581359635343"


def get_leads(actions):
    if not actions:
        return 0
    for a in actions:
        if a["action_type"] == "lead":
            return int(a["value"])
    return 0


async def main():
    async with httpx.AsyncClient(timeout=30) as c:
        # Get all campaigns
        r = await c.get(
            f"{BASE}/{ACCOUNT}/campaigns",
            params={
                "access_token": TOKEN,
                "fields": "name,id,effective_status,insights.date_preset(last_7d){impressions,clicks,reach,spend,ctr,actions}",
                "limit": 50,
            },
        )
        campaigns = r.json().get("data", [])
        print(f"=== {len(campaigns)} CAMPAIGNS ===\n")
        for camp in campaigns:
            ins = (
                camp.get("insights", {}).get("data", [{}])[0]
                if camp.get("insights")
                else {}
            )
            leads = get_leads(ins.get("actions"))
            spend = ins.get("spend", "0")
            print(
                f"  [{camp['effective_status']}] {camp['name']}"
            )
            print(
                f"    ID: {camp['id']} | Spend: ${spend} | Leads: {leads}"
            )
            print()

        # Get ALL ads across account with last_7d
        r = await c.get(
            f"{BASE}/{ACCOUNT}/ads",
            params={
                "access_token": TOKEN,
                "fields": "name,id,effective_status,campaign_id,insights.date_preset(last_7d){impressions,clicks,reach,spend,ctr,actions,cost_per_action_type}",
                "limit": 100,
            },
        )
        ads = r.json().get("data", [])
        print(f"\n=== {len(ads)} ADS (last 7d) ===\n")

        # Group by campaign
        by_campaign = {}
        for ad in ads:
            cid = ad.get("campaign_id", "unknown")
            by_campaign.setdefault(cid, []).append(ad)

        for cid, ad_list in by_campaign.items():
            # Find campaign name
            camp_name = next(
                (c["name"] for c in campaigns if c["id"] == cid), cid
            )
            print(f"\n--- {camp_name} ---")
            for ad in sorted(
                ad_list,
                key=lambda a: float(
                    a.get("insights", {}).get("data", [{}])[0].get("spend", "0")
                    if a.get("insights")
                    else "0"
                ),
                reverse=True,
            ):
                ins = (
                    ad.get("insights", {}).get("data", [{}])[0]
                    if ad.get("insights")
                    else {}
                )
                leads = get_leads(ins.get("actions"))
                spend = float(ins.get("spend", "0"))
                ctr = ins.get("ctr", "0")
                reach = ins.get("reach", "0")
                impr = ins.get("impressions", "0")
                cpl = f"${spend / leads:.2f}" if leads > 0 else "N/A"
                status = ad["effective_status"]
                flag = ""
                if spend > 3 and leads == 0:
                    flag = " ⚠️ HIGH SPEND NO LEADS"
                elif leads > 0 and spend / leads < 1.50:
                    flag = " ✅ WINNER"
                print(
                    f"  [{status}] {ad['name']}{flag}"
                )
                print(
                    f"    Spend: ${spend:.2f} | Leads: {leads} | CPL: {cpl} | CTR: {ctr}% | Reach: {reach} | Impr: {impr}"
                )


asyncio.run(main())
