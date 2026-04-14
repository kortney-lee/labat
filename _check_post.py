"""Quick check of a generated post from GCS."""
import json, sys
from google.cloud import storage

slug = sys.argv[1] if len(sys.argv) > 1 else "what-is-ai-nutrition"
client = storage.Client(project="wihy-ai")
bucket = client.bucket("wihy-web-assets")
blob = bucket.blob(f"blog/posts/{slug}.json")
post = json.loads(blob.download_as_text())

print(f"TITLE: {post.get('title')}")
print(f"TOPIC: {post.get('topic_slug')}")
print(f"ROUTE: {post.get('route_path')}")
print(f"WORDS: {post.get('word_count')}")
print()
print("CITATIONS:")
for c in post.get("citations", []):
    t = c.get("title", "?")
    j = c.get("journal", "?")
    y = c.get("year", "?")
    print(f"  - {t} ({j} {y})")
print()
print("FAQ:")
for f in post.get("faq_items", []):
    print(f"  Q: {f.get('question','?')}")
print()
print("BODY (first 1200 chars):")
print(post.get("body", "")[:1200])
