-- ====================================================================
-- SCRIPT: Consultas útiles para monitoreo y mantenimiento
-- AUTOR: Sistema de Sincronización PostgreSQL → MySQL
-- FECHA: 2025-01-22
-- ====================================================================

-- ====================================================================
-- 1. ESTADO GENERAL DE SINCRONIZACIÓN
-- ====================================================================

-- Resumen de tablas sincronizadas
SELECT
    table_name AS "Tabla",
    COUNT(*) AS "Total Registros",
    TO_CHAR(MIN(synced_at), 'YYYY-MM-DD HH24:MI') AS "Primera Sync",
    TO_CHAR(MAX(updated_at), 'YYYY-MM-DD HH24:MI') AS "Última Sync",
    CURRENT_TIMESTAMP - MAX(updated_at) AS "Tiempo Sin Sync"
FROM sync_hashes
WHERE company_id = 1  -- Cambiar por tu company_id
GROUP BY table_name
ORDER BY table_name;

-- Total de registros sincronizados
SELECT
    COUNT(*) AS "Total Hashes Almacenados",
    COUNT(DISTINCT table_name) AS "Tablas Sincronizadas",
    COUNT(DISTINCT company_id) AS "Compañías"
FROM sync_hashes;

-- ====================================================================
-- 2. DETECTAR PROBLEMAS
-- ====================================================================

-- Registros en sync_hashes que ya no existen en PostgreSQL
-- (Esto indica posibles eliminaciones)
SELECT
    sh.table_name,
    sh.record_key,
    sh.updated_at AS "Última Sync",
    'Ya no existe en origen' AS "Problema"
FROM sync_hashes sh
WHERE sh.company_id = 1
  AND sh.table_name = 'products'
  AND sh.record_key NOT IN (
      SELECT code FROM products WHERE code IS NOT NULL
  )
LIMIT 20;

-- ====================================================================
-- 3. PRODUCTOS
-- ====================================================================

-- Productos sincronizados vs totales
SELECT
    'Sincronizados' AS "Estado",
    COUNT(*) AS "Total"
FROM sync_hashes
WHERE table_name = 'products' AND company_id = 1

UNION ALL

SELECT
    'En PostgreSQL' AS "Estado",
    COUNT(*) AS "Total"
FROM products
WHERE code IS NOT NULL AND code != '';

-- Productos NO sincronizados (nuevos)
SELECT
    p.code AS "Código",
    p.description AS "Descripción",
    p.price AS "Precio",
    'No sincronizado' AS "Estado"
FROM products p
WHERE p.code IS NOT NULL
  AND p.code != ''
  AND NOT EXISTS (
      SELECT 1 FROM sync_hashes sh
      WHERE sh.table_name = 'products'
        AND sh.record_key = p.code
        AND sh.company_id = 1
  )
LIMIT 20;

-- Últimos productos sincronizados
SELECT
    sh.record_key AS "Código",
    sh.updated_at AS "Sincronizado",
    'OK' AS "Estado"
FROM sync_hashes sh
WHERE sh.table_name = 'products'
  AND sh.company_id = 1
ORDER BY sh.updated_at DESC
LIMIT 20;

-- ====================================================================
-- 4. CUSTOMERS (CLIENTS)
-- ====================================================================

-- Customers NO sincronizados
SELECT
    c.code AS "Código",
    c.description AS "Nombre",
    c.email AS "Email",
    'No sincronizado' AS "Estado"
FROM clients c
WHERE c.code IS NOT NULL
  AND c.code != ''
  AND c.description IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM sync_hashes sh
      WHERE sh.table_name = 'customers'
        AND sh.record_key = c.code
        AND sh.company_id = 1
  )
LIMIT 20;

-- ====================================================================
-- 5. SELLERS
-- ====================================================================

-- Sellers NO sincronizados
SELECT
    s.code AS "Código",
    u.description AS "Nombre",
    u.email AS "Email",
    'No sincronizado' AS "Estado"
