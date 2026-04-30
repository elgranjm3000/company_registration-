@echo off
title Compilar con Verificación de Dependencias

cd /d "%~dp0"

echo ========================================
echo   VERIFICAR DEPENDENCIAS ANTES DE COMPILAR
echo ========================================
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
echo ========================================
echo   TODAS LAS DEPENDENCIAS VERIFICADAS
echo ========================================
echo.
echo Ahora compilando el .exe...
echo.

REM Limpiar build anterior
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Compilar con PyInstaller
pyinstaller --clean sync_system_api_console.spec

if %errorlevel% neq 0 (
    echo.
    echo ========================================
    echo   ❌ ERROR: LA COMPILACION FALLO
    echo ========================================
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✅ EJECUTABLE CREADO EXITOSAMENTE
echo ========================================
echo.
echo Ubicacion: dist\SyncAPISystem.exe
echo.
echo Antes de ejecutar, verifica que el .exe
echo se abra correctamente.
echo.
pause
