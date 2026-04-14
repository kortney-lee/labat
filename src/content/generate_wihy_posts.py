"""
Generate WIHY Insights blog posts using OpenAI + Research API.

Uses GPT-4o (Kortney's trained model) for content generation and the
services.wihy.ai research API for real PubMed citations with references.

Routes:
  - /insights/{slug}   → nutrition, supplements, gut-health, heart-health, etc.
  - /fitness/{slug}     → fitness & exercise topics
  - /wellness/{slug}    → mental-health, sleep, longevity
  - /trends/{slug}      → health-apps, AI tools, tech
  - /comparison/{slug}  → comparisons, reviews, "vs" keywords
  - /research/{slug}    → (reserved for future research deep-dives)
  - /blog/{slug}        → catch-all (weight-management, meal-planning, etc.)

Usage:
    python -m src.content.generate_wihy_posts                  # generate all
    python -m src.content.generate_wihy_posts --limit 10       # first 10
    python -m src.content.generate_wihy_posts --topic nutrition # one topic
    python -m src.content.generate_wihy_posts --slug seed-oils  # one post
    python -m src.content.generate_wihy_posts --dry-run         # preview only
    python -m src.content.generate_wihy_posts --status          # show progress
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.content.blog_publisher import BRAND_GCS, generate_and_upload_hero_image, publish_post
from src.content.post_publish_hooks import on_post_published

logger = logging.getLogger("wihy.generate_wihy_posts")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# ── Config ────────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o"
TEMPERATURE = 0.7

DATA_FILE = Path("data/wihy_content_keywords.json")
PROGRESS_FILE = Path("data/wihy_posts_progress.json")

SERVICES_URL = os.getenv("SERVICES_URL", "https://services.wihy.ai").rstrip("/")
CLIENT_ID = os.getenv("WIHY_ML_CLIENT_ID", "wihy_ml_mk1waylw")
CLIENT_SECRET = os.getenv("WIHY_ML_CLIENT_SECRET", "")

BRAND = "wihy"
BRAND_CFG = BRAND_GCS["wihy"]

# ── Route mapping: topic + intent → route prefix ─────────────────────────────

# Map topic_slug → route prefix
_TOPIC_ROUTES = {
    # /insights — core health & nutrition science
    "nutrition": "/insights",
    "supplements": "/insights",
    "gut-health": "/insights",
    "heart-health": "/insights",
    "sugar-and-blood-health": "/insights",
    "processed-foods": "/insights",
    "fasting": "/insights",
    "alcohol-and-health": "/insights",
    "protein-and-muscle": "/insights",
    "hydration": "/insights",
    "immune-health": "/insights",
    "hormones": "/insights",
    "brain-health": "/insights",
    "food-scanning": "/insights",
    # /fitness — exercise & workout topics
    "fitness": "/fitness",
    # /wellness — mental health, sleep, longevity, holistic
    "mental-health": "/wellness",
    "sleep": "/wellness",
    "wellness": "/wellness",
    "longevity": "/wellness",
    # /trends — health-apps, tech, AI tools
    "health-apps": "/trends",
}

# Intent overrides — these take priority over topic-based routing
_INTENT_ROUTES = {
    "comparisons": "/comparison",
    "reviews": "/comparison",
}

def _route_base(topic_slug: str, intent: str = "") -> str:
    """Route based on intent first, then topic, then fallback to /blog."""
    # Intent-based override (comparisons, reviews → /comparison)
    if intent in _INTENT_ROUTES:
        return _INTENT_ROUTES[intent]
    # Topic-based routing
    if topic_slug in _TOPIC_ROUTES:
        return _TOPIC_ROUTES[topic_slug]
    # Catch-all: weight-management, meal-planning, etc.
    return "/blog"


# ── Data loading ──────────────────────────────────────────────────────────────

def _load_keywords(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = path or DATA_FILE
    if not target.exists():
        logger.error("Missing %s", target)
        return []
    data = json.loads(target.read_text(encoding="utf-8"))
    return data.get("keywords", [])


def _load_progress() -> set:
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


# ── Research API ──────────────────────────────────────────────────────────────

# Words that add noise to PubMed queries
_STOP_WORDS = {
    "what", "is", "are", "the", "a", "an", "of", "for", "to", "in", "on",
    "and", "or", "how", "does", "do", "can", "should", "will", "would",
    "best", "top", "most", "really", "actually", "much", "many", "vs",
    "your", "you", "my", "i", "me", "we", "it", "its", "that", "this",
    "with", "from", "by", "at", "about", "why", "when", "which", "where",
    "has", "have", "had", "be", "been", "was", "were", "not", "no",
    "good", "bad", "better", "worse", "free", "app", "apps", "review",
    "reviews", "reddit", "2024", "2025", "2026",
}

# Expand abbreviations for better PubMed results
_TERM_EXPANSIONS = {
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "bp": "blood pressure",
    "hr": "heart rate",
    "bmi": "body mass index",
    "tdee": "total daily energy expenditure",
    "hiit": "high intensity interval training",
    "bcaa": "branched chain amino acids",
    "pcos": "polycystic ovary syndrome",
    "ibs": "irritable bowel syndrome",
    "gerd": "gastroesophageal reflux",
}


def _build_pubmed_query(keyword: str) -> str:
    """Turn a user-facing keyword into a cleaner PubMed search query.

    Removes noise words, expands abbreviations, keeps the scientific core.
    Example: 'what is ai nutrition' -> 'artificial intelligence nutrition'
    """
    words = keyword.lower().split()
    expanded = []
    for w in words:
        if w in _STOP_WORDS:
            continue
        expanded.append(_TERM_EXPANSIONS.get(w, w))
    query = " ".join(expanded).strip()
    # If too short after filtering, fall back to original
    if len(query) < 4:
        return keyword
    return query


async def _fetch_fact_check(
    question: str, http: httpx.AsyncClient
) -> Optional[Dict[str, Any]]:
    """Call the Fact Check API for evidence-weighted verdicts and key findings.

    Returns structured evidence (verdict, grade, key findings, sources) from
    48M+ PubMed/PMC records in ~30-100ms with zero AI cost.
    """
    try:
        r = await http.post(
            f"{SERVICES_URL}/api/facts/check",
            json={"question": question, "limit": 10, "include_research": True, "include_sources": True},
            headers={
                "X-Client-ID": CLIENT_ID,
                "X-Client-Secret": CLIENT_SECRET,
            },
            timeout=30.0,
        )
        if r.status_code != 200:
            logger.warning("Fact Check API %d for '%s'", r.status_code, question[:60])
            return None
        data = r.json()
        if not data.get("success"):
            return None
        logger.info(
            "  Fact Check: %s — %s (%d findings) in %dms",
            data.get("verdict", "?"),
            data.get("evidence_grade", "?"),
            len(data.get("key_findings", [])),
            data.get("timing_ms", 0),
        )
        return data
    except Exception as e:
        logger.warning("Fact Check failed for '%s': %s", question[:50], e)
        return None


async def _fetch_research(query: str, http: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch PubMed citations from services.wihy.ai/api/research/search."""
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


