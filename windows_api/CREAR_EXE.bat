@echo off
title Crear Ejecutable - Sync API System

cd /d "%~dp0"

echo ========================================
echo   CREAR EJECUTABLE .EXE
echo   Sync API System
echo ========================================
echo.

REM [1/4] Verificar Python
echo [1/4] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    pause
    exit /b 1
)
echo OK: Python instalado
python --version
echo.

REM [2/4] Verificar PyInstaller
echo [2/4] Verificando PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller no esta instalado
    echo Instalando PyInstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo instalar PyInstaller
        pause
        exit /b 1
    )
)
echo OK: PyInstaller instalado
echo.

REM [3/4] Verificar archivos necesarios
echo [3/4] Verificando archivos necesarios...
if not exist "sync_system_api.py" (
    echo ERROR: No se encuentra sync_system_api.py
    pause
    exit /b 1
)
echo OK: sync_system_api.py encontrado

if not exist "api_client\base.py" (
    echo ERROR: No se encuentra api_client\base.py
    pause
    exit /b 1
)
echo OK: api_client encontrado

if not exist "sync\base.py" (
    echo ERROR: No se encuentra sync\base.py
    pause
    exit /b 1
)
echo OK: sync encontrado
echo.

REM [4/4] Crear ejecutable
echo [4/4] Creando ejecutable...
echo Esto puede tomar varios minutos...
echo.

python build_exe.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: La compilacion fallo
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡EJECUTABLE CREADO EXITOSAMENTE!
echo ========================================
echo.
echo Ubicacion: dist\SyncAPISystem\
echo.
echo Para entregar al cliente, copia:
echo   - Todo el contenido de dist\SyncAPISystem\
echo   - Los archivos .bat (CONFIGURAR.bat, MANAGER.bat, etc)
echo   - README.md e INICIO_RAPIDO.md
echo.
pause
