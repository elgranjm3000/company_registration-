"""
Módulo de consultas SQL para sincronización

Centraliza todas las consultas SQL para facilitar el mantenimiento
y evitar duplicación de código.
"""

class SyncQueries:
    """Consultas SQL para sincronización PostgreSQL ↔ MySQL"""

    # ==================== POSTGRESQL ====================

    # Products
    PG_PRODUCTS_ALL = """
        SELECT DISTINCT ON (a.code)
            a.code,
            a.description,
            a.short_name,
            a.department,
            COALESCE(c.total_stock, 0) AS stock,
            a.product_type,
            a.coin,
            f.description AS description_coin,
            CASE
                WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999
                THEN 0
                ELSE b.maximum_price
            END AS price,
            CASE
                WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999
                THEN 0
                ELSE b.offer_price
            END AS cost,
            CASE
                WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999
                THEN 0
                ELSE b.higher_price
            END AS higher_price,
            a.minimal_stock AS min_stock,
            CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status
        FROM products a
        LEFT JOIN (
            SELECT product_code, SUM(stock) as total_stock
            FROM products_stock
            GROUP BY product_code
        ) c ON a.code = c.product_code
        LEFT JOIN products_units b ON a.code = b.product_code and b.unit = '00'
        LEFT JOIN coin f ON f.code = a.coin
        WHERE a.code IS NOT NULL
          AND a.code != ''
        ORDER BY a.code
    """

    PG_PRODUCTS_BY_CODES = """
        SELECT DISTINCT ON (a.code)
            a.code,
            a.description,
            a.short_name,
            a.department,
            COALESCE(c.total_stock, 0) AS stock,
            a.product_type,
            a.coin,
            f.description AS description_coin,
            CASE
                WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999
                THEN 0
                ELSE b.maximum_price
            END AS price,
            CASE
                WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999
                THEN 0
                ELSE b.offer_price
            END AS cost,
            CASE
                WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999
                THEN 0
                ELSE b.higher_price
            END AS higher_price,
            a.minimal_stock AS min_stock,
            CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status
        FROM products a
        LEFT JOIN (
            SELECT product_code, SUM(stock) as total_stock
            FROM products_stock
            GROUP BY product_code
        ) c ON a.code = c.product_code
        LEFT JOIN products_units b ON a.code = b.product_code and b.unit = '00'
        LEFT JOIN coin f ON f.code = a.coin
        WHERE a.code IN (%s)
          AND a.code IS NOT NULL
          AND a.code != ''
        ORDER BY a.code
    """

    # Customers
    PG_CUSTOMERS_ALL = """
        SELECT
            code,
            description,
            COALESCE(address, '') AS address,
            COALESCE(client_id, '') AS client_id,
            COALESCE(email, '') AS email,
            COALESCE(phone, '') AS phone,
            COALESCE(contact, '') AS contact
        FROM clients
        WHERE code IS NOT NULL
          AND code != ''
        ORDER BY code
    """

    # Sellers
    PG_SELLERS_ALL = """
        SELECT
            email,
            COALESCE(name, '') AS name,
            COALESCE(phone, '') AS phone,
            COALESCE(status, 'active') AS status
        FROM sellers
        WHERE email IS NOT NULL
          AND email != ''
        ORDER BY email
    """

    # Categories/Departments
    PG_DEPARTMENTS_ALL = """
        SELECT
            code,
            description
        FROM department
        WHERE code IS NOT NULL
          AND code != ''
        ORDER BY code
    """

    # Quotes (para sincronización MySQL → PostgreSQL)
    PG_QUOTES_FOR_SYNC = """
        SELECT
            q.id,
            q.correlative,
            q.customer_email,
            q.seller_email,
            q.status,
            q.total,
            q.created_at,
            q.updated_at
        FROM quotes q
        WHERE q.company_id = %s
        ORDER BY q.correlative
    """

    # ==================== MYSQL ====================

    # Products
    MYSQL_PRODUCTS_GET_BY_CODE = """
        SELECT id, code, name, description, price, cost,
               stock, status, category_id, higher_price
        FROM products
        WHERE code = %s AND company_id = %s
    """

    MYSQL_PRODUCTS_INSERT = """
        INSERT INTO products (
            company_id, code, name, description, price, cost,
            stock, status, category_id, higher_price,
            sale_tax, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
    """

    MYSQL_PRODUCTS_UPDATE = """
        UPDATE products SET
            name = %s,
            description = %s,
            price = %s,
            cost = %s,
            stock = %s,
            status = %s,
            category_id = %s,
            higher_price = %s,
            updated_at = NOW()
        WHERE id = %s AND company_id = %s
    """

    MYSQL_PRODUCTS_UPDATE_STATUS = """
        UPDATE products
        SET status = %s,
            updated_at = NOW()
        WHERE company_id = %s
          AND code = %s
    """

    MYSQL_PRODUCTS_DELETE = """
        DELETE FROM products
        WHERE id = %s AND company_id = %s
    """

    MYSQL_PRODUCTS_ALL_BY_COMPANY = """
        SELECT id, code, name, description, price, cost, stock, status
        FROM products
        WHERE company_id = %s
        ORDER BY code
    """

    # Customers
    MYSQL_CUSTOMERS_GET_BY_DOCUMENT = """
        SELECT id, document_number, name, email, address, phone, contact
        FROM customers
        WHERE company_id = %s AND document_number = %s
    """

    MYSQL_CUSTOMERS_INSERT = """
        INSERT INTO customers (
            company_id, document_number, name, email,
            address, phone, contact, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            email = VALUES(email),
            address = VALUES(address),
            phone = VALUES(phone),
            contact = VALUES(contact),
            updated_at = NOW()
        )
    """

    MYSQL_CUSTOMERS_UPDATE = """
        UPDATE customers SET
            name = %s,
            email = %s,
            address = %s,
            phone = %s,
            contact = %s,
            updated_at = NOW()
        WHERE company_id = %s AND document_number = %s
    """

    MYSQL_CUSTOMERS_DELETE = """
        DELETE FROM customers
        WHERE id = %s AND company_id = %s
    """

    # Sellers
    MYSQL_SELLERS_GET_BY_EMAIL = """
        SELECT id, email, name, phone, status
        FROM sellers
        WHERE company_id = %s AND email = %s
    """

    MYSQL_SELLERS_INSERT = """
        INSERT INTO sellers (
            company_id, email, name, phone, status, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, NOW(), NOW()
        )
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            phone = VALUES(phone),
            status = VALUES(status),
            updated_at = NOW()
        )
    """

    MYSQL_SELLERS_UPDATE = """
        UPDATE sellers SET
            name = %s,
            phone = %s,
            status = %s,
            updated_at = NOW()
        WHERE company_id = %s AND email = %s
    """

    MYSQL_SELLERS_DELETE = """
        DELETE FROM sellers
        WHERE id = %s AND company_id = %s
    """

    # Categories
    MYSQL_CATEGORIES_GET_BY_NAME = """
        SELECT id, name, description
        FROM categories
        WHERE company_id = %s AND name = %s
    """

    MYSQL_CATEGORIES_INSERT = """
        INSERT INTO categories (
            company_id, name, description, status, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, NOW(), NOW()
        )
        ON DUPLICATE KEY UPDATE
            description = VALUES(description),
            updated_at = NOW()
        )
    """

    MYSQL_CATEGORIES_UPDATE = """
        UPDATE categories SET
            description = %s,
            updated_at = NOW()
        WHERE company_id = %s AND name = %s
    """

    MYSQL_CATEGORIES_DELETE = """
        DELETE FROM categories
        WHERE id = %s AND company_id = %s
    """

    # Company
    MYSQL_COMPANY_GET_BY_RIF_EMAIL = """
        SELECT c.id, c.name, c.email, c.address, c.phone
        FROM companies c
        JOIN acceso a ON c.id = a.company_id
        WHERE a.id_fiscal = %s AND a.correo_electronico = %s
        LIMIT 1
    """

    MYSQL_COMPANY_GET_BY_EMAIL = """
        SELECT id, name, email, address, phone
        FROM companies
        WHERE email = %s
        LIMIT 1
    """

    MYSQL_COMPANY_INSERT = """
        INSERT INTO companies (rif, email, name, address, phone, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """

    MYSQL_COMPANY_UPDATE = """
        UPDATE companies SET
            name = %s,
            address = %s,
            phone = %s,
            updated_at = NOW()
        WHERE id = %s
    """

    # ==================== SYNC_HASHES ====================

    SYNC_HASHES_CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS sync_hashes (
            id SERIAL PRIMARY KEY,
            company_id VARCHAR(255) DEFAULT NULL,
            table_name VARCHAR(50) NOT NULL,
            record_key VARCHAR(255) NOT NULL,
            record_hash VARCHAR(32) NOT NULL,
            last_sync_data JSONB NULL,
            last_sync_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            deleted_at TIMESTAMP NULL,
            UNIQUE(table_name, record_key, company_id)
        )
    """

    SYNC_HASHES_GET = """
        SELECT record_hash, last_sync_data
        FROM sync_hashes
        WHERE table_name = %s AND record_key = %s AND company_id = %s
    """

    SYNC_HASHES_INSERT = """
        INSERT INTO sync_hashes (table_name, record_key, record_hash, last_sync_data, company_id)
        VALUES (%s, %s, %s, %s, %s)
    """

    SYNC_HASHES_UPDATE = """
        UPDATE sync_hashes
        SET record_hash = %s,
            last_sync_data = %s,
            last_sync_at = NOW()
        WHERE table_name = %s AND record_key = %s AND company_id = %s
    """

    SYNC_HASHES_GET_ALL_BY_TABLE = """
        SELECT record_key, record_hash, last_sync_data
        FROM sync_hashes
        WHERE table_name = %s AND company_id = %s AND deleted_at IS NULL
    """

    SYNC_HASHES_GET_DELETED = """
        SELECT record_key
        FROM sync_hashes
        WHERE table_name = %s
        AND deleted_at IS NOT NULL
        ORDER BY deleted_at DESC
    """

    SYNC_HASHES_DELETE_BY_KEY = """
        DELETE FROM sync_hashes
        WHERE table_name = %s AND record_key = %s AND company_id = %s
    """

    SYNC_HASHES_DELETE_DELETED_MARKS = """
        DELETE FROM sync_hashes
        WHERE table_name = %s AND deleted_at IS NOT NULL
    """

    SYNC_HASHES_DELETE_ALL = """
        DELETE FROM sync_hashes WHERE company_id = %s
    """

    SYNC_HASHES_COUNT_BY_TABLE = """
        SELECT COUNT(*) FROM sync_hashes
        WHERE table_name = %s AND company_id = %s
    """

    # ==================== TRIGGERS ====================

    TRIGGER_ADD_DELETED_AT_COLUMN = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'sync_hashes'
                AND column_name = 'deleted_at'
            ) THEN
                ALTER TABLE sync_hashes ADD COLUMN deleted_at TIMESTAMP NULL;
            END IF;
        END $$
    """

    TRIGGER_PRODUCTS_DELETED = """
        CREATE OR REPLACE FUNCTION trigger_mark_product_deleted()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE sync_hashes
            SET deleted_at = NOW()
            WHERE table_name = 'products'
            AND record_key = OLD.code;

            IF NOT FOUND THEN
                INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                VALUES ('products', OLD.code, md5(OLD.code::text), NOW());
            END IF;

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS tr_products_mark_deleted_sync_hashes ON products;

        CREATE TRIGGER tr_products_mark_deleted_sync_hashes
            AFTER DELETE ON products
            FOR EACH ROW
            EXECUTE FUNCTION trigger_mark_product_deleted();
    """

    TRIGGER_CATEGORIES_DELETED = """
        CREATE OR REPLACE FUNCTION trigger_mark_category_deleted()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE sync_hashes
            SET deleted_at = NOW()
            WHERE table_name = 'department'
            AND record_key = OLD.code;

            IF NOT FOUND THEN
                INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                VALUES ('department', OLD.code, md5(OLD.code::text), NOW());
            END IF;

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS tr_department_mark_deleted_sync_hashes ON department;

        CREATE TRIGGER tr_department_mark_deleted_sync_hashes
            AFTER DELETE ON department
            FOR EACH ROW
            EXECUTE FUNCTION trigger_mark_category_deleted();
    """

    TRIGGER_CUSTOMERS_DELETED = """
        CREATE OR REPLACE FUNCTION trigger_mark_customer_deleted()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE sync_hashes
            SET deleted_at = NOW()
            WHERE table_name = 'clients'
            AND record_key = OLD.code;

            IF NOT FOUND THEN
                INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                VALUES ('clients', OLD.code, md5(OLD.code::text), NOW());
            END IF;

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS tr_clients_mark_deleted_sync_hashes ON clients;

        CREATE TRIGGER tr_clients_mark_deleted_sync_hashes
            AFTER DELETE ON clients
            FOR EACH ROW
            EXECUTE FUNCTION trigger_mark_customer_deleted();
    """

    TRIGGER_SELLERS_DELETED = """
        CREATE OR REPLACE FUNCTION trigger_mark_seller_deleted()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE sync_hashes
            SET deleted_at = NOW()
            WHERE table_name = 'sellers'
            AND record_key = OLD.email;

            IF NOT FOUND THEN
                INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                VALUES ('sellers', OLD.email, md5(OLD.email::text), NOW());
            END IF;

            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS tr_sellers_mark_deleted_sync_hashes ON sellers;

        CREATE TRIGGER tr_sellers_mark_deleted_sync_hashes
            AFTER DELETE ON sellers
            FOR EACH ROW
            EXECUTE FUNCTION trigger_mark_seller_deleted();
    """
