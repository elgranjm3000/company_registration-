@echo off
title Sync API System - Debug

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - MODO DEBUG
echo ========================================
echo.
echo Iniciando sistema con logs detallados...
echo.

set PYTHONIOENCODING=utf-8
python sync_system_api.py --mode sync

echo.
echo Presiona cualquier tecla para salir...
pause >nul
