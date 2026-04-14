"""
labat/services/blog_writer.py — Kortney blog writer.

Kortney is part of the Otaku Master. He writes full, substantive blog
articles for WIHY and Community Groceries. He uses:

1. RAG (WIHY vector store) for grounded research and citations
2. Alex's keyword engine for SEO keyword targeting
3. GPT-4o for heavy article writing
4. The fine-tuned model (CHAT_MODEL) to refine voice / tone
5. Shania (Imagen 4.0) for hero image generation
6. GCS for static publishing (JSON + images)

Pipeline:  topic → RAG research → Alex SEO keywords → GPT-4o article
           → fine-tuned voice pass → Shania hero image → GCS publish
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import httpx
import openai
from google.cloud import storage

from src.shared.config.models import CHAT_MODEL
from src.labat.brands import normalize_brand, BRAND_PAGE_IDS
from src.labat.services.keyword_store import get_keywords_for_topic
from src.labat.services.strategy_rules import build_strategy_block

logger = logging.getLogger("kortney.blog_writer")

# ── Config ──────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("WIHY_OPENAI_API_KEY") or ""
FINE_TUNED_MODEL = os.getenv("WIHY_FINE_TUNED_MODEL") or CHAT_MODEL
WRITER_MODEL = "gpt-4o"  # heavy lifting model for long-form
WIHY_ASK = "https://ml.wihy.ai/ask"

# GCS buckets per brand
GCS_BUCKETS = {
    "wihy": "wihy-web-assets",
    "communitygroceries": "cg-web-assets",
}

# Blog paths in bucket
BLOG_POSTS_PREFIX = "blog/posts"
BLOG_IMAGES_PREFIX = "images/blog"
BLOG_INDEX_FILE = "blog/posts/index.json"

_openai_client: openai.AsyncOpenAI | None = None


def _get_openai() -> openai.AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


# ── Brand Prompts ───────────────────────────────────────────────────────────

KORTNEY_WIHY_SYSTEM = """You are Kortney, the voice behind WIHY's blog.
Bold, science-backed, slightly provocative. You expose what the food industry hides.
Every claim backed by real data from WIHY's 48M+ research articles.
"The Information Exists. We Just Made It Usable." — that's your mission.
Hard truths first. Never preachy, always evidence-first.
Speak like a real person who did the research and is genuinely fired up about what they found.

STRUCTURE (every article):
- A punchy title that stops scrolling
- Opening hook (2-3 sentences that grab attention)
- 4-6 sections with H2 headings
- Real data and citations woven naturally into the text
- A "Why This Matters" section near the end
- A conclusion with a clear takeaway or CTA
- Total: 1200-2000 words

VOICE:
- First person plural ("we found", "here's what the data shows")
- Short paragraphs, punchy sentences mixed with longer explanatory ones
- Occasional rhetorical questions
- "Honestly" / "here's the thing" / "wild, right?" — natural interjections
- NO "As an AI" / "It's important to note" / "In conclusion"
- NO generic wellness fluff — every sentence teaches something specific
"""

KORTNEY_CG_SYSTEM = """You are Kortney, writing for Community Groceries.
Warm, purposeful, community-driven — like a neighbor who genuinely cares about your family.
You help real families eat better without breaking the bank.
Focus on practical solutions: meal prep, budget tips, kid-friendly recipes, seasonal shopping.
Every article should make someone feel supported, inspired, or equipped to feed their family better.
CG is about TOGETHERNESS and SOLUTIONS — never exposés or industry callouts (that's WIHY's job).

STRUCTURE (every article):
- A warm, inviting title that speaks to parents
- Opening that connects emotionally (shared struggle, relatable moment)
- 4-6 sections with H2 headings
- Practical tips, specific dollar amounts, real product suggestions
- A "Try This Week" actionable section
- Total: 1000-1600 words

