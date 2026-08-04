# SPDX-License-Identifier: GPL-3.0-or-later
"""High-level search orchestration.

Ties together the MarketCheck client, the DataFrame transform, and the image
cache so the UI only has to build a :class:`SearchCriteria` and call
:func:`run_search`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from . import cache, config
from .api import marketcheck
from .api.marketcheck import ProgressFn, _noop_progress
from .data import transform


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
