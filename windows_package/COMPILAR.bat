@echo off
echo ========================================
echo COMPILANDO EJECUTABLE
echo ========================================
echo.

echo [1/4] Verificando Python...
python --version
if errorlevel 1 (
    echo ERROR: Python no encontrado
    pause
    exit /b 1
)

echo.
echo [2/4] Desinstalando PyInstaller antiguo...
pip uninstall pyinstaller -y >nul 2>&1

echo.
echo [3/4] Instalando PyInstaller 5.13.2...
pip install pyinstaller==5.13.2

echo.
echo [4/4] Compilando (puede tardar 3-5 minutos)...
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
