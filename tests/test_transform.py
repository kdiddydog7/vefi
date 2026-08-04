# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the merged dealer/FSBO JSON -> DataFrame transform."""
import numpy as np
import pytest

from vefi.data import transform

SAMPLE = {
    "num_found": 2,
    "listings": [
        {
            "id": "1", "vin": "VINAAA", "price": 30000, "miles": 40000,
            "seller_type": "dealer",
            "dealer": {"name": "D1", "zip": "46033", "latitude": "39.9",
                       "longitude": "-86.1", "city": "Carmel", "state": "IN"},
            "build": {"year": 2019, "make": "Volvo", "model": "V60",
                      "body_type": "Wagon", "trim": "T5"},
            "media": {"photo_links": ["http://x/1.jpg"]},
        },
        {
            "id": "2", "vin": "VINBBB", "price": 28000, "miles": 55000,
            "dealer": {"name": "D2", "zip": "46204", "city": "Indy", "state": "IN"},
            "build": {"year": 2018, "make": "Volvo", "model": "V60",
                      "body_type": "Wagon", "trim": "T6"},
        },
    ],
}


def test_build_dataframe_flattens_nested_fields():
    df = transform.build_dataframe(SAMPLE, default_seller_type="dealer")
    assert len(df) == 2
    assert df.loc[0, "build_make"] == "Volvo"
    assert df.loc[0, "dealer_name"] == "D1"
    assert df.loc[0, "dealer_latitude"] == pytest.approx(39.9)


def test_default_seller_type_fills_when_missing():
    df = transform.build_dataframe(SAMPLE, default_seller_type="fsbo")
    # Row 0 already had a seller_type; row 1 did not.
    assert df.loc[0, "seller_type"] == "dealer"
    assert df.loc[1, "seller_type"] == "fsbo"


def test_ref_miles_reads_plural_key():
    # Regression: the source key is "ref_miles" (plural), not "ref_mile".
    sample = {"listings": [{"vin": "V", "ref_miles": 41000, "dealer": {}, "build": {}}]}
    df = transform.build_dataframe(sample)
    assert df.loc[0, "ref_miles"] == 41000


def test_combined_dealer_and_fsbo_share_schema():
    """A dealer + an FSBO listing (both nest location under 'dealer') combine cleanly.

    FSBO listings lack street/phone/msa_code; those become None rather than
    breaking the merge or losing coordinates.
    """
    dealer = {"listings": [{
        "id": "1", "vin": "DEAL1", "price": 30000, "miles": 40000,
        "seller_type": "dealer", "stock_no": "S1",
        "dealer": {"name": "Big Motors", "phone": "555-1", "street": "1 Main",
                   "msa_code": "26900", "latitude": "39.9", "longitude": "-86.1",
                   "city": "Carmel", "state": "IN", "zip": "46033"},
        "build": {"year": 2019, "make": "Volvo", "model": "V60"},
    }]}
    fsbo = {"listings": [{
        "id": "2", "vin": "FSBO1", "price": 28000, "miles": 55000,
        "seller_type": "fsbo",
        "dealer": {"name": "Private Seller", "latitude": "40.3", "longitude": "-75.1",
                   "city": "Doylestown", "state": "PA", "zip": "18902"},
        "build": {"year": 2018, "make": "Volvo", "model": "V60"},
    }]}
    combined = transform.combine(
        transform.build_dataframe(dealer, default_seller_type="dealer"),
        transform.build_dataframe(fsbo, default_seller_type="fsbo"),
    )
    assert len(combined) == 2
    # Both seller types carry mappable coordinates.
    assert combined["dealer_latitude"].notna().all()
    fsbo_row = combined[combined["vin"] == "FSBO1"].iloc[0]
    assert fsbo_row["seller_type"] == "fsbo"
    assert fsbo_row["dealer_name"] == "Private Seller"
    # FSBO-absent fields are None, not a crash.
    assert fsbo_row["dealer_phone"] is None
    assert fsbo_row["dealer_street"] is None
    assert fsbo_row["stock_no"] is None


def test_missing_coordinates_become_nan():
    df = transform.build_dataframe(SAMPLE)
    assert np.isnan(df.loc[1, "dealer_latitude"])


def test_vefi_tracking_columns_present():
    df = transform.build_dataframe(SAMPLE)
    for col in ("vefi_bookmarked", "vefi_predicted_price", "vefi_deal_percentage"):
        assert col in df.columns


def test_combine_dedupes_by_vin():
    a = transform.build_dataframe(SAMPLE, default_seller_type="dealer")
    b = transform.build_dataframe(SAMPLE, default_seller_type="fsbo")
    combined = transform.combine(a, b)
    assert len(combined) == 2  # same VINs deduped


def test_combine_handles_empty():
    import pandas as pd
    assert transform.combine(pd.DataFrame(), pd.DataFrame()).empty
