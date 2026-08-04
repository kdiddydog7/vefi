# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for option decoding (F4) and predicted pricing."""
import pandas as pd
import pytest

from vefi import options_decode, pricing


def test_extract_options_from_dicts():
    decode = {"installed_options": [
        {"code": "CQ", "name": "Convenience Package", "msrp": 1000},
        {"code": "GF", "name": "Head-up Display"},
    ]}
    table = options_decode.extract_options_table(decode)
    assert len(table) == 2
    assert "Option" in table.columns
    assert "Code" in table.columns


def test_extract_from_installed_options_details():
    # MarketCheck's real NeoVIN shape: readable names + msrp are provided.
    decode = {
        "options_packages": "GF,ML",
        "installed_options_details": [
            {"code": "GF", "name": "Heads-up Display", "msrp": "900", "type": "O"},
            {"code": "ML", "name": "Mark Levinson Audio", "msrp": "1220", "type": "O"},
            {"code": "CK", "name": "All Weather Package", "msrp": "250", "type": "P"},
        ],
    }
    table = options_decode.extract_options_table(decode)
    assert list(table.columns) == ["Code", "Option", "Type", "MSRP"]
    assert list(table["Option"]) == ["Heads-up Display", "Mark Levinson Audio",
                                     "All Weather Package"]
    assert table.iloc[0]["MSRP"] == "$900"
    assert table.iloc[2]["Type"] == "Package"


def test_extract_falls_back_to_codes_only():
    # No details, only package codes -> show the raw codes.
    decode = {"options_packages": "CK,FP,GF"}
    table = options_decode.extract_options_table(decode)
    assert list(table.columns) == ["Code"]
    assert list(table["Code"]) == ["CK", "FP", "GF"]


def test_zero_or_missing_msrp_is_blank():
    decode = {"installed_options_details": [
        {"code": "X", "name": "No-charge item", "msrp": "0"},
        {"code": "Y", "name": "Unknown price", "msrp": ""},
    ]}
    table = options_decode.extract_options_table(decode)
    assert "MSRP" not in table.columns  # both blank -> column dropped


def test_extract_options_from_strings_and_nested():
    decode = {"specs": {"options": ["Heated Seats", "Navigation"]}}
    table = options_decode.extract_options_table(decode)
    assert list(table["Option"]) == ["Heated Seats", "Navigation"]


def test_extract_options_empty():
    assert options_decode.extract_options_table({}).empty
    assert options_decode.extract_options_table({"foo": "bar"}).empty


def test_parse_listing_extra_defaults():
    parsed = options_decode.parse_listing_extra({})
    assert parsed["options"] == []
    assert parsed["seller_comments"] == ""


def test_predicted_pricing_adds_columns():
    df = pd.DataFrame({
        "vin": list("ABCDE"),
        "miles": [10000, 20000, 30000, 40000, 50000],
        "price": [40000, 36000, 33000, 30000, 27000],
        "vefi_predicted_price": [float("nan")] * 5,
        "vefi_deal_percentage": [float("nan")] * 5,
    })
    out = pricing.add_predicted_pricing(df)
    assert out["vefi_predicted_price"].notna().all()
    assert out["vefi_deal_percentage"].notna().all()


def test_predicted_pricing_insufficient_data_noop():
    df = pd.DataFrame({"miles": [10000], "price": [40000]})
    out = pricing.add_predicted_pricing(df)
    # Nothing added / no crash with a single row.
    assert len(out) == 1


def test_trendline_spans_mileage_range():
    df = pd.DataFrame({
        "miles": [10000, 20000, 30000, 40000, 50000],
        "price": [40000, 36000, 33000, 30000, 27000],
    })
    line = pricing.trendline(df, n=50)
    assert list(line.columns) == ["miles", "predicted_price"]
    assert len(line) == 50
    assert line["miles"].min() == 10000
    assert line["miles"].max() == 50000
    # Curve should track the downward price-vs-mileage trend.
    assert line["predicted_price"].iloc[0] > line["predicted_price"].iloc[-1]


def test_trendline_empty_when_insufficient_data():
    line = pricing.trendline(pd.DataFrame({"miles": [10000], "price": [40000]}))
    assert line.empty
    assert list(line.columns) == ["miles", "predicted_price"]


def test_trendline_matches_per_car_prediction():
    # The trendline model should agree with add_predicted_pricing at a data point.
    df = pd.DataFrame({
        "vin": list("ABCDE"),
        "miles": [10000, 20000, 30000, 40000, 50000],
        "price": [40000, 36000, 33000, 30000, 27000],
        "vefi_predicted_price": [float("nan")] * 5,
        "vefi_deal_percentage": [float("nan")] * 5,
    })
    priced = pricing.add_predicted_pricing(df.copy())
    line = pricing.trendline(df, n=41)  # 41 points => a node exactly at 20000
    at_20k = line.loc[line["miles"] == 20000, "predicted_price"]
    assert not at_20k.empty
    assert at_20k.iloc[0] == pytest.approx(priced.loc[1, "vefi_predicted_price"], rel=1e-6)
