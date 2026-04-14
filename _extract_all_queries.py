"""
Extract ALL unique health questions from production DB,
convert to blog-ready slugs + titles, output as JSON for seeding.
"""
import json
import re
import psycopg2
from collections import Counter

conn = psycopg2.connect(
    host='127.0.0.1', port=5433, user='postgres',
    password='Godiswilling1!', dbname='wihy_chat'
)
cur = conn.cursor()

# Pull ALL health/nutrition/fitness user questions
cur.execute("""
SELECT DISTINCT ON (lower_q)
    LOWER(TRIM(regexp_replace(LEFT(content, 200), '[^\x20-\x7E]', '', 'g'))) as lower_q,
    regexp_replace(LEFT(content, 200), '[^\x20-\x7E]', '', 'g') as original,
    COUNT(*) OVER (PARTITION BY LOWER(TRIM(regexp_replace(LEFT(content, 200), '[^\x20-\x7E]', '', 'g')))) as ask_count,
    COALESCE(intent, '') as intent
FROM chat_messages 
WHERE role = 'user' 
    AND content IS NOT NULL 
    AND LENGTH(content) BETWEEN 15 AND 300
    AND (
        intent IN ('health', 'food', 'nutrition_coach', 'research', 'meal_planner', 
                   'meal_meal_plans', 'fitness_coach', 'meal_shopping_list')
        OR content ~* '(calorie|protein|vitamin|diet|weight|cholesterol|diabetes|blood|sugar|fat|healthy|food|eat|meal|nutriti|exercise|workout|sleep|fasting|supplement|cancer|heart|kidney|liver|inflammation|gut|probiotic|antioxidant|omega|magnesium|zinc|iron|fiber|carb|keto|vegan|gluten|allerg|organic|processed|seed oil|red meat|alcohol|caffein|hydrat|electrolyte|intermittent|resistance train|muscle|strength|cardio|metaboli|insulin|cortisol|thyroid|autoimmune|joint|bone|skin|hair|brain|cognitive|mental|anxiety|depression|stress|longevity|aging)'
    )
    AND content NOT LIKE '%%test%%'
    AND content NOT LIKE '%%SEO%%'
    AND content NOT LIKE '%%seo%%'
    AND content NOT LIKE '%%ALEX%%'
    AND content NOT LIKE '%%alex%%'
    AND content NOT LIKE '%%build%%'
    AND content NOT LIKE '%%Build%%'
    AND content NOT LIKE '%%View meal%%'
    AND content NOT LIKE '%%Thanks%%'
    AND content NOT LIKE '%%Hello%%'
    AND content NOT LIKE '%%Hi %%'
    AND content NOT LIKE '%%@%%'
    AND content NOT LIKE '%%Complete%%'
    AND content NOT LIKE '%%yes%%'
    AND content NOT LIKE '%%Yes%%'
    AND content NOT LIKE '%%no%%'
    AND content NOT LIKE '%%okay%%'
    AND content NOT LIKE '%%sure%%'
    AND content NOT LIKE '%%http%%'
    AND LENGTH(TRIM(content)) > 20
ORDER BY lower_q, ask_count DESC
""")

rows = cur.fetchall()
conn.close()

print(f"Raw unique queries: {len(rows)}")

# ── Topic inference ──
def infer_topic(q):
    ql = q.lower()
    if any(w in ql for w in ['exercise', 'workout', 'fitness', 'resistance train', 'hiit', 'cardio', 'strength', 'muscle build', 'body workout']):
        return 'fitness'
    if any(w in ql for w in ['supplement', 'vitamin', 'creatine', 'omega', 'magnesium', 'b12', 'iron supplement', 'zinc', 'berberine', 'multivitamin', 'probiotic']):
        return 'supplements'
    if any(w in ql for w in ['fasting', 'intermittent']):
        return 'fasting'
    if any(w in ql for w in ['sugar', 'glucose', 'insulin', 'blood sugar', 'a1c', 'glycemic']):
        return 'sugar-and-blood-health'
    if any(w in ql for w in ['alcohol', 'wine', 'beer', 'drinking']):
        return 'alcohol-and-health'
    if any(w in ql for w in ['processed', 'ultra-processed', 'seed oil', 'additive', 'preservative']):
        return 'processed-foods'
    if any(w in ql for w in ['protein', 'whey', 'collagen', 'amino acid']):
        return 'protein-and-muscle'
    if any(w in ql for w in ['hydrat', 'water', 'electrolyte']):
        return 'hydration'
    return 'nutrition'

# ── Slug generation ──
def make_slug(q):
    s = q.lower().strip(' ?!.,')
    # Remove common question prefixes
    for prefix in [
        'what does the research say about ',
        'what does science say about ',
        'what does research say about ',
        'what are the health benefits of ',
        'what are the benefits of ',
        'what are the best ',
        'what are the key findings',
        'what are the effects of ',
        'what are ',
        'what is the best ',
        'what is the ',
        'what is ',
        'how does ',
        'how do i ',
        'how do you ',
        'how can i ',
        'how to ',
        'is it true that ',
        'is it safe to ',
        'is it healthy to ',
        'is there ',
        'is it ',
        'are there ',
        'are ',
        'can i eat ',
        'can i ',
        'can you ',
        'does ',
        'do ',
        'should i ',
        'tell me about ',
        'explain ',
        'i want to know about ',
    ]:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    # Remove trailing noise
    for suffix in [' what are the key findings', ' and how does it work', ' for health']:
        if s.endswith(suffix):
            s = s[:-len(suffix)]
    # Slugify
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'\s+', '-', s.strip())
    s = re.sub(r'-+', '-', s).strip('-')
    # Max length
    if len(s) > 80:
        s = s[:80].rsplit('-', 1)[0]
    return s

# ── Title generation (clean up the question) ──
def make_title(q):
    t = q.strip(' ?!.,')
    # Capitalize first letter
    if t:
        t = t[0].upper() + t[1:]
    # Add question mark if it's a question
    if any(t.lower().startswith(w) for w in ['what', 'how', 'is ', 'are ', 'can ', 'does ', 'do ', 'should', 'why']):
        if not t.endswith('?'):
            t += '?'
    return t

# ── Deduplicate by slug ──
seen_slugs = set()
keywords = []

for lower_q, original, ask_count, intent in sorted(rows, key=lambda x: -x[2]):
    slug = make_slug(lower_q)
    if not slug or len(slug) < 5 or slug in seen_slugs:
        continue
    seen_slugs.add(slug)
    
    topic = infer_topic(lower_q)
    title = make_title(original)
    
    keywords.append({
        "keyword": original.strip(),
        "slug": slug,
        "title": title,
        "topic_slug": topic,
        "ask_count": ask_count,
        "intent": intent or "informational",
    })

# ── Stats ──
print(f"Unique blog-ready slugs: {len(keywords)}")

topic_counts = Counter(k['topic_slug'] for k in keywords)
print(f"\nBy topic:")
for topic, count in topic_counts.most_common():
    print(f"  {topic}: {count}")

print(f"\nTop 20 most-asked:")
for k in keywords[:20]:
    print(f"  {k['ask_count']:>3}x  {k['slug']}")

# ── Save ──
output = {
    "total": len(keywords),
    "extracted_at": "2026-04-07",
    "keywords": keywords,
}

with open("data/health_keywords_all.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nSaved to data/health_keywords_all.json")
