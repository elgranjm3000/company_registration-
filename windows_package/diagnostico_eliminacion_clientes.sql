-- =====================================================
-- 📋 Script de Diagnóstico - Eliminación de Clientes
-- =====================================================
-- Ejecutar este script en PostgreSQL para verificar
-- que el sistema de eliminación está configurado
-- correctamente.
-- =====================================================

\echo '====================================================='
\echo '  DIAGNÓSTICO: Eliminación de Clientes'
\echo '====================================================='
\echo ''

-- 1. Verificar si el trigger existe
\echo '✅ PASO 1: Verificar si el trigger existe'
\echo '-----------------------------------------------------'
SELECT
    'Trigger existe' as check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'tr_clients_mark_deleted_sync_hashes'
        )
        THEN '✅ SÍ - El trigger está creado'
        ELSE '❌ NO - El trigger NO existe'
    END as resultado;

\echo ''

-- 2. Verificar la versión del trigger
\echo '✅ PASO 2: Verificar versión del trigger'
\echo '-----------------------------------------------------'
SELECT
    'Versión del trigger' as check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_proc
            WHERE proname = 'trigger_mark_client_deleted_sync_hashes'
            AND prosrc LIKE '%DECLARE%'
            AND prosrc LIKE '%v_exists%'
        )
        THEN '✅ VERSIÓN CORREGIDA - Tiene DECLARE v_exists'
        ELSE '❌ VERSIÓN ANTIGUA - Usa IF NOT FOUND (incorrecto)'
    END as resultado;

\echo ''

-- 3. Verificar estructura de sync_hashes
\echo '✅ PASO 3: Verificar tabla sync_hashes'
\echo '-----------------------------------------------------'
SELECT
    'Tabla sync_hashes' as check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'sync_hashes'
        )
        THEN '✅ La tabla existe'
        ELSE '❌ La tabla NO existe'
    END as resultado;

\echo ''

-- 4. Verificar si tiene columna deleted_at
SELECT
    'Columna deleted_at' as check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'sync_hashes'
            AND column_name = 'deleted_at'
        )
        THEN '✅ La columna deleted_at existe'
        ELSE '❌ La columna deleted_at NO existe'
    END as resultado;

\echo ''

-- 5. Mostrar clientes marcados para eliminación
\echo '✅ PASO 4: Clientes marcados para eliminación'
\echo '-----------------------------------------------------'
SELECT
    COUNT(*) as total_marcados,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ No hay pendientes'
        ELSE '⚠️ Hay clientes pendientes de eliminar'
    END as estado
FROM sync_hashes
WHERE table_name = 'customers'
  AND deleted_at IS NOT NULL;

\echo ''

-- 6. Mostrar detalles de clientes pendientes
\echo 'Detalle de clientes pendientes (si existen):'
SELECT
    record_key as code,
    deleted_at as fecha_eliminacion,
    EXTRACT(EPOCH FROM (NOW() - deleted_at))/60 as minutos_atras
FROM sync_hashes
WHERE table_name = 'customers'
  AND deleted_at IS NOT NULL
ORDER BY deleted_at DESC
LIMIT 5;

\echo ''

-- 7. Verificar trigger de sellers también
\echo '✅ PASO 5: Verificar trigger de sellers'
\echo '-----------------------------------------------------'
SELECT
    'Trigger sellers' as check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'tr_sellers_mark_deleted_sync_hashes'
        )
        THEN '✅ Trigger de sellers existe'
        ELSE '⚠️ Trigger de sellers NO existe'
    END as resultado;

\echo ''

-- 8. Resumen final
\echo '====================================================='
\echo '  📊 RESUMEN FINAL'
\echo '====================================================='
\echo ''

SELECT
    'Clientes totales' as metrica,
    COUNT(*) as valor
FROM clients
UNION ALL
SELECT
    'En sync_hashes',
    COUNT(*)
FROM sync_hashes
WHERE table_name = 'customers'
UNION ALL
SELECT
    'Marcados para eliminar',
    COUNT(*)
FROM sync_hashes
WHERE table_name = 'customers'
  AND deleted_at IS NOT NULL;

\echo ''
\echo '====================================================='
\echo '  ✅ Diagnóstico completado'
\echo '====================================================='
\echo ''
\echo 'Si todos los checks muestran ✅, el sistema está listo.'
\echo 'Si ves ❌, revisa el check específico que falló.'
\echo ''
