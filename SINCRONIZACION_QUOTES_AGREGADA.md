# ✅ SINCRONIZACIÓN DE QUOTES AGREGADA
## MySQL → PostgreSQL (Dirección Opuesta)

---

## 🎯 ACTUALIZACIÓN COMPLETADA

He agregado la sincronización automática e inteligente de **quotes (presupuestos)** al módulo `smart_sync_complete.py`.

---

## 📋 QUÉ SE AGREGÓ

### 1. Detección de Cambios en Quotes
```python
detectar_cambios_quotes()
```
- Lee quotes desde **MySQL**
- Genera hash MD5 con campos clave
- Compara con `sync_hashes` en PostgreSQL
- Detecta: **nuevos** y **modificados**

### 2. Sincronización a PostgreSQL
```python
sincronizar_quotes_postgresql()
```
- Inserta quotes completos en **PostgreSQL**
- Crea registros en:
  - `sales_operation` (operación principal)
  - `sales_operation_coins` (monedas: USD y VES)
  - `sales_operation_details` (items del quote)
  - `sales_operation_details_coins` (monedas de items)
  - `sales_operation_taxes` (impuestos)
  - `sales_operation_taxes_coins` (monedas de impuestos)

### 3. Actualización de Estados
```python
_actualizar_status_quote_postgresql()
```
- Actualiza el campo `pending` en PostgreSQL
- MySQL status → PostgreSQL pending:
  - `'approved'` → `pending = false`
  - `'rejected'` → `pending = true`
  - `'pending'` → `pending = true`

---

## 🔄 DIRECCIÓN DE SINCRONIZACIÓN

```
┌─────────────────────────────────────────────────────────────┐
│                    POSTGRESQL                              │
│                      (Origen)                              │
│                         │                                 │
│         Products │ Customers │ Categories                 │
│              ────┼───────────┼──────────►                  │
│                         │                                 │
│                         ▼                                 │
│                      MySQL                                │
│                    (Destino)                              │
│                         │                                 │
│                    Quotes ◄───────┐                        │
│                         │         │                        │
│                         └─────────┘                        │
│                         │                                 │
│                         ▼                                 │
│                    PostgreSQL                             │
│                  (sales_operation)                        │
└─────────────────────────────────────────────────────────────┘
```

**Resumen:**
- Products, Customers, Categories: **PostgreSQL → MySQL**
- Quotes: **MySQL → PostgreSQL** (dirección opuesta)

---

## 📊 FLUJO DE SINCRONIZACIÓN DE QUOTES

### 1. Detectar Cambios

```
MySQL.quotes (10:00 AM):
┌────┬──────────────┬────────┬────────┐
│ id │ quote_number │ status │ total  │
├────┼──────────────┼────────┼────────┤
│ 1  │ QUOTE-001    │ pending│ 1000   │  ← NUEVO
│ 2  │ QUOTE-002    │ pending│ 500    │  ← NUEVO
└────┴──────────────┴────────┴────────┘

sync_hashes en PostgreSQL:
┌──────────┬────────────┬──────────────┐
│table_name│ record_key │ record_hash  │
└──────────┴────────────┴──────────────┘
(vacío - primera vez)

Resultado:
- Quote #1: ✨ NUEVO (no existe en sync_hashes)
- Quote #2: ✨ NUEVO (no existe en sync_hashes)
```

### 2. Sincronizar a PostgreSQL

```
Para cada quote nuevo:
┌─────────────────────────────────────┐
│ 1. Verificar si existe en PG        │
│    SELECT * FROM sales_operation    │
│    WHERE document_no = 'QUOTE-001'  │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ NO existe    │
        └──────┬───────┘
               │
               ▼
┌───────────────────────────────────────────────────────────┐
│ 2. Insertar en PostgreSQL:                                │
│    • sales_operation (con pending=true)                   │
│    • sales_operation_coins (USD y VES)                    │
│    • sales_operation_details (items)                       │
│    • sales_operation_details_coins                         │
│    • sales_operation_taxes (impuestos)                      │
│    • sales_operation_taxes_coins                           │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Guardar hash en sync_hashes      │
│    table_name = 'quotes'            │
│    record_key = '1'                 │
│    record_hash = abc123...          │
└─────────────────────────────────────┘
```

### 3. Actualización de Estados

