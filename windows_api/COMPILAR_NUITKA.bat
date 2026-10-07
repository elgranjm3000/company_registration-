@echo off
echo ============================================================
echo  COMPILACION CON NUITKA - SyncAPISystem
echo ============================================================
echo.

cd /d "%~dp0"

echo Compilando con Nuitka (esto tarda varios minutos)...
echo.

nuitka ^
  --standalone ^
  --onefile ^
  --windows-console-mode=disable ^
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
  --include-data-files=logo.ico=logo.ico ^
  --include-data-files=logo.png=logo.png ^
  --windows-icon-from-ico=logo.ico ^
  --output-filename=SyncAPISystem.exe ^
  --output-dir=dist_nuitka ^
  --assume-yes-for-downloads ^
  sync_system_api.py

echo.
echo ============================================================
echo  Terminado. Revisa la carpeta dist_nuitka
echo ============================================================
pause
