-- Solución: Crear una tabla de configuración para almacenar el company_id
-- Esta tabla se mantendrá sincronizada con el company_id de MySQL

-- 1. Crear tabla de configuración si no existe
CREATE TABLE IF NOT EXISTS sync_config (
    key VARCHAR(100) PRIMARY KEY,
    value INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Insertar company_id si no existe
INSERT INTO sync_config (key, value)
VALUES ('current_company_id', 115)
ON CONFLICT (key) DO NOTHING;

-- 3. Trigger para products actualizado
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

-- 4. Trigger para clients actualizado
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

-- 5. Recrear triggers
DROP TRIGGER IF EXISTS tr_products_mark_updated_sync_hashes ON products;
CREATE TRIGGER tr_products_mark_updated_sync_hashes
    AFTER UPDATE ON products
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_updated_sync_hashes();

DROP TRIGGER IF EXISTS tr_clients_mark_updated_sync_hashes ON clients;
CREATE TRIGGER tr_clients_mark_updated_sync_hashes
    AFTER UPDATE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_updated_sync_hashes();
