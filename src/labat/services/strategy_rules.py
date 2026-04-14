"""
Central strategy rules for LABAT brand-aware content and intelligence prompts.

This module keeps product-specific positioning, funnel-stage guidance, and
sales targeting presets in one place so multiple services (content, intelligence,
and ad creation) can reuse the same rules.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional

LabatProduct = Literal["wihy", "communitygroceries", "whatishealthy", "vowels", "childrennutrition", "parentingwithchrist"]
FunnelStage = Literal["awareness", "consideration", "conversion"]


_PRODUCT_RULES = {
    "wihy": {
        "name": "WIHY",
        "domain": "wihy.ai",
        "positioning": "AI-powered health and performance platform â€” eat better, train smarter, track progress, shop faster, connect with coaches",
        "offer": "AI meal planning + grocery conversion + fitness dashboard + coach marketplace + progress tracking + product scanning",
        "core_messages": [
            "Plan better. Train smarter. Shop faster.",
            "From goals to groceries to results â€” one app for meals, fitness, progress, and coaching",
            "Your AI and coach-powered health operating system",
        ],
        "features": [
            "AI-guided meal planning tailored to user goals and dietary preferences",
            "Meal diary, meal calendar, and meal library for daily accountability",
            "Converts meal plans into actionable shopping lists with Instacart integration",
            "Fitness dashboard with workout tracking, training programs, and activity visibility",
            "MyProgress dashboard with weight tracking, habit completion, and health trend analytics",
            "Coach marketplace â€” discover coaches, book sessions, get personalized guidance",
            "Health data sync across devices for richer analytics",
            "Product scanning to expose hidden ingredients and misleading food marketing",
            "Research-backed AI health answers grounded in WIHY knowledge base",
            "Multi-plan subscriptions: Free, Premium, Family, Coach tiers",
            "Native iOS and Android apps plus full web experience",
        ],
        "value_themes": [
            "All-in-one health execution â€” not just a tracker, turns intention into action",
            "From plan to purchase â€” reduce drop-off between planning and real behavior",
            "Personal guidance at scale â€” AI personalization plus human coaching",
            "Outcome visibility â€” progress dashboards make improvement measurable",
        ],
        "taglines": [
            "Plan better. Train smarter. Shop faster.",
            "Your AI and coach-powered health operating system.",
            "From goals to groceries to results.",
            "One app for meals, fitness, progress, and coaching.",
        ],
        "audience_segments": [
            "Individuals pursuing weight loss, performance, or healthier routines",
            "Busy users who need meal-to-shopping execution speed",
            "Users who want coaching support with modern app convenience",
            "Wellness brands, schools, and communities needing structured health engagement",
        ],
    },
    "communitygroceries": {
        "name": "Community Groceries",
        "domain": "communitygroceries.com",
        "positioning": "family-focused groceries and meal planning ecosystem powered by AI nutrition technology",
        "offer": "AI meal planning + smart shopping lists + Instacart grocery conversion + budget-aware family nutrition",
        "core_messages": [
            "Reduce family meal stress with done-for-you AI meal planning",
            "Save money and time without sacrificing nutrition",
            "From meal plan to grocery cart in minutes â€” shop smarter, not harder",
        ],
        "features": [
            "AI-guided meal planning tailored to family size, dietary preferences, and budget",
            "Meal diary and meal calendar for daily household accountability",
            "Converts meal plans into actionable shopping lists with Instacart integration",
            "Shopping preference support for personalized grocery outputs",
            "Manual meal entry and product search autocomplete",
            "Meal library for organizing and reusing family favorites",
            "Budget-aware nutrition that maximizes food quality per dollar",
        ],
        "value_themes": [
            "From plan to purchase â€” one tap from weekly meals to grocery cart",
            "Family-first planning â€” designed for real households, not solo dieters",
            "Save money and reduce food waste with smart shopping lists",
            "Make healthier household routines that actually stick",
        ],
        "taglines": [
            "Meal plans to grocery carts â€” done.",
            "Feed your family better, faster, cheaper.",
            "Smart meals. Smart shopping. Real savings.",
            "From recipe to receipt in minutes.",
        ],
        "audience_segments": [
            "Parents and families looking for easier meal planning",
            "Budget-conscious grocery shoppers who want healthier options",
            "Busy households that need meal-to-shopping execution speed",
            "Coupon-savvy shoppers interested in meal prep and batch cooking",
        ],
    },
    "whatishealthy": {
        "name": "What Is Healthy",
        "domain": "whatishealthy.org",
        "positioning": "research-backed book exposing how food systems, culture, and convenience reshaped health â€” and how to take control back",
        "offer": "free digital book + hardcover upsell + app cross-sell journey",
        "core_messages": [
            "Healthy isn't complicated â€” we've just been disconnected from it",
            "You don't have a willpower problem. You have an environment problem.",
            "This book explains why doing 'everything right' still feels wrong.",
        ],
        "book_pitch": "In a world flooded with conflicting health advice, What Is Healthy? cuts through the noise. This book reveals how we moved from whole, intentional eating to ultra-processed convenience â€” and how that shift has led to rising obesity, chronic illness, and confusion about what 'healthy' even means.",
        "key_themes": [
            "How ultra-processed foods reshaped modern diets",
            "Why hunger, habits, and emotions are disconnected",
            "The role of dopamine and addiction in eating patterns",
            "How generational habits shape long-term health outcomes",
            "Root causes, not quick fixes â€” science + culture + personal story",
        ],
        "sales_angles": [
            "Clarity: Stop guessing what's healthy.",
            "Truth: What you've been told about food isn't the full story.",
            "Control: Take back control of your health, your habits, and your future.",
            "Generational: This isn't just about you â€” it's about what you pass down.",
        ],
        "hooks": [
            "We didn't lose health â€” we replaced it with convenience.",
            "What you eat is learned. What you pass on is inherited.",
            "People don't lack information â€” they lack clarity.",
        ],
        "audience_segments": [
            "Individuals struggling with weight, energy, or chronic illness",
            "Parents trying to build healthier habits for their families",
            "Schools and educators (nutrition literacy)",
            "Communities affected by food access and health disparities",
        ],
    },
    "vowels": {
        "name": "Vowels",
        "domain": "vowels.org",
        "positioning": "data storytelling brand focused on health crisis evidence â€” home of the What Is Healthy? book",
        "offer": "research-backed narratives + What Is Healthy? book + statistics-driven health education",
        "core_messages": [
            "Make complex public health data understandable",
            "Show human impact behind the statistics",
            "Use transparent evidence to challenge assumptions",
        ],
        "book_pitch": "In a world flooded with conflicting health advice, What Is Healthy? cuts through the noise. This book reveals how we moved from whole, intentional eating to ultra-processed convenience â€” and how that shift has led to rising obesity, chronic illness, and confusion about what 'healthy' even means.",
        "hooks": [
            "We didn't lose health â€” we replaced it with convenience.",
            "What you eat is learned. What you pass on is inherited.",
            "People don't lack information â€” they lack clarity.",
        ],
    },
    "childrennutrition": {
        "name": "Children Nutrition",
        "domain": "whatishealthy.org",
        "positioning": "science-backed children's nutrition and picky eater solutions",
        "offer": "practical guides for feeding kids healthy food they'll actually eat",
        "core_messages": [
            "Turn picky eaters into adventurous eaters with proven strategies",
            "Make healthy food fun and accessible for every family",
            "Give parents confidence with science-backed nutrition guidance",
        ],
    },
    "parentingwithchrist": {
        "name": "Parenting With Christ",
        "domain": "parentingwithchrist.com",
        "positioning": "faith-based parenting grounded in Biblical discipline and self-control",
        "offer": "Scriptural wisdom for raising disciplined, faith-rooted children",
        "core_messages": [
            "Teach children the power of fasting, discipline, and delayed gratification",
            "Raise kids who follow Jesus in a world that tells them to follow themselves",
            "Biblical parenting principles that build character and faith",
        ],
    },
}


_FUNNEL_RULES = {
    "awareness": {
        "goal": "Stop the scroll and surface a painful but relatable problem.",
        "angles": [
            "myth-busting hooks",
            "pattern interrupts",
            "counter-intuitive insight",
        ],
    },
    "consideration": {
        "goal": "Build trust with proof, mechanism, and practical value.",
        "angles": [
            "educational breakdown",
            "objection handling",
            "social proof and concrete examples",
        ],
    },
    "conversion": {
        "goal": "Create clear urgency and direct action without hype.",
        "angles": [
            "offer clarity",
            "risk reversal",
            "specific CTA with next step",
        ],
    },
}


# â”€â”€ Sales Targeting Presets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Per-brand Meta targeting defaults, applied when an adset is created with
# empty targeting.  These ensure interest-based audiences are always populated.

# Interest IDs validated against Meta Graph API /search?type=adinterest
# Each brand targets a distinct audience matching its product.
_TARGETING_PRESETS: Dict[str, Dict[str, Any]] = {
    # â”€â”€ Vowels: book audience tuned for weight-loss / health / holistic healing intent â”€â”€
    # Target: users seeking evidence-based weight and wellness transformation
    "vowels": {
        "geo_locations": {"countries": ["US"]},
        "age_min": 25,
        "age_max": 55,
        "genders": [1, 2],
        "flexible_spec": [
            {
                "interests": [
                    {"id": "6003384248805", "name": "Fitness and wellness"},
                    {"id": "6003277229371", "name": "Physical fitness"},
                    {"id": "6003382102565", "name": "Healthy diet"},
                    {"id": "6002868910910", "name": "Organic food"},
                    {"id": "6003780190452", "name": "Natural foods"},
                    {"id": "6003748928462", "name": "Personal development"},
                    {"id": "6002991736368", "name": "Reading"},
                    {"id": "6003462707303", "name": "Books"},
                ],
            },
        ],
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed", "story"],
        "instagram_positions": ["stream", "story", "reels", "explore"],
    },
    # â”€â”€ What Is Healthy: book + education funnel on nutrition misinformation
    # Target: health-conscious readers, parents who question food labels
    "whatishealthy": {
        "geo_locations": {"countries": ["US"]},
        "age_min": 25,
        "age_max": 55,
        "genders": [1, 2],
        "flexible_spec": [
            {
                "interests": [
                    {"id": "6003382102565", "name": "Healthy diet"},
                    {"id": "6002868910910", "name": "Organic food"},
                    {"id": "6003780190452", "name": "Natural foods"},
                    {"id": "6002991736368", "name": "Reading"},
                    {"id": "6003462707303", "name": "Books"},
                    {"id": "6003232518610", "name": "Parenting"},
                ],
                "behaviors": [
                    {"id": "6071631541183", "name": "Engaged Shoppers"},
                ],
            },
        ],
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed", "story"],
        "instagram_positions": ["stream", "story", "reels", "explore"],
    },
    # â”€â”€ Community Groceries: family meal planning + budget groceries â”€â”€â”€â”€â”€â”€â”€
    # Target: parents, meal preppers, coupon users, recipe followers, families
    "communitygroceries": {
        "geo_locations": {"countries": ["US"]},
        "age_min": 22,
        "age_max": 50,
        "genders": [1, 2],
        "flexible_spec": [
            {
                "interests": [
                    {"id": "6003659420716", "name": "Cooking"},
                    {"id": "6003385609165", "name": "Recipes"},
                    {"id": "837870002989553", "name": "Meal preparation"},
                    {"id": "6003054884732", "name": "Coupons"},
                    {"id": "6003174128015", "name": "Grocery store"},
                    {"id": "6003476182657", "name": "Family"},
                    {"id": "6003232518610", "name": "Parenting"},
                ],
                "behaviors": [
                    {"id": "6071631541183", "name": "Engaged Shoppers"},
                ],
            },
        ],
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed", "story"],
        "instagram_positions": ["stream", "story", "reels", "explore"],
    },
    # â”€â”€ WIHY: 10-in-1 app audience (weight loss + fitness + wellness execution) â”€â”€
    # Target: users who want all-in-one planning, fitness, and healthy-living outcomes
    "wihy": {
        "geo_locations": {"countries": ["US"]},
        "age_min": 22,
        "age_max": 50,
        "genders": [1, 2],
        "flexible_spec": [
            {
                "interests": [
                    {"id": "6003384248805", "name": "Fitness and wellness"},
                    {"id": "6003277229371", "name": "Physical fitness"},
                    {"id": "6003382102565", "name": "Healthy diet"},
                    {"id": "6002868910910", "name": "Organic food"},
                    {"id": "6003780190452", "name": "Natural foods"},
                    {"id": "6003659420716", "name": "Cooking"},
                    {"id": "837870002989553", "name": "Meal preparation"},
                    {"id": "6003174128015", "name": "Grocery store"},
                    {"id": "6003748928462", "name": "Personal development"},
                    {"id": "6003476182657", "name": "Family"},
                ],
                "behaviors": [
                    {"id": "6071631541183", "name": "Engaged Shoppers"},
                ],
            },
        ],
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed", "story"],
        "instagram_positions": ["stream", "story", "reels", "explore"],
    },
    # â”€â”€ Children Nutrition: picky eaters, kids health, school lunches â”€â”€â”€â”€â”€â”€
    # Target: parents of young children, family health-conscious moms/dads
    "childrennutrition": {
        "geo_locations": {"countries": ["US"]},
        "age_min": 25,
        "age_max": 45,
        "genders": [1, 2],
        "flexible_spec": [
            {
                "interests": [
                    {"id": "6003232518610", "name": "Parenting"},
                    {"id": "6003476182657", "name": "Family"},
                    {"id": "6003382102565", "name": "Healthy diet"},
                    {"id": "6003659420716", "name": "Cooking"},
                    {"id": "6003385609165", "name": "Recipes"},
                    {"id": "6003327060545", "name": "Education"},
                ],
            },
        ],
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed", "story"],
        "instagram_positions": ["stream", "story", "reels", "explore"],
    },
    # â”€â”€ Parenting With Christ: faith-based parenting, discipline â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Target: Christian parents, church-goers, faith-based family audience
    "parentingwithchrist": {
        "geo_locations": {"countries": ["US"]},
        "age_min": 25,
        "age_max": 50,
        "genders": [1, 2],
        "flexible_spec": [
            {
                "interests": [
                    {"id": "6003232518610", "name": "Parenting"},
                    {"id": "6003476182657", "name": "Family"},
                    {"id": "6003107902433", "name": "Christianity"},
                    {"id": "6003455271549", "name": "The Bible"},
                    {"id": "6003327060545", "name": "Education"},
                    {"id": "6003748928462", "name": "Personal development"},
                ],
            },
        ],
        "publisher_platforms": ["facebook", "instagram"],
        "facebook_positions": ["feed", "story"],
        "instagram_positions": ["stream", "story", "reels", "explore"],
    },
}


# Funnel stage â†’ Meta campaign objective + adset optimization goal
_FUNNEL_OBJECTIVE_MAP: Dict[str, Dict[str, str]] = {
    "awareness": {
        "campaign_objective": "OUTCOME_AWARENESS",
        "optimization_goal": "REACH",
        "billing_event": "IMPRESSIONS",
    },
    "consideration": {
        "campaign_objective": "OUTCOME_TRAFFIC",
        "optimization_goal": "LINK_CLICKS",
        "billing_event": "IMPRESSIONS",
    },
    "conversion": {
        "campaign_objective": "OUTCOME_SALES",
        "optimization_goal": "OFFSITE_CONVERSIONS",
        "billing_event": "IMPRESSIONS",
    },
}


def normalize_product(product: Optional[str]) -> LabatProduct:
    if not product:
        return "wihy"
    value = product.strip().lower()
    if value in _PRODUCT_RULES:
        return value  # type: ignore[return-value]
    return "wihy"


def normalize_funnel_stage(stage: Optional[str]) -> Optional[FunnelStage]:
    if not stage:
        return None
    value = stage.strip().lower()
    if value in _FUNNEL_RULES:
        return value  # type: ignore[return-value]
    return None


def build_strategy_block(product: Optional[str], funnel_stage: Optional[str] = None) -> str:
    p = normalize_product(product)
    s = normalize_funnel_stage(funnel_stage)
    product_cfg = _PRODUCT_RULES[p]

    lines = [
        "Product Strategy Context:",
        f"- product_id: {p}",
        f"- brand_name: {product_cfg['name']}",
        f"- domain: {product_cfg['domain']}",
        f"- positioning: {product_cfg['positioning']}",
        f"- core_offer: {product_cfg['offer']}",
        "- messaging_priorities:",
    ]
    for msg in product_cfg["core_messages"]:
        lines.append(f"  - {msg}")

    # Include features when available (gives Alex richer copy material)
    if "features" in product_cfg:
        lines.append("- key_features:")
        for feat in product_cfg["features"]:
            lines.append(f"  - {feat}")

    # Include value themes when available
    if "value_themes" in product_cfg:
        lines.append("- value_themes:")
        for theme in product_cfg["value_themes"]:
            lines.append(f"  - {theme}")

    # Include taglines when available
    if "taglines" in product_cfg:
        lines.append("- suggested_taglines:")
        for tag in product_cfg["taglines"]:
            lines.append(f"  - {tag}")

    # Include audience segments when available
    if "audience_segments" in product_cfg:
        lines.append("- target_audience:")
        for seg in product_cfg["audience_segments"]:
            lines.append(f"  - {seg}")

    # Include book pitch and hooks for book products
    if "book_pitch" in product_cfg:
        lines.append(f"- book_pitch: {product_cfg['book_pitch']}")
    if "hooks" in product_cfg:
        lines.append("- ad_hooks:")
        for hook in product_cfg["hooks"]:
            lines.append(f"  - {hook}")
    if "sales_angles" in product_cfg:
        lines.append("- sales_angles:")
        for angle in product_cfg["sales_angles"]:
            lines.append(f"  - {angle}")
    if "key_themes" in product_cfg:
        lines.append("- key_themes:")
        for theme in product_cfg["key_themes"]:
            lines.append(f"  - {theme}")

    if s:
        funnel_cfg = _FUNNEL_RULES[s]
        lines.extend(
            [
                "Funnel Strategy Context:",
                f"- funnel_stage: {s}",
                f"- stage_goal: {funnel_cfg['goal']}",
                "- recommended_angles:",
            ]
        )
        for angle in funnel_cfg["angles"]:
            lines.append(f"  - {angle}")

    lines.extend(
        [
            "Persuasion Guidelines:",
            "- Use evidence-first persuasion (clarity over hype).",
            "- Emphasize concrete outcomes and mechanisms.",
            "- Keep ethical boundaries: no manipulative fear claims, no fabricated stats.",
        ]
    )

    return "\n".join(lines)


# Behavior injected into conversion-funnel targeting so Meta optimises for buyers
# Correct Meta ID for "Engaged Shoppers" (Purchase behavior category)
_ENGAGED_SHOPPERS = {"id": "6071631541183", "name": "Engaged Shoppers"}


# â”€â”€ Lead Form Question Presets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Per-brand qualifying questions added to lead forms so only interested users
# submit.  Meta supports CUSTOM questions with multi-choice options.
# Standard fields (EMAIL, FIRST_NAME, LAST_NAME) are always included.
_LEAD_FORM_QUESTIONS: Dict[str, list] = {
    "wihy": [
        {"type": "EMAIL"},
        {"type": "FIRST_NAME"},
        {"type": "LAST_NAME"},
        {
            "type": "CUSTOM",
            "key": "health_goal",
            "label": "What do you want the app to help you do first?",
            "options": [
                {"value": "weight_loss", "key": "weight_loss"},
                {"value": "fitness_and_workouts", "key": "fitness_and_workouts"},
                {"value": "eat_healthier", "key": "eat_healthier"},
                {"value": "meal_planning", "key": "meal_planning"},
                {"value": "track_my_progress", "key": "track_my_progress"},
                {"value": "just_browsing", "key": "just_browsing"},
            ],
        },
    ],
    "communitygroceries": [
        {"type": "EMAIL"},
        {"type": "FIRST_NAME"},
        {"type": "LAST_NAME"},
        {
            "type": "CUSTOM",
            "key": "meal_planning_interest",
            "label": "What would help your family the most?",
            "options": [
                {"value": "weekly_meal_plans", "key": "weekly_meal_plans"},
                {"value": "grocery_savings", "key": "grocery_savings"},
                {"value": "healthy_recipes", "key": "healthy_recipes"},
                {"value": "less_food_waste", "key": "less_food_waste"},
                {"value": "just_browsing", "key": "just_browsing"},
            ],
        },
    ],
    "vowels": [
        {"type": "EMAIL"},
        {"type": "FIRST_NAME"},
        {"type": "LAST_NAME"},
        {
            "type": "CUSTOM",
            "key": "book_interest",
            "label": "What are you hoping this book helps you with?",
            "options": [
                {"value": "lose_weight_and_feel_better", "key": "weight_loss"},
                {"value": "heal_my_health_holistically", "key": "holistic_healing"},
                {"value": "understand_why_food_is_harming_me", "key": "root_causes"},
                {"value": "help_my_family_get_healthier", "key": "family_health"},
                {"value": "just_curious", "key": "just_curious"},
            ],
        },
    ],
    "whatishealthy": [
        {"type": "EMAIL"},
        {"type": "FIRST_NAME"},
        {"type": "LAST_NAME"},
        {
            "type": "CUSTOM",
            "key": "book_interest",
            "label": "What are you hoping this book helps you with?",
            "options": [
                {"value": "lose_weight_and_feel_better", "key": "weight_loss"},
                {"value": "heal_my_health_holistically", "key": "holistic_healing"},
                {"value": "understand_why_food_is_harming_me", "key": "root_causes"},
                {"value": "help_my_family_get_healthier", "key": "family_health"},
                {"value": "just_curious", "key": "just_curious"},
            ],
        },
    ],
    "childrennutrition": [
        {"type": "EMAIL"},
        {"type": "FIRST_NAME"},
        {"type": "LAST_NAME"},
        {
            "type": "CUSTOM",
            "key": "parent_challenge",
            "label": "What's your biggest challenge feeding your kids?",
            "options": [
                {"value": "picky_eaters", "key": "picky_eaters"},
                {"value": "healthy_lunches", "key": "healthy_lunches"},
                {"value": "budget_nutrition", "key": "budget_nutrition"},
                {"value": "time_for_cooking", "key": "time_cooking"},
                {"value": "just_browsing", "key": "just_browsing"},
            ],
        },
    ],
    "parentingwithchrist": [
        {"type": "EMAIL"},
        {"type": "FIRST_NAME"},
        {"type": "LAST_NAME"},
        {
            "type": "CUSTOM",
            "key": "parenting_focus",
            "label": "What area of parenting are you most focused on?",
            "options": [
                {"value": "discipline_guidance", "key": "discipline"},
                {"value": "faith_foundation", "key": "faith"},
                {"value": "healthy_habits", "key": "habits"},
                {"value": "screen_time_balance", "key": "screen_time"},
                {"value": "just_browsing", "key": "just_browsing"},
            ],
        },
    ],
}


def get_lead_form_preset(product: Optional[str]) -> list:
    """Return lead form questions for the given product/brand."""
    p = normalize_product(product)
    return list(_LEAD_FORM_QUESTIONS.get(p, _LEAD_FORM_QUESTIONS["wihy"]))


def get_targeting_preset(product: Optional[str]) -> Dict[str, Any]:
    """Return Meta targeting dict for the given product/brand."""
    p = normalize_product(product)
    return dict(_TARGETING_PRESETS.get(p, _TARGETING_PRESETS["wihy"]))


def enhance_targeting_for_funnel(
    targeting: Dict[str, Any],
    funnel_stage: Optional[str],
) -> Dict[str, Any]:
    """Adjust targeting based on funnel stage.

    - **conversion**: inject Engaged Shoppers behavior (we know who converts)
    - **awareness**: strip behaviors for maximum reach at budget
    - **consideration**: leave as-is
    """
    import copy
    t = copy.deepcopy(targeting)
    stage = normalize_funnel_stage(funnel_stage)
    specs = t.get("flexible_spec", [])

    if stage == "conversion" and specs:
        # Ensure Engaged Shoppers is present
        behaviors = specs[0].get("behaviors", [])
        if not any(b.get("id") == _ENGAGED_SHOPPERS["id"] for b in behaviors):
            behaviors.append(dict(_ENGAGED_SHOPPERS))
            specs[0]["behaviors"] = behaviors

    elif stage == "awareness" and specs:
        # Broad reach â€” drop behaviors, keep interests only
        for spec in specs:
            spec.pop("behaviors", None)

    return t


def get_funnel_objective(funnel_stage: Optional[str]) -> Dict[str, str]:
    """Return campaign objective + optimization goal for the funnel stage.

    Defaults to 'conversion' if not specified (sell, don't just drive traffic).
    """
    stage = normalize_funnel_stage(funnel_stage) or "conversion"
    return dict(_FUNNEL_OBJECTIVE_MAP[stage])


def get_product_domain(product: Optional[str]) -> str:
    """Return the landing-page domain for the given product."""
    p = normalize_product(product)
    return _PRODUCT_RULES[p]["domain"]
