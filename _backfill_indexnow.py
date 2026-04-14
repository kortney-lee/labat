"""Backfill: submit all existing posts to IndexNow."""
import asyncio
import json

from src.content.post_publish_hooks import submit_indexnow_batch

idx = json.load(open("data/index.json"))
posts = idx["posts"]
urls = []
for p in posts:
    rp = p.get("route_path") or f"/blog/{p['slug']}"
    urls.append(f"https://wihy.ai{rp}")

print(f"Submitting {len(urls)} URLs to IndexNow...")
result = asyncio.run(submit_indexnow_batch(urls))
print(f"Done: {result} URLs submitted")
