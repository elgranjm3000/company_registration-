#!/usr/bin/env python3
"""
Script de prueba para Products Sync
Valida la sincronización de productos de PostgreSQL a API REST
"""

import sys
import os
import logging
import json
from datetime import datetime

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar psycopg2
try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 no está instalado")
    print("Ejecute: pip install psycopg2-binary")
    sys.exit(1)

# Importar nuestros módulos
from api_client.products import ProductsClient
from sync.products_sync import ProductsSync


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_products_sync.log')
    ]
)

logger = logging.getLogger(__name__)


def load_config():
    """Cargar configuración desde sync_config.json"""
    config_file = 'sync_config.json'

    if not os.path.exists(config_file):
        logger.error(f"Config file not found: {config_file}")
        logger.info("Create a sync_config.json with your database credentials")
        return None

    with open(config_file, 'r') as f:
        config = json.load(f)

    return config


def connect_postgresql(config):
    """Conectar a PostgreSQL"""
    try:
        pg_config = {
            'host': config.get('postgres_host', 'localhost'),
            'port': config.get('postgres_port', 5432),
            'database': config.get('postgres_database'),
            'user': config.get('postgres_user', 'postgres'),
            'password': config.get('postgres_password')
        }

        conn = psycopg2.connect(**pg_config)
        logger.info("✅ Connected to PostgreSQL")
        return conn

    except Exception as e:
        logger.error(f"❌ Error connecting to PostgreSQL: {e}")
        return None


