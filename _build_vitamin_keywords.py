"""Scrape Google autocomplete for vitamin & mineral keywords
and merge into wihy_content_keywords.json."""

import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

KW_FILE = Path("data/wihy_content_keywords.json")

SEEDS = [
    # Individual vitamins
    "vitamin a benefits", "vitamin a deficiency", "vitamin a foods",
    "vitamin b benefits", "vitamin b complex benefits", "vitamin b12 benefits",
    "vitamin b12 deficiency", "vitamin b6 benefits", "vitamin b6 deficiency",
    "vitamin c benefits", "vitamin c deficiency", "vitamin c foods",
    "vitamin d benefits", "vitamin d deficiency", "vitamin d foods",
    "vitamin e benefits", "vitamin e for skin", "vitamin e deficiency",
    "vitamin k benefits", "vitamin k deficiency", "vitamin k foods",
    # B vitamins
    "biotin benefits", "folate benefits", "folic acid benefits",
    "niacin benefits", "thiamine benefits", "riboflavin benefits",
    # Minerals
    "iron benefits", "iron deficiency symptoms", "iron rich foods",
    "calcium benefits", "calcium deficiency", "calcium rich foods",
    "magnesium benefits", "magnesium deficiency", "magnesium for sleep",
    "potassium benefits", "potassium deficiency", "potassium rich foods",
    "zinc benefits", "zinc deficiency", "zinc for immune system",
    "selenium benefits", "selenium deficiency",
    "iodine benefits", "iodine deficiency",
    "chromium benefits", "chromium for blood sugar",
    "manganese benefits",
    "copper benefits", "copper deficiency",
    "phosphorus benefits",
    # Combos & categories
    "multivitamin benefits", "prenatal vitamins benefits",
    "vitamin deficiency symptoms", "electrolyte benefits",
    "electrolyte drinks benefits", "mineral supplements benefits",
    "water soluble vitamins", "fat soluble vitamins",
    "best vitamins for women", "best vitamins for men",
    "best vitamins for energy", "best vitamins for hair growth",
    "best vitamins for immune system", "best vitamins for skin",
    "best vitamins for anxiety", "best vitamins for brain health",
    "best vitamins for heart health", "best vitamins for kids",
    "best vitamins for seniors", "best vitamins for pregnancy",
    # Trending vitamin topics
    "vitamin d3 vs d2", "vitamin d and covid",
    "magnesium glycinate benefits", "magnesium threonate benefits",
    "zinc and vitamin c together", "b12 shots benefits",
    "methylfolate vs folic acid", "chelated minerals",
    "liposomal vitamin c", "CoQ10 benefits",
]

_TOPIC_MAP = {
    "vitamin": "supplements", "b12": "supplements", "b6": "supplements",
    "biotin": "supplements", "folate": "supplements", "folic acid": "supplements",
    "niacin": "supplements", "thiamine": "supplements", "riboflavin": "supplements",
    "iron": "nutrition", "calcium": "nutrition", "magnesium": "supplements",
    "potassium": "nutrition", "zinc": "supplements", "selenium": "supplements",
    "iodine": "supplements", "chromium": "supplements", "manganese": "supplements",
    "copper": "nutrition", "phosphorus": "nutrition", "sodium": "nutrition",
    "multivitamin": "supplements", "prenatal": "supplements",
    "electrolyte": "nutrition", "mineral": "supplements",
    "coq10": "supplements", "liposomal": "supplements",
    "chelated": "supplements", "methylfolate": "supplements",
}

_INTENT_MAP = {
    "benefits": "benefits", "side effects": "risks", "deficien": "informational",
    "symptoms": "question", "how to": "how_to", "vs": "comparisons",
    "best": "best_of", "reddit": "informational", "foods": "informational",
    "rich": "informational",
}


def _slugify(text):
    s = text.lower().strip()
    s = re.sub(r"[''']s\b", "s", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _classify_topic(kw):
    kw_lower = kw.lower()
    for term, topic in _TOPIC_MAP.items():
        if term in kw_lower:
            return topic
    return "nutrition"


def _classify_intent(kw):
    kw_lower = kw.lower()
    for term, intent in _INTENT_MAP.items():
        if term in kw_lower:
            return intent
    if kw_lower.startswith(("is ", "are ", "does ", "do ", "can ", "should ")):
        return "question"
    return "informational"


def scrape_autocomplete(seed):
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.request.quote(seed)}"
    try:
        resp = urllib.request.urlopen(url).read()
        suggestions = json.loads(resp)[1]
        return [s for s in suggestions if s.lower() != seed.lower()]
    except Exception as e:
        print(f"  WARN: failed for '{seed}': {e}")
        return []


def main():
    data = json.loads(KW_FILE.read_text(encoding="utf-8"))
    existing_slugs = {k["slug"] for k in data["keywords"]}
    print(f"Existing keywords: {len(existing_slugs)}")

    all_suggestions = set()
    for seed in SEEDS:
        suggestions = scrape_autocomplete(seed)
        all_suggestions.update(suggestions)
        all_suggestions.add(seed)
    print(f"Google autocomplete returned {len(all_suggestions)} unique suggestions")

    new_keywords = []
    for kw in sorted(all_suggestions):
        slug = _slugify(kw)
        if slug in existing_slugs:
            continue
        if len(kw) < 10 or len(kw) > 100:
            continue
        if any(x in kw.lower() for x in ["in hindi", "in tamil", "in urdu", "in spanish", "en español", "in tagalog"]):
            continue
        if any(x in kw.lower() for x in ["for dogs", "for cats", "for pets", "for horses"]):
            continue

        topic = _classify_topic(kw)
        intent = _classify_intent(kw)
        title = kw.title()
        for old, new in [("'S", "'s"), (" And ", " and "), (" For ", " for "), (" Of ", " of "), (" In ", " in "), (" The ", " the "), (" To ", " to "), (" Or ", " or "), (" With ", " with "), (" Vs ", " vs "), ("Coq10", "CoQ10"), ("Vitamin D3", "Vitamin D3"), ("Vitamin B12", "Vitamin B12")]:
            title = title.replace(old, new)

        new_keywords.append({
            "keyword": kw,
            "slug": slug,
            "title": title,
            "topic_slug": topic,
            "intent": intent,
        })
        existing_slugs.add(slug)

    print(f"New keywords to add: {len(new_keywords)}")
    if not new_keywords:
        print("Nothing new.")
        return

    from collections import Counter
    topic_counts = Counter(k["topic_slug"] for k in new_keywords)
    print("\nNew keywords by topic:")
    for t, c in topic_counts.most_common():
        print(f"  {t}: {c}")

    data["keywords"].extend(new_keywords)
    data["total"] = len(data["keywords"])
    topic_c = Counter(k["topic_slug"] for k in data["keywords"])
    intent_c = Counter(k["intent"] for k in data["keywords"])
    data["by_topic"] = dict(topic_c.most_common())
    data["by_intent"] = dict(intent_c.most_common())
    data["extracted_at"] = datetime.now(timezone.utc).isoformat()

    KW_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved! Total keywords now: {data['total']}")


if __name__ == "__main__":
    main()