VOICE:
- Second person ("you", "your family") — speaking directly to parents
- Warm and encouraging, never judgy about food choices
- Specific and actionable — exact grocery lists, dollar amounts, time estimates
- "Trust me on this one" / "game-changer" / "our family does this every Sunday"
- NO "As an AI" / "It's important to note" / "In conclusion"
- NO food industry exposés — that's WIHY territory
"""

# Voice refinement via fine-tuned model
KORTNEY_VOICE_REFINE = """You are refining a blog article into Kortney's authentic voice.
Keep ALL the facts, structure, and citations intact. Only adjust:
- Sentence rhythm: mix short punchy lines with longer flowing ones
- Personality: add natural interjections ("honestly", "here's the thing", "wild, right?")
- Remove any remaining AI-isms ("It's important to note", "In conclusion", "As mentioned")
- Make it sound like someone who genuinely cares about this topic wrote it at midnight because they couldn't stop thinking about it
- Keep all H2 headings and markdown formatting exactly as-is
- Do NOT add or remove sections. Do NOT change the facts. Just warm up the voice.
"""


# ── Topic Taxonomy (10 launch topics) ────────────────────────────────────────

TOPIC_TAXONOMY = [
    {"slug": "nutrition", "label": "Nutrition",
     "description": "Foundational nutrition articles that help you eat with more clarity and less noise."},
    {"slug": "sugar-and-blood-health", "label": "Sugar and Blood Health",
     "description": "Guides for reducing added sugar, improving meal balance, and understanding blood-sugar-friendly habits."},
    {"slug": "processed-foods", "label": "Processed Foods",
     "description": "How to identify ultra-processed foods quickly and make better grocery decisions without overcomplicating life."},
    {"slug": "protein-and-muscle", "label": "Protein and Muscle",
     "description": "Protein targets, meal structure, and recovery habits for strength, satiety, and preserving lean mass."},
    {"slug": "hydration", "label": "Hydration",
     "description": "Hydration guidance, myths, and practical ways to build better fluid habits."},
    {"slug": "fasting", "label": "Fasting",
     "description": "Articles on fasting patterns, meal timing, and what matters most before trying them."},
    {"slug": "supplements", "label": "Supplements",
     "description": "Evidence-based supplement reviews so you can separate useful tools from expensive distractions."},
    {"slug": "alcohol-and-health", "label": "Alcohol and Health",
     "description": "Articles on alcohol, recovery, sleep, and metabolic tradeoffs."},
    {"slug": "food-swaps", "label": "Food Swaps",
     "description": "Realistic alternatives that improve nutrition without making meals feel restrictive."},
    {"slug": "weight-management", "label": "Weight Management",
     "description": "Evidence-guided articles on calories, appetite, meal structure, and sustainable fat-loss habits."},
]


# ── Editorial Queue ─────────────────────────────────────────────────────────

EDITORIAL_QUEUE: List[Dict[str, str]] = [
    # ── Nutrition ────────────────────────────────────────────────────────
    {"slug": "seed-oils-truth", "brand": "wihy", "topic_slug": "nutrition",
     "topic": "Seed oils: are they really toxic? What 30 years of research actually says."},
    {"slug": "gut-microbiome-mental-health", "brand": "wihy", "topic_slug": "nutrition",
     "topic": "Your gut bacteria are talking to your brain. Here's what the science says about the gut-brain axis."},
    {"slug": "reading-nutrition-labels-guide", "brand": "wihy", "topic_slug": "nutrition",
     "topic": "How to actually read a nutrition label — the 5 things that matter and everything you can ignore."},
    {"slug": "anti-inflammatory-foods-guide", "brand": "wihy", "topic_slug": "nutrition",
     "topic": "Anti-inflammatory eating: which foods actually reduce inflammation according to research."},

    # ── Sugar and Blood Health ──────────────────────────────────────────
    {"slug": "hidden-sugar-in-cereal", "brand": "wihy", "topic_slug": "sugar-and-blood-health",
     "topic": "How much hidden sugar is really in your 'healthy' breakfast cereal? Breaking down the worst offenders."},
    {"slug": "added-sugar-healthy-swaps", "brand": "wihy", "topic_slug": "sugar-and-blood-health",
     "topic": "5 'healthy' foods with more added sugar than a candy bar — and what to eat instead."},
    {"slug": "blood-sugar-after-meals", "brand": "wihy", "topic_slug": "sugar-and-blood-health",
     "topic": "What actually happens to your blood sugar after you eat — and why the order of food matters."},

    # ── Processed Foods ─────────────────────────────────────────────────
    {"slug": "ultra-processed-foods-cancer-risk", "brand": "wihy", "topic_slug": "processed-foods",
     "topic": "Ultra-processed foods and cancer risk: what the research from 48M+ articles actually shows."},
    {"slug": "natural-flavors-exposed", "brand": "wihy", "topic_slug": "processed-foods",
     "topic": "What 'natural flavors' actually means on a food label — and why it should concern you."},
    {"slug": "emulsifiers-gut-health", "brand": "wihy", "topic_slug": "processed-foods",
     "topic": "Emulsifiers in your food: what research says about these common additives and your gut health."},

    # ── Protein and Muscle ──────────────────────────────────────────────
    {"slug": "protein-needs-debunked", "brand": "wihy", "topic_slug": "protein-and-muscle",
     "topic": "How much protein do you actually need? The supplement industry doesn't want you to know the real number."},
    {"slug": "complete-vs-incomplete-protein", "brand": "wihy", "topic_slug": "protein-and-muscle",
     "topic": "Complete vs incomplete protein: does it actually matter? What the science says about protein combining."},
    {"slug": "protein-timing-myth", "brand": "wihy", "topic_slug": "protein-and-muscle",
     "topic": "The protein timing window myth: do you really need to eat protein within 30 minutes of working out?"},

    # ── Hydration ───────────────────────────────────────────────────────
    {"slug": "how-much-water-actually-need", "brand": "wihy", "topic_slug": "hydration",
     "topic": "How much water do you actually need? The 8-glasses-a-day rule and what research really shows."},
    {"slug": "electrolytes-myth-vs-reality", "brand": "wihy", "topic_slug": "hydration",
     "topic": "Electrolyte drinks: when you actually need them vs when you're just paying for sugar water."},
    {"slug": "dehydration-signs-performance", "brand": "wihy", "topic_slug": "hydration",
     "topic": "How even mild dehydration tanks your focus, mood, and workout performance — and the signs to watch for."},

    # ── Fasting ─────────────────────────────────────────────────────────
    {"slug": "intermittent-fasting-beginners-guide", "brand": "wihy", "topic_slug": "fasting",
     "topic": "Intermittent fasting for beginners: what the research says about the most popular patterns."},
    {"slug": "16-8-fasting-research", "brand": "wihy", "topic_slug": "fasting",
     "topic": "16:8 fasting — does it actually work for fat loss? What 10 years of studies show."},
    {"slug": "fasting-and-muscle-loss", "brand": "wihy", "topic_slug": "fasting",
     "topic": "Does fasting cause muscle loss? What the research says about preserving lean mass while fasting."},

    # ── Supplements ─────────────────────────────────────────────────────
    {"slug": "multivitamin-waste-of-money", "brand": "wihy", "topic_slug": "supplements",
     "topic": "Is your multivitamin doing anything? The studies that changed how we think about supplements."},
    {"slug": "creatine-beyond-gym", "brand": "wihy", "topic_slug": "supplements",
     "topic": "Creatine beyond the gym: what research shows about brain health, aging, and recovery."},
    {"slug": "vitamin-d-deficiency-guide", "brand": "wihy", "topic_slug": "supplements",
     "topic": "Vitamin D deficiency is more common than you think — here's what the data shows and when to supplement."},

    # ── Alcohol and Health ──────────────────────────────────────────────
    {"slug": "alcohol-and-sleep-research", "brand": "wihy", "topic_slug": "alcohol-and-health",
     "topic": "That nightcap is ruining your sleep: what research shows about alcohol and sleep quality."},
    {"slug": "no-alcohol-30-days", "brand": "wihy", "topic_slug": "alcohol-and-health",
     "topic": "What actually happens to your body when you quit alcohol for 30 days — according to the data."},
    {"slug": "alcohol-calories-metabolism", "brand": "wihy", "topic_slug": "alcohol-and-health",
     "topic": "How alcohol affects your metabolism, recovery, and body composition — the numbers nobody shares."},

    # ── Food Swaps ──────────────────────────────────────────────────────
    {"slug": "healthy-snack-swaps", "brand": "wihy", "topic_slug": "food-swaps",
     "topic": "10 processed snack swaps that actually taste good — real alternatives, not cardboard."},
    {"slug": "cooking-oil-swap-guide", "brand": "wihy", "topic_slug": "food-swaps",
     "topic": "The cooking oil swap guide: which oils to use for what, and which ones to stop buying."},
    {"slug": "dairy-alternatives-compared", "brand": "wihy", "topic_slug": "food-swaps",
     "topic": "Oat, almond, soy, coconut: dairy alternatives ranked by nutrition, taste, and what the research says."},

    # ── Weight Management ───────────────────────────────────────────────
    {"slug": "calorie-counting-does-it-work", "brand": "wihy", "topic_slug": "weight-management",
     "topic": "Does calorie counting actually work? What long-term studies say about tracking for fat loss."},
    {"slug": "sustainable-fat-loss-habits", "brand": "wihy", "topic_slug": "weight-management",
     "topic": "The 5 fat loss habits that actually stick — what research says about sustainable weight management."},
    {"slug": "appetite-hormones-explained", "brand": "wihy", "topic_slug": "weight-management",
     "topic": "Why you're always hungry: ghrelin, leptin, and the hormones controlling your appetite explained."},

    # ── Community Groceries articles ────────────────────────────────────
    {"slug": "budget-meal-prep-under-75", "brand": "communitygroceries", "topic_slug": "nutrition",
     "topic": "Weekly meal prep for a family of four under $75 — real plans, real groceries."},
    {"slug": "healthy-school-lunches-kids-eat", "brand": "communitygroceries", "topic_slug": "nutrition",
     "topic": "10 school lunch ideas kids will actually eat (and parents feel good about)."},
    {"slug": "seasonal-produce-save-money", "brand": "communitygroceries", "topic_slug": "nutrition",
     "topic": "How buying seasonal produce can save your family $200/month — a monthly guide."},
    {"slug": "weeknight-dinners-30-minutes", "brand": "communitygroceries", "topic_slug": "nutrition",
     "topic": "15 weeknight dinners that take 30 minutes or less — from real family kitchens."},
    {"slug": "grocery-budget-strategies", "brand": "communitygroceries", "topic_slug": "food-swaps",
     "topic": "Smart grocery shopping: the strategies that actually cut your bill without coupons."},
]


# ── Research via WIHY Ask (RAG) ─────────────────────────────────────────────

async def _query_wihy_research(topic: str) -> Dict[str, Any]:
    """Two-pass RAG query via WIHY Ask — same pattern as Moltbook."""
    payload1 = {
        "message": f"What does science say about {topic}? Provide key findings with specific numbers and data.",
        "session_id": str(uuid.uuid4()),
        "source_site": "kortney_blog",
    }
    payload2 = {
        "message": (
            f"What are the health implications and practical considerations "
            f"regarding {topic}? Include specific studies, percentages, and actionable insights."
        ),
        "session_id": str(uuid.uuid4()),
        "source_site": "kortney_blog",
    }

    async with httpx.AsyncClient() as client:
        try:
            r1 = await client.post(WIHY_ASK, json=payload1, timeout=60)
            data1 = r1.json()
        except Exception as e:
            logger.error("WIHY research pass 1 failed: %s", e)
            data1 = {}
        try:
            r2 = await client.post(WIHY_ASK, json=payload2, timeout=60)
            data2 = r2.json()
        except Exception as e:
            logger.error("WIHY research pass 2 failed: %s", e)
            data2 = {}

    msg1 = (data1.get("message") or "").strip()
    msg2 = (data2.get("message") or "").strip()
    combined = msg1
    if msg2 and len(msg2) > 80 and msg2 not in msg1:
        combined = msg1 + "\n\n---\n" + msg2

    # Dedup citations
    citations = (data1.get("citations") or []) + (data2.get("citations") or [])
    seen = set()
    deduped = []
    for c in citations:
        key = c.get("pmcid") or c.get("title", "")
        if key and key not in seen:
            seen.add(key)
            deduped.append(c)

    return {"research": combined, "citations": deduped}


# ── SEO Keywords via Alex ──────────────────────────────────────────────────

async def _generate_seo_keywords(topic: str, brand: str) -> List[str]:
    """Generate SEO keywords for a topic using Alex's keyword engine (LLM-based).
    
    First checks the keyword store for existing matches, then generates new ones
    via GPT if needed.
    """
    # Check store first
    stored = get_keywords_for_topic(topic, brand=brand, limit=8)
    if len(stored) >= 5:
        logger.info("Found %d stored keywords for '%s'", len(stored), topic[:50])
        return stored

    # Generate via LLM
    brand_desc = (
        "WIHY (health science, food exposure, nutrition research)"
        if brand == "wihy"
        else "Community Groceries (family meals, budget nutrition, meal planning)"
    )
    system = (
        f"You are ALEX, the SEO keyword discovery engine for {brand_desc}. "
        "Given a blog article topic, return ONLY a JSON array of 8-12 target keywords/phrases. "
        "Include: primary keyword, long-tail variants, related search terms. "
        "Optimize for informational search intent — what real people type into Google. "
        "Return ONLY the JSON array, nothing else."
    )
    try:
        client = _get_openai()
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Generate SEO keywords for this blog article topic:\n\n{topic}"},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        keywords = json.loads(text)
        if isinstance(keywords, list):
            logger.info("Alex generated %d SEO keywords for '%s'", len(keywords), topic[:50])
            return [str(k).lower().strip() for k in keywords[:12]]
    except Exception as e:
        logger.error("SEO keyword generation failed: %s", e)

    # Fallback: extract key phrases from topic
    words = re.findall(r'\b\w{4,}\b', topic.lower())
    return list(set(words))[:8]


# ── Article Writing ─────────────────────────────────────────────────────────

async def write_article(slug: str) -> Optional[Dict[str, Any]]:
    """Write a complete blog article for the given slug from the editorial queue."""
    entry = None
    for e in EDITORIAL_QUEUE:
        if e["slug"] == slug:
            entry = e
            break
    if not entry:
        logger.error("Slug '%s' not found in editorial queue", slug)
        return None

    brand = entry["brand"]
    topic = entry["topic"]
    logger.info("KORTNEY: Writing '%s' for %s", slug, brand)

    # Step 1: RAG research
    research = await _query_wihy_research(topic)
    logger.info("RAG research: %d chars, %d citations", len(research["research"]), len(research["citations"]))

    # Step 2: SEO keywords from Alex
    keywords = await _generate_seo_keywords(topic, brand)
    logger.info("SEO keywords: %s", keywords[:6])

    # Step 3: Write article with brand-specific prompt
    system = KORTNEY_WIHY_SYSTEM if brand == "wihy" else KORTNEY_CG_SYSTEM

    # Inject product strategy context so Kortney writes on-brand
    strategy_ctx = build_strategy_block(product=brand)
    if strategy_ctx:
        system += f"\n\nBRAND CONTEXT:\n{strategy_ctx}"

    system += f"\n\nSEO TARGET KEYWORDS (weave these naturally — don't force them):\n{', '.join(keywords)}"

    citations_block = ""
    if research["citations"]:
        cites = []
        for i, c in enumerate(research["citations"][:8], 1):
            title = c.get("title", "Untitled")
            authors = c.get("authors", "")
            year = c.get("year", "")
            pmcid = c.get("pmcid", "")
            cites.append(f"{i}. {title} ({authors}, {year}) [PMCID: {pmcid}]")
        citations_block = "\n\nAVAILABLE CITATIONS (reference these in your article):\n" + "\n".join(cites)

    user_msg = (
        f"Write a complete blog article on this topic:\n\n"
        f"TOPIC: {topic}\n\n"
        f"RESEARCH FROM WIHY KNOWLEDGE BASE:\n{research['research'][:6000]}"
        f"{citations_block}\n\n"
        f"Write the full article in markdown. Include a ## References section at the end "
        f"listing the PubMed citations used."
    )

    try:
        client = _get_openai()
        resp = await client.chat.completions.create(
            model=WRITER_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.75,
            max_tokens=4000,
        )
        article_body = resp.choices[0].message.content.strip()
        logger.info("Draft article: %d chars", len(article_body))
    except Exception as e:
        logger.error("Article generation failed: %s", e)
        return None

    # Step 4: Refine voice via fine-tuned model
    article_body = await _refine_in_kortney_voice(article_body)

    # Step 5: Extract title from first H1/H2 line
    title = topic  # fallback
    for line in article_body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped.lstrip("# ").strip()
            break

    # Step 6: Generate meta description
    meta = await _generate_meta_description(title, topic, brand)

    article = {
        "slug": slug,
        "brand": brand,
        "title": title,
        "topic": topic,
        "topic_slug": entry.get("topic_slug", ""),
        "body": article_body,
        "meta_description": meta,
        "seo_keywords": keywords,
        "citations": research["citations"][:8],
        "author": "Kortney",
        "created_at": datetime.utcnow().isoformat(),
        "word_count": len(article_body.split()),
    }
    return article


async def _refine_in_kortney_voice(raw_article: str) -> str:
    """Pass the article through the fine-tuned model for voice consistency."""
    if not raw_article or len(raw_article) < 200:
        return raw_article
    try:
        client = _get_openai()
        resp = await client.chat.completions.create(
            model=FINE_TUNED_MODEL,
            messages=[
                {"role": "system", "content": KORTNEY_VOICE_REFINE},
                {"role": "user", "content": raw_article},
            ],
            temperature=0.85,
            max_tokens=4000,
        )
        refined = resp.choices[0].message.content.strip()
        if len(refined) > len(raw_article) * 0.5:  # sanity check
            logger.info("Voice refinement: %d → %d chars", len(raw_article), len(refined))
            return refined
        logger.warning("Voice refinement too short, using original")
        return raw_article
    except Exception as e:
        logger.warning("Voice refinement failed, using original: %s", e)
        return raw_article


async def _generate_meta_description(title: str, topic: str, brand: str) -> str:
    """Generate a concise SEO meta description."""
    try:
        client = _get_openai()
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Generate a 150-160 character SEO meta description. No quotes around it."},
                {"role": "user", "content": f"Title: {title}\nTopic: {topic}\nBrand: {brand}"},
            ],
            temperature=0.5,
            max_tokens=100,
        )
        return resp.choices[0].message.content.strip().strip('"')
    except Exception:
        return topic[:155]


# ── Hero Image ──────────────────────────────────────────────────────────────

SHANIA_GRAPHICS_URL = os.getenv(
    "SHANIA_GRAPHICS_URL",
    "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app",
)

async def _generate_hero_image(slug: str, topic: str, brand: str) -> Optional[bytes]:
    """Generate a hero image via Shania (Imagen 4.0)."""
    canonical_brand = normalize_brand(brand, default="")
    if not canonical_brand or canonical_brand not in BRAND_PAGE_IDS:
        logger.error("Hero image generation rejected unknown brand '%s' for slug '%s'", brand, slug)
        return None

    try:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{SHANIA_GRAPHICS_URL}/generate-hero-image",
                json={"topic": topic, "brand": canonical_brand, "slug": slug},
            )
            if resp.status_code != 200:
                logger.error("Shania hero image failed (%d): %s", resp.status_code, resp.text[:300])
                return None

            data = resp.json()

            # If Shania returned a URL, download the image bytes
            if data.get("url"):
                img_resp = await http.get(data["url"], timeout=30)
                if img_resp.status_code == 200:
                    logger.info("Hero image from Shania for '%s' (%d bytes)", slug, len(img_resp.content))
                    return img_resp.content

            # Fallback: Shania returned base64 inline
            if data.get("imageBase64"):
                import base64
                image_bytes = base64.b64decode(data["imageBase64"])
                logger.info("Hero image from Shania (base64) for '%s' (%d bytes)", slug, len(image_bytes))
                return image_bytes

    except Exception as e:
        logger.error("Hero image generation failed for '%s': %s", slug, e)
    return None


# ── GCS Publishing ──────────────────────────────────────────────────────────

def _get_gcs_client():
    return storage.Client()


def _publish_json_to_gcs(bucket_name: str, path: str, data: Any):
    """Upload JSON data to GCS."""
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(
        json.dumps(data, indent=2, default=str),
        content_type="application/json",
    )
    logger.info("Published JSON to gs://%s/%s", bucket_name, path)


def _publish_image_to_gcs(bucket_name: str, path: str, image_bytes: bytes):
    """Upload image to GCS."""
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    logger.info("Published image to gs://%s/%s (%d bytes)", bucket_name, path, len(image_bytes))


async def publish_article(article: Dict[str, Any], hero_bytes: Optional[bytes] = None) -> Dict[str, str]:
    """Publish article JSON and hero image to GCS. Returns public URLs."""
    brand = article["brand"]
    slug = article["slug"]
    bucket_name = GCS_BUCKETS.get(brand, GCS_BUCKETS["wihy"])

    # Publish article JSON
    post_path = f"{BLOG_POSTS_PREFIX}/{slug}.json"
    post_data = {
        "slug": slug,
        "title": article["title"],
        "body": article["body"],
        "meta_description": article.get("meta_description", ""),
        "topic_slug": article.get("topic_slug", ""),
        "seo_keywords": article.get("seo_keywords", []),
        "citations": article.get("citations", []),
        "author": article.get("author", "Kortney"),
        "brand": brand,
        "created_at": article.get("created_at", datetime.utcnow().isoformat()),
        "word_count": article.get("word_count", 0),
    }

    hero_url = ""
    if hero_bytes:
        image_path = f"{BLOG_IMAGES_PREFIX}/{slug}-hero.jpg"
        _publish_image_to_gcs(bucket_name, image_path, hero_bytes)
        hero_url = f"https://storage.googleapis.com/{bucket_name}/{image_path}"

    if hero_url:
        post_data["hero_image"] = hero_url

    _publish_json_to_gcs(bucket_name, post_path, post_data)

    urls = {
        "article": f"https://storage.googleapis.com/{bucket_name}/{post_path}",
        "hero_image": hero_url,
    }
    logger.info("KORTNEY: Published '%s' → %s", slug, urls["article"])
    return urls


def update_blog_index(brand: str):
    """Rebuild the blog index.json listing all published posts for the given brand."""
    bucket_name = GCS_BUCKETS.get(brand, GCS_BUCKETS["wihy"])
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)

    posts = []
    blobs = bucket.list_blobs(prefix=f"{BLOG_POSTS_PREFIX}/")
    for blob in blobs:
        if blob.name.endswith(".json") and "index.json" not in blob.name:
            try:
                content = blob.download_as_text()
                post = json.loads(content)
                posts.append({
                    "slug": post.get("slug", ""),
                    "title": post.get("title", ""),
                    "meta_description": post.get("meta_description", ""),
                    "topic_slug": post.get("topic_slug", ""),
                    "author": post.get("author", "Kortney"),
                    "created_at": post.get("created_at", ""),
                    "hero_image": post.get("hero_image", ""),
                    "word_count": post.get("word_count", 0),
                    "brand": post.get("brand", brand),
                    "page_type": post.get("page_type", "topic"),
                    "route_base": post.get("route_base", "/blog"),
                })
            except Exception as e:
                logger.warning("Failed to read post %s: %s", blob.name, e)

    posts.sort(key=lambda p: p.get("created_at", ""), reverse=True)
    _publish_json_to_gcs(bucket_name, BLOG_INDEX_FILE, {"posts": posts, "count": len(posts)})
    logger.info("Updated blog index for %s: %d posts", brand, len(posts))
    return posts


# ── Main Pipeline ───────────────────────────────────────────────────────────

async def write_and_publish(slug: str, generate_image: bool = True) -> Optional[Dict[str, Any]]:
    """Full pipeline: research → write → refine → image → publish."""
    article = await write_article(slug)
    if not article:
        return None

    hero_bytes = None
    if generate_image:
        hero_bytes = await _generate_hero_image(slug, article["topic"], article["brand"])

    urls = await publish_article(article, hero_bytes)
    update_blog_index(article["brand"])

    return {
        "slug": slug,
        "brand": article["brand"],
        "title": article["title"],
        "word_count": article["word_count"],
        "seo_keywords": article["seo_keywords"],
        "citations_count": len(article.get("citations", [])),
        "urls": urls,
    }


async def write_all_pending(generate_images: bool = True) -> List[Dict[str, Any]]:
    """Write and publish ALL articles in the editorial queue."""
    results = []
    for entry in EDITORIAL_QUEUE:
        slug = entry["slug"]
        logger.info("KORTNEY: Processing %d/%d — %s", len(results) + 1, len(EDITORIAL_QUEUE), slug)
        result = await write_and_publish(slug, generate_image=generate_images)
        if result:
            results.append(result)
        else:
            results.append({"slug": slug, "error": "Failed to write/publish"})
    return results


async def write_unwritten(brand: str = "wihy", generate_images: bool = True) -> List[Dict[str, Any]]:
    """Write only articles that haven't been published yet."""
    # Get already-published slugs from GCS index
    bucket_name = GCS_BUCKETS.get(brand, GCS_BUCKETS["wihy"])
    try:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(BLOG_INDEX_FILE)
        if blob.exists():
            data = json.loads(blob.download_as_text())
            published_slugs = {p.get("slug", "") for p in data.get("posts", [])}
        else:
            published_slugs = set()
    except Exception:
        published_slugs = set()

    # Filter queue to unwritten articles for this brand
    to_write = [
        e for e in EDITORIAL_QUEUE
        if e["brand"] == brand and e["slug"] not in published_slugs
    ]
    logger.info("KORTNEY: %d unwritten articles for %s (of %d total)", len(to_write), brand, len(EDITORIAL_QUEUE))

    results = []
    for i, entry in enumerate(to_write, 1):
        slug = entry["slug"]
        logger.info("KORTNEY: Writing %d/%d — %s", i, len(to_write), slug)
        result = await write_and_publish(slug, generate_image=generate_images)
        if result:
            results.append(result)
        else:
            results.append({"slug": slug, "error": "Failed to write/publish"})
    return results


