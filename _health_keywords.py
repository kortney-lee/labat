"""Extract nutrition & health keyword clusters from real user queries"""
import psycopg2
from collections import Counter

conn = psycopg2.connect(
    host='127.0.0.1', port=5433, user='postgres',
    password='Godiswilling1!', dbname='wihy_chat'
)
cur = conn.cursor()

# ── 1. All unique health/nutrition/food questions ──
cur.execute("""
SELECT regexp_replace(LEFT(content, 150), '[^\x20-\x7E]', '', 'g') as q,
       COUNT(*) as cnt,
       COALESCE(intent, '?') as intent
FROM chat_messages 
WHERE role = 'user' 
    AND content IS NOT NULL 
    AND LENGTH(content) BETWEEN 15 AND 300
    AND (
        intent IN ('health', 'food', 'nutrition_coach', 'research', 'meal_planner', 'meal_meal_plans', 'fitness_coach')
        OR content ~* '(calorie|protein|vitamin|diet|weight|cholesterol|diabetes|blood|sugar|fat|healthy|food|eat|meal|nutriti|exercise|workout|sleep|fasting)'
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
    AND content NOT LIKE '%%@%%'
    AND content NOT LIKE '%%Complete%%'
    AND content NOT LIKE '%%What does the research say about environmental%%'
GROUP BY regexp_replace(LEFT(content, 150), '[^\x20-\x7E]', '', 'g'), intent
ORDER BY cnt DESC
LIMIT 200
""")

rows = cur.fetchall()

# ── Categorize into clusters ──
clusters = {
    'DIET & WEIGHT LOSS': [],
    'SPECIFIC FOODS & INGREDIENTS': [],
    'VITAMINS & SUPPLEMENTS': [],
    'CHRONIC CONDITIONS & MEDS': [],
    'MEAL PLANNING & RECIPES': [],
    'FITNESS & EXERCISE': [],
    'FOOD SAFETY & LABELS': [],
    'SCIENCE & RESEARCH': [],
    'GENERAL HEALTH': [],
}

def categorize(q):
    ql = q.lower()
    if any(w in ql for w in ['weight loss', 'lose weight', 'belly fat', 'keto', 'low-fat', 'diet for', 'fasting', 'calorie']):
        return 'DIET & WEIGHT LOSS'
    if any(w in ql for w in ['meal plan', 'recipe', 'grocery list', 'breakfast', 'dinner', 'dessert', 'make ', 'cook']):
        return 'MEAL PLANNING & RECIPES'
    if any(w in ql for w in ['vitamin', 'supplement', 'multivitamin', 'creatine', 'omega', 'magnesium', 'berberine', 'b12', 'iron']):
        return 'VITAMINS & SUPPLEMENTS'
    if any(w in ql for w in ['diabetes', 'blood pressure', 'cholesterol', 'kidney', 'acid reflux', 'celiac', 'ibs', 'blood thinner', 'medication', 'metformin', 'statin', 'gout']):
        return 'CHRONIC CONDITIONS & MEDS'
    if any(w in ql for w in ['workout', 'exercise', 'hiit', 'weightlifting', 'resistance', 'fitness', 'home workout', 'body workout']):
        return 'FITNESS & EXERCISE'
    if any(w in ql for w in ['label', 'ingredient', 'processed', 'additive', 'carcinogen', 'safe', 'nova']):
        return 'FOOD SAFETY & LABELS'
    if any(w in ql for w in ['research', 'study', 'evidence', 'science say', 'findings']):
        return 'SCIENCE & RESEARCH'
    if any(w in ql for w in ['chicken', 'rice', 'milk', 'oat', 'almond', 'egg', 'salmon', 'broccoli', 'coffee', 'protein in', 'calories in', 'macros', 'food']):
        return 'SPECIFIC FOODS & INGREDIENTS'
    return 'GENERAL HEALTH'

for q, cnt, intent in rows:
    cat = categorize(q)
    clusters[cat].append((cnt, q, intent))

# ── Print ──
print("=" * 100)
print("NUTRITION & HEALTH: WHAT REAL USERS ASK  (clustered by topic)")
print("=" * 100)

total = sum(cnt for q, cnt, _ in rows)
print(f"\nTotal health/nutrition queries: {total}")
print(f"Unique questions: {len(rows)}\n")

for cluster_name in ['DIET & WEIGHT LOSS', 'CHRONIC CONDITIONS & MEDS', 'SPECIFIC FOODS & INGREDIENTS', 
                      'VITAMINS & SUPPLEMENTS', 'MEAL PLANNING & RECIPES', 'FITNESS & EXERCISE',
                      'FOOD SAFETY & LABELS', 'SCIENCE & RESEARCH', 'GENERAL HEALTH']:
    items = clusters[cluster_name]
    if not items:
        continue
    cluster_total = sum(c for c,_,_ in items)
    print(f"\n{'='*80}")
    print(f"  {cluster_name} ({cluster_total} queries, {len(items)} unique)")
    print(f"{'='*80}")
    for cnt, q, intent in sorted(items, key=lambda x: -x[0])[:20]:
        print(f"  {cnt:>4}x  {q}")

# ── Extract pure keyword phrases for SEO ──
print(f"\n\n{'='*100}")
print("TOP KEYWORD PHRASES FOR SEO (extracted from questions)")
print("="*100)

# Simple keyword extraction
keyword_phrases = Counter()
for q, cnt, _ in rows:
    ql = q.lower().strip('?! .')
    # Remove "what does science say about" prefixes
    for prefix in ['what does science say about ', 'what does research say about ', 
                   'what are the ', 'how do i ', 'how to ', 'is ', 'are ', 'can i ',
                   'what should i ', 'what is ', 'what are ']:
        if ql.startswith(prefix):
            ql = ql[len(prefix):]
            break
    # Remove trailing "what are the key findings"
    for suffix in [' what are the key findings', '?']:
        if ql.endswith(suffix):
            ql = ql[:-len(suffix)]
    if len(ql) > 10 and len(ql) < 80:
        keyword_phrases[ql] += cnt

print(f"\n{'Count':>6}  Keyword phrase")
print("-" * 80)
for phrase, cnt in keyword_phrases.most_common(60):
    print(f"{cnt:>6}  {phrase}")

conn.close()
