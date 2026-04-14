"""
Backfill internal links into all wihy.ai blog posts.

Downloads each post JSON from GCS, injects contextual internal links
to related posts within the body markdown, and re-uploads.

Strategy:
  1. Build a topic→posts mapping from index.json
  2. For each post, find 3-5 related posts (same topic first, then adjacent topics)
  3. Inject a "Keep Reading" section at the end of the body (before FAQ)
  4. Inject 1-2 contextual inline links within the body text
  5. Re-upload post JSON to GCS

Usage:
    python _backfill_internal_links.py                 # backfill all posts
    python _backfill_internal_links.py --dry-run       # preview changes
    python _backfill_internal_links.py --slug my-post  # backfill one post
    python _backfill_internal_links.py --limit 10      # first N posts
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx

logger = logging.getLogger("wihy.backfill_internal_links")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# ── Config ────────────────────────────────────────────────────────────────────

GCS_BUCKET = "gs://wihy-web-assets/blog/posts"
GCS_PUBLIC = "https://storage.googleapis.com/wihy-web-assets/blog/posts"
DOMAIN = "https://wihy.ai"

# Topic adjacency — topics that are related and can cross-link
TOPIC_ADJACENCY = {
    "nutrition": ["supplements", "gut-health", "processed-foods", "meal-planning", "weight-management"],
    "supplements": ["nutrition", "immune-health", "protein-and-muscle"],
    "gut-health": ["nutrition", "immune-health", "processed-foods"],
    "heart-health": ["nutrition", "fitness", "weight-management"],
    "sugar-and-blood-health": ["nutrition", "weight-management", "processed-foods"],
    "processed-foods": ["nutrition", "gut-health", "sugar-and-blood-health"],
    "fasting": ["weight-management", "nutrition", "meal-planning"],
    "alcohol-and-health": ["nutrition", "heart-health"],
    "protein-and-muscle": ["fitness", "supplements", "nutrition"],
    "hydration": ["fitness", "nutrition"],
    "immune-health": ["supplements", "gut-health", "nutrition"],
    "hormones": ["nutrition", "fitness", "weight-management"],
    "brain-health": ["mental-health", "nutrition", "supplements"],
    "food-scanning": ["nutrition", "health-apps", "meal-planning"],
    "fitness": ["protein-and-muscle", "weight-management", "heart-health"],
    "mental-health": ["brain-health", "sleep", "wellness"],
    "sleep": ["mental-health", "wellness", "longevity"],
    "wellness": ["mental-health", "sleep", "longevity"],
    "longevity": ["wellness", "nutrition", "fitness"],
    "health-apps": ["food-scanning", "fitness", "meal-planning"],
    "weight-management": ["nutrition", "fitness", "fasting", "meal-planning"],
    "meal-planning": ["nutrition", "weight-management", "food-scanning"],
}


# ── GCS helpers ───────────────────────────────────────────────────────────────

def _gcs_upload(local_path: str, gcs_path: str) -> bool:
    """Upload a file to GCS using gcloud storage."""
    gcloud = r"C:\Users\Kortn\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    try:
        subprocess.run(
            [gcloud, "storage", "cp", local_path, gcs_path],
            check=True, capture_output=True, text=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error("GCS upload failed: %s → %s: %s", local_path, gcs_path, e.stderr)
        return False


def _fetch_post(slug: str) -> Optional[Dict[str, Any]]:
    """Fetch a single post JSON from public GCS."""
    url = f"{GCS_PUBLIC}/{slug}.json"
    try:
        r = httpx.get(url, timeout=15)
        if r.status_code == 200:
            return r.json()
        logger.warning("Failed to fetch %s: %d", slug, r.status_code)
        return None
    except Exception as e:
        logger.warning("Error fetching %s: %s", slug, e)
        return None


def _fetch_index() -> List[Dict[str, Any]]:
    """Fetch the blog posts index from GCS."""
    url = f"{GCS_PUBLIC}/index.json"
    r = httpx.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("posts", [])


# ── Internal linking logic ────────────────────────────────────────────────────

def find_related_posts(
    current_slug: str,
    current_topic: str,
    all_posts: List[Dict[str, Any]],
    count: int = 5,
) -> List[Dict[str, Any]]:
    """Find related posts for internal linking.

    Priority:
      1. Same topic_slug (most relevant)
      2. Adjacent topics (defined in TOPIC_ADJACENCY)
      3. Any remaining posts (least relevant)
    """
    same_topic = []
    adjacent_topic = []
    other = []

    adjacent_topics = set(TOPIC_ADJACENCY.get(current_topic, []))

    for p in all_posts:
        if p["slug"] == current_slug:
            continue
        topic = p.get("topic_slug", "")
        if topic == current_topic:
            same_topic.append(p)
        elif topic in adjacent_topics:
            adjacent_topic.append(p)
        else:
            other.append(p)

    # Pick from same topic first, then adjacent, then other
    result = []
    for pool in [same_topic, adjacent_topic, other]:
        for p in pool:
            if len(result) >= count:
                break
            result.append(p)
        if len(result) >= count:
            break

    return result[:count]


def _build_related_section(related: List[Dict[str, Any]]) -> str:
    """Build a 'Keep Reading' section with internal links."""
    if not related:
        return ""

    lines = ["\n\n---\n\n### Keep Reading\n"]
    for p in related[:5]:
        route_path = p.get("route_path", f"/blog/{p['slug']}")
        title = p.get("title", p["slug"].replace("-", " ").title())
        lines.append(f"- [{title}]({route_path})")

    return "\n".join(lines) + "\n"


def _inject_contextual_link(body: str, related: List[Dict[str, Any]], current_topic: str) -> str:
    """Inject 1-2 contextual inline links into the body text.

    Strategy: Find natural insertion points (end of sections) and add
    a parenthetical or sentence linking to a related post.
    """
    if not related:
        return body

    # Split body into sections by ## headers
    sections = re.split(r'(^## .+$)', body, flags=re.MULTILINE)

    links_added = 0
    max_links = min(2, len(related))
    link_idx = 0

    # Find good sections to inject links
    _GOOD_SECTIONS = {"what you can do", "why this matters", "the bottom line",
                      "practical tips", "how to", "what to know",
                      "quick answer", "what the research says"}

    result_sections = []
    for i, section in enumerate(sections):
        result_sections.append(section)
        # Skip headers themselves
        if section.startswith("## "):
            continue
        if links_added >= max_links:
            continue

        # Check if previous element was a good section header
        if i > 0:
            prev_header = sections[i - 1].lower().strip().replace("## ", "")
            if any(good in prev_header for good in _GOOD_SECTIONS):
                if link_idx < len(related):
                    p = related[link_idx]
                    route_path = p.get("route_path", f"/blog/{p['slug']}")
                    title = p.get("title", p["slug"].replace("-", " ").title())
                    # Add link at end of section
                    cta = f"\n\n> **Related:** [{title}]({route_path})\n"
                    result_sections[-1] = result_sections[-1].rstrip() + cta
                    links_added += 1
                    link_idx += 1

    return "".join(result_sections)


def _has_internal_links(body: str) -> bool:
    """Check if post body already has internal links."""
    # Look for markdown links to internal routes
    internal_link_pattern = r'\[.+?\]\(/(insights|fitness|wellness|trends|comparison|blog)/'
    return bool(re.search(internal_link_pattern, body))


def _has_keep_reading(body: str) -> bool:
    """Check if post already has a Keep Reading section."""
    return "### Keep Reading" in body or "## Keep Reading" in body or "## Related Reading" in body


def inject_internal_links(
    post: Dict[str, Any],
    all_posts: List[Dict[str, Any]],
) -> Tuple[Dict[str, Any], bool]:
    """Inject internal links into a post's body. Returns (modified_post, changed)."""
    body = post.get("body", "")
    slug = post.get("slug", "")
    topic = post.get("topic_slug", "nutrition")

    if not body:
        return post, False

    # Skip if already has internal links AND keep reading section
    if _has_internal_links(body) and _has_keep_reading(body):
        logger.info("  Already has internal links — skipping %s", slug)
        return post, False

    # Find related posts
    related = find_related_posts(slug, topic, all_posts, count=5)
    if not related:
        logger.warning("  No related posts found for %s", slug)
        return post, False

    changed = False

    # 1. Inject contextual inline links (if not already present)
    if not _has_internal_links(body):
        body = _inject_contextual_link(body, related, topic)
        changed = True

    # 2. Add "Keep Reading" section (if not already present)
    if not _has_keep_reading(body):
        # Insert before FAQ section if it exists
        faq_match = re.search(r'\n## (?:FAQ|Frequently Asked Questions)\b', body, re.IGNORECASE)
        if faq_match:
            keep_reading = _build_related_section(related)
            body = body[:faq_match.start()] + keep_reading + body[faq_match.start():]
        else:
            # Append at the end
            body = body.rstrip() + _build_related_section(related)
        changed = True

    if changed:
        post["body"] = body

    # 3. Update related_posts array with correct route_paths
    post["related_posts"] = [
        {
            "slug": p["slug"],
            "title": p.get("title", p["slug"].replace("-", " ").title()),
            "route_path": p.get("route_path", f"/blog/{p['slug']}"),
        }
        for p in related[:5]
    ]

    return post, changed


