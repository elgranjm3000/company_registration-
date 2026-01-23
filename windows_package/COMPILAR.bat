@echo off
echo ========================================
echo COMPILANDO - VERSION SIMPLE
echo ========================================
echo.

pip install pyinstaller

python -m PyInstaller --onefile --noconsole --add-data "smart_sync_complete.py;." --name="sync_system" sync_system.py

echo.
echo LISTO! El archivo esta en: dist\sync_system.exe
pause
