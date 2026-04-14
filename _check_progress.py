import json
d = json.load(open("data/wihy_posts_progress.json"))
print(f"Completed: {d.get('count', 0)}")
for s in d.get("completed", []):
    print(f"  {s}")
