-- ============================================================================
-- PRUEBA MANUAL DE TRIGGERS (CORREGIDO)
-- ============================================================================

-- 1. Verificar sync_config
SELECT '=== 1. sync_config ===' as info;
SELECT * FROM sync_config WHERE key = 'company_id';

-- 2. Verificar triggers existentes
SELECT '=== 2. Triggers creados ===' as info;
SELECT tgname, tgrelid::regclass as table_name
FROM pg_trigger
WHERE tgname LIKE '%sync_hashes%'
ORDER BY tgname;

-- 3. Verificar si hay triggers INSERT
SELECT '=== 3. Buscar triggers INSERT ===' as info;
SELECT tgname
FROM pg_trigger
WHERE tgname LIKE '%inserted%'
OR tgname LIKE '%mark%';

-- 4. Prueba de INSERT en products
SELECT '=== 4. INSERT producto de prueba ===' as info;
DELETE FROM products WHERE code = 'TEST_TRIGGER_001';
INSERT INTO products (code, description, sale_price, sale_tax)
VALUES ('TEST_TRIGGER_001', 'Producto prueba trigger', 100, '16');

-- 5. Verificar sync_hashes después del INSERT
SELECT '=== 5. Verificar sync_hashes post-INSERT ===' as info;
SELECT
    table_name,
    record_key,
    pending_sync,
    company_id,
    updated_at
FROM sync_hashes
WHERE table_name = 'products'
AND record_key = 'TEST_TRIGGER_001';

-- 6. Prueba de UPDATE
SELECT '=== 6. UPDATE producto ===' as info;
UPDATE products
SET description = 'Producto ACTUALIZADO'
WHERE code = 'TEST_TRIGGER_001';

-- 7. Verificar sync_hashes después del UPDATE
SELECT '=== 7. Verificar sync_hashes post-UPDATE ===' as info;
SELECT
    table_name,
    record_key,
    pending_sync,
    updated_at
FROM sync_hashes
WHERE table_name = 'products'
AND record_key = 'TEST_TRIGGER_001';

-- 8. Prueba de DELETE
SELECT '=== 8. DELETE producto ===' as info;
DELETE FROM products WHERE code = 'TEST_TRIGGER_001';

-- 9. Verificar sync_hashes después del DELETE
SELECT '=== 9. Verificar sync_hashes post-DELETE ===' as info;
SELECT
    table_name,
    record_key,
    pending_sync,
    deleted_at
FROM sync_hashes
WHERE table_name = 'products'
AND record_key = 'TEST_TRIGGER_001';

-- 10. Limpiar
SELECT '=== 10. Limpiar ===' as info;
DELETE FROM sync_hashes WHERE record_key = 'TEST_TRIGGER_001';

SELECT '=== ✅ FIN ===' as info;
