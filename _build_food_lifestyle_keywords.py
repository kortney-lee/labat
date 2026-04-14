"""Scrape Google autocomplete for remaining content gaps:
specific foods, cooking/lifestyle, fitness, and wellness keywords.
Merge into wihy_content_keywords.json."""

import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

KW_FILE = Path("data/wihy_content_keywords.json")

SEEDS = [
    # === SPECIFIC FOODS ===
    "eggs health benefits", "are eggs healthy", "eggs cholesterol myth",
    "avocado health benefits", "avocado nutrition", "is avocado good for you",
    "salmon health benefits", "salmon vs tilapia", "best fish to eat",
    "fish oil benefits", "omega 3 foods",
    "almonds health benefits", "walnuts health benefits", "cashews vs almonds",
    "best nuts for health", "pistachio benefits",
    "blueberries health benefits", "strawberries health benefits", "acai berries benefits",
    "best berries for health", "berries antioxidants",
    "oatmeal health benefits", "overnight oats healthy", "oats vs granola",
    "olive oil health benefits", "extra virgin olive oil benefits", "best cooking oil",
    "dark chocolate health benefits", "cacao benefits", "cocoa vs cacao",
    "sweet potato health benefits", "sweet potato vs potato",
    "broccoli health benefits", "cruciferous vegetables benefits", "cauliflower benefits",
    "kale health benefits", "best vegetables for health",
    "beans health benefits", "lentils health benefits", "chickpeas benefits",
    "legumes vs beans", "best legumes for protein",
    "yogurt health benefits", "kefir benefits", "greek yogurt vs regular yogurt",
    "probiotic yogurt benefits",
    "brown rice vs white rice", "is rice healthy", "rice nutrition",
    "sourdough bread benefits", "whole grain bread benefits", "is bread healthy",
    "red meat health risks", "is beef bad for you", "grass fed beef benefits",
    "chicken breast nutrition", "chicken vs fish", "is chicken healthy",
    "tofu health benefits", "tempeh benefits", "soy health benefits",
    "edamame benefits", "is soy bad for you",
    "protein powder benefits", "whey protein benefits", "pea protein vs whey",
    "best protein powder", "casein protein benefits",
    "water intake per day", "how much water should you drink", "hydration tips",
    "dehydration symptoms", "water fasting benefits",
    # === COOKING / LIFESTYLE ===
    "air fryer healthy", "is air frying healthy", "best cooking methods for health",
    "steaming vs boiling", "grilling health risks",
    "food storage tips", "how to store vegetables", "shelf life of food",
    "portion control tips", "serving size guide", "how to eat less",
    "food label reading guide", "how to read nutrition labels", "hidden sugar in food",
    "organic vs conventional", "is organic food healthier", "dirty dozen produce",
    "clean fifteen", "pesticides in food",
    "seasonal eating benefits", "seasonal fruits and vegetables", "eating local benefits",
    "meal prep for weight loss", "meal prep for beginners",
    "grocery shopping on a budget", "healthy budget meals",
    # === FITNESS GAPS ===
    "stretching benefits", "best stretches", "morning stretching routine",
    "yoga for beginners", "yoga health benefits", "flexibility exercises",
    "running health benefits", "running for weight loss", "how to start running",
    "couch to 5k", "marathon training tips",
    "muscle recovery tips", "rest day importance", "DOMS treatment",
    "post workout recovery", "muscle soreness remedies",
    "walking health benefits", "walking for weight loss", "10000 steps myth",
    "walking vs running", "daily walking benefits",
    # === WELLNESS GAPS ===
    "meditation health benefits", "meditation for beginners", "mindfulness exercises",
    "breathing exercises for anxiety", "best meditation apps",
    "anti aging foods", "longevity diet", "blue zones diet",
    "aging gracefully tips", "best foods for longevity",
    "autoimmune diet", "autoimmune protocol diet", "AIP diet food list",
    "leaky gut autoimmune", "best foods for autoimmune",
]

