# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-listing detail panel: specs, seller info, metrics, photos, and the
on-demand option decoder (Feature F4)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import cache, options_decode
from ..api.marketcheck import MarketCheckError
from . import state


@st.fragment
def render(vehicle: pd.Series) -> None:
    st.session_state.selected_vid = vehicle["id"]
    st.session_state.selected_vin = vehicle["vin"]

    details_col, pics_col = st.columns(2)
    with details_col:
        _spec_card(vehicle)
        _listing_extra_and_options(vehicle)
    with pics_col:
        _metrics(vehicle)
        _photo_carousel(vehicle)


def _spec_card(v: pd.Series) -> None:
    with st.container(border=True):
        if v.get("vefi_distance_miles") and not pd.isna(v.get("vefi_distance_miles")):
            distance = f"{v['vefi_distance_miles']:,.0f} miles away"
        else:
            distance = "Enter your ZIP in the filters for distance"
        st.markdown(
            f":blue-badge[Year:] {v.get('build_year')} "
            f":blue-badge[Make:] {v.get('build_make')} "
            f":blue-badge[Model:] {v.get('build_model')} "
            f":blue-badge[Body:] {v.get('build_body_type')} "
            f":blue-badge[Ext:] {v.get('exterior_color')} "
            f":blue-badge[Int:] {v.get('interior_color')}",
            unsafe_allow_html=True,
        )
        st.markdown(
            f":green-badge[Trim:] {v.get('build_trim')} "
            f":green-badge[Version:] {v.get('build_version')}",
            unsafe_allow_html=True,
        )
        st.markdown(
            f":violet-badge[Dealer:] <a href='{v.get('vdp_url')}'>{v.get('dealer_name')}</a> "
            f":violet-badge[City:] {v.get('dealer_city')} "
            f":violet-badge[State:] {v.get('dealer_state')} "
            f":violet-badge[Phone:] {v.get('dealer_phone')}",
            unsafe_allow_html=True,
        )
        st.markdown(f":orange-badge[Distance] {distance}", unsafe_allow_html=True)


def _listing_extra_and_options(v: pd.Series) -> None:
    listing_id = st.session_state.selected_vid
    extra = cache.get_listing_extra(listing_id)

    if not extra:
        st.info("Listing options, features, and seller comments not yet retrieved.")
        if st.button("Retrieve listing details (1 API call)", key="get_extra"):
            try:
                cache.fetch_listing_extra(listing_id, v.get("seller_type") or "dealer")
                st.rerun()
            except MarketCheckError as exc:
                st.error(str(exc))
        return

    parsed = options_decode.parse_listing_extra(extra)
    comments = parsed["seller_comments"] or "No seller comments in listing"
    st.text_area("Seller Comments", comments, disabled=True, height=160)

    if parsed["options"]:
        st.caption("Options (as listed)")
        st.table(parsed["options"])
    if parsed["features"]:
        st.caption("Features (as listed)")
        st.table(parsed["features"])

    _vin_decode_section(v)


def _vin_decode_section(v: pd.Series) -> None:
    """Feature F4: pull the full factory option list for this exact VIN, on demand."""
    vin = v.get("vin")
    st.write("---")
    decode = cache.get_vin_decode(vin)
    if not decode:
        st.caption(
            "Used listings rarely disclose every factory option. Decode this VIN to "
            "pull the full option list from MarketCheck."
        )
        if st.button("Decode full options for this VIN (1 API call)", key="decode_vin"):
            try:
                cache.fetch_vin_decode(vin)
                st.rerun()
            except MarketCheckError as exc:
                st.error(str(exc))
        return

    table = options_decode.extract_options_table(decode)
    if table.empty:
        st.caption("VIN decoded, but MarketCheck returned no option list for this VIN.")
    elif list(table.columns) == ["Code"]:
        st.caption("Factory option codes (decoded from VIN). MarketCheck didn't provide "
                   "names for this model — look the codes up in the manufacturer's guide.")
        st.dataframe(table, hide_index=True, width="stretch")
    else:
        st.caption("Factory options (decoded from VIN)")
        st.dataframe(table, hide_index=True, width="stretch")


