# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the saved-search library (Feature F1)."""
import pandas as pd
import pytest

from vefi.data import library


@pytest.fixture
def df():
    return pd.DataFrame({"vin": ["A", "B"], "price": [100, 200]})


def _cleanup():
    for meta in library.list_searches():
        library.delete_search(meta["slug"])


def test_slugify():
    assert library.slugify("Volvo V60 Nationwide!") == "volvo-v60-nationwide"
    assert library.slugify("   ") == "search"


def test_save_list_load_roundtrip(df):
    _cleanup()
    slug = library.save_search("My Search", df, {"make": "Volvo"})
    metas = library.list_searches()
    assert any(m["slug"] == slug for m in metas)
    loaded = library.load_dataframe(slug)
    assert list(loaded["vin"]) == ["A", "B"]
    _cleanup()


def test_api_key_is_stripped_from_saved_params(df):
    _cleanup()
    slug = library.save_search("Secret", df, {"make": "Volvo", "api_key": "SECRET", "rows": 50})
    meta = library.load_meta(slug)
    assert "api_key" not in meta["params"]
    assert "rows" not in meta["params"]
    assert meta["params"]["make"] == "Volvo"
    _cleanup()


def test_unique_slug_avoids_collision(df):
    _cleanup()
    s1 = library.save_search("Dup", df)
    s2 = library.save_search("Dup", df)
    assert s1 != s2
    _cleanup()


def test_rename_and_delete(df):
    _cleanup()
    slug = library.save_search("Old", df)
    library.rename_search(slug, "New")
    assert library.load_meta(slug)["name"] == "New"
    library.delete_search(slug)
    assert not library.exists(slug)


def test_update_dataframe(df):
    _cleanup()
    slug = library.save_search("Upd", df)
    df2 = pd.concat([df, pd.DataFrame({"vin": ["C"], "price": [300]})], ignore_index=True)
    library.update_dataframe(slug, df2)
    assert len(library.load_dataframe(slug)) == 3
    assert library.load_meta(slug)["num_results"] == 3
    _cleanup()
