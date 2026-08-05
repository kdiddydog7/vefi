# SPDX-License-Identifier: GPL-3.0-or-later
"""High-level search orchestration.

Ties together the MarketCheck client, the DataFrame transform, and the image
cache so the UI only has to build a :class:`SearchCriteria` and call
:func:`run_search`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from . import cache, config
from .api import marketcheck
from .api.marketcheck import ProgressFn, _noop_progress
from .data import transform

# How many grid regions to probe when estimating a nationwide search's cost.
NATIONWIDE_SAMPLE_SIZE = 6


@dataclass
class SearchCriteria:
    make: str = ""
    model: str = ""
    body_type: str = ""
    year_string: str = ""            # comma-separated years, e.g. "2018,2019,2020"
    radius: int = 100
    zip_code: str = ""               # blank => nationwide
    seller_types: list[str] = field(default_factory=lambda: ["dealer"])

    @property
    def is_nationwide(self) -> bool:
        return not self.zip_code.strip()

    def to_params(self) -> dict:
        """Build the base MarketCheck query parameters (api_key added by the client)."""
        params: dict = {
            "country": "US",
            "car_type": "used",
            "radius": self.radius,
            "rows": config.DEALER_ROWS_PER_PAGE,
        }
        if self.make:
            params["make"] = self.make
        if self.model:
            params["model"] = self.model
        if self.body_type:
            params["body_type"] = self.body_type
        if self.year_string:
            params["year"] = self.year_string
        if not self.is_nationwide:
            params["zip"] = self.zip_code.strip()
        return params


@dataclass
class SearchResult:
    df: pd.DataFrame
    dealer_json: Optional[dict]
    fsbo_json: Optional[dict]
    params: dict


def run_search(criteria: SearchCriteria, progress: ProgressFn = _noop_progress) -> SearchResult:
    """Execute the search described by ``criteria`` and return combined results."""
    base_params = criteria.to_params()
    dealer_json: Optional[dict] = None
    fsbo_json: Optional[dict] = None
    frames: list[pd.DataFrame] = []

    if "dealer" in criteria.seller_types:
        dealer_json = _fetch(config.DEALER_SEARCH_URL, base_params, criteria, progress)
        cache.save_image_links_from_payload(dealer_json)
        frames.append(transform.build_dataframe(dealer_json, default_seller_type="dealer"))

    if "fsbo" in criteria.seller_types:
        fsbo_params = dict(base_params)
        fsbo_params["rows"] = config.FSBO_MAX_ROWS  # FSBO endpoint caps rows at 10
        fsbo_json = _fetch(config.FSBO_SEARCH_URL, fsbo_params, criteria, progress)
        cache.save_image_links_from_payload(fsbo_json)
        frames.append(transform.build_dataframe(fsbo_json, default_seller_type="fsbo"))

    df = transform.combine(*frames)
    return SearchResult(df=df, dealer_json=dealer_json, fsbo_json=fsbo_json, params=base_params)


def _fetch(url: str, params: dict, criteria: SearchCriteria, progress: ProgressFn) -> dict:
    if criteria.is_nationwide:
        return marketcheck.nationwide_search(url, params, progress=progress)
    return marketcheck.paginated_search(url, params, progress=progress)


# --------------------------------------------------------------------------- #
# Nationwide cost estimation
# --------------------------------------------------------------------------- #
@dataclass
class NationwideEstimate:
    region_count: int          # total regions a full search would sweep (68)
    sample_size: int           # regions actually probed
    sample_calls: int          # API calls the probe itself consumed
    projected_calls: int       # estimated calls to complete the full search
    min_pages: int             # smallest per-region page count seen in the sample
    max_pages: int             # largest per-region page count seen in the sample
    avg_pages: float           # mean per-region page count across the sample


def _sample_indices(total: int, sample_size: int) -> list[int]:
    """Evenly-spaced region indices, so the sample spans the country's density mix."""
    sample_size = max(1, min(sample_size, total))
    if sample_size == 1:
        return [0]
    step = (total - 1) / (sample_size - 1)
    return sorted({int(round(i * step)) for i in range(sample_size)})


def estimate_nationwide(criteria: SearchCriteria, sample_size: int = NATIONWIDE_SAMPLE_SIZE,
                        progress: ProgressFn = _noop_progress) -> NationwideEstimate:
    """Probe a spread of regions to project a nationwide search's total API calls.

    Each probe is a single ``rows=0`` call (no listings downloaded). Calls per
    region = ``max(1, ceil(num_found / rows))`` because even an empty region costs
    the one initial request.
    """
    grid = config.NATIONWIDE_GRID
    indices = _sample_indices(len(grid), sample_size)

    seller_urls = []
    if "dealer" in criteria.seller_types:
        seller_urls.append((config.DEALER_SEARCH_URL, config.DEALER_ROWS_PER_PAGE))
    if "fsbo" in criteria.seller_types:
        seller_urls.append((config.FSBO_SEARCH_URL, config.FSBO_MAX_ROWS))

    base = criteria.to_params()
    all_pages: list[int] = []
    projected = 0
    sample_calls = 0
    total_probes = len(seller_urls) * len(indices)

    for url, rows in seller_urls:
        seller_pages: list[int] = []
        for idx in indices:
            region = grid[idx]
            sample_calls += 1
            progress(sample_calls, total_probes, f"Probing region {idx + 1}…")
            num_found = marketcheck.region_count(url, base, region["lat"], region["lng"])
            pages = max(1, math.ceil(num_found / rows)) if rows else 1
            seller_pages.append(pages)
        avg = sum(seller_pages) / len(seller_pages)
        projected += round(avg * len(grid))
        all_pages.extend(seller_pages)

    return NationwideEstimate(
        region_count=len(grid),
        sample_size=len(indices),
        sample_calls=sample_calls,
        projected_calls=projected,
        min_pages=min(all_pages) if all_pages else 0,
        max_pages=max(all_pages) if all_pages else 0,
        avg_pages=round(sum(all_pages) / len(all_pages), 1) if all_pages else 0.0,
    )
