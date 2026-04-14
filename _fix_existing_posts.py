"""Fix existing GCS posts: strip ## Related Posts / ## References from body,
parse related_posts into the proper array, and fix route_base /health -> /insights."""

import json
import re
import urllib.request
from google.cloud import storage

GCS_BUCKET = "wihy-web-assets"
INDEX_URL = f"https://storage.googleapis.com/{GCS_BUCKET}/blog/posts/index.json"
POST_PREFIX = "blog/posts/"

# Route base fix
ROUTE_FIXES = {"/health": "/insights", "/is-it-healthy": "/insights"}


def fetch_post(slug: str) -> dict:
    url = f"https://storage.googleapis.com/{GCS_BUCKET}/{POST_PREFIX}{slug}.json"
    data = urllib.request.urlopen(url).read()
    return json.loads(data)


def fix_body(post: dict) -> bool:
    """Strip ## Related Posts and ## References from body. Returns True if changed."""
    body = post.get("body", "")
    original = body
    changed = False

    # Extract related_posts from body
    rp_match = re.search(r'\n## Related Posts\b.*', body, re.DOTALL | re.IGNORECASE)
    if rp_match:
        rp_block = rp_match.group(0)
        body = body[:rp_match.start()].rstrip()
        if not post.get("related_posts"):
            parsed = []
            for m in re.finditer(r'\{\s*"slug"\s*:\s*"([^"]+)"\s*,\s*"title"\s*:\s*"([^"]+)"\s*\}', rp_block):
                parsed.append({"slug": m.group(1), "title": m.group(2)})
            if parsed:
                post["related_posts"] = parsed
                print(f"  Extracted {len(parsed)} related_posts")

    # Strip References/Citations/Sources
    for heading in ('## References', '## Citations', '## Sources'):
        ref_match = re.search(rf'\n{re.escape(heading)}\b.*', body, re.DOTALL | re.IGNORECASE)
        if ref_match:
            body = body[:ref_match.start()].rstrip()
            print(f"  Stripped '{heading}' section")

    if body != original:
        post["body"] = body
        post["word_count"] = len(body.split())
        changed = True

    return changed


def fix_route(post: dict) -> bool:
    """Fix route_base from /health or /is-it-healthy to /insights."""
    rb = post.get("route_base", "")
    if rb in ROUTE_FIXES:
        new_rb = ROUTE_FIXES[rb]
        post["route_base"] = new_rb
        post["route_path"] = f"{new_rb}/{post['slug']}"
        print(f"  Fixed route: {rb} -> {new_rb}")
        return True
    return False


def main():
    # Load index
    data = urllib.request.urlopen(INDEX_URL).read()
    index = json.loads(data)
    slugs = [p["slug"] for p in index["posts"]]
    print(f"Found {len(slugs)} posts to check\n")

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    updated_slugs = []

    for slug in slugs:
        print(f"Checking: {slug}")
        post = fetch_post(slug)

        body_fixed = fix_body(post)
        route_fixed = fix_route(post)

        if body_fixed or route_fixed:
            # Upload fixed post
            blob = bucket.blob(f"{POST_PREFIX}{slug}.json")
            blob.upload_from_string(
                json.dumps(post, ensure_ascii=False, indent=2),
                content_type="application/json",
            )
            print(f"  UPLOADED fix for {slug}")
            updated_slugs.append(slug)
        else:
            print(f"  OK (no changes needed)")

    # Rebuild index with fixed route_base values
    if updated_slugs:
        print(f"\nRebuilding index ({len(updated_slugs)} posts changed)...")
        # Re-fetch all posts to build fresh index
        new_index_posts = []
        for slug in slugs:
            post = fetch_post(slug)
            entry = {k: v for k, v in post.items() if k != "body"}
            # Remove large fields from index
            for k in ("faq_items", "seo_keywords", "key_takeaways"):
                entry.pop(k, None)
            new_index_posts.append(entry)

        index_blob = bucket.blob(f"{POST_PREFIX}index.json")
        index_blob.upload_from_string(
            json.dumps({"posts": new_index_posts}, ensure_ascii=False, indent=2),
            content_type="application/json",
        )
        print("Index rebuilt!")

    print(f"\nDone. Fixed {len(updated_slugs)} posts: {updated_slugs}")


if __name__ == "__main__":
    main()
