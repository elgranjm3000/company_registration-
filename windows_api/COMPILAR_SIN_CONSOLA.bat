@echo off
title Compilar SIN Consola + Protección de Código

cd /d "%~dp0"

echo ========================================================================
echo   VERIFICANDO DEPENDENCIAS ANTES DE COMPILAR
echo ========================================================================
echo.

REM Verificar cada dependencia crítica
echo Verificando psycopg2...
python -c "import psycopg2" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ psycopg2 NO instalado - Instalando...
    pip install psycopg2-binary
) else (
    echo   ✅ psycopg2 OK
)

echo.
echo Verificando requests...
python -c "import requests" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ requests NO instalado - Instalando...
    pip install requests
) else (
    echo   ✅ requests OK
)

echo.
echo Verificando cryptography...
python -c "import cryptography" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ cryptography NO instalado - Instalando...
    pip install cryptography
) else (
    echo   ✅ cryptography OK
)

echo.
echo Verificando urllib3...
python -c "import urllib3" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ urllib3 NO instalado - Instalando...
    pip install urllib3
) else (
    echo   ✅ urllib3 OK
)

echo.
echo Verificando certifi...
python -c "import certifi" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ certifi NO instalado - Instalando...
    pip install certifi
) else (
    echo   ✅ certifi OK
)

echo.
echo Verificando pystray...
python -c "import pystray" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ pystray NO instalado - Instalando...
    pip install pystray
) else (
    echo   ✅ pystray OK
)

echo.
echo Verificando pywin32...
python -c "import pywin32" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ pywin32 NO instalado - Instalando...
    pip install pywin32
) else (
    echo   ✅ pywin32 OK
)

echo.
echo Verificando bcrypt...
python -c "import bcrypt" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ bcrypt NO instalado - Instalando...
    pip install bcrypt
) else (
    echo   ✅ bcrypt OK
)

echo.
echo Verificando plyer (notificaciones)...
python -c "import plyer" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ plyer NO instalado - Instalando...
    pip install plyer
) else (
    echo   ✅ plyer OK
)

echo.
echo Verificando win10toast (notificaciones Windows)...
python -c "import win10toast" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ win10toast NO instalado - Instalando...
    pip install win10toast
) else (
    echo   ✅ win10toast OK
)

echo.
echo Verificando pillow (pystray dependency)...
python -c "import PIL" 2>nul
if %errorlevel% neq 0 (
    echo   ❌ pillow NO instalado - Instalando...
    pip install pillow
) else (
    echo   ✅ pillow OK
)

echo.
echo ========================================================================
echo   TODAS LAS DEPENDENCIAS VERIFICADAS
echo ========================================================================
echo.

REM OPCIÓN DE OFUSCAR CÓDIGO (requiere PyArmor)
echo ========================================================================
echo   ¿DESEAS OFUSCAR EL CÓDIGO PYTHON?
echo ========================================================================
echo.
echo La ofuscación protege tu código fuente haciendo ilegible los .pyc
echo.
echo Opciones:
echo   1. SI - Ofuscar código con PyArmor (más seguro, más lento)
echo   2. NO - Compilar sin ofuscar (más rápido, código visible)
echo.
set /p OFUSCAR="Selecciona opción (1 o 2): "

if "%OFUSCAR%"=="1" (
    echo.
    echo ========================================================================
    echo   OFUSCANDO CÓDIGO CON PYARMOR...
    echo ========================================================================
    echo.

    REM Verificar si PyArmor está instalado
    python -c "import pyarmor" 2>nul
    if %errorlevel% neq 0 (
        echo   Instalando PyArmor...
        pip install pyarmor
    )

    REM Crear directorio para código ofuscado
    if exist dist_protected rmdir /s /q dist_protected
    mkdir dist_protected

    REM Ofuscar módulos principales
    echo   Ofuscando sync_system_api.py...
    pyarmor gen --output dist_protected sync_system_api.py

    echo   Ofuscando api_client...
    pyarmor gen --output dist_protected\api_client api_client\*.py

    echo   Ofuscando sync...
    pyarmor gen --output dist_protected\sync sync\*.py

    echo.
    echo ✅ Código ofuscado en dist_protected\
    echo.
    echo NOTA: El .exe se generará desde el código ofuscado
    echo.

    REM Usar el archivo ofuscado para compilar
    set SPEC_FILE=sync_system_api_windowed.spec
    set SOURCE_DIR=dist_protected

    echo.
    echo ========================================================================
    echo   COMPILANDO .EXE SIN CONSOLA (desde código ofuscado)
    echo ========================================================================
    echo.

    REM Copiar archivos necesarios al directorio ofuscado
    copy /Y config_encryption.py dist_protected\ >nul 2>&1
    copy /Y %SPEC_FILE% dist_protected\ >nul 2>&1

    REM Cambiar al directorio ofuscado y compilar
    cd dist_protected
    pyinstaller --clean %SPEC_FILE%
    cd ..

    if %errorlevel% neq 0 (
        echo.
        echo ========================================================================
        echo   ❌ ERROR: LA COMPILACION FALLO
        echo ========================================================================
        echo.
        pause
        exit /b 1
    )

    REM Mover el .exe al directorio dist principal
    if exist dist_protected\dist\SyncAPISystem.exe (
        if exist dist rmdir /s /q dist
        mkdir dist
        move /Y dist_protected\dist\SyncAPISystem.exe dist\
        echo ✅ .exe movido a dist\
    )

) else (
    echo.
    echo ========================================================================
    echo   COMPILANDO .EXE SIN CONSOLA (sin ofuscación)
    echo ========================================================================
    echo.

    REM Limpiar build anterior
    if exist build rmdir /s /q build
    if exist dist rmdir /s /q dist

    REM Compilar con PyInstaller usando spec SIN CONSOLA
    pyinstaller --clean sync_system_api_windowed.spec

    if %errorlevel% neq 0 (
        echo.
        echo ========================================================================
        echo   ❌ ERROR: LA COMPILACION FALLO
        echo ========================================================================
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ========================================================================
echo   ✅ EJECUTABLE CREADO EXITOSAMENTE
echo ========================================================================
echo.
echo Ubicacion: dist\SyncAPISystem.exe
echo.
echo Características del .exe:
echo   - ✅ SIN CONSOLA (no muestra ventana negra)
echo   - ✅ System Tray habilitado
echo   - ✅ Todas las dependencias incluidas
if "%OFUSCAR%"=="1" (
    echo   - ✅ Código OFUSCADO (protegido)
) else (
    echo   - ⚠️ Código SIN ofuscar (legible)
)
echo.
echo Para distribuir:
echo   - Comprime la carpeta dist\ en un .zip
echo   - El usuario solo necesita ejecutar SyncAPISystem.exe
echo.
pause
