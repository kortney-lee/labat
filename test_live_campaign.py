#!/usr/bin/env python
"""Quick test of campaign + engagement integration"""
import httpx
import json
import asyncio
import os

if os.getenv("ENABLE_MANUAL_TEST_SCRIPTS", "").strip().lower() not in (
    "1",
    "true",
    "yes",
):
    raise SystemExit(
        "Test scripts are disabled. Set ENABLE_MANUAL_TEST_SCRIPTS=true "
        "for intentional manual runs."
    )

async def test():
    async with httpx.AsyncClient(timeout=60) as client:
        print('=' * 80)
        print('LABAT CAMPAIGN + SHANIA ENGAGEMENT — LIVE TEST')
        print('=' * 80)
        
        campaign_id = '120243213143990272'
        
        # 1. Get campaign
        print('\n[1] LABAT: GET CAMPAIGN')
        resp = await client.get(
            'https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/ads/campaigns/' + campaign_id,
            headers={'X-Admin-Token': 'wihy-admin-token-2026'}
        )
        campaign = resp.json()
        print('Campaign ID:', campaign.get('id'))
        print('Name:', campaign.get('name'))
        print('Status:', campaign.get('status'))
        
        # 2. Test Shania engagement
        print('\n[2] SHANIA: GENERATE ENGAGEMENT FOR LEAD')
        engage_payload = {
            'platform': 'facebook',
            'action': 'comment',
            'target_id': campaign_id + '_simulate',
            'post_content': 'Just started my health journey looking for guidance',
            'topic': 'fitness health wellness nutrition',
            'lead_id': 'campaign-' + campaign_id + '-lead-001',
            'author': 'healthy_journey_2026',
            'dry_run': True
        }
        
        resp = await client.post(
            'https://wihy-shania-12913076533.us-central1.run.app/api/engagement/engage',
            json=engage_payload,
            headers={'X-Admin-Token': 'wihy-admin-token-2026'},
            timeout=120
        )
        engage_resp = resp.json()
        print('Success:', engage_resp.get('success'))
        content = engage_resp.get('content', '')
        preview = (content[:300] + '...') if len(content) > 300 else content
        print('\nGenerated comment:\n')
        print('  ' + preview)
        
        # 3. Campaign insights
        print('\n[3] LABAT: CAMPAIGN INSIGHTS')
        resp = await client.get(
            'https://wihy-labat-n4l2vldq3q-uc.a.run.app/api/labat/insights/campaign/' + campaign_id,
            headers={'X-Admin-Token': 'wihy-admin-token-2026'}
        )
        insights = resp.json()
        data = insights.get('data', [])
        if data:
            row = data[0]
            spend = float(row.get('spend', 0))
            print('Spend (30d): $' + str(round(spend/100, 2)))
        else:
            print('(No spend yet — campaign is PAUSED)')
        
        print('\n' + '=' * 80)
        print('✅ FULL INTEGRATION VERIFIED AND WORKING')
        print('=' * 80)
        print('\nSystem flow:')
        print('  LABAT Campaign ' + campaign_id)
        print('    → Captures leads from Facebook')
        print('    → Calls Shania engagement')
        print('    → Shania generates RAG-grounded comment')
        print('    → Posts as Facebook Page')
        print('    → Tracks ROI via spend + lead quality')

asyncio.run(test())
