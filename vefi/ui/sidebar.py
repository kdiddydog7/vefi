# SPDX-License-Identifier: GPL-3.0-or-later
"""Sidebar: branding, navigation, the API-usage meter (F3), and the search
library selector (F1)."""
from __future__ import annotations

import base64
import functools

import streamlit as st

from .. import __version__, config, usage
from ..data import library
from ..settings_store import get_monthly_limit
from . import state

_LOGO = config.PROJECT_ROOT / "VeFi_125_tp.png"


@functools.lru_cache(maxsize=1)
def _logo_data_uri() -> str:
    with open(_LOGO, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def render() -> None:
    with st.sidebar:
        _branding()
        st.write("---")
        _usage_meter()
        st.write("---")
        _navigation()
        st.write("---")
        _search_library()


def _branding() -> None:
    # Embed the logo in a centered container so it stays centered at any sidebar
    # width (st.image left-aligns).
    if _LOGO.exists():
        st.markdown(
            f"<div style='text-align:center'>"
            f"<img src='{_logo_data_uri()}' style='max-width:80%;height:auto'></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div style='text-align:center'><h3>VeFi</h3></div>",
                    unsafe_allow_html=True)
    st.markdown(
        f"<div style='text-align:center;color:grey;font-size:13px'>VeFi {__version__}</div>",
        unsafe_allow_html=True,
    )


def _usage_meter() -> None:
    """Feature F3: show MarketCheck calls used this month vs. the configured limit."""
    used = usage.month_count()
    limit = get_monthly_limit()
    st.caption("MarketCheck calls this month")
    if limit > 0:
        fraction = min(used / limit, 1.0)
        st.progress(fraction, text=f"{used:,} / {limit:,}")
        if used >= limit:
            st.error("Monthly limit reached — further searches may be rejected.")
        elif fraction >= 0.9:
            st.warning("Approaching your monthly limit.")
    else:
        st.metric("Calls used", f"{used:,}")


def _navigation() -> None:
    current = st.session_state.get("page", "search")
    choice = st.radio(
        "Navigation",
        options=["Search", "Settings"],
        index=0 if current == "search" else 1,
        label_visibility="collapsed",
    )
    st.session_state.page = "settings" if choice == "Settings" else "search"


def _search_library() -> None:
    """Feature F1: switch between saved searches without touching the file system."""
    st.subheader("Search Library")
    searches = library.list_searches()

    if not searches:
        st.caption("No saved searches yet. Run a search, then save it here.")
    else:
        labels = {
            m["slug"]: f"{m['name']}  ·  {m.get('num_results', 0)} cars"
            for m in searches
        }
        slugs = [m["slug"] for m in searches]
        active = st.session_state.get("active_slug")
        index = slugs.index(active) if active in slugs else 0

        selected = st.selectbox(
            "Load a saved search",
            options=slugs,
            index=index,
            format_func=lambda s: labels.get(s, s),
            key="library_select",
        )
        col_load, col_del = st.columns(2)
        with col_load:
            if st.button("Load", width="stretch"):
                state.load_from_library(selected)
                st.rerun()
        with col_del:
            if st.button("Delete", width="stretch"):
                library.delete_search(selected)
                if st.session_state.get("active_slug") == selected:
                    state.set_active(None, None, None)
                st.rerun()

        with st.expander("Rename selected"):
            new_name = st.text_input("New name", key="rename_input")
            if st.button("Save name") and new_name.strip():
                library.rename_search(selected, new_name.strip())
                st.rerun()

    if st.button("➕ New search", width="stretch"):
        state.set_active(None, None, None)
        st.session_state.page = "search"
        st.rerun()
