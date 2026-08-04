# SPDX-License-Identifier: GPL-3.0-or-later
"""Option / feature decoding (Feature F4).

Used-car listings rarely disclose every factory option. Two sources help:

* the listing **extra** payload — free-text options, features, and seller
  comments the dealer entered; and
* the **VIN decode** (NeoVIN) — the factory-installed option list for that exact
  VIN.

The VIN decode costs a metered API call, so the GUI only fetches it when the user
explicitly asks (see :mod:`vefi.cache`). This module just normalizes whatever
those endpoints return into display-friendly structures; it makes no network
calls itself.

It replaces the original hardcoded Lexus-LC-500 option table with a general
parser that works for any make/model.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

# Keys under which different MarketCheck payloads have carried an options list.
_OPTION_LIST_KEYS = (
    "installed_options", "installed_equipment", "options", "factory_options",
    "equipment", "high_value_features",
)


def parse_listing_extra(extra_json: dict) -> dict[str, Any]:
    """Pull the useful fields out of a listing 'extra' payload."""
    extra_json = extra_json or {}
    return {
        "id": extra_json.get("id"),
        "options": extra_json.get("options", []),
        "features": extra_json.get("features", []),
        "seller_comments": extra_json.get("seller_comments", ""),
        "high_value_features": extra_json.get("high_value_features", []),
        "options_packages": extra_json.get("options_packages", []),
    }


# MarketCheck's single-character option types.
_OPTION_TYPE_LABELS = {"P": "Package", "O": "Option", "S": "Standard"}


def extract_options_table(decode_json: dict) -> pd.DataFrame:
    """Normalize a VIN-decode payload into an options table.

    MarketCheck's NeoVIN decode returns ``installed_options_details`` — a list of
    ``{code, name, msrp, type}`` where ``name`` is already human-readable (e.g.
    "GF" -> "Heads-up Display"), so no per-model code mapping is needed. When only
    the raw package codes are available (``options_packages``), those are shown as
    codes. Returns an empty DataFrame if nothing option-like is present.
    """
    if not decode_json:
        return pd.DataFrame()

    # Preferred: full option details with readable names + MSRP.
    details = decode_json.get("installed_options_details")
    if isinstance(details, list) and details:
        rows = [_row_from_detail(o) for o in details if isinstance(o, dict)]
        rows = [r for r in rows if r]
        if rows:
            df = pd.DataFrame(rows)
            return _order(df, ["Code", "Option", "Type", "MSRP"])

    # Fallback: only the package codes (comma-separated string). Show raw codes so
    # a shopper who knows the model can look them up in manufacturer data.
    packages = decode_json.get("options_packages")
    if isinstance(packages, str) and packages.strip():
        codes = [c.strip() for c in packages.split(",") if c.strip()]
        if codes:
            return pd.DataFrame({"Code": codes})
    if isinstance(packages, list) and packages:
        return pd.DataFrame({"Code": [str(c) for c in packages]})

    # Last resort: any generic list of options under a known key (top level or a
    # nested specs/vin/data object).
    candidates = [decode_json]
    for nested_key in ("specs", "vin", "data"):
        nested = decode_json.get(nested_key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for obj in candidates:
        for key in _OPTION_LIST_KEYS:
            value = obj.get(key)
            if isinstance(value, list) and value:
                rows = [_normalize_option(item) for item in value]
                return _order(pd.DataFrame(rows), ["Code", "Option", "Type", "MSRP"])

    return pd.DataFrame()


def _row_from_detail(o: dict) -> dict[str, Any]:
    row: dict[str, Any] = {}
    if o.get("code"):
        row["Code"] = o["code"]
    name = o.get("name") or o.get("description")
    if name:
        row["Option"] = name
    otype = o.get("type")
    if otype:
        row["Type"] = _OPTION_TYPE_LABELS.get(otype, otype)
    msrp = _format_msrp(o.get("msrp"))
    if msrp:
        row["MSRP"] = msrp
    return row


def _format_msrp(value: Any) -> str:
    """Format an MSRP as currency; blank for missing/zero/non-numeric."""
    try:
        amount = int(float(str(value)))
    except (TypeError, ValueError):
        return ""
    return f"${amount:,}" if amount > 0 else ""


def _order(df: pd.DataFrame, preferred: list[str]) -> pd.DataFrame:
    cols = [c for c in preferred if c in df.columns] + \
           [c for c in df.columns if c not in preferred]
    return df[cols]


def _normalize_option(item: Any) -> dict[str, Any]:
    if isinstance(item, str):
        return {"Option": item}
    if isinstance(item, dict):
        row: dict[str, Any] = {}
        name = item.get("name") or item.get("description") or item.get("option")
        if name:
            row["Option"] = name
        code = item.get("code") or item.get("option_code")
        if code:
            row["Code"] = code
        otype = item.get("type") or item.get("category")
        if otype:
            row["Type"] = _OPTION_TYPE_LABELS.get(otype, otype)
        price = _format_msrp(item.get("msrp") or item.get("price"))
        if price:
            row["MSRP"] = price
        return row or {str(k): v for k, v in item.items()}
    return {"Option": str(item)}
