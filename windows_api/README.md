# Sync API System - Versión Windows

Sistema de sincronización PostgreSQL → API REST para Windows con interfaz gráfica y soporte para system tray.

## 📋 Requisitos

- **Windows 7 o superior**
- **Python 3.8 o superior**
- **Dependencias de Python** (se instalan automáticamente con `VERIFICAR_DEPENDENCIAS.bat`)

## 🚀 Instalación Rápida

### 1. Verificar Dependencias

Ejecuta el archivo **`VERIFICAR_DEPENDENCIAS.bat`** para instalar todas las dependencias necesarias:

```cmd
VERIFICAR_DEPENDENCIAS.bat
```

Este archivo instalará:
- `psycopg2-binary` - Conector PostgreSQL
- `requests` - Cliente HTTP
- `pystray` - Icono en bandeja del sistema
- `Pillow` - Manejo de imágenes para iconos
- `cryptography` - Encriptación de contraseñas

### 2. Configurar el Sistema

Ejecuta **`CONFIGURAR.bat`** para abrir la ventana de configuración:

```cmd
CONFIGURAR.bat
```

Completa los siguientes datos:
- **URL de la API**: https://api.ejemplo.com
- **Email de la API**: tu@email.com
- **RIF de la empresa**: J-12345678-9
- **Email de la empresa**: empresa@email.com
- **Host PostgreSQL**: localhost
- **Puerto PostgreSQL**: 5432
- **Base de datos**: postgres
- **Usuario PostgreSQL**: postgres
- **Contraseña PostgreSQL**: ****

### 3. Ejecutar el Sistema

#### ✅ Después de Configurar (Automático)

Cuando guardas la configuración por primera vez, el sistema **automáticamente**:

1. **Verifica la conexión** con PostgreSQL (3 pasos: PostgreSQL → API Login → Validar Empresa)
2. **Ejecuta la primera sincronización** completa con ventana de progreso
3. **Inicia el modo System Tray** en la barra de tareas

Todo esto es **automático** - no necesitas hacer nada más después de configurar.

#### Ejecuciones Manuales

Después de la configuración inicial, puedes ejecutar el sistema manualmente de diferentes formas:

## 🎯 Modos de Ejecución

### 🖥️ Manager (Modo Administrador - GUI)

Abre la ventana del administrador con:
- Panel de estado del sistema
- Estadísticas de sincronización
- Botones individuales para cada entidad
- Visor de logs en tiempo real

```cmd
MANAGER.bat
```

O desde línea de comandos:
```cmd
python sync_system_api.py --mode manager
```

### 🔄 Sincronización Única (Consola)

Ejecuta una sincronización única en modo consola:

```cmd
EJECUTAR.bat
```

O desde línea de comandos:
```cmd
python sync_system_api.py --mode sync
```

### 🔔 System Tray (Modo Servicio - Transparente)

Inicia el sistema en segundo plano con icono en la barra de tareas:

```cmd
TRAY.bat
```

O desde línea de comandos:
```cmd
python sync_system_api.py --mode tray
```

**Características del modo System Tray:**
- Se ejecuta en segundo plano sin ventana visible
- Icono en la barra de tareas (junto al reloj)
- Menú contextual (clic derecho):
  - 🖥️ Abrir Manager
  - 📊 Ver Logs
  - 🔄 Sincronizar Ahora
  - ⚙️ Configuración
  - ❌ Salir
- **Auto-inicio**: Se configura automáticamente en el registro de Windows para iniciarse al encender el equipo

### 🐛 Modo Debug

Ejecuta el sistema con logs detallados para diagnóstico:

```cmd
DEBUG.bat
```

## 📂 Estructura de Archivos

```
windows_api/
├── sync_system_api.py          # Archivo principal
├── config_encryption.py        # Encriptación de contraseñas
├── sync_config.example.json    # Ejemplo de configuración
├── sync_config_api.json        # Configuración actual (se crea automáticamente)
│
├── api_client/                 # Clientes HTTP para la API
│   ├── __init__.py
│   ├── base.py                # Cliente base con reintentos
│   ├── categories.py          # Cliente de categorías
│   ├── products.py            # Cliente de productos
│   ├── customers.py           # Cliente de clientes
│   ├── sellers.py             # Cliente de vendedores
│   ├── quotes.py              # Cliente de cotizaciones
│   └── company.py             # Cliente de empresas
│
├── sync/                       # Sincronizadores
│   ├── __init__.py
│   ├── base.py                # Sincronizador base
│   ├── categories_sync.py     # Sincronizador de categorías
│   ├── products_sync.py       # Sincronizador de productos
│   ├── customers_sync.py      # Sincronizador de clientes
│   ├── sellers_sync.py        # Sincronizador de vendedores
│   └── quotes_sync.py         # Sincronizador de cotizaciones
│
├── CONFIGURAR.bat              # Configurar el sistema
├── MANAGER.bat                 # Abrir administrador
├── EJECUTAR.bat                # Sincronizar una vez
├── TRAY.bat                    # Iniciar en modo System Tray
├── DEBUG.bat                   # Modo debug
├── VERIFICAR_DEPENDENCIAS.bat  # Instalar dependencias
└── README.md                   # Este archivo
```

