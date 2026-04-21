# FLUJO DE SINCRONIZACIÓN DE QUOTES (API → PostgreSQL)

## Resumen del Flujo

```
API REST (endpoint) → QuotesSync → PostgreSQL (sales_operation)
```

## 1. Endpoint de la API

**URL:** `GET /api/sync-batch/quotes`

**Parámetros:**
- `company_id`: ID de la empresa
- `status`: 'draft' (solo cotizaciones en borrador)

**Respuesta JSON:**
```json
{
  "quotes": [
    {
      "id": 15,
      "quote_number": "QUOTE-001",
      "quote_date": "2026-03-18T10:00:00.000000Z",
      "created_at": "2026-03-18T09:00:00.000000Z",
      "status": "draft",
      "subtotal": 1000.00,
      "tax_amount": 160.00,
      "discount_amount": 0.00,
      "total": 1160.00,

      "customer": {
        "document_number": "J-12345678-9",  ← RIF del cliente (campo clave)
        "code": "C001",
        "name": "Alejandro Jaimez",
        "address": "Av. Principal #123",
        "phone": "0414-1234567"
      },

      "seller": {
        "code": "V001",  ← Código del vendedor (campo clave)
        "name": "Juan Pérez",
        "id": 5
      },

      "items": [
        {
          "product": {
            "code": "PROD001"
          },
          "name": "Producto A",
          "quantity": 10,
          "unit_price": 100.00,
          "discount_amount": 0.00,
          "tax_amount": 160.00,
          "total": 1160.00
        }
      ]
    }
  ]
}
```

## 2. Procesamiento en QuotesSync

### Paso 2.1: Detectar Cambios (`detect_changes()`)

```python
# Obtener quotes de la API
quotes_api = self.quotes_client.get_pending_quotes(self.company_id)

# Para cada quote, verificar si ya existe en sync_hashes
for quote in quotes_api:
    quote_id = quote.get('id')

    self.pg_cursor.execute("""
        SELECT record_hash FROM sync_hashes
        WHERE table_name = 'quotes'
          AND record_key = %s
          AND company_id = %s
    """, (str(quote_id), self.company_id))

    resultado = self.pg_cursor.fetchone()

    if resultado is None:
        cambios['nuevos'].append(quote)  # Nuevo quote
```

### Paso 2.2: Buscar Cliente en tabla `clients`

```python
# Datos del cliente desde la API
customer = quote.get('customer') or {}
customer_document_number = customer.get('document_number') or ''  # RIF
customer_code_api = customer.get('code') or ''
customer_name = customer.get('name') or ''

# Buscar en tabla clients usando el RIF (document_number)
search_value = customer_document_number if customer_document_number else customer_code_api

if search_value:
    self.pg_cursor.execute("""
        SELECT code FROM clients WHERE code = %s LIMIT 1
    """, (search_value,))
    result = self.pg_cursor.fetchone()

    if result:
        client_code = result[0]  # Este es el code que se usará en sales_operation
        client_found = True
```

**IMPORTANTE:** El RIF viene en `customer.document_number` y se busca en `clients.code`.

### Paso 2.3: Obtener Código del Vendedor

```python
# Datos del vendedor desde la API
seller = quote.get('seller') or {}

# Usar seller.code directamente, o NULL si no existe
seller_code = seller.get('code') if seller.get('code') else None
seller_name = seller.get('name') or ''  # Solo para mostrar, no se usa en FK
```

**IMPORTANTE:**
- Se usa `seller.code` directamente del endpoint
- Si `seller.code` está vacío o es None, se deja como `NULL` en sales_operation
- El campo `seller` en `sales_operation` es una FK a `sellers.code`

### Paso 2.4: Insertar en `sales_operation`

```python
sql_operation = """
    INSERT INTO sales_operation (
        operation_type, document_no, emission_date, register_date,
        client_code, client_name, client_address, client_phone,
        seller, total_amount, total_tax, discount, total,
        pending, canceled, coin_code,
        address_send, contact_send, phone_send
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    RETURNING correlative
"""

self.pg_cursor.execute(sql_operation, (
    'BUDGET',              # operation_type (fijo para quotes)
    str(quote_number),     # document_no
    emission_date,         # emission_date
    register_date,         # register_date
    client_code,           # client_code (obtenido de consulta a clients)
    client_name,           # client_name
    client_address,        # client_address
    client_phone,          # client_phone
    seller_code,           # seller ← seller.code de la API o NULL
    total_amount,          # total_amount
    tax_amount,            # total_tax
    discount_amount,       # discount
    total,                 # total
    False,                 # pending
    False,                 # canceled
    '02',                  # coin_code (código de moneda: 02 = USD)
    '',                    # address_send (vacío)
    '',                    # contact_send (vacío)
    ''                     # phone_send (vacío)
))

correlative = self.pg_cursor.fetchone()[0]
```

### Paso 2.5: Insertar Items en `sales_operation_details`

```python
for item in items:
    product = item.get('product', {})
    product_code = product.get('code') if product else None

    sql_detalle = """
        INSERT INTO sales_operation_details (
            correlative, product_code, description,
            quantity, unit_price, discount, tax, total
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    self.pg_cursor.execute(sql_detalle, (
        correlative,
        product_code,
        item.get('name', ''),
        float(item.get('quantity', 0)),
        float(item.get('unit_price', 0)),
        float(item.get('discount_amount', 0)),
        float(item.get('tax_amount', 0)),
        float(item.get('total', 0))
    ))
```

