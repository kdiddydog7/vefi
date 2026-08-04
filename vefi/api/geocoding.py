# SPDX-License-Identifier: GPL-3.0-or-later
"""Geocoding helpers.

Primary path is :mod:`pgeocode` (local, offline ZIP -> lat/lon). When a listing
has no coordinates, we fall back to the U.S. Census geocoder, which is free and
requires no API key. Census calls are **not** MarketCheck calls and are not
metered by the usage counter.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import pgeocode
import requests

from .. import config

# One cached pgeocode lookup table per country code.
_nomi_cache: dict[str, pgeocode.Nominatim] = {}


def latlon_from_zip(zip_code: str, country: str = "us") -> tuple[Optional[float], Optional[float]]:
    """Return ``(lat, lon)`` for a ZIP using offline pgeocode, or ``(None, None)``."""
    if not zip_code or not str(zip_code).isdigit():
        return None, None
    try:
        nomi = _nomi_cache.get(country)
        if nomi is None:
            nomi = pgeocode.Nominatim(country)
            _nomi_cache[country] = nomi
        place = nomi.query_postal_code(str(zip_code))
        if pd.isna(place.latitude) or pd.isna(place.longitude):
            return None, None
        return float(place.latitude), float(place.longitude)
    except Exception:
        return None, None


def latlon_from_census(street: str = "", city: str = "", state: str = "",
                       zip_code: str = "") -> Optional[tuple[float, float]]:
    """Look up coordinates via the keyless U.S. Census geocoder.

    Returns ``(lat, lon)`` on a match, otherwise ``None``.
    """
    params = {
        "street": street or "",
        "city": city or "",
        "state": state or "",
        "zip": zip_code or "",
        "benchmark": "2020",
        "format": "json",
    }
    try:
        resp = requests.get(config.CENSUS_GEOCODER_URL, params=params, timeout=15)
        data = resp.json()
        matches = data.get("result", {}).get("addressMatches", [])
        if matches:
            coords = matches[0]["coordinates"]
            return float(coords["y"]), float(coords["x"])  # (lat, lon)
    except Exception:
        return None
    return None
