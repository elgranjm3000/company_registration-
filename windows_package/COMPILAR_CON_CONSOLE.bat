@echo off
echo ========================================
echo COMPILANDO CON CONSOLE (PARA VER ERRORES)
echo ========================================
echo.

echo Paso 1: Instalando dependencias...
python -m pip install pyinstaller pywin32 psycopg2-binary mysql-connector-python pillow bcrypt

echo.
echo Paso 2: Compilando CON CONSOLE (puede tardar 5-10 minutos)...
python -m PyInstaller --onefile ^
    --add-data "smart_sync_complete.py;." ^
    --hidden-import=psycopg2 ^
    --hidden-import=psycopg2.extensions ^
    --hidden-import=mysql.connector ^
    --hidden-import=dotenv ^
    --hidden-import=tkinter ^
    --hidden-import=tkinter.ttk ^
    --hidden-import=tkinter.scrolledtext ^
    --hidden-import=pil ^
    --hidden-import=bcrypt ^
    --collect-all psycopg2 ^
    --collect-all mysql ^
    --collect-all pillow ^
    --name="sync_system_debug" ^
    sync_system.py

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
