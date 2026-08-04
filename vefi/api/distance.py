# SPDX-License-Identifier: GPL-3.0-or-later
"""Distance calculations.

A fast, free, offline **haversine** (straight-line) distance. This is plenty
accurate for weighing how far away a car is, and needs no API key.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EARTH_RADIUS_MILES = 3958.8


def add_haversine_distances(df: pd.DataFrame, origin_lat: float, origin_lon: float,
                            lat_col: str = "dealer_latitude",
                            lon_col: str = "dealer_longitude",
                            out_col: str = "vefi_distance_miles") -> pd.DataFrame:
    """Return a copy of ``df`` with a straight-line distance column (in miles).

    Rows with unparseable coordinates are dropped from the returned frame.
    """
    if origin_lat is None or origin_lon is None:
        return df.copy()
    if lat_col not in df.columns or lon_col not in df.columns:
        return df.copy()

    out = df.copy()
    out[lat_col] = pd.to_numeric(out[lat_col], errors="coerce")
    out[lon_col] = pd.to_numeric(out[lon_col], errors="coerce")
    out = out.dropna(subset=[lat_col, lon_col])

    origin_lat_rad = np.radians(origin_lat)
    origin_lon_rad = np.radians(origin_lon)
    dest_lat_rad = np.radians(out[lat_col])
    dest_lon_rad = np.radians(out[lon_col])

    dlat = dest_lat_rad - origin_lat_rad
    dlon = dest_lon_rad - origin_lon_rad
    a = np.sin(dlat / 2) ** 2 + np.cos(origin_lat_rad) * np.cos(dest_lat_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    out[out_col] = EARTH_RADIUS_MILES * c
    return out
