@echo off
echo ========================================
echo COMPILANDO EJECUTABLE
echo ========================================
echo.

echo [1/3] Verificando Python...
python --version
if errorlevel 1 (
    echo ERROR: Python no encontrado
    pause
    exit /b 1
)

echo.
echo [2/3] Instalando PyInstaller 5.13.2 (compatible con Python 3.10)...
python -m pip install pyinstaller==5.13.2 --quiet

echo.
echo [3/3] Compilando (puede tardar 3-5 minutos)...
python -m PyInstaller --onefile --noconsole --add-data "smart_sync_complete.py;." --name="sync_system" sync_system.py

if errorlevel 1 (
    echo.
    echo ERROR COMPILANDO
    pause
    exit /b 1
)

echo.
echo ========================================
echo EXITO!
echo ========================================
echo.
echo El ejecutable esta en: dist\sync_system.exe
echo.
pause
