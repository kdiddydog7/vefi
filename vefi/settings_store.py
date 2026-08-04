# SPDX-License-Identifier: GPL-3.0-or-later
"""Read/write user settings (API keys, quota limit) in ``~/.vefi/config.json``.

Pure Python with no Streamlit dependency, so it is easy to unit-test. Feature F2
(entering API keys in the GUI) is built on top of this module.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any

from . import config

# Keys used in the settings file.
KEY_MARKETCHECK = "marketcheck_api_key"
KEY_MONTHLY_LIMIT = "monthly_call_limit"

_DEFAULTS: dict[str, Any] = {
    KEY_MARKETCHECK: "",
    KEY_MONTHLY_LIMIT: config.DEFAULT_MONTHLY_CALL_LIMIT,
}


def load_settings() -> dict[str, Any]:
    """Return the saved settings merged over the defaults (never raises)."""
    settings = dict(_DEFAULTS)
    try:
        if config.CONFIG_FILE.exists():
            with open(config.CONFIG_FILE, "r", encoding="utf-8") as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                settings.update(stored)
    except (json.JSONDecodeError, OSError):
        # A corrupt or unreadable config falls back to defaults rather than
        # crashing the whole app.
        pass
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """Atomically persist ``settings`` to ``~/.vefi/config.json``."""
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(str(config.CONFIG_FILE), settings)


def update_settings(**changes: Any) -> dict[str, Any]:
    """Merge ``changes`` into the stored settings, save, and return the result."""
    settings = load_settings()
    settings.update(changes)
    save_settings(settings)
    return settings


# --- Convenience accessors ------------------------------------------------- #
def get_marketcheck_key() -> str:
    return str(load_settings().get(KEY_MARKETCHECK, "")).strip()


def get_monthly_limit() -> int:
    try:
        return int(load_settings().get(KEY_MONTHLY_LIMIT, config.DEFAULT_MONTHLY_CALL_LIMIT))
    except (TypeError, ValueError):
        return config.DEFAULT_MONTHLY_CALL_LIMIT


def has_marketcheck_key() -> bool:
    return bool(get_marketcheck_key())


def _atomic_write_json(path: str, data: Any) -> None:
    """Write JSON to ``path`` via a temp file + atomic replace."""
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
