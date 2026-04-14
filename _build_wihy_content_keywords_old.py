"""
Build generate-ready keyword file from WIHY autocomplete research data.

Reads: data/wihy_autocomplete_clean_apr9_2026.json (7,415 keywords)
Outputs: data/wihy_content_keywords.json (clustered + deduped articles)

Pipeline: autocomplete → this script → generate_health_posts.py --keywords data/wihy_content_keywords.json --brand wihy
"""
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

INPUT_FILE = Path("data/wihy_autocomplete_clean_apr9_2026.json")
OUTPUT_FILE = Path("data/wihy_content_keywords.json")
PROGRESS_FILE = Path("data/health_posts_progress.json")


def to_slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    # Cap at 80 chars for URL friendliness
    if len(s) > 80:
        s = s[:80].rsplit("-", 1)[0]
    return s


def to_title(text: str) -> str:
    """Convert keyword to title case, cleaning up."""
    # Capitalize first letter of each word, but keep small words lowercase
    small = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "vs"}
    words = text.strip().split()
    result = []
    for i, w in enumerate(words):
        if i == 0 or w.lower() not in small:
            result.append(w.capitalize())
        else:
            result.append(w.lower())
    return " ".join(result)


def normalize_for_dedup(text: str) -> str:
    """Normalize a keyword for deduplication clustering."""
    s = text.lower().strip()
    # Remove common noise words that create near-duplicates
    s = re.sub(r"\b(the|a|an|app|apps|application|applications)\b", "", s)
    s = re.sub(r"\b(best|top|most popular)\b", "best", s)
    s = re.sub(r"\b(free|no cost|without paying)\b", "free", s)
    s = re.sub(r"\b(review|reviews|reviewed)\b", "review", s)
    s = re.sub(r"\b(tracker|tracking|track)\b", "track", s)
    s = re.sub(r"\b(counter|counting|count)\b", "count", s)
    s = re.sub(r"\b(planner|planning|plan)\b", "plan", s)
    s = re.sub(r"\b(scanner|scanning|scan)\b", "scan", s)
    s = re.sub(r"\b(nutrition|nutritional|nutrient)\b", "nutrition", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def pick_best_keyword(cluster: list) -> dict:
    """From a cluster of near-duplicate keywords, pick the best one."""
    # Prefer: highest seen_count, then shortest length (more searchable)
    cluster.sort(key=lambda k: (-k["seen_count"], len(k["keyword"])))
    best = cluster[0]
    # Aggregate seen_count from all variants
    best["ask_count"] = sum(k["seen_count"] for k in cluster)
    best["variants"] = len(cluster)
    return best


def load_existing_slugs() -> set:
    """Load already-generated slugs to avoid duplicates."""
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    return set()


def main():
    if not INPUT_FILE.exists():
        print(f"Missing {INPUT_FILE}")
        return

    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    keywords = data.get("keywords", [])
    print(f"Loaded {len(keywords)} raw keywords")

    existing_slugs = load_existing_slugs()
    print(f"Already generated: {len(existing_slugs)} slugs (will skip)")

    # ── Step 1: Cluster near-duplicates ───────────────────────────────────
    clusters = defaultdict(list)
    for kw in keywords:
        norm = normalize_for_dedup(kw["keyword"])
        clusters[norm].append(kw)

    print(f"Clustered into {len(clusters)} unique groups (from {len(keywords)} raw)")

    # ── Step 2: Pick best keyword per cluster ─────────────────────────────
    articles = []
    for _norm, cluster in clusters.items():
        best = pick_best_keyword(cluster)
        slug = to_slug(best["keyword"])

        # Skip if already generated
        if slug in existing_slugs:
            continue
        # Skip very short slugs (noise)
        if len(slug) < 8:
            continue

        articles.append({
            "keyword": best["keyword"],
            "slug": slug,
            "title": to_title(best["keyword"]),
            "topic_slug": best.get("topic", "nutrition"),
            "ask_count": best.get("ask_count", best["seen_count"]),
            "intent": best.get("intent", "informational"),
            "competitor": best.get("competitor", "generic"),
            "variants": best.get("variants", 1),
        })

    # ── Step 3: Deduplicate by slug ───────────────────────────────────────
    seen_slugs = set()
    unique_articles = []
    for a in articles:
        if a["slug"] not in seen_slugs:
            seen_slugs.add(a["slug"])
            unique_articles.append(a)

    # ── Step 4: Sort by ask_count (highest demand first) ──────────────────
    unique_articles.sort(key=lambda a: -a["ask_count"])

    # ── Step 5: Stats ─────────────────────────────────────────────────────
    from collections import Counter
    topic_counts = Counter(a["topic_slug"] for a in unique_articles)
    intent_counts = Counter(a["intent"] for a in unique_articles)

    print(f"\nFinal: {len(unique_articles)} unique articles to generate")
    print(f"\nBy topic:")
    for t, c in topic_counts.most_common():
        print(f"  {t}: {c}")
    print(f"\nBy intent:")
    for i, c in intent_counts.most_common():
        print(f"  {i}: {c}")

    # ── Step 6: Write output ──────────────────────────────────────────────
    output = {
        "total": len(unique_articles),
        "extracted_at": str(date.today()),
        "source": "wihy_autocomplete_apr9_2026",
        "by_topic": dict(topic_counts.most_common()),
        "by_intent": dict(intent_counts.most_common()),
        "keywords": unique_articles,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWritten to {OUTPUT_FILE}")
    print(f"Top 10 keywords:")
    for a in unique_articles[:10]:
        print(f"  [{a['ask_count']:>4}] {a['keyword']}  ({a['topic_slug']}/{a['intent']})")


if __name__ == "__main__":
    main()
