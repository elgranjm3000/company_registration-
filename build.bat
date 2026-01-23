@echo off
REM ====================================================================
REM SCRIPT: Compilar a .exe con PyInstaller
REM AUTOR: Sistema de Sincronización PostgreSQL → MySQL
REM FECHA: 2025-01-22
REM ====================================================================

echo ========================================
echo COMPILANDO SINCRONIZADOR A .EXE
echo ========================================
echo.

REM Verificar que PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller no está instalado. Instalando...
    pip install pyinstaller pywin32
)

echo.
echo [1/3] Compilando servicio Windows...
pyinstaller --onefile --noconsole ^
    --hidden-import=win32timezone ^
    --hidden-import=win32service ^
    --hidden-import=win32serviceutil ^
    --name="PostgreSQLMySQLSyncService" ^
    --icon=assets/icon.ico ^
    sync_service.py

if errorlevel 1 (
    echo ERROR compilando servicio
    pause
    exit /b 1
)

echo.
echo [2/3] Compilando interfaz de administración...
pyinstaller --onefile --windowed ^
    --name="SyncManager" ^
    --icon=assets/icon.ico ^
    sync_manager.py

if errorlevel 1 (
    echo ERROR compilando interfaz
    pause
    exit /b 1
)

echo.
echo [3/3] Compilacion completada!
echo.
echo Archivos generados:
echo - dist\PostgreSQLMySQLSyncService.exe (Servicio Windows)
echo - dist\SyncManager.exe (Interfaz de administracion)
echo.
echo Siguientes pasos:
echo 1. Copiar dist\PostgreSQLMySQLSyncService.exe a la carpeta de instalacion
echo 2. Copiar dist\SyncManager.exe a la carpeta de instalacion
echo 3. Ejecutar create_installer.bat para crear el instalador
echo.

pause
