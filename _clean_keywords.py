import json
from collections import Counter

with open('data/health_keywords_all.json') as f:
    data = json.load(f)

clean = [k for k in data['keywords'] if 'environmental-impact-and-food-processing' not in k['slug']]
data['keywords'] = clean
data['total'] = len(clean)

with open('data/health_keywords_all.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'After cleanup: {len(clean)} keywords')
print()
tc = Counter(k['topic_slug'] for k in clean)
for t, c in tc.most_common():
    print(f'  {t}: {c}')
print()
print('Top 30:')
for k in clean[:30]:
    print(f"  {k['ask_count']:>3}x  {k['slug']}")
