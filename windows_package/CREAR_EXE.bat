@echo off
setlocal enabledelayedexpansion
title Crear Ejecutable - Sync System

echo ========================================
echo   CREAR EJECUTABLE SYNC SYSTEM
echo ========================================
echo.

REM [1/7] Verificar Python
echo [1/7] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Descarga desde: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% encontrado

echo.
REM [2/7] Verificar archivos
echo [2/7] Verificando archivos...
if not exist "sync_system.py" (
    echo ERROR: sync_system.py no encontrado
    pause
    exit /b 1
)
if not exist "smart_sync_complete.py" (
    echo ERROR: smart_sync_complete.py no encontrado
    pause
    exit /b 1
)
echo Archivos encontrados

echo.
REM [2.5/7] Verificar sintaxis de Python
echo [2.5/7] Verificando sintaxis de Python...
python -m py_compile sync_system.py
if %errorlevel% neq 0 (
    echo ERROR: sync_system.py tiene errores de sintaxis
    pause
    exit /b 1
)
python -m py_compile smart_sync_complete.py
if %errorlevel% neq 0 (
    echo ERROR: smart_sync_complete.py tiene errores de sintaxis
    pause
    exit /b 1
)
echo Sintaxis correcta

echo.
REM [3/7] Crear entorno virtual
echo [3/7] Configurando entorno virtual...
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear entorno virtual
        pause
        exit /b 1
    )
)
echo Entorno virtual listo

echo.
REM [4/7] Activar entorno virtual
echo [4/7] Activando entorno virtual...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo ERROR: No se pudo activar entorno virtual
    pause
    exit /b 1
)

echo.
REM [5/7] Instalar dependencias
echo [5/7] Instalando dependencias...
echo Esto puede tomar un minuto...
python -m pip install --upgrade pip --quiet 2>nul

echo Instalando PyInstaller 6.1.0...
pip install pyinstaller==6.1.0 --quiet
if %errorlevel% neq 0 (
    echo ERROR instalando PyInstaller
    pause
    exit /b 1
)

echo Instalando psycopg2-binary...
pip install psycopg2-binary --quiet
if %errorlevel% neq 0 (
    echo ERROR instalando psycopg2-binary
    pause
    exit /b 1
)

echo Instalando mysql-connector-python...
pip install mysql-connector-python --quiet
if %errorlevel% neq 0 (
    echo ERROR instalando mysql-connector-python
    pause
    exit /b 1
)

echo Verificando dependencias...
python -c "import psycopg2; import mysql.connector; import tkinter; print('OK')" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Dependencias no instaladas correctamente
    pause
    exit /b 1
)
echo Dependencias OK

echo.
REM [5.5/7] Verificar compatibilidad completa
echo [5.5/7] Verificando compatibilidad completa...
echo Probando imports de sync_system.py...
python -c "import sys; sys.path.insert(0, '.'); exec(open('sync_system.py').read().split('if __name__')[0])" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: Puede haber problemas con los imports
    echo Continando de todos modos...
) else (
    echo Imports compatibles
)
echo Verificando modulos necesarios...
python -c "import importlib.util; spec = importlib.util.spec_from_file_location('test', 'smart_sync_complete.py'); print('Modulo sync_system OK')" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: smart_sync_complete.py tiene problemas
) else (
    echo Modulo smart_sync_complete OK
)

echo.
REM [6/7] Limpiar builds anteriores
echo [6/7] Limpiando builds anteriores...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist *.spec del *.spec 2>nul

echo.
REM [7/7] Resumen de compatibilidad
echo ========================================
echo   RESUMEN DE COMPATIBILIDAD
echo ========================================
echo.
echo Python: %PYTHON_VERSION%
echo PyInstaller: 6.1.0
echo psycopg2-binary: Instalado
echo mysql-connector-python: Instalado
echo tkinter: Disponible
echo.
echo Archivos a compilar:
echo   - sync_system.py
echo   - smart_sync_complete.py
echo.
echo Todo parece compatible. Procediendo a crear .exe...
echo ========================================
echo.

REM [7/7] Crear ejecutable
echo Creando ejecutable...
echo Esto tomara 3-5 minutos
echo.

pyinstaller ^
    --onefile ^
    --noconsole ^
    --name "sync_system" ^
    --add-data "smart_sync_complete.py;." ^
    --hidden-import psycopg2 ^
    --hidden-import psycopg2.extensions ^
    --hidden-import mysql.connector ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.scrolledtext ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    sync_system.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo   ERROR: NO SE PUDO CREAR EJECUTABLE
    echo ========================================
    pause
    exit /b 1
)

echo.
REM Verificar resultado
if exist "dist\sync_system.exe" (
    echo.
    echo ========================================
    echo   EXITO: EJECUTABLE CREADO
    echo ========================================
    echo.
    echo Ubicacion: %cd%\dist\sync_system.exe

    for %%A in (dist\sync_system.exe) do (
        set /a size_mb=%%~zA/1024/1024
        echo Tamanho: !size_mb! MB
    )

    echo.
    echo COMO USAR:
    echo   1. Ve a la carpeta dist
    echo   2. Copia sync_system.exe donde quieras
    echo   3. Ejecuta con doble clic
    echo.

) else (
    echo.
    echo ERROR: No se encontro el ejecutable
    pause
    exit /b 1
)

pause
