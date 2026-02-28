@echo off
title Compilar Sync System - CON CONSOLA (DEBUG)

cd /d "%~dp0"

echo ========================================
echo   COMPILACION CON CONSOLA (DEBUG)
echo ========================================
echo.
echo Este script crea el .exe CON consola visible
echo Sirve para ver errores que no se muestran
echo en modo SIN CONSOLA
echo.
echo ADVERTENCIA: El .exe mostrara una terminal
echo            junto con la ventana GUI
echo.
pause

REM Instalar dependencias
echo [1/3] Instalando dependencias...
pip install pyinstaller psycopg2-binary pymysql pystray Pillow bcrypt win10toast cryptography 2>nul

REM Limpiar builds anteriores
echo [2/3] Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

REM Compilar CON consola
echo [3/3] Compilando con consola...
python build_exe_debug.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Fallo en la compilacion
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡COMPILACION EXITOSA!
echo ========================================
echo.
echo El .exe se creo CON CONSOLA para DEBUG
echo.
echo Ubicacion: dist\SyncSystem_DEBUG\SyncSystem_DEBUG.exe
echo.
echo INSTRUCCIONES:
echo   1. Ejecuta: dist\SyncSystem_DEBUG\SyncSystem_DEBUG.exe --mode config
echo   2. Ingresa los datos
echo   3. Click en GUARDAR
echo   4. MIRA LA CONSOLA - aparecera el error
echo.
echo El error te dira que esta fallando
echo.
pause
