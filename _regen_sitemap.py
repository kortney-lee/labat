"""Regenerate sitemap.xml and robots.txt for WIHY from live index data, then upload to GCS."""
import json
import os
import subprocess
import urllib.request
from datetime import datetime, timezone

import httpx

BASE_URL = "https://wihy.ai"
INDEX_URL = "https://storage.googleapis.com/wihy-web-assets/blog/posts/index.json"
SITEMAP_GCS = "gs://wihy-web-assets/sitemap.xml"
ROBOTS_GCS = "gs://wihy-web-assets/robots.txt"


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _safe_route_path(post: dict) -> str:
    route_path = (post.get("route_path") or "").strip()
    if not route_path:
        slug = str(post.get("slug", "")).strip()
        route_base = str(post.get("route_base", "/blog")).strip().rstrip("/")
        route_path = f"{route_base}/{slug}" if slug else ""
    if route_path and not route_path.startswith("/"):
        route_path = f"/{route_path}"
    return route_path


def _load_posts() -> list:
    try:
        r = httpx.get(INDEX_URL, timeout=20)
        r.raise_for_status()
        payload = r.json()
        posts = payload.get("posts", []) if isinstance(payload, dict) else []
        if posts:
            print(f"Loaded {len(posts)} posts from live index")
            return posts
    except Exception as e:
        print(f"WARN: failed to load live index: {e}")

    try:
        with open("data/index.json", "r", encoding="utf-8") as f:
            payload = json.load(f)
        posts = payload.get("posts", []) if isinstance(payload, dict) else []
        print(f"Loaded {len(posts)} posts from local data/index.json")
        return posts
    except Exception as e:
        print(f"WARN: local fallback unavailable: {e}")
        return []


def main():
    posts = _load_posts()
    today = _today_iso()

    urls = []
    seen = set()

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
        full = f"{BASE_URL}{loc}"
        seen.add(full)
        urls.append(
            f"  <url>\n"
            f"    <loc>{full}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{cf}</changefreq>\n"
            f"    <priority>{pr}</priority>\n"
            f"  </url>"
        )

    for p in posts:
        route_path = _safe_route_path(p)
        if not route_path:
            continue
        full = f"{BASE_URL}{route_path}"
        if full in seen:
            continue
        seen.add(full)
        lastmod = (p.get("updated_at") or p.get("created_at") or today)[:10]
        urls.append(
            f"  <url>\n"
            f"    <loc>{full}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
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

    os.makedirs("static", exist_ok=True)
    with open("static/sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)
    with open("static/robots.txt", "w", encoding="utf-8") as f:
        f.write(robots_txt)

    n_static = len(statics)
    n_posts = len(urls) - n_static
    print(f"Sitemap: {len(urls)} URLs ({n_static} static + {n_posts} content pages)")

    subprocess.run(f'gcloud storage cp "static/sitemap.xml" "{SITEMAP_GCS}"', shell=True)
    subprocess.run(f'gcloud storage cp "static/robots.txt" "{ROBOTS_GCS}"', shell=True)
    print("Uploaded sitemap.xml + robots.txt to gs://wihy-web-assets/")

    try:
        urllib.request.urlopen("https://www.google.com/ping?sitemap=https://wihy.ai/sitemap.xml")
        print("Pinged Google with updated sitemap")
    except Exception as e:
        print(f"Google ping failed (non-critical): {e}")


if __name__ == "__main__":
    main()
