from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import matplotlib.pyplot as plt
import altair as alt

from src.analysis import (
    analysis_months, rolling_spread, seasonal_year_bootstrap,
    moving_block_mean_bootstrap, decomposition_comparison,
)


# =========================================================
# PAGE CONFIG + DARK THEME
# =========================================================

st.set_page_config(
    page_title="PJM Energy Trends & Seasonality",
    page_icon="⚡",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp,
    [data-testid="stAppViewContainer"] {
        background: #17191f;
        color: #e8ecf1;
    }

    section[data-testid="stSidebar"] {
        background: #111318;
        border-right: 1px solid #2a2f3a;
    }

    [data-testid="stMarkdownContainer"],
    [data-testid="stCaptionContainer"],
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        color: #e8ecf1;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #f5f7fb !important;
    }

    div[data-baseweb="select"] > div {
        background: #f7f8fa !important;
        border-color: #717784 !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] svg {
        color: #17191f !important;
        fill: #17191f !important;
    }

    div[role="listbox"] {
        background: #ffffff !important;
        border: 1px solid #c8ccd4 !important;
    }

    div[role="option"],
    div[role="option"] * {
        background: #ffffff !important;
        color: #111827 !important;
        opacity: 1 !important;
    }

    div[role="option"]:hover,
    div[role="option"][aria-selected="true"] {
        background: #e8eefc !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚡ PJM Energy Trends & Seasonality")
st.caption(
    "Smooth Plotly-native animation."
)


# ---------------------------------------------------------
# QUICK DATA CONTEXT
# ---------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)

c1.metric("Region", "PJM East")
c2.metric("Measure", "Demand")
c3.metric("Unit", "MW")
c4.metric("Coverage", "2002–2018")

st.markdown(
    """
### About the data

Historical **PJM East (PJME) electricity demand** is measured in **megawatts (MW)**.
The original hourly values are aggregated by **mean**, not sum, to compare
hourly, daily, weekly, monthly, quarterly and yearly *average demand*.
Monthly statistical analyses exclude the incomplete January 2002 and
August 2018 boundary months; the year-by-year seasonal chart uses 2003–2017.

Use the sidebar to choose an analysis. Open the **Uncertainty**, **Decomposition**
and **Altair date brush** views for the full Week 4 extensions.
"""
)


# =========================================================
# PATHS + DATA
# =========================================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "processed"

FILES = {
    "Daily": DATA_DIR / "PJME_daily.csv",
    "Weekly": DATA_DIR / "PJME_weekly.csv",
    "Monthly": DATA_DIR / "PJME_monthly.csv",
    "Quarterly": DATA_DIR / "PJME_quarterly.csv",
    "Yearly": DATA_DIR / "PJME_yearly.csv",
}


@st.cache_data
def load_series(path: str) -> pd.Series:
    df = pd.read_csv(
        path,
        parse_dates=["Datetime"],
        index_col="Datetime",
    )
    return df["PJME_MW"].dropna().sort_index().astype(float)


def get_series(resolution: str) -> pd.Series:
    s = load_series(str(FILES[resolution]))
    if resolution == "Monthly":
        s = s.loc["2002-02-01":"2018-07-01"]
    return s


monthly = get_series("Monthly")


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Animation Lab")

mode = st.sidebar.selectbox(
    "Choose a visualization",
    [
        "1 · Smooth rolling-window motion",
        "2 · Seasonal pattern by year",
        "3 · Progressive time-series reveal",
        "4 · Manual Streamlit-loop demo",
        "5 · Uncertainty & bootstrap confidence intervals",
        "6 · Additive vs multiplicative decomposition",
        "7 · Altair interactive date-range brush",
    ],
)

resolution = st.sidebar.selectbox(
    "Temporal resolution",
    ["Daily", "Weekly", "Monthly", "Quarterly", "Yearly"],
    index=2,
)

series = get_series(resolution)

default_window = {
    "Daily": 30,
    "Weekly": 12,
    "Monthly": 12,
    "Quarterly": 4,
    "Yearly": 3,
}[resolution]

max_window = {
    "Daily": 365,
    "Weekly": 104,
    "Monthly": 60,
    "Quarterly": 20,
    "Yearly": 10,
}[resolution]

window = st.sidebar.slider(
    "Rolling window (periods)",
    min_value=2,
    max_value=min(max_window, max(2, len(series) - 1)),
    value=min(default_window, max(2, len(series) - 1)),
)

frame_count = st.sidebar.slider(
    "Animation frames",
    min_value=20,
    max_value=80,
    value=45,
    step=5,
)

speed = st.sidebar.select_slider(
    "Playback speed",
    options=["Slow", "Normal", "Fast"],
    value="Normal",
)

FRAME_MS = {
    "Slow": 750,
    "Normal": 450,
    "Fast": 250,
}[speed]

TRANSITION_MS = {
    "Slow": 300,
    "Normal": 180,
    "Fast": 90,
}[speed]


# =========================================================
# SHARED STYLING
# =========================================================

def style_plot(fig, title, s=None, bottom=115):
    fig.update_layout(
        title=title,
        paper_bgcolor="#17191f",
        plot_bgcolor="#1f2430",
        font=dict(color="#e8ecf1"),
        height=600,
        margin=dict(l=60, r=30, t=80, b=bottom),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.08)",
        zerolinecolor="rgba(255,255,255,0.08)",
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.08)",
        zerolinecolor="rgba(255,255,255,0.08)",
    )

    if s is not None:
        span = s.max() - s.min()
        pad = max(500, span * 0.08)

        fig.update_xaxes(
            range=[s.index.min(), s.index.max()],
            title="Date",
        )

        fig.update_yaxes(
            range=[s.min() - pad, s.max() + pad],
            title="Average electricity demand (MW)",
        )

    return fig


