"""
SCRIPT DE PRUEBA: Sincronización Inteligente
Ejecuta una sincronización completa de prueba
"""

from dotenv import load_dotenv
from smart_sync_complete import ServiceApp, SmartSyncComplete
import os
import mysql.connector
import psycopg2

print("=" * 70)
print(" PRUEBA DE SINCRONIZACIÓN INTELIGENTE")
print("=" * 70)

# Cargar configuración
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

print("\n[1/6] Verificando conexiones...")

# Probar PostgreSQL
try:
    pg_conn = psycopg2.connect(**postgresql_config)
    pg_cursor = pg_conn.cursor()
    pg_cursor.execute("SELECT version()")
    version = pg_cursor.fetchone()[0]
    print(f"✅ PostgreSQL conectado: {version[:50]}...")
    pg_cursor.close()
    pg_conn.close()
except Exception as e:
    print(f"❌ Error PostgreSQL: {str(e)}")
    exit(1)

# Probar MySQL
try:
    mysql_conn = mysql.connector.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor()
    mysql_cursor.execute("SELECT DATABASE()")
    db = mysql_cursor.fetchone()[0]
    print(f"✅ MySQL conectado: Base de datos '{db}'")
    mysql_cursor.close()
    mysql_conn.close()
except Exception as e:
    print(f"❌ Error MySQL: {str(e)}")
    exit(1)

print("\n[2/6] Obteniendo company_id...")

# Obtener company_id desde tabla companies
try:
    mysql_conn = mysql.connector.connect(**mysql_config)
    mysql_cursor = mysql_conn.cursor()

    rif = os.getenv('RIF')
    email = os.getenv('EMAIL')

    mysql_cursor.execute(
        "SELECT id, name FROM companies WHERE rif = %s AND email = %s",
        (rif, email.lower())
    )
    result = mysql_cursor.fetchone()

    mysql_cursor.close()
    mysql_conn.close()

    if result:
        company_id, company_name = result
        print(f"✅ Company encontrado: {company_name} (ID: {company_id})")
    else:
        print(f"❌ No se encontró company para RIF={rif}, EMAIL={email}")
        print("   Ejecuta primero el sync de companies desde tu app.py")
        exit(1)

except Exception as e:
    print(f"❌ Error obteniendo company_id: {str(e)}")
    exit(1)

print("\n[3/6] Creando app del servicio...")

# Crear app del servicio
app = ServiceApp(postgresql_config, mysql_config, company_id)

print("✅ App creada")

print("\n[4/6] Creando módulo de sincronización...")

# Crear módulo de sincronización
sync = SmartSyncComplete(
    app,
    postgresql_config,
    mysql_config,
    company_id
)

print("✅ Módulo creado")

print("\n[5/6] Inicializando tabla sync_hashes (primera vez)...")

# Inicializar tabla de hashes
if not sync.inicializar_tabla_hashes():
    print("❌ Error inicializando tabla sync_hashes")
    exit(1)

print("✅ Tabla sync_hashes lista")

print("\n[6/6] Ejecutando sincronización completa...")
print("-" * 70)

# Ejecutar sincronización
resultado = sync.ejecutar_sync_completa()

print("-" * 70)

if resultado:
    print("\n✅ SINCRONIZACIÓN COMPLETADA EXITOSAMENTE")
    print("\n📊 Resumen:")
    print(f"   Products:   {sync.stats['products']['nuevos']} nuevos, {sync.stats['products']['modificados']} modificados")
    print(f"   Customers:  {sync.stats['customers']['nuevos']} nuevos, {sync.stats['customers']['modificados']} modificados")
    print(f"   Categories: {sync.stats['categories']['nuevos']} nuevos, {sync.stats['categories']['modificados']} modificados")
    print(f"   Quotes:     {sync.stats['quotes']['nuevos']} nuevos (MySQL→PG)")
    print(f"   Errores:     {sum(s['errores'] for s in sync.stats.values())}")
else:
    print("\n⚠️ SINCRONIZACIÓN COMPLETADA CON ERRORES")
    print("   Revisa el log para más detalles")

print("\n" + "=" * 70)
print(" PRUEBA FINALIZADA")
print("=" * 70)
