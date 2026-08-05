# SPDX-License-Identifier: GPL-3.0-or-later
"""Session-state initialization and active-search helpers."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st

from ..data import library

# Default session-state values.
_DEFAULTS = {
    "page": "search",              # "search" | "settings"
    "active_slug": None,           # slug of the loaded saved search, or None
    "df": None,                    # working DataFrame
    "search_params": None,         # params dict for the active search
    "last_result": None,           # SearchResult awaiting a save (unsaved run)
    "nw_pending": None,            # nationwide search awaiting cost confirmation
    # Per-tab selection tracking (Streamlit reruns every tab each pass).
    "vin_to_show": None,
    "df_selected_vin": None,
    "vis_selected_vin": None,
    "map_selected_vin": None,
    "bm_selected_vin": None,
    "current_pic_index": 0,
    "previous_vin": None,
    "selected_vid": None,
    "selected_vin": None,
}


def init() -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def has_active_search() -> bool:
    return st.session_state.get("df") is not None


def set_active(df: pd.DataFrame, params: Optional[dict], slug: Optional[str]) -> None:
    """Make ``df`` the working set and reset any stale selection state."""
    st.session_state.df = df
    st.session_state.search_params = params
    st.session_state.active_slug = slug
    st.session_state.vin_to_show = None
    st.session_state.df_selected_vin = None
    st.session_state.vis_selected_vin = None
    st.session_state.map_selected_vin = None
    st.session_state.bm_selected_vin = None
    st.session_state.nw_pending = None


def load_from_library(slug: str) -> None:
    """Load a saved search into the working session."""
    meta = library.load_meta(slug) or {}
    df = library.load_dataframe(slug)
    set_active(df, meta.get("params"), slug)


def persist_working_df() -> None:
    """Save the working DataFrame back to its library folder, if it is saved."""
    slug = st.session_state.get("active_slug")
    if slug and st.session_state.get("df") is not None:
        library.update_dataframe(slug, st.session_state.df)