def play_controls(frame_ms, transition_ms):
    return [
        dict(
            type="buttons",
            direction="left",
            x=0,
            y=-0.18,
            showactive=False,
            buttons=[
                dict(
                    label="▶ Play",
                    method="animate",
                    args=[
                        None,
                        {
                            "fromcurrent": True,
                            "mode": "immediate",
                            "frame": {
                                "duration": frame_ms,
                                "redraw": False,
                            },
                            "transition": {
                                "duration": transition_ms,
                                "easing": "cubic-in-out",
                            },
                        },
                    ],
                ),
                dict(
                    label="❚❚ Pause",
                    method="animate",
                    args=[
                        [None],
                        {
                            "mode": "immediate",
                            "frame": {
                                "duration": 0,
                                "redraw": False,
                            },
                            "transition": {
                                "duration": 0,
                            },
                        },
                    ],
                ),
            ],
        )
    ]


# =========================================================
# 1) SMOOTH ROLLING-WINDOW ANIMATION — PLOTLY FRAMES
# =========================================================

def build_smooth_rolling_animation(
    s: pd.Series,
    window_size: int,
    n_frames: int,
    resolution_name: str,
    frame_ms: int,
    transition_ms: int,
) -> go.Figure:

    s = s.dropna().sort_index()
    rolled = s.rolling(window_size).mean()

    start = window_size
    positions = np.unique(
        np.linspace(
            start,
            len(s),
            num=min(n_frames, max(2, len(s) - start + 1)),
            dtype=int,
        )
    ).tolist()

    if positions[-1] != len(s):
        positions.append(len(s))

    y_min = float(s.min())
    y_max = float(s.max())

    first = positions[0]
    left = s.index[first - window_size]
    right = s.index[first - 1]

    # Four traces:
    # 0 = full series, static
    # 1 = rolling mean revealed over time
    # 2 = translucent moving window rectangle as a polygon
    # 3 = current rolling-mean point
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=s.index,
            y=s.values,
            mode="lines",
            name=f"{resolution_name} demand",
            line=dict(
                width=1.3,
                color="rgba(145,165,255,0.33)",
            ),
            hovertemplate="%{x}<br>%{y:,.0f} MW<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=rolled.index[:first],
            y=rolled.iloc[:first],
            mode="lines",
            name=f"{window_size}-period rolling mean",
            line=dict(
                width=3.2,
                color="#ff7a59",
                shape="linear",
            ),
            hovertemplate="%{x}<br>%{y:,.0f} MW<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[left, right, right, left, left],
            y=[y_min, y_min, y_max, y_max, y_min],
            mode="lines",
            fill="toself",
            fillcolor="rgba(110,168,254,0.14)",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    first_value = rolled.iloc[first - 1]

    fig.add_trace(
        go.Scatter(
            x=[rolled.index[first - 1]],
            y=[first_value],
            mode="markers",
            marker=dict(
                size=11,
                color="#ff4d6d",
                line=dict(color="white", width=2),
            ),
            hovertemplate="%{x}<br>%{y:,.0f} MW<extra></extra>",
            showlegend=False,
        )
    )

    frames = []

    for upto in positions:
        left = s.index[upto - window_size]
        right = s.index[upto - 1]
        current_value = rolled.iloc[upto - 1]

        frames.append(
            go.Frame(
                name=str(upto),
                traces=[1, 2, 3],
                data=[
                    go.Scatter(
                        x=rolled.index[:upto],
                        y=rolled.iloc[:upto],
                    ),
                    go.Scatter(
                        x=[left, right, right, left, left],
                        y=[y_min, y_min, y_max, y_max, y_min],
                    ),
                    go.Scatter(
                        x=[rolled.index[upto - 1]],
                        y=[current_value],
                    ),
                ],
            )
        )

    fig.frames = frames

    slider_steps = []

    for i, upto in enumerate(positions):
        date = s.index[upto - 1]
        label = (
            date.strftime("%Y")
            if i == 0 or date.year != s.index[positions[i - 1] - 1].year
            else ""
        )

        slider_steps.append(
            dict(
                label=label,
                method="animate",
                args=[
                    [str(upto)],
                    {
                        "mode": "immediate",
                        "frame": {
                            "duration": 0,
                            "redraw": False,
                        },
                        "transition": {
                            "duration": 0,
                        },
                    },
                ],
            )
        )

    fig.update_layout(
        updatemenus=play_controls(frame_ms, transition_ms),
        sliders=[
            dict(
                active=0,
                currentvalue=dict(prefix="Through: "),
                pad=dict(t=45),
                steps=slider_steps,
            )
        ],
    )

    return style_plot(
        fig,
        f"Smooth Rolling Window · {resolution_name} · {window_size} periods",
        s,
    )


