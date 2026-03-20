-- ============================================================================
-- PRUEBA MANUAL DE TRIGGERS
-- ============================================================================
-- Ejecutar este script directamente en PostgreSQL para verificar los triggers

-- 1. Verificar que sync_config tenga company_id
SELECT '=== 1. Verificar sync_config ===' as info;
SELECT key, value FROM sync_config WHERE key = 'company_id';

-- Si no existe, insertar:
-- INSERT INTO sync_config (key, value, updated_at)
-- VALUES ('company_id', '1', NOW());

-- 2. Verificar triggers existentes
SELECT '=== 2. Triggers existentes ===' as info;
SELECT
    tgname as trigger_name,
    CASE tgtype::integer & 66
        WHEN 2 THEN 'DELETE'
        WHEN 4 THEN 'INSERT'
        WHEN 8 THEN 'UPDATE'
        WHEN 16 THEN 'TRUNCATE'
        ELSE 'OTHER'
    END as trigger_type,
    tgrelid::regclass as table_name
FROM pg_trigger
WHERE tgname LIKE '%sync_hashes%'
ORDER BY tgname;

-- 3. Prueba de INSERT en products
SELECT '=== 3. Prueba INSERT ===' as info;
INSERT INTO products (code, description, price, cost)
VALUES ('TEST_TRIGGER_001', 'Producto prueba trigger', 100.00, 50.00);

-- 4. Verificar que se creó en sync_hashes
SELECT '=== 4. Verificar sync_hashes después de INSERT ===' as info;
SELECT
    table_name,
    record_key,
    pending_sync,
    company_id,
    created_at
FROM sync_hashes
WHERE table_name = 'products'
AND record_key = 'TEST_TRIGGER_001';

-- 5. Prueba de UPDATE en products
SELECT '=== 5. Prueba UPDATE ===' as info;
UPDATE products
SET description = 'Producto prueba trigger ACTUALIZADO'
WHERE code = 'TEST_TRIGGER_001';

-- 6. Verificar que se actualizó pending_sync
SELECT '=== 6. Verificar sync_hashes después de UPDATE ===' as info;
SELECT
    table_name,
    record_key,
    pending_sync,
    updated_at
FROM sync_hashes
WHERE table_name = 'products'
AND record_key = 'TEST_TRIGGER_001';

-- 7. Prueba de DELETE en products
SELECT '=== 7. Prueba DELETE ===' as info;
DELETE FROM products WHERE code = 'TEST_TRIGGER_001';

-- 8. Verificar que se marcó deleted_at
SELECT '=== 8. Verificar sync_hashes después de DELETE ===' as info;
SELECT
    table_name,
    record_key,
    pending_sync,
    deleted_at
FROM sync_hashes
WHERE table_name = 'products'
AND record_key = 'TEST_TRIGGER_001';

-- 9. Limpiar datos de prueba
SELECT '=== 9. Limpiar datos de prueba ===' as info;
DELETE FROM sync_hashes WHERE record_key = 'TEST_TRIGGER_001';

-- 10. Resumen final
SELECT '=== ✅ PRUEBA COMPLETADA ===' as info;
SELECT 'Si ves registros en los pasos 4, 6 y 8, los triggers funcionan correctamente' as resumen;
