@echo off
title Verificar Dependencias

cd /d "%~dp0"

echo ========================================
echo   VERIFICANDO DEPENDENCIAS
echo ========================================
echo.

echo Verificando Python...
python --version
echo.

echo Verificando PyInstaller...
pip show pyinstaller
echo.

echo Verificando bcrypt...
pip show bcrypt
echo.

echo Verificando otras dependencias...
pip show pymysql
pip show psycopg2-binary
pip show pystray
pip show Pillow
pip show win10toast
pip show pywin32
echo.

echo ========================================
echo   VERIFICANDO ARCHIVOS
echo ========================================
echo.

if exist "sync_system.py" (
    echo [OK] sync_system.py
) else (
    echo [FALTA] sync_system.py
)

if exist "smart_sync_complete.py" (
    echo [OK] smart_sync_complete.py
) else (
    echo [FALTA] smart_sync_complete.py
)

if exist "smart_sellers_sync_module.py" (
    echo [OK] smart_sellers_sync_module.py
) else (
    echo [FALTA] smart_sellers_sync_module.py
)

if exist "build_exe.py" (
    echo [OK] build_exe.py
) else (
    echo [FALTA] build_exe.py
)

echo.
pause