# =========================================================
# 2) SEASONAL PATTERN BY YEAR
# =========================================================

def build_seasonal_year_animation(monthly_s: pd.Series) -> go.Figure:
    seasonal = monthly_s.loc["2003-01-01":"2017-12-01"].copy()

    df = seasonal.rename("PJME_MW").to_frame()
    df["year"] = df.index.year
    df["month_num"] = df.index.month

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]

    df["month"] = df["month_num"].map(
        dict(enumerate(month_names, start=1))
    )

    years = sorted(df["year"].unique())

    y_min = df["PJME_MW"].min()
    y_max = df["PJME_MW"].max()
    pad = (y_max - y_min) * 0.08

    first_year = years[0]
    first = df[df["year"] == first_year].sort_values("month_num")

    fig = go.Figure(
        data=[
            go.Scatter(
                x=first["month"],
                y=first["PJME_MW"],
                mode="lines+markers",
                line=dict(
                    width=3,
                    color="#78a6ff",
                    shape="linear",
                ),
                marker=dict(size=9, color="#ff8c42"),
                name=str(first_year),
            )
        ]
    )

    fig.frames = [
        go.Frame(
            name=str(year),
            data=[
                go.Scatter(
                    x=df[df["year"] == year].sort_values("month_num")["month"],
                    y=df[df["year"] == year].sort_values("month_num")["PJME_MW"],
                )
            ],
        )
        for year in years
    ]

    fig.update_layout(
        xaxis=dict(
            title="Month",
            categoryorder="array",
            categoryarray=month_names,
        ),
        yaxis=dict(
            title="Average electricity demand (MW)",
            range=[y_min - pad, y_max + pad],
        ),
        updatemenus=play_controls(FRAME_MS, TRANSITION_MS),
        sliders=[
            dict(
                active=0,
                currentvalue=dict(prefix="Year: "),
                pad=dict(t=45),
                steps=[
                    dict(
                        label=str(year),
                        method="animate",
                        args=[
                            [str(year)],
                            {
                                "mode": "immediate",
                                "frame": {
                                    "duration": 0,
                                    "redraw": False,
                                },
                                "transition": {
                                    "duration": 0,
                                },
                            },
                        ],
                    )
                    for year in years
                ],
            )
        ],
    )

    return style_plot(
        fig,
        "PJM East Seasonal Pattern by Year",
        None,
    )


# =========================================================
# 3) PROGRESSIVE TIME-SERIES REVEAL
# =========================================================

