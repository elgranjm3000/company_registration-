# 📦 Cómo crear el ejecutable .exe

## ⚠️ PROBLEMA CRÍTICO: Encriptación de contraseñas

Si creas el .exe sin incluir `config_encryption.py`, **las contraseñas quedarán expuestas** en texto plano en `sync_config.json`.

## ✅ SOLUCIÓN: Usar el script de build

### Opción 1: Script automatizado (RECOMENDADO)

```bash
# En Linux/Mac
python3 build_exe.py

# En Windows
python build_exe.py
```

Este script:
- ✅ Incluye `config_encryption.py` en el .exe
- ✅ Incluye todas las librerías de criptografía
- ✅ Verifica que la encriptación funcione

### Opción 2: PyInstaller manual

Si prefieres usar PyInstaller manualmente, **DEBES** incluir estos parámetros:

```bash
pyinstaller --onefile --name SyncSystem ^
    --hidden-import config_encryption ^
    --hidden-import cryptography ^
    --hidden-import cryptography.fernet ^
    --hidden-import cryptography.hazmat ^
    --hidden-import cryptography.hazmat.primitives ^
    --hidden-import cryptography.hazmat.backends ^
    --hidden-import psycopg2 ^
    --hidden-import pymysql ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import win10toast ^
    --add-data "config_encryption.py;." ^
    --add-data "smart_sync_complete.py;." ^
    --console sync_system.py
```

## 🔍 Verificar que la encriptación funciona

Después de crear el .exe:

1. **Ejecuta el .exe y configura las bases de datos**
2. **Abre el archivo `sync_config.json` que se cree**
3. **Verifica que las contraseñas tengan el prefijo `enc:`**:

```json
{
    "postgres_password": "enc:Z0FBQUFBQnB...",
    "mysql_password": "enc:Z0FBQUFBQnB..."
}
```

Si ves las contraseñas en texto plano (sin `enc:`), **ALGO ESTÁ MAL**.

## 📋 Archivos necesarios junto al .exe

El .exe necesita estos archivos en el mismo directorio:

- ✅ `smart_sync_complete.py` - Obligatorio
- ✅ `config_encryption.py` - Incluido en el .exe (opcional)
- ✅ `cryptography` - Debe estar instalado

## 🚨 Errores comunes

### Error: "No module named 'config_encryption'"

**Solución**: Agrega `--hidden-import config_encryption`

### Error: "No module named 'cryptography'"

**Solución**: Instala cryptography:
```bash
pip install cryptography
```

### Error: Las contraseñas están en texto plano

**Solución**: Verifica que `config_encryption.py` esté incluido con `--add-data`

## ✅ Verificación final

Después de crear el .exe, ejecuta este test:

```python
# test_exe_encryption.py
import subprocess
import json
import os

# Ejecutar el exe y crear config
subprocess.run(["SyncSystem.exe", "--mode", "config"])

# Verificar el config
if os.path.exists("sync_config.json"):
    with open("sync_config.json", "r") as f:
        config = json.load(f)

    if config.get("postgres_password", "").startswith("enc:"):
        print("✅ Encriptación FUNCIONANDO")
    else:
        print("❌ Encriptación FALLANDO - Contraseñas en texto plano")
```

## 📦 Resumen

1. **Usa `build_exe.py`** (opción recomendada)
2. **Verifica** que `sync_config.json` tenga `enc:`
3. **Distribuye** el .exe junto con `smart_sync_complete.py`

---

**Fecha**: 2026-02-27
**Estado**: ✅ Activo
**Prioridad**: 🔴 CRÍTICO - Seguridad de contraseñas
