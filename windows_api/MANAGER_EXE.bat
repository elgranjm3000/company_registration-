@echo off
title Sync API System - Manager

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - MANAGER
echo ========================================
echo.
echo Iniciando ventana del administrador...
echo.

SyncAPISystem.exe --mode manager

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo iniciar el manager
    echo.
    pause
)
