@echo off
REM ====================================================================
REM SCRIPT: Crear instalador con Inno Setup
REM AUTOR: Sistema de Sincronización PostgreSQL → MySQL
REM FECHA: 2025-01-22
REM ====================================================================

echo ========================================
echo CREANDO INSTALADOR
echo ========================================
echo.

REM Verificar que Inno Setup está instalado
where iscc >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Inno Setup no está instalado.
    echo.
    echo Por favor, instale Inno Setup desde:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo.
echo Creando instalador con Inno Setup...
echo.

iscc setup.iss

if errorlevel 1 (
    echo.
    echo ERROR creando instalador
    pause
    exit /b 1
)

echo.
echo ========================================
echo INSTALADOR CREADO EXITOSAMENTE
echo ========================================
echo.
echo Buscar el instalador en: output\setup_sync.exe
echo.
pause
