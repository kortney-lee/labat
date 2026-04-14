from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

SHANIA_GRAPHICS_URL = os.getenv(
    "SHANIA_GRAPHICS_URL",
    "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app",
)

INVENTORY_DEFAULT = Path("data/communitygroceries_trending_meal_pages.json")
INDEX_URL = "https://storage.googleapis.com/cg-web-assets/blog/posts/index.json"
IMAGE_BUCKET = "gs://cg-web-assets/images/blog"
IMAGE_URL_PREFIX = "https://storage.googleapis.com/cg-web-assets/images/blog"


def _load_inventory(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("pages", [])


async def _load_trending_from_index() -> List[Dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as http:
        r = await http.get(INDEX_URL)
        r.raise_for_status()
        data = r.json()
    out = []
    for p in data.get("posts", []):
        if str(p.get("route_base", "")).strip() == "/trending":
            out.append(
                {
                    "slug": p.get("slug"),
                    "keyword": p.get("title") or p.get("slug", "").replace("-", " "),
                    "route_base": "/trending",
                    "route_path": p.get("route_path", ""),
                }
            )
    return out


async def _load_missing_from_index() -> List[Dict[str, Any]]:
    """Return all posts across all route groups whose hero image file is 404."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        r = await http.get(INDEX_URL)
        r.raise_for_status()
        data = r.json()

    posts = data.get("posts", [])
    print(f"Checking {len(posts)} posts for missing hero images...")

    missing: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15.0) as http:
        for p in posts:
            hero = str(p.get("hero_image") or "").strip()
            if not hero:
                slug = p.get("slug", "")
                hero = f"{IMAGE_URL_PREFIX}/{slug}-hero.jpg"
            try:
                resp = await http.head(hero)
                exists = resp.status_code < 400
            except Exception:
                exists = False
            if not exists:
                missing.append(
                    {
                        "slug": p.get("slug"),
                        "keyword": p.get("title") or p.get("slug", "").replace("-", " "),
                        "route_base": p.get("route_base", "/blog"),
                        "route_path": p.get("route_path", ""),
                    }
                )

    print(f"Found {len(missing)} posts with missing hero images")
    return missing


async def _generate_hero_bytes(slug: str, topic: str, brand: str = "communitygroceries") -> Optional[bytes]:
    async with httpx.AsyncClient(timeout=60.0) as http:
        r = await http.post(
            f"{SHANIA_GRAPHICS_URL}/generate-hero-image",
            json={"topic": topic, "brand": brand, "slug": slug},
        )
        if r.status_code != 200:
            print(f"[X] generate failed {slug}: {r.status_code} {r.text[:140]}")
            return None

        payload = r.json()
        if payload.get("url"):
            img = await http.get(payload["url"], timeout=60.0)
            if img.status_code == 200:
                return img.content

        if payload.get("imageBase64"):
            return base64.b64decode(payload["imageBase64"])

    print(f"[X] no image content for {slug}")
    return None


def _upload_bytes_to_gcs(image_bytes: bytes, gcs_path: str) -> bool:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        cmd = f'gcloud storage cp "{tmp_path}" "{gcs_path}"'
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=90)
        if res.returncode != 0:
            print(f"[X] upload failed: {gcs_path} :: {res.stderr.strip()[:200]}")
            return False
        return True
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def _verify_url(url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http:
            r = await http.head(url)
            if r.status_code >= 400:
                r = await http.get(url)
            return r.status_code < 400
    except Exception:
        return False


async def run_backfill(source: str, inventory: Optional[Path], limit: Optional[int], slug: Optional[str]) -> None:
    if source == "inventory":
        if not inventory or not inventory.exists():
            raise SystemExit(f"Missing inventory file: {inventory}")
        pages = _load_inventory(inventory)
    elif source == "missing":
        pages = await _load_missing_from_index()
    else:
        pages = await _load_trending_from_index()

    if slug:
        pages = [p for p in pages if p.get("slug") == slug]

    if limit:
        pages = pages[:limit]

    if not pages:
        print("No pages to process")
        return

    print(f"Backfilling {len(pages)} meal hero images from source={source}")

    ok = 0
    failed = 0

    for i, page in enumerate(pages, 1):
        slug_val = str(page.get("slug") or "").strip()
        if not slug_val:
            failed += 1
            continue

        topic = str(page.get("keyword") or page.get("title") or slug_val.replace("-", " ")).strip()
        print(f"[{i}/{len(pages)}] generating {slug_val}")

        image_bytes = await _generate_hero_bytes(slug_val, topic, brand="communitygroceries")
        if not image_bytes:
            failed += 1
            continue

        gcs_path = f"{IMAGE_BUCKET}/{slug_val}-hero.jpg"
        if not _upload_bytes_to_gcs(image_bytes, gcs_path):
            failed += 1
            continue

        public_url = f"{IMAGE_URL_PREFIX}/{slug_val}-hero.jpg"
        if await _verify_url(public_url):
            ok += 1
            print(f"  [OK] {public_url}")
        else:
            failed += 1
            print(f"  [X] uploaded but verify failed: {public_url}")

    print(f"Done. success={ok} failed={failed}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill meal hero images to GCS for blog pages")
    parser.add_argument("--source", choices=["inventory", "index", "missing"], default="inventory")
    parser.add_argument("--inventory", default=str(INVENTORY_DEFAULT))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--slug")
    args = parser.parse_args()

    inventory_path = Path(args.inventory) if args.inventory else None
    asyncio.run(run_backfill(args.source, inventory_path, args.limit, args.slug))


if __name__ == "__main__":
    main()
