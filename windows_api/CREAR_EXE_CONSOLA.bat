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

REM Verificar si existe el spec, si no, crearlo
if not exist sync_system_api.spec (
    echo.
    echo [!] Archivo sync_system_api.spec no encontrado
    echo [*] Creando archivo spec automaticamente...
    echo.

    pyinstaller --name SyncAPISystem ^
        --onefile ^
        --console ^
        --add-data "api_client;api_client" ^
        --add-data "sync;sync" ^
        --add-data "config_encryption.py;." ^
        --hidden-import "api_client" ^
        --hidden-import "api_client.base" ^
        --hidden-import "api_client.categories" ^
        --hidden-import "api_client.company" ^
        --hidden-import "api_client.customers" ^
        --hidden-import "api_client.products" ^
        --hidden-import "api_client.quotes" ^
        --hidden-import "api_client.sellers" ^
        --hidden-import "sync" ^
        --hidden-import "sync.base" ^
        --hidden-import "sync.categories_sync" ^
        --hidden-import "sync.customers_sync" ^
        --hidden-import "sync.products_sync" ^
        --hidden-import "sync.quotes_sync" ^
        --hidden-import "sync.sellers_sync" ^
        --hidden-import "config_encryption" ^
        --hidden-import "psycopg2" ^
        --hidden-import "psycopg2.extensions" ^
        --hidden-import "psycopg2.extras" ^
        --hidden-import "psycopg2.pool" ^
        --hidden-import "pystray" ^
        --hidden-import "pystray._win32" ^
        --hidden-import "PIL" ^
        --hidden-import "PIL.Image" ^
        --hidden-import "requests" ^
        --hidden-import "cryptography" ^
        --hidden-import "cryptography.fernet" ^
        --hidden-import "tkinter" ^
        --collect-all "psycopg2" ^
        --collect-all "PIL" ^
        sync_system_api.py

    if %errorlevel% neq 0 (
        echo ERROR: La compilacion fallo
        pause
        exit /b 1
    )

    echo.
    echo ========================================
    echo   ¡EJECUTABLE CREADO!
    echo ========================================
    echo.
    echo Ubicacion: dist\
    echo.
    pause
    exit /b 0
)

echo Creando ejecutable con consola...
echo.

pyinstaller --clean sync_system_api.spec

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
echo Ubicacion: dist\SyncAPISystem\
echo.
pause
