import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas OHLCV: {sorted(missing)}")
    out = df.copy().sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    close = out["close"].astype(float)
    high = out["high"].astype(float)
    low = out["low"].astype(float)

    out["ema9"] = close.ewm(span=9, adjust=False).mean()
    out["ema21"] = close.ewm(span=21, adjust=False).mean()
    out["ema200"] = close.ewm(span=200, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out["rsi14"] = 100 - (100 / (1 + rs))
    out.loc[(avg_loss == 0) & (avg_gain > 0), "rsi14"] = 100

    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    out["atr14"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()

    # Scalping entry: established uptrend + short-term momentum confirmation.
    # RSI is bounded to avoid buying an already overextended candle.
    setup = (
        (out["close"] > out["ema200"]) &
        (out["close"] > out["ema9"]) &
        (out["ema9"] > out["ema21"]) &
        (out["rsi14"] >= 50) &
        (out["rsi14"] <= 68) &
        out["atr14"].notna()
    )
    # One entry signal when the complete setup changes from false to true.
    out["entry_signal"] = setup & ~setup.shift(1, fill_value=False)
    # Faster exit: trend crossover, or a confirmed loss of short-term momentum.
    out["exit_signal"] = (
        (out["ema9"] < out["ema21"]) |
        ((out["close"] < out["ema9"]) & (out["rsi14"] < 50))
    )
    return out
