from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List


_COMPARISON_CITATIONS = [
    {
        "title": "USDA Food Plans: Monthly Cost of Food Reports",
        "journal": "U.S. Department of Agriculture",
        "year": 2026,
        "url": "https://www.fns.usda.gov/cnpp/usda-food-plans-cost-food-monthly-reports",
    },
    {
        "title": "Thrifty Food Plan, 2021",
        "journal": "U.S. Department of Agriculture",
        "year": 2021,
        "url": "https://www.fns.usda.gov/cnpp/thrifty-food-plan-2021",
    },
    {
        "title": "Dietary Guidelines for Americans",
        "journal": "U.S. Department of Agriculture and U.S. Department of Health and Human Services",
        "year": 2026,
        "url": "https://www.dietaryguidelines.gov/",
    },
]

_TRENDING_MEAL_CITATIONS = [
    {
        "title": "Dietary Guidelines for Americans",
        "journal": "U.S. Department of Agriculture and U.S. Department of Health and Human Services",
        "year": 2026,
        "url": "https://www.dietaryguidelines.gov/",
    },
    {
        "title": "MyPlate: Healthy Eating on a Budget",
        "journal": "U.S. Department of Agriculture",
        "year": 2026,
        "url": "https://www.myplate.gov/eat-healthy/budget",
    },
    {
        "title": "MyPlate",
        "journal": "U.S. Department of Agriculture",
        "year": 2026,
        "url": "https://www.myplate.gov/",
    },
]

_AFFORDABILITY_ANSWER = (
    "Community Groceries is a paid $9.99/month subscription. The savings case is that "
    "better planning can reduce waste, duplicate purchases, and impulse spending, so the "
    "overall value can be better for many households. Exact savings vary by household."
)


def comparison_citations() -> List[Dict[str, Any]]:
    return deepcopy(_COMPARISON_CITATIONS)


def trending_meal_citations() -> List[Dict[str, Any]]:
    return deepcopy(_TRENDING_MEAL_CITATIONS)


def comparison_reference_block() -> str:
    return "\n".join(
        [
            "OFFICIAL REFERENCES TO USE IF YOU INCLUDE CITATIONS:",
            *[
                f'- "{item["title"]}" — {item["journal"]} ({item["year"]}) {item["url"]}'
                for item in _COMPARISON_CITATIONS
            ],
        ]
    )


def trending_reference_block() -> str:
    return "\n".join(
        [
            "OFFICIAL REFERENCES TO USE IF YOU INCLUDE CITATIONS:",
            *[
                f'- "{item["title"]}" — {item["journal"]} ({item["year"]}) {item["url"]}'
                for item in _TRENDING_MEAL_CITATIONS
            ],
        ]
    )


def _get_approved_citation_urls() -> set[str]:
    """Get set of approved citation URLs for validation."""
    all_citations = _COMPARISON_CITATIONS + _TRENDING_MEAL_CITATIONS
    return set(c.get("url", "").lower() for c in all_citations if c.get("url"))


def validate_citations(citations: List[Dict[str, Any]], citation_type: str = "meal") -> Dict[str, Any]:
    """Validate that all citations in a page are from approved sources.
    
    Args:
        citations: List of citation dicts from page payload
        citation_type: "meal", "comparison", or "health"
    
    Returns:
        {
            "valid": bool,
            "invalid_count": int,
            "invalid_citations": list of invalid citations,
            "message": str
        }
    """
    if citation_type in ("meal", "comparison"):
        approved = _get_approved_citation_urls()
    else:
        # For health posts, allow PubMed URLs
        approved = _get_approved_citation_urls() | {
            "https://pubmed.ncbi.nlm.nih.gov/",
            "https://pmc.ncbi.nlm.nih.gov/",
            "https://www.ncbi.nlm.nih.gov/",
        }
    
    if not citations:
        return {
            "valid": True,
            "invalid_count": 0,
            "invalid_citations": [],
            "message": "No citations to validate"
        }
    
    invalid = []
    for cite in citations:
        url = cite.get("url", "").lower()
        # Check if URL starts with any approved domain
        is_valid = any(url.startswith(approved_url) for approved_url in approved)
        if not is_valid:
            invalid.append({
                "title": cite.get("title"),
                "url": cite.get("url"),
                "reason": "URL not in approved citation pool"
            })
    
    return {
        "valid": len(invalid) == 0,
        "invalid_count": len(invalid),
        "invalid_citations": invalid,
        "message": f"{len(invalid)} citations from unapproved sources" if invalid else "All citations from approved sources"
    }


