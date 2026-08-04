# SPDX-License-Identifier: GPL-3.0-or-later
"""Predicted-price / deal-percentage modeling.

Fits a degree-2 polynomial of price vs. mileage over the rows currently in view,
then flags each car as above or below its predicted price. Intended to run on the
*filtered* set so the model reflects the segment the user is actually comparing
(e.g. only 2018 coupes).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures


def _fit_model(df: pd.DataFrame):
    """Fit the degree-2 price-vs-mileage model. Returns ``(model, valid_mask)``.

    ``model`` is ``None`` if there is not enough valid data or fitting fails.
    """
    if df.empty or "miles" not in df.columns or "price" not in df.columns:
        return None, None
    valid = df["miles"].notna() & df["price"].notna()
    df_valid = df[valid]
    if len(df_valid) < 2:
        return None, valid
    try:
        model = make_pipeline(PolynomialFeatures(degree=2), LinearRegression())
        model.fit(df_valid[["miles"]].values, df_valid["price"].values)
    except Exception:
        return None, valid
    return model, valid


def add_predicted_pricing(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``vefi_predicted_price`` and ``vefi_deal_percentage`` columns.

    A positive deal percentage means the car is priced *below* prediction (a
    better deal). Rows without both price and mileage are left as NaN.
    """
    model, valid = _fit_model(df)
    if model is None:
        return df

    df.loc[valid, "vefi_predicted_price"] = model.predict(df[valid][["miles"]].values)

    price = df.loc[valid, "price"]
    pred = df.loc[valid, "vefi_predicted_price"]
    df.loc[valid, "vefi_deal_percentage"] = np.where(
        pred != 0, (pred - price) / pred * 100, np.nan
    )
    return df


def trendline(df: pd.DataFrame, n: int = 100) -> pd.DataFrame:
    """Return a smooth predicted-price curve over the filtered vehicles.

    Fits the same model as :func:`add_predicted_pricing` and evaluates it across
    the mileage range, so the chart trendline matches the per-car "Predicted"
    values. Returns an empty frame (with the right columns) when there is not
    enough data to fit.
    """
    empty = pd.DataFrame({"miles": [], "predicted_price": []})
    model, valid = _fit_model(df)
    if model is None:
        return empty
    df_valid = df[valid]
    xs = np.linspace(df_valid["miles"].min(), df_valid["miles"].max(), n)
    ys = model.predict(xs.reshape(-1, 1))
    return pd.DataFrame({"miles": xs, "predicted_price": ys})
