"""
labat/services/content_insights_service.py — Content & blog analytics.

Aggregates data from:
- GCS blog index (published articles)
- Keyword store (SEO pipeline)
- Editorial queue (pending articles)

Used by /api/labat/insights/blog, /blog/performance, /content, /articles.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from google.cloud import storage

from src.labat.services.keyword_store import list_keywords
from src.labat.services.blog_writer import (
    get_queue_status,
    GCS_BUCKETS,
    BLOG_INDEX_FILE,
    TOPIC_TAXONOMY,
    EDITORIAL_QUEUE,
)

logger = logging.getLogger("labat.content_insights")

_gcs_client: Optional[storage.Client] = None


def _get_gcs_client() -> storage.Client:
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = storage.Client()
    return _gcs_client


def _parse_period(period: str) -> timedelta:
    """Parse period string like '7d', '30d', '90d' into timedelta."""
    period = period.strip().lower()
    if period.endswith("d"):
        try:
            return timedelta(days=int(period[:-1]))
        except ValueError:
            pass
    return timedelta(days=30)


def _load_blog_index(brand: str) -> List[Dict[str, Any]]:
    """Load the blog index from GCS for the given brand."""
    bucket_name = GCS_BUCKETS.get(brand, GCS_BUCKETS.get("wihy", "wihy-web-assets"))
    try:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(BLOG_INDEX_FILE)
        if not blob.exists():
            logger.warning("Blog index not found: gs://%s/%s", bucket_name, BLOG_INDEX_FILE)
            return []
        content = blob.download_as_text()
        data = json.loads(content)
        return data.get("posts", [])
    except Exception as e:
        logger.error("Failed to load blog index for %s: %s", brand, e)
        return []


def _load_article(brand: str, slug: str) -> Optional[Dict[str, Any]]:
    """Load a single article JSON from GCS."""
    bucket_name = GCS_BUCKETS.get(brand, GCS_BUCKETS.get("wihy", "wihy-web-assets"))
    try:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"blog/posts/{slug}.json")
        if not blob.exists():
            return None
        return json.loads(blob.download_as_text())
    except Exception as e:
        logger.warning("Failed to load article %s/%s: %s", brand, slug, e)
        return None


def _filter_by_period(
    articles: List[Dict[str, Any]], period: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (all_articles, articles_in_period)."""
    delta = _parse_period(period)
    cutoff = datetime.now(timezone.utc) - delta

    in_period = []
    for article in articles:
        created = article.get("created_at", "")
        if not created:
            continue
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                in_period.append(article)
        except (ValueError, TypeError):
            continue

    return articles, in_period


# ── Public API ────────────────────────────────────────────────────────────────


async def get_blog_performance(brand: str, period: str) -> Dict[str, Any]:
    """High-level blog performance snapshot."""
    articles = _load_blog_index(brand)
    all_articles, recent = _filter_by_period(articles, period)

    total_words = sum(a.get("word_count", 0) for a in all_articles)
    recent_words = sum(a.get("word_count", 0) for a in recent)
    avg_words = total_words // len(all_articles) if all_articles else 0

    latest = all_articles[0] if all_articles else None

    queue = get_queue_status()
    brand_queue_count = queue.get(brand, 0)

    keywords = list_keywords(brand=brand)
    published_kw = [k for k in keywords if k.get("status") == "published"]

    return {
        "brand": brand,
        "period": period,
        "total_articles": len(all_articles),
        "articles_in_period": len(recent),
        "total_word_count": total_words,
        "period_word_count": recent_words,
        "avg_word_count": avg_words,
        "latest_article": {
            "slug": latest.get("slug", ""),
            "title": latest.get("title", ""),
            "created_at": latest.get("created_at", ""),
            "word_count": latest.get("word_count", 0),
        } if latest else None,
        "editorial_queue_size": brand_queue_count,
        "keywords_targeted": len(published_kw),
    }


