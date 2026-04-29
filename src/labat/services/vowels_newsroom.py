"""
vowels_newsroom.py

Vowels newsroom helpers for RSS, Google News sitemap, and publication blueprint.
"""

from __future__ import annotations

import html
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from google.cloud import storage

from src.labat.brands import BRAND_DOMAINS
from src.labat.services.blog_writer import BLOG_INDEX_FILE, GCS_BUCKETS

logger = logging.getLogger("vowels.newsroom")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: str) -> datetime:
    if not value:
        return _utc_now()
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return _utc_now()


def _article_url(base_url: str, post: Dict[str, Any]) -> str:
    route_path = (post.get("route_path") or "").strip()
    if not route_path:
        route_base = (post.get("route_base") or "/blog").strip().rstrip("/")
        slug = (post.get("slug") or "").strip()
        route_path = f"{route_base}/{slug}" if slug else ""
    if not route_path.startswith("/"):
        route_path = f"/{route_path}"
    return f"{base_url}{route_path}"


def get_vowels_base_url() -> str:
    domain = BRAND_DOMAINS.get("vowels", "vowels.org")
    return f"https://{domain}"


def load_vowels_posts(limit: int = 200) -> List[Dict[str, Any]]:
    bucket_name = GCS_BUCKETS.get("vowels") or GCS_BUCKETS.get("wihy")
    if not bucket_name:
        return []

    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(BLOG_INDEX_FILE)
        if not blob.exists():
            return []
        payload = json.loads(blob.download_as_text())
        posts = payload.get("posts", []) if isinstance(payload, dict) else []
        vowels_posts = [p for p in posts if (p.get("brand") or "").strip().lower() == "vowels"]
        vowels_posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)
        return vowels_posts[:limit]
    except Exception as e:
        logger.warning("Failed loading Vowels index: %s", e)
        return []


def render_rss_xml(posts: List[Dict[str, Any]]) -> str:
    base_url = get_vowels_base_url()
    now_rfc = _utc_now().strftime("%a, %d %b %Y %H:%M:%S GMT")

    items: List[str] = []
    for post in posts:
        title = html.escape(str(post.get("title", "Untitled")))
        description = html.escape(str(post.get("meta_description", "")))
        link = html.escape(_article_url(base_url, post))
        pub_date = _parse_dt(str(post.get("created_at", ""))).strftime("%a, %d %b %Y %H:%M:%S GMT")
        guid = html.escape(str(post.get("slug", link)))

        items.append(
            "\n".join(
                [
                    "    <item>",
                    f"      <title>{title}</title>",
                    f"      <link>{link}</link>",
                    f"      <guid>{guid}</guid>",
                    f"      <pubDate>{pub_date}</pubDate>",
                    f"      <description>{description}</description>",
                    "    </item>",
                ]
            )
        )

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<rss version="2.0">',
            "  <channel>",
            "    <title>Vowels.org Newsroom</title>",
            f"    <link>{base_url}</link>",
            "    <description>Evidence-based nutrition journalism powered by data.</description>",
            "    <language>en-us</language>",
            f"    <lastBuildDate>{now_rfc}</lastBuildDate>",
            *items,
            "  </channel>",
            "</rss>",
        ]
    )


def render_news_sitemap_xml(posts: List[Dict[str, Any]]) -> str:
    base_url = get_vowels_base_url()
    recent_cutoff = _utc_now() - timedelta(days=2)

    entries: List[str] = []
    for post in posts:
        published = _parse_dt(str(post.get("created_at", "")))
        if published < recent_cutoff:
            continue

        title = html.escape(str(post.get("title", "Untitled")))
        loc = html.escape(_article_url(base_url, post))
        publication_date = published.strftime("%Y-%m-%dT%H:%M:%SZ")
        keywords = html.escape(str(post.get("topic_slug", "nutrition")))

        entries.append(
            "\n".join(
                [
                    "  <url>",
                    f"    <loc>{loc}</loc>",
                    "    <news:news>",
                    "      <news:publication>",
                    "        <news:name>Vowels.org</news:name>",
                    "        <news:language>en</news:language>",
                    "      </news:publication>",
                    f"      <news:publication_date>{publication_date}</news:publication_date>",
                    f"      <news:title>{title}</news:title>",
                    f"      <news:keywords>{keywords}</news:keywords>",
                    "    </news:news>",
                    "  </url>",
                ]
            )
        )

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            '        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
            *entries,
            "</urlset>",
        ]
    )


def get_newsroom_blueprint() -> Dict[str, Any]:
    return {
        "positioning": {
            "type": "nutrition-newsroom",
            "principle": "Content is powered by data, not opinions.",
            "master_editor": "Kortney (Otaku)",
        },
        "content_types": [
            "nutrition-education",
            "news-update",
            "data-insight",
            "opinion-editorial",
            "sponsored",
        ],
        "roles": ["editor-in-chief", "writer", "data-analyst", "reviewer"],
        "autonomous_mode": {
            "enabled": True,
            "fact_first": True,
            "human_override_supported": True,
        },
        "ads": {
            "phase_1": ["adsense-auto", "adsense-display", "adsense-in-article"],
            "phase_2": ["google-ad-manager", "direct-sales", "inventory-controls"],
            "placements": {
                "homepage": ["leaderboard", "in-feed", "sidebar"],
                "article": ["top-banner", "mid-article", "bottom-sponsored", "sticky-mobile"],
            },
        },
        "distribution": {
            "news_platforms": ["google-news", "microsoft-start"],
            "rss_platforms": ["feedly", "flipboard", "inoreader"],
            "social": ["instagram", "facebook", "linkedin", "x"],
        },
        "seo": ["article-schema", "sitemap", "news-sitemap", "rss-feed", "internal-linking"],
        "analytics": ["ga-pageviews", "time-on-page", "cta-ctr", "scroll-depth"],
        "legal": ["privacy", "terms", "editorial-policy", "health-disclaimer"],
        "performance": {"max_page_load_seconds": 2, "mobile_optimized": True},
    }
