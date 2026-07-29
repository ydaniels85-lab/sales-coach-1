@echo off
setlocal
cd /d "%~dp0"
start "Fin-Tastic Backend" cmd /k RUN_BACKEND.bat
start "Fin-Tastic Frontend" cmd /k RUN_FRONTEND.bat
