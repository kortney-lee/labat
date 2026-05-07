"""
_generate_vowels_content.py — Generate real Vowels.org articles using Kortney.

Full pipeline:
  1. WIHY RAG research (2-pass)
  2. Alex SEO keyword generation
  3. GPT-4o article writing (KORTNEY_VOWELS_SYSTEM voice)
  4. Fine-tuned voice refinement
  5. Shania / Imagen 4.0 hero image → GCS upload
  6. MDX file written to vowels/src/content/articles/

Usage:
  python _generate_vowels_content.py                    # generate next 5 unwritten
  python _generate_vowels_content.py --count=10         # generate 10
  python _generate_vowels_content.py --slug=fiber-gap   # generate one specific slug
  python _generate_vowels_content.py --dry-run          # print what would run, no API calls
  python _generate_vowels_content.py --list             # list available topics
  python _generate_vowels_content.py --force            # overwrite already-written articles
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ── Repo root on sys.path ────────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Load .env from repo root (contains OPENAI_API_KEY, GCS creds, etc.)
load_dotenv(ROOT / ".env")

# ── Import Kortney internals ─────────────────────────────────────────────────
from src.labat.services.blog_writer import (  # noqa: E402
    KORTNEY_VOWELS_SYSTEM,
    KORTNEY_VOICE_REFINE,
    GCS_BUCKETS,
    BLOG_IMAGES_PREFIX,
    SHANIA_GRAPHICS_URL,
    _query_wihy_research,
    _generate_seo_keywords,
    _refine_in_kortney_voice,
    _generate_meta_description,
    _publish_image_to_gcs,
)

try:
    import openai as _openai_mod
    _openai_available = True
except ImportError:
    _openai_available = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
logger = logging.getLogger("vowels.generate")

# ── Paths ────────────────────────────────────────────────────────────────────
ARTICLES_DIR = ROOT / "vowels" / "src" / "content" / "articles"
ARTICLES_DIR.mkdir(parents=True, exist_ok=True)

# ── Vowels topic queue ───────────────────────────────────────────────────────
# Each entry: slug, topic (research prompt), category, tags, source_links
VOWELS_TOPICS: list[dict] = [
    # ── Processed foods & labels ─────────────────────────────────────────────
    {"slug": "ultra-processed-foods-us-intake", "category": "from-the-data",
     "tags": ["processed food", "nutrition", "data", "public health"],
     "topic": "Ultra-processed foods now make up more than 60% of U.S. calorie intake. What the latest data shows and what families can do."},
    {"slug": "nutrition-label-claims-exposed", "category": "health-explained",
     "tags": ["labels", "grocery", "shopping", "nutrition"],
     "topic": "Why 'natural' and 'healthy' label claims still mislead shoppers: the regulatory gap and what the evidence shows."},
    {"slug": "snack-sodium-exposure-report", "category": "from-the-data",
     "tags": ["sodium", "snacks", "packaged food", "blood pressure"],
     "topic": "Snack-food sodium exposure is far higher than most families estimate. A data report with practical guidance."},

    # ── Blood sugar & metabolic ──────────────────────────────────────────────
    {"slug": "childhood-sugar-intake-trend", "category": "research-explained",
     "tags": ["added sugar", "kids nutrition", "blood sugar", "public health"],
     "topic": "Childhood added-sugar intake has shifted, but not enough. What the trend data shows and why it matters for parents."},
    {"slug": "glucose-spikes-daily-eating", "category": "health-explained",
     "tags": ["blood sugar", "glucose", "metabolic health", "meal planning"],
     "topic": "How everyday meal choices create glucose spikes — and the simple structural changes that reduce them."},
    {"slug": "late-night-eating-sleep-appetite", "category": "research-explained",
     "tags": ["sleep", "appetite", "meal timing", "metabolic health"],
     "topic": "Late-night eating and sleep disruption: what newer research says about next-day appetite, energy, and weight."},

    # ── Protein ──────────────────────────────────────────────────────────────
    {"slug": "breakfast-protein-gap", "category": "nutrition-education",
     "tags": ["protein", "breakfast", "satiety", "meal planning"],
     "topic": "Breakfast protein is still too low for most U.S. households. The evidence gap and practical fix for families."},
    {"slug": "protein-targets-evidence-review", "category": "research-explained",
     "tags": ["protein", "weight management", "muscle", "satiety"],
     "topic": "How much protein do you actually need? An evidence review of current targets for fat loss, muscle, and aging."},

    # ── Fiber ────────────────────────────────────────────────────────────────
    {"slug": "fiber-gap-america", "category": "from-the-data",
     "tags": ["fiber", "gut health", "nutrition", "public health"],
     "topic": "America's fiber gap is still massive — only 7% of adults meet recommendations. Why it matters and what to eat."},
    {"slug": "fiber-and-appetite-science", "category": "research-explained",
     "tags": ["fiber", "appetite", "satiety", "weight management"],
     "topic": "How dietary fiber controls appetite: the mechanism, the data, and the specific foods that work best."},

    # ── Grocery & food systems ───────────────────────────────────────────────
    {"slug": "grocery-inflation-nutrition-tradeoffs", "category": "food-systems",
     "tags": ["budget", "grocery", "inflation", "nutrition"],
     "topic": "Grocery inflation changed nutrition choices for millions of families. Which tradeoffs hurt health most and what to swap first."},
    {"slug": "organic-vs-conventional-evidence", "category": "research-explained",
     "tags": ["organic", "pesticides", "grocery", "nutrition"],
     "topic": "Organic vs conventional produce: what the research actually shows about pesticide exposure and nutrient differences."},
    {"slug": "food-desert-health-outcomes", "category": "food-systems",
     "tags": ["food access", "public health", "food systems", "equity"],
     "topic": "Living in a food desert: how limited grocery access measurably changes health outcomes across communities."},

    # ── Supplements ──────────────────────────────────────────────────────────
    {"slug": "vitamin-d-deficiency-evidence", "category": "health-explained",
     "tags": ["vitamin D", "supplements", "deficiency", "health"],
     "topic": "Vitamin D deficiency is widespread and underdiagnosed. What the evidence says about supplementation, testing, and dosing."},
    {"slug": "omega-3-research-review", "category": "research-explained",
     "tags": ["omega-3", "supplements", "heart health", "inflammation"],
     "topic": "Omega-3 supplements: reviewing the evidence on cardiovascular benefits, dose, and who actually needs them."},
    {"slug": "magnesium-sleep-health-data", "category": "research-explained",
     "tags": ["magnesium", "supplements", "sleep", "deficiency"],
     "topic": "Magnesium deficiency, sleep quality, and stress: what the research shows and whether supplementation helps."},

    # ── Hydration ────────────────────────────────────────────────────────────
    {"slug": "hydration-myths-data", "category": "from-the-data",
     "tags": ["hydration", "water", "myths", "health"],
     "topic": "Eight glasses a day and other hydration myths: what the data actually shows about fluid needs."},
    {"slug": "sports-drinks-vs-water-evidence", "category": "health-explained",
     "tags": ["hydration", "sports drinks", "sugar", "performance"],
     "topic": "Sports drinks vs water: when electrolyte drinks actually help vs when they just add sugar."},

    # ── Fasting & meal timing ────────────────────────────────────────────────
    {"slug": "intermittent-fasting-evidence-review", "category": "research-explained",
     "tags": ["fasting", "intermittent fasting", "weight loss", "metabolic health"],
     "topic": "Intermittent fasting: a balanced review of the evidence, who it helps, and the common mistakes."},
    {"slug": "meal-timing-metabolism-research", "category": "research-explained",
     "tags": ["meal timing", "metabolism", "circadian rhythm", "weight management"],
     "topic": "Does when you eat matter as much as what you eat? The research on meal timing and metabolic health."},

    # ── Weight & appetite ────────────────────────────────────────────────────
    {"slug": "appetite-hormones-leptin-ghrelin", "category": "health-explained",
     "tags": ["appetite", "hormones", "weight management", "hunger"],
     "topic": "Why you're always hungry: how leptin and ghrelin control appetite and what the research says about fixing it."},
    {"slug": "calorie-counting-evidence-review", "category": "research-explained",
     "tags": ["calories", "weight loss", "tracking", "habits"],
     "topic": "Does calorie counting work? Reviewing the evidence on tracking vs habit-based approaches to weight management."},

    # ── Alcohol ──────────────────────────────────────────────────────────────
    {"slug": "alcohol-sleep-quality-data", "category": "from-the-data",
     "tags": ["alcohol", "sleep", "recovery", "health"],
     "topic": "Alcohol and sleep quality: the data on how even moderate drinking disrupts deep sleep and recovery."},
    {"slug": "moderate-alcohol-health-rethink", "category": "research-explained",
     "tags": ["alcohol", "cardiovascular", "research", "public health"],
     "topic": "The 'moderate drinking is healthy' story is changing. What updated research says about alcohol and cardiovascular risk."},

    # ── Seed oils & cooking fats ─────────────────────────────────────────────
    {"slug": "seed-oils-evidence-review", "category": "health-explained",
     "tags": ["seed oils", "cooking oils", "inflammation", "nutrition"],
     "topic": "Are seed oils toxic? Reviewing 30 years of research on linoleic acid, inflammation, and what actually matters."},
    {"slug": "cooking-fats-comparison", "category": "nutrition-education",
     "tags": ["cooking oils", "saturated fat", "heart health", "nutrition"],
     "topic": "Olive oil, butter, coconut oil, canola: a practical comparison of cooking fats based on the research."},
]

SOURCE_LINKS_DEFAULT = [
    "https://www.cdc.gov/nutrition/index.html",
    "https://www.ncbi.nlm.nih.gov/pmc/",
    "https://www.dietaryguidelines.gov",
    "https://pubmed.ncbi.nlm.nih.gov/",
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _yaml_quoted(value: str) -> str:
    return json.dumps(str(value))


def _frontmatter_list(values: list[str]) -> str:
    return "\n".join(f"  - {v}" for v in values)


def _reading_time(text: str) -> int:
    return max(1, round(len(text.split()) / 220))


def _extract_title(body: str, fallback: str) -> str:
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.lstrip("# ").strip()
    return fallback


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1]
    return value


def _extract_frontmatter(raw: str) -> dict:
    match = re.match(r"(?s)^---\n(.*?)\n---\n", raw)
    if not match:
        return {}

    fm = match.group(1)
    data: dict = {}
    key_patterns = ["slug", "title", "description", "category", "publishedAt"]
    for key in key_patterns:
        m = re.search(rf"(?m)^{re.escape(key)}:\s*(.+)$", fm)
        if m:
            data[key] = _strip_quotes(m.group(1).strip())

    tags_block = re.search(r"(?m)^tags:[ \t]*\r?\n((?:[ \t]*-[ \t]*.*(?:\r?\n|$))+)", fm)
    if tags_block:
        tags = []
        for line in tags_block.group(1).splitlines():
            t = re.sub(r"^\s*-\s*", "", line).strip()
            if t:
                tags.append(_strip_quotes(t))
        data["tags"] = tags
    else:
        data["tags"] = []

    return data


def _body_word_count(raw: str) -> int:
    body = re.sub(r"(?s)^---\n.*?\n---\s*", "", raw)
    return len(re.findall(r"\b\w+\b", body))


def _topic_from_frontmatter(title: str, description: str, tags: list[str]) -> str:
    tag_hint = ", ".join(tags[:6]) if tags else "nutrition, evidence, family health"
    return (
        f"{title}. {description} "
        f"Create a complete evidence-based article with clear recommendations, practical steps, and newsroom clarity. "
        f"Prioritize these angles where relevant: {tag_hint}."
    )


def _build_thin_article_queue(min_words: int, force: bool = False) -> list[dict]:
    queue: list[dict] = []
    for path in sorted(ARTICLES_DIR.glob("*.mdx")):
        raw = path.read_text(encoding="utf-8")
        words = _body_word_count(raw)
        if not force and words > min_words:
            continue

        fm = _extract_frontmatter(raw)
        slug = fm.get("slug") or path.stem
        title = fm.get("title") or slug.replace("-", " ").title()
        description = fm.get("description") or f"Evidence-based guidance for {title}."
        category = fm.get("category") or "health-explained"
        tags = fm.get("tags") or ["nutrition", "health"]

        queue.append(
            {
                "slug": slug,
                "category": category,
                "tags": tags,
                "topic": _topic_from_frontmatter(title, description, tags),
                "existing_words": words,
            }
        )

    return sorted(queue, key=lambda x: (x.get("existing_words", 0), x["slug"]))


def _find_topic_entry_by_slug(slug: str) -> dict | None:
    for t in VOWELS_TOPICS:
        if t["slug"] == slug:
            return t

    path = ARTICLES_DIR / f"{slug}.mdx"
    if not path.exists():
        return None

    raw = path.read_text(encoding="utf-8")
    fm = _extract_frontmatter(raw)
    title = fm.get("title") or slug.replace("-", " ").title()
    description = fm.get("description") or f"Evidence-based guidance for {title}."
    category = fm.get("category") or "health-explained"
    tags = fm.get("tags") or ["nutrition", "health"]
    return {
        "slug": slug,
        "category": category,
        "tags": tags,
        "topic": _topic_from_frontmatter(title, description, tags),
    }


def _build_mdx(
    slug: str,
    title: str,
    description: str,
    category: str,
    tags: list[str],
    body: str,
    published_at: str,
    source_links: list[str],
    image_url: str = "",
    image_alt: str = "",
) -> str:
    image_line = f'\nimage: "{image_url}"' if image_url else ""
    image_alt_line = f'\nimageAlt: {_yaml_quoted(image_alt)}' if image_alt else ""

    return f"""---