def build_progressive_reveal(
    monthly_s: pd.Series,
    window_size=12,
    n_frames=55,
) -> go.Figure:

    s = monthly_s.dropna().sort_index()
    rolling = s.rolling(window_size).mean()

    positions = np.unique(
        np.linspace(
            window_size,
            len(s),
            num=min(n_frames, len(s) - window_size + 1),
            dtype=int,
        )
    ).tolist()

    first = positions[0]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=s.index,
            y=s.values,
            mode="lines",
            name="Full-series context",
            line=dict(width=1, color="rgba(255,255,255,0.09)"),
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=s.index[:first],
            y=s.iloc[:first],
            mode="lines",
            name="Observed demand",
            line=dict(width=2.3, color="#78a6ff"),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=rolling.index[:first],
            y=rolling.iloc[:first],
            mode="lines",
            name="12-month rolling trend",
            line=dict(
                width=3,
                color="#ff8c42",
                shape="linear",
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=[s.index[first - 1]],
            y=[s.iloc[first - 1]],
            mode="markers",
            marker=dict(
                size=11,
                color="#00d4aa",
                line=dict(color="white", width=2),
            ),
            showlegend=False,
        )
    )

    fig.frames = [
        go.Frame(
            name=str(upto),
            traces=[1, 2, 3],
            data=[
                go.Scatter(
                    x=s.index[:upto],
                    y=s.iloc[:upto],
                ),
                go.Scatter(
                    x=rolling.index[:upto],
                    y=rolling.iloc[:upto],
                ),
                go.Scatter(
                    x=[s.index[upto - 1]],
                    y=[s.iloc[upto - 1]],
                ),
            ],
        )
        for upto in positions
    ]

    fig.update_layout(
        updatemenus=play_controls(FRAME_MS, TRANSITION_MS),
        sliders=[
            dict(
                active=0,
                currentvalue=dict(prefix="Through: "),
                pad=dict(t=45),
                steps=[
                    dict(
                        label=(
                            s.index[upto - 1].strftime("%Y")
                            if i == 0
                            or s.index[upto - 1].year
                            != s.index[positions[i - 1] - 1].year
                            else ""
                        ),
                        method="animate",
                        args=[
                            [str(upto)],
                            {
                                "mode": "immediate",
                                "frame": {
                                    "duration": 0,
                                    "redraw": False,
                                },
                                "transition": {
                                    "duration": 0,
                                },
                            },
                        ],
                    )
                    for i, upto in enumerate(positions)
                ],
            )
        ],
    )

    return style_plot(
        fig,
        "PJM East Demand Revealed Through Time",
        s,
    )


# =========================================================
# 4) MANUAL LOOP — CLASS DEMO ONLY
# =========================================================

def draw_manual_frame(
    s: pd.Series,
    rolled: pd.Series,
    upto: int,
    window_size: int,
    resolution_name: str,
):
    """
    One Matplotlib frame for the exact Week 4 Streamlit-loop pattern.

    Streamlit does NOT rebuild a Plotly component here. Instead, it receives
    one static figure image at a time through frame.pyplot(fig), matching the
    professor's demo.
    """

    fig, ax = plt.subplots(figsize=(11, 4.4))

    # Dark visual treatment
    fig.patch.set_facecolor("#17191f")
    ax.set_facecolor("#1f2430")

    # Full series context
    ax.plot(
        s.index,
        s.values,
        color="#7f8fb3",
        alpha=0.42,
        linewidth=1.0,
        label=f"{resolution_name} demand",
    )

    if upto >= window_size:
        # Current rolling window
        left = s.index[upto - window_size]
        right = s.index[upto - 1]

        ax.axvspan(
            left,
            right,
            color="#6ea8fe",
            alpha=0.18,
        )

        # Rolling mean revealed up to this frame
        ax.plot(
            rolled.index[:upto],
            rolled.iloc[:upto],
            color="#ff7a59",
            linewidth=2.6,
            label=f"{window_size}-period rolling mean",
        )

        current_value = rolled.iloc[upto - 1]

        if pd.notna(current_value):
            ax.plot(
                [rolled.index[upto - 1]],
                [current_value],
                "o",
                color="#ff4d6d",
                markersize=7,
                markeredgecolor="white",
                markeredgewidth=1.2,
            )

    # FIXED axes throughout playback
    span = s.max() - s.min()
    pad = max(500, span * 0.08)

    ax.set_xlim(s.index.min(), s.index.max())
    ax.set_ylim(s.min() - pad, s.max() + pad)

    ax.set_title(
        f"Manual Streamlit Redraw · {resolution_name} · {window_size}-period window",
        color="#f5f7fb",
        fontsize=13,
        pad=12,
    )

    ax.set_xlabel("Date", color="#e8ecf1")
    ax.set_ylabel("Average electricity demand (MW)", color="#e8ecf1")

    ax.tick_params(colors="#cbd5e1")
    ax.grid(
        True,
        alpha=0.14,
        linewidth=0.7,
        color="#cbd5e1",
    )

    for spine in ax.spines.values():
        spine.set_color("#4b5563")

    legend = ax.legend(
        loc="upper left",
        frameon=False,
    )

    if legend is not None:
        for t in legend.get_texts():
            t.set_color("#e8ecf1")

    fig.tight_layout()

    return fig


