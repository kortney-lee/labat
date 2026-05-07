"""Regenerate hero images for articles with baked-in text."""
import asyncio
import httpx

SHANIA = "https://wihy-shania-graphics-12913076533.us-central1.run.app"

JOBS = [
    (
        "weeknight-meals-under-30-minutes-launch",
        "healthy weeknight dinner ingredients, fresh vegetables, pasta, proteins, cooking prep on a dark surface",
    ),
    (
        "school-lunch-upgrades-for-kids-launch",
        "nutritious school lunch foods, fresh fruits, vegetables, whole grain bread, protein snacks for children",
    ),
]


async def regen():
    async with httpx.AsyncClient(timeout=120) as http:
        for slug, topic in JOBS:
            print(f"Regenerating: {slug}")
            r = await http.post(
                f"{SHANIA}/generate-hero-image",
                json={"topic": topic, "brand": "wihy", "slug": slug},
            )
            print(f"  Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                url = data.get("url", "")
                print(f"  URL: {url}")
            else:
                print(f"  Error: {r.text[:300]}")


asyncio.run(regen())