def _normalize_table_rows(text: str) -> str:
    text = re.sub(
        r"(\|\s*Subscription Requirement\s*\|\s*)No(\s*\|)",
        r"\1Yes, $9.99/month\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(\|\s*Subscription Requirement\s*\|[^\n|]*\|\s*)No(\s*\|)",
        r"\1Yes, $9.99/month\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(\|\s*Subscription Model\s*\|\s*)Flexible, no commitment(\s*\|)",
        r"\1Flexible $9.99/month membership\2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(\|\s*Subscription Model\s*\|[^\n|]*\|\s*)Flexible, no commitment(\s*\|)",
        r"\1Flexible $9.99/month membership\2",
        text,
        flags=re.IGNORECASE,
    )
    return text


def normalize_comparison_text(text: str) -> str:
    if not text:
        return text
    text = _normalize_table_rows(text)
    replacements = [
        ("No, Community Groceries does not require a subscription", "Yes. Community Groceries is a $9.99/month subscription"),
        ("Community Groceries does not require a subscription", "Community Groceries requires a $9.99/month subscription"),
        ("without the commitment of a subscription", "with a lower fixed $9.99/month membership cost"),
        ("without the need for a subscription", "with a $9.99/month subscription"),
        ("better long-term value with a lower fixed $9.99/month membership cost and more flexibility", "better long-term value, plus a lower fixed $9.99/month membership cost"),
        ("Flexible, no commitment", "Flexible $9.99/month membership"),
        ("free alternative", "lower fixed-cost alternative"),
        ("no subscription", "$9.99/month subscription"),
        ("No subscription", "$9.99/month subscription"),
        ("no commitment", "paid $9.99/month membership"),
        ("No commitment", "Paid $9.99/month membership"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = re.sub(
        r"(?:costs?|pricing)\s+(?:between|from)\s+\$\d+(?:\.\d+)?\s+(?:and|to|-)\s+\$\d+(?:\.\d+)?\s+per meal",
        "pricing varies by plan size, promotions, shipping, and add-ons",
        text,
        flags=re.IGNORECASE,
    )
    return text


def sanitize_comparison_post(post: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(post)
    updated["body"] = normalize_comparison_text(str(updated.get("body", "")))
    updated["citations"] = comparison_citations()

    faq_items = []
    for item in updated.get("faq_items", []) or []:
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()
        question_lower = question.lower()

        if "subscription" in question_lower:
            answer = "Yes. Community Groceries is a $9.99/month subscription."
        elif any(token in question_lower for token in ["affordable", "cost-effective", "cheaper", "save", "worth it"]):
            answer = _AFFORDABILITY_ANSWER
        else:
            answer = normalize_comparison_text(answer)

        faq_items.append({"question": question, "answer": answer})

    updated["faq_items"] = faq_items
    updated["key_takeaways"] = [
        normalize_comparison_text(str(item)) for item in (updated.get("key_takeaways", []) or [])
    ]
    if not updated.get("key_takeaways"):
        updated["key_takeaways"] = [
            "Community Groceries is a paid $9.99/month subscription.",
            "The value case is better planning against a much larger household food budget.",
            "Exact savings vary by household, but reducing waste and duplicate purchases can improve overall value.",
        ]
    updated["word_count"] = len(str(updated.get("body", "")).split())
    return updated


def sanitize_trending_post(post: Dict[str, Any]) -> Dict[str, Any]:
    updated = deepcopy(post)
    updated["citations"] = trending_meal_citations()
    updated["word_count"] = len(str(updated.get("body", "")).split())
    return updated