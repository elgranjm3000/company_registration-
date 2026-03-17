@echo off
title Diagnosticar Ejecutable - Sync API System

cd /d "%~dp0"

echo ========================================
echo   DIAGNOSTICANDO EJECUTABLE
echo ========================================
echo.

if not exist "dist\SyncAPISystem\SyncAPISystem.exe" (
    echo ERROR: No existe el ejecutable
    echo Primero ejecuta CREAR_EXE_CONSOLA.bat
    pause
    exit /b 1
)

echo Ejecutable encontrado: dist\SyncAPISystem\SyncAPISystem.exe
echo.

cd dist\SyncAPISystem

echo ========================================
echo   PROBANDO: --mode help
echo ========================================
echo.
echo Esto deberia mostrar la ayuda sin cerrarse
echo.

SyncAPISystem.exe --mode help

if %errorlevel% neq 0 (
    echo.
    echo ERROR: El ejecutable retorno codigo %errorlevel%
)

echo.
echo ========================================
echo   DIAGNOSTICO COMPLETADO
echo ========================================
echo.
pause
