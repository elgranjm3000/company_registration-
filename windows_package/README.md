# Como crear el ejecutable

## WINDOWS:

1. Abre una terminal en la carpeta `windows_package`
2. Ejecuta: `CREAR_EXE.bat`
3. Espera 3-5 minutos
4. El ejecutable estará en: `dist\sync_system.exe`

## LINUX:

1. Abre una terminal en la carpeta `windows_package`
2. Ejecuta: `chmod +x CREAR_EXE_LINUX.sh && ./CREAR_EXE_LINUX.sh`
3. Espera 3-5 minutos
4. El ejecutable estará en: `dist/sync_system`

## REQUISITOS:

### Windows:
- Windows 7 o superior
- Python 3.8+ instalado
- Internet (para descargar dependencias la primera vez)

### Linux:
- Cualquier distribución moderna (Ubuntu, Debian, etc.)
- Python 3.8+ instalado
- python3-venv instalado (`sudo apt install python3-venv`)

## QUE HACE EL SCRIPT:

1. Crea un entorno virtual (venv)
2. Instala PyInstaller 4.10 (versión estable)
3. Instala psycopg2-binary
4. Instala mysql-connector-python
5. Compila sync_system.py en un ejecutable

## MODO DE USO DEL EJECUTABLE:

El ejecutable tiene 4 modos:

- `--mode config` - Configuración inicial (GUI)
- `--mode manager` - Interfaz de administración
- `--mode sync` - Sincronización única
- `--mode service` - Modo servicio continuo

Ejemplo:
```bash
# Windows
sync_system.exe --mode config

# Linux
./sync_system --mode config
```

## SI HAY ERRORES:

- "Python no encontrado": Instala Python desde python.org
- "No se pudo crear entorno virtual": Asegúrate de tener permisos
- "Error instalando dependencias": Ejecuta como administrador/root

