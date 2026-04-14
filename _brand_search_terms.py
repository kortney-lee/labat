from __future__ import annotations

import json
from collections import defaultdict

import httpx

SUGGEST_URL = "https://suggestqueries.google.com/complete/search"
BRANDS = ["hellofresh", "factor", "myfitnesspal"]
MODIFIERS = [
    "",
    " review",
    " reviews",
    " vs",
    " alternatives",
    " cost",
    " price",
    " promo code",
    " coupon",
    " login",
    " app",
    " healthy",
    " meal plan",
    " macros",
    " calories",
    " worth it",
    " cancel",
    " free trial",
    " recipes",
    " discount",
]


def fetch(client: httpx.Client, query: str) -> list[str]:
    r = client.get(
        SUGGEST_URL,
        params={"client": "firefox", "hl": "en", "gl": "us", "q": query},
        timeout=10.0,
    )
    r.raise_for_status()
    payload = r.json()
    return payload[1] if isinstance(payload, list) and len(payload) > 1 else []


with httpx.Client() as client:
    results: dict[str, list[str]] = {}
    for brand in BRANDS:
        seen = set()
        rows = []
        for modifier in MODIFIERS:
            query = f"{brand}{modifier}"
            for item in fetch(client, query):
                item = str(item).strip().lower()
                if item and item not in seen:
                    seen.add(item)
                    rows.append(item)
        results[brand] = sorted(rows)

    print(json.dumps(results, indent=2))

    print("\n=== CLUSTERS ===")
    for brand, rows in results.items():
        buckets = defaultdict(list)
        for item in rows:
            text = item.lower()
            if any(x in text for x in ["review", "reviews", "worth it"]):
                buckets["reviews_trust"].append(item)
            elif any(x in text for x in ["cost", "price", "coupon", "promo", "discount", "free trial"]):
                buckets["pricing_offers"].append(item)
            elif any(x in text for x in ["cancel", "login", "app"]):
                buckets["account_ops"].append(item)
            elif "vs" in text or "alternative" in text or "compared" in text:
                buckets["comparisons"].append(item)
            elif any(x in text for x in ["healthy", "calories", "macro", "meal plan", "recipes"]):
                buckets["health_use_case"].append(item)
            else:
                buckets["other"].append(item)

        print(f"\n[{brand}]")
        for name in ["reviews_trust", "pricing_offers", "account_ops", "comparisons", "health_use_case", "other"]:
            vals = buckets.get(name, [])
            if not vals:
                continue
            print(f"  {name}: {len(vals)}")
            for v in vals[:20]:
                print(f"    - {v}")
