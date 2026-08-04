# SPDX-License-Identifier: GPL-3.0-or-later
"""Make / model / body-type taxonomy for the search dropdowns.

The app ships a **bundled** list (``vefi/resources/makes_models.json``) sourced
from MarketCheck's facet aggregations, so make/model/body-type are strict
dropdowns rather than free text — a misspelling can no longer burn API calls on
a search that returns nothing.

Users can **refresh** the list from MarketCheck at any time (Settings page). A
refresh costs roughly ``2 + <number of makes>`` API calls (one for the make
list, one per make for its models, one for body types) and is written to
``~/.vefi/makes_models.json``, which then overrides the bundled copy.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from . import config
from .api import marketcheck

ProgressFn = Callable[[int, int, str], None]

_BUNDLED = Path(__file__).parent / "resources" / "makes_models.json"
_OVERRIDE = config.CONFIG_DIR / "makes_models.json"

# Sentinel shown in dropdowns to mean "do not filter on this field".
ANY = "Any"

_cache: Optional[dict] = None


# --------------------------------------------------------------------------- #
# Loading (override -> bundled -> empty)
# --------------------------------------------------------------------------- #
def load(force: bool = False) -> dict:
    global _cache
    if _cache is not None and not force:
        return _cache
    for path in (_OVERRIDE, _BUNDLED):
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    _cache = json.load(f)
                    return _cache
        except (OSError, json.JSONDecodeError):
            continue
    _cache = {"generated_at": None, "source": None, "body_types": [], "makes": {}}
    return _cache


def makes() -> list[str]:
    return sorted(load().get("makes", {}).keys())


def models_for(make: str) -> list[str]:
    return list(load().get("makes", {}).get(make, []))


def body_types() -> list[str]:
    return list(load().get("body_types", []))


def generated_at() -> Optional[str]:
    return load().get("generated_at")


def source() -> Optional[str]:
    return load().get("source")


def is_custom() -> bool:
    """True if a user refresh (override) is in effect rather than the bundled list."""
    return _OVERRIDE.exists()


def counts() -> tuple[int, int, int]:
    """Return ``(makes, total models, body types)`` in the active taxonomy."""
    data = load()
    n_makes = len(data.get("makes", {}))
    n_models = sum(len(v) for v in data.get("makes", {}).values())
    return n_makes, n_models, len(data.get("body_types", []))


def estimated_refresh_calls() -> int:
    """Approximate MarketCheck calls a refresh will cost: makes + per-make + body."""
    return len(load().get("makes", {})) + 2


# --------------------------------------------------------------------------- #
# Building / refreshing from MarketCheck facets
# --------------------------------------------------------------------------- #
def build_taxonomy(progress: Optional[ProgressFn] = None, car_type: str = "used") -> dict:
    """Crawl MarketCheck facets into a taxonomy dict. Costs 2 + N(makes) calls.

    Restricting to ``car_type="used"`` keeps the lists to models that actually
    have used-market inventory, so every dropdown choice can return results.
    """
    filt = {"car_type": car_type} if car_type else {}
    make_list = marketcheck.facet_terms("make", filt)

    result: dict[str, list[str]] = {}
    total = len(make_list)
    for i, mk in enumerate(make_list, 1):
        if progress:
            progress(i, total, mk)
        try:
            models = marketcheck.facet_terms("model", {**filt, "make": mk})
        except marketcheck.MarketCheckError:
            models = []  # skip a transient failure rather than abort the whole crawl
        result[mk] = sorted(models)

    bodies = sorted(marketcheck.facet_terms("body_type", filt))
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "marketcheck-facets",
        "car_type": car_type,
        "body_types": bodies,
        "makes": dict(sorted(result.items())),
    }


def refresh(progress: Optional[ProgressFn] = None, car_type: str = "used") -> dict:
    """Refresh the taxonomy from MarketCheck and save it as the user override."""
    data = build_taxonomy(progress, car_type)
    save(data, _OVERRIDE)
    load(force=True)
    return data


def save(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
