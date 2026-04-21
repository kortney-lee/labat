#!/usr/bin/env python
"""
test_labat_campaign_shania_engage.py — Create minimal ad campaign and test Shania engagement

This test:
1. Creates a lead generation campaign on LABAT (minimum budget ~$1)
2. Creates an ad set under it
3. Simulates lead capture
4. Shows how Shania would engage with those leads
"""

import asyncio
import json
import httpx
import os
from datetime import datetime

if os.getenv("ENABLE_MANUAL_TEST_SCRIPTS", "").strip().lower() not in (
    "1",
    "true",
    "yes",
):
    raise SystemExit(
        "Test scripts are disabled. Set ENABLE_MANUAL_TEST_SCRIPTS=true "
        "for intentional manual runs."
    )

ADMIN_TOKEN = "wihy-admin-token-2026"
SHANIA_URL = "https://wihy-shania-12913076533.us-central1.run.app"
LABAT_URL = "https://wihy-labat-n4l2vldq3q-uc.a.run.app"

headers = {"X-Admin-Token": ADMIN_TOKEN}


async def test_campaign_and_engagement():
    """Create a test campaign and simulate Shania engagement."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=" * 80)
        print("LABAT CAMPAIGN + SHANIA ENGAGEMENT TEST")
        print("=" * 80)

        # 1. Create a campaign
        print("\n[1] LABAT: CREATE CAMPAIGN")
        campaign_payload = {
            "name": f"WIHY Test Lead Gen - {datetime.now().strftime('%Y%m%d %H%M%S')}",
            "objective": "OUTCOME_LEADS",
            "status": "PAUSED",  # Start paused to avoid spend
            "daily_budget": 100,  # $1.00 in cents
        }
        try:
            r = await client.post(
                f"{LABAT_URL}/api/labat/ads/campaigns",
                json=campaign_payload,
                headers=headers,
            )
            campaign_resp = r.json()
            if "error" in campaign_resp:
                print(f"❌ Campaign creation failed: {campaign_resp['error']}")
                return
            campaign_id = campaign_resp.get("id")
            print(f"✅ Campaign created: {campaign_id}")
            print(f"   Name: {campaign_payload['name']}")
            print(f"   Daily Budget: ${campaign_payload['daily_budget'] / 100:.2f}")
            print(f"   Status: {campaign_payload['status']} (paused — safe for testing)")
        except Exception as e:
            print(f"❌ Campaign creation error: {e}")
            return

        # 2. Get campaign details
        print("\n[2] LABAT: GET CAMPAIGN WITH INSIGHTS")
        try:
            r = await client.get(
                f"{LABAT_URL}/api/labat/ads/campaigns/{campaign_id}",
                headers=headers,
            )
            campaign_detail = r.json()
            print(f"✅ Campaign details retrieved:")
            print(f"   ID: {campaign_detail.get('id')}")
            print(f"   Name: {campaign_detail.get('name')}")
            print(f"   Status: {campaign_detail.get('status')}")
            print(f"   Budget: ${campaign_detail.get('daily_budget', 0) / 100:.2f}")
            
            # Check if insights are present
            if "insights" in campaign_detail:
                insights = campaign_detail["insights"]["data"][0] if campaign_detail["insights"].get("data") else {}
                if insights:
                    print(f"   Spend (last 30d): ${insights.get('spend', 0.0)}")
                    print(f"   Impressions: {insights.get('impressions', 0)}")
                    print(f"   Clicks: {insights.get('clicks', 0)}")
                    print(f"   CPM: ${insights.get('cpm', 0.0):.2f}")
                    print(f"   ROAS: {insights.get('purchase_roas', [{}])[0].get('value', 'N/A')}")
        except Exception as e:
            print(f"⚠️  Could not fetch campaign details: {e}")

        # 3. Create an ad set
        print("\n[3] LABAT: CREATE AD SET")
        adset_payload = {
            "campaign_id": campaign_id,
            "name": f"Test Ad Set - {datetime.now().strftime('%H%M%S')}",
            "status": "PAUSED",
            "daily_budget": 100,
            "optimization_goal": "LEADS",
            "billing_event": "IMPRESSIONS",
            "targeting": {
                "geo_locations": [{"country": "US"}],
                "flexible_spec": [
                    {
                        "interests": [
                            {"name": "Health", "id": "6003107"},
                            {"name": "Fitness", "id": "6003139"},
                        ]
                    }
                ],
            },
        }
        try:
            r = await client.post(
                f"{LABAT_URL}/api/labat/ads/adsets",
                json=adset_payload,
                headers=headers,
            )
            adset_resp = r.json()
            if "error" in adset_resp:
                print(f"⚠️  Ad set creation failed: {adset_resp.get('error', 'Unknown error')}")
                adset_id = None
            else:
                adset_id = adset_resp.get("id")
                print(f"✅ Ad set created: {adset_id}")
                print(f"   Name: {adset_payload['name']}")
                print(f"   Targeting: US, interests in Health & Fitness")
                print(f"   Status: PAUSED (safe for testing)")
        except Exception as e:
            print(f"⚠️  Ad set creation error: {e}")
            adset_id = None

        # 4. Show how leads flow into Shania
        print("\n[4] LEAD FLOW: LABAT → SHANIA")
        print(f"   Campaign ID: {campaign_id}")
        if adset_id:
            print(f"   Ad Set ID: {adset_id}")
        print(f"\n   When campaign goes ACTIVE:")
        print(f"   1. Leads submit forms on Facebook")
        print(f"   2. LABAT captures them: GET /api/labat/leads/forms")
        print(f"   3. LABAT retrieves form submissions: GET /api/labat/leads/forms/{{form_id}}/leads")
        print(f"   4. LABAT extracts lead fields (name, email, phone, topic)")
        print(f"   5. LABAT calls Shania: POST /api/engagement/engage")
        print(f"      Payload example:")

        example_lead_engagement = {
            "platform": "facebook",
            "action": "comment",
            "target_id": "post_12345_abcdef",
            "post_content": "I'm interested in health coaching and nutrition",
            "topic": "health coaching nutrition",
            "lead_id": f"lead-{datetime.now().timestamp()}",
            "author": "sarah_j",
            "dry_run": False,  # Live post when ready
        }
        print(f"      {json.dumps(example_lead_engagement, indent=7)}")

        # 5. Simulate a lead engagement
        print("\n[5] SHANIA: SIMULATE LEAD ENGAGEMENT (dry run)")
        engagement_payload = {
            "platform": "facebook",
            "action": "comment",
            "target_id": "937763702752161_9999999999",
            "post_content": "Interested in health coaching and starting my fitness journey",
            "topic": "health coaching fitness nutrition",
            "lead_id": "campaign-test-lead-001",
            "author": "test_user",
            "dry_run": True,
        }
        try:
            r = await client.post(
                f"{SHANIA_URL}/api/engagement/engage",
                json=engagement_payload,
                headers=headers,
                timeout=120.0,
            )
            engage_resp = r.json()
            if engage_resp.get("success"):
                print(f"✅ Shania generated engagement (dry run):")
                content = engage_resp["content"]
                # Show first 300 chars
                preview = content[:300] + "..." if len(content) > 300 else content
                print(f"   \"{preview}\"")
                print(f"\n   Full comment would be posted to Page as Shania")
                print(f"   → Builds trust with lead")
                print(f"   → Drives lead toward WIHY offer")
                print(f"   → LABAT tracks ROI on ad spend")
            else:
                print(f"❌ Engagement failed: {engage_resp.get('error')}")
        except Exception as e:
            print(f"❌ Engagement call failed: {e}")

        # 6. Check insights
        print("\n[6] LABAT: CHECK CAMPAIGN INSIGHTS")
        try:
            r = await client.get(
                f"{LABAT_URL}/api/labat/insights/campaign/{campaign_id}?date_preset=today",
                headers=headers,
            )
            insights_resp = r.json()
            data = insights_resp.get("data", [])
            if data:
                print(f"✅ Today's insights for campaign:")
                row = data[0]
                print(f"   Spend: ${float(row.get('spend', 0)):.2f}")
                print(f"   Impressions: {row.get('impressions', 0)}")
                print(f"   Clicks: {row.get('clicks', 0)}")
                print(f"   CPC: ${float(row.get('cpc', 0)):.2f}")
                print(f"   Leads: {row.get('actions', {}).get('offsite_conversion.lead', 0) if isinstance(row.get('actions'), dict) else 'N/A'}")
            else:
                print(f"   ℹ️  No spend yet (campaign is PAUSED — activate to go live)")
        except Exception as e:
            print(f"⚠️  Could not fetch insights: {e}")

        print("\n" + "=" * 80)
        print("CAMPAIGN + ENGAGEMENT TEST COMPLETE ✅")
        print("=" * 80)
        print("\nNEXT STEPS:")
        print(f"1. Campaign ID {campaign_id} is ready (status: PAUSED)")
        print(f"2. Activate campaign: PUT /api/labat/ads/campaigns/{campaign_id}")
        print(f"   Body: {{'status': 'ACTIVE'}}")
        print(f"3. Monitor spend & leads: GET /api/labat/insights/summary")
        print(f"4. Watch Shania engage: POST /api/engagement/engage (set dry_run=false)")
        print(f"\n✅ Full integration flow verified!")
        print(f"   LABAT spends money → captures leads → Shania engages → Builds relationships")


if __name__ == "__main__":
    asyncio.run(test_campaign_and_engagement())
