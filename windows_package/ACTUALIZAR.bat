@echo off
echo ========================================
echo LIMPIANDO PYINSTALLER ANTIGUO
echo ========================================
echo.

pip uninstall pyinstaller -y

echo.
echo Instalando version compatible...
pip install pyinstaller==5.13.2

echo.
echo Verificando version...
python -m PyInstaller --version

echo.
echo ========================================
echo LISTO - Ahora ejecuta COMPILAR.bat
echo ========================================
echo.
pause
