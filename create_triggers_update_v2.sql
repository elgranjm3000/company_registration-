-- Crear triggers UPDATE simplificados (sin company_id dependiente)
-- El sistema Python completará el company_id cuando sincronice

-- Trigger para products
CREATE OR REPLACE FUNCTION trigger_mark_product_updated_sync_hashes()
RETURNS TRIGGER AS '
BEGIN
    -- Marcar como pendiente de sincronización
    -- Usar company_id = 1 como valor temporal (el sistema lo corregirá)
    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
    VALUES (''products'', NEW.code, md5(NEW.code::text), TRUE, 1, NOW())
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
BEGIN
    -- Marcar como pendiente de sincronización
    -- Usar company_id = 1 como valor temporal (el sistema lo corregirá)
    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
    VALUES (''customers'', NEW.code, md5(NEW.code::text), TRUE, 1, NOW())
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
