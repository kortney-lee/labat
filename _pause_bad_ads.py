"""Pause all underperforming ads (0 leads or CPL > $3.50). Keep winners."""
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
        # Get ALL active ads with insights
        r = await c.get(
            f"{BASE}/{ACCOUNT}/ads",
            params={
                "access_token": TOKEN,
                "fields": "name,id,effective_status,campaign_id,adset_id,"
                          "insights.date_preset(last_7d){spend,actions,ctr,impressions}",
                "limit": 100,
                "filtering": '[{"field":"effective_status","operator":"IN","value":["ACTIVE"]}]',
            },
        )
        ads = r.json().get("data", [])
        print(f"Found {len(ads)} active ads\n")

        to_pause = []
        to_keep = []

        for ad in ads:
            ins = ad.get("insights", {}).get("data", [{}])[0] if ad.get("insights") else {}
            leads = get_leads(ins.get("actions"))
            spend = float(ins.get("spend", "0"))
            ctr = float(ins.get("ctr", "0"))
            impr = int(ins.get("impressions", "0"))
            cpl = spend / leads if leads > 0 else None

            # PAUSE if: 0 leads OR CPL > $3.50
            is_bad = False
            reason = ""
            if leads == 0 and spend > 0:
                is_bad = True
                reason = f"0 leads, ${spend:.2f} wasted"
            elif leads == 0 and spend == 0 and impr < 5:
                is_bad = True
                reason = "no delivery"
            elif cpl and cpl > 3.50:
                is_bad = True
                reason = f"CPL ${cpl:.2f} too high"

            if is_bad:
                to_pause.append((ad["id"], ad["name"], reason))
            else:
                to_keep.append((ad["id"], ad["name"], leads, spend, cpl))

        print("=== KEEPING (winners) ===")
        for ad_id, name, leads, spend, cpl in to_keep:
            cpl_str = f"${cpl:.2f}" if cpl else "N/A"
            print(f"  ✅ {name} | {leads} leads | ${spend:.2f} | CPL: {cpl_str}")

        print(f"\n=== PAUSING {len(to_pause)} ADS ===")
        for ad_id, name, reason in to_pause:
            print(f"  ❌ {name} | {reason}")
            r = await c.post(
                f"{BASE}/{ad_id}",
                data={"status": "PAUSED", "access_token": TOKEN},
            )
            result = r.json()
            if result.get("success"):
                print(f"     -> PAUSED OK")
            else:
                print(f"     -> ERROR: {result}")

        print(f"\nDone. Kept {len(to_keep)} winners, paused {len(to_pause)} losers.")


asyncio.run(main())
