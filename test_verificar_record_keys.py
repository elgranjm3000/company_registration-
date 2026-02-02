#!/usr/bin/env python3
"""
Test para verificar que los record_keys se guardan correctamente
"""

import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("🧪 TEST: Verificar record_keys en system_logs")
print("=" * 80)

conn = pymysql.connect(
    host=os.getenv('DB_HOST_MYSQL'),
    database=os.getenv('DB_PORT_DATABASE_MYSQL'),
    user=os.getenv('DB_USER_MYSQL'),
    password=os.getenv('DB_PASSWORD_MYSQL')
)
cursor = conn.cursor()

# Limpiar logs de prueba
cursor.execute("DELETE FROM system_logs WHERE user_id = 'J316277860'")
conn.commit()

print("\n📌 PASO 1: Verificar tipo de dato de user_id")
print("-" * 80)

cursor.execute("DESCRIBE system_logs")
for row in cursor.fetchall():
    if row[0] == 'user_id':
        print(f"✅ user_id es de tipo: {row[1]}")
        break

print("\n📌 PASO 2: Insertar registro de prueba con RIF")
print("-" * 80)

cursor.execute("""
    INSERT INTO system_logs (user_id, action, record_key, location, lat, lng, created_at)
    VALUES (%s, %s, %s, ST_GeomFromText(%s), %s, %s, NOW())
""", ('J316277860', 'products - CREATE', 'P001', 'POINT(-66.8738 10.4873)', 10.4873, -66.8738))
conn.commit()

print("✅ Insertado: user_id='J316277860', record_key='P001'")

print("\n📌 PASO 3: Verificar registro guardado")
print("-" * 80)

cursor.execute("""
    SELECT id, user_id, action, record_key, ASTEXT(location) as location, created_at
    FROM system_logs
    WHERE user_id = 'J316277860'
    ORDER BY id DESC LIMIT 1
""")

row = cursor.fetchone()
if row:
    log_id, user_id, action, record_key, location, created = row
    print(f"✅ Registro encontrado:")
    print(f"   ID: {log_id}")
    print(f"   user_id: '{user_id}' (tipo: {type(user_id).__name__})")
    print(f"   action: '{action}'")
    print(f"   record_key: '{record_key}'")
    print(f"   location: {location}")
    print(f"   created_at: {created}")
else:
    print("❌ No se encontró el registro")

print("\n📌 PASO 4: Verificar conversión de tipos")
print("-" * 80)

# Probar guardar RIF como string
cursor.execute("""
    INSERT INTO system_logs (user_id, action, record_key, location, lat, lng, created_at)
    VALUES (%s, %s, %s, ST_GeomFromText(%s), %s, %s, NOW())
""", ('J316277860', 'test - UPDATE', 'TEST001', 'POINT(-66.8738 10.4873)', 10.4873, -66.8738))
conn.commit()

cursor.execute("SELECT user_id FROM system_logs WHERE action = 'test - UPDATE' LIMIT 1")
result = cursor.fetchone()

if result:
    user_id_guardado = result[0]
    print(f"✅ user_id guardado: '{user_id_guardado}'")
    if user_id_guardado == 'J316277860':
        print("✅ RIF guardado correctamente")
    else:
        print(f"❌ RIF incorrecto: se guardó '{user_id_guardado}'")

print("\n📌 PASO 5: Verificar todos los registros")
print("-" * 80)

cursor.execute("""
    SELECT id, user_id, action, record_key
    FROM system_logs
    WHERE user_id = 'J316277860'
    ORDER BY id DESC
""")

rows = cursor.fetchall()
print(f"\nRegistros encontrados: {len(rows)}")
for row in rows:
    log_id, user_id, action, record_key = row[:4]
    print(f"  #{log_id}: user_id='{user_id}', action='{action}', record_key='{record_key}'")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("✅ TEST COMPLETADO")
print("=" * 80)
