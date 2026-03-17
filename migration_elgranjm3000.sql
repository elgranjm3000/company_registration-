-- ============================================================================
-- MIGRACIÓN: Crear empresa elgranjm3000@gmail.com
-- Fecha: 2026-02-13
-- Descripción: Crear registros necesarios para la sincronización de quotes
-- ============================================================================

-- PASO 1: Crear email en tabla emails (referenciada por company.email)
INSERT INTO emails (account, server_email, description)
VALUES ('elgranjm3000@gmail.com', 'gmail.com', 'PRUEBA TEST')
ON CONFLICT (account) DO NOTHING;

-- PASO 2: Crear company en tabla company
INSERT INTO company (id, description, address, phone, email)
VALUES ('81', 'probando', 'Caracas', '04125933379', 'elgranjm3000@gmail.com')
ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    description = EXCLUDED.description,
    address = EXCLUDED.address,
    phone = EXCLUDED.phone;

-- ============================================================================
-- VERIFICACIÓN
-- ============================================================================
-- Verificar que la empresa fue creada correctamente
-- SELECT id, email, description, address, phone FROM company WHERE email = 'elgranjm3000@gmail.com';
