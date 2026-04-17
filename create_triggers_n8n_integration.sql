-- ============================================================================
-- TRIGGERS POSTGRESQL PARA INTEGRACIÓN CON n8n
-- ============================================================================
-- Estos triggers usan LISTEN/NOTIFY para enviar notificaciones en tiempo real
-- cuando ocurren cambios en las tablas.
--
-- El Python Bridge escucha estas notificaciones y las envía a un webhook de n8n.
--
-- Tablas monitoreadas:
--   - products
--   - customers (tabla real: clients)
--   - sellers
--   - sales (sales_operations)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. FUNCIÓN CENTRAL DE NOTIFICACIÓN
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION notify_table_changes()
RETURNS TRIGGER AS $$
DECLARE
    payload TEXT;
    record_id INTEGER;
BEGIN
    -- Determinar el ID del registro (según la tabla)
    IF TG_OP = 'DELETE' THEN
        record_id := OLD.id;
    ELSE
        record_id := NEW.id;
    END IF;

    -- Crear payload JSON
    payload = json_build_object(
        'table_name', TG_TABLE_NAME,
        'operation', TG_OP,
        'record_id', record_id,
        'timestamp', now()
    )::text;

    -- Enviar notificación
    PERFORM pg_notify('n8n_sync', payload);

    -- Retornar según la operación
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- 2. TRIGGERS PARA PRODUCTS
-- ----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS products_n8n_trigger ON products;

CREATE TRIGGER products_n8n_trigger
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW
EXECUTE FUNCTION notify_table_changes();

COMMENT ON TRIGGER products_n8n_trigger ON products IS
'Notifica a n8n cuando hay cambios en products';

-- ----------------------------------------------------------------------------
-- 3. TRIGGERS PARA CUSTOMERS (clients)
-- ----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS customers_n8n_trigger ON clients;

CREATE TRIGGER customers_n8n_trigger
AFTER INSERT OR UPDATE OR DELETE ON clients
FOR EACH ROW
EXECUTE FUNCTION notify_table_changes();

COMMENT ON TRIGGER customers_n8n_trigger ON clients IS
'Notifica a n8n cuando hay cambios en customers (clients)';

-- ----------------------------------------------------------------------------
-- 4. TRIGGERS PARA SELLERS
-- ----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS sellers_n8n_trigger ON sellers;

CREATE TRIGGER sellers_n8n_trigger
AFTER INSERT OR UPDATE OR DELETE ON sellers
FOR EACH ROW
EXECUTE FUNCTION notify_table_changes();

COMMENT ON TRIGGER sellers_n8n_trigger ON sellers IS
'Notifica a n8n cuando hay cambios en sellers';

-- ----------------------------------------------------------------------------
-- 5. TRIGGERS PARA SALES (sales_operations)
-- ----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS sales_n8n_trigger ON sales_operations;

CREATE TRIGGER sales_n8n_trigger
AFTER INSERT OR UPDATE OR DELETE ON sales_operations
FOR EACH ROW
EXECUTE FUNCTION notify_table_changes();

COMMENT ON TRIGGER sales_n8n_trigger ON sales_operations IS
'Notifica a n8n cuando hay cambios en sales (sales_operations)';

-- ----------------------------------------------------------------------------
-- 6. VERIFICACIÓN
-- ----------------------------------------------------------------------------

-- Verificar que los triggers estén creados
SELECT
    schemaname,
    tablename,
    tgname AS trigger_name,
    pg_get_triggerdef(oid) AS trigger_definition
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE tgname LIKE '%_n8n_trigger'
ORDER BY tablename;

-- Resultado esperado:
-- schemaname | tablename    | trigger_name           | trigger_definition
-- -----------+--------------+------------------------+--------------------------
-- public     | clients      | customers_n8n_trigger | CREATE TRIGGER...
-- public     | products     | products_n8n_trigger   | CREATE TRIGGER...
-- public     | sales_operations | sales_n8n_trigger | CREATE TRIGGER...
-- public     | sellers      | sellers_n8n_trigger    | CREATE TRIGGER...

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
--
-- Para probar los triggers:
--
-- 1. Iniciar el Python Bridge (python_bridge_n8n.py)
-- 2. En otra terminal, ejecutar:
--
--    -- Test INSERT
--    INSERT INTO products (name, price) VALUES ('Test Product', 100);
--
--    -- Test UPDATE
--    UPDATE products SET price = 150 WHERE name = 'Test Product';
--
--    -- Test DELETE
--    DELETE FROM products WHERE name = 'Test Product';
--
-- Deberías ver las notificaciones en el log del Python Bridge.
--
-- ============================================================================
