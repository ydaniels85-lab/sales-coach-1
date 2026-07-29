@echo off
setlocal
cd /d "%~dp0backend"
if not exist venv (
  echo Creating Python virtual environment...
  python -m venv venv
)
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Starting Fin-Tastic Sales Coach backend on http://localhost:5000
echo.
python app.py
pause
