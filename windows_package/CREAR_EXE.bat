@echo off
title Crear Ejecutable Sync System

cd /d "%~dp0"

echo ========================================
echo   CREAR EJECUTABLE .EXE
echo ========================================
echo.

REM [1/3] Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    pause
    exit /b 1
)

echo Python encontrado
python --version
echo.

REM [2/3] Instalar PyInstaller si no existe
echo Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller no encontrado. Instalando...
    pip install pyinstaller
) else (
    echo PyInstaller ya esta instalado
)
echo.

REM [3/3] Crear ejecutable
echo Iniciando creacion del ejecutable...
echo Esto puede tomar varios minutos...
echo.

python build_exe.py

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   ¡EJECUTABLE CREADO EXITOSAMENTE!
    echo ========================================
    echo.
    echo Ubicacion: dist\SyncSystem\sync_system.exe
    echo.
    echo Para ejecutar:
    echo   dist\SyncSystem\sync_system.exe --mode manager     (Ventana GUI con contadores)
    echo   dist\SyncSystem\sync_system.exe --mode tray        (Icono en barra de tareas + auto-inicio)
    echo.

    REM Preguntar si quiere ejecutar ahora
    set /p ejecutar="¿Deseas ejecutar el .exe ahora? (s/n): "
    if /i "%ejecutar%"=="s" (
        echo.
        echo Ejecutando...
        cd dist\SyncSystem
        start sync_system.exe --mode manager
        cd ..\..
    )
) else (
    echo.
    echo ========================================
    echo   ERROR: No se pudo crear el .exe
    echo ========================================
    echo.
    echo Verifica que todas las dependencias esten instaladas:
    echo   pip install psycopg2-binary pymysql pystray Pillow pyinstaller win10toast pywin32
    echo.
)

pause