```
MySQL.quotes (11:00 AM - CAMBIOS):
┌────┬──────────────┬───────────┐
│ id │ quote_number │ status    │
├────┼──────────────┼───────────┤
│ 1  │ QUOTE-001    │ approved  │  ← ¡CAMBIÓ!
│ 2  │ QUOTE-002    │ pending   │  (sin cambios)
└────┴──────────────┴───────────┘

sync_hashes en PostgreSQL:
┌──────────┬────────────┬──────────────┐
│table_name│ record_key │ record_hash  │
├──────────┼────────────┼──────────────┤
│quotes    │ 1           │ abc123...     │
│quotes    │ 2           │ def456...     │
└──────────┴────────────┴──────────────┘

Detección:
- Quote #1: hash_antiguo(abc123) ≠ hash_actual(xyz789)
  → 🔄 MODIFICADO (cambió el status)

Sincronización:
- Actualizar en PostgreSQL:
  UPDATE sales_operation
  SET pending = false  ← approved
  WHERE document_no = 'QUOTE-001'
```

---

## 📦 MÉTODOS AGREGADOS

### En `smart_sync_complete.py`:

1. **`_generar_hash_quote(quote)`** - Genera hash MD5 de un quote
   - Campos: id, quote_number, customer_id, subtotal, tax, discount, total, status

2. **`detectar_cambios_quotes()`** - Detecta cambios en quotes
   - Lee desde MySQL
   - Compara con sync_hashes en PostgreSQL
   - Retorna: nuevos, modificados

3. **`sincronizar_quotes_postgresql(cambios)`** - Sincroniza a PostgreSQL
   - Inserta quotes completos
   - Actualiza estados

4. **`_insertar_quote_postgresql(quote, correlativo, mac)`** - Inserta quote completo
   - Crea sales_operation
   - Crea monedas
   - Llama a insertar items e impuestos

5. **`_insertar_quote_monedas(correlativo, quote, bcv_rate)`** - Monedas del quote

6. **`_insertar_quote_items(correlativo, quote, bcv_rate)`** - Items del quote

7. **`_insertar_item_monedas(correlativo, line, item, bcv_rate)`** - Monedas de items

8. **`_insertar_quote_taxes(correlativo, quote, bcv_rate)`** - Impuestos del quote

9. **`_actualizar_status_quote_postgresql(quote)`** - Actualiza status

---

## ✅ INTEGRACIÓN EN MÉTODO PRINCIPAL

El método `ejecutar_sync_completa()` ahora incluye:

```python
def ejecutar_sync_completa(self):
    # Conectar bases de datos
    self._conectar_bases_datos()

    # Detectar cambios (PostgreSQL → MySQL)
    cambios_products = self.detectar_cambios_products()
    cambios_customers = self.detectar_cambios_customers()
    cambios_categories = self.detectar_cambios_categories()

    # Detectar cambios en quotes (MySQL → PostgreSQL)
    cambios_quotes = self.detectar_cambios_quotes()  # ← NUEVO

    # Sincronizar a MySQL
    self.sincronizar_products_mysql(cambios_products)
    self.sincronizar_customers_mysql(cambios_customers)
    self.sincronizar_categories_mysql(cambios_categories)

    # Sincronizar quotes a PostgreSQL (dirección opuesta)
    self.sincronizar_quotes_postgresql(cambios_quotes)  # ← NUEVO

    # Reporte final
    # Products: X nuevos, Y modificados
    # Customers: X nuevos, Y modificados
    # Categories: X nuevos, Y modificados
    # Quotes: X nuevos (MySQL→PG), Y estados actualizados  # ← NUEVO
```

---

## 📊 EJEMPLO DE LOG

