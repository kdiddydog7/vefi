# SPDX-License-Identifier: GPL-3.0-or-later
"""New-search form and the save-to-library control."""
from __future__ import annotations

import streamlit as st

from .. import search as search_service, taxonomy, usage
from ..data import library
from ..search import SearchCriteria
from ..settings_store import get_monthly_limit
from . import state

ANY = taxonomy.ANY


def render() -> None:
    """Render the search form. Runs a search and stores the result in session.

    Make/model/body-type are strict dropdowns sourced from MarketCheck's taxonomy
    (see :mod:`vefi.taxonomy`), so a typo can't waste API calls on a search that
    returns nothing. This is a plain widget layout (not ``st.form``) so the model
    list can react to the selected make.
    """
    # A nationwide search is gated by a cost estimate + confirmation (see below).
    if st.session_state.get("nw_pending"):
        _nationwide_confirm()
        return

    st.subheader("New Search")

    all_makes = taxonomy.makes()
    if not all_makes:
        st.error(
            "The make/model list isn't available. Open **Settings** and use "
            "*Refresh vehicle list from MarketCheck* to build it."
        )
        return

    col1, col2 = st.columns(2)
    with col1:
        make = st.selectbox("Make", [ANY] + all_makes, key="sf_make")
        if make == ANY:
            st.selectbox("Model", [ANY], disabled=True, key="sf_model_none")
            model = ANY
        else:
            # A make-specific key avoids a stale model value when the make changes.
            model = st.selectbox("Model", [ANY] + taxonomy.models_for(make),
                                  key=f"sf_model::{make}")
        body_type = st.selectbox("Body Type", [ANY] + taxonomy.body_types(), key="sf_body")
    with col2:
        year_range = st.slider("Year Range", 1990, 2026, (2015, 2026), key="sf_years")
        radius = st.slider("Radius (miles)", 5, 100, 100, key="sf_radius")
        zip_code = st.text_input("ZIP (blank = nationwide)", max_chars=5, key="sf_zip")

    seller_types = st.segmented_control(
        "Seller Type", ["Dealer", "FSBO"], selection_mode="multi", default=["Dealer"],
        key="sf_sellers",
    )

    if not st.button("Run Search", type="primary"):
        return

    if not seller_types:
        st.warning("Please select at least one seller type.")
        return

    criteria = SearchCriteria(
        make="" if make == ANY else make,
        model="" if model == ANY else model,
        body_type="" if body_type == ANY else body_type,
        year_string=",".join(str(y) for y in range(year_range[0], year_range[1] + 1)),
        radius=radius,
        zip_code=zip_code.strip(),
        seller_types=[s.lower() for s in seller_types],
    )
    # A nationwide search can balloon into hundreds of paginated calls, so estimate
    # the cost first and ask for confirmation. A ZIP search is bounded — run it.
    if criteria.is_nationwide:
        _prepare_nationwide(criteria)
    else:
        _run(criteria)


def _prepare_nationwide(criteria: SearchCriteria) -> None:
    status = st.empty()
    bar = st.progress(0.0)

    def progress(done: int, total: int, message: str) -> None:
        status.text(message)
        bar.progress(min(done / total, 1.0) if total else 0.0)

    try:
        with st.spinner("Estimating how many API calls this nationwide search needs…"):
            estimate = search_service.estimate_nationwide(criteria, progress=progress)
    except Exception as exc:
        status.empty()
        bar.empty()
        st.error(f"Couldn't estimate the search: {exc}")
        return
    status.empty()
    bar.empty()
    st.session_state.nw_pending = {"criteria": criteria, "estimate": estimate}
    st.rerun()


def _nationwide_confirm() -> None:
    pending = st.session_state.nw_pending
    est = pending["estimate"]
    used = usage.month_count()
    limit = get_monthly_limit()
    remaining = max(limit - used, 0)

    st.subheader("Confirm nationwide search")
    st.markdown(
        f"A nationwide search sweeps all **{est.region_count}** regions. I probed "
        f"**{est.sample_size}** of them (**{est.sample_calls}** API calls used), and they "
        f"ranged **{est.min_pages}–{est.max_pages}** pages each (avg {est.avg_pages}). "
        f"Completing the full search is estimated to require about "
        f"**~{est.projected_calls} API calls**."
    )
    st.markdown(
        f"You have **{remaining}** of your **{limit}** monthly MarketCheck calls "
        f"remaining ({used} used)."
    )
    if est.projected_calls > remaining:
        st.error(
            "⚠️ This is estimated to **exceed your remaining calls this month**. "
            "Consider cancelling and narrowing your search (add a body type, a tighter "
            "year range, or search a ZIP + radius instead of nationwide)."
        )
    else:
        st.info("This fits within your remaining calls for the month.")
    st.caption("Estimate only — actual cost depends on how listings cluster by region.")

    col_go, col_cancel = st.columns(2)
    if col_go.button("Continue — run the full search", type="primary", width="stretch"):
        st.session_state.nw_pending = None
        _run(pending["criteria"])
    if col_cancel.button("Cancel & refine search", width="stretch"):
        st.session_state.nw_pending = None
        st.rerun()


def _run(criteria: SearchCriteria) -> None:
    status = st.empty()
    bar = st.progress(0.0)

    def progress(done: int, total: int, message: str) -> None:
        status.text(message)
        bar.progress(min(done / total, 1.0) if total else 0.0)

    try:
        result = search_service.run_search(criteria, progress=progress)
    except Exception as exc:  # surface API/network errors without crashing the app
        status.empty()
        bar.empty()
        st.error(f"Search failed: {exc}")
        return

    status.empty()
    bar.empty()

    if result.df.empty:
        st.warning("No listings found for that search.")
        return

    # Unsaved working set: active_slug stays None until the user saves it.
    state.set_active(result.df, result.params, None)
    st.session_state.last_result = result
    st.success(f"Found {len(result.df)} listings.")
    st.rerun()


def render_save_bar() -> None:
    """Offer to save the current (unsaved) search, or note it is already saved."""
    if st.session_state.get("active_slug"):
        meta = library.load_meta(st.session_state.active_slug)
        name = meta.get("name") if meta else st.session_state.active_slug
        st.caption(f"💾 Saved as **{name}** — bookmarks and edits auto-save.")
        return

    result = st.session_state.get("last_result")
    if result is None:
        return

    with st.container(border=True):
        cols = st.columns([0.7, 0.3])
        name = cols[0].text_input(
            "Save this search to your library", placeholder="e.g. Volvo V60 nationwide",
            label_visibility="collapsed", key="save_name",
        )
        if cols[1].button("Save", width="stretch"):
            if not name.strip():
                st.warning("Give the search a name first.")
            else:
                slug = library.save_search(
                    name.strip(), st.session_state.df, result.params,
                    dealer_json=result.dealer_json, fsbo_json=result.fsbo_json,
                )
                st.session_state.active_slug = slug
                st.session_state.last_result = None
                st.rerun()
