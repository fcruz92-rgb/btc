@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo No se encuentra el entorno virtual .venv.
  echo Sigue las instrucciones del README para crear y activar el entorno.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m streamlit run dashboard.py
pause
