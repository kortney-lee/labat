import json
from pathlib import Path

src = Path('data/gsc_all_queries.json')
if not src.exists():
    raise SystemExit('Missing data/gsc_all_queries.json. Run _gsc_all_queries.py first.')

data = json.loads(src.read_text(encoding='utf-8'))
queries = data.get('queries', [])

meal_terms = [
    'meal', 'meals', 'meal prep', 'recipe', 'recipes',
    'breakfast', 'lunch', 'dinner', 'snack', 'high protein',
    'weight loss meals', 'healthy meals', 'low carb', 'keto meal', 'vegan meal',
]

noise = [
    'near me', 'store', 'delivery', 'kansas', 'troost',
    'community grocery', 'community grocer', 'phone', 'hours',
]

meal_rows = []
for r in queries:
    q = (r.get('query') or '').lower().strip()
    if not q:
        continue
    if any(n in q for n in noise):
        continue
    if any(t in q for t in meal_terms):
        meal_rows.append(r)

meal_rows.sort(key=lambda x: (x.get('impressions', 0), x.get('clicks', 0)), reverse=True)

print('Total GSC queries:', len(queries))
print('Meal-intent queries found:', len(meal_rows))
print('\nTop meal-intent GSC queries:')
for row in meal_rows[:40]:
    print(f"{row.get('impressions',0):>5} impr | {row.get('clicks',0):>3} clicks | pos {row.get('position',0):>5.1f} | {row.get('query')}")

Path('data').mkdir(exist_ok=True)
Path('data/gsc_trending_meals.json').write_text(
    json.dumps({'total': len(meal_rows), 'queries': meal_rows[:200]}, indent=2),
    encoding='utf-8'
)
print('\nSaved: data/gsc_trending_meals.json')
