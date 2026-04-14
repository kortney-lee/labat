import json
kw = json.load(open("data/wihy_content_keywords.json"))["keywords"]
health_topics = {"nutrition","supplements","gut-health","heart-health","sugar-and-blood-health","processed-foods","fasting","alcohol-and-health","protein-and-muscle","hydration","immune-health","longevity","hormones","brain-health"}
count = 0
for k in kw:
    if k.get("topic_slug") in health_topics and count < 15:
        print(f"{k['slug']:50s} | {k['keyword'][:60]}")
        count += 1