# ── OpenAI Generation ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Kortney, the health & wellness expert behind WIHY (What Is Healthy for You).
Write a comprehensive, evidence-based article answering this question.

Your voice: approachable, knowledgeable, real. You care about the reader — not clinical, not corporate. You cite real research when it exists.

Return ONLY a JSON object with these exact fields:
{{
  "slug": "{slug}",
  "title": "SEO-optimized headline (60 chars max)",
  "body": "Full article in markdown. Use ## for H2, ### for H3, **bold**, lists. MINIMUM 1000 words — aim for 1200-1500.",
  "meta_description": "Compelling meta description under 155 characters",
  "topic_slug": "{topic_slug}",
  "seo_keywords": ["8-12 long-tail keyword phrases as an array"],
  "faq_items": [
    {{"question": "A real question someone would ask", "answer": "Clear, helpful answer (2-4 sentences)"}},
    ... 4-6 items
  ],
  "key_takeaways": ["4-6 one-sentence takeaways"],
  "citations": [],
  "related_posts": [
    {{"slug": "related-slug", "title": "Related Article Title"}},
    ... 2-4 related topics from the provided list
  ]
}}

ARTICLE STRUCTURE:
1. Quick Answer (2-3 sentences — give the answer immediately)
2. What the Research Says (reference studies by **Journal Name (Year)** format in bold — we auto-link citations)
3. Why This Matters (practical implications — expand with real detail)
4. What You Can Do (actionable, specific advice — at least 4 bullet points)
5. The Bottom Line (2-3 sentence summary)
6. FAQ (4-6 questions with detailed 2-4 sentence answers)

