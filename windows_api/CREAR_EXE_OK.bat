@echo off
title Crear Ejecutable COMPLETO - Sync API System

cd /d "%~dp0"

echo ========================================
echo   CREAR EJECUTABLE .EXE - METODO COMPLETO
echo   Sync API System
echo ========================================
echo.
echo Este metodo crea el .exe incluyendo todos los modulos explícitamente
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    pause
    exit /b 1
)

REM Verificar PyInstaller
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

echo Verificando archivos necesarios...
echo.

if not exist "sync_system_api.py" (
    echo ERROR: No se encuentra sync_system_api.py
    pause
    exit /b 1
)

if not exist "api_client" (
    echo ERROR: No se encuentra la carpeta api_client
    pause
    exit /b 1
)

if not exist "sync" (
    echo ERROR: No se encuentra la carpeta sync
    pause
    exit /b 1
)

echo ✅ Todos los archivos necesarios existen
echo.

echo Creando ejecutable con metodo completo...
echo.

python build_exe_completo.py

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
echo Para probar:
echo   EJECUTAR_EXE_DEBUG.bat
echo.
pause
