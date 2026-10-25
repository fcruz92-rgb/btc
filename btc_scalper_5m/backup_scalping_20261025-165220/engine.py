from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import csv
import json
from pathlib import Path

@dataclass
class Position:
    qty: float
    entry_price: float
    stop_price: float
    target_price: float
    entry_fee: float
    entry_time: str
    risk_usdt: float

class PaperEngine:
    def __init__(self, cfg, log_path="trades.csv", state_path="state.json"):
        self.cfg = cfg
        self.cash = cfg.initial_capital
        self.position = None
        self.day = None
        self.day_start_equity = cfg.initial_capital
        self.daily_trades = 0
        self.cooldown = 0
        self.log_path = Path(log_path)
        self.state_path = Path(state_path)
        if not self.log_path.exists():
            with self.log_path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "time", "side", "price", "qty", "fee", "cash_after",
                    "equity_after", "pnl_net", "reason"
                ])
        self._load_state()

    def equity(self, mark_price):
        return self.cash if self.position is None else self.cash + self.position.qty * mark_price

    def _roll_day(self, timestamp, mark_price):
        day = timestamp[:10]
        if day != self.day:
            self.day = day
            self.day_start_equity = self.equity(mark_price)
            self.daily_trades = 0

    def _daily_loss_limit_hit(self, mark_price):
        eq = self.equity(mark_price)
        return eq <= self.day_start_equity * (1 - self.cfg.max_daily_loss)

    def _log(self, side, price, qty, fee, pnl, reason):
        now = datetime.now(timezone.utc).isoformat()
        eq = self.equity(price)
        with self.log_path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                now, side, f"{price:.8f}", f"{qty:.8f}", f"{fee:.8f}",
                f"{self.cash:.8f}", f"{eq:.8f}", f"{pnl:.8f}", reason
            ])

    def _save_state(self):
        data = {
            "cash": self.cash,
            "position": asdict(self.position) if self.position else None,
            "day": self.day,
            "day_start_equity": self.day_start_equity,
            "daily_trades": self.daily_trades,
            "cooldown": self.cooldown
        }
        self.state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_state(self):
        # Paper state persists between restarts. Delete state.json to reset a paper run.
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.cash = float(data.get("cash", self.cash))
            p = data.get("position")
            self.position = Position(**p) if p else None
            self.day = data.get("day")
            self.day_start_equity = float(data.get("day_start_equity", self.cash))
            self.daily_trades = int(data.get("daily_trades", 0))
            self.cooldown = int(data.get("cooldown", 0))
        except Exception as exc:
            raise RuntimeError("state.json no se pudo leer; no lo borres sin revisar trades.csv.") from exc

    def on_candle(self, row):
        ts = str(row["timestamp"])
        close = float(row["close"])
        low = float(row["low"])
        high = float(row["high"])
        atr = float(row["atr14"]) if row.get("atr14") == row.get("atr14") else 0.0
        self._roll_day(ts, close)

        # Conservative intrabar assumption: if stop and target both touch, assume stop first.
        if self.position:
            p = self.position
            exit_price, reason = None, None
            if low <= p.stop_price:
                exit_price, reason = p.stop_price * (1 - self.cfg.slippage_rate), "stop_loss"
            elif high >= p.target_price:
                exit_price, reason = p.target_price * (1 - self.cfg.slippage_rate), "take_profit"
            elif bool(row["exit_signal"]):
                exit_price, reason = close * (1 - self.cfg.slippage_rate), "ema_exit"
            if exit_price is not None:
                qty = p.qty
                gross = (exit_price - p.entry_price) * qty
                fee = exit_price * qty * self.cfg.fee_rate
                self.cash += exit_price * qty - fee
                pnl_net = gross - fee - p.entry_fee
                self.position = None
                self.daily_trades += 1
                self.cooldown = self.cfg.cooldown_candles
                self._log("SELL", exit_price, qty, fee, pnl_net, reason)
                self._save_state()
                return f"VENTA {reason} | precio={exit_price:.2f} | PnL neto aprox={pnl_net:.4f} USDT"

        if self.cooldown > 0:
            self.cooldown -= 1
            self._save_state()
            return None
        if self.position or not bool(row["entry_signal"]):
            self._save_state()
            return None
        if self.daily_trades >= self.cfg.max_trades_per_day:
            return None
        if self._daily_loss_limit_hit(close):
            return "LÍMITE DIARIO alcanzado: no se abren nuevas posiciones."

        if atr <= 0:
            return None
        entry = close * (1 + self.cfg.slippage_rate)
        stop = entry - self.cfg.atr_stop_multiplier * atr
        risk_per_btc = entry - stop
        if risk_per_btc <= 0:
            return None

        equity = self.equity(close)
        risk_budget = equity * self.cfg.risk_per_trade
        qty_by_risk = risk_budget / risk_per_btc
        qty_by_capital = (self.cash * self.cfg.max_position_fraction) / (
            entry * (1 + self.cfg.fee_rate)
        )
        qty = min(qty_by_risk, qty_by_capital)
        notional = qty * entry
        # Do not pretend an order is viable if tiny size or fee burden is unreasonable.
        if qty <= 0 or notional < 10:
            return "Sin operación: tamaño inferior a 10 USDT (umbral configurable; comprueba el exchange)."
        fee = notional * self.cfg.fee_rate
        if notional + fee > self.cash:
            return None

        target = entry + self.cfg.take_profit_r_multiple * risk_per_btc
        self.cash -= notional + fee
        self.position = Position(
            qty=qty, entry_price=entry, stop_price=stop, target_price=target,
            entry_fee=fee, entry_time=ts, risk_usdt=risk_budget
        )
        self._log("BUY", entry, qty, fee, 0.0, "entry_signal")
        self._save_state()
        return (f"COMPRA paper | precio={entry:.2f} | qty={qty:.8f} BTC | "
                f"stop={stop:.2f} | objetivo={target:.2f} | fee={fee:.4f} USDT")

    def close_at_market(self, price, reason="manual_close"):
        if not self.position:
            return None
        p = self.position
        exit_price = price * (1 - self.cfg.slippage_rate)
        fee = exit_price * p.qty * self.cfg.fee_rate
        gross = (exit_price - p.entry_price) * p.qty
        self.cash += exit_price * p.qty - fee
        pnl = gross - fee - p.entry_fee
        self.position = None
        self._log("SELL", exit_price, p.qty, fee, pnl, reason)
        self._save_state()
        return pnl
