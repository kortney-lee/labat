"""Structured social template registry for Shania prompt generation.

This keeps brand messaging and layout intent deterministic even before a
dedicated renderer such as Bannerbear is introduced.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


_RECENT_TEMPLATE_KEYS_BY_BRAND: Dict[str, List[str]] = {}
_MAX_RECENT_PER_BRAND = 2
_BRAND_ROTATION_CURSOR = 0


ALL_SOCIAL_TEMPLATE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "wihy": [
        {
            "template_key": "superhuman-protocol",
            "headline": "Build your superhuman baseline in 30 days",
            "supporting_points": [
                "cold exposure and sauna cycling for recovery",
                "morning light, grounding, and circadian alignment",
                "sleep score optimization and deep-rest targets",
                "compound lifts plus zone 2 for performance",
            ],
            "cta": "Start your 30-day protocol in WIHY",
            "layout": "high-contrast performance poster, dark base with electric accents, one dominant headline, three compact tactic chips, and one strong CTA button",
        },
        {
            "template_key": "performance-stack",
            "headline": "Your daily performance stack, simplified",
            "supporting_points": [
                "5-minute morning sunlight reset",
                "protein-first breakfast within 90 minutes",
                "zone 2 cardio for metabolic endurance",
                "evening magnesium and sleep wind-down",
            ],
            "cta": "Build your daily stack in WIHY",
            "layout": "clean protocol card with a 1-4 numbered routine, strong typographic hierarchy, and mobile-first spacing",
        },
        {
            "template_key": "biohack-fact",
            "headline": "Science-backed ways to upgrade your biology",
            "supporting_points": [
                "VO2 max outperforms most single blood markers for longevity",
                "grip strength strongly correlates with lifespan outcomes",
                "10 minutes of cold exposure can sharply elevate dopamine",
                "time-restricted eating supports cellular repair pathways",
            ],
            "cta": "Capture these metrics in WIHY",
            "layout": "data-first stat card with one hero fact, two supporting proof lines, clean chart-like blocks, and minimal decorative noise",
        },
        {
            "template_key": "transformation",
            "headline": "Lose weight with a system, not guesswork",
            "supporting_points": [
                "personalized meals matched to your goals",
                "training guidance you can actually stick to",
                "weekly progress check-ins and course correction",
                "one dashboard to keep consistency high",
            ],
            "cta": "Start your plan in WIHY",
            "layout": "transformation concept with one bold promise headline, one proof-oriented subline, and a clear CTA anchored above the fold",
        },
        {
            "template_key": "feature-stack",
            "headline": "10 things in 1 health app",
            "supporting_points": [
                "weight loss planning",
                "fitness and workouts",
                "meal planning and groceries",
                "behavior insights",
            ],
            "cta": "Try WIHY",
            "layout": "clean app-style promo with bold headline, 3 short support lines, minimal clutter",
        },
    ],
    "vowels": [
        {
            "template_key": "nutrition-expose",
            "headline": "What's really in your cereal?",
            "supporting_points": [
                "Lucky Charms: 12g sugar, almost zero protein",
                "food dyes linked to behavioral issues in children",
                "marketing targets kids with cartoon characters",
                "the nutrition label tells a different story than the box",
            ],
            "cta": "Read What Is Healthy?",
            "layout": "investigative data card with shocking nutrition comparison and bold expose headline",
        },
        {
            "template_key": "food-industry-truth",
            "headline": "The food industry doesn't want you to read this",
            "supporting_points": [
                "$14B spent on junk food marketing yearly",
                "only 19 hours of nutrition training in medical school",
                "food subsidies favor corn and soy over vegetables",
                "ultra-processed foods now 60% of American diet",
            ],
            "cta": "Get the data in What Is Healthy?",
            "layout": "dark editorial expose with one hard-hitting stat as headline and supporting data points",
        },
        {
            "template_key": "nutrition-comparison",
            "headline": "Side by side: what you think is healthy vs what is",
            "supporting_points": [
                "granola bar vs apple with almond butter",
                "fruit juice vs whole fruit",
                "low-fat yogurt vs full-fat with no added sugar",
                "veggie chips vs actual vegetables",
            ],
            "cta": "Learn to read labels — What Is Healthy?",
            "layout": "comparison split visual showing marketed 'health food' vs genuinely nutritious option",
        },
        {
            "template_key": "root-cause-insight",
            "headline": "Weight loss is not just willpower",
            "supporting_points": [
                "processed food patterns",
                "root causes of poor health",
                "holistic healing",
                "understand what is really driving symptoms",
            ],
            "cta": "Read the book",
            "layout": "editorial book-promo visual with bold statement, one explanatory line, and a book CTA",
        },
        {
            "template_key": "daily-fact",
            "headline": "One fact that changes how you eat today",
            "supporting_points": [
                "research-backed nutrition insight",
                "surprising ingredient truth",
                "simple actionable takeaway",
                "share-worthy health education",
            ],
            "cta": "Follow @vowels for daily facts",
            "layout": "clean educational fact card with one bold stat and brief explainer text",
        },
    ],
    "communitygroceries": [
        {
            "template_key": "easy-recipe",
            "headline": "Tonight's dinner in 30 minutes, start to table",
            "supporting_points": [
                "everyday ingredients already in your kitchen",
                "step-by-step instructions anyone can follow",
                "family-approved and kid-friendly flavor profile",
                "budget-friendly target under $15 total",
            ],
            "cta": "Get tonight's full recipe in Community Groceries",
            "layout": "warm food-first layout with appetizing close-up, recipe headline, prep time badge, and ingredient-count chip",
        },
        {
            "template_key": "meal-prep-sunday",
            "headline": "Meal prep Sunday, your week handled",
            "supporting_points": [
                "5 family meals prepped in about 2 hours",
                "complete grocery list included upfront",
                "weekly cost target under $60",
                "reheat-and-eat workflow for busy nights",
            ],
            "cta": "Plan your prep week in Community Groceries",
            "layout": "organized meal-grid composition with 5 containers, prep-time stamp, and total-cost callout for quick scanning",
        },
        {
            "template_key": "trending-meal",
            "headline": "This trending meal is viral for a reason",
            "supporting_points": [
                "trending across social feeds this week",
                "beginner-friendly steps and quick prep",
                "high-protein and genuinely satisfying",
                "family-tested, repeat-request favorite",
            ],
            "cta": "Find this trending meal in Community Groceries",
            "layout": "high-energy food visual with trending badge, recipe title lockup, and compact nutrition stats row",
        },
        {
            "template_key": "budget-hack",
            "headline": "Cut grocery spend without cutting nutrition",
            "supporting_points": [
                "smart grocery swaps can save $20+ each week",
                "seasonal produce is often cheaper and fresher",
                "bulk-buy staples, prep once, eat all week",
                "store-brand equivalents reduce cost fast",
            ],
            "cta": "Shop smarter in Community Groceries",
            "layout": "practical savings card with bold dollar-callout, three short budget tips, and clean family-shopping visual cues",
        },
        {
            "template_key": "family-savings",
            "headline": "Feed your family better for less",
            "supporting_points": [
                "meal planning",
                "smart grocery lists",
                "less waste",
                "more savings",
            ],
            "cta": "Try Community Groceries",
            "layout": "family grocery promo with bold practical headline, 3 short benefits, and CTA",
        },
        {
            "template_key": "meal-plan-speed",
            "headline": "A full week of meals in minutes",
            "supporting_points": [
                "budget-aware planning",
                "family-friendly meals",
                "shopping list ready",
                "less stress",
            ],
            "cta": "Plan smarter",
            "layout": "practical utility-style post with one strong benefit headline and short support bullets",
        },
    ],
}


# Active registry used for generation/publishing.
# Keep only strongest 4 template families for each launch app brand.
SOCIAL_TEMPLATE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "wihy": [
        template
        for template in ALL_SOCIAL_TEMPLATE_REGISTRY.get("wihy", [])
        if template.get("template_key")
        in {
            "superhuman-protocol",
            "performance-stack",
            "biohack-fact",
            "transformation",
        }
    ],
    "communitygroceries": [
        template
        for template in ALL_SOCIAL_TEMPLATE_REGISTRY.get("communitygroceries", [])
        if template.get("template_key")
        in {
            "easy-recipe",
            "meal-prep-sunday",
            "trending-meal",
            "budget-hack",
        }
    ],
    "vowels": ALL_SOCIAL_TEMPLATE_REGISTRY.get("vowels", []),
}


def _render_prompt(brand: str, template: Dict[str, Any]) -> str:
    points = ", ".join(template.get("supporting_points", []))
    meal_image_clause = ""
    if brand == "communitygroceries":
        meal_image_clause = (
            " Use a real appetizing meal image as the hero visual (plated food, meal prep, "
            "or family dinner scene) with warm natural lighting."
        )

    return (
        f"Create a branded social media post for {brand}. "
        f"Use the template family '{template['template_key']}'. "
        f"Visual direction: {template['layout']}. "
        f"Primary headline: {template['headline']}. "
        f"Supporting ideas to communicate: {points}. "
        f"Call to action: {template['cta']}. "
        f"{meal_image_clause}"
        "Keep the design clean and readable. Use one dominant headline, one concise support line, "
        "and one clear CTA. Prioritize mobile legibility, strong contrast, safe margins, and text that "
        "stays inside a centered content zone. Avoid clutter, tiny text, and generic motivational phrasing."
    )


def build_structured_social_topics(brand: Optional[str] = None) -> List[Dict[str, str]]:
    brands = [brand] if brand else list(SOCIAL_TEMPLATE_REGISTRY.keys())
    topics: List[Dict[str, str]] = []
    for current_brand in brands:
        for template in SOCIAL_TEMPLATE_REGISTRY.get(current_brand, []):
            topics.append(
                {
                    "prompt": _render_prompt(current_brand, template),
                    "brand": current_brand,
                    "template_key": template["template_key"],
                }
            )
    return topics


def pick_structured_social_topics(count: int, brands: Optional[List[str]] = None) -> List[Dict[str, str]]:
    global _BRAND_ROTATION_CURSOR

    pool = build_structured_social_topics()
    if brands:
        brand_set = {brand.lower() for brand in brands}
        pool = [item for item in pool if item["brand"].lower() in brand_set]
    if not pool or count <= 0:
        return []

    by_brand: Dict[str, List[Dict[str, str]]] = {}
    for item in pool:
        by_brand.setdefault(item["brand"], []).append(item)

    brand_order = sorted(by_brand.keys())
    if not brand_order:
        return []

    start = _BRAND_ROTATION_CURSOR % len(brand_order)
    brand_order = brand_order[start:] + brand_order[:start]
    _BRAND_ROTATION_CURSOR += 1

    selected: List[Dict[str, str]] = []
    selected_keys: Set[str] = set()
    max_unique = min(count, len(pool))

    while len(selected) < max_unique:
        added_this_round = False
        for brand in brand_order:
            candidates = [
                item
                for item in by_brand.get(brand, [])
                if f"{item['brand']}:{item.get('template_key', '')}" not in selected_keys
            ]
            if not candidates:
                continue

            recent = _RECENT_TEMPLATE_KEYS_BY_BRAND.get(brand, [])
            non_recent = [
                item for item in candidates if item.get("template_key", "") not in recent
            ]
            pick_pool = non_recent or candidates
            choice = random.choice(pick_pool)

            selected.append(choice)
            selected_keys.add(f"{choice['brand']}:{choice.get('template_key', '')}")

            key = choice.get("template_key", "")
            if key:
                hist = [k for k in _RECENT_TEMPLATE_KEYS_BY_BRAND.get(brand, []) if k != key]
                hist.append(key)
                _RECENT_TEMPLATE_KEYS_BY_BRAND[brand] = hist[-_MAX_RECENT_PER_BRAND:]

            added_this_round = True
            if len(selected) >= max_unique:
                break

        if not added_this_round:
            break

    return selected


def export_social_templates_local(
    output_dir: str,
    brands: Optional[List[str]] = None,
    keep_active_only: bool = False,
) -> Dict[str, List[str]]:
    """Export social template prompts to local files with numbered indexes."""
    registry = SOCIAL_TEMPLATE_REGISTRY if keep_active_only else ALL_SOCIAL_TEMPLATE_REGISTRY
    selected_brands = brands or list(registry.keys())

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    results: Dict[str, List[str]] = {}
    global_index_lines: List[str] = []
    for brand in selected_brands:
        templates = registry.get(brand, [])
        if not templates:
            continue

        brand_dir = out / brand
        brand_dir.mkdir(parents=True, exist_ok=True)

        files: List[str] = []
        brand_index_lines: List[str] = [f"brand: {brand}", "templates:"]
        for index, template in enumerate(templates):
            template_key = str(template.get("template_key", f"template_{index}")).strip() or f"template_{index}"
            prompt = _render_prompt(brand, template)
            template_number = index + 1
            content = (
                f"brand: {brand}\n"
                f"template_number: {template_number}\n"
                f"template_key: {template_key}\n"
                f"headline: {template.get('headline', '')}\n"
                f"cta: {template.get('cta', '')}\n"
                f"layout: {template.get('layout', '')}\n"
                f"supporting_points:\n"
                + "\n".join(f"- {point}" for point in template.get("supporting_points", []))
                + "\n\n"
                f"prompt:\n{prompt}\n"
            )
            file_path = brand_dir / f"{index:02d}_{template_key}.txt"
            file_path.write_text(content, encoding="utf-8")
            files.append(str(file_path))
            brand_index_lines.append(
                f"{template_number}. {template_key} | {template.get('headline', '')} | {file_path.name}"
            )
            global_index_lines.append(
                f"{brand} #{template_number}: {template_key} | {template.get('headline', '')}"
            )

        brand_index_path = brand_dir / "INDEX.txt"
        brand_index_path.write_text("\n".join(brand_index_lines) + "\n", encoding="utf-8")
        files.insert(0, str(brand_index_path))

        results[brand] = files

    if global_index_lines:
        choices_path = out / "NUMBERED_CHOICES.txt"
        choices_path.write_text("\n".join(global_index_lines) + "\n", encoding="utf-8")

    return results