@st.fragment
def manual_loop_demo():
    st.subheader("4 · Manual Streamlit-loop demo")

    st.info(
        "This is the exact class-style mechanism: Matplotlib draws one frame, "
        "`st.empty()` provides one reusable slot, and `frame.pyplot(fig)` "
        "overwrites the previous image. It is intentionally different from "
        "the smoother Plotly-native animations above."
    )

    c1, c2 = st.columns([1, 4])

    play = c1.button(
        "▶ Play manual loop",
        type="primary",
        use_container_width=True,
    )

    status = c2.empty()

    rolled = series.rolling(window).mean()

    frame = st.empty()

    # Fewer / larger steps are deliberate: the professor's Week 4 material
    # says redraw cost sets the pace, so do not add sleep.
    manual_frames = min(frame_count, 40)
    step = max(
        1,
        (len(series) - window) // manual_frames,
    )

    if play:
        for upto in range(
            window,
            len(series) + 1,
            step,
        ):
            status.caption(
                f"Frame through {series.index[upto - 1]:%Y-%m-%d}"
            )

            fig = draw_manual_frame(
                series,
                rolled,
                upto,
                window,
                resolution,
            )

            # This is the Week 4 pattern shown in class.
            frame.pyplot(
                fig,
                use_container_width=True,
            )

            # Prevent Matplotlib figures from accumulating in memory.
            plt.close(fig)

    # Always leave a useful final static chart visible.
    final_fig = draw_manual_frame(
        series,
        rolled,
        len(series),
        window,
        resolution,
    )

    frame.pyplot(
        final_fig,
        use_container_width=True,
    )

    plt.close(final_fig)

    status.caption(
        "Final frame shown. Change the window and press Play again."
    )


# =========================================================
# EXTENSION 5 — UNCERTAINTY VISUALIZATION
# =========================================================

@st.cache_data(show_spinner=False)
def cached_year_bootstrap(s: pd.Series, n_boot: int):
    return seasonal_year_bootstrap(s, n_boot=n_boot, seed=42)


@st.cache_data(show_spinner=False)
def cached_block_bootstrap(s: pd.Series, n_boot: int):
    return moving_block_mean_bootstrap(
        s, n_boot=n_boot, block_length=12, seed=42
    )


