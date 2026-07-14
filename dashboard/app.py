"""chasing-VOO — local Streamlit dashboard.

Run with::

    streamlit run dashboard/app.py

Everything is local: it reads the same SQLite database the CLI writes to, and
never sends your data anywhere. Charts compare your portfolio against the
benchmark (VOO by default).
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from chasing_voo.benchmark import close_on, latest_close
from chasing_voo.config import Config
from chasing_voo.metrics import summarize, to_frame
from chasing_voo.models import Snapshot
from chasing_voo.storage import Storage

# --- Palette (colorblind-safe, works on light or dark) -----------------------
PORTFOLIO_COLOR = "#2563eb"  # blue  — you
BENCHMARK_COLOR = "#f59e0b"  # amber — the index
POSITIVE = "#16a34a"
NEGATIVE = "#dc2626"

cfg = Config.load()
BENCH = cfg.benchmark_ticker

st.set_page_config(page_title="chasing-VOO", page_icon="📈", layout="wide")


@st.cache_data(ttl=300)
def _bench_close_cached(ticker: str, day: date):
    close = close_on(ticker, day)
    return close if close is not None else latest_close(ticker)


def load_frame() -> pd.DataFrame:
    with Storage(cfg.db_path) as store:
        snaps = store.all()
    return to_frame(snaps), snaps


df, snaps = load_frame()
summary = summarize(snaps)

st.title("📈 chasing-VOO")
st.caption(f"Are you beating the index? Benchmark: **{BENCH}** · Data: `{cfg.db_path}`")

# --- Sidebar: record a day ---------------------------------------------------
with st.sidebar:
    st.header("Record a day")
    st.write("Read your total portfolio value from your brokerage app and enter it.")
    with st.form("record_form"):
        r_date = st.date_input("Date", value=date.today())
        r_equity = st.number_input("Portfolio value ($)", min_value=0.0, step=100.0, format="%.2f")
        r_flow = st.number_input(
            "Net deposits that day ($)",
            value=0.0,
            step=100.0,
            format="%.2f",
            help="Money you moved IN (or out, negative) that day. Keeps returns honest.",
        )
        submitted = st.form_submit_button("Save")
    if submitted:
        if r_equity <= 0:
            st.error("Enter a portfolio value greater than 0.")
        else:
            try:
                close = _bench_close_cached(BENCH, r_date)
                with Storage(cfg.db_path) as store:
                    store.upsert(
                        Snapshot(
                            day=r_date,
                            equity=float(r_equity),
                            benchmark_close=float(close),
                            net_flow=float(r_flow),
                        )
                    )
                st.success(f"Saved {r_date}. {BENCH} close ${close:,.2f}.")
                st.cache_data.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"Could not save: {exc}")

    st.divider()
    st.caption(
        "Prefer automation? See the README for the optional Robinhood provider "
        "or the official Robinhood MCP path."
    )

# --- Empty state -------------------------------------------------------------
if summary.days_tracked == 0:
    st.info("No data yet. Use **Record a day** in the sidebar to add your first entry.")
    st.stop()


def pct(v):
    return "n/a" if v is None else f"{v * 100:+.2f}%"


# --- Headline metrics --------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio value", f"${summary.latest_equity:,.0f}" if summary.latest_equity else "n/a")
c2.metric(
    "Cumulative return",
    pct(summary.port_cum_ret),
    delta=f"{pct(summary.excess_cum_ret)} vs {BENCH}",
)
c3.metric(f"{BENCH} cumulative", pct(summary.bench_cum_ret))
c4.metric(
    "Win rate",
    pct(summary.win_rate),
    help="Share of comparable days your portfolio out-returned the index.",
)

if summary.beat_today is not None:
    verdict = "beat the index today ✅" if summary.beat_today else "trailed the index today ❌"
    ahead = (summary.excess_cum_ret or 0) >= 0
    overall = "ahead overall 🎉" if ahead else "behind overall"
    st.subheader(
        f"You {verdict} — you ({pct(summary.port_daily_ret)}) "
        f"vs {BENCH} ({pct(summary.bench_daily_ret)}). You're {overall}."
    )

# --- Cumulative return chart -------------------------------------------------
st.markdown("### Growth of returns since day one")
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=(df["port_cum_ret"] * 100),
        name="You",
        line=dict(color=PORTFOLIO_COLOR, width=2.5),
        hovertemplate="%{x}<br>You: %{y:.2f}%<extra></extra>",
    )
)
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=(df["bench_cum_ret"] * 100),
        name=BENCH,
        line=dict(color=BENCHMARK_COLOR, width=2.5),
        hovertemplate="%{x}<br>" + BENCH + ": %{y:.2f}%<extra></extra>",
    )
)
fig.update_layout(
    height=380,
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title="Cumulative return (%)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# --- Excess return + win rate ------------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("#### Lead / lag vs index")
    excess = df["excess_cum_ret"] * 100
    area = go.Figure()
    area.add_trace(
        go.Scatter(
            x=df.index,
            y=excess,
            fill="tozeroy",
            line=dict(color=PORTFOLIO_COLOR, width=1.5),
            name="Excess",
            hovertemplate="%{x}<br>Lead: %{y:.2f}%<extra></extra>",
        )
    )
    area.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title=f"You minus {BENCH} (%)",
        showlegend=False,
    )
    st.plotly_chart(area, use_container_width=True)

with col_b:
    st.markdown("#### Running win rate")
    wr = go.Figure()
    wr.add_trace(
        go.Scatter(
            x=df.index,
            y=df["beat_cumrate"] * 100,
            line=dict(color=POSITIVE, width=2),
            hovertemplate="%{x}<br>Win rate: %{y:.1f}%<extra></extra>",
            name="Win rate",
        )
    )
    wr.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")
    wr.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="Win rate (%)",
        yaxis_range=[0, 100],
        showlegend=False,
    )
    st.plotly_chart(wr, use_container_width=True)

# --- Data table --------------------------------------------------------------
with st.expander("Show data table"):
    display = df.copy()
    for col in ["port_daily_ret", "bench_daily_ret", "port_cum_ret", "bench_cum_ret", "excess_cum_ret", "beat_cumrate"]:
        display[col] = (display[col] * 100).round(2)
    display["beat"] = display["beat"].map({True: "✅", False: "❌"})
    display = display.rename(
        columns={
            "equity": "Equity ($)",
            "benchmark_close": f"{BENCH} close ($)",
            "net_flow": "Net flow ($)",
            "port_daily_ret": "You daily %",
            "bench_daily_ret": f"{BENCH} daily %",
            "beat": "Beat?",
            "beat_cumrate": "Win rate %",
            "port_cum_ret": "You cum %",
            "bench_cum_ret": f"{BENCH} cum %",
            "excess_cum_ret": "Lead %",
        }
    )
    st.dataframe(display, use_container_width=True)
