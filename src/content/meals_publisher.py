"""
content/meals_publisher.py — Publishes public meal templates to GCS for SEO.

Fetches all templates from user.wihy.ai, strips user data, enriches with
Recipe JSON-LD structured data, and uploads to:
  gs://cg-web-assets/meals/index.json          → collection listing
  gs://cg-web-assets/meals/{slug}.json          → individual recipe pages

Usage:
    python -m src.content.meals_publisher                     # publish all
    python -m src.content.meals_publisher --brand wihy        # for wihy.ai
    python -m src.content.meals_publisher --dry-run           # preview only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("wihy.meals_publisher")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


# ── GCS config ────────────────────────────────────────────────────────────────

BRAND_GCS = {
    "communitygroceries": {
        "meals_bucket": "gs://cg-web-assets/trending-meals",
        "domain": "https://communitygroceries.com",
        "image_url_prefix": "https://storage.googleapis.com/cg-web-assets/images/meals",
    },
    "wihy": {
        "meals_bucket": "gs://wihy-web-assets/trending-meals",
        "domain": "https://wihy.ai",
        "image_url_prefix": "https://storage.googleapis.com/wihy-web-assets/images/meals",
    },
}

USER_SERVICE_URL = os.getenv("USER_SERVICE_DIRECT_URL", "https://user.wihy.ai").rstrip("/")
WIHY_ML_CLIENT_ID = os.getenv("WIHY_ML_CLIENT_ID", "wihy_ml_mk1waylw").strip()
WIHY_ML_CLIENT_SECRET = (os.getenv("WIHY_ML_CLIENT_SECRET", "") or "").strip()


# ── Slug generation ──────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert a recipe name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "recipe"


# ── Recipe JSON-LD (Schema.org structured data) ─────────────────────────────

def _build_recipe_schema(template: Dict[str, Any], brand_cfg: Dict[str, str]) -> Dict[str, Any]:
    """Build a Schema.org Recipe JSON-LD object for SEO crawlers."""
    nutrition = template.get("nutrition", {})
    ingredients = template.get("ingredients", [])
    instructions = template.get("instructions", [])

    # Normalize ingredients to strings
    ingredient_strings = []
    for ing in ingredients:
        if isinstance(ing, str):
            ingredient_strings.append(ing)
        elif isinstance(ing, dict):
            name = ing.get("name", "")
            qty = ing.get("quantity", ing.get("amount", ""))
            unit = ing.get("unit", "")
            ingredient_strings.append(f"{qty} {unit} {name}".strip())

    # Normalize instructions to HowToStep
    steps = []
    for i, step in enumerate(instructions, 1):
        if isinstance(step, str):
            steps.append({"@type": "HowToStep", "position": i, "text": step})
        elif isinstance(step, dict):
            steps.append({
                "@type": "HowToStep",
                "position": i,
                "text": step.get("text", step.get("step", str(step))),
            })

    # ISO 8601 duration
    prep = template.get("preparation_time")
    cook = template.get("cooking_time")
    total = template.get("total_time")

    schema: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": template.get("name", ""),
        "description": template.get("description", ""),
        "recipeCategory": template.get("category", template.get("meal_type", "")),
        "recipeCuisine": template.get("cuisine", ""),
        "recipeIngredient": ingredient_strings,
        "recipeInstructions": steps,
    }

    if template.get("image_url"):
        schema["image"] = template["image_url"]

    if template.get("servings"):
        schema["recipeYield"] = str(template["servings"])

    if prep:
        schema["prepTime"] = f"PT{prep}M" if isinstance(prep, (int, float)) else str(prep)
    if cook:
        schema["cookTime"] = f"PT{cook}M" if isinstance(cook, (int, float)) else str(cook)
    if total:
        schema["totalTime"] = f"PT{total}M" if isinstance(total, (int, float)) else str(total)

    if nutrition:
        schema["nutrition"] = {
            "@type": "NutritionInformation",
        }
        if nutrition.get("calories"):
            schema["nutrition"]["calories"] = f"{nutrition['calories']} calories"
        if nutrition.get("protein"):
            schema["nutrition"]["proteinContent"] = f"{nutrition['protein']}g"
        if nutrition.get("carbs") or nutrition.get("carbohydrates"):
            carbs = nutrition.get("carbs") or nutrition.get("carbohydrates")
            schema["nutrition"]["carbohydrateContent"] = f"{carbs}g"
        if nutrition.get("fat"):
            schema["nutrition"]["fatContent"] = f"{nutrition['fat']}g"
        if nutrition.get("fiber"):
            schema["nutrition"]["fiberContent"] = f"{nutrition['fiber']}g"

    if template.get("dietary"):
        dietary = template["dietary"]
        if isinstance(dietary, list):
            schema["suitableForDiet"] = [
                f"https://schema.org/{d.title().replace(' ', '')}Diet"
                for d in dietary if d
            ]

    if template.get("difficulty"):
        schema["difficulty"] = template["difficulty"]

    return schema


# ── Template sanitization ────────────────────────────────────────────────────

SAFE_FIELDS = {
    "template_id", "name", "description", "category", "meal_type", "cuisine",
    "difficulty", "nutrition", "ingredients", "instructions", "tags", "dietary",
    "preparation_time", "cooking_time", "total_time", "servings", "image_url",
    "popularity_rank", "source", "health_score",
}


def _sanitize_template(t: Dict[str, Any]) -> Dict[str, Any]:
    """Return only public-safe fields from a template."""
    return {k: t.get(k) for k in SAFE_FIELDS if t.get(k) is not None}


def _enrich_for_seo(template: Dict[str, Any], brand_cfg: Dict[str, str]) -> Dict[str, Any]:
    """Enrich a sanitized template with SEO fields."""
    slug = _slugify(template.get("name", ""))
    name = template.get("name", "")
    description = template.get("description", "")
    category = template.get("category", template.get("meal_type", ""))

    template["slug"] = slug
    template["route_path"] = f"/meals/{slug}"
    template["meta_title"] = f"{name} Recipe | Community Groceries"
    template["meta_description"] = (
        description[:155] if description else f"Try this {category} recipe: {name}"
    )
    template["recipe_schema"] = _build_recipe_schema(template, brand_cfg)

    # SEO keywords from name + tags
    keywords = [name.lower()]
    if category:
        keywords.append(category.lower())
    if template.get("cuisine"):
        keywords.append(template["cuisine"].lower())
    tags = template.get("tags", "")
    if isinstance(tags, str) and tags:
        keywords.extend(t.strip().lower() for t in tags.split(",") if t.strip())
    elif isinstance(tags, list):
        keywords.extend(t.lower() for t in tags if t)
    template["seo_keywords"] = list(dict.fromkeys(keywords))[:10]

    return template


# ── GCS helpers ──────────────────────────────────────────────────────────────

def _gcs_upload(local_path: str, gcs_path: str) -> bool:
    try:
        result = subprocess.run(
            f'gcloud storage cp "{local_path}" "{gcs_path}"',
            capture_output=True, text=True, timeout=30, shell=True,
        )
        if result.returncode == 0:
            logger.info("Uploaded → %s", gcs_path)
            return True
        logger.error("Upload failed: %s", result.stderr.strip())
        return False
    except Exception as e:
        logger.error("Upload exception: %s", e)
        return False


# ── Fetch all templates from upstream ────────────────────────────────────────

async def _fetch_all_templates() -> List[Dict[str, Any]]:
    """Fetch all public meal templates from user.wihy.ai in paginated batches."""
    all_templates: List[Dict[str, Any]] = []
    headers = {
        "X-Client-ID": WIHY_ML_CLIENT_ID,
        "X-Client-Secret": WIHY_ML_CLIENT_SECRET,
        "Content-Type": "application/json",
    }
    offset = 0
    batch_size = 100

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            url = f"{USER_SERVICE_URL}/api/meals/templates"
            params = {"limit": batch_size, "offset": offset}
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                logger.error("Upstream returned %d at offset %d: %s", resp.status_code, offset, resp.text[:200])
                break

            data = resp.json()
            templates = data.get("templates", [])
            if not templates:
                break

            all_templates.extend(templates)
            total = data.get("total", 0)
            offset += len(templates)
            logger.info("Fetched %d/%d templates", offset, total)

            if offset >= total or len(templates) < batch_size:
                break

    return all_templates


# ── Publish to GCS ───────────────────────────────────────────────────────────

async def publish_meal_templates(brand: str = "communitygroceries", dry_run: bool = False) -> Dict[str, Any]:
    """Fetch all public templates, enrich with SEO data, publish to GCS.

    Creates:
      meals/index.json — listing of all templates (lightweight)
      meals/{slug}.json — individual recipe page data (full)
    """
    brand_cfg = BRAND_GCS.get(brand, BRAND_GCS["communitygroceries"])
    bucket = brand_cfg["meals_bucket"]

    # 1. Fetch all templates
    raw_templates = await _fetch_all_templates()
    logger.info("Fetched %d raw templates", len(raw_templates))

    if not raw_templates:
        return {"published": 0, "errors": 0}

    # 2. Sanitize + enrich
    enriched = []
    seen_slugs: set[str] = set()
    for t in raw_templates:
        safe = _sanitize_template(t)
        rich = _enrich_for_seo(safe, brand_cfg)
        slug = rich["slug"]

        # De-dup slugs
        if slug in seen_slugs:
            slug = f"{slug}-{rich.get('template_id', '')[:8]}"
            rich["slug"] = slug
            rich["route_path"] = f"/meals/{slug}"
        seen_slugs.add(slug)

        enriched.append(rich)

    # Sort by popularity
    enriched.sort(key=lambda t: t.get("popularity_rank") or 9999)

    if dry_run:
        logger.info("DRY RUN — would publish %d templates", len(enriched))
        for t in enriched[:5]:
            logger.info("  %s → /meals/%s", t["name"], t["slug"])
        return {"published": len(enriched), "errors": 0, "dry_run": True}

    published = 0
    errors = 0

    # 3. Upload individual recipe JSON files
    for t in enriched:
        slug = t["slug"]
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
                json.dump(t, f, indent=2, default=str)
                tmp_path = f.name
            ok = _gcs_upload(tmp_path, f"{bucket}/{slug}.json")
            Path(tmp_path).unlink(missing_ok=True)
            if ok:
                published += 1
            else:
                errors += 1
        except Exception as e:
            logger.error("Failed to publish %s: %s", slug, e)
            errors += 1

    # 4. Build and upload index.json (lightweight — no instructions/ingredients)
    index_entries = []
    for t in enriched:
        index_entries.append({
            "slug": t["slug"],
            "route_path": t["route_path"],
            "name": t.get("name", ""),
            "description": t.get("description", ""),
            "category": t.get("category", ""),
            "meal_type": t.get("meal_type", ""),
            "cuisine": t.get("cuisine", ""),
            "difficulty": t.get("difficulty", ""),
            "image_url": t.get("image_url", ""),
            "nutrition": t.get("nutrition", {}),
            "tags": t.get("seo_keywords", []),
            "health_score": t.get("health_score"),
            "popularity_rank": t.get("popularity_rank"),
            "servings": t.get("servings"),
            "total_time": t.get("total_time"),
            "meta_title": t.get("meta_title", ""),
            "meta_description": t.get("meta_description", ""),
        })

    index_data = {
        "recipes": index_entries,
        "count": len(index_entries),
        "updated_at": datetime.utcnow().isoformat(),
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, default=str)
        tmp_path = f.name
    _gcs_upload(tmp_path, f"{bucket}/index.json")
    Path(tmp_path).unlink(missing_ok=True)

    logger.info("Published %d templates (%d errors) to %s", published, errors, bucket)
    return {"published": published, "errors": errors}


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Publish meal templates to GCS for SEO")
    parser.add_argument("--brand", default="communitygroceries", choices=["communitygroceries", "wihy"])
    parser.add_argument("--dry-run", action="store_true", help="Preview only, don't upload")
    args = parser.parse_args()

    result = asyncio.run(publish_meal_templates(brand=args.brand, dry_run=args.dry_run))
    print(f"\n{'DRY RUN ' if args.dry_run else ''}Result: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