def _metrics(v: pd.Series) -> None:
    # All deltas below use delta_color="inverse", which renders an UP arrow in RED
    # and a DOWN arrow in GREEN. Streamlit sets the arrow direction from the delta
    # string's leading sign ("-" => down, otherwise up), so the sign we build must
    # match the meaning we want to convey.
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Miles", _int(v.get("miles")))

        # A price drop is good for the buyer: show it as a green, downward delta.
        price_change = None
        pcp = v.get("price_change_percent")
        if pcp is not None and not pd.isna(pcp) and v.get("price"):
            reduced = round(v["price"] * (abs(pcp) / (100 - abs(pcp))), -1)
            price_change = f"-${reduced:,.0f}"  # leading "-" => down arrow => green
        c2.metric(
            "Days on Market", _int(v.get("dom")), delta=price_change,
            delta_color="inverse",
            help=f"The amount the seller has adjusted the price since originally "
                 f"listed {_int(v.get('dom'))} days ago.",
        )

        pred = v.get("vefi_predicted_price")
        if pred is not None and not pd.isna(pred) and pred > 0:
            c3.metric("Predicted", f"${pred:,.0f}",
                      help="Predicted price is calculated on the currently filtered vehicles.")

        # Actual vs. predicted price. vefi_deal_percentage is positive when the car
        # is priced UNDER prediction (a good deal) and negative when OVER.
        #   over predicted (bad)  -> "+…" -> up arrow, red
        #   under predicted (good) -> "-…" -> down arrow, green
        price = v.get("price")
        actual = f"${price:,.0f}" if price and not pd.isna(price) and price > 0 else "Call Dealer"
        c4.metric("Actual Price", actual, delta=deal_delta_text(v.get("vefi_deal_percentage")),
                  delta_color="inverse")


def deal_delta_text(deal) -> str | None:
    """Build the signed 'Actual Price' delta string.

    ``deal`` is ``vefi_deal_percentage`` — positive when priced UNDER prediction
    (a good deal), negative when OVER. The leading sign drives Streamlit's arrow
    direction under ``delta_color="inverse"``:
      * over predicted (bad)  -> "+…" -> up arrow, red
      * under predicted (good) -> "-…" -> down arrow, green
    """
    if deal is None or pd.isna(deal):
        return None
    if deal < 0:  # priced over predicted
        return f"+{abs(deal):.1f}% over predicted"
    return f"-{abs(deal):.1f}% under predicted"


def _photo_carousel(v: pd.Series) -> None:
    vin = st.session_state.selected_vin
    photo_links = cache.get_image_links(vin)
    if not photo_links:
        st.caption("No photos cached for this listing.")
        return

    if st.session_state.previous_vin != vin:
        st.session_state.current_pic_index = 0
        st.session_state.previous_vin = vin
    if st.session_state.current_pic_index >= len(photo_links):
        st.session_state.current_pic_index = 0

    bm_col, prev_col, next_col, count_col = st.columns([0.35, 0.2, 0.2, 0.25],
                                                       vertical_alignment="bottom")
    with bm_col:
        _bookmark_button(v)
    with prev_col:
        if st.button("‹ Prev"):
            st.session_state.current_pic_index = (
                st.session_state.current_pic_index - 1) % len(photo_links)
    with next_col:
        if st.button("Next ›"):
            st.session_state.current_pic_index = (
                st.session_state.current_pic_index + 1) % len(photo_links)
    with count_col:
        st.caption(f"Image {st.session_state.current_pic_index + 1} of {len(photo_links)}")

    st.image(photo_links[st.session_state.current_pic_index])


def _bookmark_button(v: pd.Series) -> None:
    is_bookmarked = bool(v.get("vefi_bookmarked"))
    style = "primary" if is_bookmarked else "secondary"
    if st.button("", icon=":material/bookmark:", type=style, key="bookmark_btn"):
        df = st.session_state.df
        mask = df["vin"] == v["vin"]
        current = df.loc[mask, "vefi_bookmarked"].iloc[0]
        df.loc[mask, "vefi_bookmarked"] = not current if current else True
        state.persist_working_df()
        st.rerun()


def _int(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"
