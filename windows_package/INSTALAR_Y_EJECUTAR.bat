@echo off
setlocal enabledelayedexpansion
title Instalar Dependencias y Ejecutar

cd /d "%~dp0"

echo ========================================
echo   INSTALAR DEPENDENCIAS Y EJECUTAR
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
echo Instalando dependencias basicas...
pip install psycopg2-binary pymysql 2>nul

echo Instalando dependencias para System Tray...
pip install pystray Pillow 2>nul

echo Instalando dependencias para Notificaciones...
pip install win10toast 2>nul

echo.
REM [3/4] Verificar dependencias
echo Verificando imports...
python -c "import psycopg2; import pymysql; import tkinter; import pystray; from PIL import Image; from win10toast import ToastNotifier; print('OK: Todas las dependencias correctas')" 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudieron importar todas las dependencias
    echo.
    echo Posibles soluciones:
    echo   1. Asegurate de tener Python 3.8+ instalado
    echo   2. Ejecuta: python -m pip install --upgrade pip
    echo   3. Ejecuta: pip install --upgrade psycopg2-binary pymysql pystray Pillow win10toast
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
echo 3. Modo servicio (consola - continuo)
echo 4. Administrador (GUI)
echo 5. Modo System Tray (icono en barra de tareas - Transparente)
echo.

set /p opcion="Selecciona una opcion (1-5): "

echo.

if "%opcion%"=="1" (
    echo Iniciando configuracion GUI...
    python sync_system.py --mode config
) else if "%opcion%"=="2" (
    echo Iniciando sincronizacion...
    python sync_system.py --mode sync
    echo.
    echo Presiona cualquier tecla para ver resultados...
    pause
) else if "%opcion%"=="3" (
    echo Iniciando modo servicio...
    echo Presiona Ctrl+C para detener
    python sync_system.py --mode service
) else if "%opcion%"=="4" (
    echo Iniciando administrador GUI...
    python sync_system.py --mode manager
) else if "%opcion%"=="5" (
    echo Iniciando modo System Tray...
    echo El icono aparecera en la barra de tareas (junto al reloj)
    python sync_system.py --mode tray
) else (
    echo Opcion no valida: %opcion%
)

echo.
