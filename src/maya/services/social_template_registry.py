"""Structured social template registry for Shania prompt generation.

This keeps brand messaging and layout intent deterministic even before a
dedicated renderer such as Bannerbear is introduced.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


SOCIAL_TEMPLATE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "wihy": [
        {
            "template_key": "superhuman-protocol",
            "headline": "Unlock superhuman health",
            "supporting_points": [
                "cold exposure + sauna cycling",
                "grounding and red light therapy",
                "sleep optimization protocol",
                "compound movement training",
            ],
            "cta": "Start your protocol on WIHY",
            "layout": "bold dark futuristic design with one powerful headline, 3 biohacking tactics, and app CTA",
        },
        {
            "template_key": "performance-stack",
            "headline": "Your daily performance stack",
            "supporting_points": [
                "morning sunlight exposure",
                "protein-first breakfast",
                "zone 2 cardio",
                "magnesium before bed",
            ],
            "cta": "Build your stack on WIHY",
            "layout": "clean protocol-style post with numbered daily habits and strong headline",
        },
        {
            "template_key": "biohack-fact",
            "headline": "Science says you can upgrade your biology",
            "supporting_points": [
                "VO2 max predicts longevity better than any blood test",
                "grip strength correlates with lifespan",
                "10 min cold exposure = 250% dopamine increase",
                "time-restricted eating repairs cellular damage",
            ],
            "cta": "Track it all on WIHY",
            "layout": "data-driven bold stat card with one shocking research fact and supporting evidence line",
        },
        {
            "template_key": "transformation",
            "headline": "Lose weight with structure, not guesswork",
            "supporting_points": [
                "personalized meals",
                "fitness guidance",
                "wellness support",
                "one place to stay consistent",
            ],
            "cta": "Start with WIHY",
            "layout": "simple transformation-style post with one strong promise, one proof line, and one CTA",
        },
        {
            "template_key": "feature-stack",
            "headline": "10 things in 1 health app",
            "supporting_points": [
                "weight loss planning",
                "fitness and workouts",
                "meal planning and groceries",
                "progress tracking",
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
            "headline": "Tonight's dinner — ready in 30 minutes",
            "supporting_points": [
                "simple ingredients you already have",
                "step-by-step instructions",
                "family-approved and kid-friendly",
                "budget-friendly under $15",
            ],
            "cta": "Get the full recipe at Community Groceries",
            "layout": "warm inviting food photo style with recipe name as headline, prep time, and ingredient count",
        },
        {
            "template_key": "meal-prep-sunday",
            "headline": "Meal prep Sunday — this week sorted",
            "supporting_points": [
                "5 meals prepped in 2 hours",
                "full grocery list included",
                "under $60 for the whole family",
                "reheat and eat all week",
            ],
            "cta": "Plan your week with Community Groceries",
            "layout": "organized meal grid showing 5 prepped containers with prep time and total cost",
        },
        {
            "template_key": "trending-meal",
            "headline": "This recipe is going viral for a reason",
            "supporting_points": [
                "trending on social media this week",
                "easy enough for beginners",
                "high protein and satisfying",
                "your family will ask for seconds",
            ],
            "cta": "Find trending meals at Community Groceries",
            "layout": "eye-catching food visual with trending badge, recipe name, and quick nutrition stats",
        },
        {
            "template_key": "budget-hack",
            "headline": "Feed your family for less — without sacrificing nutrition",
            "supporting_points": [
                "smart grocery swaps that save $20+/week",
                "seasonal produce = cheaper and fresher",
                "buy in bulk, prep once, eat all week",
                "stop paying for brands — store brands are the same",
            ],
            "cta": "Shop smarter with Community Groceries",
            "layout": "practical tip-style post with bold savings number and 3 short budget tips",
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


def _render_prompt(brand: str, template: Dict[str, Any]) -> str:
    points = ", ".join(template.get("supporting_points", []))
    return (
        f"Create a branded social media post for {brand}. "
        f"Use the template family '{template['template_key']}'. "
        f"Visual direction: {template['layout']}. "
        f"Primary headline: {template['headline']}. "
        f"Supporting ideas to communicate: {points}. "
        f"Call to action: {template['cta']}. "
        "Keep the design clean and readable. Use a short headline, a short supporting line, "
        "and a single clear CTA. Avoid clutter, tiny text, and generic motivational phrasing."
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
    pool = build_structured_social_topics()
    if brands:
        brand_set = {brand.lower() for brand in brands}
        pool = [item for item in pool if item["brand"].lower() in brand_set]
    if not pool:
        return []
    if count >= len(pool):
        random.shuffle(pool)
        return pool
    return random.sample(pool, count)