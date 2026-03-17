# Categorías Sync - Implementación Completa

## 📋 Resumen

He implementado el módulo completo de sincronización de **Categorías** de PostgreSQL a API REST con las siguientes características:

### ✅ Características Implementadas

| Característica | Descripción |
|----------------|-------------|
| **Detección de cambios** | Usa `sync_hashes` para identificar nuevos/modificados/eliminados |
| **Batch inteligente** | Divide lotes > 5000 automáticamente |
| **Retry automático** | Reintenta en fallos de red con exponential backoff |
| **Rate limiting** | Detecta HTTP 429, espera y reintenta |
| **UPSERT automático** | Si existe actualiza, si no crea |
| **Logging detallado** | Cada operación está loggeada |
| **Estadísticas** | Crea/actualiza/elimina/errors |
| **Memory efficient** | Usa generators para paginación |

---

## 📂 Estructura de Archivos

```
sincronizadorchrystal/
├── api_client/                    # Clientes HTTP reutilizables
│   ├── __init__.py
│   ├── base.py                   # ✅ Cliente base con retry
│   ├── company.py                # ✅ Validación de empresa
│   └── categories.py             # ✅ Cliente de categorías
│
├── sync/                          # Sincronizadores
│   ├── __init__.py
│   ├── base.py                   # ✅ Clase base abstracta
│   └── categories_sync.py        # ✅ Sincronizador de categorías
│
├── test_categories_sync.py       # ✅ Script de prueba
├── sync_config.example.json      # ✅ Configuración de ejemplo
└── CATEGORIES_SYNC_README.md     # ✅ Este archivo
```

---

## 🚀 Uso Rápido

### 1. Configurar `sync_config.json`

```json
{
  "postgres_host": "localhost",
  "postgres_port": "5432",
  "postgres_database": "chrystal_db",
  "postgres_user": "postgres",
  "postgres_password": "password",

  "company_rif": "J-123456789",
  "company_email": "empresa@email.com",
  "company_id": 27,

  "api_config": {
    "base_url": "https://api.chrystal.com/api",
    "api_key": "your-bearer-token-here"
  }
}
```

### 2. Probar el Cliente API (sin PostgreSQL)

```bash
python3 test_categories_sync.py --mode api-only
```

Esto prueba solo la conexión con la API REST.

### 3. Probar Sincronización Completa

```bash
python3 test_categories_sync.py --mode full
```

Esto ejecuta todo el flujo: PostgreSQL → API REST.

---

## 📖 Ejemplo de Uso Programático

```python
import psycopg2
from api_client.categories import CategoriesClient
from sync.categories_sync import CategoriesSync

# Conexión a PostgreSQL
pg_conn = psycopg2.connect(
    host='localhost',
    database='chrystal_db',
    user='postgres',
    password='password'
)

# Cliente de la API
client = CategoriesClient(
    base_url='https://api.chrystal.com/api',
    api_key='your-bearer-token'
)

# Sincronizador
sync = CategoriesSync(
    pg_conn=pg_conn,
    api_client=client,
    company_id=27
)

# Ejecutar sincronización
success = sync.execute()

if success:
    print(f"Created: {sync.stats['created']}")
    print(f"Updated: {sync.stats['updated']}")
    print(f"Deleted: {sync.stats['deleted']}")
```

---

## 🔍 Flujo de Sincronización

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  FLUJO DE SINCRONIZACIÓN DE CATEGORÍAS                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. DETECTAR CAMBIOS                                                        │
│     ├── SELECT * FROM department (PostgreSQL)                              │
│     ├── Comparar con sync_hashes                                          │
│     └── Retornar: nuevos, modificados, eliminados                          │
│                                                                             │
│  2. TRANSFORMAR                                                             │
│     └── Convertir (code, description) → API format                          │
│                                                                             │
│  3. SINCRONIZAR A API                                                       │
│     ├── Dividir en lotes (max 5000)                                        │
│     ├── POST /api/sync-batch/categories                                    │
│     └── Reintentar en errores (retry automático)                           │
│                                                                             │
│  4. ACTUALIZAR SYNC_HASHES                                                  │
│     └── Marcar pending_sync = FALSE                                        │
│                                                                             │
│  5. ELIMINAR (si aplica)                                                   │
│     └── DELETE /api/sync-batch/categories                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Formato de Datos

### PostgreSQL → API

**PostgreSQL (department):**
```sql
SELECT code, description FROM department
-- Resultado: ('ELECTR', 'Electrónica')
```

