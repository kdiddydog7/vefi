# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression test for the filter panel's Clear behavior.

Clearing filters must survive a later non-form rerun (e.g. toggling the trendline
checkbox). The fix versions the filter widget keys; this test asserts that Clear
bumps the version and empties the widgets.
"""
import pytest

from vefi import settings_store
from vefi.data import transform

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

# A small, real-schema dataset with two colors so a Color filter actually reduces.
_SAMPLE = {"listings": [
    {"id": str(i), "vin": f"VIN{i}", "price": 30000 + i * 500, "miles": 20000 + i * 3000,
     "seller_type": "dealer",
     "dealer": {"name": "D", "latitude": "39.9", "longitude": "-86.1",
                "city": "Carmel", "state": "IN", "zip": "46033"},
     "build": {"year": 2020, "make": "Volvo", "model": "V60", "body_type": "Wagon",
               "trim": "T5", "version": "Momentum"},
     "exterior_color": "Red" if i % 2 == 0 else "Blue"}
    for i in range(6)
]}


def _df():
    return transform.combine(transform.build_dataframe(_SAMPLE, default_seller_type="dealer"))


def _app():
    settings_store.save_settings({settings_store.KEY_MARKETCHECK: "TEST",
                                  settings_store.KEY_MONTHLY_LIMIT: 1000})
    at = AppTest.from_file("app.py", default_timeout=60)
    at.session_state["df"] = _df()
    at.session_state["active_slug"] = "demo"
    return at.run()


def _color(at):
    return next(m for m in at.multiselect if m.label == "Color")


def _btn(at, label):
    return next(b for b in at.button if b.label == label)


def test_apply_then_clear_resets_and_bumps_version():
    at = _app()
    version_before = at.session_state["filter_version"]

    _color(at).set_value(["Red"]).run()
    _btn(at, "Apply Filters").click().run()
    assert _color(at).value == ["Red"]

    _btn(at, "Clear Filters").click().run()
    # Version bumped -> the widgets are recreated fresh and empty.
    assert at.session_state["filter_version"] == version_before + 1
    assert _color(at).value == []


def test_clear_survives_a_following_rerun():
    """The bug: filter came back after a non-submit rerun (the trendline toggle)."""
    at = _app()
    _color(at).set_value(["Red"]).run()
    _btn(at, "Apply Filters").click().run()
    _btn(at, "Clear Filters").click().run()

    # A non-form rerun (toggling the trendline checkbox) must NOT re-apply the filter.
    trend = next(c for c in at.checkbox if c.key == "show_trend")
    trend.set_value(True).run()
    assert _color(at).value == []
