"""
content/blog_publisher.py — Publishes Alex page drafts to GCS as blog posts.

Converts page_store format → CG BlogPost JSON → uploads to
gs://cg-web-assets/blog/posts/{slug}.json and updates index.json.

Usage:
    python -m src.content.blog_publisher                     # publish all drafts
    python -m src.content.blog_publisher --slug my-article   # publish one
    python -m src.content.blog_publisher --brand wihy        # publish for wihy
    python -m src.content.blog_publisher --generate          # generate + publish Big 8
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("wihy.blog_publisher")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


def _route_base_for_post(post: Dict[str, Any]) -> str:
    route_base = str(post.get("route_base", "")).strip()
    if route_base:
        return route_base if route_base.startswith("/") else f"/{route_base}"
    return "/blog"


def _route_path_for_post(post: Dict[str, Any]) -> str:
    route_path = str(post.get("route_path", "")).strip()
    if route_path:
        return route_path if route_path.startswith("/") else f"/{route_path}"
    return f"{_route_base_for_post(post).rstrip('/')}/{post.get('slug', '').strip('/')}"

# ── GCS config per brand ───────────────────────────────────────────────────────

BRAND_GCS = {
    "communitygroceries": {
        "bucket": "gs://cg-web-assets/blog/posts",
        "domain": "https://communitygroceries.com",
        "author": "Kortney",
        "image_bucket": "gs://cg-web-assets/images/blog",
        "image_url_prefix": "https://storage.googleapis.com/cg-web-assets/images/blog",
    },
    "wihy": {
        "bucket": "gs://wihy-web-assets/blog/posts",
        "domain": "https://wihy.ai",
        "author": "Kortney",
        "image_bucket": "gs://wihy-web-assets/images/blog",
        "image_url_prefix": "https://storage.googleapis.com/wihy-web-assets/images/blog",
    },
}

SHANIA_GRAPHICS_URL = os.getenv(
    "SHANIA_GRAPHICS_URL",
    "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app",
)

# ── Topic mapping (Alex page_type → CG topic_slug) ────────────────────────────

PAGE_TYPE_TO_TOPIC = {
    "is_it_healthy": "nutrition",
    "topic": "nutrition",
    "ingredient": "nutrition",
    "alternative": "nutrition",
    "fitness": "fitness",
    "exercise": "fitness",
    "supplement": "supplements",
    "fasting": "fasting",
    "alcohol": "alcohol-and-health",
    "sugar": "sugar-and-blood-health",
    "processed": "processed-foods",
    "protein": "protein-and-muscle",
    "hydration": "hydration",
}


def _infer_topic(page: Dict[str, Any]) -> str:
    """Infer CG topic_slug from Alex page data."""
    # Direct topic if present
    if page.get("topic_slug"):
        return page["topic_slug"]
    if page.get("topic"):
        return page["topic"]

    page_type = page.get("page_type", "topic")
    if page_type in PAGE_TYPE_TO_TOPIC:
        return PAGE_TYPE_TO_TOPIC[page_type]

    # Infer from keywords/title
    text = f"{page.get('title', '')} {page.get('source_keyword', '')}".lower()
    if any(w in text for w in ("exercise", "workout", "fitness", "muscle", "training")):
        return "fitness"
    if any(w in text for w in ("supplement", "vitamin", "mineral", "magnesium")):
        return "supplements"
    if any(w in text for w in ("fasting", "intermittent")):
        return "fasting"
    if any(w in text for w in ("sugar", "glucose", "insulin", "blood sugar")):
        return "sugar-and-blood-health"
    if any(w in text for w in ("alcohol", "wine", "beer", "drinking")):
        return "alcohol-and-health"
    if any(w in text for w in ("processed", "ultra-processed", "seed oil")):
        return "processed-foods"
    if any(w in text for w in ("protein", "whey", "collagen")):
        return "protein-and-muscle"

    return "nutrition"


def _infer_tags(page: Dict[str, Any]) -> List[str]:
    """Generate tags from page content."""
    tags = []
    text = f"{page.get('title', '')} {page.get('source_keyword', '')} {page.get('meta_description', '')}".lower()

    tag_keywords = {
        "weight-loss": ["weight loss", "lose weight", "fat loss"],
        "heart-health": ["heart", "cardiovascular", "cholesterol", "blood pressure"],
        "longevity": ["longevity", "lifespan", "aging", "anti-aging"],
        "mental-health": ["depression", "anxiety", "mental health", "mood"],
        "gut-health": ["gut", "microbiome", "probiotic", "digestive"],
        "cancer-prevention": ["cancer", "carcinogen", "tumor"],
        "diabetes": ["diabetes", "insulin", "blood sugar", "a1c"],
        "inflammation": ["inflammation", "inflammatory", "anti-inflammatory"],
        "sleep": ["sleep", "insomnia", "circadian"],
        "muscle-building": ["muscle", "strength", "resistance training"],
        "research-backed": ["study", "research", "evidence", "clinical"],
        "beginner-friendly": ["guide", "basics", "101", "beginner"],
    }

    for tag, kws in tag_keywords.items():
        if any(kw in text for kw in kws):
            tags.append(tag)

    # Always add research-backed for health content
    if not tags or "research-backed" not in tags:
        tags.append("research-backed")

    return tags[:5]


def _resolve_hero_image(brand: str, slug: str, provided_value: Any, brand_cfg: Dict[str, str]) -> str:
    hero_image = str(provided_value or "").strip()
    if hero_image and hero_image.lower() not in {"none", "null"}:
        return hero_image
    return f"{brand_cfg['image_url_prefix']}/{slug}-hero.jpg"


async def generate_and_upload_hero_image(
    slug: str, topic: str, brand: str = "communitygroceries",
) -> Optional[str]:
    """Call Shania Graphics to generate a real hero image, upload to GCS, return URL."""
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    try:
        async with httpx.AsyncClient(timeout=60.0) as http:
            resp = await http.post(
                f"{SHANIA_GRAPHICS_URL}/generate-hero-image",
                json={"topic": topic, "brand": brand, "slug": slug},
            )
            if resp.status_code != 200:
                logger.error("Shania hero image failed (%d) for %s: %s", resp.status_code, slug, resp.text[:200])
                return None

            data = resp.json()
            image_bytes: Optional[bytes] = None

            if data.get("url"):
                img_resp = await http.get(data["url"], timeout=30)
                if img_resp.status_code == 200:
                    image_bytes = img_resp.content

            if not image_bytes and data.get("imageBase64"):
                image_bytes = base64.b64decode(data["imageBase64"])

            if not image_bytes:
                logger.error("Shania returned no image content for %s", slug)
                return None

            # Upload to GCS
            image_gcs = f"{brand_cfg['image_bucket']}/{slug}-hero.jpg"
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            ok = _gcs_upload(tmp_path, image_gcs)
            Path(tmp_path).unlink(missing_ok=True)

            if ok:
                url = f"{brand_cfg['image_url_prefix']}/{slug}-hero.jpg"
                logger.info("Hero image uploaded for '%s' → %s (%d bytes)", slug, url, len(image_bytes))
                return url
            return None
    except Exception as e:
        logger.error("Hero image generation failed for %s: %s", slug, e)
        return None


def alex_to_blog_post(page: Dict[str, Any], brand: str = "communitygroceries") -> Dict[str, Any]:
    """Normalize an Alex page_store entry to the CG BlogPost JSON format.

    Alex now outputs the correct fields (body, seo_keywords, faq_items,
    topic_slug, citations, key_takeaways, related_posts). This function
    fills in any missing defaults and ensures field consistency.
    """
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    slug = page.get("slug", "").strip().lower()

    # Body — might still be "content" in legacy drafts
    body = page.get("body", "") or page.get("content", "") or ""

    # Keywords — handle legacy comma-separated string
    keywords = page.get("seo_keywords", [])
    if not keywords and page.get("keywords"):
        kw_raw = page["keywords"]
        if isinstance(kw_raw, str):
            keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]
        elif isinstance(kw_raw, list):
            keywords = kw_raw

    # FAQ — handle legacy {q, a} format
    faq_raw = page.get("faq_items", []) or page.get("faq", [])
    faq_items = []
    for f in faq_raw:
        faq_items.append({
            "question": f.get("question", "") or f.get("q", ""),
            "answer": f.get("answer", "") or f.get("a", ""),
        })

    # Related posts — handle legacy string array
    related_raw = page.get("related_posts", []) or page.get("related_links", [])
    related_posts = []
    for r in related_raw:
        if isinstance(r, str):
            related_posts.append({"slug": r, "title": r.replace("-", " ").title()})
        elif isinstance(r, dict):
            related_posts.append({
                "slug": r.get("slug", ""),
                "title": r.get("title", r.get("slug", "").replace("-", " ").title()),
            })

    # Word count
    word_count = page.get("word_count", 0)
    if not word_count and body:
        word_count = len(body.split())

    # Hero image placeholder
    hero_image = _resolve_hero_image(brand, slug, page.get("hero_image", ""), brand_cfg)

    return {
        "slug": slug,
        "title": page.get("title", slug.replace("-", " ").title()),
        "route_base": page.get("route_base", "/blog"),
        "route_path": page.get("route_path", f"{str(page.get('route_base', '/blog')).rstrip('/')}/{slug}"),
        "body": body,
        "meta_description": page.get("meta_description", ""),
        "topic_slug": page.get("topic_slug", "") or _infer_topic(page),
        "seo_keywords": keywords,
        "citations": page.get("citations", []),
        "author": page.get("author", brand_cfg["author"]),
        "brand": page.get("brand", brand),
        "created_at": page.get("created_at", datetime.utcnow().isoformat()),
        "updated_at": datetime.utcnow().isoformat(),
        "word_count": word_count,
        "hero_image": hero_image,
        "faq_items": faq_items,
        "key_takeaways": page.get("key_takeaways", []),
        "related_posts": related_posts,
    }


def _gcs_upload(local_path: str, gcs_path: str) -> bool:
    """Upload a file to GCS using gcloud CLI."""
    try:
        result = subprocess.run(
            f'gcloud storage cp "{local_path}" "{gcs_path}"',
            capture_output=True, text=True, timeout=30, shell=True,
        )
        if result.returncode == 0:
            logger.info("Uploaded → %s", gcs_path)
            return True
        else:
            logger.error("Upload failed: %s", result.stderr.strip())
            return False
    except Exception as e:
        logger.error("Upload exception: %s", e)
        return False


def _gcs_read(gcs_path: str) -> Optional[str]:
    """Read a file from GCS."""
    try:
        result = subprocess.run(
            f'gcloud storage cat "{gcs_path}"',
            capture_output=True, text=True, timeout=45, shell=True,
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception:
        return None


def _gcs_list_json(bucket: str) -> List[str]:
    """List JSON objects under the bucket path (gs://.../blog/posts)."""
    try:
        result = subprocess.run(
            f'gcloud storage ls "{bucket}/*.json"',
            capture_output=True,
            text=True,
            timeout=45,
            shell=True,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _index_entry_from_post(post: Dict[str, Any], brand: str) -> Dict[str, Any]:
    """Create lightweight index entry from a full post payload."""
    return {
        "slug": post.get("slug", ""),
        "route_base": _route_base_for_post(post),
        "route_path": _route_path_for_post(post),
        "title": post.get("title", ""),
        "meta_description": post.get("meta_description", ""),
        "topic_slug": post.get("topic_slug", "nutrition"),
        "author": post.get("author", "Kortney"),
        "created_at": post.get("created_at", datetime.utcnow().isoformat()),
        "hero_image": post.get("hero_image", ""),
        "word_count": post.get("word_count", 0),
        "brand": brand,
        "tags": post.get("tags", _infer_tags(post)),
    }


def rebuild_index_from_bucket(brand: str = "communitygroceries") -> bool:
    """Rebuild index.json from all post JSON objects in the configured bucket."""
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    bucket = brand_cfg["bucket"]
    object_paths = _gcs_list_json(bucket)

    if not object_paths:
        logger.error("No JSON objects found under %s", bucket)
        return False

    post_paths = [p for p in object_paths if not p.endswith("/index.json")]
    posts: List[Dict[str, Any]] = []

    for path in post_paths:
        raw = _gcs_read(path)
        if not raw:
            logger.warning("Skipping unreadable object: %s", path)
            continue
        try:
            post = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Skipping invalid JSON object: %s", path)
            continue

        slug = str(post.get("slug", "")).strip()
        if not slug:
            logger.warning("Skipping object without slug: %s", path)
            continue
        posts.append(_index_entry_from_post(post, brand))

    posts.sort(key=lambda p: str(p.get("created_at", "")), reverse=True)

    index_data = {
        "posts": posts,
        "count": len(posts),
        "updated_at": datetime.utcnow().isoformat(),
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, default=str)
        tmp_path = f.name

    success = _gcs_upload(tmp_path, f"{bucket}/index.json")
    Path(tmp_path).unlink(missing_ok=True)
    if success:
        logger.info("Rebuilt index for %s with %d posts", brand, len(posts))
    return success


def publish_post(post: Dict[str, Any], brand: str = "communitygroceries") -> bool:
    """Publish a single blog post JSON to GCS."""
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    bucket = brand_cfg["bucket"]
    slug = post["slug"]

    # Write post JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(post, f, indent=2, default=str)
        tmp_path = f.name

    success = _gcs_upload(tmp_path, f"{bucket}/{slug}.json")
    Path(tmp_path).unlink(missing_ok=True)

    if not success:
        return False

    # Update index.json
    index_raw = _gcs_read(f"{bucket}/index.json")
    if index_raw:
        try:
            index_data = json.loads(index_raw)
        except json.JSONDecodeError:
            index_data = {"posts": [], "count": 0}
    else:
        index_data = {"posts": [], "count": 0}

    posts_list = index_data.get("posts", [])

    # Build index entry (lightweight — no full body)
    index_entry = _index_entry_from_post(post, brand)

    # Upsert: replace existing entry with same slug
    posts_list = [p for p in posts_list if p.get("slug") != slug]
    posts_list.insert(0, index_entry)  # newest first

    index_data["posts"] = posts_list
    index_data["count"] = len(posts_list)
    index_data["updated_at"] = datetime.utcnow().isoformat()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, default=str)
        tmp_path = f.name

    success = _gcs_upload(tmp_path, f"{bucket}/index.json")
    Path(tmp_path).unlink(missing_ok=True)

    return success


def publish_from_page_store(
    brand: str = "communitygroceries",
    slug: Optional[str] = None,
    status_filter: str = "draft",
) -> Dict[str, Any]:
    """Publish page_store entries to GCS.

    Args:
        brand: Target brand ("communitygroceries" or "wihy")
        slug: Specific slug to publish (None = all matching)
        status_filter: Only publish pages with this status

    Returns:
        {"published": [...slugs], "errors": [...]}
    """
    from src.services.page_store import list_pages, get_page, refresh_page

    result = {"published": [], "errors": []}

    if slug:
        pages = [get_page(slug)]
        pages = [p for p in pages if p]
    else:
        pages = list_pages(status=status_filter, limit=100)

    if not pages:
        logger.info("No pages to publish (status=%s)", status_filter)
        return result

    for page in pages:
        page_slug = page.get("slug", "")
        try:
            blog_post = alex_to_blog_post(page, brand=brand)
            if publish_post(blog_post, brand=brand):
                result["published"].append(page_slug)
                # Update status in page_store
                refresh_page(page_slug, {"status": "published", "published_at": datetime.utcnow().isoformat()})
                logger.info("✓ Published: %s", page_slug)
            else:
                result["errors"].append(page_slug)
                logger.error("✗ Failed: %s", page_slug)
        except Exception as e:
            result["errors"].append(page_slug)
            logger.error("✗ Error publishing %s: %s", page_slug, e)

    logger.info(
        "Done: %d published, %d errors",
        len(result["published"]),
        len(result["errors"]),
    )
    return result


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Publish Alex page drafts to GCS blog")
    parser.add_argument("--brand", default="communitygroceries", choices=["communitygroceries", "wihy"])
    parser.add_argument("--slug", help="Publish a specific page by slug")
    parser.add_argument("--status", default="draft", help="Status filter (default: draft)")
    parser.add_argument("--generate", action="store_true", help="Generate Big 8 pages first")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild index.json from all published post JSON files")
    parser.add_argument("--dry-run", action="store_true", help="Convert but don't upload")
    args = parser.parse_args()

    if args.rebuild_index:
        ok = rebuild_index_from_bucket(brand=args.brand)
        if ok:
            print("\n✅ Index rebuild complete")
            return
        print("\n❌ Index rebuild failed")
        sys.exit(1)

    if args.generate:
        logger.info("Generating Big 8 health pages first...")
        from src.content.seed_health_pages import seed_big_8
        asyncio.run(seed_big_8(brand=args.brand))

    if args.dry_run:
        from src.services.page_store import list_pages, get_page
        if args.slug:
            pages = [get_page(args.slug)]
            pages = [p for p in pages if p]
        else:
            pages = list_pages(status=args.status, limit=100)

        for page in pages:
            blog_post = alex_to_blog_post(page, brand=args.brand)
            print(f"\n{'='*60}")
            print(f"SLUG: {blog_post['slug']}")
            print(f"TITLE: {blog_post['title']}")
            print(f"TOPIC: {blog_post['topic_slug']}")
            print(f"KEYWORDS: {blog_post['seo_keywords'][:5]}")
            print(f"WORD COUNT: {blog_post['word_count']}")
            print(f"FAQ COUNT: {len(blog_post['faq_items'])}")
            print(f"BODY PREVIEW: {blog_post['body'][:200]}...")
        return

    result = publish_from_page_store(
        brand=args.brand,
        slug=args.slug,
        status_filter=args.status,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
