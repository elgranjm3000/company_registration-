-- ============================================================================
-- TEST MANUAL DE VALIDACIÓN DE COMPAÑÍA
-- ============================================================================
-- Ejecutar estos pasos para verificar manualmente si la validación funciona
-- ============================================================================

-- ============================================================================
-- PASO 1: Verificar si existe en tabla 'acceso' (MySQL)
-- ============================================================================
-- Debe coincidir AMBOS: id_fiscal (RIF) Y correo_electronico

SELECT id_fiscal, correo_electronico
FROM acceso
WHERE id_fiscal = 'J502741284'
  AND correo_electronico = 'multiserviciosleblanc2@gmail.com';

-- Esperado: ✅ 1 fila (RIF y email coinciden)
-- Si devuelve 0 filas: ❌ La empresa NO está registrada en acceso


-- ============================================================================
-- PASO 2: Verificar si existe en tabla 'company' (PostgreSQL)
-- ============================================================================
-- Busca por email (case-insensitive)

SELECT id, email, address, phone
FROM company
WHERE LOWER(email) = LOWER('multiserviciosleblanc2@gmail.com');

-- Esperado: ✅ 1 fila (email coincide)
-- Si devuelve 0 filas: ❌ La empresa NO está registrada en company (PostgreSQL)


-- ============================================================================
-- PASO 3: Verificar si existe en tabla 'companies' (MySQL)
-- ============================================================================
-- Busca por RIF

SELECT id, name, rif, email, address, phone, status
FROM companies
WHERE rif = 'J502741284';

-- Esperado:
--   ✅ 1 fila = La empresa ya está registrada
--   ⚠️ 0 filas = La empresa NO está registrada (se creará automáticamente)


-- ============================================================================
-- SIMULAR ERROR - Cambiar RIF para que falle en 'acceso'
-- ============================================================================
SELECT id_fiscal, correo_electronico
FROM acceso
WHERE id_fiscal = 'J000000000'
  AND correo_electronico = 'multiserviciosleblanc2@gmail.com';
-- Esperado: ❌ 0 filas (RIF incorrecto)


-- ============================================================================
-- SIMULAR ERROR - Cambiar email para que falle en 'company'
-- ============================================================================
SELECT id, email, address, phone
FROM company
WHERE LOWER(email) = LOWER('email_inexistente@gmail.com');
-- Esperado: ❌ 0 filas (email no existe)
