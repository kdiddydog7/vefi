# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the make/model/body-type taxonomy (bundled load + refresh)."""
import pytest

from vefi import taxonomy
from vefi.api import marketcheck


@pytest.fixture(autouse=True)
def isolate():
    # Each test starts from the bundled list with no user override.
    taxonomy._cache = None
    taxonomy._OVERRIDE.unlink(missing_ok=True)
    yield
    taxonomy._cache = None
    taxonomy._OVERRIDE.unlink(missing_ok=True)


def test_bundled_makes_loaded():
    makes = taxonomy.makes()
    assert len(makes) > 20
    assert "Lexus" in makes
    assert "KIA" in makes  # MarketCheck's canonical spelling, not "Kia"


def test_models_for_make():
    assert "LC" in taxonomy.models_for("Lexus")
    assert "V60" in taxonomy.models_for("Volvo")
    assert taxonomy.models_for("NotARealMake") == []


def test_body_types_present():
    assert "Sedan" in taxonomy.body_types()
    assert "SUV" in taxonomy.body_types()


def test_counts_and_estimate():
    n_makes, n_models, n_body = taxonomy.counts()
    assert n_makes > 0 and n_models > 0 and n_body > 0
    assert taxonomy.estimated_refresh_calls() == n_makes + 2


def test_bundled_is_not_custom():
    assert taxonomy.is_custom() is False
    assert taxonomy.generated_at()  # bundled file carries a date


def test_refresh_writes_override(monkeypatch):
    def fake_facet(field, filters=None, limit=1000):
        if field == "make":
            return ["Volvo", "Lexus"]
        if field == "model":
            return {"Volvo": ["V60", "XC90"], "Lexus": ["LC", "RX"]}[(filters or {})["make"]]
        if field == "body_type":
            return ["Sedan", "SUV"]
        return []

    monkeypatch.setattr(marketcheck, "facet_terms", fake_facet)
    data = taxonomy.refresh(car_type="used")

    assert data["source"] == "marketcheck-facets"
    assert data["makes"]["Volvo"] == ["V60", "XC90"]
    # The override now drives load().
    assert taxonomy.is_custom() is True
    assert set(taxonomy.makes()) == {"Volvo", "Lexus"}
    assert set(taxonomy.body_types()) == {"Sedan", "SUV"}


def test_refresh_skips_failing_make(monkeypatch):
    def fake_facet(field, filters=None, limit=1000):
        if field == "make":
            return ["Good", "Bad"]
        if field == "model":
            if (filters or {})["make"] == "Bad":
                raise marketcheck.MarketCheckError("boom")
            return ["M1"]
        return ["Sedan"]

    monkeypatch.setattr(marketcheck, "facet_terms", fake_facet)
    data = taxonomy.refresh(car_type="used")
    assert data["makes"]["Good"] == ["M1"]
    assert data["makes"]["Bad"] == []  # failure skipped, not fatal
