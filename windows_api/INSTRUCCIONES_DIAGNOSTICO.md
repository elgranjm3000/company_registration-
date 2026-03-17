# 🔍 INSTRUCCIONES PARA DIAGNOSTICAR EL .EXE

El .exe tiene ahora **diagnóstico extremo** integrado. Si se cierra inmediatamente, seguir estos pasos:

## 📋 PASO 1: Recompilar el .exe

```cmd
cd windows_api
CREAR_EXE_CONSOLA.bat
```

## 📋 PASO 2: Ejecutar el .exe

### Opción A: Desde línea de comandos

```cmd
cd dist\SyncAPISystem
SyncAPISystem.exe --mode help
```

### Opción B: Doble clic

Solo haz doble clic en `SyncAPISystem.exe`

## 📋 PASO 3: Revisar el archivo de log

Si el .exe falla, se creará un archivo llamado **`startup_crash.log`** en:

```
dist\SyncAPISystem\startup_crash.log
```

## 📋 PASO 4: Enviar el contenido del log

Abre `startup_crash.log` y envíame el contenido. El log contiene:

- ✅ Tipo de error (IMPORT_ERROR, PSYCOPG2_ERROR, RUNTIME_ERROR)
- ✅ Mensaje de error completo
- ✅ Traceback completo del error
- ✅ Versión de Python
- ✅ Ruta del ejecutable
- ✅ Si es .exe compilado (frozen)
- ✅ Directorio de trabajo
- ✅ Todo el sys.path (rutas de búsqueda de módulos)

## 🎯 Lo que debe mostrar el log si todo está bien:

Si el .exe se crea correctamente, el log NO se creará y deberías ver:

```
usage: SyncAPISystem.exe [-h] [--mode {config,manager,reconfig,sync,tray}]
```

## ⚠️ Errores Comunes y Soluciones:

### Error: "No module named 'api_client'"

**Causa**: PyInstaller no incluyó la carpeta api_client
**Solución**: El .spec debe tener:
```python
datas=[
    ('api_client', 'api_client'),
    ('sync', 'sync'),
]
```

### Error: "No module named 'psycopg2'"

**Causa**: PostgreSQL client no incluido
**Solución**: Agregar `--collect-all=psycopg2`

### Error: "No module named 'tkinter'"

**Causa**: Tkinter no incluido (raro en Windows)
**Solución**: Debería venir incluido con Python

## 📞 Si el log está vacío o no existe:

Significa que el .exe se está cerrando ANTES de que Python ejecute cualquier código.

Posibles causas:
1. El .exe está corrupto - Borrar `dist/` y recompilar
2. Falta MSVC Runtime - Instalar Visual C++ Redistributable
3. Antivirus bloqueando - Desactivar temporalmente

---

## 🔄 Para Recompilar Desde Cero:

```cmd
cd windows_api
rmdir /s /q build dist
del *.spec
CREAR_EXE_CONSOLA.bat
```
