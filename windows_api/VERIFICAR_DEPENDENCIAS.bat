@echo off
title Sync API System - Verificar Dependencias

cd /d "%~dp0"

echo ========================================
echo   VERIFICANDO DEPENDENCIAS
echo ========================================
echo.

REM [1/3] Verificar Python
echo [1/3] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: Python no esta instalado
    echo.
    echo   Pasos:
    echo     1. Ve a https://www.python.org/downloads/
    echo     2. Descarga Python 3.8 o superior
    echo     3. IMPORTANTE: Marca "Add Python to PATH"
    echo     4. Instala
    echo.
    pause
    exit /b 1
)
echo   OK: Python instalado
python --version
echo.

REM [2/3] Verificar dependencias instaladas
echo [2/3] Verificando dependencias instaladas...
echo   - psycopg2-binary (PostgreSQL)
python -c "import psycopg2; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install psycopg2-binary

echo   - requests (HTTP Client)
python -c "import requests; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install requests

echo   - pystray (System Tray)
python -c "import pystray; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install pystray

echo   - PIL/Pillow (Iconos)
python -c "from PIL import Image; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install Pillow

echo   - tkinter (GUI)
python -c "import tkinter; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: Incluido con Python

echo   - cryptography (Encriptacion)
python -c "from cryptography.fernet import Fernet; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install cryptography

echo   - win10toast (Notificaciones Windows)
python -c "from win10toast import ToastNotifier; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install win10toast pywin32

echo   - pywin32 (Dependencia de win10toast)
python -c "import win32con; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install pywin32

echo.
echo   - PySide6 (Autenticación moderna)
python -c "import PySide6; print('     OK')" 2>nul
if %errorlevel% neq 0 echo     FALTA: pip install PySide6

echo.

REM [3/3] Intentar instalar dependencias faltantes
echo [3/3] Intentando instalar dependencias faltantes...
echo.

pip install psycopg2-binary requests pystray Pillow cryptography win10toast pywin32 PySide6 2>nul

echo.
echo ========================================
echo   VERIFICACION FINAL
echo ========================================
echo.

python -c "import psycopg2; import requests; import pystray; from PIL import Image; import tkinter; from cryptography.fernet import Fernet; from win10toast import ToastNotifier; import win32con; import PySide6; print('OK: Todas las dependencias estan instaladas')" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar todas las dependencias
    echo.
    echo Ejecuta manualmente:
    echo   pip install psycopg2-binary requests pystray Pillow cryptography win10toast pywin32
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Todas las dependencias estan instaladas correctamente
echo.
echo El sistema esta listo para usar:
echo   - CONFIGURAR.bat: Configurar el sistema por primera vez
echo   - MANAGER.bat: Abrir el administrador
echo   - EJECUTAR.bat: Sincronizar una vez
echo   - TRAY.bat: Iniciar en modo System Tray
echo.
pause
