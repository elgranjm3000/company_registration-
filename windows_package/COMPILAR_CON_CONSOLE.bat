@echo off
echo ========================================
echo COMPILANDO CON CONSOLE (PARA VER ERRORES)
echo ========================================
echo.

echo Paso 1: Instalando PyInstaller...
python -m pip install pyinstaller pywin32

echo.
echo Paso 2: Compilando CON CONSOLE...
python -m PyInstaller --onefile --add-data "smart_sync_complete.py;." --hidden-import=psycopg2 --hidden-import=mysql.connector --hidden-import=dotenv --hidden-import=tkinter --name="sync_system_debug" sync_system.py

echo.
echo ========================================
echo LISTO!
echo ========================================
echo.
echo El archivo esta en: dist\sync_system_debug.exe
echo.
echo ESTA VERSION TIENE CONSOLA - Podras ver errores
echo.
pause