def uncertainty_panel():
    st.subheader("5 · Understanding variability and uncertainty")
    st.markdown(
        """**Two shaded bands can look similar while answering different questions.**
        The rolling ±2 SD band shows the *spread of observed demand* within
        a 12-month window. The bootstrapped seasonal band estimates
        *uncertainty in the historical mean for each calendar month*.
        Neither is a forecast or a prediction interval for future demand."""
    )
    s = analysis_months(monthly)
    resamples = st.slider(
        "Bootstrap resamples", 500, 5000, 2000, 500,
        help="Resampling entire years preserves their within-year monthly pattern.",
    )
    tab_ci, tab_spread, tab_mean = st.tabs([
        "95% CI band · seasonal averages",
        "±2 SD · rolling spread",
        "95% CI · overall historical mean",
    ])

    with tab_ci:
        profile = cached_year_bootstrap(s, resamples)
        labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels, y=profile["ci_high"], mode="lines",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=labels, y=profile["ci_low"], mode="lines",
            line=dict(width=0), fill="tonexty",
            fillcolor="rgba(110,168,254,0.25)",
            name="95% year-bootstrap CI for the seasonal mean",
            hovertemplate="%{x}: lower bound %{y:,.0f} MW<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=labels, y=profile["mean"], mode="lines+markers",
            name="Mean demand by calendar month",
            line=dict(color="#ff8c42", width=3),
            marker=dict(size=8),
            hovertemplate="%{x}: mean %{y:,.0f} MW<extra></extra>",
        ))
        fig = style_plot(
            fig, "Seasonal monthly average · year-resampled 95% confidence band",
            bottom=80,
        )
        fig.update_xaxes(title="Calendar month", type="category")
        fig.update_yaxes(title="Average electricity demand (MW)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"{profile.attrs['n_years']} complete calendar years "
            f"({profile.attrs['years'][0]}–{profile.attrs['years'][1]}); "
            f"{resamples:,} bootstrap resamples of whole years, with replacement."
        )
        st.info(
            "**Interpretation:** The ribbon describes uncertainty in each "
            "calendar month's *historical average across years*. Entire years "
            "are resampled as units to retain within-year dependence. The "
            "interval is not the likely range of an individual month, "
            "and year-to-year trend/nonstationarity limits its interpretation."
        )

    with tab_spread:
        spread = rolling_spread(s, window=12)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=spread.index, y=spread["upper"], mode="lines",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=spread.index, y=spread["lower"], mode="lines",
            line=dict(width=0), fill="tonexty",
            fillcolor="rgba(125,165,250,0.20)",
            name="12-month rolling mean ±2 SD (spread)",
        ))
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, mode="lines", name="Monthly demand",
            line=dict(color="rgba(160,180,245,0.45)", width=1.2),
        ))
        fig.add_trace(go.Scatter(
            x=spread.index, y=spread["mean"], mode="lines",
            name="12-month rolling mean",
            line=dict(color="#ff8c42", width=3),
        ))
        fig = style_plot(fig, "Observed monthly spread around the 12-month mean", bottom=75)
        fig.update_xaxes(title="Date")
        fig.update_yaxes(title="Demand (MW)")
        fig.update_yaxes(range=[
            float(min(s.min(), spread["lower"].min())) - 800,
            float(max(s.max(), spread["upper"].max())) + 800,
        ])
        st.plotly_chart(fig, use_container_width=True)
        st.warning(
            "**This is NOT a 95% confidence interval.** It is the observed "
            "12-month rolling mean ±2 sample standard deviations. A ±2 SD "
            "range describes variation in the data; approximate 95% coverage "
            "would require distributional assumptions that may not hold here."
        )

    with tab_mean:
        boot = cached_block_bootstrap(s, resamples)
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=boot["bootstrap_means"], nbinsx=42,
            name="Moving-block bootstrap means", marker_color="#78a6ff",
        ))
        for x, name, color, dash in [
            (boot["lo"], "2.5th percentile", "#ff8c42", "dash"),
            (boot["hi"], "97.5th percentile", "#ff8c42", "dash"),
            (boot["estimate"], "Observed sample mean", "#00d4aa", "solid"),
        ]:
            fig.add_vline(x=x, line_color=color, line_dash=dash,
                          annotation_text=name, annotation_position="top")
        fig = style_plot(fig, "Uncertainty in the overall historical monthly mean", bottom=80)
        fig.update_xaxes(title="Estimated mean demand (MW)")
        fig.update_yaxes(title="Bootstrap frequency")
        st.plotly_chart(fig, use_container_width=True)
        a, b, c = st.columns(3)
        a.metric("Historical mean", f"{boot['estimate']:,.0f} MW")
        b.metric("95% CI lower", f"{boot['lo']:,.0f} MW")
        c.metric("95% CI upper", f"{boot['hi']:,.0f} MW")
        st.caption(
            f"Circular moving-block bootstrap: {resamples:,} replicates, "
            f"{boot['block_length']} consecutive months per block, "
            f"{boot['observations']} complete interior monthly observations."
        )
        st.info(
            "**Interpretation:** This is an approximate 95% confidence interval "
            "for the *overall historical mean demand*, not a band for monthly "
            "observations or future predictions. Twelve-month blocks preserve "
            "some serial dependence, but long-run trend and nonstationarity "
            "remain important limitations."
        )


# =========================================================
# EXTENSION 6 — ADDITIVE VS MULTIPLICATIVE DECOMPOSITION
# =========================================================

