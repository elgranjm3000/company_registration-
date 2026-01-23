@echo off
title Ejecutar Sync System (Directo con Python)

cd /d "%~dp0"

echo ========================================
echo   EJECUTAR SYNC SYSTEM (PYTHON DIRECTO)
echo ========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Descarga desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Verificar archivos
if not exist "sync_system.py" (
    echo ERROR: sync_system.py no encontrado
    pause
    exit /b 1
)

if not exist "smart_sync_complete.py" (
    echo ERROR: smart_sync_complete.py no encontrado
    pause
    exit /b 1
)

REM Verificar dependencias
echo Verificando dependencias...
python -c "import psycopg2; import mysql.connector; import tkinter" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo Instalando dependencias...
    pip install psycopg2-binary mysql-connector-python
)

echo.
echo ========================================
echo   SELECCIONA MODO DE EJECUCION
echo ========================================
echo.
echo 1. Configurar sistema (primera vez)
echo 2. Administrador
echo 3. Sincronizar ahora
echo 4. Modo servicio (continuo)
echo.

set /p opcion="Selecciona una opcion (1-4): "

if "%opcion%"=="1" (
    echo.
    echo Iniciando configuracion...
    python sync_system.py --mode config
) else if "%opcion%"=="2" (
    echo.
    echo Iniciando administrador...
    python sync_system.py --mode manager
) else if "%opcion%"=="3" (
    echo.
    echo Iniciando sincronizacion...
    python sync_system.py --mode sync
) else if "%opcion%"=="4" (
    echo.
    echo Iniciando modo servicio...
    echo Presiona Ctrl+C para detener
    python sync_system.py --mode service
) else (
    echo Opcion no valida
)

echo.
pause