FROM sellers s
JOIN users u ON s.user_code = u.code
WHERE u.email IS NOT NULL
  AND u.email != ''
  AND NOT EXISTS (
      SELECT 1 FROM sync_hashes sh
      WHERE sh.table_name = 'sellers'
        AND sh.record_key = s.code
        AND sh.company_id = 1
  )
LIMIT 20;

-- ====================================================================
-- 6. CATEGORIES (DEPARTMENTS)
-- ====================================================================

-- Categories NO sincronizadas
SELECT
    d.code AS "Código",
    d.description AS "Descripción",
    'No sincronizado' AS "Estado"
FROM department d
WHERE d.code IS NOT NULL
  AND d.code != ''
  AND NOT EXISTS (
      SELECT 1 FROM sync_hashes sh
      WHERE sh.table_name = 'categories'
        AND sh.record_key = d.code
        AND sh.company_id = 1
  );

-- ====================================================================
-- 7. ANÁLISIS DE ACTIVIDAD
-- ====================================================================

-- Actividad de sincronización por día (últimos 7 días)
SELECT
    DATE(updated_at) AS "Fecha",
    COUNT(*) AS "Total Actualizaciones",
    COUNT(DISTINCT table_name) AS "Tablas Afectadas"
FROM sync_hashes
WHERE company_id = 1
  AND updated_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(updated_at)
ORDER BY DATE(updated_at) DESC;

-- Distribución por tabla
SELECT
    table_name AS "Tabla",
    COUNT(*) AS "Registros",
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS "% del Total"
FROM sync_hashes
WHERE company_id = 1
GROUP BY table_name
ORDER BY COUNT(*) DESC;

-- ====================================================================
-- 8. MANTENIMIENTO
-- ====================================================================

-- Espacio utilizado por la tabla
SELECT
    pg_size_pretty(pg_total_relation_size('sync_hashes')) AS "Tamaño Total",
    pg_size_pretty(pg_relation_size('sync_hashes')) AS "Tamaño Tabla",
    pg_size_pretty(pg_total_relation_size('sync_hashes') - pg_relation_size('sync_hashes')) AS "Tamaño Índices";

-- Registros duplicados (no debería haber ninguno)
SELECT
    table_name,
    record_key,
    company_id,
    COUNT(*) AS "Duplicados"
FROM sync_hashes
GROUP BY table_name, record_key, company_id
HAVING COUNT(*) > 1;

-- Hashes antiguos (no actualizados en más de 30 días)
SELECT
    table_name,
    COUNT(*) AS "Registros Antiguos",
    CURRENT_TIMESTAMP - MAX(updated_at) AS "Tiempo Sin Actualizar"
FROM sync_hashes
WHERE company_id = 1
  AND updated_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
GROUP BY table_name;

-- ====================================================================
-- 9. EXPORTAR DATOS
-- ====================================================================

-- Exportar todos los hashes a CSV (desde psql)
-- COPY (
--     SELECT table_name, record_key, record_hash, updated_at, company_id
--     FROM sync_hashes
--     WHERE company_id = 1
--     ORDER BY table_name, record_key
-- ) TO '/tmp/sync_hashes_backup.csv' CSV HEADER;

-- Exportar con datos completos (JSONB)
-- COPY (
--     SELECT table_name, record_key, record_hash, last_sync_data, updated_at
--     FROM sync_hashes
--     WHERE company_id = 1
--     ORDER BY updated_at DESC
-- ) TO '/tmp/sync_hashes_full_backup.csv' CSV HEADER;

-- ====================================================================
-- 10. LIMPIEZA
-- ====================================================================

-- Ver registros que serían eliminados (ejemplo: más de 1 año sin actualizar)
-- SELECT COUNT(*)
-- FROM sync_hashes
-- WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '1 year';

-- Eliminar registros antiguos (CUIDADO: Ejecutar solo después de verificar)
-- DELETE FROM sync_hashes
-- WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '1 year'
-- AND company_id = 1;

-- ====================================================================
-- FIN DE CONSULTAS
-- ====================================================================
