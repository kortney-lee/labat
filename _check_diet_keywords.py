"""Quick check: find all diet/holistic/trend keywords in the WIHY keyword set."""
import json, re

data = json.loads(open("data/wihy_content_keywords.json").read())
diet_words = [
    "diet", "holistic", "whole food", "clean eat", "detox", "superfood",
    "alkaline", "paleo", "keto", "mediterranean", "plant.based", "vegan",
    "carnivore", "ayurved", "functional", "trend", "fad", "anti.inflammat",
    "elimination", "dash diet", "fodmap", "zone diet", "atkins", "whole30",
    "macro", "calorie count", "intuitive eating", "mindful eating",
]
pattern = "|".join(diet_words)
matches = [k for k in data["keywords"] if re.search(pattern, k["keyword"], re.IGNORECASE)]
print(f"Found {len(matches)} diet/holistic/trend keywords out of {data['total']}:\n")
for m in sorted(matches, key=lambda x: x["keyword"]):
    print(f"  [{m.get('topic_slug','')}] {m['keyword']}")
