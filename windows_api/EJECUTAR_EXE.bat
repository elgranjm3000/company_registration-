@echo off
title Sync API System - Sincronizar

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - SINCRONIZAR
echo ========================================
echo.
echo Iniciando sincronizacion completa...
echo.

SyncAPISystem.exe --mode sync

echo.
echo Presiona cualquier tecla para salir...
pause >nul
