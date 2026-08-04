# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the Folium map builder."""
import pandas as pd

from vefi import mapping

_DF = pd.DataFrame({
    "vin": ["A", "B"],
    "dealer_latitude": [39.9, 40.1], "dealer_longitude": [-86.1, -85.9],
    "price": [30000, 28000], "miles": [40000, 55000],
    "build_year": [2019, 2018], "build_make": ["Volvo", "Volvo"],
    "build_model": ["V60", "V60"], "exterior_color": ["Blue", "Black"],
    "dealer_name": ["D1", "D2"], "vdp_url": ["u1", "u2"],
})


def test_create_map_builds_for_valid_coords():
    assert mapping.create_map(_DF) is not None


def test_create_map_none_without_coord_columns():
    assert mapping.create_map(pd.DataFrame({"vin": ["A"]})) is None


def test_create_map_none_when_all_coords_missing():
    df = _DF.copy()
    df["dealer_latitude"] = None
    df["dealer_longitude"] = None
    assert mapping.create_map(df) is None