def test_products_sync():
    """Probar sincronización de productos"""

    logger.info("=" * 70)
    logger.info("TEST: Products Sync (PostgreSQL → API REST)")
    logger.info("=" * 70)

    # 1. Cargar configuración
    logger.info("\n📋 Step 1: Loading configuration...")
    config = load_config()

    if not config:
        return False

    # Verificar que hay api_config
    api_config = config.get('api_config')
    if not api_config:
        logger.error("❌ api_config not found in sync_config.json")
        logger.info("Add api_config section to sync_config.json")
        return False

    # 2. Conectar a PostgreSQL
    logger.info("\n🔌 Step 2: Connecting to PostgreSQL...")
    pg_conn = connect_postgresql(config)

    if not pg_conn:
        return False

    # 3. Crear cliente de API
    logger.info("\n🌐 Step 3: Initializing API client...")

    try:
        products_client = ProductsClient(
            base_url=api_config['base_url'],
            api_key=api_config['api_key']
        )
        logger.info("✅ Products API client initialized")
    except Exception as e:
        logger.error(f"❌ Error initializing API client: {e}")
        pg_conn.close()
        return False

    # 4. Obtener company_id
    logger.info("\n🏢 Step 4: Getting company_id...")

    company_rif = config.get('company_rif')
    company_email = config.get('company_email')

    if not company_rif or not company_email:
        logger.error("❌ company_rif and company_email required in config")
        pg_conn.close()
        return False

    # Usar company_id del config
    company_id = config.get('company_id')

    if not company_id:
        logger.warning("⚠️  company_id not found in config, using default: 27")
        company_id = 27

    logger.info(f"Using company_id: {company_id}")

    # 5. Ejecutar sincronización
    logger.info("\n🔄 Step 5: Executing products sync...")

    try:
        products_sync = ProductsSync(
            pg_conn=pg_conn,
            api_client=products_client,
            company_id=company_id,
            logger=logger
        )

        success = products_sync.execute()

        if success:
            logger.info("\n" + "=" * 70)
            logger.info("✅ TEST PASSED: Products sync completed successfully")
            logger.info("=" * 70)

            # Mostrar estadísticas
            stats = products_sync.stats
            logger.info(f"📊 Results:")
            logger.info(f"   Created: {stats['created']}")
            logger.info(f"   Updated: {stats['updated']}")
            logger.info(f"   Deleted: {stats['deleted']}")
            logger.info(f"   Errors: {stats['errors']}")

            return True
        else:
            logger.error("\n" + "=" * 70)
            logger.error("❌ TEST FAILED: Products sync had errors")
            logger.error("=" * 70)
            return False

    except Exception as e:
        logger.error(f"\n❌ Exception during sync: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        # Cerrar conexión
        pg_conn.close()
        logger.info("\n🔌 PostgreSQL connection closed")


def test_api_directly():
    """Prueba simple del cliente API sin PostgreSQL"""

    logger.info("=" * 70)
    logger.info("TEST: API Client (Direct)")
    logger.info("=" * 70)

    config = load_config()
    if not config:
        return False

    api_config = config.get('api_config')
    if not api_config:
        logger.error("❌ api_config not found")
        return False

    try:
        # Crear cliente
        client = ProductsClient(
            base_url=api_config['base_url'],
            api_key=api_config['api_key']
        )

        # Probar obtener productos
        logger.info("\n📡 Testing GET /products...")

        company_id = config.get('company_id', 27)

        products = list(client.get_all(company_id=company_id))

        logger.info(f"✅ Retrieved {len(products)} products")

        for prod in products[:5]:  # Mostrar primeros 5
            logger.info(f"   - {prod['code']}: {prod['name']} (${prod['price']})")

        # Probar obtener mapa de categorías
        logger.info("\n📂 Testing categories map...")

        categories_map = client.get_categories_map(company_id=company_id)

        logger.info(f"✅ Retrieved {len(categories_map)} categories")

        for name, cat_id in list(categories_map.items())[:5]:
            logger.info(f"   - {name}: ID {cat_id}")

        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_sync_with_pending():
    """Marcar algunos productos como pending_sync y probar sincronización"""

    logger.info("=" * 70)
    logger.info("TEST: Products Sync with pending_sync")
    logger.info("=" * 70)

    config = load_config()
    if not config:
        return False

    # Conectar a PostgreSQL
    pg_conn = connect_postgresql(config)
    if not pg_conn:
        return False

    try:
        # Marcar algunos productos como pending_sync
        logger.info("\n📝 Marking some products as pending_sync...")

        company_id = config.get('company_id', 27)

        pg_cursor = pg_conn.cursor()

        # Marcar primeros 10 productos como pending
        pg_cursor.execute("""
            INSERT INTO sync_hashes (table_name, record_key, record_hash, company_id, pending_sync, updated_at)
            SELECT 'products', code, MD5(code::text), %s, TRUE, NOW()
            FROM products
            WHERE code IS NOT NULL
            LIMIT 10
            ON CONFLICT (table_name, record_key, company_id)
            DO UPDATE SET pending_sync = TRUE, updated_at = NOW()
        """, (company_id,))

        pg_conn.commit()

        logger.info("✅ Marked 10 products as pending_sync")

        # Ahora ejecutar sincronización
        logger.info("\n🔄 Running sync...")

        api_config = config.get('api_config')
        products_client = ProductsClient(
            base_url=api_config['base_url'],
            api_key=api_config['api_key']
        )

        products_sync = ProductsSync(
            pg_conn=pg_conn,
            api_client=products_client,
            company_id=company_id,
            logger=logger
        )

        success = products_sync.execute()

        if success:
            logger.info("\n✅ TEST PASSED")
        else:
            logger.error("\n❌ TEST FAILED")

        return success

    except Exception as e:
        logger.error(f"❌ Exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

    finally:
        pg_conn.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Test Products Sync')
    parser.add_argument(
        '--mode',
        choices=['full', 'api-only', 'pending'],
        default='full',
        help='Test mode: full (with PostgreSQL), api-only (API client only), or pending (mark pending and sync)'
    )

    args = parser.parse_args()

    if args.mode == 'full':
        success = test_products_sync()
    elif args.mode == 'api-only':
        success = test_api_directly()
    elif args.mode == 'pending':
        success = test_sync_with_pending()
    else:
        success = False

    sys.exit(0 if success else 1)
