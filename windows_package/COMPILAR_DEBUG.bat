@echo off
title Compilar Sync System - CON CONSOLA (DEBUG)

cd /d "%~dp0"

echo ========================================
echo   COMPILACION CON CONSOLA (DEBUG)
echo ========================================
echo.
echo Este script crea el .exe CON consola visible
echo Sirve para ver errores que no se muestran
echo en modo SIN CONSOLA
echo.
echo ADVERTENCIA: El .exe mostrara una terminal
echo            junto con la ventana GUI
echo.
pause

REM Instalar dependencias
echo [1/3] Instalando dependencias...
pip install pyinstaller psycopg2-binary pymysql pystray Pillow bcrypt win10toast cryptography 2>nul

REM Limpiar builds anteriores
echo [2/3] Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

REM Compilar CON consola
echo [3/3] Compilando con consola...
python -c "
import PyInstaller.__main__

pyinstaller_opts = [
    'sync_system.py',
    '--name=SyncSystem_DEBUG',
    '--onedir',
    '--console',  # <-- CONSOLA VISIBLE
    '--add-data=smart_sync_complete.py;.',
    '--add-data=smart_sellers_sync_module.py;.',
    '--add-data=config_encryption.py;.',
    '--add-data=mysql_error_logger.py;.',
    '--clean',
    '--noconfirm',
    '--hidden-import=pymysql',
    '--hidden-import=psycopg2',
    '--hidden-import=pystray',
    '--hidden-import=PIL',
    '--hidden-import=win10toast',
    '--hidden-import=tkinter',
    '--hidden-import=bcrypt',
    '--hidden-import=config_encryption',
    '--hidden-import=cryptography',
    '--hidden-import=mysql_error_logger',
    '--collect-all=psycopg2',
    '--collect-all=pystray',
    '--collect-all=Pillow',
]

print('Ejecutando PyInstaller con consola...')
PyInstaller.__main__.run(pyinstaller_opts)
"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Fallo en la compilacion
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡COMPILACION EXITOSA!
echo ========================================
echo.
echo El .exe se creo CON CONSOLA para DEBUG
echo.
echo Ubicacion: dist\SyncSystem_DEBUG\sync_system_debug.exe
echo.
echo INSTRUCCIONES:
echo   1. Ejecuta: dist\SyncSystem_DEBUG\sync_system_debug.exe --mode config
echo   2. Ingresa los datos
echo   3. Click en GUARDAR
echo   4. MIRA LA CONSOLA - aparecera el error
echo.
echo El error te dira que esta fallando
echo.
pause
