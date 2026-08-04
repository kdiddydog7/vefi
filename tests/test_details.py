# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the Actual-Price delta sign logic (over/under predicted arrow+color).

The leading sign of the delta string sets Streamlit's arrow direction; with
delta_color="inverse" that means: over predicted -> "+" -> up/red, under
predicted -> "-" -> down/green. This locks in that convention.
"""
import numpy as np

from vefi.ui.details import deal_delta_text


def test_over_predicted_is_positive_signed():
    # deal_percentage < 0 means priced OVER prediction (bad deal) -> up arrow, red.
    text = deal_delta_text(-36.0)
    assert text.startswith("+")
    assert "over predicted" in text
    assert text == "+36.0% over predicted"


def test_under_predicted_is_negative_signed():
    # deal_percentage > 0 means priced UNDER prediction (good deal) -> down, green.
    text = deal_delta_text(12.3)
    assert text.startswith("-")
    assert "under predicted" in text
    assert text == "-12.3% under predicted"


def test_none_and_nan_return_none():
    assert deal_delta_text(None) is None
    assert deal_delta_text(np.nan) is None


def test_zero_counts_as_under():
    # Exactly at prediction: treat as (non-negative) under side, down/green.
    assert deal_delta_text(0.0).startswith("-")
