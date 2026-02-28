# 📋 Logging de Errores de MySQL

## Descripción

El sistema de sincronización ahora guarda automáticamente todos los errores de MySQL en archivos separados, **SIN mostrar detalles técnicos al usuario**.

## Ubicación

Los logs se guardan en:
```
logs/mysql_errors/
├── mysql_errors_20260227_143025.log
├── mysql_errors_20260227_151230.log
└── ...
```

## ¿Qué se guarda?

Cada error incluye:
- 📅 **Timestamp**: Fecha y hora exacta del error
- 🔧 **Operación**: Qué se estaba intentando hacer (ej: "BATCH INSERT products")
- ❌ **Tipo de Error**: Nombre de la excepción
- 📝 **Mensaje**: Descripción del error
- 💾 **Query SQL**: El query que falló (formateado)
- 🔢 **Parámetros**: Parámetros del query
- 📚 **Stack Trace**: Traza completa del error
- 📊 **Contexto**: Información adicional (batch size, etc.)

## Ejemplo de Log

```
================================================================================
ERROR #1 - 2026-02-27 14:30:25
================================================================================

Operación: BATCH INSERT products

Contexto: Batch size: 150 elementos

Tipo de Error: IntegrityError
Mensaje: (1048, "Column 'coin' cannot be null")

Query SQL:
----------------------------------------
INSERT INTO products (
    company_id, code, name, description, price, cost, stock, min_stock,
    category_id, status, product_type, images, higher_price, sale_tax,
    aliquot, coin, description_coin, unitary_cost, buy_tax, buy_aliquot,
    created_at, updated_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
)
ON DUPLICATE KEY UPDATE ...
----------------------------------------

Parámetros: [(1, 'PROD001', 'Producto 1', ...), ...]

Stack Trace:
----------------------------------------
Traceback (most recent call last):
  File "smart_sync_complete.py", line 3391, in sincronizar_products_mysql
    self.mysql_cursor.executemany(insert_query, batch_data)
pymysql.err.IntegrityError: (1048, "Column 'coin' cannot be null")
----------------------------------------
```

## ¿Qué ve el usuario?

El usuario **NO** ve los errores técnicos. Solo ve un mensaje simple:

```
⚠️ Error al insertar productos en MySQL (ver log en carpeta logs/mysql_errors/)
```

O:
```
⚠️ Error al sincronizar products (ver log en carpeta logs/mysql_errors/)
```

## ¿Cómo revisar los logs?

### Opción 1: Buscar la carpeta directamente
```bash
# En Linux/Mac
cd logs/mysql_errors/
ls -lh

# Ver el log más reciente
cat mysql_errors_*.log | less

# O con tu editor favorito
nano mysql_errors_*.log
```

### Opción 2: Buscar errores específicos
```bash
# Buscar errores de "IntegrityError"
grep -n "IntegrityError" logs/mysql_errors/*.log

# Buscar errores de "connection"
grep -n "connection" logs/mysql_errors/*.log
```

### Opción 3: En Windows
```
1. Abrir el explorador de archivos
2. Navegar a la carpeta del sistema
3. Entrar en: logs → mysql_errors
4. Abrir el archivo .log más reciente con Notepad o Notepad++
```

## Limpieza automática

El sistema mantiene automáticamente solo los **10 archivos de log más recientes**.

Los archivos antiguos se eliminan automáticamente para no saturar el disco.

## Errores que se loggean

1. **Errores de BATCH INSERT**: Cuando falla la inserción de múltiples productos
2. **Errores de BATCH UPDATE**: Cuando falla la actualización de múltiples productos
3. **Errores de conexión**: Cuando no se puede conectar a MySQL
4. **Errores de query individuales**: Cuando falla un query específico

## Troubleshooting

### Problema: Los productos no se insertan en MySQL

**Pasos para diagnosticar:**

1. **Revisar si hay errores de MySQL**:
   ```bash
   ls logs/mysql_errors/
   ```

2. **Si hay archivos de log, abrir el más reciente**:
   ```bash
   cat logs/mysql_errors/mysql_errors_*.log | less
   ```

3. **Buscar el problema específico**:
   - Busca "IntegrityError" → Problema con datos obligatorios (NULL, unique key, etc.)
   - Busca "Connection" → Problema de conexión a MySQL
   - Busca "Timeout" → Problema de tiempo de espera

4. **Soluciones comunes**:
   - `Column 'X' cannot be null` → El campo X no tiene valor por defecto
   - `Duplicate entry` → Ya existe un registro con esa clave única
   - `Lost connection` → Problema de red o MySQL se cayó

### Problema: No se crean archivos de log

**Causas posibles:**
1. `mysql_error_logger.py` no está en el mismo directorio que `smart_sync_complete.py`
2. Falta permiso de escritura en la carpeta `logs/mysql_errors/`

**Solución:**
```bash
# Verificar que el archivo existe
ls mysql_error_logger.py

# Verificar permisos
chmod +w logs/mysql_errors/

# Crear directorio si no existe
mkdir -p logs/mysql_errors/
```

## Ventajas

✅ **No alarmas al usuario**: El usuario no ve errores técnicos confusos
✅ **Debug fácil**: Toda la información necesaria para diagnosticar problemas
✅ **Traza completa**: Stack trace completo para ver exactamente dónde falló
✅ **Histórico**: Mantienen un histórico de errores para detectar problemas recurrentes
✅ **Auto-limpieza**: No satura el disco con logs antiguos

## Notas importantes

- Los logs son **SILENCIOSOS**: Solo se escriben en archivo, NO en consola
- El usuario verá mensajes simples: "Ver log en carpeta logs/mysql_errors/"
- Los logs se crean por sesión de sincronización
- Cada archivo tiene un timestamp único: `mysql_errors_YYYYMMDD_HHMMSS.log`

---

**Fecha**: 2026-02-27
**Versión**: 1.0
**Estado**: ✅ Activo
