# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end test of the nationwide search cost-confirmation gate (no real calls)."""
import pytest

from vefi import search as search_module, settings_store
from vefi.api import marketcheck
from vefi.data import transform
from vefi.search import SearchResult

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

_SAMPLE = {"listings": [
    {"id": str(i), "vin": f"V{i}", "price": 30000, "miles": 40000, "seller_type": "dealer",
     "dealer": {"name": "D", "latitude": "39.9", "longitude": "-86.1", "zip": "46033"},
     "build": {"year": 2020, "make": "Toyota", "model": "Camry"}}
    for i in range(3)
]}


@pytest.fixture
def app(monkeypatch):
    settings_store.save_settings({settings_store.KEY_MARKETCHECK: "TEST",
                                  settings_store.KEY_MONTHLY_LIMIT: 500})
    # Every region probe reports a dense region (2000 found -> 40 pages) with no real HTTP.
    monkeypatch.setattr(marketcheck, "region_count", lambda *a, **k: 2000)
    return AppTest.from_file("app.py", default_timeout=60).run()


def _run_nationwide(at):
    # Make/Model/Body default to "Any" and ZIP is blank => nationwide, Dealer selected.
    next(b for b in at.button if b.label == "Run Search").click().run()
    return at


def test_nationwide_shows_confirmation_with_estimate(app):
    at = _run_nationwide(app)
    pending = at.session_state["nw_pending"]
    assert pending is not None
    est = pending["estimate"]
    assert est.projected_calls == 40 * 68  # 2000/50 = 40 pages * 68 regions
    # The confirmation copy is on screen.
    body = " ".join(m.value for m in at.markdown)
    assert "Confirm nationwide search" in " ".join(s.value for s in at.subheader)
    assert "2,720" in body or "2720" in body


def test_over_budget_warns(app):
    at = _run_nationwide(app)
    # 2,720 projected vs 500 limit -> error shown.
    assert any("exceed your remaining calls" in e.value for e in at.error)


def test_cancel_returns_to_form(app):
    at = _run_nationwide(app)
    next(b for b in at.button if b.label.startswith("Cancel")).click().run()
    assert at.session_state["nw_pending"] is None
    assert any(b.label == "Run Search" for b in at.button)  # back on the form


def test_continue_runs_the_search(app, monkeypatch):
    at = _run_nationwide(app)
    df = transform.combine(transform.build_dataframe(_SAMPLE, default_seller_type="dealer"))
    monkeypatch.setattr(search_module, "run_search",
                        lambda *a, **k: SearchResult(df=df, dealer_json={}, fsbo_json=None,
                                                     params={"make": "Toyota"}))
    next(b for b in at.button if b.label.startswith("Continue")).click().run()
    assert at.session_state["nw_pending"] is None
    assert at.session_state["df"] is not None
    assert len(at.session_state["df"]) == 3
