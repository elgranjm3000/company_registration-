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

echo Creando ejecutable con consola...
echo.

REM Limpiar build anterior
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

pyinstaller --name SyncAPISystem ^
	--onefile ^
	--console ^
	--clean ^
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
	--hidden-import "pystray._appindicator" ^
	--hidden-import "pystray._darwin" ^
	--hidden-import "pystray._util" ^
	--hidden-import "pystray._win32" ^
	--hidden-import "PIL" ^
	--hidden-import "PIL.Image" ^
	--hidden-import "PIL.ImageDraw" ^
	--hidden-import "PIL.ImageFont" ^
	--hidden-import "requests" ^
	--hidden-import "requests.adapters" ^
	--hidden-import "requests.auth" ^
	--hidden-import "requests.models" ^
	--hidden-import "requests.sessions" ^
	--hidden-import "urllib3" ^
	--hidden-import "cryptography" ^
	--hidden-import "cryptography.fernet" ^
	--hidden-import "cryptography.hazmat" ^
	--hidden-import "cryptography.hazmat.primitives" ^
	--hidden-import "cryptography.hazmat.backends" ^
	--hidden-import "tkinter" ^
	--hidden-import "tkinter.ttk" ^
	--hidden-import "tkinter.scrolledtext" ^
	--hidden-import "tkinter.messagebox" ^
	--hidden-import "tkinter.filedialog" ^
	--hidden-import "threading" ^
	--hidden-import "queue" ^
	--hidden-import "json" ^
	--hidden-import "datetime" ^
	--hidden-import "os" ^
	--hidden-import "sys" ^
	--hidden-import "time" ^
	--hidden-import "logging" ^
	--hidden-import "hashlib" ^
	--hidden-import "base64" ^
	--hidden-import "winreg" ^
	--collect-all "psycopg2" ^
	--collect-all "PIL" ^
	sync_system_api.py

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
pause
