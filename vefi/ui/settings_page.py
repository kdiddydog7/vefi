# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings page (Feature F2): enter API keys and the monthly call limit in the GUI."""
from __future__ import annotations

import streamlit as st

from .. import settings_store, taxonomy, usage


def render() -> None:
    st.header("Settings")
    st.caption(
        "Your keys are stored locally in `~/.vefi/config.json` and never leave your "
        "machine. They are not part of the app's source code."
    )

    current = settings_store.load_settings()

    with st.form("settings_form"):
        st.subheader("API keys")
        mc_key = st.text_input(
            "MarketCheck API key (required)",
            value=current.get(settings_store.KEY_MARKETCHECK, ""),
            type="password",
            help="Get a free key at marketcheck.com. Required to run any search.",
        )

        st.subheader("Quota")
        limit = st.number_input(
            "Monthly MarketCheck call limit",
            min_value=0,
            value=int(current.get(settings_store.KEY_MONTHLY_LIMIT, 1000)),
            step=100,
            help="Used only for the sidebar progress meter. It does not block requests.",
        )

        if st.form_submit_button("Save settings", type="primary"):
            settings_store.save_settings({
                settings_store.KEY_MARKETCHECK: mc_key.strip(),
                settings_store.KEY_MONTHLY_LIMIT: int(limit),
            })
            st.success("Settings saved.")
            st.rerun()

    st.write("---")
    st.subheader("Usage")
    col1, col2 = st.columns(2)
    col1.metric("Calls this month", f"{usage.month_count():,}")
    col2.metric("Calls all-time", f"{usage.total_count():,}")
    if st.button("Reset this month's counter"):
        usage.reset_current_month()
        st.rerun()
    history = usage.history()
    if history:
        with st.expander("Monthly history"):
            st.table({"Month": list(history.keys()), "Calls": list(history.values())})

    _vehicle_list_section()


def _vehicle_list_section() -> None:
    st.write("---")
    st.subheader("Vehicle list (make / model / body type)")

    n_makes, n_models, n_body = taxonomy.counts()
    dated = taxonomy.generated_at() or "unknown"
    origin = "your last refresh" if taxonomy.is_custom() else "bundled with the app"
    st.caption(
        f"Currently **{n_makes} makes · {n_models} models · {n_body} body types** "
        f"— {origin}, dated **{dated}**."
    )

    est = taxonomy.estimated_refresh_calls()
    st.caption(
        f"Refreshing re-fetches the full list from MarketCheck's live inventory "
        f"(~**{est} API calls** — one for the make list, one per make, one for body "
        f"types). Do this once or twice a year to pick up new models."
    )

    if st.button(f"Refresh vehicle list from MarketCheck (~{est} calls)"):
        if not settings_store.has_marketcheck_key():
            st.error("Add your MarketCheck API key above first.")
            return
        status = st.empty()
        bar = st.progress(0.0)

        def progress(i: int, total: int, make: str) -> None:
            status.text(f"Fetching models for {make} ({i}/{total})…")
            bar.progress(i / total if total else 0.0)

        try:
            data = taxonomy.refresh(progress=progress)
        except Exception as exc:  # surface API errors without crashing
            status.empty()
            bar.empty()
            st.error(f"Refresh failed: {exc}")
            return
        status.empty()
        bar.empty()
        models = sum(len(v) for v in data["makes"].values())
        st.success(
            f"Updated to {len(data['makes'])} makes and {models} models "
            f"(dated {data['generated_at']})."
        )
        st.rerun()
