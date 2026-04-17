@echo off
REM Script para iniciar el Python Bridge de PostgreSQL a n8n en Windows

echo ========================================================================
echo 🚀 INICIANDO PYTHON BRIDGE: PostgreSQL =^> n8n
echo ========================================================================

REM Verificar que existe el archivo de configuración
if not exist "bridge_config.json" (
    echo ❌ ERROR: No existe bridge_config.json
    echo.
    echo Crea el archivo desde el ejemplo:
    echo   copy bridge_config.json.example bridge_config.json
    echo.
    echo Luego edita bridge_config.json con tus credenciales.
    pause
    exit /b 1
)

echo ✅ bridge_config.json encontrado

REM Verificar dependencias
echo.
echo 📦 Verificando dependencias...

python -c "import psycopg2" 2>nul
if errorlevel 1 (
    echo ❌ Falta psycopg2-binary. Instalando...
    pip install psycopg2-binary
)

python -c "import requests" 2>nul
if errorlevel 1 (
    echo ❌ Falta requests. Instalando...
    pip install requests
)

echo ✅ Dependencias OK

REM Iniciar el bridge
echo.
echo 🔧 Iniciando Python Bridge...
echo    Presiona Ctrl+C para detener
echo.
echo ========================================================================

python python_bridge_n8n.py

pause
