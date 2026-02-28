@echo off
title Compilar Sync System - Version Completa

cd /d "%~dp0"

echo ========================================
echo   COMPILACION COMPLETA DE SYNC SYSTEM
echo ========================================
echo.
echo Selecciona el modo de compilacion:
echo.
echo   1. CON Consola (DEBUG) - Muestra terminal para ver errores
echo   2. SIN Consola (PRODUCCION) - Solo GUI, sin terminal
echo.

set /p modo="Selecciona 1 o 2: "

if "%modo%"=="1" (
    echo.
    echo Modo seleccionado: CON CONSOLA (DEBUG)
    echo.
    goto compilar_con_consola
) else if "%modo%"=="2" (
    echo.
    echo Modo seleccionado: SIN CONSOLA (PRODUCCION)
    echo.
    goto compilar_sin_consola
) else (
    echo.
    echo Opcion no valida. Usando modo CON CONSOLA por defecto.
    echo.
    goto compilar_con_consola
)

:compilar_con_consola
echo ========================================
echo   COMPILANDO CON CONSOLA...
echo ========================================
echo.

python build_exe.py --console
goto fin

:compilar_sin_consola
echo ========================================
echo   COMPILANDO SIN CONSOLA...
echo ========================================
echo.

python build_exe.py
goto fin

:fin
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

if "%modo%"=="1" (
    echo El .exe se creo CON CONSOLA
    echo.
    echo Podras ver la terminal y los mensajes de error
) else (
    echo El .exe se creo SIN CONSOLA
    echo.
    echo Si tienes problemas, usa la opcion 1 (CON CONSOLA)
)

echo.
echo Ubicacion: dist\SyncSystem\sync_system.exe
echo.

REM Preguntar si quiere ejecutar ahora
set /p ejecutar="¿Deseas ejecutar el .exe ahora en modo manager? (s/n): "
if /i "%ejecutar%"=="s" (
    echo.
    echo Ejecutando en modo manager...
    cd dist\SyncSystem
    start sync_system.exe --mode manager
    cd ..\..
)

echo.
pause
