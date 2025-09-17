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

info "=== CONSTRUCCIÓN DE .EXE CON PYTHON NATIVO ==="

# Verificar que Python3 está disponible
if ! command -v python3 &> /dev/null; then
    error "Python3 no está instalado"
    error "Ejecuta: sudo apt install python3 python3-pip"
    exit 1
fi

# Verificar que app.py existe
if [ ! -f "app.py" ]; then
    error "app.py no encontrado en el directorio actual"
    exit 1
fi

# Verificar entorno virtual
if [[ "$VIRTUAL_ENV" == "" ]]; then
    warning "Entorno virtual no activado"
    info "Se recomienda usar entorno virtual, pero continuando..."
    PYTHON_CMD="python3"
    PIP_CMD="python3 -m pip"
else
    success "Entorno virtual activo: $VIRTUAL_ENV"
    PYTHON_CMD="python"
    PIP_CMD="pip"
fi

# Verificar/instalar dependencias
info "Verificando dependencias..."

DEPENDENCIES=("mysql-connector-python" "pyinstaller")

for dep in "${DEPENDENCIES[@]}"; do
    if ! $PYTHON_CMD -c "import ${dep//[-.]/_}" 2>/dev/null; then
        info "Instalando $dep..."
        $PIP_CMD install "$dep"
        
        if [ $? -eq 0 ]; then
            success "$dep instalado"
        else
            error "Error instalando $dep"
            exit 1
        fi
    else
        success "$dep ya está instalado"
    fi
done

# Verificar tkinter
if ! $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
    error "tkinter no está disponible"
    info "Instala con: sudo apt install python3-tk"
    exit 1
fi

success "Todas las dependencias verificadas"

# Limpiar construcciones anteriores
info "Limpiando builds anteriores..."
rm -rf build/ dist/ *.spec

# Crear directorio assets si no existe
mkdir -p assets

# Generar spec para Windows desde Linux
info "Generando configuración PyInstaller para Windows..."
cat > CompanyRegistration.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

# Configuración específica para generar .exe desde Linux
a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets') if os.path.exists('assets') else [],
    ],
    hiddenimports=[
        'mysql.connector',
        'mysql.connector.pooling',
        'mysql.connector.constants',
        'mysql.connector.abstracts',
        'mysql.connector.conversion',
        'mysql.connector.cursor',
        'mysql.connector.errorcode',
        'mysql.connector.errors',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'tkinter.font',
        'tkinter.constants',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'test',
        'unittest',
        'doctest',
        'pydoc',
        'xml',
        'email',
        'http',
        'urllib',
        'json',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyd = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyd,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CompanyRegistration.exe',  # Forzar extensión .exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)
EOF

# Construir ejecutable
info "Construyendo ejecutable..."
info "NOTA: Esto creará un ejecutable Linux, NO un .exe real de Windows"
warning "Para un .exe real de Windows, necesitas Wine o compilar en Windows"

$PYTHON_CMD -m PyInstaller \
    --clean \
    --noconfirm \
    CompanyRegistration.spec

# Verificar resultado
if [ -f "dist/CompanyRegistration.exe" ]; then
    warning "Archivo creado, pero es ejecutable Linux con extensión .exe"
    
    # Renombrar para evitar confusión
    mv dist/CompanyRegistration.exe dist/CompanyRegistration-linux
    
    info "Renombrado a: dist/CompanyRegistration-linux"
    info "Este archivo solo funciona en Linux, NO en Windows"
    
    # Crear estructura de distribución
    mkdir -p ejecutable_linux
    cp dist/CompanyRegistration-linux ejecutable_linux/
    chmod +x ejecutable_linux/CompanyRegistration-linux
    
    # Crear información
    cat > ejecutable_linux/README_LINUX.txt << EOF
EJECUTABLE PARA LINUX
====================

Archivo: CompanyRegistration-linux
Creado: $(date)
Plataforma: Linux solamente
Método: PyInstaller nativo

NOTA IMPORTANTE:
Este archivo NO es un .exe de Windows.
Solo funciona en sistemas Linux.

PARA USAR EN LINUX:
1. ./CompanyRegistration-linux
2. O hacer doble clic si el entorno gráfico lo permite

PARA CREAR VERDADERO .EXE DE WINDOWS:
Necesitas una de estas opciones:
1. Wine + PyInstaller (como en el script anterior)
2. Docker con imagen Windows
3. Compilar en una máquina Windows real
4. GitHub Actions (compilación en la nube)

FUNCIONALIDADES:
- Registro de nuevas compañías
- Validación de RIF venezolano
- Validación de email
- Detección de duplicados
- Log de actividad detallado
- Conexión segura a MySQL
EOF

    success "Ejecutable Linux creado en: ejecutable_linux/"
    
elif [ -f "dist/CompanyRegistration" ]; then
    success "Ejecutable Linux creado: dist/CompanyRegistration"
    
    # Crear estructura de distribución
    mkdir -p ejecutable_linux
    cp dist/CompanyRegistration ejecutable_linux/
    chmod +x ejecutable_linux/CompanyRegistration
    
    # Obtener tamaño
    size=$(du -h ejecutable_linux/CompanyRegistration | cut -f1)
    info "Tamaño: $size"
    
    # Crear información
    cat > ejecutable_linux/README_LINUX.txt << EOF
EJECUTABLE PARA LINUX
====================

Archivo: CompanyRegistration
Creado: $(date)
Plataforma: Linux
Tamaño: $size
Método: PyInstaller nativo

INSTRUCCIONES DE USO:
1. ./CompanyRegistration
2. O hacer doble clic en entorno gráfico

DISTRIBUCIÓN:
Para otros usuarios Linux:
  tar -czf CompanyRegistration-Linux.tar.gz ejecutable_linux/

NOTA IMPORTANTE:
Este NO es un archivo .exe de Windows.
Solo funciona en Linux.

Para crear .exe real de Windows, usa:
- Wine + este script
- Docker con Windows
- Compilación en Windows
- GitHub Actions
EOF

    success "Ejecutable Linux listo en: ejecutable_linux/"
    
else
    error "No se pudo crear el ejecutable"
    exit 1
fi

# Crear script para .exe real
cat > crear_exe_real.sh << 'EOF'
#!/bin/bash
echo "PARA CREAR .EXE REAL DE WINDOWS:"
echo "================================"
echo ""
echo "OPCION 1 - Wine (en este mismo Linux):"
echo "  sudo apt install wine"
echo "  # Luego usar el script con Wine"
echo ""
echo "OPCION 2 - GitHub Actions (en la nube):"
echo "  # Subir código a GitHub"
echo "  # GitHub compila automáticamente"
echo ""
echo "OPCION 3 - Docker (sin Wine):"
echo "  sudo apt install docker.io"
echo "  # Usar contenedor Windows"
echo ""
echo "OPCION 4 - Windows real:"
echo "  # Llevar código a PC Windows"
echo "  # pip install pyinstaller mysql-connector-python"
echo "  # pyinstaller --onefile --windowed app.py"
echo ""
echo "El ejecutable actual solo funciona en Linux."
EOF
chmod +x crear_exe_real.sh

warning "IMPORTANTE: El archivo creado NO es un .exe de Windows"
info "Es un ejecutable Linux que solo funciona en Linux"
info "Para crear .exe real: ./crear_exe_real.sh"

info "=== CONSTRUCCIÓN COMPLETADA ==="