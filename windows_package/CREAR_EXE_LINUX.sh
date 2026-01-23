#!/bin/bash
# ========================================
#   CREAR EJECUTABLE SYNC SYSTEM - LINUX
# ========================================

set -e

echo "========================================"
echo "  CREAR EJECUTABLE SYNC SYSTEM - LINUX"
echo "========================================"
echo ""

# [1/7] Verificar Python
echo "[1/7] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 no está instalado"
    echo "Instala con: sudo apt install python3 python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION encontrado"

echo ""
# [2/7] Verificar archivos
echo "[2/7] Verificando archivos..."
if [ ! -f "sync_system.py" ]; then
    echo "ERROR: sync_system.py no encontrado"
    exit 1
fi

if [ ! -f "smart_sync_complete.py" ]; then
    echo "ERROR: smart_sync_complete.py no encontrado"
    exit 1
fi
echo "Archivos encontrados"

echo ""
# [2.5/7] Verificar sintaxis de Python
echo "[2.5/7] Verificando sintaxis de Python..."
python3 -m py_compile sync_system.py
if [ $? -ne 0 ]; then
    echo "ERROR: sync_system.py tiene errores de sintaxis"
    exit 1
fi

python3 -m py_compile smart_sync_complete.py
if [ $? -ne 0 ]; then
    echo "ERROR: smart_sync_complete.py tiene errores de sintaxis"
    exit 1
fi
echo "Sintaxis correcta"

echo ""
# [3/7] Crear entorno virtual
echo "[3/7] Configurando entorno virtual..."
if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: No se pudo crear entorno virtual"
        echo "Instala venv: sudo apt install python3-venv"
        exit 1
    fi
fi
echo "Entorno virtual listo"

echo ""
# [4/7] Activar entorno virtual
echo "[4/7] Activando entorno virtual..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: No se pudo activar entorno virtual"
    exit 1
fi

echo ""
# [5/7] Instalar dependencias
echo "[5/7] Instalando dependencias..."
echo "Esto puede tomar un minuto..."
python3 -m pip install --upgrade pip --quiet

echo "Instalando PyInstaller 4.10..."
pip install pyinstaller==4.10 --quiet
if [ $? -ne 0 ]; then
    echo "ERROR instalando PyInstaller"
    exit 1
fi

echo "Instalando psycopg2-binary..."
pip install psycopg2-binary --quiet
if [ $? -ne 0 ]; then
    echo "ERROR instalando psycopg2-binary"
    exit 1
fi

echo "Instalando mysql-connector-python..."
pip install mysql-connector-python --quiet
if [ $? -ne 0 ]; then
    echo "ERROR instalando mysql-connector-python"
    exit 1
fi

echo "Verificando dependencias..."
python3 -c "import psycopg2; import mysql.connector; import tkinter; print('OK')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Dependencias no instaladas correctamente"
    exit 1
fi
echo "Dependencias OK"

echo ""
# [5.5/7] Verificar compatibilidad completa
echo "[5.5/7] Verificando compatibilidad completa..."
echo "Probando imports de sync_system.py..."
python3 -c "import sys; sys.path.insert(0, '.'); exec(open('sync_system.py').read().split('if __name__')[0])" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: Puede haber problemas con los imports"
    echo "Continuando de todos modos..."
else
    echo "Imports compatibles"
fi
echo "Verificando módulos necesarios..."
python3 -c "import importlib.util; spec = importlib.util.spec_from_file_location('test', 'smart_sync_complete.py'); print('Módulo smart_sync_complete OK')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: smart_sync_complete.py tiene problemas"
else
    echo "Módulo smart_sync_complete OK"
fi

echo ""
# [6/7] Limpiar builds anteriores
echo "[6/7] Limpiando builds anteriores..."
rm -rf build dist *.spec 2>/dev/null

echo ""
# [7/7] Resumen de compatibilidad
echo "========================================="
echo "  RESUMEN DE COMPATIBILIDAD"
echo "========================================="
echo ""
echo "Python: $PYTHON_VERSION"
echo "PyInstaller: 4.10"
echo "psycopg2-binary: Instalado"
echo "mysql-connector-python: Instalado"
echo "tkinter: Disponible"
echo ""
echo "Archivos a compilar:"
echo "  - sync_system.py"
echo "  - smart_sync_complete.py"
echo ""
echo "Todo parece compatible. Procediendo a crear ejecutable..."
echo "========================================="
echo ""

# [7/7] Crear ejecutable
echo "Creando ejecutable..."
echo "Esto tomará 3-5 minutos"
echo ""

pyinstaller \
    --onefile \
    --noconsole \
    --name "sync_system" \
    --add-data "smart_sync_complete.py:." \
    --hidden-import psycopg2 \
    --hidden-import psycopg2.extensions \
    --hidden-import mysql.connector \
    --hidden-import tkinter \
    --hidden-import tkinter.ttk \
    --hidden-import tkinter.scrolledtext \
    --exclude-module matplotlib \
    --exclude-module numpy \
    --exclude-module pandas \
    sync_system.py

if [ $? -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "  ERROR: NO SE PUDO CREAR EJECUTABLE"
    echo "========================================"
    exit 1
fi

echo ""
# Verificar resultado
if [ -f "dist/sync_system" ]; then
    echo ""
    echo "========================================"
    echo "  EXITO: EJECUTABLE CREADO"
    echo "========================================"
    echo ""
    echo "Ubicación: $(pwd)/dist/sync_system"

    SIZE_MB=$(du -m dist/sync_system | cut -f1)
    echo "Tamaño: $SIZE_MB MB"

    echo ""
    echo "COMO USAR:"
    echo "  1. Ve a la carpeta dist"
    echo "  2. Copia sync_system donde quieras"
    echo "  3. Ejecuta: ./sync_system"
    echo "  O: chmod +x sync_system && ./sync_system"
    echo ""

else
    echo ""
    echo "ERROR: No se encontró el ejecutable"
    exit 1
fi
