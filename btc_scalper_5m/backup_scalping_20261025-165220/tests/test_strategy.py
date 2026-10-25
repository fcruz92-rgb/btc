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
