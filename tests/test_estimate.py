# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for nationwide-search cost estimation (no real API calls)."""
from vefi import config, search
from vefi.api import marketcheck
from vefi.search import SearchCriteria


def test_sample_indices_evenly_spread():
    idx = search._sample_indices(68, 6)
    assert len(idx) == 6
    assert idx[0] == 0
    assert idx[-1] == 67
    assert idx == sorted(idx)


def test_sample_indices_edge_cases():
    assert search._sample_indices(68, 1) == [0]
    assert len(search._sample_indices(3, 10)) == 3  # capped at region count


def test_estimate_projects_from_sample(monkeypatch):
    # A region_count of 350 -> ceil(350/50) = 7 pages; 7 * 68 = 476 projected.
    monkeypatch.setattr(marketcheck, "region_count", lambda *a, **k: 350)
    est = search.estimate_nationwide(SearchCriteria(seller_types=["dealer"]))
    assert est.region_count == len(config.NATIONWIDE_GRID) == 68
    assert est.sample_size == 6
    assert est.sample_calls == 6          # one probe per sampled region
    assert est.avg_pages == 7
    assert est.projected_calls == 476


def test_estimate_averages_varied_densities(monkeypatch):
    counts = iter([50, 100, 600, 2000, 0, 350])  # pages: 1,2,12,40,1,7 (avg 10.5)
    monkeypatch.setattr(marketcheck, "region_count", lambda *a, **k: next(counts))
    est = search.estimate_nationwide(SearchCriteria(seller_types=["dealer"]))
    assert est.min_pages == 1
    assert est.max_pages == 40
    assert est.avg_pages == 10.5
    assert est.projected_calls == round(10.5 * 68)  # 714


def test_empty_region_still_costs_one_call(monkeypatch):
    monkeypatch.setattr(marketcheck, "region_count", lambda *a, **k: 0)
    est = search.estimate_nationwide(SearchCriteria(seller_types=["dealer"]))
    assert est.avg_pages == 1               # a 0-result region still costs its first call
    assert est.projected_calls == 68


def test_estimate_counts_both_seller_types(monkeypatch):
    monkeypatch.setattr(marketcheck, "region_count", lambda *a, **k: 100)
    est = search.estimate_nationwide(SearchCriteria(seller_types=["dealer", "fsbo"]))
    # 6 probes per seller type.
    assert est.sample_calls == 12
    # dealer: ceil(100/50)=2 -> 2*68=136; fsbo: ceil(100/10)=10 -> 10*68=680.
    assert est.projected_calls == 136 + 680
