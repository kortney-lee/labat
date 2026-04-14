"""
Backfill hero images for the 56 posts with raw JSON in body.
Calls Shania, uploads to GCS, skips if image already exists.
"""
import asyncio, base64, subprocess, tempfile, os
import urllib.request, json
import httpx

SHANIA = "https://wihy-shania-graphics-n4l2vldq3q-uc.a.run.app"
IMAGE_BUCKET = "gs://cg-web-assets/images/blog"
IMAGE_URL_PREFIX = "https://storage.googleapis.com/cg-web-assets/images/blog"

AFFECTED_SLUGS = [
    "prepared-meals-vs-buying-groceries",
    "hellofresh-worth-it-for-weight-loss",
    "community-groceries-vs-hellofresh",
    "are-cholesterol-and-blood-pressure-connected",
    "are-boiled-eggs-heart-healthy",
    "are-blood-pressure-wrist-watches-accurate",
    "are-blood-pressure-wrist-monitors-reliable",
    "are-blood-pressure-wrist-cuffs-accurate-reddit",
    "are-blood-pressure-wrist-cuffs-accurate",
    "are-blood-pressure-watches-accurate",
    "are-blood-pressure-tablets-blood-thinners",
    "are-blood-pressure-monitors-reliable",
    "are-blood-pressure-monitors-on-smart-watches-accurate",
    "are-blood-pressure-monitors-accurate-for-irregular-heartbeat",
    "are-blood-pressure-monitors-accurate-for-heart-rate",
    "are-blood-pressure-monitors-accurate-at-home",
    "are-blood-pressure-monitors-accurate",
    "are-blood-pressure-monitor-watches-accurate",
    "are-blood-pressure-meds-safe-for-breastfeeding",
    "are-blood-pressure-meds-considered-blood-thinners",
    "are-blood-pressure-meds-bad-for-your-health",
    "are-blood-pressure-meds-bad-for-you-reddit",
    "are-blood-pressure-medications-safe-during-pregnancy",
    "are-blood-pressure-medications-safe",
    "are-blood-pressure-machines-reliable",
    "are-blood-pressure-machines-accurate-for-heart-rate",
    "are-blood-pressure-machines-accurate-at-home",
    "are-blood-pressure-machines-accurate",
    "are-blood-pressure-cuffs-accurate-for-heart-rate",
    "are-blood-pressure-cuffs-accurate",
    "are-blood-pressure-cuff-accurate",
    "are-blood-pressure-apps-reliable",
    "are-blood-pressure-and-resting-heart-rate-related",
    "are-blood-pressure-and-resting-heart-rate-linked",
    "are-blood-pressure-and-pulse-rate-connected",
    "are-blood-lipids-cholesterol",
    "are-berberine-weight-loss-patches-safe",
    "are-baked-potatoes-heart-healthy",
    "are-at-home-gut-microbiome-tests-accurate",
    "are-at-home-blood-pressure-wrist-cuffs-accurate",
    "are-any-weight-loss-injections-covered-by-insurance",
    "are-any-weight-loss-drugs-covered-by-insurance-in-canada",
    "are-any-weight-loss-drugs-covered-by-insurance",
    "are-any-ultra-processed-foods-healthy",
    "are-any-processed-foods-healthy",
    "are-any-blood-pressure-apps-accurate",
    "are-all-ultra-processed-foods-bad-for-you",
    "are-all-type-2-diabetics-obese",
    "are-all-type-2-diabetics-insulin-dependent",
    "are-all-sugars-carbohydrates",
    "are-all-sugar-gliders-nocturnal",
    "are-all-sugar-alcohols-the-same",
    "are-all-red-meats-carcinogenic",
    "omega-3-fatty-acids-and-heart-disease",
    "alcohol-and-breast-cancer-risk",
    "exercise-and-depression-treatment",
]


def _get_post_title(slug: str) -> str:
    """Fetch post title from GCS, fallback to slug-based topic."""
    url = f"https://storage.googleapis.com/cg-web-assets/blog/posts/{slug}.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.load(r)
        return data.get("title") or slug.replace("-", " ")
    except Exception:
        return slug.replace("-", " ")


async def _image_exists(slug: str) -> bool:
    url = f"{IMAGE_URL_PREFIX}/{slug}-hero.jpg"
    async with httpx.AsyncClient(timeout=10.0) as http:
        try:
            r = await http.head(url)
            return r.status_code == 200
        except Exception:
            return False


async def _generate_and_upload(slug: str, topic: str) -> bool:
    async with httpx.AsyncClient(timeout=90.0) as http:
        try:
            r = await http.post(
                f"{SHANIA}/generate-hero-image",
                json={"topic": topic, "brand": "communitygroceries", "slug": slug},
            )
        except Exception as e:
            print(f"  [X] request error: {e}")
            return False

        if r.status_code != 200:
            print(f"  [X] Shania {r.status_code}: {r.text[:120]}")
            return False

        payload = r.json()
        image_bytes = None
        if payload.get("url"):
            try:
                img = await http.get(payload["url"], timeout=60.0)
                if img.status_code == 200:
                    image_bytes = img.content
            except Exception:
                pass
        if not image_bytes and payload.get("imageBase64"):
            image_bytes = base64.b64decode(payload["imageBase64"])
        if not image_bytes:
            print(f"  [X] no image bytes")
            return False

    gcs_path = f"{IMAGE_BUCKET}/{slug}-hero.jpg"
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    result = subprocess.run(
        ["gcloud", "storage", "cp", tmp_path, gcs_path],
        capture_output=True, text=True, shell=True
    )
    os.unlink(tmp_path)
    if result.returncode != 0:
        print(f"  [X] gcloud upload failed: {result.stderr[:120]}")
        return False
    return True


async def main():
    total = len(AFFECTED_SLUGS)
    ok = 0
    skipped = 0
    failed = 0

    for i, slug in enumerate(AFFECTED_SLUGS, 1):
        print(f"[{i}/{total}] {slug}")

        if await _image_exists(slug):
            print(f"  [SKIP] already exists")
            skipped += 1
            continue

        topic = _get_post_title(slug)
        success = await _generate_and_upload(slug, topic)
        if success:
            ok += 1
            print(f"  [OK] {IMAGE_URL_PREFIX}/{slug}-hero.jpg")
        else:
            failed += 1

    print(f"\nDone. ok={ok} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    asyncio.run(main())
