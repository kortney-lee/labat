"""
labat/services/opportunity_store.py — JSON file store for speaking/partnership opportunities.

Alex discovers opportunities via LLM and stores them here via /api/content/opportunities.
Same pattern as keyword_store.py.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("wihy.opportunity_store")

_DATA_DIR = Path(os.getenv("KEYWORD_DATA_DIR", "data"))
_OPPS_FILE = _DATA_DIR / "opportunities.json"
_lock = threading.Lock()


def _ensure_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not _OPPS_FILE.exists():
        return []
    try:
        return json.loads(_OPPS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt opportunities file — starting fresh")
        return []


def _save(opps: List[Dict[str, Any]]):
    _ensure_dir()
    _OPPS_FILE.write_text(
        json.dumps(opps, indent=2, default=str), encoding="utf-8"
    )


def list_opportunities(
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    with _lock:
        opps = _load()
    result = []
    for o in opps:
        if status and o.get("status") != status:
            continue
        result.append(o)
    return result[:limit]


def add_opportunity(data: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        opps = _load()
        title = data.get("title", "").lower().strip()
        for existing in opps:
            if existing.get("title", "").lower().strip() == title:
                return existing  # dedup
        entry = {
            "id": f"opp_{len(opps)+1:04d}",
            **data,
            "created_at": datetime.utcnow().isoformat(),
        }
        opps.append(entry)
        _save(opps)
    return entry
