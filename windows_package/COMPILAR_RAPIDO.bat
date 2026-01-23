@echo off
echo ========================================
echo COMPILANDO EJECUTABLE UNICO
echo ========================================
echo.

echo Verificando Python...
python --version
if errorlevel 1 (
    echo ERROR: Python no esta instalado o no esta en el PATH
    echo Por favor instala Python 3.8+ y agrega al PATH
    pause
    exit /b 1
)

echo.
echo Paso 1: Instalando PyInstaller...
python -m pip install pyinstaller pywin32

echo.
echo Paso 2: Compilando (puede tardar 5-10 minutos)...
python -m PyInstaller --onefile --noconsole ^
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
    --name="sync_system" ^
    sync_system.py

if errorlevel 1 (
    echo.
    echo ERROR: Fallo la compilacion
    pause
    exit /b 1
)

echo.
echo ========================================
echo LISTO!
echo ========================================
echo.
echo El archivo esta en: dist\sync_system.exe
echo.
pause
