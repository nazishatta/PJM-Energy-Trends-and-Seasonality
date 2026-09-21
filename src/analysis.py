"""Validated, reusable time-series calculations for the PJME dashboard.

All intervals below are descriptive or uncertainty intervals for historical
statistics. They are not forecasts of future electricity demand.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose

ANALYSIS_START = "2002-02-01"
ANALYSIS_END = "2018-07-01"
COMPLETE_YEARS_START = "2003-01-01"
COMPLETE_YEARS_END = "2017-12-01"


def analysis_months(monthly: pd.Series) -> pd.Series:
    """Full interior months, regular at monthly-start frequency; no silent interpolation."""
    series = monthly.sort_index().loc[ANALYSIS_START:ANALYSIS_END].astype(float)
    if series.index.has_duplicates:
        raise ValueError("Monthly timestamps must be unique.")
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Expected a DatetimeIndex.")
    expected = pd.date_range(series.index.min(), series.index.max(), freq="MS")
    if not series.index.equals(expected) or series.isna().any():
        raise ValueError("Monthly observations must be complete and contiguous.")
    if len(series) < 24:
        raise ValueError("Need at least two annual cycles for decomposition.")
    return series


def rolling_spread(monthly: pd.Series, window: int = 12) -> pd.DataFrame:
    """Mean ±2 sample SD of observed months within each window, NOT a 95% CI."""
    if window < 2 or window > len(monthly):
        raise ValueError("Invalid rolling-window length")
    roll = monthly.rolling(window, min_periods=window)
    center = roll.mean()
    std = roll.std(ddof=1)
    return pd.DataFrame({
        "mean": center,
        "std": std,
        "lower": center - 2 * std,
        "upper": center + 2 * std,
    }).dropna()


def complete_year_profile(monthly: pd.Series) -> pd.DataFrame:
    """Calendar-year × calendar-month matrix; discard any year lacking 12 months."""
    s = monthly.sort_index().loc[COMPLETE_YEARS_START:COMPLETE_YEARS_END]
    frame = s.rename("demand_mw").to_frame()
    frame["year"] = frame.index.year
    frame["month"] = frame.index.month
    pivot = frame.pivot(index="year", columns="month", values="demand_mw")
    pivot = pivot.reindex(columns=range(1, 13)).dropna(axis=0, how="any")
    if len(pivot) < 3:
        raise ValueError("At least three complete years required for seasonal bootstrap.")
    return pivot


def seasonal_year_bootstrap(
    monthly: pd.Series, *, n_boot: int = 2000, seed: int = 42
) -> pd.DataFrame:
    """95% percentile CI for each historical calendar-month mean.

    Bootstrap units are whole years, so months within a selected year are
    resampled together. Intervals describe the historical year population
    under a year-exchangeability approximation and are NOT a forecast band.
    """
    if n_boot < 100:
        raise ValueError("Use at least 100 bootstrap resamples.")
    pivot = complete_year_profile(monthly)
    values = pivot.to_numpy(dtype=float)
    n_years = len(values)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n_years, size=(n_boot, n_years))
    estimates = values[indices].mean(axis=1)
    low, high = np.percentile(estimates, [2.5, 97.5], axis=0)
    result = pd.DataFrame({
        "month": np.arange(1, 13),
        "mean": values.mean(axis=0),
        "ci_low": low,
        "ci_high": high,
    })
    result.attrs["years"] = (int(pivot.index.min()), int(pivot.index.max()))
    result.attrs["n_years"] = n_years
    result.attrs["n_boot"] = n_boot
    return result


def moving_block_mean_bootstrap(
    monthly: pd.Series, *, n_boot: int = 2000, block_length: int = 12,
    seed: int = 42,
) -> dict:
    """Circular moving-block bootstrap of the historical overall mean.

    A block spans 12 consecutive months by default, partially preserving
    within-year serial dependence. This is approximate with a changing trend
    or other nonstationarity; it does not predict individual months.
    """
    if n_boot < 100:
        raise ValueError("Use at least 100 bootstrap resamples.")
    s = analysis_months(monthly)
    values = s.to_numpy(dtype=float)
    n = len(values)
    if not 1 <= block_length <= n:
        raise ValueError("Invalid block length")
    rng = np.random.default_rng(seed)
    blocks_per_sample = int(np.ceil(n / block_length))
    starts = rng.integers(0, n, size=(n_boot, blocks_per_sample))
    offsets = np.arange(block_length)
    indices = (starts[..., None] + offsets) % n
    sample_values = values[indices.reshape(n_boot, -1)[:, :n]]
    means = sample_values.mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return {
        "estimate": float(values.mean()),
        "lo": float(lo),
        "hi": float(hi),
        "bootstrap_means": means,
        "n_boot": n_boot,
        "block_length": block_length,
        "observations": n,
    }


def decomposition_comparison(monthly: pd.Series, period: int = 12) -> dict:
    """Additive and multiplicative decompositions on identical monthly data."""
    s = analysis_months(monthly)
    if (s <= 0).any():
        raise ValueError("Multiplicative decomposition requires positive MW values.")
    additive = seasonal_decompose(
        s, model="additive", period=period, extrapolate_trend="freq"
    )
    multiplicative = seasonal_decompose(
        s, model="multiplicative", period=period, extrapolate_trend="freq"
    )
    add_pct = 100 * additive.resid / additive.trend
    mult_pct = 100 * (multiplicative.resid - 1)
    return {
        "additive": additive,
        "multiplicative": multiplicative,
        "add_pct": add_pct,
        "mult_pct": mult_pct,
        "period": period,
        "n": len(s),
    }
