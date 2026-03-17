# 🔍 Diagnóstico de Problemas con el .EXE

Si el ejecutable se cierra inmediatamente al abrirlo, sigue estos pasos:

## 📋 Pasos para Diagnosticar

### 1. Verificar que el .exe existe

```cmd
dir dist\SyncAPISystem\SyncAPISystem.exe
```

Si no existe, ejecuta primero:
```cmd
CREAR_EXE_CONSOLA.bat
```

### 2. Ejecutar el script de diagnóstico

```cmd
diagnosticar_exe.bat
```

Este script:
- Verifica que el .exe exista
- Ejecuta `SyncAPISystem.exe --mode help`
- Muestra el código de salida
- Mantiene la consola abierta para ver errores

### 3. Ejecutar con captura de errores

```cmd
EJECUTAR_EXE_DEBUG.bat
```

Este script:
- Muestra el directorio actual
- Lista archivos DLL en `_internal\`
- Ejecuta el .exe
- Captura y muestra el código de salida
- Se mantiene abierto para ver errores

### 4. Verificar archivos incluidos

El ejecutable compilado debe incluir en `dist\SyncAPISystem\`:

```
dist/SyncAPISystem/
├── SyncAPISystem.exe        ← El ejecutable
├── _internal/                ← Dependencias de Python
│   ├── api_client/           ← Módulos API (DEBE ESTAR)
│   ├── sync/                 ← Módulos de sincronización (DEBE ESTAR)
│   ├── psycopg2/            ← PostgreSQL client
│   ├── requests/            ← HTTP client
│   ├── pystray/             ← System tray
│   ├── PIL/                 ← Pillow (imágenes)
│   ├── cryptography/        ← Encriptación
│   └── [otras DLLs...]
└── config_encryption.py     ← Encriptación (opcional)
```

**⚠️ IMPORTANTE**: Si `api_client/` o `sync/` NO están en `_internal/`, el .exe fallará.

## 🐛 Problemas Comunes

### Problema 1: "No se pueden importar los módulos"

**Causa**: Las carpetas `api_client/` y `sync/` no se incluyeron en la compilación.

**Solución**:
1. Verifica que `sync_system_api.spec` tenga:
   ```python
   datas=[
       ('api_client', 'api_client'),
       ('sync', 'sync'),
       ('config_encryption.py', '.'),
   ]
   ```

2. Recompila usando el `.spec`:
   ```cmd
   pyinstaller --clean sync_system_api.spec
   ```

### Problema 2: "psycopg2 no está instalado"

**Causa**: PostgreSQL client no se incluyó correctamente.

**Solución**:
1. En `sync_system_api.spec`, verifica:
   ```python
   hiddenimports=[
       'psycopg2',
       'psycopg2.extensions',
       'psycopg2.extras',
   ]
   ```

2. O agrega:
   ```cmd
   --collect-all=psycopg2
   ```

### Problema 3: Falta DLL o dependencia

**Síntoma**: Error genérico de Windows

**Solución**:
1. Instala Visual C++ Redistributable:
   - https://aka.ms/vs/17/release/vc_redist.x64.exe

2. Reinstala Python y todas las dependencias:
   ```cmd
   pip install --upgrade pyinstaller psycopg2-binary requests pystray Pillow cryptography
   ```

### Problema 4: Se cierra sin mensaje de error

**Causa**: Error antes de que se inicialice la consola

**Solución**:
1. Ejecuta desde CMD directamente:
   ```cmd
   cd dist\SyncAPISystem
   SyncAPISystem.exe --mode help
   ```

2. O crea un wrapper `.bat`:
   ```cmd
   @echo off
   cd dist\SyncAPISystem
   SyncAPISystem.exe %*
   pause
   ```

## ✅ Verificación Rápida

Después de compilar, verifica esto:

```cmd
cd dist\SyncAPISystem

1. ¿Existe SyncAPISystem.exe?
   dir SyncAPISystem.exe

2. ¿Existen las carpetas necesarias en _internal?
   dir _internal\api_client
   dir _internal\sync

3. ¿Se ejecuta --mode help?
   SyncAPISystem.exe --mode help

4. ¿Cuál es el tamaño del .exe?
   Debe ser entre 10-15 MB mínimo
```

## 🔧 Soluciones Avanzadas

### Si nada funciona:

1. **Compilar sin encriptación** (para debug):
   En `sync_system_api.spec`, comenta:
   ```python
   # cipher=block_cipher,
   ```
   Y en `pyz`:
   ```python
   # pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
   pyz = PYZ(a.pure, a.zipped_data)
   ```

2. **Modo debug de PyInstaller**:
   ```cmd
   pyinstaller --debug=all --log-level=DEBUG sync_system_api.spec
   ```

3. **Verificar con PyInstaller Extractor**:
   Si el .exe se crea pero no funciona, extrae su contenido:
   ```cmd
   pyinstxtractor SyncAPISystem.exe
   ```
   Y verifica qué archivos contiene.

## 📞 Si persiste el problema

Envía esta información:

1. Salida de `diagnosticar_exe.bat`
2. Salida de `EJECUTAR_EXE_DEBUG.bat`
3. Contenido de `dist/SyncAPISystem/_internal/` (lista de archivos)
4. Tamaño de `SyncAPISystem.exe`
5. Versión de Windows
6. Versión de Python (`python --version`)
7. Versión de PyInstaller (`pip show pyinstaller`)

---

**Recuerda**: El .exe debe ejecutarse en Windows. No funcionará en Linux.
