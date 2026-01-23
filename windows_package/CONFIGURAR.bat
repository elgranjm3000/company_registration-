@echo off
title Configurar Sync System

cd /d "%~dp0"

echo Iniciando configuracion del sistema...
echo.

if not exist "dist\sync_system.exe" (
    echo ERROR: No existe dist\sync_system.exe
    echo Ejecuta primero: CREAR_EXE.bat
    pause
    exit /b 1
)

echo Ejecutando: dist\sync_system.exe --mode config
echo.

dist\sync_system.exe --mode config

if %errorlevel% neq 0 (
    echo.
    echo Error al ejecutar. Presiona cualquier tecla para ver detalles...
    pause
)
