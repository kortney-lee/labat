import json
d = json.load(open("data/health_keywords_all.json"))
kws = d["keywords"]

# Group by topic
from collections import defaultdict
by_topic = defaultdict(list)
for k in kws:
    by_topic[k["topic_slug"]].append(k["slug"])

for topic in sorted(by_topic.keys()):
    slugs = by_topic[topic]
    print(f"\n{'='*80}")
    print(f"  {topic.upper()} ({len(slugs)} posts)")
    print(f"{'='*80}")
    for i, s in enumerate(slugs, 1):
        print(f"  {i:3}. {s}")

print(f"\n\nTOTAL: {len(kws)} posts across {len(by_topic)} topics")
