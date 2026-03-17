# 📦 Cómo Compilar el Ejecutable para el Cliente

Esta guía explica cómo crear el ejecutable (.exe) de **Sync API System** para entregar al cliente.

## 📋 Requisitos Previos

### 1. Instalar Python 3.8+

Asegúrate de tener Python instalado en tu máquina de desarrollo:

```cmd
python --version
```

Si no está instalado, descárgalo de: https://www.python.org/downloads/

### 2. Instalar PyInstaller

PyInstaller es la herramienta que convierte el código Python en un .exe:

```cmd
pip install pyinstaller
```

### 3. Instalar Dependencias del Proyecto

Todas las dependencias necesarias:

```cmd
pip install psycopg2-binary requests pystray Pillow cryptography
```

O ejecuta:

```cmd
VERIFICAR_DEPENDENCIAS.bat
```

## 🚀 Métodos de Compilación

### Método 1: Automático (Recomendado)

El método más fácil es usar el archivo .bat preparado:

#### Paso 1: Ejecutar el script de compilación

```cmd
CREAR_EXE.bat
```

Este script:
1. ✅ Verifica que Python esté instalado
2. ✅ Verifica que PyInstaller esté instalado
3. ✅ Verifica que todos los archivos necesarios existan
4. ✅ Ejecuta `build_exe.py` que crea el .exe
5. ✅ Muestra instrucciones para entregar al cliente

#### Paso 2: Esperar la compilación

La compilación puede tomar **5-10 minutos** dependiendo de tu equipo.

Verás una salida similar a:

```
==================================================
  CREANDO EJECUTABLE .EXE - SYNC API SYSTEM
==================================================

Opciones de PyInstaller:
  sync_system_api.py
  --name=SyncAPISystem
  ...

Iniciando compilación...
Esto puede tomar varios minutos...
```

### Método 2: Usar Python directamente

Si prefieres ejecutar directamente el script de Python:

```cmd
python build_exe.py
```

### Método 3: Usar PyInstaller directamente

Para máximo control, puedes usar PyInstaller directamente:

#### Con consola (para desarrollo/debug):

```cmd
CREAR_EXE_CONSOLA.bat
```

O:

```cmd
pyinstaller --name=SyncAPISystem ^
    --onedir ^
    --console ^
    --clean ^
    --noconfirm ^
    --add-data="config_encryption.py;." ^
    --add-data="api_client;base" ^
    --add-data="sync;base" ^
    --hidden-import=psycopg2 ^
    --hidden-import=requests ^
    --hidden-import=pystray ^
    --hidden-import=PIL ^
    --hidden-import=tkinter ^
    --hidden-import=cryptography ^
    --collect-all=psycopg2 ^
    --collect-all=pystray ^
    --collect-all=Pillow ^
    sync_system_api.py
```

#### Sin consola (para producción):

```cmd
CREAR_EXE_SIN_CONSOLA.bat
```

O:

```cmd
pyinstaller sync_system_api.spec
```

## 📁 Estructura del Ejecutable Creado

Después de compilar, se crearán las siguientes carpetas:

```
windows_api/
├── build/              # Archivos temporales de compilación (puedes borrar)
├── dist/
│   └── SyncAPISystem/  # ⭐ ESTO ES LO QUE DEBES ENTREGAR AL CLIENTE
│       ├── SyncAPISystem.exe  # Ejecutable principal
│       ├── api_client/        # Módulos del cliente HTTP
│       ├── sync/              # Módulos de sincronización
│       ├── ...                # DLLs y dependencias
```

## 📦 Qué Entregar al Cliente

### Archivos esenciales (obligatorios):

1. **Todo el contenido de `dist/SyncAPISystem/`**
   - Incluye `SyncAPISystem.exe`
   - Todas las DLLs y dependencias
   - Carpetas `api_client/` y `sync/`

2. **Archivos .bat para el usuario** (copiar de `windows_api/`):
   - `CONFIGURAR.bat` - Para configurar el sistema
   - `MANAGER.bat` - Para abrir el administrador
   - `TRAY.bat` - Para iniciar en modo System Tray
   - `EJECUTAR.bat` - Para sincronizar una vez
   - `VERIFICAR_DEPENDENCIAS.bat` - Solo para desarrollo (opcional)

3. **Documentación** (copiar de `windows_api/`):
   - `README.md` - Documentación completa
   - `INICIO_RAPIDO.md` - Guía rápida de inicio

### Estructura para el cliente:

```
SyncAPISystem_v1.0/
├── SyncAPISystem.exe
├── api_client/
├── sync/
├── [DLLs y archivos de PyInstaller]
│
├── CONFIGURAR.bat
├── MANAGER.bat
├── TRAY.bat
├── EJECUTAR.bat
│
├── README.md
└── INICIO_RAPIDO.md
```

## 🗜️ Crear un ZIP para entregar

Para facilitar la entrega, comprime todo en un ZIP:

