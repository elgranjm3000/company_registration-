@echo off
title Sync API System - Configurar

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - CONFIGURAR
echo ========================================
echo.
echo Iniciando configuracion del sistema...
echo.

SyncAPISystem.exe --mode config

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo iniciar la configuracion
    echo.
    pause
)
