@echo off
title Compilar Sync System - CON Consola (DEBUG)

cd /d "%~dp0"

echo ========================================
echo   COMPILACION CON CONSOLE (DEBUG MODE)
echo ========================================
echo.
echo Este script crea el .exe CON terminal visible
echo Util para ver errores y hacer debug
echo.
echo Para crear el .exe SIN terminal (produccion):
echo   Ejecuta: COMPILAR_SIN_CONSOOLA.bat
echo.

pause

python build_exe.py --console

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo   ERROR: Fallo en la compilacion
    echo ========================================
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡COMPILACION EXITOSA!
echo ========================================
echo.
echo El .exe se creo CON CONSOLA
echo.
echo Ubicacion: dist\SyncSystem\sync_system.exe
echo.
echo Para ejecutar:
echo   dist\SyncSystem\sync_system.exe --mode tray
echo.
pause
