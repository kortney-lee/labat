from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.content.blog_publisher import BRAND_GCS, generate_and_upload_hero_image, publish_post
from src.content.commercial_page_policy import (
    sanitize_trending_post,
    trending_meal_citations,
    trending_reference_block,
)

logger = logging.getLogger("wihy.generate_trending_meal_pages")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o"
INVENTORY_FILE = Path("data/communitygroceries_trending_meal_pages.json")
PROGRESS_FILE = Path("data/communitygroceries_trending_meal_progress.json")

SERVICES_URL = os.getenv("SERVICES_URL", "https://services.wihy.ai").rstrip("/")
CLIENT_ID = os.getenv("WIHY_ML_CLIENT_ID", "wihy_ml_mk1waylw")
CLIENT_SECRET = os.getenv("WIHY_ML_CLIENT_SECRET", "")
MIN_WORD_COUNT = 800
MAX_ATTEMPTS = 3
REQUIRED_SECTION_ALIASES = {
    "Why This Meal Topic is Trending": [
        "why this meal topic is trending",
        "why this topic is trending",
        "why this meal is trending",
    ],
    "Quick Nutrition Breakdown": [
        "quick nutrition breakdown",
        "nutrition breakdown",
    ],
    "Practical Grocery List": [
        "practical grocery list",
        "grocery list",
    ],
    "3 Simple Ways to Make It Healthier": [
        "3 simple ways to make it healthier",
        "three simple ways to make it healthier",
        "ways to make it healthier",
    ],
    "Budget and Prep Tips": [
        "budget and prep tips",
        "budget tips",
        "prep tips",
    ],
    "Who This Meal Style is Best For": [
        "who this meal style is best for",
        "who this is best for",
        "who it's best for",
        "who it is best for",
    ],
    "FAQ": [
        "faq",
        "frequently asked questions",
    ],
}

CANONICAL_HEADING_PATTERNS = {
    "Why This Meal Topic is Trending": [
        r"why .*trending",
    ],
    "Quick Nutrition Breakdown": [
        r"quick nutrition breakdown",
        r"nutrition breakdown",
        r"nutrition (?:snapshot|overview|at a glance)",
    ],
    "Practical Grocery List": [
        r"practical grocery list",
        r"grocery list",
        r"what to buy",
        r"shopping list",
    ],
    "3 Simple Ways to Make It Healthier": [
        r"(?:3|three) simple ways to make it healthier",
        r"ways to make it healthier",
        r"how to make it healthier",
        r"make it healthier",
    ],
    "Budget and Prep Tips": [
        r"budget and prep tips",
        r"budget tips",
        r"prep tips",
        r"budget-friendly prep",
    ],
    "Who This Meal Style is Best For": [
        r"who this meal style is best for",
        r"who this is best for",
        r"who it(?:'s| is) best for",
        r"best for",
    ],
    "FAQ": [
        r"faq",
        r"frequently asked questions",
    ],
}


def _load_inventory(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or INVENTORY_FILE
    if not target.exists():
        logger.error("Missing %s", target)
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    return data.get("pages", [])


def _load_progress() -> set[str]:
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    return set()


def _save_progress(completed: set[str]) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps({"completed": sorted(completed), "count": len(completed)}, indent=2),
        encoding="utf-8",
    )


