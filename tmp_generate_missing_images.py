"""Find posts missing hero images and generate them via Shania Graphics."""
import asyncio
import json
import logging
import os
import sys

import httpx
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BUCKET = "cg-web-assets"
SHANIA_URL = os.getenv(
    "SHANIA_GRAPHICS_URL",
    "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app",
)
IMAGE_PREFIX = "images/blog"
POSTS_PREFIX = "blog/posts"


def get_missing() -> list[dict]:
    """Return list of posts whose hero image file doesn't exist in GCS."""
    client = storage.Client()
    bucket = client.bucket(BUCKET)

    # Existing image slugs
    existing = set()
    for blob in bucket.list_blobs(prefix=f"{IMAGE_PREFIX}/"):
        name = blob.name.split("/")[-1]
        if name.endswith("-hero.jpg"):
            existing.add(name.replace("-hero.jpg", ""))

    # All posts
    missing = []
    for blob in bucket.list_blobs(prefix=f"{POSTS_PREFIX}/"):
        if not blob.name.endswith(".json") or "index.json" in blob.name:
            continue
        try:
            post = json.loads(blob.download_as_text())
            slug = post.get("slug", "")
            if slug and slug not in existing:
                missing.append({
                    "slug": slug,
                    "title": post.get("title", ""),
                    "topic_slug": post.get("topic_slug", ""),
                    "brand": post.get("brand", "communitygroceries"),
                })
        except Exception:
            pass

    return missing


async def generate_image(slug: str, topic: str, brand: str) -> bytes | None:
    """Call Shania Graphics to generate a hero image."""
    async with httpx.AsyncClient(timeout=90) as http:
        try:
            resp = await http.post(
                f"{SHANIA_URL}/generate-hero-image",
                json={"topic": topic, "brand": brand, "slug": slug},
            )
            if resp.status_code != 200:
                logger.error("  Shania %d for %s: %s", resp.status_code, slug, resp.text[:200])
                return None

            data = resp.json()

            # Option A: Shania returns a URL
            if data.get("url"):
                img_resp = await http.get(data["url"], timeout=30)
                if img_resp.status_code == 200:
                    return img_resp.content

            # Option B: base64
            if data.get("imageBase64"):
                import base64
                return base64.b64decode(data["imageBase64"])

            logger.error("  No image data for %s", slug)
            return None
        except Exception as e:
            logger.error("  Image gen failed for %s: %s", slug, e)
            return None


async def upload_and_patch(slug: str, image_bytes: bytes, brand: str):
    """Upload image to GCS and update the post JSON."""
    client = storage.Client()
    bucket = client.bucket(BUCKET)

    # Upload image
    image_path = f"{IMAGE_PREFIX}/{slug}-hero.jpg"
    blob = bucket.blob(image_path)
    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    hero_url = f"https://storage.googleapis.com/{BUCKET}/{image_path}"
    logger.info("  Uploaded %s (%d KB)", image_path, len(image_bytes) // 1024)

    # Patch post JSON
    post_blob = bucket.blob(f"{POSTS_PREFIX}/{slug}.json")
    if post_blob.exists():
        post = json.loads(post_blob.download_as_text())
        post["hero_image"] = hero_url
        post_blob.upload_from_string(
            json.dumps(post, indent=2, default=str),
            content_type="application/json",
        )

    return hero_url


async def main():
    missing = get_missing()
    logger.info("Posts missing hero images: %d", len(missing))
    for m in missing:
        logger.info("  %s", m["slug"])

    if not missing:
        logger.info("All posts have images!")
        return

    success = 0
    failed = 0
    for i, post in enumerate(missing, 1):
        slug = post["slug"]
        topic = post["title"] or slug.replace("-", " ")
        brand = "communitygroceries"
        logger.info("[%d/%d] Generating image for: %s", i, len(missing), slug)

        image_bytes = await generate_image(slug, topic, brand)
        if image_bytes and len(image_bytes) > 1000:
            await upload_and_patch(slug, image_bytes, brand)
            success += 1
        else:
            failed += 1
            logger.warning("  SKIP %s (no image returned)", slug)

    # Rebuild index to update hero_image URLs
    logger.info("\nRebuilding blog index...")
    sys.path.insert(0, ".")
    from src.labat.services.blog_writer import update_blog_index
    update_blog_index("communitygroceries")

    logger.info("\n=== DONE ===")
    logger.info("Generated: %d  |  Failed: %d  |  Still missing: %d", success, failed, failed)


if __name__ == "__main__":
    asyncio.run(main())
