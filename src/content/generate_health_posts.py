"""
Generate blog posts for ALL health keywords and publish to GCS.

Reads from data/health_keywords_all.json, generates via OpenAI,
publishes to gs://cg-web-assets/blog/posts/ (and/or wihy bucket).

Usage:
    python -m src.content.generate_health_posts                # generate all
    python -m src.content.generate_health_posts --limit 10     # first 10
    python -m src.content.generate_health_posts --topic fitness # one topic
    python -m src.content.generate_health_posts --slug seed-oils-and-inflammation  # one post
    python -m src.content.generate_health_posts --brand wihy   # for wihy.ai
    python -m src.content.generate_health_posts --dry-run      # preview only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

# Load local .env for CLI runs where shell env vars are not exported.
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.content.blog_publisher import BRAND_GCS, generate_and_upload_hero_image, publish_post

logger = logging.getLogger("wihy.generate_health_posts")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o"
TEMPERATURE = 0.5
DATA_FILE = Path("data/health_keywords_all.json")
PROGRESS_FILE = Path("data/health_posts_progress.json")

# Research API (services.wihy.ai) — fetched ONCE per keyword for real citations
SERVICES_URL = os.getenv("SERVICES_URL", "https://services.wihy.ai").rstrip("/")
CLIENT_ID = os.getenv("WIHY_ML_CLIENT_ID", "wihy_ml_mk1waylw")
CLIENT_SECRET = os.getenv("WIHY_ML_CLIENT_SECRET", "")


def _load_keywords(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path if path else DATA_FILE
    if not target.exists():
        logger.error("Missing %s", target)
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    return data.get("keywords", [])


def _load_progress() -> set:
    """Track which slugs have been generated to allow resuming."""
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    return set()


def _save_progress(completed: set):
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps({"completed": sorted(completed), "count": len(completed)}, indent=2),
        encoding="utf-8",
    )


# ── Research API ───────────────────────────────────────────────────────────────

async def _fetch_research(query: str, http: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch real PubMed citations from services.wihy.ai/api/research/search.

    Returns list of article dicts: {title, journal, year, pmid, pmcid, url}.
    Fails silently — GPT-4o will still write without citations.
    """
    try:
        r = await http.get(
            f"{SERVICES_URL}/api/research/search",
            params={"keyword": query, "limit": 8, "minYear": 2020},
            headers={
                "X-Client-ID": CLIENT_ID,
                "X-Client-Secret": CLIENT_SECRET,
            },
            timeout=12.0,
        )
        if r.status_code != 200:
            logger.warning("Research API %d for '%s'", r.status_code, query[:60])
            return []
        data = r.json()
        articles = data.get("articles", []) or data.get("results", [])
        out = []
        for a in articles:
            links = a.get("links", {})
            out.append({
                "title": a.get("title", ""),
                "journal": a.get("journal", ""),
                "year": a.get("publicationYear") or a.get("year", ""),
                "pmid": a.get("pmid", ""),
                "pmcid": a.get("pmcid", ""),
                "url": links.get("pubmedLink") or links.get("doi") or "",
            })
        logger.info("  Research: %d articles for '%s'", len(out), query[:50])
        return out
    except Exception as e:
        logger.warning("Research fetch failed for '%s': %s", query[:50], e)
        return []


# ── LLM Generation ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Kortney, the health & nutrition expert behind {brand_name}.
Write a comprehensive, evidence-based blog post answering this health question.

Your voice: approachable, knowledgeable, real. You care about the reader — not clinical, not corporate. You cite real research when it exists.

Return ONLY a JSON object with these exact fields:
{{
  "slug": "{slug}",
  "title": "SEO-optimized headline (60 chars max)",
  "body": "Full article in markdown. Use ## for H2, ### for H3, **bold**, lists. 800-1500 words.",
  "meta_description": "Compelling meta description under 155 characters",
  "topic_slug": "{topic_slug}",
  "seo_keywords": ["8-12 long-tail keyword phrases as an array"],
  "faq_items": [
    {{"question": "A real question someone would ask", "answer": "Clear, helpful answer"}},
    ... 3-5 items
  ],
  "key_takeaways": ["3-5 one-sentence takeaways"],
  "citations": [
    {{"title": "Study title", "journal": "Journal name", "year": 2024, "url": "https://pubmed.ncbi.nlm.nih.gov/..."}},
    ... USE the real PubMed studies provided below
  ],
  "related_posts": [
    {{"slug": "related-slug", "title": "Related Article Title"}},
    ... 2-4 related topics from the provided list
  ]
}}

