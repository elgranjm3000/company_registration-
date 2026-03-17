-- ============================================
-- INSTALACIÓN DE TRIGGER PARA ELIMINACIÓN DE PRODUCTOS
-- ============================================
-- Este script agrega el trigger que marca automáticamente
-- los productos eliminados en la tabla sync_hashes
--
-- Uso:
--   psql -U postgres -d chrystaldb -f install_trigger_eliminar_productos.sql
-- ============================================

-- PASO 1: Agregar columna deleted_at a sync_hashes
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'sync_hashes'
        AND column_name = 'deleted_at'
    ) THEN
        ALTER TABLE sync_hashes ADD COLUMN deleted_at TIMESTAMP NULL;
        RAISE NOTICE '✅ Columna deleted_at agregada a sync_hashes';
    ELSE
        RAISE NOTICE 'ℹ️ Columna deleted_at ya existe en sync_hashes';
    END IF;
END $$;

-- PASO 2: Crear función del trigger
CREATE OR REPLACE FUNCTION trigger_mark_product_deleted()
RETURNS TRIGGER AS $$
BEGIN
    -- Marcar el registro en sync_hashes como eliminado
    UPDATE sync_hashes
    SET deleted_at = NOW()
    WHERE table_name = 'products'
    AND record_key = OLD.code;

    -- Si no existe en sync_hashes, insertar el registro marcado como eliminado
    IF NOT FOUND THEN
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
        VALUES ('products', OLD.code, md5(OLD.code::text), NOW());
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- PASO 3: Eliminar trigger anterior si existe
DROP TRIGGER IF EXISTS tr_products_mark_deleted ON products;

-- PASO 4: Crear trigger
CREATE TRIGGER tr_products_mark_deleted
    AFTER DELETE ON products
    FOR EACH ROW
    EXECUTE FUNCTION trigger_mark_product_deleted();

-- ============================================
-- VERIFICACIÓN
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '╔════════════════════════════════════════════════════════════╗';
    RAISE NOTICE '║     TRIGGER DE ELIMINACIÓN INSTALADO CORRECTAMENTE             ║';
    RAISE NOTICE '╚════════════════════════════════════════════════════════════╝';
    RAISE NOTICE '';
    RAISE NOTICE '✅ Trigger activo: tr_products_mark_deleted';
    RAISE NOTICE '   - Se activa automáticamente al eliminar un producto';
    RAISE NOTICE '   - Marca el producto en sync_hashes con deleted_at';
    RAISE NOTICE '';
    RAISE NOTICE '📋 Estructura de sync_hashes:';
    RAISE NOTICE '   - table_name: Nombre de la tabla (ej: "products")';
    RAISE NOTICE '   - record_key: Clave del registro (ej: código del producto)';
    RAISE NOTICE '   - record_hash: Hash del registro';
    RAISE NOTICE '   - deleted_at: ⭐ Timestamp de eliminación (NUEVO CAMPO)';
    RAISE NOTICE '';
    RAISE NOTICE '🔄 Flujo de eliminación:';
    RAISE NOTICE '   1. Usuario ejecuta: DELETE FROM products WHERE code = ''XXX''';
    RAISE NOTICE '   2. Trigger se activa automáticamente';
    RAISE NOTICE '   3. Trigger marca: UPDATE sync_hashes SET deleted_at = NOW()';
    RAISE NOTICE '   4. Sincronización lee: WHERE deleted_at IS NOT NULL';
    RAISE NOTICE '   5. Sincronización elimina de MySQL';
    RAISE NOTICE '   6. Sincronización limpia: DELETE FROM sync_hashes';
    RAISE NOTICE '';
    RAISE NOTICE '✨ Listo para usar!';
    RAISE NOTICE '';
END $$;

-- Mostrar estructura de sync_hashes
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'sync_hashes'
ORDER BY ordinal_position;
