@echo off
setlocal
cd /d "%~dp0frontend"
if not exist node_modules (
  echo Installing frontend packages...
  npm install
)
echo.
echo Starting Fin-Tastic Sales Coach frontend on http://localhost:5173
echo.
npm run dev
pause
