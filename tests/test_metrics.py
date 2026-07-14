from datetime import date

from chasing_voo.metrics import build_frame, window_view
from chasing_voo.models import BenchmarkClose, Snapshot


def _snap(d, equity, flow=0.0):
    return Snapshot(day=date(2026, 1, d), equity=equity, net_flow=flow)


def _bench(d, ticker, close):
    return BenchmarkClose(day=date(2026, 1, d), ticker=ticker, close=close)


def test_empty_series():
    assert build_frame([], []).empty
    v = window_view(build_frame([], []), ["VOO"])
    assert v.days == 0
    assert v.benchmarks == {}


def test_single_day_baseline():
    df = build_frame([_snap(1, 1000)], [_bench(1, "VOO", 400)])
    v = window_view(df, ["VOO"])
    assert v.days == 1
    assert v.port_cum_total == 0.0
    assert v.benchmarks["VOO"].beat_today is None
    assert v.benchmarks["VOO"].comparable_days == 0


def test_beating_the_index():
    snaps = [_snap(1, 1000), _snap(2, 1100)]  # +10%
    bench = [_bench(1, "VOO", 400), _bench(2, "VOO", 420)]  # +5%
    v = window_view(build_frame(snaps, bench), ["VOO"])
    bv = v.benchmarks["VOO"]
    assert bv.beat_today is True
    assert bv.win_rate == 1.0
    assert abs(v.port_cum_total - 0.10) < 1e-9
    assert bv.excess > 0


def test_trailing_the_index():
    snaps = [_snap(1, 1000), _snap(2, 1010)]  # +1%
    bench = [_bench(1, "VOO", 400), _bench(2, "VOO", 440)]  # +10%
    bv = window_view(build_frame(snaps, bench), ["VOO"]).benchmarks["VOO"]
    assert bv.beat_today is False
    assert bv.win_rate == 0.0
    assert bv.excess < 0


def test_deposits_do_not_count_as_return():
    snaps = [_snap(1, 1000), _snap(2, 2000, flow=1000)]  # doubled, all deposit
    bench = [_bench(1, "VOO", 400), _bench(2, "VOO", 400)]
    v = window_view(build_frame(snaps, bench), ["VOO"])
    assert abs(v.port_cum_total) < 1e-9


def test_multiple_benchmarks_independent():
    snaps = [_snap(1, 1000), _snap(2, 1050)]  # +5%
    bench = [
        _bench(1, "VOO", 400), _bench(2, "VOO", 408),  # +2% -> beat
        _bench(1, "QQQ", 300), _bench(2, "QQQ", 330),  # +10% -> lose
    ]
    v = window_view(build_frame(snaps, bench), ["VOO", "QQQ"])
    assert v.benchmarks["VOO"].beat_today is True
    assert v.benchmarks["QQQ"].beat_today is False


def test_window_rebases_cumulative():
    # 3 days; a window starting at day 2 should rebase day-2 cumulative to 0.
    snaps = [_snap(1, 1000), _snap(2, 1100), _snap(3, 1210)]  # +10%, +10%
    bench = [_bench(1, "VOO", 400), _bench(2, "VOO", 420), _bench(3, "VOO", 441)]
    df = build_frame(snaps, bench)
    full = window_view(df, ["VOO"])
    assert abs(full.port_cum_total - 0.21) < 1e-9  # 1.1*1.1 - 1
    windowed = window_view(df, ["VOO"], start=date(2026, 1, 2))
    assert abs(windowed.port_cum_total - 0.10) < 1e-9  # only day 3's +10%
    assert windowed.benchmarks["VOO"].comparable_days == 1


def test_win_rate_fraction_of_comparable_days():
    snaps = [_snap(1, 1000), _snap(2, 1100), _snap(3, 1100), _snap(4, 1210)]
    bench = [_bench(d, "VOO", c) for d, c in [(1, 400), (2, 420), (3, 441), (4, 445)]]
    bv = window_view(build_frame(snaps, bench), ["VOO"]).benchmarks["VOO"]
    assert bv.comparable_days == 3
    assert abs(bv.win_rate - 2 / 3) < 1e-9
