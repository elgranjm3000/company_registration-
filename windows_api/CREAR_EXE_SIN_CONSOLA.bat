@echo off
title Crear Ejecutable Sin Consola - Sync API System

cd /d "%~dp0"

echo ========================================
echo   CREAR EJECUTABLE .EXE (SIN CONSOLA)
echo   Sync API System
echo ========================================
echo.
echo Este ejecutable NO mostrara la consola
echo (modo produccion - sin ventana negra)
echo.

REM Verificar dependencias
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo Creando ejecutable SIN consola...
echo.

pyinstaller --name=SyncAPISystem ^
    --onedir ^
    --windowed ^
    --noconsole ^
    --clean ^
    --noconfirm ^
    --log-level=INFO ^
    --add-data="config_encryption.py;." ^
    --add-data="api_client;base" ^
    --add-data="sync;base" ^
    --hidden-import=psycopg2 ^
    --hidden-import=requests ^
    --hidden-import=pystray ^
    --hidden-import=PIL ^
    --hidden-import=tkinter ^
    --hidden-import=cryptography ^
    --hidden-import=config_encryption ^
    --hidden-import=api_client ^
    --hidden-import=sync ^
    --collect-all=psycopg2 ^
    --collect-all=pystray ^
    --collect-all=Pillow ^
    sync_system_api.spec

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
echo NOTA: Sin consola - modo produccion
echo.
pause
