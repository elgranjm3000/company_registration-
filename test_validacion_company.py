#!/usr/bin/env python3
"""
TEST MANUAL DE VALIDACIÓN DE COMPAÑÍA
======================================
Prueba la lógica de validación de compañía sin ejecutar la sincronización completa

Flujo de validación:
1. Verificar tabla 'acceso' (MySQL) - RIF + email deben coincidir
2. Verificar tabla 'company' (PostgreSQL) - email debe existir
3. Verificar tabla 'companies' (MySQL) - si no existe, se creará

Uso:
    python test_validacion_company.py
"""

import sys
import pymysql
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Configuración PostgreSQL
postgresql_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_DATABASE', 'dataaa'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'muentes123.')
}

# Configuración MySQL (desde sync_config.json)
mysql_config = {
    'host': '91.238.160.176',
    'port': 3306,
    'database': 'chrystal_movil',
    'user': 'chrystal_app',
    'password': 'muentes123.',
    'charset': 'utf8mb4'
}

# RIF y email de prueba (desde sync_config.json)
company_rif = 'J502741284'
company_email = 'multiserviciosleblanc2@gmail.com'
company_name = 'ss'

def print_separator(title=""):
    """Imprime un separador visual"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


print("=" * 70)
print("🧪 TEST DE VALIDACIÓN DE COMPAÑÍA")
print("=" * 70)
print(f"📋 RIF: {company_rif}")
print(f"📧 Email: {company_email}")
print()

pg_conn = None
mysql_conn = None

try:
    # Conectar a PostgreSQL
    print("🔌 Conectando a PostgreSQL...")
    pg_conn = psycopg2.connect(**postgresql_config)
    pg_cursor = pg_conn.cursor()
    print("✅ Conectado a PostgreSQL\n")

    # Conectar a MySQL
    print("🔌 Conectando a MySQL...")
    mysql_conn = pymysql.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor()
    print("✅ Conectado a MySQL\n")

    # ============================================================================
    # PASO 1: Verificar tabla 'acceso' (MySQL)
    # ============================================================================
    print_separator("PASO 1: Verificar tabla 'acceso' (MySQL)")
    print(f"🔍 Buscando: RIF='{company_rif}', Email='{company_email}'")

    query_acceso = """
    SELECT id_fiscal, correo_electronico
    FROM acceso
    WHERE id_fiscal = %s AND correo_electronico = %s
    LIMIT 1
    """

    mysql_cursor.execute(query_acceso, (company_rif, company_email))
    acceso = mysql_cursor.fetchone()

    if not acceso:
        print("❌ PASO 1 FALLÓ: Empresa NO encontrada en 'acceso'")
        print(f"   RIF: {company_rif}")
        print(f"   Email: {company_email}")
        print()
        print("💡 La empresa debe estar registrada primero en la tabla 'acceso'")
        print("💡 Verifica que el RIF y email sean correctos")
        print_separator("RESULTADO FINAL")
        print("❌ VALIDACIÓN FALLÓ EN PASO 1")
        print("   La empresa NO puede ser registrada en 'companies'")
        print_separator()
        sys.exit(1)

    print("✅ PASO 1 EXITOSO: Empresa encontrada en 'acceso'")
    print(f"   RIF: {acceso[0]}")
    print(f"   Email: {acceso[1]}")

    # ============================================================================
    # PASO 2: Verificar tabla 'company' (PostgreSQL)
    # ============================================================================
    print_separator("PASO 2: Verificar tabla 'company' (PostgreSQL)")
    print(f"🔍 Buscando: Email='{company_email}'")

    query_pg_company = """
    SELECT c.id, c.email, c.address, c.phone
    FROM company c
    WHERE LOWER(c.email) = LOWER(%s)
    LIMIT 1
    """

    pg_cursor.execute(query_pg_company, (company_email,))
    pg_company = pg_cursor.fetchone()

    if not pg_company:
        print("❌ PASO 2 FALLÓ: Empresa NO encontrada en 'company' de PostgreSQL")
        print(f"   Email: {company_email}")
        print()
        print("💡 La empresa debe estar registrada en la tabla 'company' de PostgreSQL")
        print("💡 Verifica que el email sea correcto")
        print_separator("RESULTADO FINAL")
        print("❌ VALIDACIÓN FALLÓ EN PASO 2")
        print("   La empresa NO puede ser registrada en 'companies'")
        print_separator()
        sys.exit(1)

    print("✅ PASO 2 EXITOSO: Empresa encontrada en 'company' de PostgreSQL")
    print(f"   ID: {pg_company[0]}")
    print(f"   Email: {pg_company[1]}")
    print(f"   Address: {pg_company[2]}")
    print(f"   Phone: {pg_company[3]}")

    # Guardar datos de PostgreSQL
    pg_company_data = {
        'id': pg_company[0],
        'email': pg_company[1],
        'address': pg_company[2],
        'phone': pg_company[3]
    }

    # ============================================================================
    # PASO 3: Verificar tabla 'companies' (MySQL)
    # ============================================================================
    print_separator("PASO 3: Verificar tabla 'companies' (MySQL)")
    print(f"🔍 Buscando: RIF='{company_rif}'")

    query_companies = """
    SELECT id, name, rif, email, address, phone, status
    FROM companies
    WHERE rif = %s
    LIMIT 1
    """

    mysql_cursor.execute(query_companies, (company_rif,))
    company = mysql_cursor.fetchone()

    if company:
        print("✅ Empresa ya existe en 'companies'")
        print(f"   ID: {company[0]}")
        print(f"   Name: {company[1]}")
        print(f"   RIF: {company[2]}")
        print(f"   Email: {company[3]}")
        print(f"   Status: {company[6]}")
        company_id = company[0]
    else:
        print("⚠️ Empresa NO existe en 'companies'")
        print("   💡 Se creará automáticamente porque pasaron los pasos 1 y 2")
        print()
        print("   📋 Datos que se usarían para crear:")
        print(f"   RIF: {company_rif}")
        print(f"   Email: {company_email.lower()}")
        print(f"   Address: {pg_company_data['address']}")
        print(f"   Phone: {pg_company_data['phone']}")
        print(f"   Name: {company_name}")
        print()

        # Crear empresa (opcional - comentado para solo simular)
        # print("💾 Creando empresa en 'companies'...")
        # insert_query = """
        # INSERT INTO companies (
        #     address, phone, rif, email, name,
        #     key_system_items_id, status, created_at, updated_at
        # ) VALUES (
        #     %s, %s, %s, %s, %s, 1, 'active', NOW(), NOW()
        # )
        # """
        # mysql_cursor.execute(insert_query, (
        #     pg_company_data['address'],
        #     pg_company_data['phone'],
        #     company_rif,
        #     company_email.lower(),
        #     company_name
        # ))
        # mysql_conn.commit()
        # company_id = mysql_cursor.lastrowid
        # print(f"✅ Nueva empresa creada con ID: {company_id}")
        company_id = "NO CREADO (modo simulación)"

    # ============================================================================
    # RESULTADO FINAL
    # ============================================================================
    print_separator("RESULTADO FINAL")
    print("✅ VALIDACIÓN EXITOSA")
    print(f"   ✅ Paso 1: Existe en 'acceso' (MySQL)")
    print(f"   ✅ Paso 2: Existe en 'company' (PostgreSQL)")
    if isinstance(company_id, int):
        print(f"   ✅ Paso 3: Ya existe en 'companies' (ID: {company_id})")
    else:
        print(f"   ✅ Paso 3: Se crearía en 'companies' automáticamente")
    print()
    print("🎉 La empresa PUEDE ser sincronizada correctamente")
    print_separator()

    # Cerrar conexiones
    pg_cursor.close()
    mysql_cursor.close()

except psycopg2.Error as e:
    print(f"\n❌ Error PostgreSQL: {e}")
    sys.exit(1)
except pymysql.Error as e:
    print(f"\n❌ Error MySQL: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    sys.exit(1)
finally:
    if pg_conn:
        pg_conn.close()
    if mysql_conn:
        mysql_conn.close()
