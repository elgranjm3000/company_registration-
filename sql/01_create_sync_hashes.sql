-- ====================================================================
-- SCRIPT: Crear tabla sync_hashes para detección de cambios
-- AUTOR: Sistema de Sincronización PostgreSQL → MySQL
-- FECHA: 2025-01-22
-- DESCRIPCIÓN: Crea tabla para almacenar hashes MD5 de registros
--              sincronizados, permitiendo detectar cambios
-- ====================================================================

-- Eliminar tabla si existe (opcional, comentar en producción)
-- DROP TABLE IF EXISTS sync_hashes CASCADE;

-- Crear tabla principal
CREATE TABLE IF NOT EXISTS sync_hashes (
    -- Clave primaria
    id SERIAL PRIMARY KEY,

    -- Identificación del registro
    table_name VARCHAR(50) NOT NULL,        -- Nombre de tabla: 'products', 'customers', etc.
    record_key VARCHAR(100) NOT NULL,       -- Clave única: 'code', 'document_number', etc.
    record_hash VARCHAR(32) NOT NULL,       -- Hash MD5 para detectar cambios

    -- Datos adicionales (opcional)
    last_sync_data JSONB,                   -- Datos completos del registro en JSON

    -- Metadatos
    synced_at TIMESTAMP DEFAULT NOW(),      -- Primera sincronización
    updated_at TIMESTAMP DEFAULT NOW(),     -- Última actualización
    company_id INTEGER,                     -- ID de compañía (multi-tenant)

    -- Restricción de unicidad: un hash por registro/tabla/company
    UNIQUE(table_name, record_key, company_id)
);

-- Crear índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_sync_hashes_lookup
    ON sync_hashes(table_name, record_key, company_id);

CREATE INDEX IF NOT EXISTS idx_sync_hashes_table
    ON sync_hashes(table_name, company_id);

CREATE INDEX IF NOT EXISTS idx_sync_hashes_updated
    ON sync_hashes(updated_at DESC);

-- Comentarios de tabla y columnas
COMMENT ON TABLE sync_hashes IS
'Almacena hashes MD5 de registros sincronizados para detectar cambios PostgreSQL → MySQL';

COMMENT ON COLUMN sync_hashes.id IS
'Identificador único autoincremental';

COMMENT ON COLUMN sync_hashes.table_name IS
'Nombre de la tabla en PostgreSQL (products, customers, sellers, categories)';

COMMENT ON COLUMN sync_hashes.record_key IS
'Clave única del registro (code, document_number, etc.)';

COMMENT ON COLUMN sync_hashes.record_hash IS
'Hash MD5 de los campos clave del registro para detectar cambios';

COMMENT ON COLUMN sync_hashes.last_sync_data IS
'Datos completos del registro en formato JSON (opcional, para auditoría)';

COMMENT ON COLUMN sync_hashes.synced_at IS
'Timestamp de primera sincronización del registro';

COMMENT ON COLUMN sync_hashes.updated_at IS
'Timestamp de última actualización del hash';

COMMENT ON COLUMN sync_hashes.company_id IS
'ID de compañía para soporte multi-tenant';

-- ====================================================================
-- FIN DEL SCRIPT
-- ====================================================================

-- Verificación
SELECT
    'Tabla sync_hashes creada exitosamente' as status,
    COUNT(*) as column_count
FROM information_schema.columns
WHERE table_name = 'sync_hashes';