```
[2025-01-22 10:30:15] ℹ️ INFO: === INICIANDO SERVICIO DE SINCRONIZACIÓN ===
[2025-01-22 10:30:16] ℹ️ INFO: Detectando cambios en products...
[2025-01-22 10:30:18] ℹ️ INFO:   ✨ NUEVO: PROD1248
[2025-01-22 10:30:19] ℹ️ INFO: Products: 1 nuevos, 0 modificados, 0 eliminados
[2025-01-22 10:30:20] ℹ️ INFO: Detectando cambios en customers...
[2025-01-22 10:30:21] ℹ️ INFO: Customers: 0 nuevos, 0 modificados, 0 eliminados
[2025-01-22 10:30:22] ℹ️ INFO: Detectando cambios en categories...
[2025-01-22 10:30:23] ℹ️ INFO: Categories: 0 nuevos, 0 modificados, 0 eliminados
[2025-01-22 10:30:24] ℹ️ INFO: Detectando cambios en quotes (MySQL → PostgreSQL)...  ← NUEVO
[2025-01-22 10:30:25] ℹ️ INFO:   ✨ NUEVO: Quote #123 (QUOTE-2025-001)              ← NUEVO
[2025-01-22 10:30:26] ℹ️ INFO:   ✨ NUEVO: Quote #124 (QUOTE-2025-002)              ← NUEVO
[2025-01-22 10:30:30] ℹ️ INFO:   🔄 MODIFICADO: Quote #100 (QUOTE-2024-100)      ← NUEVO
[2025-01-22 10:30:31] ℹ️ INFO: Quotes: 2 nuevos, 1 modificados                       ← NUEVO
[2025-01-22 10:30:32] ℹ️ INFO: Sincronizando quotes a PostgreSQL...              ← NUEVO
[2025-01-22 10:30:45] ℹ️ INFO:   Procesando quote #123...                             ← NUEVO
[2025-01-22 10:31:00] ℹ️ INFO:   Procesando quote #124...                             ← NUEVO
[2025-01-22 10:31:05] ℹ️ INFO:   🔄 Status actualizado: Quote #100 → approved        ← NUEVO
[2025-01-22 10:31:06] ✅ ÉXITO: Quotes sincronizados a PostgreSQL: 2 nuevos      ← NUEVO
[2025-01-22 10:31:07] ℹ️ INFO: ╔════════════════════════════════════════════════════════════════╗
[2025-01-22 10:31:08] ℹ️ INFO: ║                    RESUMEN DE SINCRONIZACIÓN                    ║
[2025-01-22 10:31:09] ℹ️ INFO: ╚════════════════════════════════════════════════════════════════╝
[2025-01-22 10:31:10] ✅ ÉXITO: Products:   1 nuevos, 0 modificados
[2025-01-22 10:31:11] ✅ ÉXITO: Customers:  0 nuevos, 0 modificados
[2025-01-22 10:31:12] ✅ ÉXITO: Categories: 0 nuevos, 0 modificados
[2025-01-22 10:31:13] ✅ ÉXITO: Quotes:     2 nuevos (MySQL→PG), 1 estados actualizados  ← NUEVO
[2025-01-22 10:31:14] ℹ️ INFO: Duración:   45.32 segundos
[2025-01-22 10:31:15] ✅ ÉXITO: ✅ SINCRONIZACIÓN COMPLETADA CON ÉXITO
```

---

## 🎯 RESUMEN FINAL

### Sistema Completo de Sincronización

| Entidad | Dirección | Detección | Hash en |
|---------|-----------|-----------|---------|
| **Products** | PostgreSQL → MySQL | Hash comparison | sync_hashes |
| **Customers** | PostgreSQL → MySQL | Hash comparison | sync_hashes |
| **Categories** | PostgreSQL → MySQL | Hash comparison | sync_hashes |
| **Quotes** | **MySQL → PostgreSQL** | Hash comparison | **sync_hashes** |

### Todo es Automático

✅ Servicio de Windows ejecuta sincronización cada X tiempo
✅ Detecta automáticamente nuevos quotes en MySQL
✅ Sincroniza automáticamente a PostgreSQL
✅ Actualiza estados automáticamente (approved/rejected)
✅ Guarda hashes para detectar cambios futuros

---

## 🚀 PRÓXIMOS PASOS

El sistema está **COMPLETO**. Ahora puedes:

1. **Probar el módulo:**
   ```python
   python smart_sync_complete.py
   ```

2. **Compilar a .exe:**
   ```bash
   build.bat
   ```

3. **Crear instalador:**
   ```bash
   create_installer.bat
   ```

4. **Instalar en servidor:**
   - Ejecutar `setup_sync_service.exe`
   - Configurar conexiones
   - ¡Listo!

---

**Actualización: 2025-01-22**
**Versión: 1.1 (con quotes)**
**Estado: ✅ COMPLETO**
