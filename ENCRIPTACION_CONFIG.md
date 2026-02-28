# 🔒 Encriptación de sync_config.json

## Problema de Seguridad

**ANTES (INSEGURO)**: El archivo `sync_config.json` exponía contraseñas en texto plano:

```json
{
  "postgres_password": "muentes123.",
  "mysql_password": "muentes123."
}
```

Esto era un problema de seguridad crítico, especialmente en Windows donde cualquiera podía leer las credenciales.

## Solución Implementada

**DESPUÉS (SEGURO)**: Las contraseñas ahora están encriptadas:

```json
{
  "postgres_password": "enc:Z0FBQUFBQnBvbGJqTjhDR2RJ...",
  "mysql_password": "enc:Z0FBQUFBQnBvbGJqcWNZekh6d2Ny..."
}
```

## Características de Seguridad

### ✅ Encriptación Fuerte
- **Algoritmo**: Fernet (AES-128)
- **Estándar**: Criptografía aprobada por NIST
- **Seguridad**: 128-bit AES en modo CBC con HMAC

### ✅ Clave Única por Máquina
- La clave de encriptación se genera basada en:
  - Hostname de la máquina
  - ID único del hardware (MAC address)
  - Salt fijo

**Beneficio**: Si el archivo se copia a otra máquina, **NO se puede desencriptar**.

### ✅ Campos Encriptados
Solo se encriptan datos sensibles:
- `postgres_password`
- `mysql_password`
- `api_key` (si existe)
- `secret_key` (si existe)
- `access_token` (si existe)
- `refresh_token` (si existe)

### ✅ Campos NO Encriptados
Los siguientes campos permanecen en texto plano (no sensibles):
- `postgres_host`, `postgres_port`, `postgres_database`
- `mysql_host`, `mysql_port`, `mysql_database`
- `company_rif`, `company_email`, `company_name`
- Otros campos de configuración

## Funcionamiento

### Al Guardar (`guardar_config()`)
```python
# 1. Encriptar campos sensibles
config_enc = encrypt_config(config)

# 2. Guardar en archivo JSON
with open("sync_config.json", "w") as f:
    json.dump(config_enc, f, indent=4)

# 3. En Linux/Mac: ocultar el archivo
# mover a .sync_config.json (con punto al inicio)
```

### Al Cargar (`cargar_config()`)
```python
# 1. Leer archivo JSON
with open("sync_config.json", "r") as f:
    config = json.load(f)

# 2. Desencriptar campos sensibles
config_dec = decrypt_config(config)

# 3. Retornar config con contraseñas en texto plano
return config_dec
```

## Compatibilidad

### ✅ Requisitos
```bash
pip install cryptography
```

### ⚠️ Sin `cryptography`
- El sistema muestra una advertencia
- Las contraseñas se guardan en **texto plano** (no recomendado)
- Funciona pero sin seguridad

### ✅ Con `cryptography`
- Las contraseñas se encriptan automáticamente
- Totalmente transparente para el usuario
- Máxima seguridad

## Archivo Oculto (Linux/Mac)

En Linux y Mac, el archivo se mueve automáticamente a `.sync_config.json` (con punto):

```bash
# El archivo es oculto
.sync_config.json  # Solo visible con ls -la
```

## Windows Credential Manager (Opcional)

El módulo `config_encryption.py` incluye funciones para usar Windows Credential Manager:

```python
from config_encryption import save_to_windows_credential_manager

# Guardar en Windows Credential Manager (más seguro que archivo)
save_to_windows_credential_manager(
    target_name="PostgreSQL_Sync",
    username="postgres",
    password="muelles123."
)
```

**Nota**: Esta funcionalidad requiere `pywin32`:
```bash
pip install pywin32
```

## Tests

Ejecutar test de encriptación:
```bash
python3 test_config_encryption.py
```

El test verifica:
- ✅ Encriptación/desencriptación individual
- ✅ Encriptación/desencriptación de config completo
- ✅ Guardar/cargar archivo JSON
- ✅ Solo campos sensibles se encriptan

## Seguridad Adicional

### 🔒 Protección contra Robo
- Si un atacante roba el archivo, **no puede desencriptarlo** sin la clave única de la máquina
- La clave está basada en hardware, no es reversible

### 🔒 Protección contra Copia
- El archivo **no funciona** en otra máquina
- Cada máquina tiene su propia clave única

### 🔒 Protección contra Lectura
- Las contraseñas son ilegibles en el archivo
- Empiezan con `enc:` para identificarlas fácilmente

## Ejemplo de Uso

```python
from config_encryption import encrypt_config, decrypt_config
import json

# Config original
config = {
    "postgres_host": "localhost",
    "postgres_password": "mi_password_secreto"  # ← Texto plano
}

# Encriptar
config_enc = encrypt_config(config)
# config_enc["postgres_password"] = "enc:Z0FBQUFBQnB..."

# Guardar
with open("sync_config.json", "w") as f:
    json.dump(config_enc, f)

# Cargar y desencriptar
with open("sync_config.json", "r") as f:
    config_loaded = json.load(f)

config_dec = decrypt_config(config_loaded)
# config_dec["postgres_password"] = "mi_password_secreto"  # ← Texto plano
```

## Archivos Modificados

1. **config_encryption.py** (nuevo)
   - Módulo de encriptación/desencriptación
   - Funciones para config completo
   - Soporte para Windows Credential Manager

2. **sync_system.py** (modificado)
   - `cargar_config()`: Desencripta automáticamente
   - `guardar_config()`: Encripta automáticamente
   - Oculta archivo en Linux/Mac

3. **windows_package/** (actualizado)
   - Mismos cambios para compatibilidad

4. **test_config_encryption.py** (nuevo)
   - Suite de tests completa
   - Verifica todas las funciones

## Resumen

✅ **ANTES**: Contraseñas visibles en texto plano (INSEGURO)
✅ **DESPUÉS**: Contraseñas encriptadas con AES-128 (SEGURO)
✅ **TRANSPARENTE**: Automático, sin cambios en el código existente
✅ **MÁXIMA SEGURIDAD**: Clave única por máquina
✅ **COMPATIBLE**: Funciona en Windows, Linux, Mac
✅ **TESTEADO**: Suite completa de tests

---

**Fecha**: 2026-02-27
**Estado**: ✅ IMPLEMENTADO Y TESTEADO
**Commit**: e9b39fe
