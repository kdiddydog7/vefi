# SPDX-License-Identifier: GPL-3.0-or-later
"""Persistent MarketCheck API call counter (Feature F3).

Every MarketCheck request routes through :func:`record`, which increments a
per-month bucket stored in ``~/.vefi/usage.json``. The GUI reads the current
month's count to show the user how close they are to their quota.

Pure Python (no Streamlit) so it can be unit-tested directly.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from . import config


def _current_month() -> str:
    """Return the current UTC month key, e.g. ``"2026-08"``."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load() -> dict[str, Any]:
    try:
        if config.USAGE_FILE.exists():
            with open(config.USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("months", {})
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"months": {}}


def _save(data: dict[str, Any]) -> None:
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    directory = os.path.dirname(str(config.USAGE_FILE)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, str(config.USAGE_FILE))
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def record(n: int = 1) -> int:
    """Add ``n`` calls to the current month's tally and return the new total."""
    if n <= 0:
        return month_count()
    data = _load()
    month = _current_month()
    data["months"][month] = int(data["months"].get(month, 0)) + int(n)
    data["last_call_at"] = datetime.now(timezone.utc).isoformat()
    _save(data)
    return data["months"][month]


def month_count(month: str | None = None) -> int:
    """Return the recorded call count for ``month`` (default: current month)."""
    data = _load()
    return int(data["months"].get(month or _current_month(), 0))


def total_count() -> int:
    """Return the all-time recorded call count across every month."""
    data = _load()
    return sum(int(v) for v in data["months"].values())


def history() -> dict[str, int]:
    """Return the full ``{month: count}`` mapping, sorted by month ascending."""
    data = _load()
    return {k: int(v) for k, v in sorted(data["months"].items())}


def reset_current_month() -> None:
    """Zero out the current month's counter (e.g. after the quota resets)."""
    data = _load()
    data["months"][_current_month()] = 0
    _save(data)
