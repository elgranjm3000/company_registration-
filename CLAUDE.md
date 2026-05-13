---
name: sincronizadorchrystal
description: Sistema de sincronización Chrystal - Sincronización PostgreSQL ↔ API REST
metadata:
  type: project
  author: elgranjm3000
  language: Python
  platform: Windows
---

# Sistema de Sincronización Chrystal

Sistema de escritorio en Windows que sincroniza datos entre una base de datos PostgreSQL local y una API REST externa (Chrystal Mobile). Opera en segundo plano con un icono en la barra de tareas (System Tray).

## Arquitectura

```
PostgreSQL Local ← Sincronizador Chrystal → API REST (Chrystal Mobile)
```

## Componentes Principales

### Archivos Principales

| Archivo | Propósito |
|---------|----------|
| `sync_system_api.py` | Punto de entrada principal, contiene GUI (Tkinter), gestión de autenticación, System Tray y coordinación |
| `api_client/` | Clientes HTTP para comunicarse con la API REST |
| `sync/` | Módulos de sincronización específicos para cada entidad |
| `config_encryption.py` | Cifrado/decifrado de configuración |

## Clases y Funciones Principales

### `SincronizadorAPI` (Clase principal)
- **Propósito**: Orquestar toda la sincronización
- **Funciones clave**:
  - `autenticar_usuario()`: Validar email/password para acceso
  - `ejecutar_sincronizacion()`: Ejecutar sincronización completa
  - `ejecutar_primera_sync_y_tray()`: Primera configuración + sync + System Tray
  - `mostrar_banner()`: Sistema multiplataforma de notificaciones
  - `get_config()`: Cargar/decifrar configuración desde archivo

### `APIAuthManager` (Gestor de autenticación)
- **Propósito**: Manejar autenticación con API Key
- **Funciones clave**:
  - `ping_api_key(api_key)`: Validar API Key contra `/sync-client/ping`
  - `validate_company(rif, email)`: Validar empresa contra `/sync-client/company/validate`
- **Almacenamiento**: Guarda tokens/keys en memoria (no en disco)

### `APISyncManager` (Gestor de sincronización)
- **Propósito**: Coordinar todos los sincronizadores y manejar PostgreSQL
- **Funciones clave**:
  - `connect_postgresql()`: Conexión a PostgreSQL
  - `initialize_api_clients()`: Inicializar clientes API
  - `sync_all()`: Ejecutar sincronización de todas las entidades
- **Características**:
  - Retry automático con exponential backoff
  - Rate limiting (HTTP 429)
  - Logging detallado de requests

### `ConfigWindow` (GUI de configuración)
- **Propósito**: Ventana para primera configuración
- **Elementos**:
  - Pestaña "API KEY" para ingresar API Key
  - Campos de empresa (RIF, email) que se autocompletan desde el ping
  - Configuración de intervalo de sincronización
  - Botón "Probar Conexión API" que valida el ping

### `SystemTrayService` (System Tray)
- **Propósito**: Ejecutar en segundo plano como icono en barra de tareas
- **Funciones clave**:
  - `iniciar()`: Inicializar icono y loop de sincronización (bloqueante)
  - `bucle_sincronizacion()`: Loop infinito que sincroniza cada N minutos
  - `ejecutar_sincronizacion()`: Ejecutar una sincronización completa
  - `crear_menu_tray()`: Crear menú contextual (Sincronizar, Configurar, Salir)
- **Comportamiento**: 
  - Se mantiene vivo mientras el icono existe
  - Sincronización en thread daemon (no bloquea el proceso principal)

### `ManagerWindow` (GUI de gestión)
- **Propósito**: Ventana para administración avanzada
- **Funciones**:
  - Ver logs
  - Configurar y reconfigurar
  - Ejecutar sincronización manual
  - Verificar estado de conexión

## API Clients

### `BaseAPIClient` (Cliente HTTP base)
- **Patrón**: Singleton para reutilizar conexión
- **Características**:
  - Retry strategy configurable
  - Session pooling y reutilizable
  - Logging automático de requests

### Clientes de Entidad

| Cliente | Endpoints |
|---------|-----------|
| `CompanyClient` | `POST /sync-client/batch/company/validate` |
| `CategoriesClient` | `GET/POST/DELETE /sync-client/batch/categories` |
| `ProductsClient` | `GET/POST/PUT/DELETE /sync-client/batch/products` |
| `CustomersClient` | `GET/POST/PUT/DELETE /sync-client/batch/customers` |
| `SellersClient` | `GET/POST/PUT/DELETE /sync-client/batch/sellers` |
| `QuotesClient` | `GET/POST/PUT/DELETE /sync-client/batch/quotes` |

