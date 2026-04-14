"""Check and fix duplicate titles."""
import httpx
import json

slugs = ["why-fitbit-versa-2-wrong-time-button", "why-fitbit-versa-2-wrog-time"]
for slug in slugs:
    r = httpx.get(f"https://storage.googleapis.com/wihy-web-assets/blog/posts/{slug}.json", timeout=15)
    if r.status_code == 200:
        p = r.json()
        print(f"Slug: {slug}")
        print(f"  Title: {p.get('title')}")
        print(f"  Route: {p.get('route_path')}")
        print(f"  Words: {p.get('word_count')}")
        print(f"  Created: {p.get('created_at')}")
        print(f"  Meta: {p.get('meta_description', '')[:80]}")
        print()
    else:
        print(f"{slug}: HTTP {r.status_code}")
