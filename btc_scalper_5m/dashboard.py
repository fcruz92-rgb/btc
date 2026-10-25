from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import logging

import ccxt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from config import Config
from strategy import add_indicators

ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "bot.log"
TRADES_PATH = ROOT / "trades.csv"
STATE_PATH = ROOT / "state.json"

st.set_page_config(page_title="BTC Scalper | Live Monitor", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")
# La interfaz refresca con frecuencia, pero las consultas al exchange se cachean para evitar rate limits.
st_autorefresh(interval=60_000, key="btc_scalper_refresh")

cfg = Config()
quote_currency = cfg.symbol.split("/")[-1] if "/" in cfg.symbol else "USD"

st.markdown(
    """
    <style>
      :root {
        color-scheme: dark;
        --neon-cyan: #22e6ff;
        --neon-blue: #218cff;
        --neon-violet: #9a72ff;
        --neon-green: #2ff5a6;
        --neon-pink: #ff4fd8;
        --neon-bg: #010812;
        --panel: rgba(4, 18, 32, .92);
        --muted: #69849c;
      }
      html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: #010812; color: #eaf3ff;
      }
      [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(circle at 78% 3%, rgba(24,109,255,.17), transparent 27%),
          radial-gradient(circle at 15% 85%, rgba(0,224,255,.08), transparent 30%),
          linear-gradient(145deg, #01060d 0%, #03111f 48%, #01070f 100%);
      }
      [data-testid="stAppViewContainer"]::before {
        content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .23;
        background-image: linear-gradient(rgba(38,210,255,.04) 1px, transparent 1px), linear-gradient(90deg, rgba(38,210,255,.04) 1px, transparent 1px);
        background-size: 44px 44px; mask-image: linear-gradient(to bottom, black, transparent 90%);
      }
      [data-testid="stHeader"] { background: rgba(1,8,18,.78); }
      .block-container { padding-top: 1.35rem; padding-bottom: 2.5rem; max-width: 1700px; position: relative; z-index: 1; }
      h1, h2, h3 { color: #f3f8ff !important; letter-spacing: -.025em; }
      h1 { font-size: 2rem !important; font-weight: 800 !important; text-shadow: 0 0 22px rgba(34,230,255,.12); }
      h2 { font-size: 1.25rem !important; font-weight: 750 !important; margin-top: .45rem !important; }
      h3 { font-size: 1.02rem !important; font-weight: 700 !important; }
      p, label, [data-testid="stMarkdownContainer"] { color: #c5d8e9; }
      [data-testid="stMetric"] {
        position: relative; overflow: hidden;
        background: linear-gradient(145deg, rgba(5,24,41,.98), rgba(2,13,25,.98));
        padding: 17px 18px; border-radius: 13px;
        border: 1px solid rgba(34,214,255,.19); min-height: 126px;
        box-shadow: inset 0 0 24px rgba(34,214,255,.025), 0 0 24px rgba(0,120,190,.055);
      }
      [data-testid="stMetric"]::before { content:""; position:absolute; left:0; top:0; width:3px; height:100%; background:linear-gradient(180deg,#22e6ff,#218cff); opacity:.85; }
      [data-testid="stMetricLabel"] { color: #6f8da5 !important; font-size: .79rem !important; letter-spacing:.055em; text-transform:uppercase; }
      [data-testid="stMetricValue"] { color: #eaf9ff !important; font-size: 1.55rem !important; font-weight: 800 !important; text-shadow: 0 0 15px rgba(34,230,255,.11); }
      [data-testid="stMetricDelta"] { font-size: .78rem !important; }
      [data-testid="stAlert"] { border-radius: 11px; background: rgba(5,22,37,.86); border: 1px solid rgba(34,214,255,.2); }
      [data-testid="stDataFrame"] { border: 1px solid rgba(34,214,255,.19); border-radius: 12px; overflow: hidden; }
      [data-testid="stCode"] { border: 1px solid rgba(34,214,255,.19); border-radius: 12px; background: rgba(1,8,18,.9); }
      [data-testid="stSidebar"] { background: linear-gradient(180deg,rgba(2,13,25,.98),rgba(1,7,14,.99)); border-right:1px solid rgba(35,218,255,.2); }
      hr { border-color: rgba(70,145,190,.2) !important; }
      .hero { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding: 24px 26px; margin: 0 0 18px 0;
        position:relative; overflow:hidden;
        background: radial-gradient(circle at 80% 30%,rgba(33,140,255,.13),transparent 34%), linear-gradient(115deg,rgba(4,20,35,.98),rgba(2,13,25,.98));
        border: 1px solid rgba(34,214,255,.38); border-radius: 15px;
        box-shadow: 0 0 0 1px rgba(0,187,255,.035), 0 0 28px rgba(0,130,255,.07), inset 0 0 28px rgba(34,214,255,.025); }
      .hero:after { content:""; position:absolute; inset:0; pointer-events:none; background:linear-gradient(90deg,rgba(34,230,255,.055),transparent 58%); }
      .hero-title { color:#f2f8ff; font-size:1.85rem; font-weight:850; letter-spacing:-.045em; line-height:1.15; }
      .hero-title span { color:#22e6ff !important; text-shadow:0 0 15px rgba(34,230,255,.6); }
      .hero-subtitle { color:#7894aa; font-size:.86rem; margin-top:8px; font-family:'JetBrains Mono',monospace; }
      .hero-mark { display:flex; align-items:center; justify-content:center; width:62px; height:62px; flex:0 0 62px; border-radius:14px;
        background:linear-gradient(145deg,rgba(34,230,255,.12),rgba(33,140,255,.08)); border:1px solid rgba(34,230,255,.55); color:#22e6ff; font-size:2rem;
        box-shadow:0 0 25px rgba(34,230,255,.12),inset 0 0 20px rgba(34,230,255,.05); }
      .pill { display:inline-block; padding:6px 10px; margin-top:12px; border-radius:999px; font-size:.7rem; font-weight:800; letter-spacing:.07em;
        color:#2ff5a6; background:rgba(47,245,166,.07); border:1px solid rgba(47,245,166,.35); box-shadow:0 0 14px rgba(47,245,166,.045); }
      .section-note { color:#607f97; font-size:.81rem; margin-top:-7px; margin-bottom:12px; }
      .panel-label { color:#22cfee; font-size:.72rem; text-transform:uppercase; letter-spacing:.13em; font-weight:800; font-family:'JetBrains Mono',monospace; margin-bottom:8px; }
      .status-card { padding:14px 16px; background:linear-gradient(145deg,rgba(4,24,40,.98),rgba(1,12,22,.98)); border:1px solid rgba(34,214,255,.22); border-radius:12px; margin-bottom:12px; box-shadow:inset 0 0 22px rgba(34,214,255,.025); }
      .small-muted { color: #7894aa; font-size: .84rem; }
      [data-testid="stPlotlyChart"] { border:1px solid rgba(34,214,255,.15); border-radius:12px; padding:5px; background:rgba(2,13,25,.62); }
      @media (max-width: 700px) { .hero { padding:17px; } .hero-title {font-size:1.35rem;} .hero-mark {display:none;} }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_exchange(exchange_id: str):
    if exchange_id not in ccxt.exchanges:
        raise ValueError(f"Exchange CCXT desconocido: {exchange_id}")
    exchange_class = getattr(ccxt, exchange_id)
    ex = exchange_class({"enableRateLimit": True, "timeout": 20000})
    if exchange_id == "revolutx":
        ex.load_markets(params={"region": "EEA"})
    else:
        ex.load_markets()
    return ex


@st.cache_data(ttl=60, show_spinner=False)
def fetch_market_data():
    ex = get_exchange(cfg.exchange_id)
    if cfg.symbol not in ex.markets:
        raise ValueError(
            f"El par {cfg.symbol} no aparece en los mercados de {cfg.exchange_id}. "
            "Revisa EXCHANGE_ID y SYMBOL en .env."
        )
    params = {"region": "EEA"} if cfg.exchange_id == "revolutx" else {}
    raw = ex.fetch_ohlcv(cfg.symbol, timeframe=cfg.timeframe, limit=300, params=params)
    if not raw:
        raise RuntimeError("El exchange no ha devuelto velas.")
    df = pd.DataFrame(raw, columns=["timestamp_ms", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp_ms"], unit="ms", utc=True).astype(str)
    # El bot opera solo sobre velas cerradas. El dashboard sigue ese mismo criterio.
    if len(df) > 1:
        df = df.iloc[:-1].copy()
    df = add_indicators(df)
    ticker = None
    try:
        ticker = ex.fetch_ticker(cfg.symbol, params=params)
    except Exception:
        pass
    live_price = None
    if ticker:
        live_price = ticker.get("last") or ticker.get("close")
    if live_price is None:
        live_price = float(df.iloc[-1]["close"])
    return df, float(live_price)


def read_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_trades():
    if not TRADES_PATH.exists():
        return pd.DataFrame(columns=["time", "side", "price", "qty", "fee", "cash_after", "equity_after", "pnl_net", "reason"])
    try:
        return pd.read_csv(TRADES_PATH)
    except Exception:
        return pd.DataFrame(columns=["time", "side", "price", "qty", "fee", "cash_after", "equity_after", "pnl_net", "reason"])


def last_log_lines(n=14):
    if not LOG_PATH.exists():
        return ["Todavía no existe bot.log. Arranca primero python bot.py."]
    try:
        return LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except Exception as exc:
        return [f"No se pudo leer bot.log: {exc}"]


def fmt_money(value, currency=quote_currency):
    try:
        return f"{float(value):,.2f} {currency}"
    except (TypeError, ValueError):
        return "—"


st.markdown(
    f"""
    <div class="hero">
      <div>
        <div class="hero-title">BTC Scalper <span style="color:#5ce1d0">/</span> Live Monitor</div>
        <div class="hero-subtitle">Supervisión de mercado, señales e historial de la estrategia</div>
        <div class="pill">● PAPER TRADING · SIN ÓRDENES REALES</div>
      </div>
      <div class="hero-mark">↗</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption(f"{cfg.exchange_id.upper()}  /  {cfg.symbol}  /  Velas {cfg.timeframe}  /  Panel cada 10 s · mercado cacheado 60 s")

if cfg.mode != "paper" or cfg.live_trading:
    st.error("Configuración inesperada: este panel está pensado para supervisar el modo PAPER. No habilites trading real desde este dashboard.")
else:
    st.success("Entorno de simulación activo. El dashboard no envía órdenes y no necesita claves API.")

try:
    candles, live_price = fetch_market_data()
    market_error = None
except Exception as exc:
    candles, live_price, market_error = None, None, str(exc)

state = read_state()
trades = read_trades()
logs = last_log_lines()

if market_error:
    st.error(f"No se pudieron actualizar los datos de mercado: {market_error}")

if candles is not None and not candles.empty:
    last = candles.iloc[-1]
    latest_candle_time = pd.to_datetime(last["timestamp"], utc=True)
    price_for_equity = float(live_price if live_price is not None else last["close"])
    cash = float(state.get("cash", cfg.initial_capital))
    position = state.get("position")
    qty = float(position.get("qty", 0)) if position else 0.0
    equity = cash + qty * price_for_equity
    initial = float(cfg.initial_capital)
    total_return = ((equity / initial) - 1) * 100 if initial else 0.0
    unrealized_pnl = 0.0
    if position:
        entry_price = float(position.get("entry_price", 0))
        entry_fee = float(position.get("entry_fee", 0))
        estimated_exit_fee = price_for_equity * qty * cfg.fee_rate
        unrealized_pnl = (price_for_equity - entry_price) * qty - entry_fee - estimated_exit_fee

    closed = trades[trades.get("side", pd.Series(dtype=str)).astype(str).str.upper() == "SELL"].copy() if not trades.empty else pd.DataFrame()
    if not closed.empty:
        closed["pnl_net_num"] = pd.to_numeric(closed.get("pnl_net", 0), errors="coerce").fillna(0)
        realized_pnl = float(closed["pnl_net_num"].sum())
        win_rate = float((closed["pnl_net_num"] > 0).mean() * 100)
        closed_count = len(closed)
    else:
        realized_pnl, win_rate, closed_count = 0.0, 0.0, 0

    log_fresh = False
    if LOG_PATH.exists():
        log_fresh = (datetime.now().timestamp() - LOG_PATH.stat().st_mtime) < 8 * 60
    status_label = "Actividad reciente" if log_fresh else "Sin logs recientes"

    st.markdown('<div class="panel-label">Resumen de cuenta</div>', unsafe_allow_html=True)
    a, b, c, d, e = st.columns(5)
    a.metric("Precio de mercado", fmt_money(price_for_equity))
    b.metric("Patrimonio simulado", fmt_money(equity), f"{total_return:+.2f}% desde inicio")
    c.metric("Efectivo PAPER", fmt_money(cash))
    d.metric("PnL realizado", fmt_money(realized_pnl), f"{closed_count} ventas cerradas")
    e.metric("PnL abierto estimado", fmt_money(unrealized_pnl) if position else fmt_money(0), "posición abierta" if position else "sin posición abierta")

    col_left, col_right = st.columns([1.8, 1])
    with col_left:
        st.subheader("Mercado e indicadores")
        st.markdown('<div class="section-note">Últimas 100 velas cerradas · las horas se muestran en horario peninsular español</div>', unsafe_allow_html=True)
        chart_df = candles.tail(100).copy()
        chart_df["timestamp_dt"] = pd.to_datetime(chart_df["timestamp"], utc=True).dt.tz_convert(ZoneInfo("Europe/Madrid"))
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=chart_df["timestamp_dt"], open=chart_df["open"], high=chart_df["high"],
            low=chart_df["low"], close=chart_df["close"], name="BTC/USD",
            increasing_line_color="#26d6a3", decreasing_line_color="#ff647c",
            increasing_fillcolor="#26d6a3", decreasing_fillcolor="#ff647c"
        ))
        for col, label, color in [("ema9", "EMA 9", "#57d8cf"), ("ema21", "EMA 21", "#f6b85b"), ("ema200", "EMA 200", "#a78bfa")]:
            fig.add_trace(go.Scatter(x=chart_df["timestamp_dt"], y=chart_df[col], mode="lines", name=label, line={"width": 1.8, "color": color}))
        fig.add_hline(y=price_for_equity, line_dash="dot", line_color="#e6edf7", opacity=.65, annotation_text="Precio actual", annotation_font_color="#cbd7e7")
        fig.update_layout(
            height=460, margin={"l": 10, "r": 10, "t": 30, "b": 10}, xaxis_rangeslider_visible=False,
            legend={"orientation":"h", "y":1.04, "x":0, "font":{"color":"#b9c9dc", "size":11}},
            paper_bgcolor="rgba(1,8,18,0)", plot_bgcolor="rgba(3,17,31,.88)", font={"color":"#c5d8e9"},
            xaxis={"gridcolor":"#213149", "linecolor":"#2b3b52", "tickfont":{"color":"#91a7c1"}},
            yaxis={"gridcolor":"#213149", "linecolor":"#2b3b52", "tickfont":{"color":"#91a7c1"}},
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        rsi_fig = go.Figure()
        rsi_fig.add_trace(go.Scatter(x=chart_df["timestamp_dt"], y=chart_df["rsi14"], name="RSI 14", mode="lines", line={"color":"#22e6ff", "width":2.2}, fill="tozeroy", fillcolor="rgba(34,230,255,.08)"))
        rsi_fig.add_hline(y=50, line_dash="dash", line_color="#9a72ff", annotation_text="Nivel 50", annotation_font_color="#9a72ff")
        rsi_fig.update_yaxes(range=[0, 100], gridcolor="rgba(34,214,255,.10)", linecolor="rgba(34,214,255,.20)")
        rsi_fig.update_xaxes(gridcolor="rgba(34,214,255,.10)", linecolor="rgba(34,214,255,.20)", tickfont={"color":"#7894aa"})
        rsi_fig.update_layout(height=190, margin={"l": 10, "r": 10, "t": 20, "b": 10}, showlegend=False, paper_bgcolor="rgba(1,8,18,0)", plot_bgcolor="rgba(3,17,31,.88)", font={"color":"#c5d8e9"})
        st.plotly_chart(rsi_fig, use_container_width=True)

    with col_right:
        st.subheader("Estado del bot")
        st.metric("Archivo de log", status_label)
        local_candle_time = latest_candle_time.tz_convert(ZoneInfo("Europe/Madrid"))
        st.write(f"**Última vela cerrada (España):** {local_candle_time.strftime('%d/%m/%Y %H:%M:%S %Z')}")
        st.caption(f"Referencia UTC: {latest_candle_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        st.write(f"**EMA9:** {float(last['ema9']):,.2f} {quote_currency}")
        st.write(f"**EMA21:** {float(last['ema21']):,.2f} {quote_currency}")
        st.write(f"**EMA200:** {float(last['ema200']):,.2f} {quote_currency}")
        st.write(f"**RSI14:** {float(last['rsi14']):.2f}")
        entry_ok = bool(last.get("entry_signal", False))
        exit_ok = bool(last.get("exit_signal", False))
        if entry_ok:
            st.success("La última vela cerrada cumple la señal de entrada")
        elif position and exit_ok:
            st.warning("EMA9 está por debajo de EMA21; revisar la lógica de salida paper")
        else:
            st.info("Sin señal de entrada en la última vela cerrada")

        st.subheader("Posición PAPER")
        if position:
            st.write(f"**Cantidad:** {qty:.8f} BTC")
            st.write(f"**Entrada:** {fmt_money(position.get('entry_price'))}")
            st.write(f"**Stop:** {fmt_money(position.get('stop_price'))}")
            st.write(f"**Objetivo:** {fmt_money(position.get('target_price'))}")
            st.write(f"**PnL abierto estimado:** {fmt_money(unrealized_pnl)}")
        else:
            st.write("No hay ninguna posición simulada abierta.")
        st.caption(f"Operaciones cerradas ganadoras: {win_rate:.1f}% (solo orientativo con {closed_count} cierres).")

    st.divider()
    st.subheader("Operaciones recientes")
    st.markdown('<div class="section-note">Las operaciones se leen desde trades.csv; si no hay señales, esta tabla puede permanecer vacía.</div>', unsafe_allow_html=True)
    if not trades.empty:
        show_cols = [c for c in ["time", "side", "price", "qty", "fee", "pnl_net", "reason"] if c in trades.columns]
        st.dataframe(trades[show_cols].tail(15).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.write("Todavía no hay operaciones en trades.csv. Es normal si no ha aparecido ninguna señal.")

    st.subheader("Registro técnico")
    st.markdown('<div class="section-note">Últimos mensajes del proceso del bot para diagnosticar conexiones, señales y errores.</div>', unsafe_allow_html=True)
    st.code("\n".join(logs), language="text")
    st.caption("Diseño neon inspirado en MIKO AI Agent Lab. Panel cada 10 segundos; los datos del mercado se reutilizan durante 60 segundos para reducir llamadas a la API.")
else:
    st.subheader("Esperando datos del mercado")
    st.write("Comprueba que el exchange, el símbolo y la región del archivo .env sean correctos.")
    st.code("\n".join(logs), language="text")
