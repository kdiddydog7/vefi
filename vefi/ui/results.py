# SPDX-License-Identifier: GPL-3.0-or-later
"""Results view: filters plus the table / chart / map / bookmarks tabs."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from .. import mapping, pricing
from ..api import distance, geocoding
from . import details

DISTANCE_OPTIONS = {"Nationwide": None, "500 miles": 500, "200 miles": 200,
                    "100 miles": 100, "50 miles": 50, "20 miles": 20}

COLUMN_LABELS = {
    "build_year": "Year", "build_make": "Make", "build_model": "Model",
    "build_body_type": "Body Type", "miles": "Miles", "price": "Price", "dom": "DoM",
    "price_change_percent": "Price Change", "exterior_color": "Ext Color",
    "interior_color": "Int Color", "carfax_1_owner": "1-Owner",
    "carfax_clean_title": "Clean Carfax", "seller_type": "Seller",
    "build_trim": "Trim", "build_version": "Version", "dealer_name": "Dealer",
    "dealer_dealer_type": "Dealer Type", "dealer_city": "City",
    "dealer_state": "State", "dealer_zip": "Dealer Zip", "dealer_phone": "Phone",
    "vin": "VIN", "vefi_distance_miles": "Distance (mi)",
}
COLUMN_ORDER = [
    "build_year", "build_make", "build_model", "build_body_type", "miles", "price",
    "vefi_distance_miles", "dom", "price_change_percent", "exterior_color",
    "interior_color", "carfax_1_owner", "carfax_clean_title", "seller_type",
    "dealer_name", "dealer_city", "dealer_state", "dealer_zip", "dealer_phone", "vin",
]


def render() -> None:
    original_df = st.session_state.df.copy()
    filtered_df = _filter_panel(original_df)

    table_tab, vis_tab, map_tab, bm_tab = st.tabs(
        ["Results Table", "Visualizations", "Geo Map", "Bookmarks"]
    )
    with table_tab:
        _table(filtered_df, key="df", track="df_selected_vin")
    with vis_tab:
        _scatter(filtered_df)
    with map_tab:
        _map(filtered_df)
    with bm_tab:
        bookmarks = st.session_state.df[st.session_state.df["vefi_bookmarked"] == True]  # noqa: E712
        _table(bookmarks, key="bm", track="bm_selected_vin")

    _maybe_show_details(filtered_df)


# --------------------------------------------------------------------------- #
# Filters
# --------------------------------------------------------------------------- #
# Range sliders: (column, label, rounding step).
_RANGE_SPECS = [("price", "Price", 100), ("miles", "Miles", 100),
                ("build_year", "Year", 1), ("dom", "Days on Market", 1)]
# Vehicle-category multiselects: (column, label).
_MULTI_SPECS = [("build_body_type", "Body Type"), ("build_trim", "Trim"),
                ("build_version", "Version"), ("exterior_color", "Color")]
# Base names of every filter widget (before the version suffix).
_FILTER_BASES = ([f"rng_{c}" for c, _, _ in _RANGE_SPECS]
                 + [f"ms_{f}" for f, _ in _MULTI_SPECS]
                 + ["ms_carfax", "filter_zip", "filter_distance"])


# Filter widgets live inside an st.form. Clearing them by deleting their
# session_state keys does NOT reset the form widgets' browser-side state, so a
# later non-submit rerun (e.g. toggling the trendline) re-applies the old values.
# The reliable fix is to give the widgets a *new identity* on clear: every filter
# key carries a version suffix, and "Clear Filters" (or a new search) bumps the
# version so the whole group is recreated fresh.
def _fv() -> int:
    return int(st.session_state.get("filter_version", 0))


def _fk(base: str) -> str:
    """Versioned session key for a filter widget."""
    return f"{base}__v{_fv()}"


def _bump_filter_version() -> None:
    old = _fv()
    for base in _FILTER_BASES:  # drop the abandoned keys so state doesn't grow
        st.session_state.pop(f"{base}__v{old}", None)
    st.session_state["filter_version"] = old + 1


def _filter_panel(original_df: pd.DataFrame) -> pd.DataFrame:
    # A new search shouldn't inherit the previous one's filters (and its slider
    # values could be out of the new data's range), so reset when the data changes.
    _reset_filters_on_new_dataset(original_df)

    filtered_df = original_df.copy()
    # Compact filter toolbar: each group lives in a popover so the controls
    # collapse to a single row instead of a tall panel. The form keeps changes
    # batched, so results/map/chart only recompute when "Apply" is clicked. Each
    # group's button shows a count of how many of its filters are active.
    with st.form("filter_form", enter_to_submit=False, border=False):
        c1, c2, c3, c4, c5 = st.columns([1.8, 1.0, 1.0, 1.0, 1.0],
                                         vertical_alignment="center")

        with c1:
            label = _badge("Price · Miles · Year · Days", _range_active_count(original_df))
            with st.popover(label, width="stretch"):
                for col, lbl, step in _RANGE_SPECS:
                    filtered_df = _range_filter(original_df, filtered_df, col, lbl, step)

        with c2:
            with st.popover(_badge("Vehicle", _vehicle_active_count()),
                            width="stretch"):
                filtered_df = _category_filters(original_df, filtered_df)

        with c3:
            has_zip = bool(str(st.session_state.get(_fk("filter_zip"), "")).strip())
            with st.popover(_badge("Distance", 1 if has_zip else 0),
                            width="stretch"):
                user_zip = st.text_input("Your 5-digit ZIP", max_chars=5,
                                         key=_fk("filter_zip"))
                selected_distance = st.selectbox(
                    "Max Distance", list(DISTANCE_OPTIONS.keys()), key=_fk("filter_distance"))

        with c4:
            st.form_submit_button("Apply Filters", type="primary", width="stretch")
        with c5:
            cleared = st.form_submit_button("Clear Filters", width="stretch")

        # Distance is computed on submit so it reflects the current filters.
        filtered_df = _apply_distance(filtered_df, user_zip, selected_distance)
        filtered_df = pricing.add_predicted_pricing(filtered_df)

    if cleared:
        _bump_filter_version()
        st.rerun()

    st.caption(f"Showing {len(filtered_df)} of {len(original_df)} listings")
    return filtered_df


def _badge(label: str, n: int) -> str:
    return f"{label} ({n})" if n else label


def _range_bounds(original: pd.DataFrame, col: str, step: int):
    """Return the (lo, hi) slider bounds for ``col``, or ``None`` if unusable."""
    if col not in original.columns:
        return None
    values = pd.to_numeric(original[col], errors="coerce").dropna()
    if values.empty:
        return None
    lo = int(values.min()) // step * step
    hi = (int(values.max()) + step - 1) // step * step
    if lo == hi:
        lo, hi = lo - step, hi + step
    return lo, hi


def _range_filter(original: pd.DataFrame, filtered: pd.DataFrame, col: str,
                  label: str, step: int) -> pd.DataFrame:
    bounds = _range_bounds(original, col, step)
    if bounds is None:
        return filtered
    lo, hi = bounds
    filtered[col] = pd.to_numeric(filtered[col], errors="coerce")
    selected = st.slider(label, lo, hi, (lo, hi), step=step, key=_fk(f"rng_{col}"))
    mask = ((filtered[col] >= selected[0]) & (filtered[col] <= selected[1])) | filtered[col].isna()
    return filtered[mask]


def _range_active_count(original: pd.DataFrame) -> int:
    """How many range sliders are narrowed from their full extent (for the badge)."""
    n = 0
    for col, _, step in _RANGE_SPECS:
        key = _fk(f"rng_{col}")
        if key not in st.session_state:
            continue
        bounds = _range_bounds(original, col, step)
        if bounds and tuple(st.session_state[key]) != bounds:
            n += 1
    return n


def _category_filters(original: pd.DataFrame, filtered: pd.DataFrame) -> pd.DataFrame:
    for field, label in _MULTI_SPECS:
        filtered = _multiselect(original, filtered, field, label)
    if st.checkbox("Clean Carfax only", key=_fk("ms_carfax")):
        filtered = filtered[filtered["carfax_clean_title"] == True]  # noqa: E712
    return filtered


def _multiselect(original, filtered, field, label):
    if field not in original.columns:
        return filtered
    options = [o for o in original[field].dropna().unique().tolist()]
    chosen = st.multiselect(label, options, placeholder="All", key=_fk(f"ms_{field}"))
    if chosen:
        filtered = filtered[filtered[field].isin(chosen)]
    return filtered


def _vehicle_active_count() -> int:
    """Number of active vehicle-category filters (for the popover's badge)."""
    ss = st.session_state
    n = sum(1 for f, _ in _MULTI_SPECS if ss.get(_fk(f"ms_{f}")))
    if ss.get(_fk("ms_carfax")):
        n += 1
    return n


def _reset_filters_on_new_dataset(original: pd.DataFrame) -> None:
    token = (st.session_state.get("active_slug"), len(original), tuple(original.columns[:4]))
    if st.session_state.get("_filter_token") != token:
        st.session_state["_filter_token"] = token
        _bump_filter_version()


def _apply_distance(filtered: pd.DataFrame, user_zip: str,
                    selected_distance: str) -> pd.DataFrame:
    if not user_zip.strip():
        return filtered
    lat, lon = geocoding.latlon_from_zip(user_zip.strip())
    if lat is None:
        st.error(f"Could not find coordinates for ZIP {user_zip}.")
        return filtered

    dist = distance.add_haversine_distances(st.session_state.df, lat, lon)
    dist_map = dist[["vin", "vefi_distance_miles"]]

    # Merge the distance column into both the working set (for details) and the
    # filtered view, without dropping rows that lack coordinates.
    st.session_state.df = (
        st.session_state.df.drop(columns=["vefi_distance_miles"], errors="ignore")
        .merge(dist_map, on="vin", how="left")
    )
    filtered = (
        filtered.drop(columns=["vefi_distance_miles"], errors="ignore")
        .merge(dist_map, on="vin", how="left")
    )

    limit = DISTANCE_OPTIONS[selected_distance]
    if limit is not None:
        filtered = filtered[filtered["vefi_distance_miles"] <= limit]
    return filtered


# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
def _table(df: pd.DataFrame, key: str, track: str) -> None:
    if df.empty:
        st.info("No listings to show here.")
        return
    display = df.copy()
    display["price"] = display["price"].apply(_currency)
    display["miles"] = display["miles"].apply(_number)
    if "price_change_percent" in display.columns:
        display["price_change_percent"] = display["price_change_percent"].apply(_percent)

    order = [c for c in COLUMN_ORDER if c in display.columns]
    event = st.dataframe(
        display, hide_index=True, height=400, on_select="rerun",
        selection_mode="single-row", column_order=order, key=f"table_{key}",
        column_config={c: COLUMN_LABELS.get(c, c) for c in order},
    )
    if event.selection and event.selection.rows:
        vin = df.iloc[event.selection.rows[0]]["vin"]
        if vin != st.session_state.get(track):
            st.session_state[track] = vin
            st.session_state.vin_to_show = vin


def _scatter(df: pd.DataFrame) -> None:
    if df.empty or "price" not in df.columns or "miles" not in df.columns:
        st.info("Not enough data to chart.")
        return
    plot_df = df.dropna(subset=["price", "miles"])
    if plot_df.empty:
        st.info("Not enough priced listings to chart.")
        return

    # Predicted-price trendline for the current filter (same model as the pill).
    trend = pricing.trendline(plot_df)

    # Streamlit does not allow click-selection (on_select) on a *layered* chart,
    # and overlaying the trendline makes the chart layered. So the trendline is a
    # toggle: on -> show the trendline (no click-to-open); off -> clickable points.
    show_trend = False
    if not trend.empty:
        cb_col, msg_col = st.columns([0.45, 0.55], vertical_alignment="center")
        with cb_col:
            show_trend = st.checkbox(
                "Show predicted-price trendline", value=False, key="show_trend",
                help="The red line is the predicted price for the current filter. "
                     "While it's shown, click-to-open is disabled — pick a car from "
                     "the Results Table or Geo Map instead.",
            )
        with msg_col:
            if show_trend:
                msg, color = "Disable trendline to enable viewing car details", "#e45756"
            else:
                msg, color = "Click points to view car details", "grey"
            # padding-right keeps the text clear of the chart's hover toolbar.
            st.markdown(
                f"<div style='text-align:right;padding-right:10ch;color:{color};"
                f"font-size:0.9em'>{msg}</div>",
                unsafe_allow_html=True,
            )

    point = alt.selection_point(fields=["vin"], name="point_select")
    body = alt.selection_point(fields=["build_body_type"], bind="legend")
    year = alt.selection_point(fields=["build_year"], bind="legend")

    y_min, y_max = plot_df["price"].min(), plot_df["price"].max()
    if show_trend:
        y_min = min(y_min, trend["predicted_price"].min())
        y_max = max(y_max, trend["predicted_price"].max())
    y_scale = alt.Scale(domain=[y_min * 0.95, y_max * 1.05])

    points = (
        alt.Chart(plot_df)
        .mark_point(filled=True, cursor="pointer")
        .encode(
            x=alt.X("miles", title="Mileage"),
            y=alt.Y("price", title="Price ($)", scale=y_scale),
            color=alt.Color("build_year:N", title="Year"),
            shape=alt.condition(body, alt.Shape("build_body_type:N", title="Body"),
                                alt.value("circle")),
            size=alt.condition(point, alt.value(160), alt.value(90)),
            opacity=alt.condition(year | body, alt.value(1), alt.value(0.35)),
            tooltip=[alt.Tooltip("vin:N", title="VIN"),
                     alt.Tooltip("price", title="Price", format="$,"),
                     alt.Tooltip("miles", title="Miles", format=","),
                     alt.Tooltip("build_year", title="Year")],
        )
        .add_params(point, year, body)
    )

    if show_trend:
        line = (
            alt.Chart(trend)
            .mark_line(color="#e45756", strokeWidth=3)
            .encode(
                x="miles",
                y=alt.Y("predicted_price", scale=y_scale),
                tooltip=[alt.Tooltip("predicted_price", title="Predicted", format="$,")],
            )
        )
        chart = alt.layer(points, line).properties(height=420)
        st.altair_chart(chart, use_container_width=True)
        st.caption("Red line = predicted price for the current filter; it updates as you filter.")
        return

    event = st.altair_chart(points.properties(height=420), use_container_width=True,
                            on_select="rerun")
    selection = (event or {}).get("selection", {}).get("point_select", [])
    if selection and "vin" in selection[0]:
        vin = selection[0]["vin"]
        if vin != st.session_state.get("vis_selected_vin"):
            st.session_state.vis_selected_vin = vin
            st.session_state.vin_to_show = vin


def _map(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No listings to map.")
        return
    fmap = mapping.create_map(df)
    if not fmap:
        st.warning("No mappable coordinates in the current results.")
        return
    event = st_folium(fmap, use_container_width=True, height=700,
                      returned_objects=["last_object_clicked_tooltip"])
    vin = (event or {}).get("last_object_clicked_tooltip")
    if vin and vin != st.session_state.get("map_selected_vin"):
        st.session_state.map_selected_vin = vin
        st.session_state.vin_to_show = vin


def _maybe_show_details(filtered_df: pd.DataFrame) -> None:
    vin = st.session_state.get("vin_to_show")
    if not vin:
        return
    working = st.session_state.df
    if vin not in working["vin"].values:
        return
    vehicle = working[working["vin"] == vin].iloc[0].copy()
    # Carry the prediction from the filtered view (model is fit on the filter).
    match = filtered_df[filtered_df["vin"] == vin]
    if not match.empty:
        vehicle["vefi_predicted_price"] = match["vefi_predicted_price"].values[0]
        vehicle["vefi_deal_percentage"] = match["vefi_deal_percentage"].values[0]
        if "vefi_distance_miles" in match.columns:
            vehicle["vefi_distance_miles"] = match["vefi_distance_miles"].values[0]
    details.render(vehicle)


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def _currency(x):
    return None if pd.isna(x) else f"${x:,.0f}"


def _number(x):
    return None if pd.isna(x) else f"{x:,.0f}"


def _percent(x):
    return None if pd.isna(x) else f"{x:,.1f}%"