_TOPIC_MAP = {
    "egg": "nutrition", "avocado": "nutrition", "salmon": "nutrition",
    "fish": "nutrition", "omega": "nutrition", "almond": "nutrition",
    "walnut": "nutrition", "cashew": "nutrition", "nut": "nutrition",
    "pistachio": "nutrition", "blueberr": "nutrition", "strawberr": "nutrition",
    "acai": "nutrition", "berr": "nutrition", "oat": "nutrition",
    "granola": "nutrition", "olive oil": "nutrition", "cooking oil": "nutrition",
    "chocolate": "nutrition", "cacao": "nutrition", "cocoa": "nutrition",
    "sweet potato": "nutrition", "potato": "nutrition", "broccoli": "nutrition",
    "cruciferous": "nutrition", "cauliflower": "nutrition", "kale": "nutrition",
    "vegetable": "nutrition", "bean": "nutrition", "lentil": "nutrition",
    "chickpea": "nutrition", "legume": "nutrition", "yogurt": "nutrition",
    "kefir": "nutrition", "probiotic": "gut-health", "rice": "nutrition",
    "bread": "nutrition", "sourdough": "nutrition", "whole grain": "nutrition",
    "beef": "nutrition", "red meat": "nutrition", "grass fed": "nutrition",
    "chicken": "nutrition", "poultry": "nutrition", "tofu": "nutrition",
    "tempeh": "nutrition", "soy": "nutrition", "edamame": "nutrition",
    "protein powder": "supplements", "whey": "supplements", "casein": "supplements",
    "pea protein": "supplements", "water": "nutrition", "hydrat": "nutrition",
    "dehydrat": "nutrition",
    "air fry": "nutrition", "cooking": "nutrition", "steam": "nutrition",
    "grill": "nutrition", "food storage": "nutrition", "shelf life": "nutrition",
    "portion": "nutrition", "serving": "nutrition", "food label": "nutrition",
    "nutrition label": "nutrition", "hidden sugar": "nutrition",
    "organic": "nutrition", "pesticide": "nutrition", "dirty dozen": "nutrition",
    "clean fifteen": "nutrition", "seasonal": "nutrition", "eating local": "nutrition",
    "meal prep": "nutrition", "grocery": "nutrition", "budget": "nutrition",
    "stretch": "fitness", "yoga": "fitness", "flexib": "fitness",
    "running": "fitness", "marathon": "fitness", "5k": "fitness",
    "couch to": "fitness", "recovery": "fitness", "rest day": "fitness",
    "doms": "fitness", "muscle sore": "fitness", "post workout": "fitness",
    "walking": "fitness", "steps": "fitness",
    "meditation": "mental-health", "mindfulness": "mental-health",
    "breathing": "mental-health",
    "aging": "nutrition", "longevity": "nutrition", "blue zone": "nutrition",
    "autoimmune": "nutrition", "aip": "nutrition", "leaky gut": "gut-health",
}

_INTENT_MAP = {
    "benefits": "benefits", "side effects": "risks", "risks": "risks",
    "myth": "informational", "vs": "comparisons", "best": "best_of",
    "how to": "how_to", "how much": "question", "guide": "how_to",
    "tips": "how_to", "is ": "question", "are ": "question",
    "should": "question", "can ": "question", "foods": "informational",
    "list": "informational", "for beginners": "how_to",
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
        if any(x in kw.lower() for x in ["in hindi", "in tamil", "in urdu", "in spanish",
                                           "en español", "in tagalog", "in telugu",
                                           "in marathi", "in bengali"]):
            continue
        if any(x in kw.lower() for x in ["for dogs", "for cats", "for pets",
                                           "for horses", "for chickens"]):
            continue

        topic = _classify_topic(kw)
        intent = _classify_intent(kw)
        title = kw.title()
        for old, new in [("'S", "'s"), (" And ", " and "), (" For ", " for "),
                         (" Of ", " of "), (" In ", " in "), (" The ", " the "),
                         (" To ", " to "), (" Or ", " or "), (" With ", " with "),
                         (" Vs ", " vs "), (" On ", " on "), (" A ", " a "),
                         ("Aip", "AIP"), ("Doms", "DOMS"), ("5K", "5K"),
                         ("Dha", "DHA"), ("Epa", "EPA")]:
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
