# BTC Scalper 5M — starter seguro para Windows

Bot educativo para BTC/USDT en velas de 5 minutos. Esta versión ejecuta únicamente simulación (`paper`) y backtesting. **No envía órdenes reales.**

## Qué incluye
- EMA 9/21/200, RSI 14 y ATR 14.
- Entrada al cierre de vela: cierre > EMA200, EMA9 > EMA21 y RSI cruza 50 al alza.
- Salida por stop (1,5 ATR), objetivo (2R) o cruce bajista EMA9/EMA21.
- Riesgo nominal 0,5% del equity por operación; límite diario inicial 2%; máximo 8 operaciones/día.
- Costes aproximados configurables: comisión y deslizamiento en ambos lados.
- Registro en `trades.csv`, estado paper en `state.json` y logs en `bot.log`.
- Backtesting y pruebas automáticas.

## Advertencias importantes
- No hay garantía de rentabilidad. El scalping puede perder dinero incluso con reglas disciplinadas.
- `INITIAL_CAPITAL_USDT=55` es una aproximación a 50 EUR convertidos a USDT, no una cotización en tiempo real. Ajusta el saldo simulado.
- La comisión predeterminada `FEE_RATE=0.001` equivale a 0,10% por lado; consulta tu tarifa real y el tipo de orden. `SLIPPAGE_RATE=0.0005` es una hipótesis, no un dato observado.
- El umbral de 10 USDT del motor es una comprobación conservadora configurable, no sustituye los filtros reales del mercado del exchange.
- Las velas OHLC no revelan el orden exacto intravela. Si stop y objetivo aparecen tocados en la misma vela, el backtest supone conservadoramente que se ejecuta primero el stop.
- El stop de esta versión se controla localmente. Si el PC, el proceso o Internet se detienen, no existe un stop real en el exchange. Por eso el modo real está bloqueado.
- Para activar dinero real habría que implementar y probar órdenes protectoras nativas del exchange, recuperación/reconciliación de órdenes, tratamiento de fills parciales, reglas mínimas de cantidad/notional, y validar que la entidad de exchange elegida está autorizada para prestar servicios en España.

## Instalación (Windows 10/11)
1. Instala Python 3.11 o posterior y marca "Add Python to PATH".
2. Descomprime el ZIP en una carpeta, por ejemplo `C:\btc-scalper-5m`.
3. Abre PowerShell en esa carpeta:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```
   Si PowerShell bloquea la activación, usa CMD y ejecuta `.venv\Scripts\activate.bat`.
4. Ejecuta pruebas:
   ```powershell
   pytest -q
   ```
5. Backtest con datos históricos públicos:
   ```powershell
   python backtest.py --days 90
   ```
   Genera `backtest_trades.csv` y `backtest_equity.csv`.
6. Ejecuta simulación en tiempo real:
   ```powershell
   python bot.py
   ```
   O haz doble clic en `run_paper.bat`. Necesita Internet y deja el PC encendido.
7. Detén con `Ctrl+C`.

## Configuración
Edita `.env`. Valores principales:
- `MODE=paper`: obligatorio para esta versión.
- `INITIAL_CAPITAL_USDT=55`: capital simulado aproximado.
- `FEE_RATE=0.001`: 0,10% por operación de compra y por venta.
- `SLIPPAGE_RATE=0.0005`: 0,05% de deslizamiento supuesto por lado.
- `RISK_PER_TRADE=0.005`: riesgo teórico de 0,5%.
- `MAX_DAILY_LOSS=0.02`: detiene nuevas entradas al superar el 2% diario.
- `MAX_POSITION_FRACTION=0.80`: no usa más del 80% del efectivo en la compra.
- `MAX_TRADES_PER_DAY=8`: limita el número de operaciones cerradas por día.

## Importante sobre el backtest
El backtest es una primera aproximación, no una validación profesional. Usa velas públicas, no simula libro de órdenes, latencia ni fills parciales; tampoco representa todos los fallos operativos. Evalúa varios periodos y reserva un tramo fuera de muestra antes de concluir que la estrategia funciona.

## Seguridad del exchange
No se necesitan API keys para consultar velas públicas. No introduzcas claves para este modo. Nunca habilites permisos de retirada en una API de trading. Consulta el registro CNMV/ESMA y confirma la entidad jurídica concreta que presta el servicio en España antes de abrir una cuenta o depositar fondos.
