DASHBOARD LOCAL PARA BTC SCALPER (PAPER)

1) Copia dashboard.py, requirements-dashboard.txt y run_dashboard.bat en la misma carpeta donde tienes bot.py, config.py, strategy.py, .env y los archivos trades.csv/state.json/bot.log.

2) Abre PowerShell en esa carpeta y activa el entorno:
   .\.venv\Scripts\Activate.ps1

3) Instala las dependencias del dashboard:
   python -m pip install -r requirements-dashboard.txt

4) Deja el bot funcionando en una ventana de PowerShell:
   python bot.py

5) Abre una segunda ventana de PowerShell en la misma carpeta y ejecuta:
   streamlit run dashboard.py
   También puedes hacer doble clic en run_dashboard.bat.

6) Se abrirá el navegador normalmente en http://localhost:8501. Si no se abre, copia esa dirección en el navegador.

El dashboard se actualiza cada 10 segundos. Lee datos públicos de mercado y los archivos locales del bot. No envía órdenes y no requiere claves API.

NOTAS:
- Para Revolut X, usa el mismo EXCHANGE_ID y SYMBOL que ya funcionan en el bot (por ejemplo, revolutx y BTC/USD). El dashboard añade region=EEA a las consultas de Revolut X.
- Si el mercado no está disponible, revisa el símbolo y la configuración de región en .env.
- El valor de patrimonio es una estimación del motor PAPER; no representa saldo real de Revolut X.
- Mantén MODE=paper y LIVE_TRADING=false. Este dashboard no habilita trading real.
