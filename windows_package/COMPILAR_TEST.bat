@echo off
echo ========================================
echo COMPILANDO TEST SIMPLE
echo ========================================
echo.

echo Este creara un ejecutable de PRUEBA
echo SIN dependencias de bases de datos
echo.

python -m PyInstaller --onefile --windowed --name="test_sync" sync_system_test.py

echo.
echo ========================================
echo LISTO!
echo ========================================
echo.
echo Ejecuta: dist\test_sync.exe
echo Si esto funciona, el problema es con las dependencias
echo.
pause
