# SPDX-License-Identifier: GPL-3.0-or-later
"""End-to-end check that the make->model dropdown cascade works in the app.

Uses Streamlit's AppTest to run app.py in-process (no browser, no API calls).
"""
import pytest

from vefi import settings_store

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def _sb(at, label):
    for s in at.selectbox:
        if s.label == label:
            return s
    return None


@pytest.fixture
def app():
    # A key is required for the app to show the search page instead of the gate.
    settings_store.save_settings({settings_store.KEY_MARKETCHECK: "TEST_KEY",
                                  settings_store.KEY_MONTHLY_LIMIT: 1000})
    return AppTest.from_file("app.py", default_timeout=60).run()


def test_make_dropdown_populated(app):
    make = _sb(app, "Make")
    assert make is not None
    assert make.options[0] == "Any"
    assert "Lexus" in make.options
    assert len(make.options) > 20


def test_model_cascades_from_make(app):
    _sb(app, "Make").set_value("Lexus").run()
    model = _sb(app, "Model")
    assert model.options[0] == "Any"
    assert "LC" in model.options


def test_switching_make_swaps_models_without_crash(app):
    _sb(app, "Make").set_value("Lexus").run()
    _sb(app, "Make").set_value("Volvo").run()
    model = _sb(app, "Model")
    assert "V60" in model.options
    assert "LC" not in model.options


def test_body_type_dropdown_populated(app):
    body = _sb(app, "Body Type")
    assert body.options[0] == "Any"
    assert "Sedan" in body.options
