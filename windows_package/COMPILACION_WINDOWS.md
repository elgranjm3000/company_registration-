# 📦 Guía de Compilación para Windows

## Especificaciones Técnicas del .EXE

Este documento explica cómo compilar el sistema en Windows con todas las dependencias necesarias para que funcionen:
- ✅ System Tray (icono en barra de tareas)
- ✅ Notificaciones Banner prominentes
- ✅ Sincronización automática
- ✅ Logs separados por empresa

## 🔧 Requisitos Previos

### 1. Instalar Python en Windows
```bash
# Descargar desde: https://www.python.org/downloads/
# Versión recomendada: Python 3.9.x o 3.10.x
# IMPORTANTE: Marcar "Add Python to PATH" durante la instalación
```

### 2. Instalar Dependencias
```bash
pip install pyinstaller mysql-connector-python psycopg2-binary pystray Pillow win10toast python-dotenv
```

## 📝 Archivos .SPEC Configurados

Se han creado dos archivos `.spec` con todas las dependencias necesarias:

### 1. `build_scripts/app.spec`
Para compilar `app.py` (aplicación principal)

### 2. `windows_package/sync_system.spec` (NUEVO)
Para compilar `sync_system.py` (sistema de sincronización)

## 🚀 Comandos de Compilación

### Opción 1: Compilar sync_system.py (RECOMENDADO)
```bash
cd windows_package
pyinstaller --onefile --windowed sync_system.spec
```

El .exe se generará en: `windows_package/dist/sync_system.exe`

### Opción 2: Compilar con línea de comando (sin .spec)
```bash
cd windows_package
pyinstaller --onefile --windowed ^
  --hidden-import=pystray ^
  --hidden-import=PIL ^
  --hidden-import=win10toast ^
  --hidden-import=pypiwin32 ^
  --hidden-import=pywin32 ^
  --hidden-import=mysql.connector ^
  --hidden-import=psycopg2 ^
  --icon=icon.ico ^
  sync_system.py
```

## 📋 Dependencias Incluidas en el .SPEC

### System Tray:
- ✅ `pystray` - Icono en barra de tareas
- ✅ `PIL/Pillow` - Imágenes del icono
- ✅ `pystray._appindicator` - Soporte Linux
- ✅ `pystray._darwin` - Soporte macOS
- ✅ `pystray._win32` - Soporte Windows

### Notificaciones Banner:
- ✅ `win10toast` - Notificaciones de Windows 10/11
- ✅ `win10toast.toast` - Módulo de toast

### Windows API:
- ✅ `pypiwin32` - Wrappers de Windows API
- ✅ `pywin32` - Extensions para Python
- ✅ `win32api` - API de Windows
- ✅ `win32con` - Constantes de Windows
- ✅ `win32gui` - Interfaz gráfica de Windows
- ✅ `win32clipboard` - Portapapeles
- ✅ `pythoncom` - COM objects
- ✅ `pywintypes` - Tipos de Windows

### Base de Datos:
- ✅ `mysql.connector` - Conector MySQL
- ✅ `psycopg2` - Conector PostgreSQL

## 🎨 Icono Personalizado

Opcionalmente puedes agregar un icono personalizado:

1. Coloca el archivo `icon.ico` en `windows_package/`
2. El .spec ya incluye: `icon='icon.ico'`
3. Si no existe, PyInstaller usará el icono por defecto

## ✅ Verificación del .EXE Compilado

### Test de Funcionalidades:

1. **System Tray:**
   ```bash
   sync_system.exe --mode tray
   # Debe aparecer icono en barra de tareas
   ```

2. **Configuración:**
   ```bash
   sync_system.exe --mode config
   # Debe abrir ventana de configuración
   ```

3. **Manager:**
   ```bash
   sync_system.exe --mode manager
   # Debe abrir ventana del Manager
   ```

4. **Verificar Notificaciones:**
   - Ejecuta una sincronización
   - Debe aparecer notificación Banner en esquina superior derecha
   - Duración: 5-10 segundos

## 🔍 Solución de Problemas Comunes

### Error: "No module named 'pystray'"
```bash
pip install pystray Pillow
```

### Error: "No module named 'win10toast'"
```bash
pip install win10toast pypiwin32
```

### Error: "No module named 'mysql.connector'"
```bash
pip install mysql-connector-python
```

### Error: "No module named 'psycopg2'"
```bash
pip install psycopg2-binary
```

### Las notificaciones no aparecen:
1. Verificar que `win10toast` esté instalado
2. Revisar configuración de notificaciones de Windows
3. Verificar que la aplicación tenga permisos

## 📦 Estructura del .EXE Compilado

```
windows_package/
├── dist/
│   └── sync_system.exe          ← .EXE final (único archivo)
├── build/                       ← Archivos temporales de compilación
└── sync_system.spec             ← Archivo de configuración PyInstaller
```

## 🚀 Distribución

Para distribuir el .EXE:

1. **Solo el archivo .exe:**
   - Copiar `dist/sync_system.exe`
   - Funciona standalone (sin dependencias externas)

2. **Con archivos de configuración:**
   - `sync_system.exe`
   - `sync_config.json` (opcional, se crea al ejecutar)
   - `logs/` (se crea automáticamente)

3. **Instalador (opcional):**
   - Usar Inno Setup para crear un installer profesional
   - Incluir shortcut en escritorio
   - Iniciar con Windows (Startup folder)

## 📝 Notas Importantes

1. **Tamaño del .EXE:** ~50-80 MB (incluye Python y todas las dependencias)
2. **Primer arranque:** Puede ser lento (desempaqueta dependencias)
3. **Antivirus:** Algunos antivirus pueden marcarlo como falso positivo
4. **Windows Defender:** Agregar excepción si bloquea el .EXE
5. **Logs:** Se crean en `logs/` junto al .EXE

## 🎯 Modos de Ejecución

```bash
# System Tray (recomendado para producción)
sync_system.exe --mode tray

# Configuración inicial
sync_system.exe --mode config

# Manager manual
sync_system.exe --mode manager

# Sincronización única
sync_system.exe --mode sync-once
```

## 📞 Soporte

Si encuentras problemas durante la compilación:

1. Verificar que todas las dependencias estén instaladas
2. Usar Python 3.9 o 3.10 (evitar 3.11+ por ahora)
3. Ejecutar como Administrador
4. Desactivar antivirus temporalmente durante la compilación
