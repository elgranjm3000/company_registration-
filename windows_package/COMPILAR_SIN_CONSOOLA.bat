@echo off
title Compilar Sync System - SIN Consola (PRODUCCION)

cd /d "%~dp0"

echo ========================================
echo   COMPILACION SIN CONSOLE (PRODUCCION)
echo ========================================
echo.
echo Este script crea el .exe SIN terminal visible
echo Solo se ve la ventana de la aplicacion GUI
echo.
echo Para crear el .exe CON terminal (debug):
echo   Ejecuta: COMPILAR_CON_CONSOOLA.bat
echo.

pause

python build_exe.py

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
echo El .exe se creo SIN CONSOLA
echo.
echo Ubicacion: dist\SyncSystem\sync_system.exe
echo.
echo Para ejecutar:
echo   dist\SyncSystem\sync_system.exe --mode tray
echo.
echo IMPORTANTE:
echo   Si el .exe no funciona, compila con --console
echo   para ver los mensajes de error
echo.
pause
