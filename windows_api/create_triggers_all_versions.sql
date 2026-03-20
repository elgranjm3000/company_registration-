-- Crear triggers compatibles con MÚLTIPLES VERSIONES de PostgreSQL
-- Este archivo detecta automáticamente la versión y usa la sintaxis correcta

-- ===========================================================================
-- PRODUCTS
-- ===========================================================================

-- Función para INSERT/UPDATE en products (compatible con todas las versiones)
CREATE OR REPLACE FUNCTION trigger_mark_product_updated_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_pg_version TEXT;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Detectar versión de PostgreSQL
    SELECT substring(version() from 'PostgreSQL ([0-9]+\.[0-9]+)') INTO v_pg_version;

    -- PostgreSQL 9.5+ usa ON CONFLICT (más eficiente)
    IF v_pg_version::float >= 9.5 THEN
        INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
        VALUES ('products', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
        ON CONFLICT (table_name, record_key, company_id)
        DO UPDATE SET
            pending_sync = TRUE,
            updated_at = NOW();
    ELSE
        -- PostgreSQL 9.0-9.4 usa IF/THEN
        SELECT COUNT(*) INTO v_exists
        FROM sync_hashes
        WHERE table_name = 'products'
        AND record_key = NEW.code
        AND company_id = v_company_id;

        IF v_exists > 0 THEN
            UPDATE sync_hashes
            SET pending_sync = TRUE,
                updated_at = NOW()
            WHERE table_name = 'products'
            AND record_key = NEW.code
            AND company_id = v_company_id;
        ELSE
            INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
            VALUES ('products', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
        END IF;
    END IF;

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

-- ===========================================================================
-- CLIENTS
-- ===========================================================================

-- Función para INSERT/UPDATE en clients
CREATE OR REPLACE FUNCTION trigger_mark_client_updated_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_pg_version TEXT;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Detectar versión de PostgreSQL
    SELECT substring(version() from 'PostgreSQL ([0-9]+\.[0-9]+)') INTO v_pg_version;

    -- PostgreSQL 9.5+ usa ON CONFLICT
    IF v_pg_version::float >= 9.5 THEN
        INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
        VALUES ('customers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
        ON CONFLICT (table_name, record_key, company_id)
        DO UPDATE SET
            pending_sync = TRUE,
            updated_at = NOW();
    ELSE
        -- PostgreSQL 9.0-9.4 usa IF/THEN
        SELECT COUNT(*) INTO v_exists
        FROM sync_hashes
        WHERE table_name = 'customers'
        AND record_key = NEW.code
        AND company_id = v_company_id;

        IF v_exists > 0 THEN
            UPDATE sync_hashes
            SET pending_sync = TRUE,
                updated_at = NOW()
            WHERE table_name = 'customers'
            AND record_key = NEW.code
            AND company_id = v_company_id;
        ELSE
            INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
            VALUES ('customers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
        END IF;
    END IF;

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

-- Función para DELETE en clients
CREATE OR REPLACE FUNCTION trigger_mark_client_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro en sync_hashes
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'customers'
    AND record_key = OLD.code
    AND company_id = v_company_id;

    -- Si existe, actualizar deleted_at
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET deleted_at = NOW()
        WHERE table_name = 'customers'
        AND record_key = OLD.code
        AND company_id = v_company_id;
    ELSE
        -- Si no existe, insertar nuevo registro con deleted_at
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
        VALUES ('customers', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_clients_mark_deleted_sync_hashes ON clients;
CREATE TRIGGER tr_clients_mark_deleted_sync_hashes
    AFTER DELETE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_deleted_sync_hashes();

-- ===========================================================================
-- SELLERS
-- ===========================================================================

-- Función para INSERT/UPDATE en sellers
CREATE OR REPLACE FUNCTION trigger_mark_seller_updated_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_pg_version TEXT;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Detectar versión de PostgreSQL
    SELECT substring(version() from 'PostgreSQL ([0-9]+\.[0-9]+)') INTO v_pg_version;

    -- PostgreSQL 9.5+ usa ON CONFLICT
    IF v_pg_version::float >= 9.5 THEN
        INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
        VALUES ('sellers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW())
        ON CONFLICT (table_name, record_key, company_id)
        DO UPDATE SET
            pending_sync = TRUE,
            updated_at = NOW();
    ELSE
        -- PostgreSQL 9.0-9.4 usa IF/THEN
        SELECT COUNT(*) INTO v_exists
        FROM sync_hashes
        WHERE table_name = 'sellers'
        AND record_key = NEW.code
        AND company_id = v_company_id;

        IF v_exists > 0 THEN
            UPDATE sync_hashes
            SET pending_sync = TRUE,
                updated_at = NOW()
            WHERE table_name = 'sellers'
            AND record_key = NEW.code
            AND company_id = v_company_id;
        ELSE
            INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
            VALUES ('sellers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_sellers_mark_inserted_sync_hashes ON sellers;
CREATE TRIGGER tr_sellers_mark_inserted_sync_hashes
    AFTER INSERT ON sellers
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_seller_updated_sync_hashes();

DROP TRIGGER IF EXISTS tr_sellers_mark_updated_sync_hashes ON sellers;
CREATE TRIGGER tr_sellers_mark_updated_sync_hashes
    AFTER UPDATE ON sellers
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_seller_updated_sync_hashes();

-- Función para DELETE en sellers
CREATE OR REPLACE FUNCTION trigger_mark_seller_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

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

-- ===========================================================================
-- VERIFICACIÓN
-- ===========================================================================

SELECT
    'Versión PostgreSQL' as info,
    version() as version;

SELECT
    'Triggers creados exitosamente' as status,
    'Compatible con PostgreSQL 9.0+' as compatibility;

-- Verificar triggers activos
SELECT
    'INSERT products' as trigger_name,
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_products_mark_inserted_sync_hashes')
         THEN '✅' ELSE '❌' END as status
UNION ALL
SELECT 'UPDATE products',
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_products_mark_updated_sync_hashes')
         THEN '✅' ELSE '❌' END
UNION ALL
SELECT 'INSERT clients',
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_clients_mark_inserted_sync_hashes')
         THEN '✅' ELSE '❌' END
UNION ALL
SELECT 'UPDATE clients',
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_clients_mark_updated_sync_hashes')
         THEN '✅' ELSE '❌' END
UNION ALL
SELECT 'DELETE clients',
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_clients_mark_deleted_sync_hashes')
         THEN '✅' ELSE '❌' END
UNION ALL
SELECT 'INSERT sellers',
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_sellers_mark_inserted_sync_hashes')
         THEN '✅' ELSE '❌' END
UNION ALL
SELECT 'UPDATE sellers',
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_sellers_mark_updated_sync_hashes')
         THEN '✅' ELSE '❌' END
UNION ALL
SELECT 'DELETE sellers',
    CASE WHEN EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'tr_sellers_mark_deleted_sync_hashes')
         THEN '✅' ELSE '❌' END;
