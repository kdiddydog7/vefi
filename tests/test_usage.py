# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for the persistent MarketCheck call counter (Feature F3)."""
from datetime import datetime, timezone

from vefi import usage


def _reset():
    usage.reset_current_month()


def test_record_increments_current_month():
    _reset()
    start = usage.month_count()
    assert usage.record(1) == start + 1
    assert usage.record(2) == start + 3
    assert usage.month_count() == start + 3


def test_zero_or_negative_is_noop():
    _reset()
    usage.record(1)
    before = usage.month_count()
    assert usage.record(0) == before
    assert usage.record(-5) == before


def test_history_and_total_track_current_month():
    _reset()
    usage.record(4)
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    assert usage.history()[month] == usage.month_count()
    assert usage.total_count() >= usage.month_count()


def test_reset_zeros_current_month():
    usage.record(5)
    usage.reset_current_month()
    assert usage.month_count() == 0