def decomposition_panel():
    st.subheader("6 · Additive versus multiplicative decomposition")
    st.markdown(
        """The differenced monthly series exhibits annual repetition, so both
        models use **12 observations per seasonal cycle**. The same 198 complete
        interior months are used in both comparisons.

        - **Additive:** observed = trend + seasonal + residual (MW).
        - **Multiplicative:** observed = trend × seasonal × residual (ratios).
        """
    )
    s = analysis_months(monthly)
    results = decomposition_comparison(s, period=12)
    a, m = st.tabs(["Side-by-side decomposition", "Comparable residuals (%)"])
    with a:
        from plotly.subplots import make_subplots
        fig = make_subplots(
            rows=4, cols=2, shared_xaxes="columns", vertical_spacing=0.065,
            subplot_titles=[
                "Additive · observed MW", "Multiplicative · observed MW",
                "Additive · trend MW", "Multiplicative · trend MW",
                "Additive · seasonal MW", "Multiplicative · seasonal factor",
                "Additive · residual MW", "Multiplicative · residual factor",
            ],
        )
        colors = ["#78a6ff", "#ff8c42", "#00d4aa", "#bc97ff"]
        for col, key in enumerate(["additive", "multiplicative"], start=1):
            res = results[key]
            for row, values in enumerate(
                [res.observed, res.trend, res.seasonal, res.resid], start=1
            ):
                fig.add_trace(go.Scatter(
                    x=values.index, y=values.values,
                    mode="lines", line=dict(color=colors[row - 1], width=1.8),
                    showlegend=False,
                ), row=row, col=col)
        fig = style_plot(
            fig, "Same monthly demand, two different seasonal models", bottom=70
        )
        fig.update_layout(height=990, hovermode="x")
        for row in [1, 2, 3, 4]:
            for col in [1, 2]:
                fig.update_xaxes(gridcolor="rgba(255,255,255,0.07)",
                                 row=row, col=col)
                fig.update_yaxes(gridcolor="rgba(255,255,255,0.07)",
                                 row=row, col=col)
        fig.update_yaxes(title_text="MW", row=3, col=1)
        fig.update_yaxes(title_text="×", row=3, col=2)
        fig.update_yaxes(title_text="MW", row=4, col=1)
        fig.update_yaxes(title_text="×", row=4, col=2)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Seasonal and residual scales differ between models: additive is "
            "measured in MW, multiplicative as ratios. Do not compare their "
            "raw residual amplitudes directly. Trend edges are extrapolated "
            "using statsmodels `extrapolate_trend='freq'`."
        )
    with m:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=results["add_pct"].index, y=results["add_pct"],
            mode="lines", name="Additive residual / trend (%)",
            line=dict(color="#78a6ff", width=1.6),
        ))
        fig.add_trace(go.Scatter(
            x=results["mult_pct"].index, y=results["mult_pct"],
            mode="lines", name="(Multiplicative residual − 1) × 100 (%)",
            line=dict(color="#ff8c42", width=1.6),
        ))
        fig.add_hline(y=0, line_color="#cbd5e1", line_dash="dash")
        fig = style_plot(
            fig, "Residuals expressed in comparable percent-of-level units",
            bottom=80,
        )
        fig.update_xaxes(title="Date")
        fig.update_yaxes(title="Approximate residual (% of trend / ratio)")
        st.plotly_chart(fig, use_container_width=True)
        st.info(
            "**Interpretation:** Look for remaining annual repetition, changes "
            "in residual spread as demand level changes, and sustained runs "
            "above or below zero. The residuals are placed on a comparable "
            "percentage scale for visual inspection; neither model is "
            "declared universally better by this chart."
        )


# =========================================================
# EXTENSION 7 — ALTAIR INTERACTIVE DATE-RANGE BRUSH
# =========================================================

def altair_brush_panel():
    st.subheader("7 · Interactive date-range brush")
    st.markdown(
        """Drag across the **bottom overview chart** to select a period.
        The detail chart above updates in your browser without changing the
        source data. Drag the selection handles to refine it; double-click
        or click outside to clear the range."""
    )
    # Date-indexed, sorted, complete monthly data; all resolution files
    # are available to the selection. Daily data can exceed Altair's 5k
    # default inline row limit, so disable the limit *for this view*.
    alt.data_transformers.disable_max_rows()
    s = series.dropna().sort_index()
    df = s.rename("demand_mw").reset_index()
    df.columns = ["date", "demand_mw"]
    df["rolling_mw"] = s.rolling(window, min_periods=window).mean().values
    long = df.melt(
        id_vars=["date"], value_vars=["demand_mw", "rolling_mw"],
        var_name="series", value_name="mw",
    ).dropna()
    long["series"] = long["series"].map({
        "demand_mw": f"{resolution} average demand",
        "rolling_mw": f"{window}-period rolling mean",
    })
    brush = alt.selection_interval(encodings=["x"], name="date_range")
    palette = alt.Scale(
        domain=[f"{resolution} average demand", f"{window}-period rolling mean"],
        range=["#78a6ff", "#ff8c42"],
    )
    detail = (
        alt.Chart(long)
        .mark_line(strokeWidth=2)
        .encode(
            x=alt.X("date:T", title="Selected date range"),
            y=alt.Y("mw:Q", title="Average electricity demand (MW)",
                    scale=alt.Scale(zero=False)),
            color=alt.Color("series:N", scale=palette, title="Series"),
            tooltip=[
                alt.Tooltip("date:T", title="Date"),
                alt.Tooltip("mw:Q", title="Demand (MW)", format=",.0f"),
                alt.Tooltip("series:N", title="Series"),
            ],
        )
        .transform_filter(brush)
        .properties(height=390, title="Detail · drag on the overview to filter")
    )
    overview = (
        alt.Chart(df)
        .mark_area(color="#78a6ff", opacity=0.35)
        .encode(
            x=alt.X("date:T", title="Drag to select dates"),
            y=alt.Y("demand_mw:Q", title="MW", scale=alt.Scale(zero=False)),
        )
        .add_params(brush)
        .properties(height=105, title="Overview · date-range brush")
    )
    chart = alt.vconcat(detail, overview, spacing=22).resolve_scale(
        x="independent", y="independent"
    ).configure(background="#17191f").configure_view(
        stroke=None
    ).configure_axis(
        labelColor="#e8ecf1", titleColor="#e8ecf1", gridColor="#333b49"
    ).configure_title(color="#f5f7fb").configure_legend(
        labelColor="#e8ecf1", titleColor="#e8ecf1"
    )
    st.altair_chart(chart, use_container_width=True, theme=None)
    st.caption(
        f"Viewing {len(s):,} {resolution.lower()} observations; "
        f"{window}-period rolling mean. The brush filters the displayed "
        "detail only; it does not recompute the full-series rolling mean."
    )
    st.info(
        "**Temporal-honesty note:** Both charts label their units and "
        "resolution. The y-axis is permitted to start above zero because "
        "these are line/area temporal comparisons, and the selected time "
        "range is explicitly shown in the overview. Read changes in "
        "magnitude from the labeled MW axis, not simply their visual slope."
    )


