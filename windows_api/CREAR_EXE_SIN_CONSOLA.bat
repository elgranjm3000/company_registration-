@echo off
title Crear Ejecutable Sin Consola - Sync API System

cd /d "%~dp0"

echo ========================================
echo   CREAR EJECUTABLE .EXE (SIN CONSOLA)
echo   Sync API System
echo ========================================
echo.
echo Este ejecutable NO mostrara la consola
echo (modo produccion - sin ventana negra)
echo.

REM Verificar dependencias
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo Creando ejecutable SIN consola...
echo.

REM Limpiar build anterior
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Usar archivo .spec especifico para modo sin consola
pyinstaller --clean sync_system_api_windowed.spec

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
echo NOTA: Sin consola - modo produccion
echo       Las notificaciones funcionaran correctamente
echo.
pause
