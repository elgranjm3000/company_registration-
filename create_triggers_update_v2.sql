-- Crear triggers INSERT/UPDATE/DELETE que obtienen company_id desde sync_config

-- Trigger para products (INSERT y UPDATE usan la misma función)
CREATE OR REPLACE FUNCTION trigger_mark_product_updated_sync_hashes()
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
    VALUES ('products', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
    ON CONFLICT (table_name, record_key, company_id)
    DO UPDATE SET
        pending_sync = TRUE,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_products_mark_inserted_sync_hashes ON products;
CREATE TRIGGER tr_products_mark_inserted_sync_hashes
    AFTER INSERT ON products
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_updated_sync_hashes();

DROP TRIGGER IF EXISTS tr_products_mark_updated_sync_hashes ON products;
CREATE TRIGGER tr_products_mark_updated_sync_hashes
    AFTER UPDATE ON products
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_updated_sync_hashes();

-- Trigger para clients (INSERT y UPDATE usan la misma función)
CREATE OR REPLACE FUNCTION trigger_mark_client_updated_sync_hashes()
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
    VALUES ('customers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
    ON CONFLICT (table_name, record_key, company_id)
    DO UPDATE SET
        pending_sync = TRUE,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_clients_mark_inserted_sync_hashes ON clients;
CREATE TRIGGER tr_clients_mark_inserted_sync_hashes
    AFTER INSERT ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_updated_sync_hashes();

DROP TRIGGER IF EXISTS tr_clients_mark_updated_sync_hashes ON clients;
CREATE TRIGGER tr_clients_mark_updated_sync_hashes
    AFTER UPDATE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_updated_sync_hashes();
