@echo off
setlocal enabledelayedexpansion
title Instalar Servicio Sync System

echo ========================================
echo   INSTALAR SERVICIO SYNC SYSTEM
echo ========================================
echo.

REM [1/6] Verificar administrador
echo [1/6] Verificando permisos de administrador...
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
REM [2/6] Verificar que existe el ejecutable
echo [2/6] Verificando ejecutable...
if not exist "dist\sync_system.exe" (
    echo ERROR: No se encontro dist\sync_system.exe
    echo.
    echo Primero debes crear el ejecutable ejecutando CREAR_EXE.bat
    echo.
    pause
    exit /b 1
)
echo Ejecutable encontrado: dist\sync_system.exe

echo.
REM [3/6] Obtener ruta completa
echo [3/6] Obteniendo rutas...
set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%SCRIPT_DIR%dist\sync_system.exe"
set "EXE_PATH=%EXE_PATH:\=/%"
echo Ruta ejecutable: %EXE_PATH%

echo.
REM [4/6] Descargar NSSM si no existe
echo [4/6] Verificando NSSM...
if not exist "nssm.exe" (
    echo NSSM no encontrado. Descargando...
    echo.
    echo Esto puede tomar unos segundos...

    REM Descargar NSSM de forma silenciosa
    powershell -Command "& {Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'nssm.zip'}" 2>nul

    if %errorlevel% neq 0 (
        echo ERROR: No se pudo descargar NSSM
        echo.
        echo Alternativa:
        echo   1. Descarga NSSM desde https://nssm.cc/download
        echo   2. Extrae nssm.exe en esta carpeta
        echo   3. Ejecuta este script nuevamente
        echo.
        pause
        exit /b 1
    )

    echo Extrayendo NSSM...
    powershell -Command "& {Expand-Archive -Path 'nssm.zip' -DestinationPath 'nssm_temp' -Force}" 2>nul

    if exist "nssm_temp\nssm-2.24\win64\nssm.exe" (
        copy "nssm_temp\nssm-2.24\win64\nssm.exe" "nssm.exe" >nul
        echo NSSM extraido correctamente
    ) else if exist "nssm_temp\nssm-2.24\win32\nssm.exe" (
        copy "nssm_temp\nssm-2.24\win32\nssm.exe" "nssm.exe" >nul
        echo NSSM extraido correctamente
    ) else (
        echo ERROR: No se pudo encontrar nssm.exe en el archivo
        pause
        exit /b 1
    )

    rm -r nssm_temp nssm.zip 2>nul
) else (
    echo NSSM encontrado
)

echo.
REM [5/6] Verificar configuracion
echo [5/6] Verificando configuracion...
if not exist "sync_config.json" (
    echo WARNING: No se encontro sync_config.json
    echo.
    echo Debes ejecutar el modo config primero:
    echo   dist\sync_system.exe --mode config
    echo.
    set /p continuar="Deseas continuar de todos modos? (s/n): "
    if /i not "!continuar!"=="s" (
        echo Instalacion cancelada
        pause
        exit /b 1
    )
)
echo Configuracion: OK

echo.
REM [6/6] Instalar servicio
echo [6/6] Instalando servicio...
echo.

REM Detener servicio si existe
sc query SyncSystemService >nul 2>&1
if %errorlevel% equ 0 (
    echo Deteniendo servicio existente...
    nssm stop SyncSystemService 2>nul
    timeout /t 2 >nul
    nssm remove SyncSystemService confirm 2>nul
)

REM Instalar con NSSM
echo Creando servicio "SyncSystemService"...
nssm install SyncSystemService "%EXE_PATH%" --mode service

if %errorlevel% neq 0 (
    echo ERROR: No se pudo instalar el servicio
    pause
    exit /b 1
)

REM Configurar servicio para inicio automático
echo Configurando servicio...
nssm set SyncSystemService Start SERVICE_AUTO_START
nssm set SyncSystemService AppDirectory "%SCRIPT_DIR%dist"
nssm set SyncSystemService DisplayName "Sync System - Sincronizacion Automatica"
nssm set SyncSystemService Description "Sincronizacion automatica entre PostgreSQL y MySQL"

REM Configurar reinicio automático si falla
nssm set SyncSystemService AppThrottle 1500
nssm set SyncSystemService AppExit Default Restart
nssm set SyncSystemService AppRestartDelay 10000

echo.
echo ========================================
echo   SERVICIO INSTALADO EXITOSAMENTE
echo ========================================
echo.
echo Nombre del servicio: SyncSystemService
echo Tipo de inicio: Automatico
echo Ejecutable: %EXE_PATH%
echo.
echo El servicio se iniciara automaticamente al:
echo   - Prender la computadora
echo   - Reiniciar Windows
echo.
echo COMANDOS UTILES:
echo   Iniciar servicio:  nssm start SyncSystemService
echo   Detener servicio:   nssm stop SyncSystemService
echo   Ver estado:         sc query SyncSystemService
echo   Ver logs:           type sync_system.log
echo.
echo Para desinstalar, ejecuta: DESINSTALAR_SERVICIO.bat
echo.

REM Iniciar el servicio ahora
set /p iniciar="Deseas iniciar el servicio ahora? (s/n): "
if /i "!iniciar!"=="s" (
    echo.
    echo Iniciando servicio...
    nssm start SyncSystemService
    timeout /t 3 >nul

    sc query SyncSystemService | find "RUNNING" >nul
    if %errorlevel% equ 0 (
        echo.
        echo ========================================
        echo   SERVICIO INICIADO Y FUNCIONANDO
        echo ========================================
        echo.
        echo El servicio esta corriendo en segundo plano.
        echo Puedes cerrar esta ventana.
        echo.
        echo Para verificar estado: sc query SyncSystemService
    ) else (
        echo.
        echo WARNING: El servicio se instaló pero no se pudo iniciar
        echo Revisa sync_system.log para ver errores
    )
)

echo.
pause
