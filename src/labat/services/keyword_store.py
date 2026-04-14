"""
labat/services/keyword_store.py — In-process keyword store for SEO keywords.

Alex discovers keywords, Kortney consumes them when writing articles.
Stored in a local JSON file so keywords survive restarts but don't need
a full database. The Labat/Master Agent exposes CRUD via
/api/content/keywords routes.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("wihy.keyword_store")

_DATA_DIR = Path(os.getenv("KEYWORD_DATA_DIR", "data"))
_KEYWORDS_FILE = _DATA_DIR / "keywords.json"
_lock = threading.Lock()


def _ensure_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not _KEYWORDS_FILE.exists():
        return []
    try:
        return json.loads(_KEYWORDS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt keywords file — starting fresh")
        return []


def _save(keywords: List[Dict[str, Any]]):
    _ensure_dir()
    _KEYWORDS_FILE.write_text(
        json.dumps(keywords, indent=2, default=str), encoding="utf-8"
    )


# ── Public API ────────────────────────────────────────────────────────────────


def list_keywords(
    status: Optional[str] = None,
    min_priority: int = 0,
    limit: int = 200,
    brand: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return keywords, optionally filtered."""
    with _lock:
        kws = _load()
    result = []
    for kw in kws:
        if status and kw.get("status") != status:
            continue
        if kw.get("priority_score", 0) < min_priority:
            continue
        if brand and kw.get("brand", "wihy") != brand:
            continue
        result.append(kw)
    return result[:limit]


def add_keyword(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add a keyword. Returns the saved object (with generated id)."""
    with _lock:
        kws = _load()
        # Dedup by keyword+brand
        word = data.get("keyword", "").lower().strip()
        brand = data.get("brand", "wihy")
        for existing in kws:
            if existing.get("keyword", "").lower() == word and existing.get("brand", "wihy") == brand:
                return existing  # already exists
        entry = {
            "id": f"kw_{len(kws)+1:04d}",
            "keyword": word,
            "brand": brand,
            "source": data.get("source", "manual"),
            "intent": data.get("intent", "informational"),
            "priority_score": data.get("priority_score", 5),
            "suggested_page_type": data.get("suggested_page_type", "topic"),
            "status": data.get("status", "pending"),
            "discovered_by": data.get("discovered_by", "unknown"),
            "discovered_at": data.get("discovered_at", datetime.utcnow().isoformat()),
        }
        kws.append(entry)
        _save(kws)
    return entry


def update_keyword_status(keyword_id: str, new_status: str) -> Optional[Dict[str, Any]]:
    """Update the status of a keyword by id."""
    with _lock:
        kws = _load()
        for kw in kws:
            if kw.get("id") == keyword_id:
                kw["status"] = new_status
                kw["updated_at"] = datetime.utcnow().isoformat()
                _save(kws)
                return kw
    return None


def get_keywords_for_topic(topic: str, brand: str = "wihy", limit: int = 12) -> List[str]:
    """Return keyword strings relevant to a topic (simple substring match)."""
    with _lock:
        kws = _load()
    topic_lower = topic.lower()
    matches = []
    for kw in kws:
        if kw.get("brand", "wihy") != brand:
            continue
        word = kw.get("keyword", "").lower()
        # Score: direct substring match > word overlap
        if word in topic_lower or topic_lower in word:
            matches.append((2, word))
        else:
            overlap = len(set(word.split()) & set(topic_lower.split()))
            if overlap > 0:
                matches.append((overlap, word))
    matches.sort(key=lambda x: -x[0])
    return [m[1] for m in matches[:limit]]


def bulk_add_keywords(keywords: List[Dict[str, Any]]) -> Dict[str, int]:
    """Add multiple keywords at once. Returns count of added/skipped."""
    added = 0
    skipped = 0
    for kw_data in keywords:
        with _lock:
            kws = _load()
        word = kw_data.get("keyword", "").lower().strip()
        brand = kw_data.get("brand", "wihy")
        exists = any(
            k.get("keyword", "").lower() == word and k.get("brand", "wihy") == brand
            for k in kws
        )
        if exists:
            skipped += 1
        else:
            add_keyword(kw_data)
            added += 1
    return {"added": added, "skipped": skipped}
