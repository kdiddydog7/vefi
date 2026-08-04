# SPDX-License-Identifier: GPL-3.0-or-later
"""Folium map of listings, clustered by dealer location."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Optional

import folium
import pandas as pd
from folium.plugins import MarkerCluster


def create_map(df: pd.DataFrame) -> Optional[folium.Map]:
    """Build a clustered map of the given listings, or ``None`` if not mappable."""
    if "dealer_latitude" not in df.columns or "dealer_longitude" not in df.columns:
        return None

    mappable = df.dropna(subset=["dealer_latitude", "dealer_longitude"])
    if mappable.empty:
        return None

    center = [mappable["dealer_latitude"].mean(), mappable["dealer_longitude"].mean()]
    fmap = folium.Map(location=center, zoom_start=5)
    cluster = MarkerCluster(options={
        "spiderfyOnMaxZoom": True,
        "disableClusteringAtZoom": 12,
        "showCoverageOnHover": True,
        "zoomToBoundsOnClick": True,
        "maxClusterRadius": 35,
    }).add_to(fmap)

    seen: dict[tuple, int] = defaultdict(int)
    for _, row in mappable.iterrows():
        key = (row["dealer_latitude"], row["dealer_longitude"])
        count = seen[key]
        seen[key] += 1

        # Fan out cars sharing an exact coordinate into a tiny spiral.
        if count > 0:
            angle = count * 0.3
            radius = 0.00050 * count
            lat = row["dealer_latitude"] + radius * math.cos(angle)
            lon = row["dealer_longitude"] + radius * math.sin(angle)
        else:
            lat, lon = row["dealer_latitude"], row["dealer_longitude"]

        folium.Marker(
            location=[lat, lon],
            tooltip=row.get("vin"),
            popup=folium.Popup(_popup_html(row), max_width=300),
        ).add_to(cluster)

    return fmap


def _popup_html(row: pd.Series) -> str:
    price = _fmt_int(row.get("price"))
    miles = _fmt_int(row.get("miles"))
    return (
        f"{row.get('build_year', '')} {row.get('build_make', '')} "
        f"{row.get('build_model', '')}<br>"
        f"Price: {price}<br>Miles: {miles}<br>"
        f"Ext Color: {row.get('exterior_color', '')}<br>"
        f"{row.get('dealer_name', '')}<br>"
        f"<a href=\"{row.get('vdp_url', '')}\" target=\"_blank\">Link</a>"
    )


def _fmt_int(value) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "N/A"
