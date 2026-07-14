"""chasing-VOO — local Streamlit dashboard (read-only).

Run with::

    streamlit run dashboard/app.py

Reads the same SQLite database the automated updater writes to and never sends
your data anywhere. Compares your portfolio against one or more indices
(S&P 500 / Dow / Nasdaq) over a selectable date range.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from chasing_voo.config import Config
from chasing_voo.metrics import build_frame, window_view
from chasing_voo.storage import Storage

# --- Validated palette (dataviz skill) ---------------------------------------
# Categorical slots 1–4, light surface. Contrast/CVD relief = legend + direct
# labels + table view (all present below).
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
GOOD = "#006300"
BAD = "#c0362c"
PORTFOLIO = "#2a78d6"  # blue — You
SERIES_COLORS = {"VOO": "#1baf7a", "DIA": "#eda100", "QQQ": "#008300"}  # aqua/yellow/green

cfg = Config.load()
st.set_page_config(page_title="chasing-VOO", page_icon="📈", layout="wide")

# --- Global styling ----------------------------------------------------------
st.markdown(
    """
    <style>
      .stApp { background: #f9f9f7; }
      .block-container { padding-top: 2.2rem; max-width: 1180px; }
      h1, h2, h3, h4 { font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
        letter-spacing: -0.01em; color: #0b0b0b; }
      .cv-title { font-size: 1.9rem; font-weight: 700; margin-bottom: .1rem; }
      .cv-sub { color: #52514e; font-size: .95rem; margin-bottom: 1.4rem; }
      .cv-card { background: #fcfcfb; border: 1px solid rgba(11,11,11,.08);
        border-radius: 14px; padding: 16px 18px; height: 100%; }
      .cv-klabel { color: #898781; font-size: .78rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: .04em; }
      .cv-kval { color: #0b0b0b; font-size: 1.75rem; font-weight: 700;
        font-variant-numeric: tabular-nums; margin-top: 2px; line-height: 1.1; }
      .cv-kdelta { font-size: .85rem; font-weight: 600; margin-top: 3px; }
      .cv-good { color: #006300; } .cv-bad { color: #c0362c; }
      .cv-verdict { font-size: 1.15rem; font-weight: 600; color: #0b0b0b;
        background: #fcfcfb; border: 1px solid rgba(11,11,11,.08); border-left: 4px solid #2a78d6;
        border-radius: 10px; padding: 12px 16px; margin: .2rem 0 1.4rem; }
      .cv-chip { display:inline-block; width:10px; height:10px; border-radius:3px;
        margin-right:7px; vertical-align:middle; }
      [data-testid="stSidebar"] { background: #fcfcfb; border-right: 1px solid rgba(11,11,11,.06); }
    </style>
    """,
    unsafe_allow_html=True,
)


def load():
    with Storage(cfg.db_path) as store:
        return build_frame(store.snapshots(), store.benchmark_closes())


df = load()


def pct(v, plus=True):
    if v is None or pd.isna(v):
        return "—"
    return f"{v * 100:{'+' if plus else ''}.2f}%"


def klass(v):
    return "cv-good" if (v is not None and v >= 0) else "cv-bad"


# --- Sidebar: controls -------------------------------------------------------
with st.sidebar:
    st.markdown("### Compare against")
    available = cfg.tickers
    labels = {t: cfg.label(t) for t in available}
    selected = st.multiselect(
        "Indices",
        options=available,
        default=available,
        format_func=lambda t: labels[t],
        label_visibility="collapsed",
    )

    st.markdown("### Date range")
    range_choice = st.radio(
        "Range",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time", "Custom"],
        index=3,
        label_visibility="collapsed",
    )

    custom_start = custom_end = None
    if not df.empty:
        data_min, data_max = df.index.min(), df.index.max()
        if range_choice == "Custom":
            picked = st.date_input(
                "Custom range",
                value=(data_min, data_max),
                min_value=data_min,
                max_value=data_max,
            )
            if isinstance(picked, tuple) and len(picked) == 2:
                custom_start, custom_end = picked

    st.divider()
    st.markdown("#### Automation")
    st.caption("Recorded automatically each weekday after close — no manual entry.")
    if not df.empty:
        st.caption(f"Days tracked: **{len(df)}**  ·  Last: **{df.index.max()}**")
    st.caption(f"Source: `{cfg.provider}`")

# --- Resolve window ----------------------------------------------------------
start = end = None
if not df.empty:
    data_max = df.index.max()
    if range_choice == "Last 7 days":
        start = data_max - timedelta(days=7)
    elif range_choice == "Last 30 days":
        start = data_max - timedelta(days=30)
    elif range_choice == "Last 90 days":
        start = data_max - timedelta(days=90)
    elif range_choice == "Custom":
        start, end = custom_start, custom_end

view = window_view(df, selected, start=start, end=end)

# --- Header ------------------------------------------------------------------
st.markdown('<div class="cv-title">📈 chasing-VOO</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="cv-sub">Are you beating the market? · Range: <b>{range_choice}</b> · '
    f'{view.days} day(s)</div>',
    unsafe_allow_html=True,
)

if view.days == 0:
    st.info("No data yet. The automated updater populates this after its first run.")
    st.stop()

# --- Headline verdict --------------------------------------------------------
beaten = [cfg.label(t) for t in selected
          if view.benchmarks.get(t) and view.benchmarks[t].beat_today is True]
trailed = [cfg.label(t) for t in selected
           if view.benchmarks.get(t) and view.benchmarks[t].beat_today is False]
if beaten or trailed:
    parts = []
    if beaten:
        parts.append(f"beat <b>{', '.join(beaten)}</b>")
    if trailed:
        parts.append(f"trailed <b>{', '.join(trailed)}</b>")
    st.markdown(
        f'<div class="cv-verdict">Today you '
        f'({pct(view.port_daily_today)}) — ' + " · ".join(parts) + "</div>",
        unsafe_allow_html=True,
    )

# --- KPI cards ---------------------------------------------------------------
cols = st.columns(2 + len(selected))
with cols[0]:
    st.markdown(
        f'<div class="cv-card"><div class="cv-klabel">Portfolio value</div>'
        f'<div class="cv-kval">${view.latest_equity:,.0f}</div>'
        f'<div class="cv-kdelta cv-good">&nbsp;</div></div>',
        unsafe_allow_html=True,
    )
with cols[1]:
    st.markdown(
        f'<div class="cv-card"><div class="cv-klabel">You · {range_choice.lower()}</div>'
        f'<div class="cv-kval">{pct(view.port_cum_total)}</div>'
        f'<div class="cv-kdelta {klass(view.port_daily_today)}">today {pct(view.port_daily_today)}</div></div>',
        unsafe_allow_html=True,
    )
for i, t in enumerate(selected):
    bv = view.benchmarks.get(t)
    if not bv:
        continue
    with cols[2 + i]:
        chip = SERIES_COLORS.get(t, MUTED)
        st.markdown(
            f'<div class="cv-card">'
            f'<div class="cv-klabel"><span class="cv-chip" style="background:{chip}"></span>vs {cfg.label(t)}</div>'
            f'<div class="cv-kval {klass(bv.excess)}">{pct(bv.excess)}</div>'
            f'<div class="cv-kdelta {MUTED and ""}" style="color:#898781">win rate {pct(bv.win_rate, plus=False)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)


def style_axes(fig, ytitle):
    fig.update_layout(
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, sans-serif", color=INK_2, size=12),
        margin=dict(l=8, r=8, t=10, b=8), height=380, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=INK)),
    )
    fig.update_yaxes(title=dict(text=ytitle, font=dict(color=MUTED, size=11)),
                     gridcolor=GRID, zerolinecolor=AXIS, tickfont=dict(color=MUTED))
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", zerolinecolor=AXIS,
                     linecolor=AXIS, tickfont=dict(color=MUTED))
    return fig


# --- Cumulative return chart -------------------------------------------------
st.markdown("#### Growth of returns over the range")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=view.index, y=view.port_cum * 100, name="You",
    line=dict(color=PORTFOLIO, width=3),
    hovertemplate="You: %{y:.2f}%<extra></extra>",
))
for t in selected:
    bv = view.benchmarks.get(t)
    if not bv:
        continue
    fig.add_trace(go.Scatter(
        x=view.index, y=bv.cum * 100, name=cfg.label(t),
        line=dict(color=SERIES_COLORS.get(t, MUTED), width=2),
        hovertemplate=f"{cfg.label(t)}: %{{y:.2f}}%<extra></extra>",
    ))
# Direct end-labels (secondary encoding for the CVD/contrast relief rule).
_last = view.index[-1]
_ends = [("You", float(view.port_cum.iloc[-1] * 100), PORTFOLIO)]
for t in selected:
    bv = view.benchmarks.get(t)
    if bv is not None and len(bv.cum):
        _ends.append((cfg.label(t), float(bv.cum.iloc[-1] * 100), SERIES_COLORS.get(t, MUTED)))
for name, yv, color in _ends:
    fig.add_annotation(x=_last, y=yv, text=f" {name}", showarrow=False,
                       xanchor="left", font=dict(color=color, size=12, family="system-ui"))
fig.update_xaxes(range=[view.index[0], _last + (pd.Timedelta(days=max(1, view.days // 6)))])
style_axes(fig, "Cumulative return (%)")
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# --- Today's return: You vs each index ---------------------------------------
if view.port_daily_today is not None:
    st.markdown("#### Today — you vs each index")
    names = ["You"] + [cfg.label(t) for t in selected if view.benchmarks.get(t)]
    vals = [view.port_daily_today * 100] + [
        (view.benchmarks[t].daily_today or 0) * 100 for t in selected if view.benchmarks.get(t)
    ]
    colors = [PORTFOLIO] + [SERIES_COLORS.get(t, MUTED) for t in selected if view.benchmarks.get(t)]
    bar = go.Figure(go.Bar(
        x=names, y=vals, marker_color=colors,
        text=[f"{v:+.2f}%" for v in vals], textposition="outside",
        textfont=dict(color=INK), hoverinfo="skip",
    ))
    bar.update_layout(
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=300,
        margin=dict(l=8, r=8, t=24, b=8),
        font=dict(family="system-ui, sans-serif", color=INK_2),
    )
    bar.update_yaxes(title=dict(text="Daily return (%)", font=dict(color=MUTED, size=11)),
                     gridcolor=GRID, zerolinecolor=AXIS, tickfont=dict(color=MUTED))
    bar.update_xaxes(tickfont=dict(color=INK))
    st.plotly_chart(bar, use_container_width=True, config={"displayModeBar": False})

# --- Data table (table view = accessibility fallback) ------------------------
with st.expander("Show data table"):
    show = pd.DataFrame(index=view.index)
    show["Equity ($)"] = df.loc[view.index, "equity"].round(2)
    show["You cum %"] = (view.port_cum * 100).round(2)
    for t in selected:
        bv = view.benchmarks.get(t)
        if bv is not None:
            show[f"{cfg.label(t)} cum %"] = (bv.cum * 100).round(2)
    st.dataframe(show, use_container_width=True)

st.caption("Personal tracking, not financial advice. Index proxies: VOO≈S&P 500, "
           "DIA≈Dow, QQQ≈Nasdaq-100.")
