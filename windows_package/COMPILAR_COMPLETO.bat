@echo off
title Compilar Sync System - Version Completa

cd /d "%~dp0"

echo ========================================
echo   COMPILACION COMPLETA DE SYNC SYSTEM
echo ========================================
echo.

REM Paso 1: Instalar TODAS las dependencias necesarias
echo [1/5] Instalando dependencias de Python...
echo.

pip install pyinstaller psycopg2-binary pymysql pystray Pillow bcrypt win10toast 2>nul
if %errorlevel% neq 0 (
    echo ERROR instalando dependencias
    pause
    exit /b 1
)

echo Dependencias instaladas correctamente
echo.

REM Paso 2: Verificar que los archivos necesarios existen
echo [2/5] Verificando archivos...
echo.

if not exist "sync_system.py" (
    echo ERROR: No existe sync_system.py
    pause
    exit /b 1
)

if not exist "smart_sync_complete.py" (
    echo ERROR: No existe smart_sync_complete.py
    pause
    exit /b 1
)

if not exist "smart_sellers_sync_module.py" (
    echo ERROR: No existe smart_sellers_sync_module.py
    pause
    exit /b 1
)

echo Todos los archivos necesarios existen
echo.

REM Paso 3: Limpiar builds anteriores
echo [3/5] Limpiando compilaciones anteriores...
echo.

if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

echo Limpieza completada
echo.

REM Paso 4: Compilar
echo [4/5] Compilando ejecutable...
echo Esto tomara varios minutos...
echo.

python build_exe.py

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo   ERROR: Fallo en la compilacion
    echo ========================================
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ¡COMPILACION EXITOSA!
echo ========================================
echo.

REM Paso 5: Verificar resultado
echo [5/5] Verificando resultado...
echo.

if exist "dist\SyncSystem\sync_system.exe" (
    echo Ejecutable creado correctamente
    echo.
    echo Ubicacion: dist\SyncSystem\sync_system.exe
    echo.
    echo Para ejecutar:
    echo   - Modo Manager (ventana con contadores):
    echo     dist\SyncSystem\sync_system.exe --mode manager
    echo.
    echo   - Modo Tray (icono en barra tareas):
    echo     dist\SyncSystem\sync_system.exe --mode tray
    echo.
    echo   - Modo Configuracion:
    echo     dist\SyncSystem\sync_system.exe --mode config
    echo.

    REM Preguntar si quiere ejecutar ahora
    set /p ejecutar="¿Deseas ejecutar el .exe ahora en modo manager? (s/n): "
    if /i "%ejecutar%"=="s" (
        echo.
        echo Ejecutando en modo manager...
        cd dist\SyncSystem
        start sync_system.exe --mode manager
        cd ..\..
    )
) else (
    echo ERROR: No se encontro el ejecutable
    echo Deberia estar en: dist\SyncSystem\sync_system.exe
)

echo.
pause
