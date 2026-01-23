@echo off
setlocal enabledelayedexpansion
title Desinstalar Servicio Sync System

echo ========================================
echo   DESINSTALAR SERVICIO SYNC SYSTEM
echo ========================================
echo.

REM [1/4] Verificar administrador
echo [1/4] Verificando permisos de administrador...
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Este script requiere permisos de administrador
    echo.
    echo Pasos:
    echo   1. Click derecho en este archivo
    echo   2. Seleccionar "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)
echo Administrador: OK

echo.
REM [2/4] Verificar NSSM
echo [2/4] Verificando NSSM...
if not exist "nssm.exe" (
    echo ERROR: No se encontro nssm.exe
    echo.
    echo Este script debe estar en la misma carpeta que nssm.exe
    pause
    exit /b 1
)
echo NSSM encontrado

echo.
REM [3/4] Verificar que existe el servicio
echo [3/4] Verificando servicio...
sc query SyncSystemService >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo El servicio "SyncSystemService" no esta instalado
    echo No hay nada que desinstalar
    echo.
    pause
    exit /b 0
)
echo Servicio encontrado: SyncSystemService

echo.
REM [4/4] Desinstalar servicio
echo [4/4] Desinstalando servicio...
echo.

REM Mostrar estado actual
sc query SyncSystemService
echo.

REM Preguntar confirmacion
echo Esto eliminara el servicio "SyncSystemService"
set /p confirm="Estas seguro? (s/n): "
if /i not "!confirm!"=="s" (
    echo Desinstalacion cancelada
    pause
    exit /b 0
)

echo.
echo Deteniendo servicio...
nssm stop SyncSystemService 2>nul
timeout /t 2 >nul

echo Eliminando servicio...
nssm remove SyncSystemService confirm

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo eliminar el servicio
    pause
    exit /b 1
)

echo.
echo ========================================
echo   SERVICIO DESINSTALADO
echo ========================================
echo.
echo El servicio "SyncSystemService" ha sido eliminado
echo El ejecutable sync_system.exe NO fue eliminado
echo.
echo Puedes reinstalar el servicio ejecutando:
echo   INSTALAR_SERVICIO.bat
echo.
pause
