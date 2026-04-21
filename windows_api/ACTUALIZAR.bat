@echo off
title Actualizar desde Git - Sync API System

cd /d "%~dp0"

echo ========================================
echo   ACTUALIZAR DESDE GITHUB
echo   Sync API System
echo ========================================
echo.

echo Actualizando archivos desde GitHub...
echo.

git pull origin main

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo actualizar desde GitHub
    echo.
    echo Posibles causas:
    echo 1. Git no está instalado
    echo 2. Hay cambios locales sin commit
    echo 3. No hay conexion a internet
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡ACTUALIZACION COMPLETA!
echo ========================================
echo.
echo Ahora puedes ejecutar CREAR_EXE_CONSOLA.bat
echo.
pause
