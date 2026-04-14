import json, sys
from google.cloud import storage

client = storage.Client()
bucket = client.bucket("cg-web-assets")

blob = bucket.blob("blog/posts/who-should-avoid-fasting.json")
print(f"Exists: {blob.exists()}")
if blob.exists():
    post = json.loads(blob.download_as_text())
    print(f"hero_image: {post.get('hero_image', 'MISSING')}")

sys.path.insert(0, ".")
from src.labat.services.blog_writer import update_blog_index
posts = update_blog_index("communitygroceries")
print(f"Index rebuilt: {len(posts)} posts")

img_blobs = list(bucket.list_blobs(prefix="images/blog/"))
img_slugs = set(
    b.name.split("/")[-1].replace("-hero.jpg", "")
    for b in img_blobs if b.name.endswith("-hero.jpg")
)
missing = [p["slug"] for p in posts if p["slug"] not in img_slugs]
print(f"Still missing images: {len(missing)}")
for m in missing:
    print(f"  {m}")
