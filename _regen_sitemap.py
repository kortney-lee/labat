"""Regenerate sitemap.xml and robots.txt from live index.json, upload to GCS."""
import json, os, subprocess, sys

BRAND = "https://wihy.ai"
TODAY = "2026-04-10"

# Load index
idx = json.load(open("data/index.json"))
posts = idx["posts"]

urls = []
seen = set()

# Static pages
statics = [
    ("/", "weekly", "1.0"),
    ("/about", "monthly", "0.8"),
    ("/subscription", "monthly", "0.8"),
    ("/chat", "weekly", "0.7"),
    ("/privacy", "yearly", "0.3"),
    ("/terms", "yearly", "0.3"),
    ("/blog", "daily", "0.9"),
    ("/insights", "daily", "0.9"),
    ("/fitness", "daily", "0.9"),
    ("/wellness", "daily", "0.9"),
    ("/trends", "daily", "0.9"),
    ("/comparison", "daily", "0.9"),
    ("/is-it-healthy", "daily", "0.9"),
    ("/search", "weekly", "0.7"),
    ("/support", "monthly", "0.5"),
]

for loc, cf, pr in statics:
    full = f"{BRAND}{loc}"
    seen.add(full)
    urls.append(
        f"  <url>\n"
        f"    <loc>{full}</loc>\n"
        f"    <changefreq>{cf}</changefreq>\n"
        f"    <priority>{pr}</priority>\n"
        f"  </url>"
    )

# Blog posts
for p in posts:
    rp = p.get("route_path") or f"/blog/{p['slug']}"
    full = f"{BRAND}{rp}"
    if full in seen:
        continue
    seen.add(full)
    lm = (p.get("created_at") or TODAY)[:10]
    urls.append(
        f"  <url>\n"
        f"    <loc>{full}</loc>\n"
        f"    <lastmod>{lm}</lastmod>\n"
        f"    <changefreq>weekly</changefreq>\n"
        f"    <priority>0.7</priority>\n"
        f"  </url>"
    )

sitemap_xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "\n".join(urls)
    + "\n</urlset>"
)

robots_txt = (
    "User-agent: *\n"
    "Allow: /\n"
    "\n"
    "Sitemap: https://wihy.ai/sitemap.xml\n"
)

# Write locally
os.makedirs("static", exist_ok=True)
with open("static/sitemap.xml", "w", encoding="utf-8") as f:
    f.write(sitemap_xml)
with open("static/robots.txt", "w", encoding="utf-8") as f:
    f.write(robots_txt)

n_static = len(statics)
n_posts = len(urls) - n_static
print(f"Sitemap: {len(urls)} URLs ({n_static} static + {n_posts} posts)")

# Upload to GCS
subprocess.run(
    f'gcloud storage cp "static/sitemap.xml" "gs://wihy-web-assets/sitemap.xml"',
    shell=True,
)
subprocess.run(
    f'gcloud storage cp "static/robots.txt" "gs://wihy-web-assets/robots.txt"',
    shell=True,
)
print("Uploaded sitemap.xml + robots.txt to gs://wihy-web-assets/")

# Ping Google
import urllib.request
try:
    urllib.request.urlopen(f"https://www.google.com/ping?sitemap=https://wihy.ai/sitemap.xml")
    print("Pinged Google with updated sitemap")
except Exception as e:
    print(f"Google ping failed (non-critical): {e}")
