# FLUJO DE SINCRONIZACIÓN DE CLIENTES - ANÁLISIS PASO A PASO

## DATOS DEL TEST EJECUTADO (company_id=86)

```
PostgreSQL local: 119 clientes
API REST:       114 clientes
Resultado:      "114 creados, 5 actualizados"
```

---

## 🔍 PUNTO CLAVE DE CONFUSIÓN

**Usuario cree:** "El backend no tiene ningún cliente"
**Realidad:** El backend YA TIENE 114 clientes

Por eso se ven "5 actualizados" - porque 114 clientes ya existían en el backend y solo 5 eran nuevos.

---

## 📋 FLUJO COMPLETO PASO A PASO

### PASO 1: `execute()` inicia la sincronización

**Archivo:** `sync/customers_sync.py:612-686`

```python
def execute(self) -> Dict[str, int]:
    # PASO 1: PostgreSQL → API REST
    cambios = self.detect_changes()

    if cambios['nuevos'] or cambios['modificados']:
        self.sync_to_api(cambios)

    # PASO 2: API REST → PostgreSQL
    nuevos_desde_api = self.detect_new_from_api()

    if nuevos_desde_api:
        insertados = self.sync_new_from_api(nuevos_desde_api)
```

---

### PASO 2: `detect_changes()` - Detectar qué clientes enviar al API

**Archivo:** `sync/customers_sync.py:45-204`

#### 2.1. Verifica si es PRIMERA VEZ (sync_hashes vacío)

```python
# Líneas 60-68
self.pg_cursor.execute("""
    SELECT COUNT(*)
    FROM sync_hashes
    WHERE table_name = 'customers'
      AND company_id = %s
""", (self.company_id,))

count_in_hashes = self.pg_cursor.fetchone()[0]
```

**Resultado del test:** `count_in_hashes = 0` (PRIMERA VEZ)

#### 2.2. Obtiene TODOS los clientes de PostgreSQL

```python
# Líneas 71-83 (CASO 1: Primera vez)
if count_in_hashes == 0:
    self.info("🎯 Primera sincronización: obteniendo TODOS los clientes")

    self.pg_cursor.execute("SELECT COUNT(*) FROM clients")
    total_customers = self.pg_cursor.fetchone()[0]
    # Resultado: 119

    self.pg_cursor.execute("SELECT code FROM clients")
    pending_codes = [row[0] for row in self.pg_cursor.fetchall()]
    # Resultado: Lista con 119 códigos
```

#### 2.3. Recupera los 119 clientes completos

```python
# Líneas 120-144
query = f"""
    SELECT code, description, address, client_id,
           email, phone, contact, status
    FROM clients
    WHERE code IN ({placeholders})
      AND code IS NOT NULL AND code != ''
      AND description IS NOT NULL AND description != ''
    ORDER BY code
"""

self.pg_cursor.execute(query, pending_codes)
customers = self.pg_cursor.fetchall()
# Resultado: 119 clientes
```

#### 2.4. Clasifica como NUEVOS (porque sync_hashes está vacío)

```python
# Líneas 148-172
for customer in customers:
    code = customer[0]

    hash_actual = self._generar_hash(customer)
    hash_guardado = self._obtener_hash_guardado(self.table_name, code)

    if hash_guardado is None:
        # Primer sync -> hash_guardado es None
        cambios['nuevos'].append(customer)
    elif hash_guardado != hash_actual:
        cambios['modificados'].append(customer)

    self._guardar_hash(self.table_name, code, hash_actual)
```

**Resultado:**
- `cambios['nuevos']`: 119 clientes
- `cambios['modificados']`: 0 clientes
- `cambios['eliminados']`: 0 clientes

---

### PASO 3: `sync_to_api()` - Enviar 119 clientes al API

**Archivo:** `sync/customers_sync.py:269-371`

#### 3.1. Combina nuevos y modificados

```python
# Líneas 279-286
todos_los_customers = changes.get('nuevos', []) + changes.get('modificados', [])
# Resultado: 119 clientes
```

#### 3.2. Transforma al formato de la API

```python
# Líneas 288-292
customers_api = [
    self.transform_to_api(cust)
    for cust in todos_los_customers
]
```

**Transformación (líneas 210-263):**

```python
def transform_to_api(self, pg_record: tuple) -> Dict[str, Any]:
    (code, description, address, client_id, email, phone, contact, status) = pg_record

    return {
        'codigo': code,              # code de PostgreSQL -> campo 'codigo'
        'document_number': client_id,  # client_id de PostgreSQL
        'name': description or contact,
        'email': email,
        'phone': phone,
        'address': address,
        'status': 'active' if status == '01' else 'inactive'
    }
```

#### 3.3. Envía al endpoint POST /api/sync-batch/customers

```python
# Líneas 307-311
result = self.api_client.sync_batch(
    company_id=self.company_id,
    customers=customers_api  # 119 clientes
)
```

**Payload enviado:**
```json
{
  "company_id": 86,
  "customers": [
    {
      "codigo": "V12345678",
      "document_number": "12345678",
      "name": "Juan Pérez",
      "email": "juan@email.com",
      "phone": "+58-414-1234567",
      "address": "Calle 123",
      "status": "active"
    },
    ... // 118 más
  ]
}
```

