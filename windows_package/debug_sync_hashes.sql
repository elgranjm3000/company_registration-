-- =====================================================
-- 🔍 DIAGNÓSTICO: ¿Por qué devuelve 0 la consulta?
-- =====================================================
-- Ejecutar este script en PostgreSQL para diagnosticar
-- por qué la consulta de customers eliminados devuelve 0
-- =====================================================

\echo '====================================================='
\echo '  PASO 1: Verificar QUÉ table_name existe en sync_hashes'
\echo '====================================================='
SELECT DISTINCT table_name FROM sync_hashes;

\echo ''
\echo '====================================================='
\echo '  PASO 2: Verificar SI hay registros con deleted_at'
\echo '====================================================='
SELECT
    table_name,
    COUNT(*) as total_registros,
    COUNT(CASE WHEN deleted_at IS NOT NULL THEN 1 END) as con_deleted_at,
    COUNT(CASE WHEN deleted_at IS NULL THEN 1 END) as sin_deleted_at
FROM sync_hashes
GROUP BY table_name;

\echo ''
\echo '====================================================='
\echo '  PASO 3: Buscar CUALQUIER registro con deleted_at'
\echo '====================================================='
SELECT
    table_name,
    record_key,
    deleted_at
FROM sync_hashes
WHERE deleted_at IS NOT NULL
ORDER BY deleted_at DESC
LIMIT 20;

\echo ''
\echo '====================================================='
\echo '  PASO 4: Buscar específicamente customers/clients'
\echo '====================================================='
-- Buscar con 'customers'
SELECT 'Buscando table_name = customers' as busqueda;
SELECT COUNT(*) as total
FROM sync_hashes
WHERE table_name = 'customers'
AND deleted_at IS NOT NULL;

\echo ''

-- Buscar con 'clients' (por si se guardó con ese nombre)
SELECT 'Buscando table_name = clients' as busqueda;
SELECT COUNT(*) as total
FROM sync_hashes
WHERE table_name = 'clients'
AND deleted_at IS NOT NULL;

\echo ''
\echo '====================================================='
\echo '  PASO 5: Verificar TODOS los registros de customers'
\echo '====================================================='
SELECT
    id,
    table_name,
    record_key,
    record_hash,
    deleted_at,
    synced_at,
    updated_at
FROM sync_hashes
WHERE table_name IN ('customers', 'clients')
ORDER BY deleted_at DESC NULLS LAST
LIMIT 10;

\echo ''
\echo '====================================================='
\echo '  PASO 6: Simular la consulta exacta del código'
\echo '====================================================='
SELECT 'Consulta exacta del código Python:' as info;
\echo 'SELECT record_key'
\echo 'FROM sync_hashes'
\echo 'WHERE table_name = customers'
\echo 'AND deleted_at IS NOT NULL'
\echo 'ORDER BY deleted_at DESC'

SELECT record_key
FROM sync_hashes
WHERE table_name = 'customers'
AND deleted_at IS NOT NULL
ORDER BY deleted_at DESC;

\echo ''
\echo '====================================================='
\echo '  📊 RESULTADOS ESPERADOS'
\echo '====================================================='
/*
Si PASO 1 muestra:
- ✅ 'customers' → El nombre está correcto
- ❌ 'clients' → PROBLEMA: El código busca 'customers' pero se guardó como 'clients'

Si PASO 2 muestra:
- ✅ con_deleted_at > 0 para customers → Hay registros
- ❌ con_deleted_at = 0 → PROBLEMA: No hay registros marcados como eliminados

Si PASO 5 muestra:
- ✅ deleted_at tiene valores → Los registros están marcados
- ❌ deleted_at es NULL → PROBLEMA: El trigger no está marcando los registros
*/

\echo ''
\echo '====================================================='
\echo '  ✅ Si encontraste el problema, aquí está la solución'
\echo '====================================================='

-- Si el problema es table_name = 'clients' en lugar de 'customers':
/*
UPDATE sync_hashes
SET table_name = 'customers'
WHERE table_name = 'clients';
*/

-- Si el problema es que el trigger no está funcionando:
/*
-- Verificar si el trigger existe
SELECT tgname FROM pg_trigger
WHERE tgname = 'tr_clients_mark_deleted_sync_hashes';

-- Si no existe, crearlo (ver script actualizar_trigger_cliente.sql)
*/