def patch_existing_articles_topic_slug(brand: str = "wihy") -> List[str]:
    """Patch existing published articles to add topic_slug from the editorial queue."""
    bucket_name = GCS_BUCKETS.get(brand, GCS_BUCKETS["wihy"])
    client = _get_gcs_client()
    bucket = client.bucket(bucket_name)

    # Build slug → topic_slug map from editorial queue
    slug_to_topic = {e["slug"]: e.get("topic_slug", "") for e in EDITORIAL_QUEUE}

    patched = []
    blobs = bucket.list_blobs(prefix=f"{BLOG_POSTS_PREFIX}/")
    for blob in blobs:
        if blob.name.endswith(".json") and "index.json" not in blob.name:
            try:
                content = blob.download_as_text()
                post = json.loads(content)
                slug = post.get("slug", "")
                existing_topic = post.get("topic_slug", "")
                mapped_topic = slug_to_topic.get(slug, "")

                if mapped_topic and existing_topic != mapped_topic:
                    post["topic_slug"] = mapped_topic
                    blob.upload_from_string(
                        json.dumps(post, indent=2, default=str),
                        content_type="application/json",
                    )
                    patched.append(slug)
                    logger.info("Patched topic_slug for '%s' → '%s'", slug, mapped_topic)
            except Exception as e:
                logger.warning("Failed to patch %s: %s", blob.name, e)

    if patched:
        update_blog_index(brand)

    return patched


def get_queue_status() -> Dict[str, Any]:
    """Return the editorial queue with counts per brand."""
    wihy_count = sum(1 for e in EDITORIAL_QUEUE if e["brand"] == "wihy")
    cg_count = sum(1 for e in EDITORIAL_QUEUE if e["brand"] == "communitygroceries")
    return {
        "total": len(EDITORIAL_QUEUE),
        "wihy": wihy_count,
        "communitygroceries": cg_count,
        "articles": EDITORIAL_QUEUE,
    }
