@echo off
setlocal enabledelayedexpansion
title Sync API System - Instalar y Ejecutar

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - INSTALADOR
echo ========================================
echo.

REM [1/4] Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo.
    echo Pasos:
    echo   1. Ve a https://www.python.org/downloads/
    echo   2. Descarga Python 3.8 o superior
    echo   3. IMPORTANTE: Marca "Add Python to PATH"
    echo   4. Instala
    echo.
    pause
    exit /b 1
)

echo Python encontrado
python --version
echo.

REM [2/4] Instalar dependencias
echo Instalando dependencias...
echo.

echo   - psycopg2-binary (PostgreSQL)
pip install psycopg2-binary 2>nul

echo   - requests (HTTP Client)
pip install requests 2>nul

echo   - pystray (System Tray)
pip install pystray 2>nul

echo   - Pillow (Iconos)
pip install Pillow 2>nul

echo   - cryptography (Encriptacion)
pip install cryptography 2>nul

echo.
REM [3/4] Verificar dependencias
echo Verificando imports...
python -c "import psycopg2; import requests; import pystray; from PIL import Image; from cryptography.fernet import Fernet; print('OK: Todas las dependencias correctas')" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudieron importar todas las dependencias
    echo.
    echo Posibles soluciones:
    echo   1. Asegurate de tener Python 3.8+ instalado
    echo   2. Ejecuta: python -m pip install --upgrade pip
    echo   3. Ejecuta: pip install --upgrade psycopg2-binary requests pystray Pillow cryptography
    echo.
    pause
    exit /b 1
)

echo.
REM [4/4] Menu de ejecucion
echo ========================================
echo   DEPENDENCIAS INSTALADAS CORRECTAMENTE
echo ========================================
echo.
echo Selecciona modo de ejecucion:
echo.
echo 1. Configurar sistema (primera vez - GUI)
echo 2. Sincronizar ahora (consola)
echo 3. Administrador (GUI)
echo 4. Modo System Tray (icono en barra de tareas)
echo 5. Reconfigurar sistema
echo 6. Salir
echo.

set /p opcion="Selecciona una opcion (1-6): "

echo.

if "%opcion%"=="1" (
    echo Iniciando configuracion GUI...
    python sync_system_api.py --mode config
) else if "%opcion%"=="2" (
    echo Iniciando sincronizacion...
    python sync_system_api.py --mode sync
    echo.
    echo Presiona cualquier tecla para ver resultados...
    pause >nul
) else if "%opcion%"=="3" (
    echo Iniciando administrador GUI...
    python sync_system_api.py --mode manager
) else if "%opcion%"=="4" (
    echo Iniciando modo System Tray...
    echo El icono aparecera en la barra de tareas (junto al reloj)
    python sync_system_api.py --mode tray
) else if "%opcion%"=="5" (
    echo Iniciando reconfiguracion...
    python sync_system_api.py --mode reconfig
) else if "%opcion%"=="6" (
    echo Saliendo...
    exit /b 0
) else (
    echo Opcion no valida: %opcion%
    pause
)

echo.