```cmd
powershell Compress-Archive -Path dist\SyncAPISystem\*,*.bat,*.md -DestinationPath SyncAPISystem_v1.0.zip
```

O manualmente:
1. Selecciona todo el contenido de `dist/SyncAPISystem/`
2. Selecciona los archivos `.bat`
3. Selecciona los archivos `.md`
4. Crea un ZIP llamado `SyncAPISystem_v1.0.zip`

## 🔧 Solución de Problemas

### Error: "No se puede encontrar psycopg2"

**Solución:**

```cmd
pip install psycopg2-binary
```

Y recompila usando `--collect-all=psycopg2`:

```cmd
pyinstaller --collect-all=psycopg2 sync_system_api.py
```

### Error: "No se puede encontrar PIL/Pillow"

**Solución:**

```cmd
pip install Pillow
```

Y recompila usando `--collect-all=Pillow`:

```cmd
pyinstaller --collect-all=Pillow sync_system_api.py
```

### Error: "No se puede encontrar pystray"

**Solución:**

```cmd
pip install pystray
```

Y recompila usando `--collect-all=pystray`:

```cmd
pyinstaller --collect-all=pystray sync_system_api.py
```

### Error: "El ejecutable es demasiado grande"

Esto es normal. PyInstaller incluye:
- Python completo (~15 MB)
- Todas las dependencias
- PostgreSQL client libs (~10 MB)
- PIL/Pillow para imágenes (~5 MB)

**Tamaño esperado**: 50-80 MB comprimido

### Error: "No se ejecuta en Windows sin Python"

Esto NO debería pasar. PyInstaller crea un ejecutable **independiente** que NO requiere Python instalado.

Si pasa, verifica que:
1. Usaste `--onedir` (carpeta con dependencias)
2. Incluiste todas las DLLs de `dist/SyncAPISystem/`

### El ejecutable se cierra inmediatamente

**Causa**: Estás usando la versión sin consola (`--windowed` o `--noconsole`) y hay un error al inicio.

**Solución temporal**: Compila con consola para ver el error:

```cmd
CREAR_EXE_CONSOLA.bat
```

Ejecuta y mira qué error aparece en la consola.

### Error: "ImportError: No module named 'api_client'"

**Causa**: PyInstaller no incluyó los módulos locales.

**Solución**: Agrega los `--add-data` correctamente:

```cmd
--add-data="api_client;base"
--add-data="sync;base"
```

## 🎯 Recomendaciones para Producción

### 1. Usar versión sin consola

Para el cliente final, usa la versión **SIN consola** (`--windowed` o `--noconsole`):

```cmd
CREAR_EXE_SIN_CONSOLA.bat
```

Esto evita que aparezca una ventana negra de consola.

### 2. Probar antes de entregar

Siempre prueba el ejecutable antes de entregarlo:

```cmd
cd dist\SyncAPISystem
SyncAPISystem.exe --mode config
```

### 3. Incluir instrucciones claras

El cliente debe saber:
1. Cómo configurar el sistema (CONFIGURAR.bat)
2. Cómo ejecutarlo (MANAGER.bat o TRAY.bat)
3. Dónde se guardan los logs

### 4. Versión del ejecutable

Para control de versiones, considera agregar:
- Número de versión en el nombre: `SyncAPISystem_v1.0.0.zip`
- Fecha de compilación
- Notas de release

## 📝 Checklist de Compilación

Antes de entregar al cliente:

- [ ] Python 3.8+ instalado
- [ ] PyInstaller instalado (`pip install pyinstaller`)
- [ ] Todas las dependencias instaladas
- [ ] Ejecutado `CREAR_EXE.bat` exitosamente
- [ ] Probado el ejecutable: `SyncAPISystem.exe --mode config`
- [ ] Probado el modo Manager: `SyncAPISystem.exe --mode manager`
- [ ] Probado el modo Tray: `SyncAPISystem.exe --mode tray`
- [ ] Copiados todos los archivos de `dist/SyncAPISystem/`
- [ ] Incluidos archivos .bat (CONFIGURAR, MANAGER, TRAY, EJECUTAR)
- [ ] Incluida documentación (README.md, INICIO_RAPIDO.md)
- [ ] Creado ZIP para entrega
- [ ] Probado el ZIP en una máquina limpia (sin Python)

## 🎉 Ejecutable Listo

Una vez completado estos pasos, tendrás un archivo ZIP listo para entregar al cliente con:

- ✅ Ejecutable independiente (no requiere Python instalado)
- ✅ Todos los archivos necesarios
- ✅ Scripts .bat para fácil uso
- ✅ Documentación completa

El cliente solo necesita:
1. Descomprimir el ZIP
2. Ejecutar `CONFIGURAR.bat`
3. Ejecutar `MANAGER.bat` o `TRAY.bat`

---

**¿Necesitas ayuda?** Revisa `README.md` para más información del sistema.
