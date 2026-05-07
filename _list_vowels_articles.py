"""List all published vowels articles sorted by date"""
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"projectId": "wihy-ai"})

db = firestore.client()
docs = (
    db.collection("vowels_articles")
    .limit(50)
    .stream()
)

articles = []
for d in docs:
    a = d.to_dict()
    articles.append({
        "slug": a.get("slug", ""),
        "title": a.get("title", ""),
        "published": str(a.get("publishedAt", ""))[:10],
        "words": a.get("word_count", 0),
        "topic": a.get("topic_slug", ""),
    })

for a in articles:
    print(f"{a['published']}  {a['words']:>5}w  {a['topic']:30}  {a['title'][:65]}")
    print(f"  https://vowels.org/article/{a['slug']}")
    print()