# =========================================================
# RENDER
# =========================================================

if mode == "1 · Smooth rolling-window motion":
    st.subheader("1 · Smooth rolling-window motion")
    st.write(
        "This version uses **Plotly-native frames**, so the chart stays mounted "
        "and its traces transition in place instead of Streamlit destroying and "
        "recreating the chart every frame."
    )

    fig = build_smooth_rolling_animation(
        series,
        window,
        frame_count,
        resolution,
        FRAME_MS,
        TRANSITION_MS,
    )

    st.plotly_chart(fig, use_container_width=True)

elif mode == "2 · Seasonal pattern by year":
    st.subheader("2 · Seasonal pattern by year")
    st.write(
        "Each frame is one complete calendar year. Use Play/Pause or drag the slider."
    )
    st.plotly_chart(
        build_seasonal_year_animation(monthly),
        use_container_width=True,
    )

elif mode == "3 · Progressive time-series reveal":
    st.subheader("3 · Progressive time-series reveal")
    st.write(
        "Observed demand and the 12-month trend emerge progressively through time."
    )
    st.plotly_chart(
        build_progressive_reveal(
            monthly,
            window_size=12,
            n_frames=frame_count,
        ),
        use_container_width=True,
    )

elif mode == "4 · Manual Streamlit-loop demo":
    manual_loop_demo()

elif mode == "5 · Uncertainty & bootstrap confidence intervals":
    uncertainty_panel()

elif mode == "6 · Additive vs multiplicative decomposition":
    decomposition_panel()

else:
    altair_brush_panel()



# =========================================================
# DYNAMIC INTERPRETATION
# =========================================================

st.markdown("---")
st.subheader("What to notice")

if mode == "1 · Smooth rolling-window motion" or mode == "4 · Manual Streamlit-loop demo":
    if resolution == "Monthly":
        if window < 12:
            st.info(f"**{window}-month window:** retains much of the annual seasonal variation.")
        elif window == 12:
            st.success("**12-month window:** averages over a full annual cycle, revealing slower movement.")
        else:
            st.warning(f"**{window}-month window:** smooths seasonal and shorter-term movements; turning points may be suppressed.")
    else:
        st.info(f"**{resolution} view:** {window}-period smoothing changes the amount of short-term variation shown.")
elif mode == "2 · Seasonal pattern by year":
    st.info("**Seasonal comparison:** each frame represents one complete calendar year (2003–2017); compare the shape and amplitude of summer and winter demand.")
elif mode == "3 · Progressive time-series reveal":
    st.info("**Progressive reveal:** the monthly series and its 12-month rolling mean accumulate through time; the gray reference line shows the full record.")
elif mode == "5 · Uncertainty & bootstrap confidence intervals":
    st.info("**Which uncertainty?** The year-bootstrap CI estimates seasonal averages, the ±2 SD band describes variation, and the moving-block CI estimates the overall historical mean.")
elif mode == "6 · Additive vs multiplicative decomposition":
    st.info("**Decomposition:** annual trend and seasonal structures are modeled on the same complete monthly sample. Inspect comparable percent residuals before interpreting fit.")
else:
    st.info("**Date brush:** the selected temporal range changes the displayed detail; it does not alter the original observations or the precomputed rolling mean.")


# =========================================================
# HONESTY NOTE
# =========================================================

st.markdown("---")
st.subheader("Temporal-honesty choice")
st.markdown(
    f"""
The selected resolution is **{resolution}** and is displayed explicitly because
temporal aggregation changes the apparent story. Fixed y-axis limits are used
within each animation, preventing automatic rescaling from exaggerating motion.
The rolling-window length is also disclosed because smoothing changes what the
viewer sees. Monthly statistical analysis excludes incomplete boundary months.
The uncertainty ribbons are labeled separately as descriptive spread or
confidence intervals; no chart is presented as a prediction of future demand.
"""
)
