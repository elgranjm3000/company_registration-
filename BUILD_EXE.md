# 📦 Cómo crear el ejecutable .exe

## 🔒 PROTECCIÓN DEL CÓDIGO FUENTE

### ⚠️ ¿El cliente puede ver tu código?

**SÍ, si no compilas con encriptación.**

Con PyInstaller hay 3 niveles de protección:

| Nivel | Comando | Protección | El cliente puede ver código |
|-------|---------|------------|----------------------------|
| 1. Sin encriptación | `pyinstaller file.spec` | ❌ Ninguna | ✅ SÍ (fácil de extraer) |
| 2. Con clave | `pyinstaller --key "CLAVE" file.spec` | 🔐 Media | ⚠️ Difícil (necesita clave) |
| 3. PyArmor | `pyarmor pack file.py` | 🛡️ Muy Alta | ❌ Casi imposible |

### ✅ TU CONFIGURACIÓN ACTUAL: PROTEGIDA CON CLAVE

Los archivos `.spec` ya tienen encriptación configurada:

```python
block_cipher = bytes.fromhex('1c99a2c513420a908c50aa6bea5d914a')
```

**Para compilar con protección:**

```bash
# Windows
pyinstaller --onefile --name SyncSystem ^
    --key "1c99a2c513420a908c50aa6bea5d914a" ^
    sync_system.py

# O usando el archivo .spec (YA CONFIGURADO)
pyinstaller sync_system.spec
```

**Resultado:** El código está encriptado dentro del .exe 🔐

### ⚠️ PROBLEMA CRÍTICO: Encriptación de contraseñas

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

- ✅ `smart_sync_complete.py` - **EMPACADO DENTRO del .exe** (encriptado con la clave)
- ✅ `config_encryption.py` - Incluido en el .exe (opcional)
- ✅ `cryptography` - Debe estar instalado

### ✅ BUENA NOTICIA

El archivo **`smart_sync_complete.py`** está empaquetado DENTRO del .exe porque `sync_system.py` lo importa como módulo:

```python
import smart_sync_complete  # ← En sync_system.py
```

**Esto significa que:**
- ✅ El cliente **NO PUEDE** abrir `smart_sync_complete.py` (está dentro del .exe)
- ✅ El código está **encriptado con la clave** `1c99a2c513420a908c50aa6bea5d914a`
- ⚠️ Un atacante podría extraer el .pyc y desencriptarlo (difícil pero posible)

### 🔒 Si necesitas MÁXIMA protección

Si el código es **extremadamente confidencial** y no quieres que nadie lo vea nunca:

**Opción 1: Usar PyArmor** (Máxima protección)

```bash
# Instalar PyArmor
pip install pyarmor

# Ofuscar smart_sync_complete.py
pyarmor obfuscate smart_sync_complete.py

# Esto crea smart_sync_complete.py obfuscado (ilegible)
# El archivo original se renombra a smart_sync_complete.py.bak
```

**Opción 2: Mover lógica crítica a servidor**

- Coloca el algoritmo de sincronización en un servidor web
- El .exe solo hace llamadas HTTP a tu API
- El cliente nunca ve el código fuente

### 🔒 Niveles de protección alcanzados:

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
2. **Verifica** que `sync_config.json` tenga `enc:` (contraseñas encriptadas)
3. **Protege el código** con `--key` o PyArmor
4. **Distribuye SOLO el .exe** (todo está empaquetado dentro):
   - ✅ `dist/SyncSystem.exe` o `dist/CompanyRegistration.exe`
   - ⚠️ NO necesitas `smart_sync_complete.py` (ya está dentro)
   - ✅ Iconos y assets si los hay (están incluidos en el .exe)

### 🔒 Niveles de protección alcanzados:

| Componente | Protección actual | ¿Cliente puede ver? |
|------------|-------------------|---------------------|
| sync_system.py (en .exe) | 🔐 Encriptado con clave | ⚠️ Difícil pero posible |
| smart_sync_complete.py (en .exe) | 🔐 Encriptado con clave | ⚠️ Difícil pero posible |
| Contraseñas en config | 🔐 Encriptadas Fernet | ❌ No (sin la clave maestra) |

### 📌 Recomendación final

**Tu configuración ACTUAL ofrece:**
- ✅ **Buena protección** para código fuente (encriptado con clave)
- ✅ **Excelente protección** para contraseñas (Fernet encryption)
- ⚠️ **No es imposible** de reverse engineering, pero es **difícil**

**Para clientes estándar:** Esta protección es **SUFICIENTE**

**Para clientes técnicos o si necesitas máxima seguridad:** Considera PyArmor o arquitectura servidor-cliente

---

**Fecha**: 2026-02-27
**Estado**: ✅ Activo
**Prioridad**: 🔴 CRÍTICO - Seguridad de contraseñas
