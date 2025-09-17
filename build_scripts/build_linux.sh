#!/bin/bash

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }
error() { log "${RED}❌ ERROR: $1${NC}"; }
success() { log "${GREEN}✅ $1${NC}"; }
warning() { log "${YELLOW}⚠️  $1${NC}"; }
info() { log "${BLUE}ℹ️  $1${NC}"; }

info "=== CONSTRUCCIÓN DE EJECUTABLE PARA LINUX ==="

# Verificar que estamos en entorno virtual
if [[ "$VIRTUAL_ENV" == "" ]]; then
    error "Entorno virtual no activado"
    error "Ejecuta: source venv/bin/activate"
    exit 1
fi

# Limpiar construcciones anteriores
info "Limpiando builds anteriores..."
rm -rf build/ dist/ *.spec

# Verificar dependencias
info "Verificando dependencias..."
python -c "import mysql.connector; import tkinter; print('✅ Dependencias OK')" || {
    error "Faltan dependencias. Ejecuta: pip install -r requirements.txt"
    exit 1
}

# Generar spec automáticamente primero
info "Generando configuración PyInstaller..."
pyi-makespec \
    --onefile \
    --windowed \
    --name "CompanyRegistration" \
    --add-data "assets:assets" \
    --hidden-import "mysql.connector" \
    --hidden-import "mysql.connector.pooling" \
    app.py

# Construir ejecutable
info "Construyendo ejecutable..."
pyinstaller \
    --clean \
    --noconfirm \
    CompanyRegistration.spec

# Verificar resultado
if [ -f "dist/CompanyRegistration" ]; then
    success "Ejecutable creado exitosamente"
    info "Ubicación: $(pwd)/dist/CompanyRegistration"
    info "Tamaño: $(du -h dist/CompanyRegistration | cut -f1)"
    
    # Hacer ejecutable
    chmod +x dist/CompanyRegistration
    
    # Crear script de lanzamiento
    cat > dist/run_app.sh << 'EOF'
#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"
./CompanyRegistration
EOF
    chmod +x dist/run_app.sh
    
    success "Script de lanzamiento creado: dist/run_app.sh"
    
    # Probar ejecución
    warning "Probando ejecutable..."
    ./dist/CompanyRegistration --version 2>/dev/null && success "Ejecutable funciona correctamente" || warning "No se pudo probar automáticamente"
    
else
    error "Error construyendo ejecutable"
    exit 1
fi

info "=== CONSTRUCCIÓN COMPLETADA ==="
