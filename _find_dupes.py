"""Find and differentiate near-duplicate post titles."""
import httpx
import json
import subprocess
import tempfile
from pathlib import Path
from collections import defaultdict

GCS_BUCKET = "gs://wihy-web-assets/blog/posts"
GCS_PUBLIC = "https://storage.googleapis.com/wihy-web-assets/blog/posts"
GCLOUD = r"C:\Users\Kortn\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"


def main():
    r = httpx.get(f"{GCS_PUBLIC}/index.json", timeout=15)
    index = r.json()
    posts = index.get("posts", [])
    
    # Group by title to find exact duplicates
    by_title = defaultdict(list)
    for p in posts:
        by_title[p["title"].lower().strip()].append(p)
    
    dupes = {t: ps for t, ps in by_title.items() if len(ps) > 1}
    print(f"=== Exact duplicate titles: {len(dupes)} ===")
    for title, ps in dupes.items():
        print(f"\n  Title: {title}")
        for p in ps:
            print(f"    - {p['slug']} ({p.get('route_path', '?')})")
    
    # Find near-duplicate titles (similar words)
    print(f"\n=== Near-duplicate titles ===")
    seen = set()
    for i, p1 in enumerate(posts):
        for p2 in posts[i+1:]:
            key = tuple(sorted([p1["slug"], p2["slug"]]))
            if key in seen:
                continue
            seen.add(key)
            
            words1 = set(p1["title"].lower().split())
            words2 = set(p2["title"].lower().split())
            common = words1 & words2
            # Remove stop words
            common -= {"the", "a", "an", "of", "for", "to", "in", "on", "and", "or", "is", "are", "your", "you", "best", "how", "what", "why", "do"}
            
            if len(common) >= 3 and len(common) / max(len(words1), len(words2)) >= 0.5:
                print(f"\n  Similar ({len(common)} shared words):")
                print(f"    1: {p1['title']} ({p1['slug']})")
                print(f"    2: {p2['title']} ({p2['slug']})")


if __name__ == "__main__":
    main()
