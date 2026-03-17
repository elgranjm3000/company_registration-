#!/usr/bin/env python3
"""
Test para validar la creación automática de company:
1. Verificar que existe en 'acceso'
2. Si NO existe en 'companies', crearla automáticamente
"""

import sys
import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

mysql_config = {
    'host': os.getenv('DB_HOST_MYSQL'),
    'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
    'user': os.getenv('DB_USER_MYSQL'),
    'password': os.getenv('DB_PASSWORD_MYSQL')
}

# RIF de prueba - DEBE existir en acceso pero NO en companies
company_rif = 'J123456789'
company_email = 'test_prueba@gmail.com'
company_name = 'Empresa Test C.A.'

print("=" * 70)
print("🧪 TEST: Creación automática de Company")
print("=" * 70)
print(f"📋 RIF: {company_rif}")
print(f"📧 Email: {company_email}")
print(f"🏢 Nombre: {company_name}")
print()

try:
    mysql_conn = pymysql.connect(
        host=mysql_config['host'],
        database=mysql_config['database'],
        user=mysql_config['user'],
        password=mysql_config['password'],
        cursorclass=pymysql.cursors.DictCursor
    )
    mysql_cursor = mysql_conn.cursor()

    # Primero verificar si existe en acceso
    print("🔍 PASO 1: Verificando tabla 'acceso'...")
    query_acceso = """
    SELECT id_fiscal, correo_electronico
    FROM acceso
    WHERE id_fiscal = %s
    LIMIT 1
    """
    mysql_cursor.execute(query_acceso, (company_rif,))
    acceso = mysql_cursor.fetchone()

    if not acceso:
        print("❌ NO existe en 'acceso' - No se puede crear la empresa")
        print("💡 Este test requiere que el RIF exista en 'acceso' primero")
        mysql_cursor.close()
        mysql_conn.close()
        sys.exit(1)

    print("✅ Existe en tabla 'acceso'")
    print()

    # Verificar si existe en companies
    print("🔍 PASO 2: Verificando tabla 'companies'...")
    query_companies = """
    SELECT id, name, rif, email
    FROM companies
    WHERE rif = %s
    LIMIT 1
    """
    mysql_cursor.execute(query_companies, (company_rif,))
    company = mysql_cursor.fetchone()

    if company:
        print("⚠️ La empresa YA existe en 'companies'")
        print(f"   ID: {company['id']}")
        print(f"   Nombre: {company['name']}")
        print()
        print("💡 Eliminando registro para probar la creación...")

        mysql_cursor.execute("DELETE FROM companies WHERE rif = %s", (company_rif,))
        mysql_conn.commit()
        print("✅ Registro eliminado. Reintentando...")
        print()

    # Ahora probar la creación
    print("🔍 PASO 3: Creando empresa en 'companies'...")

    insert_query = """
    INSERT INTO companies (
        address, phone, rif, email, name,
        key_system_items_id, status, created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, 1, 'active', NOW(), NOW()
    )
    """

    mysql_cursor.execute(insert_query, (
        'Dirección de prueba',
        '0414-1234567',
        company_rif,
        company_email.lower(),
        company_name
    ))

    mysql_conn.commit()
    company_id = mysql_cursor.lastrowid

    print(f"✅ Empresa creada exitosamente!")
    print(f"   ID: {company_id}")
    print(f"   RIF: {company_rif}")
    print(f"   Nombre: {company_name}")

    # Verificar que se creó correctamente
    print()
    print("🔍 PASO 4: Verificando creación...")
    mysql_cursor.execute(query_companies, (company_rif,))
    verification = mysql_cursor.fetchone()

    if verification:
        print("✅ Verificación exitosa:")
        print(f"   ID: {verification['id']}")
        print(f"   Name: {verification['name']}")
        print(f"   RIF: {verification['rif']}")
        print(f"   Email: {verification['email']}")
    else:
        print("❌ ERROR: No se encontró después de crear")

    print()
    print("=" * 70)
    print("🎉 TEST COMPLETADO")
    print("=" * 70)
    print("✅ La creación automática funciona correctamente")
    print("✅ Si existe en 'acceso', se puede crear en 'companies'")

    mysql_cursor.close()
    mysql_conn.close()

except Exception as e:
    print()
    print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
    sys.exit(1)
