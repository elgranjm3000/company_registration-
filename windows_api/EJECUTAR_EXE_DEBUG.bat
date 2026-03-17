@echo off
title Ejecutar EXE con Debug - Sync API System

cd /d "%~dp0"

echo ========================================
echo   EJECUTANDO .EXE CON CAPTURA DE ERRORES
echo ========================================
echo.

if not exist "dist\SyncAPISystem\SyncAPISystem.exe" (
    echo ❌ ERROR: No existe el ejecutable
    echo.
    echo Ubicacion esperada: dist\SyncAPISystem\SyncAPISystem.exe
    echo.
    echo Primero ejecuta: CREAR_EXE_CONSOLA.bat
    echo.
    pause
    exit /b 1
)

cd dist\SyncAPISystem

echo 📂 Directorio actual: %CD%
echo.
echo 📋 Archivos en el directorio:
dir /B *.exe *.dll _internal 2>nul
echo.
echo ========================================
echo   EJECUTANDO: SyncAPISystem.exe --mode help
echo ========================================
echo.

SyncAPISystem.exe --mode help

set EXIT_CODE=%errorlevel%

echo.
echo ========================================
echo   RESULTADO
echo ========================================
echo.
echo Codigo de salida: %EXIT_CODE%
echo.

if %EXIT_CODE% neq 0 (
    echo ❌ ERROR: El ejecutable fallo con codigo %EXIT_CODE%
    echo.
    echo Posibles causas:
    echo   1. Faltan archivos DLL en _internal\
    echo   2. Faltan api_client\ o sync\
    echo   3. Error de dependencias de Python
    echo.
    echo Revisa el error arriba para más detalles
) else (
    echo ✅ EXITO: El ejecutable funciono correctamente
)

echo.
echo Presiona cualquier tecla para salir...
pause >nul
