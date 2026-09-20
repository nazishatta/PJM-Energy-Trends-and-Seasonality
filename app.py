from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import matplotlib.pyplot as plt


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
    "Smooth Plotly-native animation for Week 4 time-series analysis."
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
### How to read this visualization

This project analyzes **PJM East electricity demand** over time.

- The faint line shows observed electricity demand.
- The orange line shows the rolling mean.
- The shaded region shows the observations currently used to calculate that mean.
- Use **Play / Pause** or drag the timeline slider to inspect how the pattern develops through time.

Changing the rolling-window length changes what the chart emphasizes:
short windows retain more seasonal variation, while longer windows reveal
the broader trend but can suppress meaningful turning points.
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
                shape="spline",
                smoothing=0.55,
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
                    shape="spline",
                    smoothing=0.55,
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
                shape="spline",
                smoothing=0.55,
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

else:
    manual_loop_demo()



# =========================================================
# DYNAMIC INTERPRETATION
# =========================================================

st.markdown("---")
st.subheader("What to notice")

if resolution == "Monthly":
    if window < 12:
        st.info(
            f"""
**{window}-month window:** this is shorter than the 12-month annual cycle.
It smooths some short-term variation, but much of the recurring seasonal
pattern remains visible.
"""
        )
    elif window == 12:
        st.success(
            """
**12-month window:** this spans one complete annual cycle.
Seasonal highs and lows largely average out, making the underlying
long-run demand trend easier to see.
"""
        )
    else:
        st.warning(
            f"""
**{window}-month window:** this is longer than one annual cycle.
The line becomes smoother, but some meaningful shorter-term changes
and turning points may also be suppressed.
"""
        )
else:
    st.info(
        f"""
At **{resolution.lower()}** resolution, the active rolling window is
**{window} periods**. Changing temporal resolution and window length changes
how much short-term variability is retained versus smoothed away.
"""
    )


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
viewer sees.
"""
)