def upload_post(post: Dict[str, Any]) -> bool:
    """Upload a modified post to GCS."""
    slug = post["slug"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(post, f, indent=2, default=str)
        tmp_path = f.name

    success = _gcs_upload(tmp_path, f"{GCS_BUCKET}/{slug}.json")
    Path(tmp_path).unlink(missing_ok=True)
    return success


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Backfill internal links into wihy.ai blog posts")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without uploading")
    parser.add_argument("--slug", help="Process a single post by slug")
    parser.add_argument("--limit", type=int, help="Process first N posts only")
    parser.add_argument("--force", action="store_true", help="Re-inject even if post already has links")
    args = parser.parse_args()

    # 1. Fetch index
    logger.info("Fetching blog index...")
    index_posts = _fetch_index()
    logger.info("Found %d posts in index", len(index_posts))

    if not index_posts:
        logger.error("No posts found in index!")
        return

    # 2. Filter
    if args.slug:
        slugs = [args.slug]
    else:
        slugs = [p["slug"] for p in index_posts]

    if args.limit:
        slugs = slugs[:args.limit]

    logger.info("Processing %d posts...", len(slugs))

    # 3. Process each post
    updated = 0
    skipped = 0
    errors = 0

    for i, slug in enumerate(slugs, 1):
        logger.info("[%d/%d] %s", i, len(slugs), slug)

        # Fetch full post
        post = _fetch_post(slug)
        if not post:
            errors += 1
            continue

        # Inject links
        modified, changed = inject_internal_links(post, index_posts)

        if not changed and not args.force:
            skipped += 1
            continue

        if args.dry_run:
            # Show what would change
            body = modified.get("body", "")
            related = modified.get("related_posts", [])
            print(f"\n  Would add links to {slug}:")
            for rp in related:
                print(f"    → {rp.get('title', '')} ({rp.get('route_path', '')})")

            # Show inline links
            inline_links = re.findall(r'> \*\*Related:\*\* \[(.+?)\]\((.+?)\)', body)
            for text, href in inline_links:
                print(f"    ↳ Inline: [{text}]({href})")

            updated += 1
            continue

        # Upload
        if upload_post(modified):
            updated += 1
            logger.info("  ✓ Updated with %d related links", len(modified.get("related_posts", [])))
        else:
            errors += 1
            logger.error("  ✗ Upload failed")

    # Summary
    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Done:")
    print(f"  Updated: {updated}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors:  {errors}")

    # 4. Rebuild index with updated related_posts (if not dry run)
    if not args.dry_run and updated > 0:
        logger.info("Rebuilding index.json is not needed — individual posts updated in place")
        logger.info("Related posts are stored per-post, not in the index")


if __name__ == "__main__":
    main()
