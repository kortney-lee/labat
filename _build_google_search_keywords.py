"""
Build keyword inventory from Google-wide search demand using Google Autocomplete.

Why this source:
- GSC only shows queries your site already ranks/impresses for.
- Google Autocomplete reflects broad real user search behavior across Google.

Output:
  data/health_keywords_google_search.json
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, List, Set

import httpx

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"

# Core health/food seed intents to expand from.
SEEDS = [
    "is",
    "are",
    "what is",
    "what are",
    "how to",
    "best foods for",
    "foods that",
    "foods to avoid",
    "diet for",
    "nutrition for",
    "supplements for",
    "exercise for",
    "intermittent fasting",
    "seed oils",
    "processed food",
    "sugar and",
    "gut health",
    "protein and",
    "omega 3",
    "cholesterol and",
    "blood pressure and",
    "blood sugar and",
]

# Health/food anchor terms to combine with seed intents.
TOPICS = [
    "heart health",
    "inflammation",
    "weight loss",
    "insulin resistance",
    "type 2 diabetes",
    "cholesterol",
    "blood pressure",
    "gut microbiome",
    "ultra processed foods",
    "red meat",
    "fiber",
    "sugar",
    "protein",
    "vitamin d",
    "magnesium",
    "creatine",
    "omega 3",
    "keto diet",
    "mediterranean diet",
    "vegan diet",
    "exercise and depression",
    "sleep and metabolism",
    "alcohol and cancer",
    "foods for energy",
    "foods for anxiety",
    "foods for brain health",
    "foods for liver health",
]

BAD_PATTERNS = [
    "near me",
    "store",
    "delivery",
    "kansas city",
    "troost",
    "community grocery",
    "community grocer",
    "job",
    "jobs",
    "hours",
    "phone number",
    "address",
    "instagram",
    "facebook",
    "youtube",
]


def to_slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def classify_topic(q: str) -> str:
    ql = q.lower()
    if any(x in ql for x in ["exercise", "workout", "cardio", "strength", "walking", "hiit"]):
        return "fitness"
    if any(x in ql for x in ["supplement", "vitamin", "magnesium", "omega", "creatine", "probiotic", "berberine"]):
        return "supplements"
    if any(x in ql for x in ["fasting", "16 8", "autophagy", "time restricted"]):
        return "fasting"
    if any(x in ql for x in ["processed", "seed oil", "nitrate", "additive", "trans fat"]):
        return "processed-foods"
    if any(x in ql for x in ["sugar", "blood sugar", "insulin", "glycemic", "diabetes"]):
        return "sugar-and-blood-health"
    if any(x in ql for x in ["protein", "muscle", "sarcopenia", "strength training"]):
        return "protein-and-muscle"
    if any(x in ql for x in ["alcohol", "wine", "drinking", "liver"]):
        return "alcohol-and-health"
    if any(x in ql for x in ["water", "hydration", "electrolyte", "dehydration"]):
        return "hydration"
    return "nutrition"


def keep_query(q: str) -> bool:
    q = q.strip().lower()
    if len(q) < 8 or len(q) > 90:
        return False
    if any(b in q for b in BAD_PATTERNS):
        return False
    if not re.search(r"[a-z]", q):
        return False
    # Keep informational queries likely to convert to blog intent.
    starts = ("is ", "are ", "what ", "how ", "does ", "do ", "can ", "best ", "foods ", "diet ")
    return q.startswith(starts)


def fetch_suggestions(client: httpx.Client, query: str) -> List[str]:
    try:
        r = client.get(
            SUGGEST_URL,
            params={"client": "firefox", "q": query, "hl": "en", "gl": "us"},
            timeout=10.0,
        )
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list):
            return [str(x).strip() for x in payload[1] if isinstance(x, str)]
    except Exception:
        return []
    return []


def main() -> None:
    roots = [f"{seed} {topic}" for seed in SEEDS for topic in TOPICS]

    suggestions: Set[str] = set()
    with httpx.Client() as client:
        for q in roots:
            for s in fetch_suggestions(client, q):
                if keep_query(s):
                    suggestions.add(s.lower())

        # Expand once more using accepted suggestions as new roots (sampled for scale)
        for q in sorted(list(suggestions))[:500]:
            for s in fetch_suggestions(client, q):
                if keep_query(s):
                    suggestions.add(s.lower())

    keywords = []
    seen_slugs: Set[str] = set()
    for q in sorted(suggestions):
        slug = to_slug(q)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        keywords.append(
            {
                "keyword": q,
                "slug": slug,
                "title": q.title(),
                "topic_slug": classify_topic(q),
                "ask_count": 0,
                "intent": "research",
                "source": "google-autocomplete",
            }
        )

    by_topic = Counter(k["topic_slug"] for k in keywords)

    out = {
        "generated_at": date.today().isoformat(),
        "source": "google-autocomplete-us-en",
        "total": len(keywords),
        "keywords": keywords,
    }

    Path("data").mkdir(exist_ok=True)
    path = Path("data/health_keywords_google_search.json")
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Total Google-wide keywords: {len(keywords)}")
    print("By topic:")
    for topic, count in by_topic.most_common():
        print(f"  {topic:<28} {count}")
    print(f"Saved -> {path}")
    print("Run with:")
    print("  python -m src.content.generate_health_posts --keywords data/health_keywords_google_search.json")


if __name__ == "__main__":
    main()