DO NOT include a "## Related Posts" section in the body — we render that from the related_posts array.
DO NOT include a "## References" or "## Citations" section in the body — we render that from the citations array.
The body should END after the FAQ section. Nothing else after that.

CITATION RULES:
- Leave the citations array EMPTY — we auto-populate it from your body text.
- When referencing a study in the body, use this format: **Journal Name (Year)** — e.g., "According to **Nutrients (2024)**, ..."
- Only reference studies that DIRECTLY relate to the article topic.
- If a provided study is about general nutrition policy and the article is about AI apps, DO NOT reference it.
- If NONE of the provided studies are relevant, write from established medical consensus — no fake references.
- It is better to have 0 study references than to force irrelevant ones.

CONTENT QUALITY RULES:
- MINIMUM 1000 words in the body — this is a HARD requirement. Aim for 1200-1500 words.
- Each section should be thorough: 150-300 words per section.
- FAQ answers should be 2-4 sentences each, not one-liners.
- Every section should have real, specific information — no filler.
- For app/product comparisons: focus on factual features, pricing, pros/cons.
- For health topics: be specific about mechanisms, dosages, timing when relevant.
- Include a CTA: "Have a specific question? Ask WIHY for a personalized answer → https://wihy.ai"
- Do NOT pad with generic health advice unrelated to the topic."""


async def _call_openai(
    system: str, user_prompt: str, http: httpx.AsyncClient
) -> Optional[str]:
    """Call OpenAI GPT-4o with JSON mode."""
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
                "max_tokens": 8192,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=90.0,
        )
        if r.status_code != 200:
            logger.error("OpenAI error: %s", r.text[:200])
            return None
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error("OpenAI error: %s", e)
        return None


def _parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from Gemini response, handling markdown fences and truncation."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to fix common issues: unescaped newlines in strings, truncated JSON
    # Replace literal newlines inside string values
    fixed = re.sub(r'(?<=": ")(.*?)(?="[,\}])', lambda m: m.group(0).replace('\n', '\\n'), cleaned, flags=re.DOTALL)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Try closing truncated JSON
    bracket_count = cleaned.count('{') - cleaned.count('}')
    brace_count = cleaned.count('[') - cleaned.count(']')
    if bracket_count > 0 or brace_count > 0:
        # Truncate to last complete value, close brackets
        # Find last complete key-value by looking for last '"}' or '"]'
        last_good = max(cleaned.rfind('"}'), cleaned.rfind('"]'), cleaned.rfind('}'))
        if last_good > 0:
            attempt = cleaned[:last_good + 1]
            attempt += ']' * brace_count + '}' * bracket_count
            try:
                return json.loads(attempt)
            except json.JSONDecodeError:
                pass

    logger.error("JSON parse error after all repair attempts\nText: %s", cleaned[:300])
    return None


async def generate_post(
    keyword: Dict[str, Any],
    related_slugs: List[str],
    http: httpx.AsyncClient,
) -> Optional[Dict[str, Any]]:
    """Generate a single blog post: fetch research FIRST, then write with Gemini."""
    slug = keyword["slug"]
    topic = keyword.get("topic_slug", "nutrition")
    intent = keyword.get("intent", "")
    question = keyword.get("keyword", slug.replace("-", " "))

    # ── Step 1: Fetch research only for health/science topics ──────────
    # App searches, comparisons, reviews don't need PubMed citations
    _RESEARCH_TOPICS = {
        "nutrition", "supplements", "gut-health", "heart-health",
        "sugar-and-blood-health", "processed-foods", "fasting",
        "alcohol-and-health", "protein-and-muscle", "hydration",
        "immune-health", "longevity", "hormones", "brain-health",
        "fitness", "mental-health", "sleep", "wellness",
    }
    needs_research = (
        topic in _RESEARCH_TOPICS
        and intent not in {"comparisons", "reviews", "best_of", "pricing"}
        and not any(w in question.lower() for w in ["app", "tracker", "scanner", "planner", "tool", "vs"])
    )

    articles = []
    fact_check = None
    if needs_research:
        search_query = _build_pubmed_query(question)
        logger.info("  PubMed query: '%s'", search_query[:60])
        # Run Fact Check API and Research API in parallel
        fc_task = asyncio.create_task(_fetch_fact_check(question, http))
        res_task = asyncio.create_task(_fetch_research(search_query, http))
        fact_check, articles = await fc_task, await res_task
    else:
        logger.info("  Skipping research (non-health/app topic)")

    # Build research context — combine Fact Check verdict + PubMed articles
    research_block = ""
    if fact_check or articles:
        lines = []

        # Fact Check evidence summary (pre-analyzed from 48M+ records)
        if fact_check:
            verdict = fact_check.get("verdict", "")
            grade = fact_check.get("evidence_grade", "")
            quick = fact_check.get("quick_answer", "")
            answer = fact_check.get("answer", {})
            what_studies = answer.get("what_studies_show", "")
            studies_count = answer.get("studies_analyzed", 0)
            study_summary = answer.get("study_type_summary", "")
            breakdown = answer.get("evidence_breakdown", {})

            lines.append("EVIDENCE SUMMARY (from 48M+ peer-reviewed records):")
            lines.append(f"  Topic: {question}")
            lines.append(f"  Verdict: {verdict}")
            lines.append(f"  Evidence Grade: {grade}")
            lines.append(f"  Studies Analyzed: {studies_count} ({study_summary})")
            if breakdown:
                lines.append(
                    f"  Evidence Breakdown: {breakdown.get('supporting', 0)} supporting, "
                    f"{breakdown.get('opposing', 0)} opposing, "
                    f"{breakdown.get('mixed', 0)} mixed"
                )
            lines.append(f"  Summary: {quick}")
            if what_studies:
                lines.append(f"  What Studies Show: {what_studies}")
            lines.append("")

            # Key findings with real journal citations
            key_findings = fact_check.get("key_findings", [])
            if key_findings:
                lines.append("KEY FINDINGS (cite these — they are REAL peer-reviewed studies):")
                for j, f in enumerate(key_findings, 1):
                    journal = f.get("journal", "")
                    year = f.get("year", "")
                    finding = f.get("finding", "")
                    study_type = f.get("studyType", "")
                    link = f.get("link", "")
                    pmcid = f.get("pmcid", "")
                    lines.append(
                        f'{j}. {finding}'
                        f'\n   — {journal} ({year}) [{study_type}]'
                        f'{f" [PMCID: {pmcid}]" if pmcid else ""}'
                        f'{f" {link}" if link else ""}'
                    )
                lines.append("")

            # Fact Check sources as additional citations
            fc_sources = fact_check.get("sources", [])
            if fc_sources:
                lines.append("ADDITIONAL SOURCES:")
                for s in fc_sources[:10]:
                    src_url = s.get("url", "")
                    url_part = f" {src_url}" if src_url else ""
                    lines.append(
                        f'  - {s.get("name", "")} ({s.get("year", "")})'
                        f' [{s.get("study_type", "")}]'
                        f'{url_part}'
                    )
                lines.append("")

        # PubMed articles (supplement Fact Check findings)
        if articles:
            lines.append("PUBMED ARTICLES (additional studies — only cite those DIRECTLY relevant):")
            for i, a in enumerate(articles, 1):
                lines.append(
                    f'{i}. "{a["title"]}" — {a["journal"]} ({a["year"]})'
                    f'  [PMID: {a["pmid"]}] {a["url"]}'
                )
            lines.append("")

        lines.append("REMINDER: Use the verdict and key findings to ground your article. Only cite studies that DIRECTLY relate to the topic. Do NOT hallucinate citations.")
        research_block = "\n".join(lines)
    else:
        research_block = "No research citations needed for this topic. Write from practical knowledge and expertise. Do NOT reference any studies or journals."

    system = SYSTEM_PROMPT.format(slug=slug, topic_slug=topic)

    related_context = ""
    if related_slugs:
        related_context = f"\n\nEXISTING ARTICLES (use for related_posts linking):\n{', '.join(related_slugs[:30])}"

    # Topics that are about apps/tools — prompt should mention WIHY
    _APP_TOPICS = {"health-apps", "food-scanning", "meal-planning"}
    _APP_INTENTS = {"comparisons", "reviews", "best_of"}
    is_app_keyword = (
        topic in _APP_TOPICS
        or intent in _APP_INTENTS
        or any(w in question.lower() for w in ["app", "tracker", "scanner", "planner", "tool"])
    )

    wihy_cta = ""
    if is_app_keyword:
        wihy_cta = (
            "\n\nWIHY PRODUCT CONTEXT (mention naturally, don't force):\n"
            "WIHY (What Is Healthy for You) is an AI-powered health platform at wihy.ai that offers:\n"
            "- AI meal planning with personalized nutrition\n"
            "- Food scanning (barcode + photo) with ingredient analysis\n"
            "- AI nutritionist chat for health questions\n"
            "- Fitness program generation\n"
            "Mention WIHY where it fits naturally in the article. Include a link: https://wihy.ai"
        )

    user_msg = (
        f'Write a blog post answering: "{question}"\n\n'
        f'IMPORTANT: Your article body MUST be at least 1000 words. Go deep — readers want thorough, specific answers.\n\n'
        f'{research_block}{related_context}{wihy_cta}'
    )

    # ── Step 2: Generate with OpenAI GPT-4o ──────────────────────────────
    raw = await _call_openai(system, user_msg, http)
    if not raw:
        return None

    post = _parse_json(raw)
    if not post:
        return None

    # ── Step 3: Enrich & normalize ───────────────────────────────────────
    route = _route_base(topic, intent)
    post["slug"] = slug
    post.setdefault("topic_slug", topic)
    post["route_base"] = route
    post["route_path"] = f"{route}/{slug}"
    post.setdefault("author", "Kortney")
    post["brand"] = BRAND
    post["created_at"] = datetime.now(timezone.utc).isoformat()
    post["model"] = MODEL

    body = post.get("body", "")
    post["word_count"] = len(body.split()) if body else 0
    post.setdefault(
        "hero_image",
        f"{BRAND_CFG['image_url_prefix']}/{slug}-hero.jpg",
    )

    # Auto-populate citations by matching journal+year references in the body
    # Merge Fact Check sources into articles list for citation matching
    all_articles = list(articles)
    if fact_check:
        for f in fact_check.get("key_findings", []):
            if f.get("journal") and f.get("year"):
                all_articles.append({
                    "title": f.get("finding", ""),
                    "journal": f["journal"],
                    "year": f["year"],
                    "pmid": "",
                    "pmcid": f.get("pmcid", ""),
                    "url": f.get("link", ""),
                })
        for s in fact_check.get("sources", []):
            if s.get("name") and s.get("year"):
                all_articles.append({
                    "title": "",
                    "journal": s["name"],
                    "year": s["year"],
                    "pmid": "",
                    "pmcid": s.get("id", ""),
                    "url": s.get("url", ""),
                })
    citations = []
    if all_articles and body:
        body_lower = body.lower()
        for a in all_articles:
            journal = a.get("journal", "").strip()
            year = str(a.get("year", ""))
            if not journal or not year:
                continue
            # Build multiple journal name variants to search for
            journal_lower = journal.lower()
            # Strip parenthetical suffixes: "Advances in nutrition (Bethesda, Md.)" -> "advances in nutrition"
            journal_base = re.split(r"\s*[\(:]", journal_lower)[0].strip()
            # Try matching: full name, base name, or first 2+ meaningful words
            variants = {journal_lower, journal_base}
            # Short name: first word if distinctive (e.g., "nutrients", "bmj")
            first_word = journal_base.split()[0] if journal_base else ""
            if len(first_word) >= 3 and first_word not in {"the", "and", "for", "new", "international"}:
                variants.add(first_word)
            # Check if any variant + year appears in body
            matched = False
            for v in variants:
                if len(v) >= 3 and v in body_lower and year in body:
                    matched = True
                    break
            if matched:
                citations.append({
                    "title": a["title"],
                    "journal": journal,
                    "year": a["year"],
                    "url": a["url"],
                })
    if citations:
        logger.info("  Auto-matched %d citations from body references", len(citations))
    post["citations"] = citations

    # If body admits no relevant studies found, clear citations
    body_lower = body.lower()
    if any(phrase in body_lower for phrase in [
        "no direct studies", "no specific studies", "no relevant studies",
        "no studies directly", "none of the provided studies",
    ]):
        if post.get("citations"):
            logger.info("  Body says no relevant studies — clearing %d citations", len(post["citations"]))
            post["citations"] = []

    # ── Hallucinated citation scrubber ───────────────────────────────────
    # Find all **Journal Name (Year)** references in body and strip any
    # that don't match a real PubMed article we fetched or Fact Check finding
    if all_articles and body:
        known_journals = set()
        for a in all_articles:
            j = a.get("journal", "").strip().lower()
            if j:
                known_journals.add(j)
                known_journals.add(re.split(r"\s*[\(:]", j)[0].strip())
        # Find bold journal references: **Something (2024)**
        ref_pattern = re.compile(r'\*\*([^*]+?)\s*\((\d{4})\)\*\*')
        hallucinated = []
        for m in ref_pattern.finditer(body):
            ref_name = m.group(1).strip().lower()
            ref_year = m.group(2)
            # Check if this matches any known PubMed journal
            matched = False
            for kj in known_journals:
                if kj in ref_name or ref_name in kj:
                    matched = True
                    break
                # Also check first distinctive word
                first = kj.split()[0] if kj else ""
                if len(first) >= 4 and first in ref_name:
                    matched = True
                    break
            if not matched:
                hallucinated.append(m.group(0))
        if hallucinated:
            logger.warning("  Stripping %d hallucinated reference(s): %s",
                          len(hallucinated), ", ".join(hallucinated[:3]))
            for h in hallucinated:
                # Replace **Journal (Year)** with just the text without bold
                plain = h.replace("**", "")
                body = body.replace(h, plain)
            post["body"] = body

    # ── Strip trailing ## Related Posts / ## References from body ────────
    body = post.get("body", "")
    # Strip ## Related Posts section and parse into related_posts array
    rp_match = re.search(r'\n## Related Posts\b.*', body, re.DOTALL | re.IGNORECASE)
    if rp_match:
        rp_block = rp_match.group(0)
        body = body[:rp_match.start()].rstrip()
        # Parse JSON objects from the related posts block
        if not post.get("related_posts"):
            parsed_rp = []
            for m in re.finditer(r'\{\s*"slug"\s*:\s*"([^"]+)"\s*,\s*"title"\s*:\s*"([^"]+)"\s*\}', rp_block):
                parsed_rp.append({"slug": m.group(1), "title": m.group(2)})
            if parsed_rp:
                post["related_posts"] = parsed_rp
                logger.info("  Extracted %d related_posts from body", len(parsed_rp))

    # Strip ## References / ## Citations section (rendered from citations array)
    for heading in (r'## References', r'## Citations', r'## Sources'):
        ref_match = re.search(rf'\n{heading}\b.*', body, re.DOTALL | re.IGNORECASE)
        if ref_match:
            body = body[:ref_match.start()].rstrip()
            logger.info("  Stripped '%s' section from body", heading.replace(r'\b', ''))
    post["body"] = body

    # Ensure tags
    post.setdefault("tags", _infer_tags(post))

    return post


def _infer_tags(post: Dict[str, Any]) -> List[str]:
    """Generate tags from post content."""
    tags = []
    text = f"{post.get('title', '')} {post.get('keyword', '')} {post.get('meta_description', '')}".lower()
    tag_kw = {
        "weight-loss": ["weight loss", "lose weight", "fat loss"],
        "heart-health": ["heart", "cardiovascular", "cholesterol"],
        "mental-health": ["depression", "anxiety", "mental health", "mood"],
        "gut-health": ["gut", "microbiome", "probiotic"],
        "sleep": ["sleep", "insomnia", "circadian"],
        "nutrition": ["nutrition", "nutrient", "vitamin"],
        "fitness": ["exercise", "workout", "training"],
        "research-backed": ["study", "research", "evidence"],
    }
    for tag, kws in tag_kw.items():
        if any(kw in text for kw in kws):
            tags.append(tag)
    if "research-backed" not in tags:
        tags.append("research-backed")
    return tags[:5]


# ── Internal linking ──────────────────────────────────────────────────────────

_TOPIC_ADJACENCY = {
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


def _fetch_published_index() -> List[Dict[str, Any]]:
    """Fetch the published blog index from GCS for internal linking."""
    url = "https://storage.googleapis.com/wihy-web-assets/blog/posts/index.json"
    try:
        r = httpx.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("posts", [])
    except Exception as e:
        logger.warning("Could not fetch published index for linking: %s", e)
    return []


def _inject_internal_links(post: Dict[str, Any], published: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Inject internal links into a post body and update related_posts."""
    body = post.get("body", "")
    slug = post.get("slug", "")
    topic = post.get("topic_slug", "nutrition")

    if not body or not published:
        return post

    # Find related posts by topic proximity
    adjacent = set(_TOPIC_ADJACENCY.get(topic, []))
    same_topic = [p for p in published if p.get("topic_slug") == topic and p["slug"] != slug]
    adj_topic = [p for p in published if p.get("topic_slug") in adjacent and p["slug"] != slug]

    related = (same_topic + adj_topic)[:5]
    if not related:
        return post

    # Build "Keep Reading" section
    lines = ["\n\n---\n\n### Keep Reading\n"]
    for p in related[:5]:
        route_path = p.get("route_path", f"/blog/{p['slug']}")
        title = p.get("title", p["slug"].replace("-", " ").title())
        lines.append(f"- [{title}]({route_path})")
    keep_reading = "\n".join(lines) + "\n"

    # Insert before FAQ if present, else append
    faq_match = re.search(r'\n## (?:FAQ|Frequently Asked Questions)\b', body, re.IGNORECASE)
    if faq_match:
        body = body[:faq_match.start()] + keep_reading + body[faq_match.start():]
    else:
        body = body.rstrip() + keep_reading

    post["body"] = body

    # Update related_posts array
    post["related_posts"] = [
        {
            "slug": p["slug"],
            "title": p.get("title", p["slug"].replace("-", " ").title()),
            "route_path": p.get("route_path", f"/blog/{p['slug']}"),
        }
        for p in related[:5]
    ]

    return post


