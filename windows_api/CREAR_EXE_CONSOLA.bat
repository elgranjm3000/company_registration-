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

REM Limpiar build anterior
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Usar archivo .spec especifico para modo con consola
pyinstaller --clean sync_system_api_console.spec

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
echo Ubicacion: dist\SyncAPISystem.exe
echo.
echo NOTA: Con consola - modo debug
echo.
pause
