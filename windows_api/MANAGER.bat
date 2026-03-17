@echo off
title Sync API System - Manager

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - MANAGER
echo ========================================
echo.
echo Iniciando ventana del administrador...
echo.

python sync_system_api.py --mode manager

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo iniciar el manager
    echo.
    pause
)
