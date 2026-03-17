-- Crear triggers UPDATE para optimizar detección de cambios

-- Trigger para products
CREATE OR REPLACE FUNCTION trigger_mark_product_updated_sync_hashes()
RETURNS TRIGGER AS '
DECLARE
    v_company_id INTEGER;
BEGIN
    -- Obtener el company_id desde la tabla company
    SELECT id INTO v_company_id FROM company LIMIT 1;

    -- Insertar o actualizar en sync_hashes
    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
    VALUES (''products'', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
    ON CONFLICT (table_name, record_key, company_id)
    DO UPDATE SET
        pending_sync = TRUE,
        updated_at = NOW();

    RETURN NEW;
END;
' LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_products_mark_updated_sync_hashes ON products;

CREATE TRIGGER tr_products_mark_updated_sync_hashes
    AFTER UPDATE ON products
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_updated_sync_hashes();

-- Trigger para clients
CREATE OR REPLACE FUNCTION trigger_mark_client_updated_sync_hashes()
RETURNS TRIGGER AS '
DECLARE
    v_company_id INTEGER;
BEGIN
    -- Obtener el company_id desde la tabla company
    SELECT id INTO v_company_id FROM company LIMIT 1;

    -- Insertar o actualizar en sync_hashes
    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
    VALUES (''customers'', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
    ON CONFLICT (table_name, record_key, company_id)
    DO UPDATE SET
        pending_sync = TRUE,
        updated_at = NOW();

    RETURN NEW;
END;
' LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_clients_mark_updated_sync_hashes ON clients;

CREATE TRIGGER tr_clients_mark_updated_sync_hashes
    AFTER UPDATE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_updated_sync_hashes();
