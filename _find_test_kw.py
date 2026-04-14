import json
d = json.load(open("data/wihy_content_keywords.json", "r", encoding="utf-8"))
prog = json.load(open("data/wihy_posts_progress.json", "r", encoding="utf-8"))
done = set(prog.get("completed", []))
matches = [k for k in d["keywords"] if k["slug"] not in done and ("app" in k["keyword"].lower() or "scanner" in k["keyword"].lower())]
for m in matches[:10]:
    print(f'{m["slug"]:50s} {m["topic_slug"]:15s} {m["intent"]}')
