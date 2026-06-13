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

pip install pyinstaller psycopg2-binary pymysql pystray Pillow bcrypt win10toast pywin32 cryptography requests PySide6 2>nul
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

if not exist "config_encryption.py" (
    echo ERROR: No existe config_encryption.py
    echo.
    echo ⚠️ CRITICO: Sin config_encryption.py las contrasenas quedaran expuestas
    pause
    exit /b 1
)

if not exist "mysql_error_logger.py" (
    echo ERROR: No existe mysql_error_logger.py
    echo.
    echo ⚠️ ADVERTENCIA: Sin mysql_error_logger.py no se podran debuggear errores de MySQL
    pause
    exit /b 1
)

echo Todos los archivos necesarios existen
echo.
echo ✅ config_encryption.py encontrado - Las contrasenas seran encriptadas
echo ✅ mysql_error_logger.py encontrado - Los errores de MySQL se guardaran en logs
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
    echo ⚠️ IMPORTANTE - Encriptacion de contrasenas:
    echo   - El .exe incluye config_encryption.py
    echo   - Las contrasenas se guardaran con el prefijo 'enc:'
    echo   - Verifica que sync_config.json tenga 'enc:' en las contrasenas
    echo.
    echo 📝 Logging de errores:
    echo   - Los errores de MySQL se guardan en logs/mysql_errors/
    echo   - Los errores NO se muestran al usuario
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

    REM Verificar tamano del exe (debe ser grande por incluir cryptography)
    for %%A in ("dist\SyncSystem\sync_system.exe") do set size=%%~zA
    set /a sizeMB=%size%/1048576
    echo Tamaño del .exe: %sizeMB% MB
    if %sizeMB% LSS 20 (
        echo.
        echo ⚠️ ADVERTENCIA: El .exe parece pequeno (%sizeMB% MB)
        echo    Puede que no incluya todas las dependencias
        echo    Verifica que cryptography este instalado
        echo.
    )

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
