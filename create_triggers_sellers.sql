-- Crear triggers para sellers que obtienen company_id desde sync_config

-- Trigger para INSERT/UPDATE en sellers
CREATE OR REPLACE FUNCTION trigger_mark_seller_updated_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'current_company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Marcar como pendiente de sincronización
    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
    VALUES ('sellers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
    ON CONFLICT (table_name, record_key, company_id)
    DO UPDATE SET
        pending_sync = TRUE,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_sellers_mark_updated_sync_hashes ON sellers;

CREATE TRIGGER tr_sellers_mark_updated_sync_hashes
    AFTER INSERT OR UPDATE ON sellers
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_seller_updated_sync_hashes();

-- Trigger para DELETE en sellers
CREATE OR REPLACE FUNCTION trigger_mark_seller_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'current_company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro en sync_hashes
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'sellers'
    AND record_key = OLD.code
    AND company_id = v_company_id;

    -- Si existe, actualizar deleted_at
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET deleted_at = NOW()
        WHERE table_name = 'sellers'
        AND record_key = OLD.code
        AND company_id = v_company_id;
    ELSE
        -- Si no existe, insertar nuevo registro con deleted_at
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
        VALUES ('sellers', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_sellers_mark_deleted_sync_hashes ON sellers;

CREATE TRIGGER tr_sellers_mark_deleted_sync_hashes
    AFTER DELETE ON sellers
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_seller_deleted_sync_hashes();

-- Verificación
SELECT
    'Trigger UPDATE sellers' as check_name,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'tr_sellers_mark_updated_sync_hashes'
        )
        THEN '✅ ACTIVO'
        ELSE '❌ NO EXISTE'
    END as status
UNION ALL
SELECT
    'Trigger DELETE sellers' as check_name,
    CASE
        WHEN EXISTS (
            SELECT 1 FROM pg_trigger
            WHERE tgname = 'tr_sellers_mark_deleted_sync_hashes'
        )
        THEN '✅ ACTIVO'
        ELSE '❌ NO EXISTE'
    END as status;