## Sincronizadores Específicos

### `BaseSync` (Clase base abstracta)
- **Patrón**: Template Method para reutilizar lógica común
- **Flujo**:
  1. Detectar cambios usando `sync_hashes`
  2. Transformar registros a formato API
  3. Sincronizar a la API
  4. Actualizar `sync_hashes`

### `CategoriesSync`
- **Tabla origen**: `department` en PostgreSQL
- **Transformación**: `(code, description) → {name, description, status}`
- **Características especiales**:
  - Sincronización en lotes (batch_size configurable)
  - UPSERT automático (si existe actualiza, si no crea)
  - Detección automática

### `ProductsSync`
- **Tabla origen**: `products` en PostgreSQL
- **Transformación compleja**: Mapeo de campos incluyendo precios en VES/USD
- **Manejo de tipo de cambio**: Detecta si el cambio es de precio, stock u otros
- **Validaciones**: 
  - Campos obligatorios antes de sincronizar
  - Categoría existente verificada
  - Manejo de datos nulos

### `CustomersSync`
- **Tabla origen**: `clients` en PostgreSQL
- **Validación**: Email obligatorio, se valida formato
- **Lógica especial**: Solo sincroniza si la empresa coincide

### `SellersSync`
- **Tabla origen**: `sellers` en PostgreSQL
- **Transformación directa**: Campos mapeados uno a uno

### `QuotesSync`
- **Relaciones**: Sincroniza cotizaciones con sus detalles (líneas, productos)
- **Manejo complejo**: Actualiza o crea cotizaciones relacionadas

## Dependencias Clave

```python
# Base de datos
psycopg2-binary  # PostgreSQL adapter

# Cliente HTTP
requests         # REST API client
urllib3          # Dependencia de requests
certifi          # Certificados SSL

# GUI
tkinter           # Interfaz gráfica (built-in)

# System Tray
pystray          # Icono en barra de tareas
Pillow (PIL)     # Manejo de imágenes para pystray

# Notificaciones Windows
win10toast        # Toast notifications (opcional)
pywin32           # Windows API
pythoncom          # COM para notificaciones

# Seguridad
cryptography       # Encriptación de configuración

# Utilidades
threading         # Concurrencia
queue             # Comunicación entre hilos
json              # Serialización
datetime           # Fechas
logging           # Logging
hashlib           # Hashes MD5
base64            # Codificación
```

## Problemas Resueltos

### 1. Notificaciones Windows - WNDPROC Error
- **Problema**: `TypeError: WPARAM is simple, so must be an int object (got NoneType)` con win10toast
- **Causa**: pywin32 no puede manejar WPARAM=None en callbacks de ventana en ciertos mensajes
- **Solución actual**:
  - Usar `threaded=True` en `ToastNotifier.show_toast()`
  - Forzar `classAtom = None` para evitar conflicto
  - Manejo robusto de excepciones

### 2. Autenticación con API Key
- **Problema**: El login con email/password fue reemplazado por autenticación estática con API Key
- **Solución**: 
  - Endpoint `/sync-client/ping` para validar token
  - Tokens guardados en memoria (no en disco por seguridad)
  - Empresa autocompletada desde respuesta del ping (RIF, email)

### 3. Detección de Cambios Eficiente
- **Problema**: Sincronizar tablas grandes era lento y generaba muchos cambios
- **Solución**: 
  - Tabla `sync_hashes` con hashes MD5 de cada registro
  - Solo se sincronizan registros que han cambiado (hash diferente)
  - Trigger PostgreSQL para marcar automáticamente registros modificados

### 4. Manejo de Errores y Retries
- **Problema**: Conexiones fallidas, timeouts, errores del servidor
- **Solución**:
  - Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s, 60s (máx)
  - Diferentes timeouts según tipo de error:
    - 10s: conexión/lectura
    - 20s: escritura
    - 60s: server errors (5xx)
  - Límite de rate: espera HTTP 429 antes de reintentar

## Flujo de Sincronización Detallado

```
1. Validación de API Key
   ↓
2. Conexión a PostgreSQL
   ↓
3. Detección de cambios en sync_hashes
   ↓
4. Para cada entidad (Categories → Products → Customers → Sellers → Quotes):
   a. Leer registros modificados
   b. Transformar a formato API
   c. Sincronizar (batch)
   d. Actualizar sync_hashes
   ↓
5. Esperar intervalo configurado
   ↓
6. Repetir desde paso 1
```

## Configuración

