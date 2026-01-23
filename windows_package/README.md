# Como crear el ejecutable

## PASOS:

1. Abre una terminal en la carpeta `windows_package`
2. Ejecuta: `CREAR_EXE.bat`
3. Espera 3-5 minutos
4. El ejecutable estará en: `dist\sync_system.exe`

## REQUISITOS:

- Windows 7 o superior
- Python 3.8+ instalado
- Internet (para descargar dependencias la primera vez)

## QUE HACE EL SCRIPT:

1. Crea un entorno virtual (venv)
2. Instala PyInstaller 6.1.0
3. Instala psycopg2-binary
4. Instala mysql-connector-python
5. Compila sync_system.py en un .exe

## SI HAY ERRORES:

- "Python no encontrado": Instala Python desde python.org
- "No se pudo crear entorno virtual": Asegúrate de tener permisos
- "Error instalando dependencias": Ejecuta como administrador
