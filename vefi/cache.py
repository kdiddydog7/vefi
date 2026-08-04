# SPDX-License-Identifier: GPL-3.0-or-later
"""On-disk caches for per-listing data that costs API calls to fetch.

Cached payloads live in ``data/cache/`` keyed by VIN or listing id. Caching
matters here because each miss is a metered MarketCheck call, so re-opening a
listing you already viewed is free.
"""
from __future__ import annotations

import json
from typing import Optional

from . import config
from .api import marketcheck


def _path(name: str):
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return config.CACHE_DIR / name


def _read(name: str) -> Optional[dict]:
    path = _path(name)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _write(name: str, data: dict) -> None:
    with open(_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# --- Image links (harvested from search payloads, no extra API cost) -------- #
def save_image_links_from_payload(raw_json: dict) -> None:
    """Extract and cache each listing's photo links from a search payload."""
    seen: set[str] = set()
    for listing in (raw_json or {}).get("listings", []):
        vin = listing.get("vin")
        if not vin or vin in seen:
            continue
        media = listing.get("media") or {}
        photo_links = media.get("photo_links")
        if not photo_links:
            continue
        _write(f"{vin}.images.json", {"vin": vin, "photo_links": photo_links})
        seen.add(vin)


def get_image_links(vin: str) -> Optional[list[str]]:
    data = _read(f"{vin}.images.json")
    return data.get("photo_links") if data else None


# --- Listing extra (options / features / seller comments) — metered --------- #
def get_listing_extra(listing_id: str) -> Optional[dict]:
    return _read(f"{listing_id}.extra.json")


def fetch_listing_extra(listing_id: str, seller_type: str) -> dict:
    """Return listing 'extra' data, from cache if present else a metered API call."""
    cached = get_listing_extra(listing_id)
    if cached is not None:
        return cached
    data = marketcheck.listing_extra(listing_id, seller_type)
    _write(f"{listing_id}.extra.json", data)
    return data


# --- VIN decode (full option/spec list, Feature F4) — metered --------------- #
def get_vin_decode(vin: str) -> Optional[dict]:
    return _read(f"{vin}.decode.json")


def fetch_vin_decode(vin: str) -> dict:
    """Return NeoVIN decode data, from cache if present else a metered API call."""
    cached = get_vin_decode(vin)
    if cached is not None:
        return cached
    data = marketcheck.decode_vin(vin)
    _write(f"{vin}.decode.json", data)
    return data
