#!/usr/bin/env python3
import psycopg2
import pymysql
import hashlib
from dotenv import load_dotenv
import os

load_dotenv()

def safe_float(value):
    """Convertir valor a float de forma segura"""
    try:
        return float(value) if value is not None else 0.0
    except:
        return 0.0

# Conectar a PostgreSQL
pg_conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_DATABASE'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
pg_cursor = pg_conn.cursor()

# Conectar a MySQL
mysql_conn = pymysql.connect(
    host=os.getenv('DB_HOST_MYSQL'),
    user=os.getenv('DB_USER_MYSQL'),
    password=os.getenv('DB_PASSWORD_MYSQL'),
    database=os.getenv('DB_PORT_DATABASE_MYSQL')
)
mysql_cursor = mysql_conn.cursor()

company_id = 27

print('=' * 80)
print('TEST COMPLETO DE SINCRONIZACIÓN DE SELLERS')
print('=' * 80)
print()

# 1. Verificar estado actual en MySQL
print('1. ESTADO ACTUAL EN MYSQL')
print('-' * 80)

# Ver usuarios sellers
mysql_cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'seller'")
users_count = mysql_cursor.fetchone()[0]
print(f'Usuarios sellers en MySQL.users: {users_count}')

# Ver sellers
mysql_cursor.execute("SELECT COUNT(*) FROM sellers")
sellers_count = mysql_cursor.fetchone()[0]
print(f'Sellers en MySQL.sellers: {sellers_count}')

if users_count > 0:
    mysql_cursor.execute("SELECT id, email, first_name, last_name FROM users WHERE role = 'seller' LIMIT 5")
    users = mysql_cursor.fetchall()
    print(f'\nPrimeros {len(users)} usuarios sellers:')
    for u in users:
        print(f'   ID: {u[0]:5} | Email: {u[1]:30} | Nombre: {u[2]} {u[3]}')

print()

# 2. Obtener sellers de PostgreSQL
print('2. OBTENIENDO SELLERS DE POSTGRESQL')
print('-' * 80)

pg_cursor.execute("""
    SELECT
        s.code as seller_code,
        s.description,
        s.status,
        s.percent_sales,
        s.percent_receivable,
        s.inkeeper,
        s.user_code,
        s.percent_gerencial_debit_note,
        s.percent_gerencial_credit_note,
        s.percent_returned_check,
        u.email,
        u.user_password as password
    FROM sellers s
    LEFT JOIN users u ON s.user_code = u.code
    WHERE s.user_code IS NOT NULL
      AND u.email IS NOT NULL
      AND u.email != ''
      AND u.email != '@'
    ORDER BY s.code
""")

sellers = pg_cursor.fetchall()

if not sellers:
    print('❌ No se encontraron sellers en PostgreSQL')
else:
    print(f'✅ Se encontraron {len(sellers)} sellers en PostgreSQL')

print()

# 3. Analizar qué se haría en la sincronización
print('3. SIMULACIÓN DE SINCRONIZACIÓN')
print('-' * 80)

sellers_nuevos = 0
sellers_modificados = 0
usuarios_a_crear = 0
usuarios_existentes = 0

for seller in sellers:
    (seller_code, description, status, percent_sales,
     percent_receivable, inkeeper, user_code,
     percent_gerencial_debit_note, percent_gerencial_credit_note,
     percent_returned_check, email, password) = seller

    # Buscar si existe usuario en MySQL
    mysql_cursor.execute(
        "SELECT id FROM users WHERE email = %s AND role = 'seller' LIMIT 1",
        (email,)
    )
    user_result = mysql_cursor.fetchone()

    # Buscar si existe seller en MySQL
    mysql_cursor.execute(
        "SELECT id FROM sellers WHERE code = %s LIMIT 1",
        (seller_code,)
    )
    seller_result = mysql_cursor.fetchone()

    # Determinar qué acción se tomaría
    if not user_result:
        usuarios_a_crear += 1
        accion_user = 'CREAR USUARIO'
    else:
        usuarios_existentes += 1
        accion_user = 'USUARIO EXISTE'

    if not seller_result:
        sellers_nuevos += 1
        accion_seller = 'NUEVO SELLER'
    else:
        sellers_modificados += 1
        accion_seller = 'ACTUALIZAR SELLER'

    print(f'   {accion_user:20} | {accion_seller:20} | Seller: {seller_code:10} | Email: {email}')

print()
print('RESUMEN DE ACCIONES')
print('-' * 80)
print(f'Usuarios a crear en MySQL.users:    {usuarios_a_crear}')
print(f'Usuarios ya existentes:             {usuarios_existentes}')
print(f'Sellers nuevos a insertar:          {sellers_nuevos}')
print(f'Sellers a actualizar:               {sellers_modificados}')
print()

# 4. Si hay sellers nuevos, mostrar detalle de inserción
if usuarios_a_crear > 0 or sellers_nuevos > 0:
    print('4. DETALLE DE INSERCIÓN')
    print('-' * 80)

    for seller in sellers:
        (seller_code, description, status, percent_sales,
         percent_receivable, inkeeper, user_code,
         percent_gerencial_debit_note, percent_gerencial_credit_note,
         percent_returned_check, email, password) = seller

        mysql_cursor.execute(
            "SELECT id FROM users WHERE email = %s AND role = 'seller' LIMIT 1",
            (email,)
        )
        user_result = mysql_cursor.fetchone()

        if not user_result:
            # Generar nombre
            nombre_parts = description.split(' ')
            first_name = nombre_parts[0] if nombre_parts else seller_code
            last_name = ' '.join(nombre_parts[1:]) if len(nombre_parts) > 1 else ''

            print(f'\n📝 Usuario a CREAR para seller {seller_code}:')
            print(f'   Email:       {email}')
            print(f'   Password:    {"SÍ (" + str(len(password)) + " chars)" if password else "NO"}')
            print(f'   Role:        seller')
            print(f'   First Name:  {first_name}')
            print(f'   Last Name:   {last_name}')
            print(f'   Status:      active')

            print(f'\n📝 Seller a INSERTAR:')
            print(f'   Code:        {seller_code}')
            print(f'   Description: {description}')
            print(f'   Status:      {status}')
            print(f'   Percent Sales: {percent_sales}%')
            print(f'   User Code:   {user_code}')
            break  # Solo mostrar el primero

print()
print('=' * 80)
print('TEST FINALIZADO')
print('=' * 80)

pg_cursor.close()
pg_conn.close()
mysql_cursor.close()
mysql_conn.close()
