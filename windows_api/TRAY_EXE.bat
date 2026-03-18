@echo off
title Sync API System - System Tray

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - MODO SYSTEM TRAY
echo ========================================
echo.
echo Iniciando servicio en segundo plano...
echo El icono aparecera en la barra de tareas (junto al reloj)
echo.
echo El sistema se iniciara automaticamente al encender el equipo.
echo.

SyncAPISystem.exe --mode tray

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo iniciar el System Tray
    echo.
    pause
)
