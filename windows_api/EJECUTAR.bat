@echo off
title Sync API System - Ejecutar

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - SINCRONIZAR
echo ========================================
echo.
echo Iniciando sincronizacion en modo consola...
echo.

python sync_system_api.py --mode sync

echo.
echo Presiona cualquier tecla para salir...
pause >nul
