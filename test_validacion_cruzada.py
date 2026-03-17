#!/usr/bin/env python3
"""
Test para validar el nuevo flujo de validación cruzada:
1. acceso (MySQL): RIF y email coincidentes
2. company (PostgreSQL): email existe
3. Si ambas OK → crear en companies (MySQL)
"""

import sys
import pymysql
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Configuración PostgreSQL
postgresql_config = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_DATABASE'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

# Configuración MySQL
mysql_config = {
    'host': os.getenv('DB_HOST_MYSQL'),
    'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
    'user': os.getenv('DB_USER_MYSQL'),
    'password': os.getenv('DB_PASSWORD_MYSQL')
}

# RIF y email del .env
company_rif = os.getenv('RIF')
company_email = os.getenv('EMAIL')
company_name = os.getenv('COMPANY_NOMBRE')

print("=" * 70)
print("🧪 TEST: Validación Cruzada de Company")
print("=" * 70)
print(f"📋 RIF: {company_rif}")
print(f"📧 Email: {company_email}")
print(f"🏢 Nombre: {company_name}")
print()

try:
    # Conectar a MySQL
    print("🔌 Conectando a MySQL...")
    mysql_conn = pymysql.connect(
        host=mysql_config['host'],
        database=mysql_config['database'],
        user=mysql_config['user'],
        password=mysql_config['password'],
        cursorclass=pymysql.cursors.DictCursor
    )
    mysql_cursor = mysql_conn.cursor()
    print("✅ Conexión a MySQL exitosa\n")

    # Conectar a PostgreSQL
    print("🔌 Conectando a PostgreSQL...")
    pg_conn = psycopg2.connect(**postgresql_config)
    pg_cursor = pg_conn.cursor()
    print("✅ Conexión a PostgreSQL exitosa\n")

    # PASO 1: Verificar en acceso (MySQL)
    print("=" * 70)
    print("📌 PASO 1: Verificar en 'acceso' (MySQL)")
    print("=" * 70)
    print("🔍 Consulta: RIF y email coincidentes")

    query_acceso = """
    SELECT id_fiscal, correo_electronico
    FROM acceso
    WHERE id_fiscal = %s AND correo_electronico = %s
    LIMIT 1
    """

    mysql_cursor.execute(query_acceso, (company_rif, company_email))
    acceso = mysql_cursor.fetchone()

    if not acceso:
        print("❌ ERROR: No se encontraron datos coincidentes en 'acceso'")
        print(f"   RIF: {company_rif}")
        print(f"   Email: {company_email}")
        print()
        print("💡 La empresa debe estar en 'acceso' con RIF y email coincidentes")
        sys.exit(1)

    print("✅ Empresa encontrada en 'acceso'")
    print(f"   id_fiscal: {acceso['id_fiscal']}")
    print(f"   correo: {acceso['correo_electronico']}")
    print()

    # PASO 2: Verificar en company (PostgreSQL)
    print("=" * 70)
    print("📌 PASO 2: Verificar en 'company' (PostgreSQL)")
    print("=" * 70)
    print("🔍 Consulta: por email")

    query_pg = """
    SELECT c.id, c.email, c.address, c.phone, c.description
    FROM company c
    WHERE LOWER(c.email) = LOWER(%s)
    LIMIT 1
    """

    pg_cursor.execute(query_pg, (company_email,))
    pg_company = pg_cursor.fetchone()

    if not pg_company:
        print("❌ ERROR: No se encontraron datos en 'company' de PostgreSQL")
        print(f"   Email: {company_email}")
        print()
        print("💡 La empresa debe estar en la tabla 'company' de PostgreSQL")
        sys.exit(1)

    print("✅ Empresa encontrada en 'company'")
    print(f"   ID: {pg_company[0]}")
    print(f"   Email: {pg_company[1]}")
    print()

    # PASO 3: Buscar en companies (MySQL)
    print("=" * 70)
    print("📌 PASO 3: Buscar en 'companies' (MySQL)")
    print("=" * 70)

    query_companies = """
    SELECT id, name, rif, email
    FROM companies
    WHERE rif = %s
    LIMIT 1
    """

    mysql_cursor.execute(query_companies, (company_rif,))
    company = mysql_cursor.fetchone()

    if company:
        print("✅ Empresa encontrada en 'companies'")
        print(f"   ID: {company['id']}")
        print(f"   Name: {company['name']}")
        print(f"   RIF: {company['rif']}")
        print(f"   Email: {company['email']}")
        company_id = company['id']
        accion = "Usar existente"
    else:
        print("⚠️ Empresa NO encontrada en 'companies'")
        print("💡 Creando nueva empresa...")

        # Crear en companies
        insert_query = """
        INSERT INTO companies (
            address, phone, rif, email, name,
            key_system_items_id, status, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, 1, 'active', NOW(), NOW()
        )
        """

        mysql_cursor.execute(insert_query, (
            pg_company[2],  # address de PostgreSQL
            pg_company[3],  # phone de PostgreSQL
            company_rif,
            company_email.lower(),
            company_name
        ))

        mysql_conn.commit()
        company_id = mysql_cursor.lastrowid

        print("✅ Empresa creada exitosamente")
        print(f"   ID: {company_id}")
        print(f"   Nombre: {company_name}")
        accion = "Crear nueva"

    # RESUMEN
    print()
    print("=" * 70)
    print("🎉 VALIDACIÓN CRUZADA COMPLETADA CON ÉXITO")
    print("=" * 70)
    print()
    print("✅ PASO 1: Validación en 'acceso' (MySQL)")
    print("   ✅ RIF y email coincidentes")
    print()
    print("✅ PASO 2: Validación en 'company' (PostgreSQL)")
    print("   ✅ Email encontrado")
    print()
    print("✅ PASO 3: Sincronización con 'companies' (MySQL)")
    print(f"   ✅ {accion} (ID: {company_id})")
    print()
    print("=" * 70)
    print("📋 Resumen de validaciones:")
    print("=" * 70)
    print(f"   acceso (MySQL):            ✅ {acceso['id_fiscal']}")
    print(f"   company (PostgreSQL):      ✅ {pg_company[0]}")
    print(f"   companies (MySQL):         ✅ {company_id}")
    print()

    # Cerrar conexiones
    mysql_cursor.close()
    mysql_conn.close()
    pg_cursor.close()
    pg_conn.close()

except Exception as e:
    print()
    print("=" * 70)
    print(f"❌ ERROR: {type(e).__name__}")
    print(f"   {str(e)}")
    print("=" * 70)
    import traceback
    traceback.print_exc()
    sys.exit(1)
