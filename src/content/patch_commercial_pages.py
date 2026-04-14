from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.content.blog_publisher import publish_post
from src.content.commercial_page_policy import sanitize_comparison_post, sanitize_trending_post


def _inventory_slugs(path: Path) -> Iterable[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    for page in data.get("pages", []):
        slug = str(page.get("slug", "")).strip()
        if slug:
            yield slug


def _read_live_post(slug: str) -> Dict[str, object] | None:
    result = subprocess.run(
        f'gcloud storage cat "gs://cg-web-assets/blog/posts/{slug}.json"',
        capture_output=True,
        text=True,
        shell=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return json.loads(result.stdout)


def _publish_group(name: str, slugs: Iterable[str], sanitizer: Callable[[Dict[str, object]], Dict[str, object]]) -> Tuple[int, int]:
    published = 0
    skipped = 0
    for slug in slugs:
        post = _read_live_post(slug)
        if not post:
            skipped += 1
            print(f"SKIP {name}: missing live post for {slug}")
            continue
        updated = sanitizer(post)
        if publish_post(updated, brand="communitygroceries"):
            published += 1
            print(f"OK {name}: {slug}")
        else:
            raise SystemExit(f"Failed publishing {slug}")
    return published, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch published commercial Community Groceries pages")
    parser.add_argument(
        "--group",
        choices=["all", "comparison", "trending"],
        default="all",
        help="Patch all commercial pages or only one group",
    )
    args = parser.parse_args()

    comparison_published = 0
    comparison_skipped = 0
    trending_published = 0
    trending_skipped = 0

    if args.group in {"all", "comparison"}:
        comparison_slugs = list(_inventory_slugs(Path("data/communitygroceries_comparison_pages.json")))
        comparison_published, comparison_skipped = _publish_group(
            "comparison", comparison_slugs, sanitize_comparison_post
        )

    if args.group in {"all", "trending"}:
        trending_slugs = list(_inventory_slugs(Path("data/communitygroceries_trending_meal_pages.json")))
        trending_published, trending_skipped = _publish_group(
            "trending", trending_slugs, sanitize_trending_post
        )

    print(
        "Done. "
        f"comparison_published={comparison_published} comparison_skipped={comparison_skipped} "
        f"trending_published={trending_published} trending_skipped={trending_skipped}"
    )


if __name__ == "__main__":
    main()