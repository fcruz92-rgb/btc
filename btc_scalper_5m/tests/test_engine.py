from engine import PaperEngine, Position
from config import Config


def test_position_exits_after_max_hold_candles(tmp_path):
    cfg = Config()
    log_path = tmp_path / "trades.csv"
    state_path = tmp_path / "state.json"
    engine = PaperEngine(cfg, log_path=log_path, state_path=state_path)
    engine.cash = 0.0
    engine.position = Position(
        qty=0.001,
        entry_price=100.0,
        stop_price=90.0,
        target_price=120.0,
        entry_fee=0.01,
        entry_time="2026-01-01T00:00:00+00:00",
        risk_usdt=0.5,
        bars_held=cfg.max_hold_candles - 1,
    )
    row = {
        "timestamp": "2026-01-01T00:20:00+00:00",
        "close": 105.0,
        "low": 103.0,
        "high": 106.0,
        "atr14": 1.0,
        "exit_signal": False,
        "entry_signal": False,
    }
    result = engine.on_candle(row)
    assert result is not None
    assert "time_exit" in result
    assert engine.position is None


def test_stop_has_priority_if_stop_and_target_touch_same_candle(tmp_path):
    cfg = Config()
    engine = PaperEngine(
        cfg,
        log_path=tmp_path / "trades.csv",
        state_path=tmp_path / "state.json",
    )
    engine.cash = 0.0
    engine.position = Position(
        qty=0.001,
        entry_price=100.0,
        stop_price=95.0,
        target_price=105.0,
        entry_fee=0.01,
        entry_time="2026-01-01T00:00:00+00:00",
        risk_usdt=0.5,
    )
    row = {
        "timestamp": "2026-01-01T00:05:00+00:00",
        "close": 100.0,
        "low": 94.0,
        "high": 106.0,
        "atr14": 1.0,
        "exit_signal": False,
        "entry_signal": False,
    }
    result = engine.on_candle(row)
    assert result is not None
    assert "stop_loss" in result


def test_skips_entry_when_target_is_too_small_vs_costs(tmp_path):
    cfg = Config()
    engine = PaperEngine(
        cfg,
        log_path=tmp_path / "trades.csv",
        state_path=tmp_path / "state.json",
    )
    starting_cash = engine.cash
    row = {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "close": 100.0,
        "low": 99.9,
        "high": 100.1,
        "atr14": 0.1,
        "exit_signal": False,
        "entry_signal": True,
    }
    result = engine.on_candle(row)
    assert result is not None
    assert "insuficiente" in result
    assert engine.position is None
    assert engine.cash == starting_cash
