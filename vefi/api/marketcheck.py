# SPDX-License-Identifier: GPL-3.0-or-later
"""MarketCheck API client.

Every outbound request passes through :func:`_request`, which:
  * injects the user's API key (from settings, never hardcoded),
  * records the call for the usage meter (Feature F3),
  * logs the request/response to ``data/logs/api_requests.log``.

The client is UI-agnostic: long-running operations accept an optional
``progress`` callback ``fn(done: int, total: int, message: str)`` so the
Streamlit layer can render progress bars without this module importing
Streamlit.
"""
from __future__ import annotations

import json
import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Iterable, Optional

import requests

from .. import config, usage
from ..settings_store import get_marketcheck_key

ProgressFn = Callable[[int, int, str], None]


class MarketCheckError(RuntimeError):
    """Raised when a MarketCheck request fails or returns no usable data."""


def _noop_progress(done: int, total: int, message: str) -> None:  # pragma: no cover
    pass


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
_logger: Optional[logging.Logger] = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("vefi.api_requests")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(
            str(config.LOG_DIR / "api_requests.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
        )
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
    _logger = logger
    return logger


# --------------------------------------------------------------------------- #
# Low-level request (the single choke point that meters + logs every call)
# --------------------------------------------------------------------------- #
def _request(url: str, params: Optional[dict] = None, headers: Optional[dict] = None,
             timeout: int = 30) -> requests.Response:
    """Perform a metered, logged GET against MarketCheck and return the response.

    Increments the usage counter by exactly one, regardless of outcome, because
    MarketCheck bills on requests made, not on successful ones.
    """
    key = get_marketcheck_key()
    if not key:
        raise MarketCheckError(
            "No MarketCheck API key configured. Add one on the Settings page."
        )

    params = dict(params or {})
    params.setdefault("api_key", key)
    req_headers = {"Host": "mc-api.marketcheck.com", "Authorization": key}
    if headers:
        req_headers.update(headers)

    logger = _get_logger()
    # Never log the api_key value.
    safe_params = {k: v for k, v in params.items() if k != "api_key"}
    logger.info("REQUEST - %s - %s", url, json.dumps(safe_params))

    usage.record(1)
    try:
        resp = requests.get(url, params=params, headers=req_headers, timeout=timeout)
    except requests.RequestException as exc:
        logger.error("ERROR - %s - %s", url, exc)
        raise MarketCheckError(f"Network error contacting MarketCheck: {exc}") from exc

    logger.info("RESPONSE - STATUS %s - %s", resp.status_code, url)
    return resp


# --------------------------------------------------------------------------- #
# Paginated single-location search (one ZIP / one lat-lng)
# --------------------------------------------------------------------------- #
def paginated_search(base_url: str, params: dict, max_listings: Optional[int] = None,
                     progress: ProgressFn = _noop_progress) -> dict:
    """Fetch all pages of a single-location search and merge them into one payload."""
    params = dict(params)
    rows_per_page = int(params.get("rows", config.DEALER_ROWS_PER_PAGE))
    params["rows"] = rows_per_page

    all_listings: list[dict] = []
    start = 0
    total_listings: Optional[int] = None
    last_page: dict = {}

    while True:
        params["start"] = start
        resp = _request(base_url, params)
        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            if all_listings:
                break  # return what we have
            raise MarketCheckError(
                f"MarketCheck returned HTTP {resp.status_code}."
            ) from exc

        last_page = resp.json()
        if total_listings is None:
            total_listings = int(last_page.get("num_found", 0))
            if max_listings is not None:
                total_listings = min(total_listings, max_listings)

        current = last_page.get("listings")
        if current is None:
            raise MarketCheckError("Unexpected response: no 'listings' field.")
        all_listings.extend(current)

        done = min(len(all_listings), total_listings)
        progress(done, total_listings, f"Fetched {done} of {total_listings} listings…")

        if len(all_listings) >= total_listings or not current:
            break
        if max_listings is not None and len(all_listings) >= max_listings:
            break
        start += rows_per_page
        time.sleep(0.5)  # be gentle on the free tier

    result = dict(last_page)
    result["listings"] = all_listings
    result["num_found"] = (
        max_listings if (max_listings is not None and max_listings < last_page.get("num_found", 0))
        else len(all_listings)
    )
    return result


# --------------------------------------------------------------------------- #
# Nationwide search (many lat-lng zones, one request each)
# --------------------------------------------------------------------------- #
def nationwide_search(base_url: str, params: dict,
                      grid: Optional[Iterable[dict]] = None,
                      max_listings: Optional[int] = None,
                      progress: ProgressFn = _noop_progress) -> dict:
    """Run a search across the nationwide coordinate grid, one page per zone."""
    grid = list(grid if grid is not None else config.NATIONWIDE_GRID)
    combined: list[dict] = []
    total_zones = len(grid)

    for i, zone in enumerate(grid, start=1):
        zone_params = dict(params)
        zone_params["latitude"] = zone["lat"]
        zone_params["longitude"] = zone["lng"]
        zone_params.pop("zip", None)
        progress(i, total_zones, f"Searching zone {i} of {total_zones}…")
        try:
            page = paginated_search(base_url, zone_params, max_listings)
        except MarketCheckError:
            continue  # skip a failing zone rather than aborting the whole run
        combined.extend(page.get("listings", []))

    return {"num_found": len(combined), "listings": combined}


# --------------------------------------------------------------------------- #
# Per-listing / per-VIN detail endpoints
# --------------------------------------------------------------------------- #
def decode_vin(vin: str) -> dict:
    """Return NeoVIN option/spec decode for a VIN (Feature F4). Metered."""
    resp = _request(config.VIN_DECODE_URL.format(vin=vin))
    if resp.status_code != 200:
        raise MarketCheckError(f"VIN decode failed: HTTP {resp.status_code}")
    return resp.json()


def listing_extra(listing_id: str, seller_type: str) -> dict:
    """Return the 'extra' payload (options, features, comments) for a listing. Metered."""
    if seller_type == "fsbo":
        url = config.FSBO_EXTRA_URL.format(listing_id=listing_id)
    else:
        url = config.DEALER_EXTRA_URL.format(listing_id=listing_id)
    resp = _request(url)
    if resp.status_code != 200:
        raise MarketCheckError(f"Listing detail fetch failed: HTTP {resp.status_code}")
    return resp.json()


def facet_terms(field: str, filters: Optional[dict] = None, limit: int = 1000) -> list[str]:
    """Return the unique taxonomy terms for ``field`` via a single metered facet call.

    Uses ``rows=0`` so no listings are returned — only the aggregated term list
    (e.g. every ``make``, or every ``model`` for a given make). One API call.
    """
    params = {"rows": 0, "facets": f"{field}|0|{limit}"}
    if filters:
        params.update(filters)
    resp = _request(config.DEALER_SEARCH_URL, params)
    if resp.status_code != 200:
        raise MarketCheckError(f"Facet request failed: HTTP {resp.status_code}")
    facet = (resp.json().get("facets") or {}).get(field) or []
    return [t["item"] for t in facet if isinstance(t, dict) and t.get("item")]
