"""Fix duplicate titles by differentiating the post with the typo slug."""
import httpx
import json
import subprocess
import tempfile
from pathlib import Path

GCS_BUCKET = "gs://wihy-web-assets/blog/posts"
GCLOUD = r"C:\Users\Kortn\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

def fix_duplicate_title():
    # The typo-slug post gets a differentiated title
    slug = "why-fitbit-versa-2-wrog-time"
    r = httpx.get(f"https://storage.googleapis.com/wihy-web-assets/blog/posts/{slug}.json", timeout=15)
    post = r.json()
    
    old_title = post["title"]
    post["title"] = "How to Fix Wrong Time on Fitbit Versa 2"
    post["meta_description"] = "Step-by-step guide to fix the wrong time display on your Fitbit Versa 2. Covers time zone, sync, and restart fixes."
    
    print(f"Title: {old_title} -> {post['title']}")
    
    # Upload
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(post, f, indent=2, default=str)
        tmp_path = f.name
    
    subprocess.run([GCLOUD, "storage", "cp", tmp_path, f"{GCS_BUCKET}/{slug}.json"], check=True, capture_output=True)
    Path(tmp_path).unlink(missing_ok=True)
    
    print(f"Updated {slug} in GCS")
    
    # Also update index.json
    r2 = httpx.get("https://storage.googleapis.com/wihy-web-assets/blog/posts/index.json", timeout=15)
    index = r2.json()
    for p in index.get("posts", []):
        if p["slug"] == slug:
            p["title"] = post["title"]
            p["meta_description"] = post["meta_description"]
            break
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(index, f, indent=2, default=str)
        tmp_path = f.name
    
    subprocess.run([GCLOUD, "storage", "cp", tmp_path, f"{GCS_BUCKET}/index.json"], check=True, capture_output=True)
    Path(tmp_path).unlink(missing_ok=True)
    
    print("Updated index.json")

if __name__ == "__main__":
    fix_duplicate_title()
