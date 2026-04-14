from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

MEAL_KEYWORDS = [
    "healthy meal prep for weight loss",
    "high protein meal prep ideas",
    "easy healthy dinner ideas",
    "budget healthy meals for family",
    "low carb meal prep ideas",
    "high protein breakfast ideas",
    "healthy lunch ideas for work",
    "mediterranean diet meal plan",
    "anti inflammatory meal plan",
    "diabetic friendly meal ideas",
    "heart healthy dinner recipes",
    "gluten free meal prep ideas",
    "high fiber meal ideas",
    "healthy snacks for weight loss",
    "meal prep for beginners",
    "cheap healthy meal prep",
    "healthy air fryer meals",
    "high protein vegetarian meals",
    "one pot healthy dinners",
    "easy healthy meals for busy weeknights",
]


def to_slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def to_title(keyword: str) -> str:
    return keyword.title()


pages = []
for kw in MEAL_KEYWORDS:
    slug = to_slug(kw)
    pages.append(
        {
            "slug": slug,
            "route_base": "/trending",
            "route_path": f"/trending/{slug}",
            "page_type": "trending-meal",
            "topic_slug": "nutrition",
            "keyword": kw,
            "title": to_title(kw),
            "meta_description": f"Learn how to use {kw} with practical grocery planning and healthier meal choices.",
            "seo_keywords": [kw, "healthy meals", "meal planning", "community groceries"],
        }
    )

payload = {
    "brand": "communitygroceries",
    "generated_at": date.today().isoformat(),
    "source": "google-autocomplete-informed-seed",
    "pages": pages,
}

Path("data").mkdir(exist_ok=True)
out_path = Path("data/communitygroceries_trending_meal_pages.json")
out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

print(f"Saved {len(pages)} pages -> {out_path}")
