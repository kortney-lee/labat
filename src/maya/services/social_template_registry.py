"""Structured social template registry for Shania prompt generation.

This keeps brand messaging and layout intent deterministic even before a
dedicated renderer such as Bannerbear is introduced.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set


_RECENT_TEMPLATE_KEYS_BY_BRAND: Dict[str, List[str]] = {}
_MAX_RECENT_PER_BRAND = 8
_BRAND_ROTATION_CURSOR = 0
_TEMPLATE_CURSOR_BY_BRAND: Dict[str, int] = {}


_WIHY_DYNAMIC_TOPICS: List[Dict[str, Any]] = [
    {
        "topic_key": "morning-energy",
        "topic_label": "morning energy",
        "duration": "10-minute",
        "outcome": "steady morning energy",
        "protocol_headline": "Do this in the first 10 minutes after you wake up",
        "timing_headline": "If your morning energy is off, start here",
        "research_headline": "4 research-backed ways to feel more awake without more coffee",
        "action_points": [
            "bright light within 30 minutes of waking",
            "cold water on your face or a short cold rinse",
            "protein before a high-sugar breakfast",
            "5 minutes of movement before screens",
        ],
        "proof_points": [
            "light exposure helps set circadian rhythm early",
            "cold exposure can increase alertness without more caffeine",
            "protein early in the day reduces the late-morning crash",
            "short movement blocks raise energy faster than passive scrolling",
        ],
    },
    {
        "topic_key": "meal-timing",
        "topic_label": "meal timing",
        "duration": "same-day",
        "outcome": "more stable blood sugar",
        "protocol_headline": "Try this eating rhythm for steadier blood sugar",
        "timing_headline": "The easiest meal-timing upgrade you can make today",
        "research_headline": "4 small meal-timing shifts that change your whole day",
        "action_points": [
            "eat protein first instead of starting with refined carbs",
            "front-load more calories earlier in the day",
            "take a 10-minute walk after meals",
            "stop eating about 3 hours before bed",
        ],
        "proof_points": [
            "protein-first meals blunt glucose spikes",
            "post-meal walking improves glucose handling quickly",
            "late-night eating can make sleep and hunger signals worse",
            "meal timing changes how energetic the next day feels",
        ],
    },
    {
        "topic_key": "better-sleep",
        "topic_label": "better sleep",
        "duration": "60-minute",
        "outcome": "deeper sleep tonight",
        "protocol_headline": "Do this in the hour before bed tonight",
        "timing_headline": "Your sleep is usually lost before your head hits the pillow",
        "research_headline": "4 research-backed ways to sleep deeper starting tonight",
        "action_points": [
            "dim lights one hour before bed",
            "cool the room to roughly 65-68°F",
            "cut screens late or use blue-light blockers",
            "keep bedtime within the same 30-minute window",
        ],
        "proof_points": [
            "light control is one of the fastest sleep-quality upgrades",
            "cooler rooms help support deeper sleep stages",
            "sleep timing consistency matters more than a perfect routine",
            "late stimulation shows up as worse recovery the next morning",
        ],
    },
    {
        "topic_key": "all-day-energy",
        "topic_label": "all-day energy",
        "duration": "all-day",
        "outcome": "energy without the caffeine crash",
        "protocol_headline": "If your energy crashes by 2 p.m., start here",
        "timing_headline": "How to keep your energy up without living on caffeine",
        "research_headline": "4 fixes for the afternoon crash that have nothing to do with supplements",
        "action_points": [
            "use morning light before reaching for a second cup of coffee",
            "swap the afternoon coffee for water and a 10-minute walk",
            "eat a protein-heavy snack instead of sugar at 3 p.m.",
            "stop caffeine early enough that sleep stays intact",
        ],
        "proof_points": [
            "hydration and movement solve many fake energy crashes",
            "afternoon caffeine often steals tomorrow's energy",
            "protein is more reliable than sugar for stable focus",
            "energy management is usually a schedule problem, not a supplement problem",
        ],
    },
    {
        "topic_key": "strength-basics",
        "topic_label": "strength training",
        "duration": "20-minute",
        "outcome": "more useful strength with less gym time",
        "protocol_headline": "Want more strength without wasting an hour at the gym?",
        "timing_headline": "The 20-minute strength plan that is actually enough to matter",
        "research_headline": "4 strength basics that outperform random gym time",
        "action_points": [
            "pick 3 compound movements like squats, rows, and presses",
            "do 2 hard sets per movement instead of junk volume",
            "train 3 times per week before adding complexity",
            "progress reps or load slowly and track the numbers",
        ],
        "proof_points": [
            "consistency beats program-hopping for actual strength gains",
            "compound movements cover more ground than machine circuits",
            "tracking reps exposes progress that motivation misses",
            "short focused sessions outperform long unfocused workouts",
        ],
    },
    {
        "topic_key": "recovery-reset",
        "topic_label": "recovery",
        "duration": "15-minute",
        "outcome": "better recovery between hard days",
        "protocol_headline": "Use this 15-minute reset between hard training days",
        "timing_headline": "Recovery is usually where good training plans fall apart",
        "research_headline": "4 recovery basics that work better than expensive recovery gear",
        "action_points": [
            "take an easy walk after training instead of collapsing on the couch",
            "eat protein in a practical post-workout window",
            "get outside light again in the late afternoon",
            "treat sleep as part of training, not the leftover time",
        ],
        "proof_points": [
            "recovery habits determine whether training compounds or stalls",
            "protein timing matters less than total protein, but it still helps",
            "light and sleep quality shape how recovered you actually feel",
            "better recovery usually comes from basics, not expensive tools",
        ],
    },
]

_WIHY_DYNAMIC_FRAMES: List[Dict[str, str]] = [
    {
        "frame_key": "protocol-card",
        "layout_template": "recipe-style protocol card with a strong headline, four clear steps, clean spacing, and direct utility-first copy that feels immediately usable",
        "point_source": "action_points",
        "headline_field": "protocol_headline",
    },
    {
        "frame_key": "timing-playbook",
        "layout_template": "timeline-style layout with time anchors, cause-and-effect language, and practical moves someone can apply the same day",
        "point_source": "action_points",
        "headline_field": "timing_headline",
    },
    {
        "frame_key": "research-checklist",
        "layout_template": "clean editorial checklist with one evidence-led headline, four concise proof-driven lines, and no product-marketing treatment",
        "point_source": "proof_points",
        "headline_field": "research_headline",
    },
]


def _build_wihy_dynamic_templates() -> List[Dict[str, Any]]:
    templates: List[Dict[str, Any]] = []
    for frame in _WIHY_DYNAMIC_FRAMES:
        point_source = frame.get("point_source", "action_points")
        headline_field = frame.get("headline_field", "")
        for topic in _WIHY_DYNAMIC_TOPICS:
            templates.append(
                {
                    "template_key": f"{frame['frame_key']}-{topic['topic_key']}",
                    "headline": str(topic.get(headline_field) or topic.get("outcome") or topic.get("topic_label") or ""),
                    "supporting_points": list(topic.get(point_source, [])),
                    "cta": "",
                    "layout": frame["layout_template"],
                }
            )
    return templates


def _copy_template(template: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **template,
        "supporting_points": list(template.get("supporting_points", [])),
    }


def get_templates_for_brand(brand: str, keep_active_only: bool = True) -> List[Dict[str, Any]]:
    normalized_brand = (brand or "").strip().lower()
    if not normalized_brand:
        return []

    if normalized_brand == "wihy":
        return _build_wihy_dynamic_templates()

    templates = [_copy_template(template) for template in ALL_SOCIAL_TEMPLATE_REGISTRY.get(normalized_brand, [])]
    if not keep_active_only:
        return templates

    active_keys_by_brand: Dict[str, Set[str]] = {
        "communitygroceries": {"easy-recipe", "meal-prep-sunday", "trending-meal", "budget-hack"},
    }
    active_keys = active_keys_by_brand.get(normalized_brand)
    if not active_keys:
        return templates
    return [template for template in templates if template.get("template_key") in active_keys]


def get_template_registry(keep_active_only: bool = True) -> Dict[str, List[Dict[str, Any]]]:
    brands = sorted(set(ALL_SOCIAL_TEMPLATE_REGISTRY.keys()) | {"wihy"})
    return {
        brand: get_templates_for_brand(brand, keep_active_only=keep_active_only)
        for brand in brands
    }


def get_template_driven_brands() -> Set[str]:
    return {brand for brand, templates in get_template_registry(keep_active_only=True).items() if templates}


ALL_SOCIAL_TEMPLATE_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "wihy": [],
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


# Snapshot registry for callers that still import the constant directly.
SOCIAL_TEMPLATE_REGISTRY: Dict[str, List[Dict[str, Any]]] = get_template_registry(keep_active_only=True)


def _render_prompt(brand: str, template: Dict[str, Any]) -> str:
    headline = str(template.get("headline", "")).strip()
    if headline and headline[-1] not in ".!?":
        headline = f"{headline}."
    points = ", ".join(template.get("supporting_points", []))
    cta = str(template.get("cta", "")).strip()
    meal_image_clause = ""
    brand_specific_guidance = ""
    if brand == "communitygroceries":
        meal_image_clause = (
            "Use a real appetizing meal image as the hero visual (plated food, meal prep, "
            "or family dinner scene) with warm natural lighting."
        )
    elif brand == "wihy":
        brand_specific_guidance = (
            "Keep this editorial and useful. Do not include app promotion, download language, "
            "mock phones, CTA buttons, or product-marketing framing. Make it feel like a saved post, "
            "not an ad."
        )

    cta_clause = f"Call to action: {cta}. " if cta else ""
    closing_guidance = (
        "Keep the design clean and readable. Use one dominant headline and concise supporting lines. "
        "Prioritize mobile legibility, strong contrast, safe margins, and text that stays inside a centered content zone. "
        "Avoid clutter, tiny text, and generic motivational phrasing."
    )
    optional_guidance = " ".join(
        part for part in (meal_image_clause, brand_specific_guidance, cta_clause.strip()) if part
    )

    return (
        f"Create a branded social media post for {brand}. "
        f"Use the template family '{template['template_key']}'. "
        f"Visual direction: {template['layout']}. "
        f"Primary headline: {headline} "
        f"Supporting ideas to communicate: {points}. "
        f"{optional_guidance} "
        f"{closing_guidance}"
    )


def build_structured_social_topics(brand: Optional[str] = None) -> List[Dict[str, str]]:
    brands = [brand] if brand else sorted(get_template_driven_brands())
    topics: List[Dict[str, str]] = []
    for current_brand in brands:
        for template in get_templates_for_brand(current_brand, keep_active_only=True):
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

            ordered_candidates = sorted(
                candidates,
                key=lambda item: str(item.get("template_key", "")),
            )
            start_cursor = _TEMPLATE_CURSOR_BY_BRAND.get(brand, 0) % len(ordered_candidates)
            recent = _RECENT_TEMPLATE_KEYS_BY_BRAND.get(brand, [])
            choice = None
            chosen_index = start_cursor

            # First pass: find next non-recent template from this brand's cursor.
            for offset in range(len(ordered_candidates)):
                idx = (start_cursor + offset) % len(ordered_candidates)
                candidate = ordered_candidates[idx]
                if candidate.get("template_key", "") in recent:
                    continue
                choice = candidate
                chosen_index = idx
                break

            # Fallback: if all are recent, advance cursor anyway and take the next one.
            if choice is None:
                choice = ordered_candidates[start_cursor]
                chosen_index = start_cursor

            _TEMPLATE_CURSOR_BY_BRAND[brand] = (chosen_index + 1) % len(ordered_candidates)

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
    registry = get_template_registry(keep_active_only=keep_active_only)
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