async def get_blog_overview(
    brand: str, period: str, page_type: Optional[str] = None
) -> Dict[str, Any]:
    """Blog listing with period filter and optional page_type filter."""
    articles = _load_blog_index(brand)
    all_articles, recent = _filter_by_period(articles, period)

    # Filter by page_type if provided
    if page_type:
        recent = [a for a in recent if a.get("page_type", "topic") == page_type]
        all_articles = [a for a in all_articles if a.get("page_type", "topic") == page_type]

    return {
        "brand": brand,
        "period": period,
        "page_type": page_type,
        "articles": [
            {
                "slug": a.get("slug", ""),
                "title": a.get("title", ""),
                "author": a.get("author", "Kortney"),
                "created_at": a.get("created_at", ""),
                "word_count": a.get("word_count", 0),
                "hero_image": a.get("hero_image", ""),
                "meta_description": a.get("meta_description", ""),
                "page_type": a.get("page_type", "topic"),
                "route_base": a.get("route_base", "/blog"),
                "route_path": a.get("route_path", "") or f"{a.get('route_base', '/blog').rstrip('/')}/{a.get('slug', '')}",
                "topic_slug": a.get("topic_slug", ""),
                "tags": a.get("tags", []),
            }
            for a in recent
        ],
        "total": len(all_articles),
        "in_period": len(recent),
    }


async def get_content_insights(brand: str, period: str) -> Dict[str, Any]:
    """Content pipeline status: keywords + editorial queue."""
    keywords = list_keywords(brand=brand)

    kw_by_status: Dict[str, int] = {}
    for kw in keywords:
        st = kw.get("status", "unknown")
        kw_by_status[st] = kw_by_status.get(st, 0) + 1

    queue = get_queue_status()
    articles = _load_blog_index(brand)
    _, recent = _filter_by_period(articles, period)

    return {
        "brand": brand,
        "period": period,
        "keywords": {
            "total": len(keywords),
            "by_status": kw_by_status,
        },
        "editorial_queue": {
            "total": queue.get("total", 0),
            "wihy": queue.get("wihy", 0),
            "communitygroceries": queue.get("communitygroceries", 0),
        },
        "published": {
            "total": len(articles),
            "in_period": len(recent),
        },
    }


async def get_articles_insights(brand: str, period: str) -> Dict[str, Any]:
    """Detailed per-article data with SEO keywords and citations."""
    articles = _load_blog_index(brand)
    _, recent = _filter_by_period(articles, period)

    detailed = []
    for a in recent:
        slug = a.get("slug", "")
        full = _load_article(brand, slug)
        entry = {
            "slug": slug,
            "title": a.get("title", ""),
            "author": a.get("author", "Kortney"),
            "created_at": a.get("created_at", ""),
            "word_count": a.get("word_count", 0),
            "hero_image": a.get("hero_image", ""),
            "meta_description": a.get("meta_description", ""),
        }
        if full:
            entry["seo_keywords"] = full.get("seo_keywords", [])
            entry["citations_count"] = len(full.get("citations", []))
        detailed.append(entry)

    return {
        "brand": brand,
        "period": period,
        "articles": detailed,
        "total": len(articles),
        "in_period": len(detailed),
    }


async def get_topic_taxonomy(brand: str) -> Dict[str, Any]:
    """Return the full topic taxonomy with article counts per topic."""
    articles = _load_blog_index(brand)

    # Count published articles per topic_slug
    published_by_topic: Dict[str, int] = {}
    for a in articles:
        ts = a.get("topic_slug", "")
        if ts:
            published_by_topic[ts] = published_by_topic.get(ts, 0) + 1

    # Count queued articles per topic_slug
    queued_by_topic: Dict[str, int] = {}
    for e in EDITORIAL_QUEUE:
        if e.get("brand") == brand or brand == "all":
            ts = e.get("topic_slug", "")
            if ts:
                queued_by_topic[ts] = queued_by_topic.get(ts, 0) + 1

    topics = []
    for t in TOPIC_TAXONOMY:
        slug = t["slug"]
        topic_articles = [a for a in articles if a.get("topic_slug") == slug]
        topics.append({
            "slug": slug,
            "label": t["label"],
            "description": t["description"],
            "published_count": published_by_topic.get(slug, 0),
            "queued_count": queued_by_topic.get(slug, 0),
            "articles": [
                {
                    "slug": a.get("slug", ""),
                    "title": a.get("title", ""),
                    "created_at": a.get("created_at", ""),
                    "hero_image": a.get("hero_image", ""),
                    "meta_description": a.get("meta_description", ""),
                }
                for a in topic_articles
            ],
        })

    return {
        "brand": brand,
        "topic_count": len(TOPIC_TAXONOMY),
        "total_published": len(articles),
        "topics": topics,
    }