### Paso 2.6: Actualizar Estado en la API

```python
# Marcar como 'approved' en la API
if self.quotes_client.update_quote_status(quote_id, self.company_id, 'approved'):
    self._log(f"Estado actualizado en API: {quote_id} → approved", "info")
```

### Paso 2.7: Guardar Hash en `sync_hashes`

```python
hash_value = self._generar_hash_quote(quote)

self.pg_cursor.execute("""
    INSERT INTO sync_hashes (table_name, record_key, record_hash, company_id, pending_sync, deleted_at)
    VALUES ('quotes', %s, %s, %s, FALSE, NULL)
""", (str(quote_id), hash_value, self.company_id))
```

## 3. Mapeo de Campos

| Campo API | Campo PostgreSQL | Observaciones |
|-----------|------------------|---------------|
| `quote_number` | `document_no` | Convertido a string |
| `quote_date` | `emission_date` | Parseado desde ISO format |
| `created_at` | `register_date` | Parseado desde ISO format |
| `customer.document_number` | `client_code` | **Se busca en tabla clients** |
| `customer.name` | `client_name` | Copia directa |
| `customer.address` | `client_address` | Copia directa |
| `customer.phone` | `client_phone` | Copia directa |
| `seller.code` | `seller` | **Directo o NULL** |
| `subtotal` | `total_amount` | Convertido a float |
| `tax_amount` | `total_tax` | Convertido a float |
| `discount_amount` | `discount` | Convertido a float |
| `total` | `total` | Convertido a float |
| - | `coin_code` | **Fijo: '02'** |
| - | `operation_type` | **Fijo: 'BUDGET'** |
| `items[].product.code` | `product_code` | Directo |
| `items[].name` | `description` | Directo |
| `items[].quantity` | `quantity` | Convertido a float |
| `items[].unit_price` | `unit_price` | Convertido a float |
| `items[].discount_amount` | `discount` | Convertido a float |
| `items[].tax_amount` | `tax` | Convertido a float |
| `items[].total` | `total` | Convertido a float |

## 4. Llaves Foráneas

### `client_code`
```sql
FOREIGN KEY (client_code) REFERENCES clients(code)
```
- Se obtiene buscando en `clients.code` usando el `customer.document_number` (RIF)

### `seller`
```sql
FOREIGN KEY (seller) REFERENCES sellers(code)
```
- Se usa `seller.code` directamente de la API
- Si no existe, se deja como `NULL`

### `coin_code`
```sql
FOREIGN KEY (coin_code) REFERENCES coin(code)
```
- Fijo: `'02'` (USD)

### `product_code` (en sales_operation_details)
```sql
FOREIGN KEY (product_code) REFERENCES products(code)
```
- Se usa `item.product.code` directamente de la API

## 5. Errores Comunes y Soluciones

### Error 1: Cliente no encontrado
```
❌ Cliente no encontrado en tabla clients. Document_Number='', Code=''
```
**Solución:** Verificar que `customer.document_number` viene con valor desde la API

### Error 2: Seller no existe
```
❌ inserción o actualización en la tabla «sales_operation» viola la llave foránea «sales_operation_seller_fkey»
```
**Solución:** Verificar que `seller.code` existe en la tabla `sellers`, o dejar como `NULL`

### Error 3: Coin no existe
```
❌ inserción o actualización en la tabla «sales_operation» viola la llave foránea «sales_operation_coin_code_fkey»
```
**Solución:** Usar `'02'` en lugar de `'USD'`

## 6. Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────┐
│  API REST                                                        │
│  GET /api/sync-batch/quotes?company_id=X&status=draft           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  QuotesSync.detect_changes()                                     │
│  - Obtener quotes de la API                                      │
│  - Verificar en sync_hashes si son nuevos                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  QuotesSync.sync_to_postgresql()                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Para cada quote nuevo:                                  │    │
│  │                                                          │    │
│  │  1. Buscar cliente:                                     │    │
│  │     customer.document_number → clients.code              │    │
│  │                                                          │    │
│  │  2. Obtener seller:                                     │    │
│  │     seller.code (directo o NULL)                         │    │
│  │                                                          │    │
│  │  3. Insertar sales_operation                            │    │
│  │                                                          │    │
│  │  4. Insertar sales_operation_details (items)             │    │
│  │                                                          │    │
│  │  5. Actualizar estado en API: draft → approved           │    │
│  │                                                          │    │
│  │  6. Guardar hash en sync_hashes                         │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PostgreSQL                                                      │
│  ├─ sales_operation (encabezado)                                │
│  └─ sales_operation_details (items)                             │
└─────────────────────────────────────────────────────────────────┘
```

## Archivos de Código

- `sync/quotes_sync.py` - Lógica de sincronización
- `api_client/quotes.py` - Cliente HTTP para la API
- `mostrar_quotes_registrados.py` - Script para ver datos registrados
- `debug_quotes_api.py` - Script para ver endpoint de la API