ARTICLE STRUCTURE:
1. Quick Answer (2-3 sentences — give the answer immediately)
2. What the Research Says (cite the REAL studies provided, refer to them by first-author name or journal)
3. Why This Matters (practical implications)
4. What You Can Do (actionable advice)
5. The Bottom Line (1-2 sentence summary)
6. FAQ (3-5 questions)

IMPORTANT:
- Use ONLY the real PubMed studies provided in the RESEARCH EVIDENCE section below.
- Reference studies by author/journal/year in the article body.
- Copy the citation objects exactly into the citations array.
- If no studies are provided, write based on established medical consensus and skip the citations array.
- Include a CTA: "Have a specific question? Ask {brand_name} for a personalized answer → {brand_url}"
- Every claim should be supportable by the research provided."""


async def generate_post(
    keyword: Dict[str, Any],
    brand: str,
    related_slugs: List[str],
    http: httpx.AsyncClient,
) -> Optional[Dict[str, Any]]:
    """Generate a single blog post: fetch research FIRST, then write with GPT-4o."""
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    brand_name = "Community Groceries" if brand == "communitygroceries" else "WIHY"
    brand_url = brand_cfg["domain"]

    slug = keyword["slug"]
    topic = keyword.get("topic_slug", "nutrition")
    question = keyword.get("keyword", slug.replace("-", " "))

    # ── Step 1: Fetch REAL research from services.wihy.ai ────────────────────
    # Use slug-derived query (concise) not the full verbose question
    search_query = slug.replace("-", " ")  # "exercise and depression treatment"
    articles = await _fetch_research(search_query, http)

    # Build research context block for the prompt
    research_block = ""
    if articles:
        lines = ["RESEARCH EVIDENCE (use these real studies in your article):"]
        for i, a in enumerate(articles, 1):
            lines.append(
                f"{i}. \"{a['title']}\" — {a['journal']} ({a['year']})"
                f"  [PMID: {a['pmid']}] {a['url']}"
            )
        research_block = "\n".join(lines)
    else:
        research_block = "RESEARCH EVIDENCE: No PubMed studies found. Write based on established medical consensus."

    system = SYSTEM_PROMPT.format(
        brand_name=brand_name,
        slug=slug,
        topic_slug=topic,
        brand_url=brand_url,
    )

    # Related slugs for internal linking
    related_context = ""
    if related_slugs:
        related_context = f"\n\nEXISTING ARTICLES (use for related_posts linking):\n{', '.join(related_slugs[:30])}"

    user_msg = f"Write a blog post answering: \"{question}\"\n\n{research_block}{related_context}"

    # ── Step 2: Generate article with GPT-4o grounded in real research ───────
    try:
        r = await http.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "temperature": TEMPERATURE,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=90.0,
        )
        if r.status_code != 200:
            logger.error("OpenAI error for %s: %s", slug, r.text[:200])
            return None

        content = r.json()["choices"][0]["message"]["content"]
        post = json.loads(content)

        # Ensure required fields
        post["slug"] = slug
        post.setdefault("topic_slug", topic)
        post.setdefault("author", "Kortney")
        post.setdefault("brand", brand)
        post.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        body = post.get("body", "")
        post.setdefault("word_count", len(body.split()) if body else 0)
        post.setdefault(
            "hero_image",
            f"{brand_cfg['image_url_prefix']}/{slug}-hero.jpg",
        )

        # If GPT-4o didn't include citations but we have research, inject them
        if not post.get("citations") and articles:
            post["citations"] = [
                {"title": a["title"], "journal": a["journal"], "year": a["year"], "url": a["url"]}
                for a in articles if a["title"]
            ][:6]

        return post

    except Exception as e:
        logger.error("Generation failed for %s: %s", slug, e)
        return None


# ── Batch Runner ──────────────────────────────────────────────────────────────

async def run_batch(
    brand: str = "communitygroceries",
    limit: Optional[int] = None,
    topic_filter: Optional[str] = None,
    slug_filter: Optional[str] = None,
    keywords_file: Optional[str] = None,
    dry_run: bool = False,
):
    """Generate and publish posts in batches."""
    if not OPENAI_API_KEY:
        logger.error("Set OPENAI_API_KEY environment variable")
        return

    kw_path = Path(keywords_file) if keywords_file else None
    keywords = _load_keywords(kw_path)
    if not keywords:
        return

    completed = _load_progress()
    logger.info("Previously completed: %d posts", len(completed))

    # Filter
    if slug_filter:
        keywords = [k for k in keywords if k["slug"] == slug_filter]
    elif topic_filter:
        keywords = [k for k in keywords if k.get("topic_slug") == topic_filter]

    # Skip already done
    keywords = [k for k in keywords if k["slug"] not in completed]

    if limit:
        keywords = keywords[:limit]

    if not keywords:
        logger.info("Nothing to generate (all done or no matches)")
        return

    logger.info("Generating %d posts for %s...", len(keywords), brand)

    # All slugs for internal linking
    all_slugs = [k["slug"] for k in _load_keywords(kw_path)]
    all_slugs.extend(completed)

    success = 0
    errors = 0

    async with httpx.AsyncClient(timeout=90.0) as http:
        for i, kw in enumerate(keywords, 1):
            slug = kw["slug"]
            logger.info("[%d/%d] Generating: %s", i, len(keywords), slug)

            if dry_run:
                print(f"  DRY RUN: would generate {slug} ({kw.get('topic_slug', '?')})")
                continue

            post = await generate_post(kw, brand, all_slugs, http)
            if not post:
                errors += 1
                continue

            # Generate real hero image via Shania
            topic = post.get("title", slug.replace("-", " "))
            hero_url = await generate_and_upload_hero_image(slug, topic, brand)
            if hero_url:
                post["hero_image"] = hero_url

            # Publish to GCS
            if publish_post(post, brand=brand):
                completed.add(slug)
                _save_progress(completed)
                success += 1
                logger.info("  ✓ Published: %s (%d words, %d citations)",
                            slug, post.get("word_count", 0), len(post.get("citations", [])))
            else:
                errors += 1
                logger.error("  ✗ Upload failed: %s", slug)

            # Rate limit: ~2 seconds between posts (research + openai calls)
            if i < len(keywords):
                await asyncio.sleep(2)

    logger.info("Done: %d published, %d errors, %d total completed", success, errors, len(completed))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate health blog posts from keyword inventory")
    parser.add_argument("--brand", default="communitygroceries", choices=["communitygroceries", "wihy"])
    parser.add_argument("--limit", type=int, help="Max posts to generate")
    parser.add_argument("--topic", help="Filter by topic_slug")
    parser.add_argument("--slug", help="Generate a single post by slug")
    parser.add_argument("--keywords", help="Path to keywords JSON file (default: data/health_keywords_all.json)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without generating")
    parser.add_argument("--status", action="store_true", help="Show progress stats")
    args = parser.parse_args()

    if args.status:
        kw_path = Path(args.keywords) if args.keywords else None
        completed = _load_progress()
        keywords = _load_keywords(kw_path)
        remaining = [k for k in keywords if k["slug"] not in completed]
        print(f"Total keywords: {len(keywords)}")
        print(f"Completed: {len(completed)}")
        print(f"Remaining: {len(remaining)}")
        from collections import Counter
        tc = Counter(k["topic_slug"] for k in remaining)
        print("\nRemaining by topic:")
        for t, c in tc.most_common():
            print(f"  {t}: {c}")
        return

    asyncio.run(run_batch(
        brand=args.brand,
        limit=args.limit,
        topic_filter=args.topic,
        slug_filter=args.slug,
        keywords_file=args.keywords,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
