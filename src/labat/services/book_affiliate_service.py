"""
labat/services/book_affiliate_service.py

Affiliate-only Amazon book promotion utilities.
This service builds trackable links and can publish to Facebook via existing post_service.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.labat.config import AMAZON_ASSOCIATE_TAG, AMAZON_MARKETPLACE, BOOK_PRIMARY_ASIN
from src.labat.services.post_service import create_post


@dataclass(frozen=True)
class BookEdition:
    title: str
    author: str
    format_name: str
    asin: str


_BOOK_EDITIONS: List[BookEdition] = [
    BookEdition(
        title="What is Healthy?: And Why is it so Hard To Achieve?",
        author="Kortney O Lee",
        format_name="Kindle eBook",
        asin="B0DL7Z7NFL",
    ),
    BookEdition(
        title="What is Healthy?: And Why is it so Hard To Achieve?",
        author="Kortney O Lee",
        format_name="Audible audiobook",
        asin="B0GVWM74FR",
    ),
    BookEdition(
        title="What is Healthy?: And Why is it so Hard To Achieve?",
        author="Kortney O Lee",
        format_name="Paperback",
        asin="B0FJ2494LH",
    ),
    BookEdition(
        title="What is Healthy?: And Why is it so Hard To Achieve?",
        author="Kortney O Lee",
        format_name="Hardcover",
        asin="B0FJ23J6JQ",
    ),
    BookEdition(
        title="What Is Healthy?: And Why is it so Hard to Achieve?",
        author="Kortney O Lee",
        format_name="Kindle eBook",
        asin="B0FHZNGZCX",
    ),
    BookEdition(
        title="What Is Healthy?: And Why is it so Hard to Achieve?",
        author="Kortney O Lee",
        format_name="Audible audiobook",
        asin="B0GNK4NBJM",
    ),
    BookEdition(
        title="What Is Healthy?: And Why is it so Hard to Achieve?",
        author="Kortney O Lee",
        format_name="Paperback",
        asin="B0FJ24T4ZD",
    ),
    BookEdition(
        title="What Is Healthy?: And Why is it so Hard to Achieve?",
        author="Kortney O Lee",
        format_name="Hardcover",
        asin="B0FK57XHST",
    ),
]


def _marketplace_base_url() -> str:
    host = (AMAZON_MARKETPLACE or "amazon.com").strip()
    return f"https://www.{host}"


def _edition_by_asin(asin: str) -> Optional[BookEdition]:
    needle = (asin or "").strip().upper()
    for edition in _BOOK_EDITIONS:
        if edition.asin.upper() == needle:
            return edition
    return None


def _pick_edition(seed: Optional[int] = None, asin: Optional[str] = None) -> BookEdition:
    if asin:
        exact = _edition_by_asin(asin)
        if exact:
            return exact

    if seed is not None:
        rng = random.Random(seed)
        return rng.choice(_BOOK_EDITIONS)

    # Stable daily rotation when not explicitly seeded.
    idx = datetime.utcnow().timetuple().tm_yday % len(_BOOK_EDITIONS)
    return _BOOK_EDITIONS[idx]


def build_affiliate_link(asin: str) -> str:
    base = _marketplace_base_url()
    clean_asin = (asin or BOOK_PRIMARY_ASIN).strip().upper()
    if AMAZON_ASSOCIATE_TAG:
        return f"{base}/dp/{clean_asin}?tag={AMAZON_ASSOCIATE_TAG}"
    return f"{base}/dp/{clean_asin}"


def preview_book_post(asin: Optional[str] = None, seed: Optional[int] = None) -> Dict[str, Any]:
    edition = _pick_edition(seed=seed, asin=asin)
    link = build_affiliate_link(edition.asin)

    message = (
        f"{edition.title} by {edition.author} is now available in {edition.format_name}.\n\n"
        f"If you're ready to reset your health habits with evidence-backed guidance, start here:\n"
        f"{link}\n\n"
        "#WhatIsHealthy #Health #Nutrition #Wellness"
    )

    return {
        "title": edition.title,
        "author": edition.author,
        "format": edition.format_name,
        "asin": edition.asin,
        "affiliate_link": link,
        "message": message,
    }


async def publish_book_post(
    asin: Optional[str] = None,
    page_id: Optional[str] = None,
    seed: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    payload = preview_book_post(asin=asin, seed=seed)

    if dry_run:
        payload["status"] = "dry_run"
        payload["published"] = False
        return payload

    result = await create_post(
        message=payload["message"],
        link=payload["affiliate_link"],
        page_id=page_id,
        published=True,
    )
    payload["status"] = "published"
    payload["published"] = True
    payload["post_id"] = result.get("id")
    return payload


def list_book_editions() -> List[Dict[str, str]]:
    return [
        {
            "title": e.title,
            "author": e.author,
            "format": e.format_name,
            "asin": e.asin,
            "affiliate_link": build_affiliate_link(e.asin),
        }
        for e in _BOOK_EDITIONS
    ]