def _read_live_post(slug: str, brand: str) -> Optional[Dict[str, Any]]:
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    bucket = brand_cfg["bucket"].replace("/blog/posts", "")
    result = subprocess.run(
        ["gcloud", "storage", "cat", f"{bucket}/blog/posts/{slug}.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _missing_sections(body: str) -> List[str]:
    missing = []
    normalized = body.lower()
    for section, aliases in REQUIRED_SECTION_ALIASES.items():
        if not any(alias in normalized for alias in aliases):
            missing.append(section)
    return missing


def _normalize_required_headings(body: str) -> str:
    if not body:
        return body

    normalized_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("##"):
            normalized_lines.append(line)
            continue

        heading_text = stripped.lstrip("#").strip().lower()
        replacement = None
        for canonical, patterns in CANONICAL_HEADING_PATTERNS.items():
            if any(re.fullmatch(pattern, heading_text) for pattern in patterns):
                replacement = canonical
                break

        if replacement:
            prefix = line[: len(line) - len(line.lstrip())]
            normalized_lines.append(f"{prefix}## {replacement}")
        else:
            normalized_lines.append(line)

    return "\n".join(normalized_lines)


def _validate_payload(payload: Dict[str, Any], keyword: str) -> List[str]:
    issues: List[str] = []
    body = _normalize_required_headings(str(payload.get("body", "") or ""))
    payload["body"] = body
    title = str(payload.get("title", "") or "")
    meta_description = str(payload.get("meta_description", "") or "")

    word_count = len(body.split())
    if word_count < MIN_WORD_COUNT:
        issues.append(f"Body is too short ({word_count} words). Minimum is {MIN_WORD_COUNT}.")

    missing_sections = _missing_sections(body)
    if missing_sections:
        issues.append("Missing required sections: " + ", ".join(missing_sections))

    if keyword.lower() not in title.lower():
        issues.append("Title must clearly include the primary keyword.")

    if len(meta_description) > 155:
        issues.append("Meta description exceeds 155 characters.")

    if not payload.get("faq_items"):
        issues.append("FAQ items are required.")
    
    # Validate citations are from approved sources
    from src.content.commercial_page_policy import validate_citations
    citations = payload.get("citations", [])
    if citations:
        citation_check = validate_citations(citations, citation_type="meal")
        if not citation_check.get("valid"):
            issues.append(f"Citations from unapproved sources: {citation_check.get('message')}")

    return issues


SYSTEM_PROMPT = """You are Kortney writing practical trending-meal pages for Community Groceries.

Goal:
- Help users quickly understand what people are searching for and how to turn that into healthier, realistic meals.
- Keep the advice grounded, simple, and actionable.
- No hype and no unsupported medical claims.
- Do not use unrelated medical studies or PubMed citations for these meal-intent pages. Use only the official consumer guidance references provided.

Return ONLY valid JSON with these exact fields:
{{
    "slug": "{slug}",
    "title": "SEO title",
    "body": "Markdown article, 900-1300 words",
    "meta_description": "Under 155 chars",
    "topic_slug": "{topic_slug}",
    "seo_keywords": ["array", "of", "target", "keywords"],
    "faq_items": [
        {{"question": "...", "answer": "..."}}
    ],
    "key_takeaways": ["..."],
    "citations": [
        {{"title": "...", "journal": "...", "year": 2024, "url": "https://..."}}
    ],
    "related_posts": [
        {{"slug": "...", "title": "..."}}
    ]
}}

Required body structure:
1. Why this meal topic is trending
2. Quick nutrition breakdown
3. Practical grocery list
4. 3 simple ways to make it healthier
5. Budget and prep tips
6. Who this meal style is best for
7. FAQ

Length and specificity rules:
- The body must be 900-1300 words.
- Each main section before the FAQ needs at least 2 substantive paragraphs.
- Do not use placeholder copy, generic filler, or broad wellness language that could fit any meal topic.
- Anchor every section to the exact meal keyword in the prompt.
- If the draft is under the minimum length, expand the practical guidance instead of shortening sections.

End with a clear CTA to Community Groceries meal planning.
"""


def _build_related_posts(
    slug: str,
    keywords: List[str],
    topic_slug: str,
    all_pages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Build related_posts array by matching keywords and topic.
    
    Priority:
    1. Same topic with overlapping keywords (≥2 overlaps)
    2. Same topic without keyword overlap
    3. Different topic with significant keyword overlap
    """
    if not all_pages:
        return []
    
    my_keywords = set(k.lower().strip() for k in keywords)
    
    # Filter out self
    candidates = [p for p in all_pages if p.get("slug") != slug]
    
    # Score each candidate
    scored = []
    for page in candidates:
        page_keywords = set(k.lower().strip() for k in page.get("seo_keywords", []))
        overlap_count = len(my_keywords & page_keywords)
        is_same_topic = page.get("topic_slug") == topic_slug
        
        score = 0
        if is_same_topic and overlap_count >= 2:
            score = 100 + overlap_count  # Highest priority: same topic + good keyword overlap
        elif is_same_topic:
            score = 50  # Second: same topic
        elif overlap_count >= 2:
            score = 25 + overlap_count  # Third: keyword overlap
        else:
            score = 0
        
        if score > 0:
            scored.append((score, page))
    
    # Sort by score desc and take top 5
    scored.sort(key=lambda x: x[0], reverse=True)
    related = [page for _, page in scored[:5]]
    
    return [
        {
            "slug": p.get("slug", ""),
            "title": p.get("title", p.get("slug", "").replace("-", " ").title()),
            "route_path": p.get("route_path", f"/meals/{p.get('slug', '')}"),
        }
        for p in related
    ]


def _inject_internal_links(post: Dict[str, Any]) -> Dict[str, Any]:
    """Inject internal links into body and ensure related_posts is set."""
    body = post.get("body", "")
    related_posts = post.get("related_posts", [])
    
    if not body or not related_posts:
        return post
    
    # Build "Keep Reading" section
    lines = ["\n\n---\n\n### Keep Reading\n"]
    for p in related_posts[:5]:
        route_path = p.get("route_path", f"/meals/{p.get('slug', '')}")
        title = p.get("title", p.get("slug", "").replace("-", " ").title())
        lines.append(f"- [{title}]({route_path})")
    keep_reading = "\n".join(lines) + "\n"
    
    # Insert before FAQ if present, else append
    import re
    faq_match = re.search(r'\n## (?:FAQ|Frequently Asked Questions)\b', body, re.IGNORECASE)
    if faq_match:
        body = body[:faq_match.start()] + keep_reading + body[faq_match.start():]
    else:
        body = body.rstrip() + keep_reading
    
    post["body"] = body
    return post


async def generate_page(
    page: Dict[str, Any],
    brand: str,
    all_pages: List[Dict[str, Any]],
    http: httpx.AsyncClient,
) -> Optional[Dict[str, Any]]:
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    brand_name = "Community Groceries" if brand == "communitygroceries" else "WIHY"
    slug = page["slug"]
    topic_slug = page.get("topic_slug", "nutrition")
    keyword = page.get("keyword", slug.replace("-", " "))
    route_base = page.get("route_base", "/trending")
    route_path = page.get("route_path", f"{route_base.rstrip('/')}/{slug}")
    page_type = page.get("page_type", "trending-meal")

    reference_block = trending_reference_block()

    related_candidates = [p["slug"] for p in all_pages if p["slug"] != slug][:20]

    user_prompt = f"""
Primary keyword: {keyword}
Target title: {page.get('title', '')}
Target route: {route_path}
Target brand: {brand_name}
Meta description target: {page.get('meta_description', '')}
Preferred SEO keywords: {', '.join(page.get('seo_keywords', []))}
Available related page slugs: {', '.join(related_candidates)}

Write the page so it can rank for this meal intent and provide practical health-first meal guidance.

Hard requirements:
- The body must land between 900 and 1300 words.
- Use these exact markdown headings: Why This Meal Topic is Trending; Quick Nutrition Breakdown; Practical Grocery List; 3 Simple Ways to Make It Healthier; Budget and Prep Tips; Who This Meal Style is Best For; FAQ.
- The title must include the primary keyword.
- The draft must be specific to this keyword, not reusable generic meal-prep advice.

Citation rules for this page type:
- Use only the official references provided below.
- Do not cite PubMed studies, journals, or unrelated clinical research.
- Keep citations aligned to healthy eating guidance, budgeting, and practical meal planning.

{reference_block}
"""

    retry_prompt = user_prompt
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = await http.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "temperature": 0.35,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT.format(slug=slug, topic_slug=topic_slug),
                    },
                    {"role": "user", "content": retry_prompt},
                ],
                "max_completion_tokens": 4000,
                "response_format": {"type": "json_object"},
            },
            timeout=90.0,
        )
        if response.status_code != 200:
            logger.error("OpenAI error for %s: %s", slug, response.text[:200])
            return None

        payload = json.loads(response.json()["choices"][0]["message"]["content"])
        body = payload.get("body", "")

        payload["slug"] = slug
        payload["route_base"] = route_base
        payload["route_path"] = route_path
        payload["page_type"] = page_type
        payload["topic_slug"] = topic_slug
        payload.setdefault("seo_keywords", page.get("seo_keywords", []))
        payload.setdefault("title", page.get("title", slug.replace("-", " ").title()))
        payload.setdefault("meta_description", page.get("meta_description", ""))
        payload.setdefault("author", "Kortney")
        payload.setdefault("brand", brand)
        payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        payload.setdefault(
            "hero_image",
            f"{brand_cfg['image_url_prefix']}/{slug}-hero.jpg",
        )
        payload.setdefault("word_count", len(body.split()) if body else 0)
        payload.setdefault("schema_type", "Article")
        payload.setdefault("tags", ["trending-meals", topic_slug, "meal-intent"])
        payload["citations"] = trending_meal_citations()

        issues = _validate_payload(payload, keyword)
        if not issues:
            # Build related posts and inject internal links
            payload["related_posts"] = _build_related_posts(
                slug=slug,
                keywords=payload.get("seo_keywords", []),
                topic_slug=topic_slug,
                all_pages=all_pages,
            )
            payload = _inject_internal_links(payload)
            return sanitize_trending_post(payload)

        if attempt == MAX_ATTEMPTS:
            logger.error("Validation failed for %s after %d attempts: %s", slug, attempt, "; ".join(issues))
            return None

        retry_prompt = (
            user_prompt
            + "\n\nYour last draft failed validation. Revise the existing draft instead of starting over. Fix all of these issues exactly:\n- "
            + "\n- ".join(issues)
            + "\n\nReturn a fuller, page-specific draft that satisfies every required section and word-count requirement. Preserve the good parts of the previous draft, but expand the weak sections. Keep the required section headings exactly as written in the prompt.\n\nPrevious draft JSON:\n"
            + json.dumps(payload, ensure_ascii=False)
        )


async def run_batch(
    brand: str = "communitygroceries",
    inventory_file: Optional[str] = None,
    slug_filter: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    force: bool = False,
    reuse_live_hero: bool = False,
) -> None:
    if not OPENAI_API_KEY:
        logger.error("Set OPENAI_API_KEY environment variable")
        return

    inventory_path = Path(inventory_file) if inventory_file else INVENTORY_FILE
    pages = _load_inventory(inventory_path)
    if not pages:
        return

    completed = _load_progress()
    logger.info("Previously completed: %d pages", len(completed))

    if slug_filter:
        pages = [page for page in pages if page["slug"] == slug_filter]

    if not force:
        pages = [page for page in pages if page["slug"] not in completed]

    if limit:
        pages = pages[:limit]

    if not pages:
        logger.info("Nothing to generate")
        return

    async with httpx.AsyncClient(timeout=90.0) as http:
        for index, page in enumerate(pages, 1):
            slug = page["slug"]
            logger.info("[%d/%d] Generating: %s", index, len(pages), slug)
            if dry_run:
                print(f"DRY RUN: would generate {slug} -> {page.get('route_path')}")
                continue

            generated = await generate_page(page, brand, pages, http)
            if not generated:
                continue

            if reuse_live_hero:
                live_post = _read_live_post(slug, brand)
                if live_post and live_post.get("hero_image"):
                    generated["hero_image"] = live_post["hero_image"]
            else:
                topic = generated.get("title", slug.replace("-", " "))
                hero_url = await generate_and_upload_hero_image(slug, topic, brand)
                if hero_url:
                    generated["hero_image"] = hero_url

            if publish_post(generated, brand=brand):
                completed.add(slug)
                _save_progress(completed)
                logger.info("  ✓ Published: %s (%d words)", slug, generated.get("word_count", 0))
            else:
                logger.error("  ✗ Upload failed: %s", slug)

            if index < len(pages):
                await asyncio.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Community Groceries trending meal pages")
    parser.add_argument("--brand", default="communitygroceries", choices=["communitygroceries", "wihy"])
    parser.add_argument("--inventory", help="Path to page inventory JSON")
    parser.add_argument("--slug", help="Generate a single page by slug")
    parser.add_argument("--limit", type=int, help="Max pages to generate")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--force", action="store_true", help="Regenerate even if slug is marked complete")
    parser.add_argument("--reuse-live-hero", action="store_true", help="Keep the currently published hero image instead of regenerating it")
    args = parser.parse_args()

    inventory_path = Path(args.inventory) if args.inventory else INVENTORY_FILE
    if args.status:
        pages = _load_inventory(inventory_path)
        completed = _load_progress()
        remaining = [page for page in pages if page["slug"] not in completed]
        print(f"Total pages: {len(pages)}")
        print(f"Completed: {len(completed)}")
        print(f"Remaining: {len(remaining)}")
        for page in remaining:
            print(f"  {page['route_path']}")
        return

    asyncio.run(
        run_batch(
            brand=args.brand,
            inventory_file=args.inventory,
            slug_filter=args.slug,
            limit=args.limit,
            dry_run=args.dry_run,
            force=args.force,
            reuse_live_hero=args.reuse_live_hero,
        )
    )


if __name__ == "__main__":
    main()