### Archivo de Configuración
- **Ubicación**: `~/.chrystal_sync_config.json` (home del usuario en Windows)
- **Campos**:
  ```json
  {
    "api_url": "https://chrystal.com.ve/mobiletest/public/api",
    "api_key": "<API_KEY_ENCRYPTADO>",
    "company_rif": "J-XXXXXXXX-X",
    "company_email": "empresa@ejemplo.com",
    "company_id": 123,
    "postgres_host": "localhost",
    "postgres_port": 5432,
    "postgres_database": "chrystal_db",
    "postgres_user": "postgres",
    "postgres_password": "<PASSWORD_ENCRYPTADO>",
    "sync_interval_minutes": 30
  }
  ```
- **Campos sensibles**: `api_key`, `postgres_password`, `postgres_user` están encriptados con AES (Fernet)

## Esquemas de la Base de Datos PostgreSQL

### Tablas Principales

| Tabla | Propósito |
|-------|----------|
| `products` | Productos con precios en VES/USD |
| `clients` | Clientes (clientes) |
| `department` | Departamentos (categorías) |
| `sellers` | Vendedores |
| `quotes` | Cotizaciones |
| `quote_lines` | Líneas de cotización |
| `quote_products` | Productos en cotización |
| `company` | Empresas (para validación) |

### Tabla de Sistema

| Tabla | Propósito |
|-------|----------|
| `sync_hashes` | Registro de hashes MD5 para detección de cambios |

```sql
CREATE TABLE sync_hashes (
    table_name VARCHAR(50),
    record_key VARCHAR(50),
    record_hash VARCHAR(32),
    pending_sync BOOLEAN DEFAULT TRUE
);
```

## Compilación

### Especifices de PyInstaller

**Para versión SIN consola (producción):**
- Archivo: `windows_api/sync_system_api_windowed.spec`
- Características:
  - `console=False` - No muestra ventana de consola
  - Oculta todas las dependencias (win10toast, pystray, etc.)
  - Icono: `icon.ico` si existe

**Para versión CON consola (debug):**
- Archivo: `windows_api/sync_system_api_console.spec`
- Características:
  - `console=True` - Muestra consola para diagnóstico
  - Todas las demás dependencias iguales

### Script de Compilación

**Para compilar SIN consola:**
```batch
@echo off
cd /d "%~dp0"
pyinstaller sync_system_api_windowed.spec
```

**Para compilar CON consola:**
```batch
@echo off
cd /d "%~dp0"
pyinstaller sync_system_api_console.spec
```

## Modos de Ejecución

### Modo Automático (.exe compilado)
- Ejecutable: `SyncAPISystem.exe`
- Sin argumentos
- Flujo:
  1. Si no existe config → abre `ConfigWindow` para configurar
  2. Si existe config → valida API Key, sincroniza una vez, inicia System Tray
  3. System Tray se mantiene en barra de tareas sincronizando automáticamente

### Modo Configuración
```bash
python sync_system_api.py --mode config
```
Abre ventana de configuración (requiere autenticación previa con email/password).

### Modo Administración
```bash
python sync_system_api.py --mode manager
```
Abre ventana de gestión con logs y controles.

### Modo Sincronización Única
```bash
python sync_system_api.py --mode sync
```
Ejecuta una sincronización completa y sale.

### Modo Servicio (loop infinito)
```bash
python sync_system_api.py --mode service
```
Sincroniza continuamente cada intervalo configurado.

### Modo System Tray
```bash
python sync_system_api.py --mode tray
```
Ejecuta como System Tray en la barra de tareas.

## Notificaciones Multiplataforma

### Windows
```python
win10toast.ToastNotifier().show_toast(
    title="Título",
    msg="Mensaje", 
    duration=5,
    threaded=True,  # Importante para evitar errores de WPARAM
    icon_path="icon.ico"
)
```

### Linux
```python
import notify2
notify2.init("Sincronizador Chrystal")
n = notify2.Notification("Título", "Mensaje", "icon.png")
n.set_timeout(5000)  # milisegundos
n.show()
```

### macOS
```python
import subprocess
subprocess.run([
    'terminal-notifier',
    '-title', 'Título',
    '-message', 'Mensaje',
    '-timeout', '5'
])
```

## Historial de Cambios Recientes

- Migración de autenticación email/password → API Key estática
- Implementación de detección eficiente de cambios (sync_hashes)
- Cambio de endpoints `/sync-batch/` → `/sync-client/batch/`
- Implementación de System Tray para operación en segundo plano
- Múltiples correcciones en manejo de errores y retries
