"""Scrape Google autocomplete for natural ingredients / holistic remedy keywords
and merge them into wihy_content_keywords.json."""

import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

KW_FILE = Path("data/wihy_content_keywords.json")

# ── Seed terms for Google autocomplete ────────────────────────────────────────
SEEDS = [
    # Core ingredients the user asked about
    "lemon water benefits", "turmeric benefits", "cinnamon health",
    "ginger benefits", "honey health benefits",
    # Trending holistic / natural remedies
    "sea moss benefits", "ashwagandha benefits", "moringa benefits",
    "bone broth benefits", "elderberry benefits", "kombucha benefits",
    "spirulina benefits", "collagen benefits", "maca root benefits",
    "aloe vera health", "manuka honey benefits", "fermented foods benefits",
    "cayenne pepper benefits", "black seed oil benefits", "shilajit benefits",
    "chamomile tea benefits", "peppermint tea benefits", "flaxseed benefits",
    "hemp seeds benefits", "chlorella benefits",
    # Extra holistic / trending
    "apple cider vinegar benefits", "coconut oil benefits",
    "chia seeds benefits", "rosemary benefits", "lavender benefits",
    "oregano oil benefits", "echinacea benefits",
    "lion's mane benefits", "reishi mushroom benefits", "cordyceps benefits",
    "magnesium benefits", "zinc benefits", "vitamin d benefits",
    "omega 3 benefits", "probiotics benefits", "prebiotics benefits",
    "berberine benefits", "creatine benefits", "glutathione benefits",
    # Diet trends
    "clean eating benefits", "detox diet", "alkaline diet",
    "whole30 diet", "anti-inflammatory diet", "holistic nutrition",
    "intuitive eating", "mindful eating", "functional medicine diet",
    "carnivore diet benefits", "elimination diet",
    "superfood smoothie", "adaptogen",
]

# Map ingredient keywords to topic_slug
_TOPIC_MAP = {
    "sea moss": "supplements", "ashwagandha": "supplements", "moringa": "supplements",
    "spirulina": "supplements", "maca": "supplements", "shilajit": "supplements",
    "chlorella": "supplements", "lion's mane": "supplements", "reishi": "supplements",
    "cordyceps": "supplements", "berberine": "supplements", "creatine": "supplements",
    "glutathione": "supplements", "magnesium": "supplements", "zinc": "supplements",
    "vitamin d": "supplements", "omega 3": "supplements", "probiotics": "supplements",
    "prebiotics": "supplements", "collagen": "supplements", "echinacea": "supplements",
    "adaptogen": "supplements",
    "turmeric": "nutrition", "cinnamon": "nutrition", "ginger": "nutrition",
    "honey": "nutrition", "garlic": "nutrition", "lemon": "nutrition",
    "bone broth": "nutrition", "elderberry": "nutrition", "flaxseed": "nutrition",
    "hemp seed": "nutrition", "chia seed": "nutrition", "coconut oil": "nutrition",
    "apple cider vinegar": "nutrition", "aloe vera": "nutrition",
    "manuka honey": "nutrition", "cayenne": "nutrition", "black seed": "nutrition",
    "chamomile": "nutrition", "peppermint": "nutrition", "rosemary": "nutrition",
    "lavender": "nutrition", "oregano": "nutrition", "green tea": "nutrition",
    "matcha": "nutrition", "ferment": "nutrition", "kombucha": "gut-health",
    "superfood": "nutrition",
    "clean eat": "nutrition", "detox": "nutrition", "alkaline": "nutrition",
    "whole30": "nutrition", "anti-inflammatory": "nutrition",
    "holistic": "nutrition", "intuitive eat": "nutrition",
    "mindful eat": "nutrition", "functional medicine": "nutrition",
    "carnivore diet": "nutrition", "elimination diet": "nutrition",
}

_INTENT_MAP = {
    "benefits": "benefits", "side effects": "risks", "how to": "how_to",
    "vs": "comparisons", "best": "best_of", "reddit": "informational",
}


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[''']s\b", "s", s)  # lion's -> lions
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _classify_topic(kw: str) -> str:
    kw_lower = kw.lower()
    for term, topic in _TOPIC_MAP.items():
        if term in kw_lower:
            return topic
    return "nutrition"


def _classify_intent(kw: str) -> str:
    kw_lower = kw.lower()
    for term, intent in _INTENT_MAP.items():
        if term in kw_lower:
            return intent
    if kw_lower.startswith(("is ", "are ", "does ", "do ", "can ", "should ")):
        return "question"
    return "informational"


def scrape_autocomplete(seed: str) -> list[str]:
    url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={urllib.request.quote(seed)}"
    try:
        resp = urllib.request.urlopen(url).read()
        suggestions = json.loads(resp)[1]
        return [s for s in suggestions if s.lower() != seed.lower()]
    except Exception as e:
        print(f"  WARN: failed for '{seed}': {e}")
        return []


def main():
    # Load existing
    data = json.loads(KW_FILE.read_text(encoding="utf-8"))
    existing_slugs = {k["slug"] for k in data["keywords"]}
    print(f"Existing keywords: {len(existing_slugs)}")

    # Scrape
    all_suggestions = set()
    for seed in SEEDS:
        suggestions = scrape_autocomplete(seed)
        all_suggestions.update(suggestions)
        # Also add the seed itself
        all_suggestions.add(seed)
    print(f"Google autocomplete returned {len(all_suggestions)} unique suggestions")

    # Filter and build keyword entries
    new_keywords = []
    for kw in sorted(all_suggestions):
        slug = _slugify(kw)
        if slug in existing_slugs:
            continue
        if len(kw) < 10 or len(kw) > 100:
            continue
        # Skip non-English or spammy
        if any(x in kw.lower() for x in ["in hindi", "in tamil", "in urdu", "in spanish", "en español", "in tagalog"]):
            continue
        # Skip pet-specific
        if any(x in kw.lower() for x in ["for dogs", "for cats", "for pets", "for horses"]):
            continue

        topic = _classify_topic(kw)
        intent = _classify_intent(kw)
        title = kw.title().replace("'S", "'s").replace(" And ", " and ").replace(" For ", " for ").replace(" Of ", " of ").replace(" In ", " in ").replace(" The ", " the ").replace(" To ", " to ").replace(" Or ", " or ").replace(" With ", " with ").replace(" On ", " on ").replace(" At ", " at ").replace(" Vs ", " vs ")

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
        print("Nothing new to add.")
        return

    # Show topic breakdown
    from collections import Counter
    topic_counts = Counter(k["topic_slug"] for k in new_keywords)
    print("\nNew keywords by topic:")
    for t, c in topic_counts.most_common():
        print(f"  {t}: {c}")

    # Merge
    data["keywords"].extend(new_keywords)
    data["total"] = len(data["keywords"])

    # Rebuild by_topic / by_intent
    topic_c = Counter(k["topic_slug"] for k in data["keywords"])
    intent_c = Counter(k["intent"] for k in data["keywords"])
    data["by_topic"] = dict(topic_c.most_common())
    data["by_intent"] = dict(intent_c.most_common())
    data["extracted_at"] = datetime.now(timezone.utc).isoformat()

    # Save
    KW_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved! Total keywords now: {data['total']}")


if __name__ == "__main__":
    main()
