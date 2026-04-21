#!/usr/bin/env python
"""
test_orchestrate_post.py — Test the full Alex → Shania → LABAT orchestrated pipeline.

Tests:
1. Shania Graphics health check
2. Plan-only post (text, no image)
3. Generate post with brand logo asset (no extra styling)
4. Orchestrated pipeline (Alex signals + Shania content + delivery)
5. Facebook post via LABAT route
6. Verify post appears in page feed
7. Clean up (delete test post)
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
SHANIA_GRAPHICS_URL = "https://wihy-shania-graphics-12913076533.us-central1.run.app"
SHANIA_ENGAGEMENT_URL = "https://wihy-shania-12913076533.us-central1.run.app"
ALEX_URL = "https://wihy-alex-n4l2vldq3q-uc.a.run.app"

HEADERS = {"X-Admin-Token": ADMIN_TOKEN, "Content-Type": "application/json"}

BRANDS_TO_TEST = ["wihy", "communitygroceries"]


async def run_tests():
    created_post_ids = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        print("=" * 70)
        print("ORCHESTRATED PIPELINE TEST: Alex → Shania → LABAT")
        print(f"Time: {datetime.now().isoformat()}")
        print("=" * 70)

        # ── 1. Health checks ──────────────────────────────────────────

        print("\n[1] HEALTH CHECKS")

        # Shania Graphics
        try:
            r = await client.get(f"{SHANIA_GRAPHICS_URL}/health")
            h = r.json()
            print(f"  Shania Graphics: {h.get('status', 'unknown')} (templates: {h.get('templates', '?')})")
        except Exception as e:
            print(f"  Shania Graphics: FAILED - {e}")

        # Shania Engagement
        try:
            r = await client.get(f"{SHANIA_ENGAGEMENT_URL}/health")
            h = r.json()
            print(f"  Shania Engagement: {h.get('status', 'unknown')}")
        except Exception as e:
            print(f"  Shania Engagement: FAILED - {e}")

        # Alex
        try:
            r = await client.get(f"{ALEX_URL}/api/alex/health")
            h = r.json()
            print(f"  Alex: {h.get('status', 'unknown')}")
        except Exception as e:
            print(f"  Alex: FAILED - {e}")

        # ── 2. Plan-only post (text, no image generation) ────────────

        print("\n[2] PLAN-ONLY POST (text only)")
        for brand in BRANDS_TO_TEST:
            try:
                r = await client.post(
                    f"{SHANIA_GRAPHICS_URL}/plan-post",
                    json={"prompt": "The hidden dangers of ultra-processed snack foods for kids", "brand": brand},
                    headers=HEADERS,
                )
                plan = r.json()
                if r.status_code == 200:
                    caption_preview = plan.get("caption", "")[:100]
                    hashtags = plan.get("hashtags", [])[:5]
                    print(f"  [{brand}] OK — caption: \"{caption_preview}...\"")
                    print(f"           hashtags: {hashtags}")
                    print(f"           approvalId: {plan.get('approvalId', 'N/A')}")
                else:
                    print(f"  [{brand}] FAILED {r.status_code}: {plan}")
            except Exception as e:
                print(f"  [{brand}] ERROR: {e}")

        # ── 3. Generate post with brand logo (should be clean) ───────

        print("\n[3] GENERATE POST (brand logo — no extra styling)")
        for brand in BRANDS_TO_TEST:
            try:
                r = await client.post(
                    f"{SHANIA_GRAPHICS_URL}/generate-post",
                    json={
                        "prompt": "Why reading food labels matters more than counting calories",
                        "brand": brand,
                        "outputSize": "feed_square",
                    },
                    headers=HEADERS,
                )
                result = r.json()
                if r.status_code == 200:
                    image_url = result.get("imageUrl")
                    caption_preview = result.get("caption", "")[:80]
                    print(f"  [{brand}] OK — image: {image_url or 'inline'}")
                    print(f"           caption: \"{caption_preview}...\"")
                    print(f"           brand: {result.get('brand')}")
                else:
                    print(f"  [{brand}] FAILED {r.status_code}: {result.get('error', result)}")
            except Exception as e:
                print(f"  [{brand}] ERROR: {e}")

        # ── 4. Orchestrated pipeline (dry run) ───────────────────────

        print("\n[4] ORCHESTRATED PIPELINE (dry run)")
        for brand in BRANDS_TO_TEST:
            try:
                r = await client.post(
                    f"{SHANIA_GRAPHICS_URL}/orchestrate-post",
                    json={
                        "prompt": "Hidden sugars in foods marketed as healthy — what parents need to know",
                        "brand": brand,
                        "platforms": ["facebook", "twitter"],
                        "dryRun": True,
                    },
                    headers=HEADERS,
                )
                result = r.json()
                if r.status_code == 200:
                    pipeline = result.get("pipeline", {})
                    alex_status = pipeline.get("alex", {}).get("status", "?")
                    shania_status = pipeline.get("shania", {}).get("status", "?")
                    delivery = pipeline.get("delivery", {})
                    print(f"  [{brand}] OK")
                    print(f"           Alex: {alex_status}")
                    print(f"           Shania: {shania_status} (caption: {pipeline.get('shania', {}).get('captionLength', 0)} chars)")
                    print(f"           Delivery: {json.dumps(delivery, default=str)[:120]}")
                    print(f"           Image: {result.get('imageUrl', 'N/A')}")
                else:
                    print(f"  [{brand}] FAILED {r.status_code}: {result.get('error', result)}")
            except Exception as e:
                print(f"  [{brand}] ERROR: {e}")

        # ── 5. Live Facebook post via orchestration ──────────────────

        print("\n[5] LIVE FACEBOOK POST (via orchestration)")
        try:
            r = await client.post(
                f"{SHANIA_GRAPHICS_URL}/orchestrate-post",
                json={
                    "prompt": "Exposing what food companies hide in plain sight — the truth about ultra-processed foods",
                    "brand": "wihy",
                    "platforms": ["facebook"],
                    "dryRun": False,
                },
                headers=HEADERS,
            )
            result = r.json()
            if r.status_code == 200:
                pipeline = result.get("pipeline", {})
                fb_delivery = pipeline.get("delivery", {}).get("facebook", {})
                print(f"  Status: {fb_delivery.get('status', 'unknown')}")
                post_result = fb_delivery.get("result", {})
                post_id = post_result.get("id")
                if post_id:
                    created_post_ids.append(post_id)
                    print(f"  Post ID: {post_id}")
                print(f"  Caption preview: \"{result.get('caption', '')[:80]}...\"")
                print(f"  Image URL: {result.get('imageUrl', 'N/A')}")
            else:
                print(f"  FAILED {r.status_code}: {result.get('error', result)}")
        except Exception as e:
            print(f"  ERROR: {e}")

        # ── 6. Verify post in page feed ──────────────────────────────

        print("\n[6] VERIFY POST IN PAGE FEED")
        try:
            r = await client.get(
                f"{SHANIA_ENGAGEMENT_URL}/api/labat/page/feed?limit=5",
                headers=HEADERS,
            )
            feed = r.json()
            posts = feed.get("data", [])
            print(f"  Found {len(posts)} posts in feed:")
            for p in posts[:3]:
                msg = (p.get("message") or "(no text)")[:60]
                print(f"    {p['id']} | {p.get('created_time', '')} | {msg}")
        except Exception as e:
            print(f"  ERROR: {e}")

        # ── 7. Alex-initiated orchestration (via Alex route) ─────────

        print("\n[7] ALEX-INITIATED ORCHESTRATION (dry run)")
        try:
            r = await client.post(
                f"{ALEX_URL}/api/alex/orchestrate-post",
                json={
                    "prompt": "The real cost of fast food: what $5 buys your health",
                    "brand": "wihy",
                    "platforms": ["facebook", "twitter"],
                    "dry_run": True,
                },
                headers={"X-Admin-Token": ADMIN_TOKEN, "Content-Type": "application/json"},
            )
            result = r.json()
            if r.status_code == 200:
                print(f"  Source: {result.get('source', '?')}")
                print(f"  Brand: {result.get('brand', '?')}")
                caption = result.get("caption", "")[:80]
                print(f"  Caption: \"{caption}...\"")
                print(f"  Image URL: {result.get('imageUrl', 'N/A')}")
            else:
                print(f"  FAILED {r.status_code}: {result}")
        except Exception as e:
            print(f"  ERROR: {e}")

        # ── 8. Cleanup ───────────────────────────────────────────────

        print("\n[8] CLEANUP — deleting test posts")
        for pid in created_post_ids:
            try:
                r = await client.delete(
                    f"{SHANIA_ENGAGEMENT_URL}/api/labat/posts/{pid}",
                    headers=HEADERS,
                )
                result = r.json()
                print(f"  Deleted {pid}: {result}")
            except Exception as e:
                print(f"  Failed to delete {pid}: {e}")

        if not created_post_ids:
            print("  No posts to clean up.")

        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_tests())
