#!/bin/bash
# Script para iniciar el Python Bridge de PostgreSQL a n8n

echo "========================================================================"
echo "🚀 INICIANDO PYTHON BRIDGE: PostgreSQL → n8n"
echo "========================================================================"

# Verificar que existe el archivo de configuración
if [ ! -f "bridge_config.json" ]; then
    echo "❌ ERROR: No existe bridge_config.json"
    echo ""
    echo "Crea el archivo desde el ejemplo:"
    echo "  cp bridge_config.json.example bridge_config.json"
    echo ""
    echo "Luego edita bridge_config.json con tus credenciales."
    exit 1
fi

# Verificar que exista el archivo de configuración
echo "✅ bridge_config.json encontrado"

# Verificar dependencias
echo ""
echo "📦 Verificando dependencias..."

python3 -c "import psycopg2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Falta psycopg2-binary. Instalando..."
    pip install psycopg2-binary
fi

python3 -c "import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Falta requests. Instalando..."
    pip install requests
fi

echo "✅ Dependencias OK"

# Iniciar el bridge
echo ""
echo "🔧 Iniciando Python Bridge..."
echo "   Presiona Ctrl+C para detener"
echo ""
echo "========================================================================"

python3 python_bridge_n8n.py