## 📊 Entidades Sincronizadas

El sistema sincroniza las siguientes entidades desde PostgreSQL hacia la API:

1. **Categories** - Categorías de productos
2. **Products** - Productos con precios y unidades
3. **Customers** - Clientes
4. **Sellers** - Vendedores
5. **Quotes** - Cotizaciones (bidireccional: API → PostgreSQL → API)

## 🔐 Seguridad

- Las contraseñas de PostgreSQL se almacenan **encriptadas** en `sync_config_api.json`
- Utiliza `cryptography.fernet` para encriptación AES-128
- Nunca almacena contraseñas en texto plano

## 📝 Logs

Los logs se guardan en:
```
logs/sync_api_{email}.log
```

Incluyen:
- 📤 Peticiones HTTP a la API
- 📥 Respuestas de la API
- ⚠️ Errores y advertencias
- 🔄 Estado de sincronización
- 📊 Estadísticas

## ⚙️ Configuración

### Auto-inicio en Windows

Al ejecutar **`TRAY.bat`** por primera vez, el sistema se configura automáticamente para iniciarse al encender Windows.

**Registro:**
- **Ruta**: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
- **Nombre**: `SyncAPISystemTray`
- **Valor**: `"python.exe" "sync_system_api.py" --mode tray`

### Intervalo de Sincronización

Por defecto, el sistema sincroniza cada **30 minutos**.

Para cambiar el intervalo, edita `sync_config_api.json`:
```json
{
  "sync_interval_minutes": 60
}
```

## 🔧 Solución de Problemas

### Error: "No se pudo conectar a PostgreSQL"

**Soluciones:**
1. Verifica que PostgreSQL esté ejecutándose
2. Verifica las credenciales en `sync_config_api.json`
3. Verifica que el firewall permita conexiones al puerto 5432

### Error: "No se pudo conectar a la API"

**Soluciones:**
1. Verifica tu conexión a internet
2. Verifica que la URL de la API sea correcta
3. Verifica tus credenciales (email y password)

### Error: "No se pudo crear el icono"

**Soluciones:**
1. Ejecuta `VERIFICAR_DEPENDENCIAS.bat`
2. Asegúrate de tener `pystray` y `Pillow` instalados:
   ```cmd
   pip install pystray Pillow
   ```

### Error: "No se pudo importar psycopg2"

**Soluciones:**
1. Ejecuta `VERIFICAR_DEPENDENCIAS.bat`
2. O instala manualmente:
   ```cmd
   pip install psycopg2-binary
   ```

### Error: "El icono no existe" (auto-inicio)

**Soluciones:**
1. Reconfigura el sistema con `CONFIGURAR.bat`
2. O ejecuta `TRAY.bat` nuevamente para actualizar el registro

## 📱 Uso desde Línea de Comandos

```cmd
# Configurar
python sync_system_api.py --mode config

# Sincronizar una vez
python sync_system_api.py --mode sync

# Abrir manager
python sync_system_api.py --mode manager

# Iniciar system tray
python sync_system_api.py --mode tray

# Reconfigurar
python sync_system_api.py --mode reconfig
```

## 🎨 Características del Manager

El **Manager** es una interfaz gráfica que permite:

- **Panel de Estado**: Muestra si el sistema está activo o no configurado
- **Estadísticas**: Muestra contadores de entidades sincronizadas
- **Sincronización Individual**: Sincroniza entidades por separado:
  - Categories
  - Products
  - Customers
  - Sellers
  - Quotes
- **Botón Sincronizar Todo**: Ejecuta sincronización completa
- **Visor de Logs**: Muestra logs en tiempo real con colores
- **Botón Ver Logs**: Abre el archivo de logs en el editor de texto
- **Botón Reconfigurar**: Permite reconfigurar el sistema

## 🔄 Flujo de Sincronización

1. **Detectar Cambios**: Compara hashes MD5 para identificar cambios
2. **Preparar Lotes**: Organiza datos en lotes de 5000 registros
3. **Enviar a API**: Utiliza endpoints batch de la API
4. **Procesar Respuesta**: Actualiza hashes de registros sincronizados
5. **Reintentos**: Reintenta automáticamente en errores 5xx (errores del servidor)
6. **Estadísticas**: Muestra resultados (creados, modificados, sin cambios)

## 📞 Soporte

Si encuentras algún error o necesitas ayuda:

1. Revisa los logs en `logs/sync_api_{email}.log`
2. Ejecuta en modo debug: `DEBUG.bat`
3. Verifica las credenciales en `sync_config_api.json`

## 📄 Licencia

Este software es parte del sistema de sincronización Chrystal.

---

**Versión**: 1.0.0
**Fecha**: Marzo 2026
**Sistema**: Windows 7+
**Python**: 3.8+
