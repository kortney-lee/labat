"""Analyze the saved GSC data - what food/health queries do we actually have?"""
import json

data = json.load(open('data/gsc_all_queries.json', encoding='utf-8'))
queries = data['queries']

print(f'Total GSC queries (2024-2026): {len(queries)}')
print()

food_terms = [
    'food', 'eat', 'healthy', 'health', 'nutrition', 'diet', 'calori', 'protein',
    'vitamin', 'organic', 'fresh', 'vegetable', 'veggie', 'fruit', 'grain', 'meat',
    'dairy', 'sugar', 'fat', 'fiber', 'sodium', 'ingredient', 'recipe', 'meal',
    'cook', 'produce', 'grocery list', 'supplement', 'weight', 'carb', 'gluten',
    'vegan', 'paleo', 'keto', 'omega', 'antioxidant', 'inflammatory', 'gut',
]
loc_terms = ['near me', 'store', 'delivery', 'shop', 'market', 'kansas', 'troost',
             'community grocer', 'kc ', 'in kc']

food_health = []
grocery_location = []
other = []

for r in queries:
    q = r['query'].lower()
    if any(t in q for t in food_terms):
        food_health.append(r)
    elif any(t in q for t in loc_terms):
        grocery_location.append(r)
    else:
        other.append(r)

print(f'Food/health related:    {len(food_health)}')
print(f'Location/store related: {len(grocery_location)}')
print(f'Other:                  {len(other)}')

print('\n=== FOOD/HEALTH QUERIES (sorted by impressions) ===')
food_health.sort(key=lambda x: x['impressions'], reverse=True)
for r in food_health:
    print(f"  {r['impressions']:>5} impr  {r['clicks']:>3} clicks  pos {r['position']:>5.0f}  {r['query']}")

print('\n=== OTHER NON-LOCATION QUERIES ===')
other.sort(key=lambda x: x['impressions'], reverse=True)
for r in other[:30]:
    print(f"  {r['impressions']:>5} impr  {r['clicks']:>3} clicks  {r['query']}")
