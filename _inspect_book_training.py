import json

with open("data/book_refs/book_references_training_unicode_issues.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Get unique output values (the model's trained responses about the book)
seen = set()
for item in data:
    out = item.get("output", "")[:300]
    instruction = item.get("instruction", "")[:100]
    if out not in seen and len(out) > 50:
        seen.add(out)
        print(f"Q: {instruction}")
        print(f"A: {out}")
        print("---")
    if len(seen) > 30:
        break
