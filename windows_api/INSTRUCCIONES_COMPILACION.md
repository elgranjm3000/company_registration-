# 📦 Instrucciones para Compilar el Ejecutable .EXE

## ⚠️ ANTES DE COMPILAR - INSTALAR DEPENDENCIAS

Es **OBLIGATORIO** instalar todas las dependencias de Python ANTES de compilar el .exe:

```bash
pip install psycopg2-binary requests urllib3 certifi pystray pywin32 bcrypt cryptography pillow plyer win10toast
```

O instalar desde requirements.txt:

```bash
pip install -r requirements.txt
```

### Verificar que los módulos estén instalados:

```bash
python -c "import psycopg2; print('✅ psycopg2 OK')"
python -c "import requests; print('✅ requests OK')"
python -c "import cryptography; print('✅ cryptography OK')"
python -c "import pystray; print('✅ pystray OK')"
```

Si alguno muestra error, instalarlo:
```bash
pip install psycopg2-binary requests
```

## 🔧 COMPILAR EL .EXE

### Opción 1: Usar el script .bat (Recomendado)

```bash
cd windows_api
CREAR_EXE_CONSOLA.bat
```

### Opción 2: Compilar manualmente

```bash
cd windows_api
pyinstaller --clean sync_system_api_console.spec
```

## 📂 Ubicación del Ejecutable

Después de compilar, el .exe estará en:
```
windows_api\dist\SyncAPISystem.exe
```

## ❌ ERRORES COMUNES Y SOLUCIONES

### Error: "No module named 'requests'"
**Solución:**
```bash
pip install requests urllib3 certifi
pyinstaller --clean sync_system_api_console.spec
```

### Error: "No module named 'psycopg2'"
**Solución:**
```bash
pip install psycopg2-binary
pyinstaller --clean sync_system_api_console.spec
```

### Error: "No module named 'cryptography'"
**Solución:**
```bash
pip install cryptography
pyinstaller --clean sync_system_api_console.spec
```

### Error: "pyinstaller no se reconoce como comando"
**Solución:**
```bash
pip install pyinstaller
```

### Error: El .exe se cierra inmediatamente
**Solución:** Ejecutar desde CMD para ver el error:
```bash
cd windows_api\dist
SyncAPISystem.exe
```

O presionar Win+R, escribir `cmd` y navegar a la carpeta.

## 🔄 Recompilar Después de Cambios en el Código

Si modificas el código de Python o los archivos .spec:

1. Limpiar build anterior:
   ```bash
   rmdir /s /q build
   rmdir /s /q dist
   ```

2. Recompilar:
   ```bash
   pyinstaller --clean sync_system_api_console.spec
   ```

## 📝 Notas Importantes

- ✅ **Siempre** instala las dependencias antes de compilar
- ✅ Usa `--clean` para forzar una recompilación completa
- ✅ El archivo spec usa `collect_all()` para incluir dependencias automáticamente
- ✅ El .exe resultante es independiente (no requiere Python instalado)

## 🚀 Prueba del Ejecutable

Después de compilar, prueba el .exe:

```bash
cd dist
SyncAPISystem.exe --mode config
```

Si abre la ventana de configuración, ¡la compilación fue exitosa!
