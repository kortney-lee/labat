"""
labat/services/page_store.py — JSON file store for SEO page drafts.

Alex generates page drafts and stores them here via /api/content/pages.
Same pattern as keyword_store.py — simple, crash-safe, no DB needed.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("wihy.page_store")

_DATA_DIR = Path(os.getenv("KEYWORD_DATA_DIR", "data"))
_PAGES_FILE = _DATA_DIR / "pages.json"
_lock = threading.Lock()


def _ensure_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not _PAGES_FILE.exists():
        return []
    try:
        return json.loads(_PAGES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt pages file — starting fresh")
        return []


def _save(pages: List[Dict[str, Any]]):
    _ensure_dir()
    _PAGES_FILE.write_text(
        json.dumps(pages, indent=2, default=str), encoding="utf-8"
    )


def list_pages(
    status: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    with _lock:
        pages = _load()
    result = []
    for p in pages:
        if status and p.get("status") != status:
            continue
        result.append(p)
    return result[:limit]


def get_page(slug: str) -> Optional[Dict[str, Any]]:
    with _lock:
        pages = _load()
    for p in pages:
        if p.get("slug") == slug:
            return p
    return None


def add_page(data: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        pages = _load()
        slug = data.get("slug", "").lower().strip()
        for existing in pages:
            if existing.get("slug") == slug:
                existing.update(data)
                existing["updated_at"] = datetime.utcnow().isoformat()
                _save(pages)
                return existing
        entry = {
            "id": f"pg_{len(pages)+1:04d}",
            **data,
            "created_at": datetime.utcnow().isoformat(),
        }
        pages.append(entry)
        _save(pages)
    return entry


def refresh_page(slug: str, refresh_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with _lock:
        pages = _load()
        for p in pages:
            if p.get("slug") == slug:
                p.update(refresh_data)
                p["refreshed_at"] = datetime.utcnow().isoformat()
                _save(pages)
                return p
    return None
