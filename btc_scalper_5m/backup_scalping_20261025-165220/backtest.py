import argparse
import ccxt
import pandas as pd
from config import Config
from strategy import add_indicators

def fetch_history(exchange_id, symbol, timeframe, days):
    ex = getattr(ccxt, exchange_id)({"enableRateLimit": True})
    ex.load_markets()
    since = ex.milliseconds() - days * 24 * 60 * 60 * 1000
    all_rows = []
    while since < ex.milliseconds():
        batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not batch:
            break
        all_rows.extend(batch)
        next_since = batch[-1][0] + 1
        if next_since <= since:
            break
        since = next_since
        if len(batch) < 2:
            break
    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).astype(str)
    return df

def run_backtest(df, cfg):
    d = add_indicators(df).reset_index(drop=True)
    cash = cfg.initial_capital
    qty = 0.0
    entry = stop = target = entry_fee = 0.0
    trades = []
    equity_curve = []
    day = None
    day_start = cash
    daily_trades = 0

    for i in range(220, len(d)):
        r = d.iloc[i]
        ts, close, low, high = str(r.timestamp), float(r.close), float(r.low), float(r.high)
        this_day = ts[:10]
        if this_day != day:
            day, day_start, daily_trades = this_day, cash + qty * close, 0

        if qty > 0:
            exit_price, reason = None, None
            if low <= stop:
                exit_price, reason = stop * (1 - cfg.slippage_rate), "stop"
            elif high >= target:
                exit_price, reason = target * (1 - cfg.slippage_rate), "target"
            elif bool(r.exit_signal):
                exit_price, reason = close * (1 - cfg.slippage_rate), "ema_exit"
            if exit_price is not None:
                fee = exit_price * qty * cfg.fee_rate
                pnl = (exit_price - entry) * qty - fee - entry_fee
                cash += exit_price * qty - fee
                trades.append({"timestamp": ts, "entry": entry, "exit": exit_price,
                               "qty": qty, "pnl_net": pnl, "reason": reason})
                qty = 0.0
                daily_trades += 1

        if qty == 0 and bool(r.entry_signal) and daily_trades < cfg.max_trades_per_day:
            equity = cash
            if equity > day_start * (1 - cfg.max_daily_loss) and float(r.atr14) > 0:
                price = close * (1 + cfg.slippage_rate)
                stop_candidate = price - cfg.atr_stop_multiplier * float(r.atr14)
                risk_budget = equity * cfg.risk_per_trade
                q_risk = risk_budget / max(price - stop_candidate, 1e-12)
                q_cash = (cash * cfg.max_position_fraction) / (price * (1 + cfg.fee_rate))
                q = min(q_risk, q_cash)
                if q * price >= 10 and q > 0:
                    fee = q * price * cfg.fee_rate
                    if q * price + fee <= cash:
                        qty, entry, stop, target, entry_fee = (
                            q, price, stop_candidate,
                            price + cfg.take_profit_r_multiple * (price - stop_candidate), fee
                        )
                        cash -= q * price + fee
        equity_curve.append(cash + qty * close)

    # Mark any final open position to market for reporting; do not imply it was closed.
    final_equity = cash + qty * float(d.iloc[-1].close)
    eq = pd.Series(equity_curve, dtype=float)
    peak = eq.cummax()
    max_dd = float(((eq / peak) - 1).min() * 100) if len(eq) else 0.0
    total_return = (final_equity / cfg.initial_capital - 1) * 100
    wins = sum(1 for t in trades if t["pnl_net"] > 0)
    print(f"Velas analizadas: {max(0, len(d)-220)}")
    print(f"Operaciones cerradas: {len(trades)} | ganadoras: {wins}")
    print(f"Capital inicial: {cfg.initial_capital:.2f} USDT")
    print(f"Equity final (posición abierta valorada a mercado): {final_equity:.2f} USDT")
    print(f"Rentabilidad neta simulada: {total_return:.2f}%")
    print(f"Drawdown máximo aproximado: {max_dd:.2f}%")
    pd.DataFrame(trades).to_csv("backtest_trades.csv", index=False)
    pd.DataFrame({"equity": equity_curve}).to_csv("backtest_equity.csv", index=False)
    print("Resultados guardados en backtest_trades.csv y backtest_equity.csv")
    print("Nota: el backtest no modela latencia real, profundidad del libro ni ejecución exacta.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--symbol", default="BTC/USDT")
    args = parser.parse_args()
    cfg = Config()
    # Don't call cfg.validate here because backtest is an offline/historical mode.
    if args.days < 10:
        raise SystemExit("--days debe ser al menos 10.")
    df = fetch_history(args.exchange, args.symbol, "5m", args.days)
    if len(df) < 300:
        raise SystemExit("No se han descargado suficientes velas; revisa el exchange/par.")
    run_backtest(df, cfg)

if __name__ == "__main__":
    main()
