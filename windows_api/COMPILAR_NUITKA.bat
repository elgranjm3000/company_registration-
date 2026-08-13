@echo off
echo ============================================================
echo  COMPILACION CON NUITKA - SyncAPISystem
echo  (Codigo compilado a C = protegido + sin error multi-instancia)
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Verificando Nuitka...
nuitka --version
if errorlevel 1 (
    echo   ERROR: Nuitka no esta instalado.
    echo   Ejecuta: pip install nuitka
    pause
    exit /b 1
)
echo   OK - Nuitka instalado
echo.

echo [2/3] Compilando (esto tarda varios minutos)...
echo.

nuitka ^
  --standalone ^
  --onefile ^
  --windows-disable-console ^
  --enable-plugin=tk-inter ^
  --enable-plugin=pyside6 ^
  --include-package=api_client ^
  --include-package=sync ^
  --include-module=config_encryption ^
  --include-package=psycopg2 ^
  --include-package=requests ^
  --include-package=urllib3 ^
  --include-package=certifi ^
  --include-package=pystray ^
  --include-package=PIL ^
  --include-package=win10toast ^
  --include-package=win32api ^
  --include-package=win32con ^
  --include-package=win32gui ^
  --include-package=win32process ^
  --include-package=pythoncom ^
  --include-package=pywintypes ^
  --include-package=cryptography ^
  --include-package=cffi ^
  --include-package=bcrypt ^
  --include-data-files=logo.ico=. ^
  --include-data-files=logo.png=. ^
  --windows-icon-from-ico=logo.ico ^
  --output-filename=SyncAPISystem.exe ^
  --output-dir=dist_nuitka ^
  --company-name="Chrystal" ^
  --product-name="SyncAPI System" ^
  --file-version=1.0.0 ^
  --product-version=1.0.0 ^
  --assume-yes-for-downloads ^
  sync_system_api.py

if errorlevel 1 (
    echo.
    echo [ERROR] La compilacion fallo.
    echo   Revisa los mensajes de arriba.
    echo.
    echo   Causas comunes:
    echo   - Falta compilador C (MSVC o MinGW)
    echo   - Falta algun modulo
    echo.
    pause
    exit /b 1
)

echo.
echo [3/3] Compilacion exitosa.
echo.
echo   El ejecutable esta en:
echo   dist_nuitka\SyncAPISystem.exe
echo.
echo ============================================================
echo  IMPORTANTE: Distribuye SOLO el .exe (un solo archivo)
echo  Tu codigo esta compilado a C (no recuperable)
echo ============================================================
pause
