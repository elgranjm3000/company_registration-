-- =====================================================
-- 🔧 CORRECCIÓN DEL TRIGGER DE ELIMINACIÓN DE CLIENTES
-- =====================================================
-- Ejecutar este script en la base de datos del cliente
-- para corregir el trigger de eliminación de clientes
-- =====================================================

-- 1. Eliminar trigger antiguo si existe
DROP TRIGGER IF EXISTS tr_clients_mark_deleted_sync_hashes ON clients;

-- 2. Eliminar función antigua COMPLETAMENTE (esto es crítico)
DROP FUNCTION IF EXISTS trigger_mark_client_deleted_sync_hashes();

-- 3. Crear la función CORREGIDA desde cero
CREATE OR REPLACE FUNCTION trigger_mark_client_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_exists INTEGER;
BEGIN
    -- Verificar si ya existe el registro en sync_hashes
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'customers'
    AND record_key = OLD.code;  -- ✅ CORREGIDO: Usar OLD.code, no OLD.email

    -- Si existe, actualizar deleted_at
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET deleted_at = NOW()
        WHERE table_name = 'customers'
        AND record_key = OLD.code;  -- ✅ CORREGIDO: Usar OLD.code, no OLD.email
    ELSE
        -- Si no existe, insertar nuevo registro con deleted_at
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
        VALUES ('customers', OLD.code, md5(OLD.code::text), NOW());  -- ✅ CORREGIDO: OLD.code
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- 4. Crear el trigger con la función corregida
CREATE TRIGGER tr_clients_mark_deleted_sync_hashes
    AFTER DELETE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_deleted_sync_hashes();

-- =====================================================
-- ✅ Verificación
-- =====================================================

-- Mostrar la versión del trigger
SELECT
    'Versión del trigger' as check,
    CASE
        WHEN pg_get_functiondef(oid) LIKE '%OLD.code%'
        THEN '✅ VERSIÓN CORRECTA - Usa OLD.code'
        ELSE '❌ VERSIÓN INCORRECTA - Usa OLD.email'
    END as resultado
FROM pg_proc
WHERE proname = 'trigger_mark_client_deleted_sync_hashes';

-- Mostrar si el trigger existe
SELECT
    'Trigger existe' as check,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'tr_clients_mark_deleted_sync_hashes'
        )
        THEN '✅ SÍ'
        ELSE '❌ NO'
    END as resultado;

-- =====================================================
-- 📋 Resumen de cambios
-- =====================================================
/*
CAMBIOS REALIZADOS:
1. ✅ Cambiado OLD.email → OLD.code (CORRECCIÓN CRÍTICA)
2. ✅ Agregado DECLARE v_exists INTEGER
3. ✅ Cambiado IF NOT FOUND → SELECT COUNT(*) INTO v_exists
4. ✅ Cambiado lógica UPDATE/INSERT por IF v_exists > 0

ESTOS CAMBIOS CORRIGEN:
- El problema de buscar por email en lugar de code
- El problema de IF NOT FOUND después de UPDATE
- La incompatibilidad con PostgreSQL 9.1+
*/
