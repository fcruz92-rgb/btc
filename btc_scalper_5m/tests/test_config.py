from dataclasses import replace
import pytest
from config import Config

def test_defaults_are_safe():
    cfg = Config()
    assert cfg.mode == "paper"
    cfg.validate()

def test_live_mode_is_blocked():
    cfg = replace(Config(), mode="live", live_trading=False)
    with pytest.raises(RuntimeError, match="Trading REAL bloqueado"):
        cfg.validate()
