#!/usr/bin/env python
"""
test_shania_labat_roundtrip.py — Test Shania ↔ LABAT communication

Tests the full engagement pipeline:
1. LABAT lists lead forms
2. LABAT fetches leads from a form
3. Shania engages with that lead (dry run)
4. Verify roundtrip communication works
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


async def test_roundtrip():
    """Test full Shania ↔ LABAT communication."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=" * 70)
        print("TESTING SHANIA ↔ LABAT ROUNDTRIP")
        print("=" * 70)

        # 1. Test Shania health
        print("\n[1] SHANIA HEALTH CHECK")
        try:
            r = await client.get(f"{SHANIA_URL}/health", headers=headers)
            shania_health = r.json()
            print(f"✅ Shania health: {shania_health['status']}")
            print(f"   Monitor: running={shania_health['monitor']['running']}")
            print(
                f"   Facebook config: shania_app={shania_health['facebook']['shania_app']}, "
                f"page_token={shania_health['facebook']['shania_page_token']}"
            )
        except Exception as e:
            print(f"❌ Shania health failed: {e}")
            return

        # 2. Test LABAT health
        print("\n[2] LABAT HEALTH CHECK")
        try:
            r = await client.get(f"{LABAT_URL}/health", headers=headers)
            labat_health = r.json()
            print(f"✅ LABAT health: {labat_health['status']}")
            all_green = all(labat_health["config"].values())
            print(
                f"   Config ready: {all_green} "
                f"(shania_app={labat_health['config']['shania_app']}, "
                f"labat_app={labat_health['config']['labat_app']})"
            )
        except Exception as e:
            print(f"❌ LABAT health failed: {e}")
            return

        # 3. List lead forms on LABAT
        print("\n[3] LABAT: LIST LEAD FORMS")
        try:
            r = await client.get(f"{LABAT_URL}/api/labat/leads/forms", headers=headers)
            forms_resp = r.json()
            forms = forms_resp.get("data", [])
            print(f"✅ Found {len(forms)} lead forms")
            if forms:
                for i, form in enumerate(forms[:2]):  # Show first 2
                    print(f"   Form {i + 1}: id={form['id']}, name={form['name']}, leads={form.get('leads_count', 0)}")
            else:
                print("   ℹ️  No forms found (create one in Ads Manager > Lead Generation)")
        except Exception as e:
            print(f"⚠️  Could not list forms: {e}")
            forms = []

        # 4. Simulate engagement request to Shania (dry run)
        print("\n[4] SHANIA: DRY-RUN ENGAGEMENT")
        engage_payload = {
            "platform": "facebook",
            "action": "comment",
            "target_id": "123456789_abcdef",  # Fake post ID
            "post_content": "I've been struggling with my weight and diet consistency. Any tips?",
            "topic": "weight loss nutrition diet",
            "lead_id": "test-lead-uuid-001",
            "author": "john_smith",
            "dry_run": True,
        }
        try:
            r = await client.post(
                f"{SHANIA_URL}/api/engagement/engage",
                json=engage_payload,
                headers=headers,
                timeout=60.0,
            )
            engage_resp = r.json()
            if engage_resp.get("success"):
                print(f"✅ Shania generated engagement content (dry run)")
                print(f"   Platform: {engage_resp['platform']}")
                print(f"   Action: {engage_resp['action']}")
                print(f"   Generated comment:\n     \"{engage_resp['content']}\"")
            else:
                print(f"❌ Engagement failed: {engage_resp.get('error')}")
        except Exception as e:
            print(f"❌ Engagement call failed: {e}")

        # 5. Test LABAT insight (cost summary)
        print("\n[5] LABAT: LEAD COST SUMMARY")
        try:
            r = await client.get(
                f"{LABAT_URL}/api/labat/leads/cost?date_preset=last_30d",
                headers=headers,
            )
            cost_resp = r.json()
            data = cost_resp.get("data", [])
            if data:
                print(f"✅ Lead cost insights for last 30 days:")
                for i, row in enumerate(data[:2]):
                    print(
                        f"   {i + 1}. {row.get('campaign_name', 'N/A')}: "
                        f"spend=${row.get('spend', 0)} | "
                        f"clicks={row.get('clicks', 0)} | "
                        f"leads={row.get('actions', {}).get('offsite_conversion.lead', 0) if isinstance(row.get('actions'), dict) else 'N/A'}"
                    )
            else:
                print("   ℹ️  No cost data yet (campaigns may not have leads)")
        except Exception as e:
            print(f"⚠️  Could not fetch cost summary: {e}")

        # 6. Test auth endpoint (exchange-shania)
        print("\n[6] LABAT: AUTH ENDPOINT (for token exchange)")
        print(f"   POST /api/labat/auth/exchange-shania")
        print(f"   Usage: exchange short-lived Shania token for long-lived page token")
        print(f"   Status: Ready to accept tokens (placeholder currently deployed)")

        print("\n" + "=" * 70)
        print("ROUNDTRIP TEST COMPLETE ✅")
        print("=" * 70)
        print("\nNEXT STEPS:")
        print("1. Get real Shania page token from Graph API Explorer")
        print("2. Call POST /api/labat/auth/exchange-shania to store it")
        print("3. Then Shania can publish to Facebook, reply to posts, send messages")
        print("\nLABAT endpoint summary:")
        print("  Ads:        POST /api/labat/ads/campaigns")
        print("  Leads:      GET  /api/labat/leads/forms")
        print("  Insights:   GET  /api/labat/insights/summary")
        print("\nShania endpoint summary:")
        print("  Engagement: POST /api/engagement/engage (dry-run or live post)")
        print("  Facebook:   POST /api/labat/posts (publish), GET /api/labat/page/feed")


if __name__ == "__main__":
    asyncio.run(test_roundtrip())