**API REST Format:**
```json
{
  "name": "ELECTR",
  "description": "Electrónica",
  "status": "active"
}
```

---

## 🛡️ Manejo de Errores

| Error | Manejo |
|-------|--------|
| **Timeout** | Reintenta hasta 3 veces con exponential backoff |
| **Connection Error** | Reintenta hasta 3 veces |
| **Rate Limit (429)** | Espera 2s, 4s, 6s... y reintenta |
| **Auth Error (401)** | Levanta `AuthenticationError` |
| **Validation (422)** | Levanta `ValidationError` |
| **Not Found (404)** | Levanta `NotFoundError` |

---

## 📝 Logs

El sistema genera logs detallados en:

1. **Consola**: Tiempo real
2. **Archivo**: `test_categories_sync.log`

```
2024-03-13 10:00:00 - test_categories_sync - INFO - ======
2024-03-13 10:00:01 - CategoriesSync - INFO - Starting CategoriesSync
2024-03-13 10:00:02 - CategoriesSync - INFO - 🔍 Step 1: Detecting changes...
2024-03-13 10:00:03 - CategoriesSync - INFO - Found 17 categories in PostgreSQL
2024-03-13 10:00:04 - CategoriesSync - INFO - 🚀 Step 2: Syncing to API...
2024-03-13 10:00:05 - CategoriesClient - INFO - Processing batch 1/1 (17 categories)
2024-03-13 10:00:06 - CategoriesClient - INFO - ✅ Batch sync complete: 5 created, 12 updated
2024-03-13 10:00:07 - CategoriesSync - INFO - ✅ Categories synced: 5 created, 12 updated
```

---

## ⚙️ Configuración Avanzada

### Cambiar tamaño de lote

```python
client = CategoriesClient(
    base_url='https://api.chrystal.com/api',
    api_key='token',
    batch_size=1000  # Lotes de 1000 en lugar de 5000
)
```

### Cambiar número de reintentos

```python
client = CategoriesClient(
    base_url='https://api.chrystal.com/api',
    api_key='token',
    max_retries=5  # Reintentar hasta 5 veces
)
```

### Timeout personalizado

```python
client = CategoriesClient(
    base_url='https://api.chrystal.com/api',
    api_key='token',
    timeout=60  # 60 segundos de timeout
)
```

---

## 🧪 Pruebas Unitarias (Siguientes Pasos)

Para productos, customers y sellers, la estructura será idéntica:

```python
from api_client.products import ProductsClient
from sync.products_sync import ProductsSync

# Mismo patrón:
products_sync = ProductsSync(pg_conn, products_client, company_id)
products_sync.execute()
```

---

## ✅ Checklist de Implementación

- [x] `api_client/base.py` - Cliente base con retry
- [x] `api_client/company.py` - Validación de empresa
- [x] `api_client/categories.py` - Cliente de categorías
- [x] `sync/base.py` - Clase base abstracta
- [x] `sync/categories_sync.py` - Sincronizador de categorías
- [x] `test_categories_sync.py` - Script de prueba
- [x] `sync_config.example.json` - Configuración de ejemplo
- [x] Documentación completa

---

## 📞 Soporte

Si encuentras algún error:

1. Revisa `test_categories_sync.log` para detalles
2. Verifica que `sync_config.json` tenga `api_config`
3. Confirma que el API key sea válido

---

## ✅ Products - IMPLEMENTADO

Products ya está implementado con las siguientes características adicionales:

### Características Específicas de Products

| Feature | Descripción |
|---------|-------------|
| **JOIN complejo** | Une products, products_units, products_stock, products_image, taxes, coin, units |
| **Mapeo de categorías** | Convierte department codes a category_ids automáticamente |
| **Transformación segura** | Maneja memoryview, NULLs, y conversiones de tipo |
| **Cache de categorías** | Obtiene mapa de categorías una sola vez y lo reutiliza |

### Archivos Creados para Products

```
api_client/products.py         # ✅ Cliente HTTP para products
sync/products_sync.py          # ✅ Sincronizador de products
test_products_sync.py          # ✅ Script de prueba con 3 modos
```

### Modos de Prueba

```bash
# Probar solo el cliente API
python3 test_products_sync.py --mode api-only

# Sincronización completa
python3 test_products_sync.py --mode full

# Marcar productos como pending y sincronizar
python3 test_products_sync.py --mode pending
```

---

## 🎯 Próximos Pasos

Entidades restantes:

1. **Customers** ✏️ - Estructura similar a categories
2. **Sellers** 👤 - Requiere manejo de users adicionales

¿Quieres que implemente **Customers** ahora?
