from datetime import date

from chasing_voo.metrics import summarize, to_frame
from chasing_voo.models import Snapshot


def _snap(d, equity, close, flow=0.0):
    return Snapshot(day=date(2026, 1, d), equity=equity, benchmark_close=close, net_flow=flow)


def test_empty_series():
    assert to_frame([]).empty
    s = summarize([])
    assert s.days_tracked == 0
    assert s.win_rate is None


def test_single_day_has_no_comparable_returns():
    s = summarize([_snap(1, 1000, 400)])
    assert s.days_tracked == 1
    assert s.comparable_days == 0
    assert s.beat_today is None
    assert s.port_cum_ret == 0.0  # baseline day


def test_beating_the_index():
    # Day 2: portfolio +10%, benchmark +5% -> beat.
    snaps = [_snap(1, 1000, 400), _snap(2, 1100, 420)]
    df = to_frame(snaps)
    assert abs(df["port_daily_ret"].iloc[1] - 0.10) < 1e-9
    assert abs(df["bench_daily_ret"].iloc[1] - 0.05) < 1e-9
    s = summarize(snaps)
    assert s.beat_today is True
    assert s.win_rate == 1.0


def test_trailing_the_index():
    snaps = [_snap(1, 1000, 400), _snap(2, 1010, 440)]  # +1% vs +10%
    s = summarize(snaps)
    assert s.beat_today is False
    assert s.win_rate == 0.0
    assert s.excess_cum_ret < 0


def test_deposits_do_not_count_as_return():
    # Equity doubles but it's entirely a deposit -> ~0% return, not +100%.
    snaps = [_snap(1, 1000, 400), _snap(2, 2000, 400, flow=1000)]
    df = to_frame(snaps)
    assert abs(df["port_daily_ret"].iloc[1]) < 1e-9
    s = summarize(snaps)
    assert abs(s.port_cum_ret) < 1e-9


def test_win_rate_is_fraction_of_comparable_days():
    # 3 comparable days, win on 2 of them -> 2/3.
    snaps = [
        _snap(1, 1000, 400),
        _snap(2, 1100, 420),   # +10% vs +5% -> win
        _snap(3, 1100, 441),   # 0% vs +5%  -> loss
        _snap(4, 1210, 445),   # +10% vs +0.9% -> win
    ]
    s = summarize(snaps)
    assert s.comparable_days == 3
    assert abs(s.win_rate - 2 / 3) < 1e-9
