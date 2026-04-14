from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.content.blog_publisher import publish_post

POSTS_GCS_PREFIX = "gs://cg-web-assets/blog/posts"
USDA_COST_REPORT_URL = "https://www.fns.usda.gov/cnpp/usda-food-plans-cost-food-monthly-reports"
USDA_THRIFTY_URL = "https://www.fns.usda.gov/cnpp/thrifty-food-plan-2021"


def _read_post(slug: str) -> Dict[str, Any]:
    result = subprocess.run(
        f'gcloud storage cat "{POSTS_GCS_PREFIX}/{slug}.json"',
        capture_output=True,
        text=True,
        check=False,
        shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed reading {slug}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def _common_citations() -> list[dict[str, Any]]:
    return [
        {
            "title": "USDA Food Plans: Monthly Cost of Food Reports",
            "journal": "U.S. Department of Agriculture",
            "year": 2026,
            "url": USDA_COST_REPORT_URL,
        },
        {
            "title": "Thrifty Food Plan, 2021",
            "journal": "U.S. Department of Agriculture",
            "year": 2021,
            "url": USDA_THRIFTY_URL,
        },
    ]


def _factor_cost_post(post: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(post)
    updated["body"] = """# Factor Cost Per Meal: What You Actually Pay

## Quick Answer

The honest answer is that Factor pricing is not one permanent number. Your effective cost changes based on how many meals you order, whether an intro promotion is active, and whether shipping or add-ons change the total. Community Groceries is different: it is a $9.99 per month membership, and the value comes from helping households plan meals, shop with intention, and reduce waste instead of paying a prepared-meal markup every week.

## Head-to-Head Comparison

| Feature | Factor | Community Groceries |
|---|---|---|
| Core cost model | Per-meal prepared-food pricing | $9.99/month membership plus your normal grocery spend |
| Convenience | Ready-to-eat meals | Meal planning and grocery guidance |
| Ingredient control | Limited to the weekly menu | High |
| Best use case | Paying for speed and convenience | Planning meals, reducing waste, and shopping to budget |
| Subscription | Recurring meal plan | Yes, $9.99/month |

## Cost and Value

Prepared meals can make sense when convenience is the top priority, but that convenience usually comes with a markup compared with buying and preparing food at home. The stronger comparison is not just "price per meal". It is whether you want to keep paying prepared-meal pricing every week or pay a low monthly planning fee and buy the groceries your household actually needs.

Community Groceries is not free. It costs $9.99 per month. The affordability argument is that a household already spends money on food anyway, and better planning can help that food budget go further. USDA food plan reports show that home-prepared eating patterns still represent meaningful monthly household spend, which is exactly why reducing waste, duplicate purchases, and impulse decisions matters.

That means the right question is not "Is Community Groceries zero dollars?" It is "Can a $9.99 monthly membership help me manage a much larger grocery budget more intentionally?" For many households, that is a more realistic and more useful way to evaluate value.

## Health / Nutrition / Flexibility

Factor is built around pre-made meals, so the convenience is real. But a prepared-meal service is still limited by its weekly menu, portioning, and preset ingredients. If a household wants more flexibility around ingredients, family preferences, budget swaps, or using food already in the kitchen, that model has limits.

Community Groceries gives users more control over what they buy and cook. That matters for people trying to shop around allergies, preferences, cultural food patterns, or cost constraints. It also matters for households that want healthier choices without locking themselves into one company's menu every week.

## Who Each Option Is Best For

**Factor** is best for people who want fully prepared meals and are comfortable paying extra for convenience.

**Community Groceries** is better for people who want planning help, grocery flexibility, and a lower fixed platform cost while keeping control over what they buy.

## Bottom Line

The original "Factor costs $11 to $15 per meal and Community Groceries has no subscription" framing is too simplistic and inaccurate on the Community Groceries side. Community Groceries does have a subscription, and it costs $9.99 per month. The better comparison is prepared-meal markup versus a lower-cost planning membership that helps a household shop smarter with the grocery budget it already has.

If you want convenience above all else, Factor may still fit. If you want more control, more flexibility, and a lower fixed monthly platform cost, Community Groceries is the stronger long-term value play.

## FAQ

**Q: How much does Factor cost per meal?**

A: Factor pricing varies by plan size, promotions, shipping, and add-ons. Check the current checkout flow for exact pricing rather than relying on one fixed number in a blog post.

**Q: Can I customize Factor meals?**

A: You can choose from the weekly menu, but it is still a preset prepared-meal system rather than open-ended grocery-level customization.

**Q: Is Community Groceries more affordable than Factor?**

A: Community Groceries costs $9.99 per month. Whether it is cheaper overall depends on your household's grocery habits, but the value proposition is that better planning can help reduce waste, duplicate purchases, and impulse spending over time.

**Q: What dietary options does Factor offer?**

A: Factor markets several dietary styles, but the exact menu changes over time, so users should review the live menu for the current offering.

**Q: Does Community Groceries require a subscription?**

A: Yes. Community Groceries is a $9.99/month subscription."""
    updated["faq_items"] = [
        {
            "question": "How much does Factor cost per meal?",
            "answer": "Factor pricing varies by plan size, promotions, shipping, and add-ons. Check the current checkout flow for exact pricing rather than relying on one fixed number in a blog post.",
        },
        {
            "question": "Can I customize Factor meals?",
            "answer": "You can choose from the weekly menu, but it is still a preset prepared-meal system rather than open-ended grocery-level customization.",
        },
        {
            "question": "Is Community Groceries more affordable than Factor?",
            "answer": "Community Groceries costs $9.99 per month. Whether it is cheaper overall depends on your household's grocery habits, but the value proposition is that better planning can help reduce waste, duplicate purchases, and impulse spending over time.",
        },
        {
            "question": "What dietary options does Factor offer?",
            "answer": "Factor markets several dietary styles, but the exact menu changes over time, so users should review the live menu for the current offering.",
        },
        {
            "question": "Does Community Groceries require a subscription?",
            "answer": "Yes. Community Groceries is a $9.99/month subscription.",
        },
    ]
    updated["key_takeaways"] = [
        "Community Groceries is not free; it costs $9.99 per month.",
        "Prepared-meal pricing should not be treated as one fixed permanent number because promos, shipping, and add-ons can change the effective cost.",
        "The value case for Community Groceries is better planning against a much larger household food budget, not pretending the service has no subscription.",
    ]
    updated["citations"] = _common_citations()
    updated["word_count"] = len(updated["body"].split())
    return updated


def _comparison_post(post: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(post)
    updated["body"] = """# Community Groceries vs Factor: Better Value for Healthy Meals?

## Quick Answer

Factor wins on convenience because the meals arrive prepared. Community Groceries wins on flexibility, ingredient control, and fixed platform cost. The important correction is this: Community Groceries is not a no-subscription product. It is a $9.99/month membership, and the value case is that it helps households shop and plan more intentionally instead of paying prepared-meal pricing every week.

## Head-to-Head Comparison

| Feature | Community Groceries | Factor |
|---|---|---|
| Model | Grocery planning membership | Prepared meal delivery |
| Fixed platform cost | $9.99/month | Recurring meal-plan pricing |
| Ingredient flexibility | High | Limited to weekly menu |
| Cooking required | Yes | No |
| Best fit | Budget-aware households that want control | People paying for maximum convenience |

## Cost and Value

Factor is built for speed. That is useful, but convenience is usually the most expensive part of the model. Community Groceries takes a different angle. Instead of charging prepared-meal markup, it charges a $9.99 monthly subscription and helps users make better use of the grocery money they were already going to spend.

That distinction matters. USDA food plan reports show that food-at-home budgets are already meaningful for real households. When the food budget is large, even small improvements in planning, ingredient reuse, and shopping discipline can matter more than arguing over a single meal price screenshot.

## Health / Nutrition / Flexibility

Factor can be useful when someone wants grab-and-go structure. But because the meals are preset, flexibility is naturally narrower. Community Groceries is stronger for households that want to swap ingredients, plan around family preferences, or build meals around a tighter weekly budget.

That extra control can matter just as much as convenience, especially for users trying to make healthier choices consistently instead of outsourcing every meal to a prepared service.

## Who Each Option Is Best For

- **Factor**: Best for users who want convenience first and are comfortable paying for prepared meals.
- **Community Groceries**: Best for users who want a lower fixed platform fee, more ingredient control, and better long-term grocery planning.

## Bottom Line

Factor is the easier option if the main goal is to avoid cooking. Community Groceries is the better fit if the goal is to shop smarter, waste less, and keep more control over what comes into the kitchen. The comparison should be framed honestly: Community Groceries is a $9.99/month subscription, not a free service, and its value comes from helping households use their grocery budget better.

## FAQ

**What makes Community Groceries a good Factor alternative?**
Community Groceries gives users more control over ingredients, meal planning, and budget decisions while keeping the platform cost at $9.99/month.

**Is Community Groceries more cost-effective than Factor?**
It can be, but the honest comparison is $9.99/month plus your grocery spend versus prepared-meal pricing. The value comes from planning and waste reduction, not from pretending there is no subscription.

**Can I achieve specific dietary goals with Community Groceries?**
Yes. Community Groceries supports ingredient-level planning, which gives users more room to adapt meals to dietary goals and household preferences.
"""
    updated["faq_items"] = [
        {
            "question": "What makes Community Groceries a good Factor alternative?",
            "answer": "Community Groceries gives users more control over ingredients, meal planning, and budget decisions while keeping the platform cost at $9.99/month.",
        },
        {
            "question": "Is Community Groceries more cost-effective than Factor?",
            "answer": "It can be, but the honest comparison is $9.99/month plus your grocery spend versus prepared-meal pricing. The value comes from planning and waste reduction, not from pretending there is no subscription.",
        },
        {
            "question": "Can I achieve specific dietary goals with Community Groceries?",
            "answer": "Yes. Community Groceries supports ingredient-level planning, which gives users more room to adapt meals to dietary goals and household preferences.",
        },
    ]
    updated["key_takeaways"] = [
        "Community Groceries is a $9.99/month subscription, not a free service.",
        "Factor is stronger on convenience; Community Groceries is stronger on ingredient control and planning flexibility.",
        "The value argument for Community Groceries is better grocery planning against a real household food budget.",
    ]
    updated["citations"] = _common_citations()
    updated["word_count"] = len(updated["body"].split())
    return updated


def _alternative_post(post: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(post)
    updated["body"] = """# Best Factor Alternative for Healthy Meals and Better Value

## Quick Answer

If you want the closest thing to fully prepared convenience, Factor is still the convenience-first option. But if you want more flexibility, more ingredient control, and a much lower fixed platform cost, Community Groceries is the stronger long-term alternative. One important correction: Community Groceries is not free. It is a $9.99/month subscription.

## Head-to-Head Comparison

| Feature | Factor | Community Groceries |
|---|---|---|
| Core model | Prepared meals | Grocery planning membership |
| Flexibility | Limited to weekly menu | High |
| Dietary control | Moderate | High |
| Platform cost | Prepared-meal pricing | $9.99/month |
| Best for | Users buying convenience | Users optimizing budget and ingredient control |

## Why People Look for Alternatives

People usually look for a Factor alternative for one of three reasons: they want lower total food costs, they want more control over ingredients, or they do not want to stay locked into prepared meals as a long-term habit. Those are legitimate reasons, but the comparison still needs to be honest about the alternative's business model.

Community Groceries is not a no-cost tool. It is a $9.99 monthly membership designed to help households plan meals and shop more intentionally. The pitch is not "free instead of Factor". The pitch is "a much lower fixed monthly platform fee while keeping control of your grocery decisions."

## Cost and Value

Prepared meals are often easiest when time is tight, but they can become expensive as a default routine. Community Groceries asks users to do more of the planning and cooking themselves, but that tradeoff can improve long-term value because the household is buying food directly instead of paying prepared-meal markup every week.

USDA food plan reports are useful context here because they show that household food-at-home spending is already substantial. That is why planning matters. When the grocery budget is large enough, even small improvements in waste reduction and better list discipline can be meaningful.

## Health / Nutrition / Flexibility

Community Groceries gives users more room to choose ingredients, portions, and swaps that fit real household needs. That makes it a stronger alternative for families, budget-sensitive shoppers, or people whose goals change week to week.

Factor still has an advantage for users who want a prepared meal without shopping or cooking. But if health goals depend on ingredient choice, budget control, and consistency at home, Community Groceries gives users more room to build around those priorities.

## Who Each Option Is Best For

- **Factor**: Best for people who want ready-to-eat meals and accept the convenience premium.
- **Community Groceries**: Best for people who want a $9.99/month planning tool, grocery flexibility, and better control over how their food budget is used.

## Bottom Line

The best Factor alternative is not the one that pretends to be free. It is the one that offers a more sustainable value model. Community Groceries is a paid subscription, but at $9.99/month it is a very different cost structure from a prepared-meal service. For users who want more flexibility and more control over spending, that is the stronger long-term alternative.

## FAQ

**What makes Community Groceries a better choice for dietary flexibility?**
Community Groceries supports ingredient-level planning, which makes it easier to adjust meals to budget, preferences, and dietary goals.

**Is Community Groceries more affordable than Factor?**
Community Groceries costs $9.99/month. It can be more affordable overall if better planning helps a household use its grocery budget more efficiently, but it should not be described as a free alternative.

**Can I still get ready-to-eat meals with Community Groceries?**
No. Community Groceries is not a prepared-meal delivery service. Its value is in planning, shopping guidance, and flexibility rather than ready-to-eat convenience.
"""
    updated["faq_items"] = [
        {
            "question": "What makes Community Groceries a better choice for dietary flexibility?",
            "answer": "Community Groceries supports ingredient-level planning, which makes it easier to adjust meals to budget, preferences, and dietary goals.",
        },
        {
            "question": "Is Community Groceries more affordable than Factor?",
            "answer": "Community Groceries costs $9.99/month. It can be more affordable overall if better planning helps a household use its grocery budget more efficiently, but it should not be described as a free alternative.",
        },
        {
            "question": "Can I still get ready-to-eat meals with Community Groceries?",
            "answer": "No. Community Groceries is not a prepared-meal delivery service. Its value is in planning, shopping guidance, and flexibility rather than ready-to-eat convenience.",
        },
    ]
    updated["key_takeaways"] = [
        "Community Groceries is a $9.99/month subscription with a very different cost structure from Factor.",
        "Factor is still stronger for ready-to-eat convenience.",
        "Community Groceries is stronger for ingredient control, meal planning flexibility, and long-term budget management.",
    ]
    updated["citations"] = _common_citations()
    updated["word_count"] = len(updated["body"].split())
    return updated


def main() -> None:
    patches = {
        "factor-cost-per-meal": _factor_cost_post,
        "community-groceries-vs-factor": _comparison_post,
        "best-factor-alternative": _alternative_post,
    }

    for slug, updater in patches.items():
        post = _read_post(slug)
        updated = updater(post)
        if not publish_post(updated, brand="communitygroceries"):
            raise SystemExit(f"Failed publishing {slug}")
        print(f"Published {slug}")


if __name__ == "__main__":
    main()