slug: {slug}
title: {_yaml_quoted(title)}
description: {_yaml_quoted(description)}
category: {category}
author: Kortney
publishedAt: {published_at}
readingTime: {_reading_time(body)}
takeaway: "Evidence-based guidance from Vowels editorial research."
tags:
{_frontmatter_list(tags)}
status: published{image_line}{image_alt_line}
sourceLinks:
{_frontmatter_list(source_links)}
---

{body}
"""


# ── Hero image via Shania ────────────────────────────────────────────────────

async def _fetch_hero_image(slug: str, topic: str) -> str:
    """Call Shania /generate-hero-image, upload to GCS, return public URL. Returns '' on failure."""
    try:
        async with httpx.AsyncClient(timeout=90) as http:
            resp = await http.post(
                f"{SHANIA_GRAPHICS_URL}/generate-hero-image",
                json={"topic": topic, "brand": "wihy", "slug": slug},
            )
            if resp.status_code != 200:
                logger.warning("Shania hero image failed (%d) for %s: %s", resp.status_code, slug, resp.text[:200])
                return ""

            data = resp.json()

            # Shania returns a GCS URL directly
            if data.get("url"):
                logger.info("Hero image URL from Shania for '%s': %s", slug, data["url"])
                return data["url"]

            # Fallback: base64 bytes — upload to GCS ourselves
            import base64
            if data.get("imageBase64"):
                image_bytes = base64.b64decode(data["imageBase64"])
                bucket_name = GCS_BUCKETS.get("vowels", "wihy-web-assets")
                image_path = f"{BLOG_IMAGES_PREFIX}/vowels-{slug}-hero.jpg"
                _publish_image_to_gcs(bucket_name, image_path, image_bytes)
                url = f"https://storage.googleapis.com/{bucket_name}/{image_path}"
                logger.info("Hero image uploaded for '%s': %s", slug, url)
                return url

    except Exception as e:
        logger.warning("Hero image generation failed for '%s': %s", slug, e)
    return ""


# ── Article writing pipeline ─────────────────────────────────────────────────

async def write_vowels_article(entry: dict, dry_run: bool = False) -> dict | None:
    """Run full Kortney pipeline for a Vowels article. Returns result dict."""
    slug = entry["slug"]
    topic = entry["topic"]
    category = entry["category"]
    tags = entry["tags"]

    logger.info("KORTNEY → VOWELS: Writing '%s'", slug)
    logger.info("  Topic: %s", topic[:100])

    if dry_run:
        logger.info("  [dry-run] Skipping API calls.")
        return {"slug": slug, "dry_run": True}

    # Step 1: RAG research
    logger.info("  Step 1: WIHY RAG research...")
    research = await _query_wihy_research(topic)
    logger.info("  Research: %d chars, %d citations", len(research["research"]), len(research["citations"]))

    # Step 2: SEO keywords
    logger.info("  Step 2: Alex SEO keywords...")
    keywords = await _generate_seo_keywords(topic, brand="wihy")
    logger.info("  Keywords: %s", keywords[:6])

    # Step 3: GPT-4o article with Vowels system prompt
    logger.info("  Step 3: GPT-4o article writing...")

    system = KORTNEY_VOWELS_SYSTEM
    system += f"\n\nSEO TARGET KEYWORDS (weave naturally):\n{', '.join(keywords)}"

    citations_block = ""
    if research["citations"]:
        cites = []
        for i, c in enumerate(research["citations"][:8], 1):
            title = c.get("title", "Untitled")
            authors = c.get("authors", "")
            year = c.get("year", "")
            pmcid = c.get("pmcid", "")
            cites.append(f"{i}. {title} ({authors}, {year}) [PMCID: {pmcid}]")
        citations_block = "\n\nAVAILABLE CITATIONS:\n" + "\n".join(cites)

    user_msg = (
        f"Write a complete newsroom-quality article on this topic:\n\n"
        f"TOPIC: {topic}\n\n"
        f"RESEARCH FROM WIHY KNOWLEDGE BASE:\n{research['research'][:6000]}"
        f"{citations_block}\n\n"
        f"Write the full article in markdown. Include a ## References section at the end."
    )

    if not _openai_available:
        logger.error("openai package not available")
        return None

    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("WIHY_OPENAI_API_KEY") or ""
    if not openai_key:
        logger.error("No OPENAI_API_KEY set")
        return None

    import openai as _oa
    client = _oa.AsyncOpenAI(api_key=openai_key)
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.75,
            max_tokens=4000,
        )
        body = resp.choices[0].message.content.strip()
        logger.info("  Draft: %d chars", len(body))
    except Exception as e:
        logger.error("  Article generation failed: %s", e)
        return None

    # Step 4: Voice refinement
    logger.info("  Step 4: Voice refinement...")
    body = await _refine_in_kortney_voice(body)

    # Step 5: Meta description
    title = _extract_title(body, topic[:80])
    meta = await _generate_meta_description(title, topic, brand="wihy")

    # Step 6: Shania hero image
    logger.info("  Step 5: Shania hero image (Imagen 4.0)...")
    image_url = await _fetch_hero_image(slug, topic)
    if image_url:
        logger.info("  Hero image: %s", image_url)
    else:
        logger.warning("  Hero image unavailable — Unsplash fallback will be used")

    # Collect source URLs from citations
    source_links = SOURCE_LINKS_DEFAULT[:]
    for c in research["citations"][:5]:
        pmcid = c.get("pmcid", "")
        if pmcid:
            source_links.append(f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/")

    published_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    mdx = _build_mdx(
        slug=slug,
        title=title,
        description=meta,
        category=category,
        tags=tags,
        body=body,
        published_at=published_at,
        source_links=source_links,
        image_url=image_url,
        image_alt=f"{title} — Vowels Nutrition",
    )

    out_path = ARTICLES_DIR / f"{slug}.mdx"
    out_path.write_text(mdx, encoding="utf-8")
    logger.info("  Written: %s (%d chars)", out_path.name, len(mdx))

    return {
        "slug": slug,
        "title": title,
        "path": str(out_path),
        "image_url": image_url,
        "word_count": len(body.split()),
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="Generate Vowels articles via Kortney pipeline")
    parser.add_argument("--slug", help="Generate one specific article by slug")
    parser.add_argument("--count", type=int, default=5, help="Number of articles to generate (default: 5)")
    parser.add_argument("--all", action="store_true", help="Generate all matching items (ignore --count limit)")
    parser.add_argument("--fill-thin", action="store_true", help="Auto-fill existing thin article files from frontmatter")
    parser.add_argument("--min-words", type=int, default=250, help="Word-count threshold for --fill-thin (default: 250)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would run without calling APIs")
    parser.add_argument("--force", action="store_true", help="Overwrite already-written articles")
    parser.add_argument("--list", action="store_true", help="List all available topic slugs and exit")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable Vowels topics:")
        for t in VOWELS_TOPICS:
            exists = (ARTICLES_DIR / f"{t['slug']}.mdx").exists()
            status = "✓ exists" if exists else "· pending"
            print(f"  {status}  {t['slug']}")
            print(f"           {t['topic'][:90]}")
        return

    # Resolve topic list
    if args.slug:
        match = _find_topic_entry_by_slug(args.slug)
        if not match:
            logger.error("Slug '%s' not found. Run --list to see available slugs.", args.slug)
            sys.exit(1)
        queue = [match]
    elif args.fill_thin:
        queue = _build_thin_article_queue(min_words=args.min_words, force=args.force)
        if not args.all:
            queue = queue[: args.count]
    else:
        # Skip already-written unless --force
        pending = [
            t for t in VOWELS_TOPICS
            if args.force or not (ARTICLES_DIR / f"{t['slug']}.mdx").exists()
        ]
        queue = pending if args.all else pending[: args.count]

    if not queue:
        logger.info("Nothing to generate — all topics already written. Use --force to regenerate.")
        return

    logger.info("Generating %d Vowels article(s) via Kortney...", len(queue))
    results = []
    for entry in queue:
        result = await write_vowels_article(entry, dry_run=args.dry_run)
        if result:
            results.append(result)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Kortney generated {len(results)} Vowels article(s)")
    for r in results:
        if r.get("dry_run"):
            print(f"  [dry-run] {r['slug']}")
        else:
            img = "✓ image" if r.get("image_url") else "· no image"
            print(f"  ✓ {r['slug']}  ({r.get('word_count', '?')} words)  {img}")
    print(f"{'=' * 60}\n")
    print("Next steps:")
    print("  cd vowels && npm run build")
    print("  firebase deploy --only hosting:vowels --project wihy-ai --config ../firebase.vowels.json")


if __name__ == "__main__":
    asyncio.run(main())