# ── Batch Runner ──────────────────────────────────────────────────────────────

async def run_batch(
    limit: Optional[int] = None,
    topic_filter: Optional[str] = None,
    slug_filter: Optional[str] = None,
    keywords_file: Optional[str] = None,
    dry_run: bool = False,
):
    """Generate and publish posts in batches."""
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

    if not dry_run and not OPENAI_API_KEY:
        logger.error("Set OPENAI_API_KEY environment variable")
        return

    logger.info("Generating %d posts with %s...", len(keywords), MODEL)

    # All slugs for internal linking
    all_slugs = [k["slug"] for k in _load_keywords(kw_path)]
    all_slugs.extend(completed)

    # Fetch existing published posts for internal linking
    published_posts = _fetch_published_index()

    success = 0
    errors = 0

    async with httpx.AsyncClient(timeout=90.0) as http:
        for i, kw in enumerate(keywords, 1):
            slug = kw["slug"]
            route = _route_base(kw.get("topic_slug", "nutrition"), kw.get("intent", ""))
            logger.info("[%d/%d] %s → %s/%s", i, len(keywords), kw.get("keyword", slug), route, slug)

            if dry_run:
                print(f"  DRY RUN: {slug} ({kw.get('topic_slug', '?')}) -> {route}/{slug}")
                continue

            t0 = time.time()
            post = await generate_post(kw, all_slugs, http)
            if not post:
                errors += 1
                continue

            elapsed = time.time() - t0
            logger.info("  Generated in %.1fs (%d words, %d citations)",
                        elapsed, post.get("word_count", 0), len(post.get("citations", [])))

            # Inject internal links to related published posts
            post = _inject_internal_links(post, published_posts)

            # Generate hero image via Shania
            topic_text = post.get("title", slug.replace("-", " "))
            hero_url = await generate_and_upload_hero_image(slug, topic_text, BRAND)
            if hero_url:
                post["hero_image"] = hero_url

            # Publish to GCS
            if publish_post(post, brand=BRAND):
                completed.add(slug)
                _save_progress(completed)
                success += 1
                logger.info("  ✓ Published: %s/%s", route, slug)

                # Post-publish hooks: IndexNow + social media
                try:
                    hook_results = await on_post_published(post)
                    parts = []
                    if hook_results.get("indexnow"):
                        parts.append("IndexNow ✓")
                    if hook_results.get("social"):
                        parts.append("Social ✓")
                    if parts:
                        logger.info("  ↳ %s", " | ".join(parts))
                except Exception as hook_err:
                    logger.debug("  ↳ Post-publish hooks failed: %s", hook_err)
            else:
                errors += 1
                logger.error("  ✗ Upload failed: %s", slug)

            # Rate limit: Gemini is generous but research API needs spacing
            if i < len(keywords):
                await asyncio.sleep(1.5)

    logger.info("Done: %d published, %d errors, %d total completed", success, errors, len(completed))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate WIHY Insights posts with OpenAI + Research API")
    parser.add_argument("--limit", type=int, help="Max posts to generate")
    parser.add_argument("--topic", help="Filter by topic_slug")
    parser.add_argument("--slug", help="Generate a single post by slug")
    parser.add_argument("--keywords", help="Path to keywords JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without generating")
    parser.add_argument("--status", action="store_true", help="Show progress stats and route breakdown")
    args = parser.parse_args()

    if args.status:
        kw_path = Path(args.keywords) if args.keywords else None
        completed = _load_progress()
        keywords = _load_keywords(kw_path)
        remaining = [k for k in keywords if k["slug"] not in completed]
        print(f"Total keywords: {len(keywords)}")
        print(f"Completed: {len(completed)}")
        print(f"Remaining: {len(remaining)}")

        # Route breakdown
        route_counts = Counter(
            _route_base(k.get("topic_slug", "nutrition"), k.get("intent", ""))
            for k in remaining
        )
        print(f"\nRouting:")
        for r, c in route_counts.most_common():
            print(f"  {r}/*: {c}")

        tc = Counter(k.get("topic_slug", "?") for k in remaining)
        print("\nRemaining by topic:")
        for t, c in tc.most_common():
            print(f"  {t}: {c}")
        return

    asyncio.run(run_batch(
        limit=args.limit,
        topic_filter=args.topic,
        slug_filter=args.slug,
        keywords_file=args.keywords,
        dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
