# 📋 Instrucciones para Test de Eliminación de Clientes - .EXE DEBUG

## 🎯 Objetivo
Verificar que al eliminar un cliente de PostgreSQL, también se elimina de MySQL usando el ejecutable.

---

## ✅ Requisitos Previos

1. **Ejecutable DEBUG compilado** con las últimas correcciones
2. **Base de datos PostgreSQL** con el trigger actualizado
3. **Base de datos MySQL** con el cliente a eliminar
4. **Consola visible** (el .exe DEBUG muestra la consola)

---

## 🔧 PASO 1: Compilar el .EXE DEBUG (si no está compilado)

```batch
cd windows_package
python build_exe_debug.py
```

Esto creará: `dist/SyncSystem_DEBUG/SyncSystem_DEBUG.exe`

---

## 🧪 PASO 2: Test Completo de Eliminación

### 2.1. Preparación: Insertar cliente de prueba en MySQL

Ejecutar en MySQL Workbench o consola:

```sql
-- Verificar que el cliente existe en PostgreSQL
SELECT code, description FROM clients WHERE code = '19507188';

-- Insertar en MySQL si no existe
INSERT INTO customers (company_id, document_type, document_number, name, address, email, status)
SELECT 87, 'V', '19507188', c.description, c.address, c.email, 'active'
FROM clients c
WHERE c.code = '19507188'
AND NOT EXISTS (
    SELECT 1 FROM customers WHERE document_number = '19507188' AND company_id = 87
);
```

### 2.2. Ejecutar el .EXE DEBUG

```batch
cd dist\SyncSystem_DEBUG
SyncSystem_DEBUG.exe --mode config
```

**⚠️ IMPORTANTE:** Mantén la ventana de consola abierta para ver los logs

### 2.3. Verificar que el trigger se crea correctamente

En la consola del .exe, deberías ver logs como:

```
[INFO] Creando trigger de eliminación para clientes...
[DEBUG] Trigger tr_clients_mark_deleted_sync_hashes creado correctamente
```

### 2.4. Eliminar cliente de PostgreSQL

En pgAdmin o consola PostgreSQL:

```sql
DELETE FROM clients WHERE code = '19507188';
```

### 2.5. Ejecutar sincronización

En la consola del .exe, presiona el botón de sincronización o espera a que se ejecute automáticamente.

Deberías ver logs como:

```
🗑️ VERIFICANDO CUSTOMERS ELIMINADOS EN POSTGRESQL...
   🔍 Company ID: 87
   🔍 Trigger existe: True
   🔍 Total customers marcados como eliminados: 1
      - code=19507188, deleted_at=2026-02-28 18:42:34
   🔍 Cliente encontrado en MySQL: id=47414, name=muentes
   ✅ Cliente eliminado: 19507188
```

### 2.6. Verificación Final

Ejecutar en MySQL:

```sql
-- Verificar que ya no existe
SELECT id, name, document_number
FROM customers
WHERE document_number = '19507188' AND company_id = 87;

-- Debe retornar 0 filas
```

---

## 📊 Qué buscar en los logs de consola

### ✅ Logs de ÉXITO:

```
🗑️ VERIFICANDO CUSTOMERS ELIMINADOS EN POSTGRESQL...
   🔍 Company ID: 87
   🔍 Trigger existe: True
   🔍 Total customers marcados como eliminados: 1
      - code=19507188, deleted_at=2026-02-28 18:42:34

Procesando: 19507188
   🔍 Cliente encontrado en MySQL: id=47414, name=muentes
   ✅ Encontrado en MySQL: id=47414, name=muentes
   ✅ Eliminado de MySQL

✅ Cliente eliminado: 19507188
```

### ❌ Logs de ERROR:

Si ves algo como:

```
❌ No se pudo obtener company_id
```

→ El problema es la configuración, no el trigger.

```
🔍 Total customers marcados como eliminados: 0
   ℹ️ No hay customers eliminados que procesar
   💡 Si borraste un cliente en PostgreSQL y no aparece aquí:
      1. Verifica que el trigger esté creado
      2. Verifica que el cliente realmente se borró
      3. Revisa la tabla sync_hashes manualmente
```

→ El trigger no funcionó. Revisa si el trigger se creó correctamente en PostgreSQL.

---

## 🔍 Diagnóstico Manual (si los logs no son suficientes)

### Verificar que el trigger existe en PostgreSQL:

```sql
SELECT
    tgname AS trigger_name,
    tgrelid::regclass AS table_name
FROM pg_trigger
WHERE tgname = 'tr_clients_mark_deleted_sync_hashes';
```

Debería retornar 1 fila.

### Verificar la definición del trigger:

```sql
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'trigger_mark_client_deleted_sync_hashes';
```

Debería mostrar:

```sql
CREATE OR REPLACE FUNCTION trigger_mark_client_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_exists INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_exists ...
```

**✅ IMPORTANTE:** Debe tener `DECLARE v_exists INTEGER;`

### Verificar sync_hashes después de eliminar:

```sql
SELECT *
FROM sync_hashes
WHERE table_name = 'customers'
  AND deleted_at IS NOT NULL;
```

Debería mostrar el cliente eliminado con `deleted_at` poblado.

---

## 📝 Checklist de Verificación

- [ ] .EXE DEBUG compilado con las últimas correcciones
- [ ] Cliente existe en PostgreSQL antes de test
- [ ] Cliente existe en MySQL antes de test
- [ ] .EXE se ejecuta y muestra consola
- [ ] Trigger se crea al iniciar el sistema (revisar logs)
- [ ] Al eliminar cliente de PostgreSQL, trigger marca en sync_hashes
- [ ] Al ejecutar sincronización, cliente se elimina de MySQL
- [ ] Verificación final confirma que ya no existe en MySQL

---

## 🎯 Resultado Esperado

✅ **Al eliminar un cliente de PostgreSQL:**
1. Trigger lo marca en `sync_hashes` automáticamente
2. Sincronización detecta el registro
3. Cliente se elimina de MySQL automáticamente
4. Consola muestra logs detallados del proceso

---

## ❌ Si no funciona

1. **Verifica que el trigger tenga la versión corregida** (con `DECLARE v_exists`)
2. **Revisa los logs de consola** del .exe DEBUG
3. **Verifica sync_hashes manualmente** en PostgreSQL
4. **Ejecuta el test manual** que hicimos en Python para aislar el problema

---

## 📞 Para Soporte

Si algo no funciona, proporcionar:
1. Captura de pantalla de la consola del .exe
2. Resultado de `SELECT pg_get_functiondef(...)`
3. Contenido de `sync_hashes` después de eliminar
4. Logs completos de la sincronización
