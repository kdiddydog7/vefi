# SPDX-License-Identifier: GPL-3.0-or-later
"""VeFi — Streamlit entry point.

Run with:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="VeFi Vehicle Finder", layout="wide")

from vefi import config, settings_store           # noqa: E402
from vefi.ui import results, search_form, settings_page, sidebar, state  # noqa: E402


def main() -> None:
    config.ensure_dirs()
    state.init()
    sidebar.render()

    if st.session_state.page == "settings":
        settings_page.render()
        return

    # Gate: every search needs a MarketCheck key. Send the user to Settings.
    if not settings_store.has_marketcheck_key():
        st.info("👋 Welcome to VeFi. Add your MarketCheck API key to get started.")
        settings_page.render()
        return

    if state.has_active_search():
        search_form.render_save_bar()
        results.render()
    else:
        st.title("VeFi Vehicle Finder")
        st.caption("Search used-car listings, compare deals, and map results.")
        search_form.render()


if __name__ == "__main__":
    main()
