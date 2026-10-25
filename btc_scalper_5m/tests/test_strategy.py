import pandas as pd
from strategy import add_indicators

def sample_df(n=350):
    ts = pd.date_range("2025-01-01", periods=n, freq="5min", tz="UTC").astype(str)
    close = [100 + i * 0.1 for i in range(n)]
    return pd.DataFrame({
        "timestamp": ts,
        "open": close,
        "high": [x + 0.5 for x in close],
        "low": [x - 0.5 for x in close],
        "close": close,
        "volume": [1.0] * n
    })

def test_indicators_created():
    out = add_indicators(sample_df())
    for col in ["ema9", "ema21", "ema200", "rsi14", "atr14", "entry_signal", "exit_signal"]:
        assert col in out.columns

def test_sorted_and_unique_timestamps():
    df = sample_df()
    df = pd.concat([df.iloc[::-1], df.iloc[[10]]], ignore_index=True)
    out = add_indicators(df)
    assert out["timestamp"].is_monotonic_increasing
    assert out["timestamp"].is_unique


def test_scalping_entry_is_a_setup_transition_not_only_an_rsi_cross():
    import math

    n = 500
    close = [100 + i * 0.03 + 1.5 * math.sin(i / 3.7) for i in range(n)]
    ts = pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC").astype(str)
    df = pd.DataFrame({
        "timestamp": ts,
        "open": close,
        "high": [x + 0.35 for x in close],
        "low": [x - 0.35 for x in close],
        "close": close,
        "volume": [1.0] * n,
    })
    out = add_indicators(df)
    assert out["entry_signal"].any()
    eligible = (
        (out["close"] > out["ema200"]) &
        (out["close"] > out["ema9"]) &
        (out["ema9"] > out["ema21"]) &
        out["rsi14"].between(50, 68) &
        out["atr14"].notna()
    )
    assert (out.loc[out["entry_signal"], "close"] > out.loc[out["entry_signal"], "ema200"]).all()
    assert eligible[out["entry_signal"]].all()
    assert not (out["entry_signal"] & out["entry_signal"].shift(1, fill_value=False)).any()
