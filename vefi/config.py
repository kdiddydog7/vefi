# SPDX-License-Identifier: GPL-3.0-or-later
"""Static configuration: API endpoints, filesystem paths, and defaults.

This module holds **no secrets**. API keys are supplied by the user at runtime and
live in ``~/.vefi/config.json`` (see :mod:`vefi.settings_store`).
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# MarketCheck API endpoints
# --------------------------------------------------------------------------- #
MARKETCHECK_BASE = "https://mc-api.marketcheck.com/v2"
DEALER_SEARCH_URL = f"{MARKETCHECK_BASE}/search/car/active"
FSBO_SEARCH_URL = f"{MARKETCHECK_BASE}/search/car/fsbo/active"
VIN_DECODE_URL = f"{MARKETCHECK_BASE}/decode/car/neovin/{{vin}}/specs"
DEALER_EXTRA_URL = f"{MARKETCHECK_BASE}/listing/car/{{listing_id}}/extra"
FSBO_EXTRA_URL = f"{MARKETCHECK_BASE}/listing/car/fsbo/{{listing_id}}/extra"

# The U.S. Census geocoder is free and keyless; used as a coordinate fallback.
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/address"

# FSBO (for-sale-by-owner) search is capped by MarketCheck at 10 rows per request.
FSBO_MAX_ROWS = 10
DEALER_ROWS_PER_PAGE = 50

# --------------------------------------------------------------------------- #
# Filesystem paths
# --------------------------------------------------------------------------- #
# Project root = the directory that contains the `vefi/` package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Per-user data lives inside the project so a saved search library is easy to
# find and back up. Everything here is gitignored.
DATA_DIR = Path(os.environ.get("VEFI_DATA_DIR", PROJECT_ROOT / "data"))
SEARCHES_DIR = DATA_DIR / "searches"          # one folder per saved search
CACHE_DIR = DATA_DIR / "cache"                # per-VIN decode / photo caches
LOG_DIR = DATA_DIR / "logs"

# Secrets & usage counter live in the home directory so they survive repo
# updates / re-clones and are never accidentally committed.
CONFIG_DIR = Path(os.environ.get("VEFI_CONFIG_DIR", Path.home() / ".vefi"))
CONFIG_FILE = CONFIG_DIR / "config.json"
USAGE_FILE = CONFIG_DIR / "usage.json"

# --------------------------------------------------------------------------- #
# Defaults
# --------------------------------------------------------------------------- #
# MarketCheck's free tier historically allows a limited number of calls per
# month. This is user-configurable in the Settings page; it only drives the
# progress meter, it does not block requests.
DEFAULT_MONTHLY_CALL_LIMIT = 1000


def ensure_dirs() -> None:
    """Create all runtime directories if they do not already exist."""
    for d in (DATA_DIR, SEARCHES_DIR, CACHE_DIR, LOG_DIR, CONFIG_DIR):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Nationwide search grid
# --------------------------------------------------------------------------- #
# ~100-mile-radius circles spread across the contiguous U.S. A nationwide search
# issues one MarketCheck request per point, so this list is intentionally the
# minimum needed for good coverage (each point = one API call).
NATIONWIDE_GRID: list[dict[str, float]] = [
    {"lat": 40.6800943, "lng": -74.0488554},
    {"lat": 38.3585756, "lng": -78.8113654},
    {"lat": 42.6016548, "lng": -71.9402604},
    {"lat": 40.4464492, "lng": -79.9816367},
    {"lat": 43.1003178, "lng": -75.3231468},
    {"lat": 40.4967065, "lng": -76.7059641},
    {"lat": 38.2893738, "lng": -76.1582304},
    {"lat": 35.8957007, "lng": -77.4220015},
    {"lat": 32.8680279, "lng": -81.4649702},
    {"lat": 30.4746897, "lng": -82.5416304},
    {"lat": 26.53691, "lng": -80.8167769},
    {"lat": 28.3309509, "lng": -81.893437},
    {"lat": 30.6721831, "lng": -85.3965503},
    {"lat": 31.2761775, "lng": -88.4511423},
    {"lat": 30.522069, "lng": -91.3077941},
    {"lat": 30.4074458, "lng": -94.1031942},
    {"lat": 29.4952082, "lng": -96.8943605},
    {"lat": 28.7758831, "lng": -99.451925},
    {"lat": 34.3210969, "lng": -79.0470179},
    {"lat": 42.1736724, "lng": -78.5093258},
    {"lat": 38.2628125, "lng": -82.0299546},
    {"lat": 36.6518029, "lng": -80.474074},
    {"lat": 35.0197038, "lng": -82.2967849},
    {"lat": 32.7205826, "lng": -84.0076351},
    {"lat": 33.3842565, "lng": -87.2374741},
    {"lat": 35.1635256, "lng": -85.5016343},
    {"lat": 39.256545, "lng": -85.3038804},
    {"lat": 44.5501999, "lng": -85.1061265},
    {"lat": 42.898946, "lng": -84.2052475},
    {"lat": 40.5876979, "lng": -82.952332},
    {"lat": 37.0091473, "lng": -83.6995195},
    {"lat": 37.1853098, "lng": -86.9957749},
    {"lat": 35.2353454, "lng": -88.9293686},
    {"lat": 32.9796842, "lng": -90.4235093},
    {"lat": 32.7541953, "lng": -92.9763391},
    {"lat": 41.4057571, "lng": -86.5924758},
    {"lat": 39.2961527, "lng": -88.7897414},
    {"lat": 37.435096, "lng": -90.3762722},
    {"lat": 35.1691715, "lng": -91.9534402},
    {"lat": 31.1430265, "lng": -98.7053205},
    {"lat": 31.6440993, "lng": -95.8855356},
    {"lat": 33.555639, "lng": -97.6998304},
    {"lat": 34.1297416, "lng": -94.9641606},
    {"lat": 36.2042911, "lng": -97.0942806},
    {"lat": 36.5379613, "lng": -94.1923958},
    {"lat": 39.2781861, "lng": -92.3804057},
    {"lat": 39.0930026, "lng": -94.6913337},
    {"lat": 41.0150163, "lng": -89.9550043},
    {"lat": 43.2783009, "lng": -88.9661083},
    {"lat": 45.7040118, "lng": -92.5963442},
    {"lat": 41.5927302, "lng": -93.5804926},
    {"lat": 43.5663447, "lng": -96.7665277},
    {"lat": 39.6246061, "lng": -105.0502191},
    {"lat": 35.7486103, "lng": -106.1927973},
    {"lat": 32.5676715, "lng": -111.4835042},
    {"lat": 40.7553827, "lng": -111.971066},
    {"lat": 43.6199824, "lng": -116.2777067},
    {"lat": 39.5123164, "lng": -119.7493863},
    {"lat": 36.0400056, "lng": -115.1351285},
    {"lat": 37.917996, "lng": -121.7488981},
    {"lat": 47.6576191, "lng": -122.4379359},
    {"lat": 45.018798, "lng": -122.9213343},
    {"lat": 34.3339123, "lng": -118.5707484},
    {"lat": 33.7695599, "lng": -116.2416468},
    {"lat": 41.054089, "lng": -96.6200648},
    {"lat": 34.4895426, "lng": -101.8935213},
    {"lat": 38.5851952, "lng": -97.5841229},
    {"lat": 47.5491763, "lng": -117.4583904},
]
