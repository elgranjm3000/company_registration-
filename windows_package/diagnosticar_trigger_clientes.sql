-- =====================================================
-- 🔍 DIAGNÓSTICO COMPLETO: Trigger de eliminación de clientes
-- =====================================================
-- Ejecutar este script paso a paso para diagnosticar
-- por qué el trigger no marca en sync_hashes
-- =====================================================

\echo '====================================================='
\echo '  PASO 1: ¿Existe el trigger?'
\echo '====================================================='
SELECT
    'Existe' as chequeo,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'tr_clients_mark_deleted_sync_hashes'
        )
        THEN '✅ SÍ - El trigger existe'
        ELSE '❌ NO - El trigger NO existe. SOLUCIÓN: Ejecutar actualizar_trigger_cliente.sql'
    END as resultado;

\echo ''
\echo '====================================================='
\echo '  PASO 2: ¿Cuál es la versión del trigger?'
\echo '====================================================='
SELECT
    pg_get_functiondef(oid) as definicion_funcion
FROM pg_proc
WHERE proname = 'trigger_mark_client_deleted_sync_hashes';

\echo ''
\echo 'Verificar si tiene OLD.code (CORRECTO) o OLD.email (INCORRECTO):'
SELECT
    'Versión del trigger' as chequeo,
    CASE
        WHEN pg_get_functiondef(oid) LIKE '%OLD.code%'
        THEN '✅ VERSIÓN CORRECTA - Usa OLD.code'
        ELSE '❌ VERSIÓN INCORRECTA - Usa OLD.email o otra cosa. SOLUCIÓN: Ejecutar actualizar_trigger_cliente.sql'
    END as resultado
FROM pg_proc
WHERE proname = 'trigger_mark_client_deleted_sync_hashes';

\echo ''
\echo '====================================================='
\echo '  PASO 3: ¿La tabla sync_hashes existe?'
\echo '====================================================='
SELECT
    'Tabla sync_hashes' as chequeo,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'sync_hashes'
        )
        THEN '✅ SÍ - La tabla existe'
        ELSE '❌ NO - La tabla NO existe. SOLUCIÓN: Crear tabla sync_hashes'
    END as resultado;

\echo ''
\echo '====================================================='
\echo '  PASO 4: ¿Hay clientes en la tabla clients?'
\echo '====================================================='
SELECT COUNT(*) as total_clients FROM clients;

\echo ''
\echo 'Mostrar 5 clientes de ejemplo:'
SELECT code, description FROM clients LIMIT 5;

\echo ''
\echo '====================================================='
\echo '  PASO 5: TEST EN VIVO - Eliminar un cliente de prueba'
\echo '====================================================='

-- Buscar un cliente que no tenga ventas (para poder eliminarlo)
\echo 'Buscando cliente sin ventas para test...'
WITH cliente_sin_ventas AS (
    SELECT c.code
    FROM clients c
    LEFT JOIN sales_operation s ON c.code = s.client_code
    WHERE s.client_code IS NULL
    LIMIT 1
)
SELECT
    code as cliente_a_eliminar,
    'Este cliente se usará para el test' as info
FROM cliente_sin_ventas;

\echo ''
\echo '¿Hay un cliente disponible para el test?'
\echo 'Si aparece un cliente arriba, continúa. Si no, aparece vacío, busca otro manualmente.'

-- Guardar el código del cliente en una variable
WITH cliente_test AS (
    SELECT c.code, c.description
    FROM clients c
    LEFT JOIN sales_operation s ON c.code = s.client_code
    WHERE s.client_code IS NULL
    AND c.code IS NOT NULL
    LIMIT 1
)
SELECT
    'Cliente de test:' as info,
    code,
    description
FROM cliente_test;

\echo ''
\echo '====================================================='
\echo '  PASO 6: Verificar sync_hashes ANTES de eliminar'
\echo '====================================================='
SELECT
    'sync_hashes ANTES' as paso,
    COUNT(*) as total,
    COUNT(CASE WHEN table_name = 'customers' THEN 1 END) as customers,
    COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as con_deleted_at
FROM sync_hashes;

\echo ''
\echo 'Registros de customers en sync_hashes ANTES:'
SELECT * FROM sync_hashes WHERE table_name = 'customers' AND deleted_at IS NOT NULL;

\echo ''
\echo '====================================================='
\echo '  PASO 7: Eliminar cliente de prueba'
\echo '====================================================='
\echo 'Ejecuta manualmente:'
\echo 'DELETE FROM clients WHERE code = ''<CODIGO_DEL_PASO_5>'';'
\echo ''
\echo 'O si quieres hacerlo automático con el cliente encontrado:'
WITH cliente_a_eliminar AS (
    SELECT c.code
    FROM clients c
    LEFT JOIN sales_operation s ON c.code = s.client_code
    WHERE s.client_code IS NULL
    AND c.code IS NOT NULL
    LIMIT 1
)
DELETE FROM clients
WHERE code IN (SELECT code FROM cliente_a_eliminar);

\echo ''
\echo '✅ Cliente eliminado'

\echo ''
\echo '====================================================='
\echo '  PASO 8: Verificar sync_hashes DESPUÉS de eliminar'
\echo '====================================================='
SELECT
    'sync_hashes DESPUÉS' as paso,
    COUNT(*) as total,
    COUNT(CASE WHEN table_name = 'customers' THEN 1 END) as customers,
    COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as con_deleted_at
FROM sync_hashes;

\echo ''
\echo 'Registros de customers en sync_hashes DESPUÉS:'
SELECT * FROM sync_hashes WHERE table_name = 'customers' AND deleted_at IS NOT NULL;

\echo ''
\echo '====================================================='
\echo '  📊 DIAGNÓSTICO FINAL'
\echo '====================================================='
/*
INTERPRETACIÓN DE LOS RESULTADOS:

PASO 8 después de eliminar:
- ✅ Si aparece un registro con deleted_at = trigger FUNCIONA
- ❌ Si NO aparece ningún registro = trigger NO FUNCIONA

Si el trigger NO funciona:
1. Verifica que el trigger exista (PASO 1)
2. Verifica que tenga la versión correcta con OLD.code (PASO 2)
3. Verifica que sync_hashes exista (PASO 3)
4. Ejecuta el script actualizar_trigger_cliente.sql

Si el trigger SÍ funciona pero el .exe no elimina:
- El problema está en el código Python, no en el trigger
- Revisa los logs del .exe para ver qué está haciendo
*/
