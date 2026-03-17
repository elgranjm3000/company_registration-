@echo off
title Crear Ejecutable con Consola - Sync API System

cd /d "%~dp0"

echo ========================================
echo   CREAR EJECUTABLE .EXE (CON CONSOLA)
echo   Sync API System
echo ========================================
echo.
echo Este ejecutable mostrara la consola
echo (util para debug)
echo.

REM Verificar dependencias
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo Creando ejecutable con consola...
echo.

pyinstaller --clean sync_system_api.spec

if %errorlevel% neq 0 (
    echo.
    echo ERROR: La compilacion fallo
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡EJECUTABLE CREADO!
echo ========================================
echo.
echo Ubicacion: dist\SyncAPISystem\
echo.
pause
