@echo off
setlocal enabledelayedexpansion
title Compilador Sync System

echo ========================================
echo   CREACION DE EJECUTABLE SYNC SYSTEM
echo ========================================
echo.

REM [1/9] Verificar Python
echo [1/9] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% encontrado!

echo.
REM [2/9] Verificar archivos
echo [2/9] Verificando archivos...
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
REM [3/9] Crear requirements
echo [3/9] Creando requirements.txt...
echo pyinstaller==5.13.2> requirements.txt
echo psycopg2-binary==2.9.7>> requirements.txt
echo mysql-connector-python==8.2.0>> requirements.txt

echo.
REM [4/9] Limpiar anteriores
echo [4/9] Limpiando builds anteriores...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist *.spec del *.spec 2>nul

echo.
REM [5/9] Instalar dependencias
echo [5/9] Instalando dependencias...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ERROR instalando dependencias
    pause
    exit /b 1
)

echo.
REM [6/9] Verificar dependencias
echo [6/9] Verificando dependencias...
python -c "import psycopg2; import mysql.connector; import tkinter; print('OK')" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Dependencias no instaladas correctamente
    pause
    exit /b 1
)
echo Dependencias OK

echo.
REM [7/9] Crear ejecutable
echo [7/9] Creando ejecutable...
echo.
echo Esto puede tomar 3-5 minutos...
echo Por favor espera...
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
REM [8/9] Verificar creacion
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
    echo Para usarlo:
    echo   1. Copia sync_system.exe a donde quieras
    echo   2. Ejecuta con doble clic
    echo   3. Configura en primera ejecucion
    echo.
    echo PROCESO COMPLETADO!

) else (
    echo.
    echo ERROR: No se encontro el ejecutable
    pause
    exit /b 1
)

pause
