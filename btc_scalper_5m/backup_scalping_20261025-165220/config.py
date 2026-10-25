import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Config:
    exchange_id: str = os.getenv("EXCHANGE_ID", "binance")
    symbol: str = os.getenv("SYMBOL", "BTC/USDT")
    timeframe: str = os.getenv("TIMEFRAME", "5m")
    mode: str = os.getenv("MODE", "paper").lower()
    initial_capital: float = float(os.getenv("INITIAL_CAPITAL_USDT", "55"))
    risk_per_trade: float = float(os.getenv("RISK_PER_TRADE", "0.005"))
    max_daily_loss: float = float(os.getenv("MAX_DAILY_LOSS", "0.02"))
    max_position_fraction: float = float(os.getenv("MAX_POSITION_FRACTION", "0.80"))
    fee_rate: float = float(os.getenv("FEE_RATE", "0.001"))
    slippage_rate: float = float(os.getenv("SLIPPAGE_RATE", "0.0005"))
    atr_stop_multiplier: float = float(os.getenv("ATR_STOP_MULTIPLIER", "1.5"))
    take_profit_r_multiple: float = float(os.getenv("TAKE_PROFIT_R_MULTIPLE", "2.0"))
    poll_seconds: int = int(os.getenv("POLL_SECONDS", "15"))
    cooldown_candles: int = int(os.getenv("COOLDOWN_CANDLES", "1"))
    max_trades_per_day: int = int(os.getenv("MAX_TRADES_PER_DAY", "8"))
    live_trading: bool = os.getenv("LIVE_TRADING", "false").lower() == "true"
    api_key: str = os.getenv("API_KEY", "")
    api_secret: str = os.getenv("API_SECRET", "")

    def validate(self):
        if self.mode not in {"paper", "backtest", "testnet", "live"}:
            raise ValueError("MODE debe ser paper, backtest, testnet o live.")
        if self.initial_capital <= 0:
            raise ValueError("INITIAL_CAPITAL_USDT debe ser positivo.")
        if not 0 < self.risk_per_trade <= 0.01:
            raise ValueError("RISK_PER_TRADE debe estar entre 0 y 1%.")
        if not 0 < self.max_daily_loss <= 0.05:
            raise ValueError("MAX_DAILY_LOSS debe estar entre 0 y 5%.")
        if not 0 < self.max_position_fraction <= 1:
            raise ValueError("MAX_POSITION_FRACTION debe estar entre 0 y 1.")
        if self.fee_rate < 0 or self.slippage_rate < 0:
            raise ValueError("Comisiones y slippage no pueden ser negativos.")
        # Real trading intentionally blocked in this starter project:
        # local stops are not protective if the PC/network is down.
        if self.mode == "live" or self.live_trading:
            raise RuntimeError(
                "Trading REAL bloqueado en esta versión. El stop se controla localmente "
                "y no protege si el PC/Internet falla. Primero valida paper/backtest y "
                "añade órdenes protectoras nativas del exchange, reconciliación de órdenes "
                "y pruebas específicas de la entidad/API que uses."
            )
        if self.mode == "testnet":
            raise RuntimeError(
                "MODE=testnet no está habilitado en este starter: los parámetros de testnet "
                "varían por exchange. Usa MODE=paper hasta configurar y verificar el sandbox "
                "oficial de tu exchange."
            )
