"""Check SEO internal linking on wihy.ai"""
import httpx
import re
import json

def main():
    # 1. Check blog index page
    print("=== Blog Index Page ===")
    r = httpx.get("https://wihy.ai/blog", timeout=15, follow_redirects=True)
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    
    # Find all internal links
    all_links = re.findall(r'href="(/[^"]+)"', r.text)
    blog_links = [l for l in all_links if l.startswith("/blog/") or l.startswith("/insights/") or l.startswith("/fitness/") or l.startswith("/wellness/") or l.startswith("/trends/") or l.startswith("/comparison/")]
    print(f"Internal blog links found: {len(blog_links)}")
    for l in blog_links[:10]:
        print(f"  {l}")
    
    # Check SPA indicators
    has_root = 'id="root"' in r.text or 'id="__next"' in r.text
    has_app = 'id="app"' in r.text or 'id="__app"' in r.text
    print(f"SPA indicators - root: {has_root}, app: {has_app}")
    
    # Check if any post titles appear in raw HTML
    content_matches = len(re.findall(r"sugar|cereal|vitamin|protein|seed.oil|weight|supplement", r.text, re.I))
    print(f"Post keywords in raw HTML: {content_matches}")
    
    # 2. Check a specific blog post page
    print("\n=== Sample Blog Post ===")
    r2 = httpx.get("https://wihy.ai/insights/hidden-sugar-in-cereal", timeout=15, follow_redirects=True)
    print(f"Status: {r2.status_code}, Length: {len(r2.text)}")
    
    all_links2 = re.findall(r'href="(/[^"]+)"', r2.text)
    internal_links = [l for l in all_links2 if l.startswith("/blog/") or l.startswith("/insights/") or l.startswith("/fitness/") or l.startswith("/wellness/") or l.startswith("/trends/") or l.startswith("/comparison/")]
    print(f"Internal links on post page: {len(internal_links)}")
    for l in internal_links[:10]:
        print(f"  {l}")
    
    # 3. Check GCS index for what posts exist
    print("\n=== GCS Post Index ===")
    r3 = httpx.get("https://storage.googleapis.com/wihy-web-assets/blog/posts/index.json", timeout=15)
    print(f"Status: {r3.status_code}")
    if r3.status_code == 200:
        posts = r3.json()
        print(f"Total posts in index: {len(posts)}")
        # Check related_posts field
        sample = posts[0] if posts else {}
        print(f"Sample keys: {list(sample.keys())}")
    
    # 4. Check a single post JSON for related_posts
    print("\n=== Sample Post JSON ===")
    if posts:
        slug = posts[0].get("slug", "")
        r4 = httpx.get(f"https://storage.googleapis.com/wihy-web-assets/blog/posts/{slug}.json", timeout=15)
        if r4.status_code == 200:
            post = r4.json()
            print(f"Post: {post.get('title', 'N/A')}")
            print(f"Related posts: {post.get('related_posts', [])}")
            print(f"Tags: {post.get('tags', [])}")
            # Check if body has internal links
            body = post.get("body", "")
            body_links = re.findall(r'\[.*?\]\((/[^)]+)\)', body)
            print(f"Markdown internal links in body: {len(body_links)}")
            for l in body_links[:5]:
                print(f"  {l}")

if __name__ == "__main__":
    main()