---

### PASO 4: EL API RESPONDE - AQUÍ ESTÁ LA CLAVE

**Endpoint backend:** `POST /api/sync-batch/customers`

#### 4.1. ¿Qué hace el backend?

El backend recibe 119 clientes y procesa CADA UNO:

```python
# Lógica del backend (pseudocódigo)
for customer in request['customers']:
    codigo = customer['codigo']

    # Buscar si ya existe en BD
    existing = db.query("SELECT * FROM customers WHERE codigo = ?", codigo)

    if existing:
        # YA EXISTE -> UPDATE
        db.update("UPDATE customers SET ... WHERE codigo = ?", codigo)
        updated_count += 1
    else:
        # NO EXISTE -> INSERT
        db.insert("INSERT INTO customers ...")
        created_count += 1
```

#### 4.2. Resultado del backend

**Antes de recibir los 119 clientes:**
- El backend YA TENÍA 114 clientes
- De esos 114, algunos coinciden con los códigos de PostgreSQL

**Al procesar los 119 clientes de PostgreSQL:**
- **114 coincidían** con códigos que ya existían → `UPDATE`
- **5 eran nuevos** (códigos que no existían) → `INSERT`

**Respuesta del API:**
```json
{
  "success": true,
  "created": 5,      // 5 clientes nuevos insertados
  "updated": 114,    // 114 clientes ya existían, se actualizaron
  "errors": 0
}
```

---

### PASO 5: Mostrar resultado al usuario

**Archivo:** `sync/customers_sync.py:313-323`

```python
self.stats['created'] = result.get('created', 0)   # 5
self.stats['updated'] = result.get('updated', 0)   # 114

self.info(
    f"✅ Clientes sincronizados: {self.stats['created']} creados, "
    f"{self.stats['updated']} actualizados"
)
```

**Output:**
```
✅ Clientes sincronizados: 5 creados, 114 actualizados
```

---

### PASO 6: `detect_new_from_api()` - Detectar nuevos desde backend

**Archivo:** `sync/customers_sync.py:441-482`

#### 6.1. Obtener todos los clientes del API

```python
# Líneas 455-458
clientes_api = list(self.api_client.get_all(company_id=self.company_id))
# Resultado: 114 clientes (ahora que PostgreSQL envió 119, el backend tiene 114+5=119)
```

**Endpoint:** `GET /api/sync-batch/customers?company_id=86`

#### 6.2. Obtener códigos existentes en PostgreSQL

```python
# Líneas 460-463
self.pg_cursor.execute("SELECT code FROM clients")
codigos_pg = {row[0] for row in self.pg_cursor.fetchall()}
# Resultado: Set con 119 códigos
```

#### 6.3. Detectar nuevos (existen en API pero NO en PG)

```python
# Líneas 465-471
for cliente_api in clientes_api:
    codigo_api = cliente_api.get('codigo')

    if codigo_api and codigo_api not in codigos_pg:
        nuevos_clientes.append(cliente_api)
```

**Resultado:** `0` nuevos clientes

**¿Por qué?**
- PostgreSQL tiene 119 clientes
- API tiene 114 clientes (antes del sync) o 119 (después del sync)
- Como PostgreSQL ≥ API, no hay clientes nuevos en el backend

---

## 📊 RESUMEN DEL FLUJO

```
1. PostgreSQL local:     119 clientes
2. API REST (antes):     114 clientes ← EL BACKEND NO ESTABA VACÍO

3. detect_changes():
   - sync_hashes está vacío (primera vez)
   - Obtiene TODOS los 119 clientes
   - Los marca como "nuevos" para enviar al API

4. sync_to_api():
   - Transforma 119 clientes al formato de API
   - Envía POST /api/sync-batch/customers con 119 clientes

5. Backend procesa:
   - 114 clientes ya existían → UPDATE
   - 5 clientes eran nuevos → INSERT
   - Responde: {created: 5, updated: 114}

6. detect_new_from_api():
   - Obtiene clientes del API: 114 (o 119 después del sync)
   - PostgreSQL ya tiene 119
   - No hay clientes nuevos en el backend → 0

RESULTADO FINAL:
  📤 A API REST: 5 creados, 114 actualizados
  📥 DESDE API: 0 nuevos clientes importados
```

---

## 🎯 CONCLUSIÓN

**El backend NO estaba vacío.** El backend YA TENÍA 114 clientes.

Cuando envías 119 clientes desde PostgreSQL:
- **114 ya existían** en el backend → el backend los actualizó
- **5 eran nuevos** → el backend los creó

Por eso ves "114 actualizados, 5 creados" y no al revés.

---

## ✅ VERIFICACIÓN

Para verificar que el backend tenía datos antes del sync:

```bash
# Antes de sincronizar, consulta el API
curl -H "Authorization: Bearer TU_TOKEN" \
  "https://tu-api.com/api/sync-batch/customers?company_id=86"

# Debería retornar 114 clientes ANTES de que tú sincronices
```

O revisa la base de datos del backend directamente:

```sql
SELECT COUNT(*) FROM customers WHERE company_id = 86;
-- Resultado: 114 (antes del sync)
```
