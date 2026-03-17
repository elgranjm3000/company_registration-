#!/usr/bin/env python3
"""
Script para probar todos los endpoints de la API con datos de PostgreSQL
"""

import psycopg2
import requests
import json
import sys
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================

# API Configuration
API_BASE_URL = "https://chrystal.com.ve/mobile/public/api"
API_EMAIL = "admin@test.com"
API_PASSWORD = "password"

# PostgreSQL Configuration
# Modifica estos valores según tu configuración
PG_HOST = "localhost"
PG_PORT = 5432
PG_DATABASE = "nueva"
PG_USER = "postgres"
PG_PASSWORD = "postgres"  # Cambia esto

# ==========================================
# FUNCIONES
# ==========================================

def log(message, level="INFO"):
    """Imprimir log con colores"""
    colors = {
        'INFO': '\033[94m',      # Azul
        'SUCCESS': '\033[92m',   # Verde
        'WARNING': '\033[93m',   # Amarillo
        'ERROR': '\033[91m',     # Rojo
        'RESET': '\033[0m'
    }
    color = colors.get(level, colors['RESET'])
    print(f"{color}[{level}]{colors['RESET']} {message}")

def connect_postgresql():
    """Conectar a PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD
        )
        log(f"Conectado a PostgreSQL: {PG_DATABASE}@{PG_HOST}:{PG_PORT}", "SUCCESS")
        return conn
    except Exception as e:
        log(f"Error conectando a PostgreSQL: {e}", "ERROR")
        return None

def api_login():
    """Hacer login en la API"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json={
                'email': API_EMAIL,
                'password': API_PASSWORD
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            log(f"Login exitoso. Token: {token[:50]}...", "SUCCESS")
            return token
        else:
            log(f"Login fallido. Status: {response.status_code}", "ERROR")
            log(f"Respuesta: {response.text}", "ERROR")
            return None

    except Exception as e:
        log(f"Error en login: {e}", "ERROR")
        return None

def test_category_endpoint(conn, token):
    """Probar endpoint de categorías"""
    log("\n" + "="*70, "INFO")
    log("PROBANDO ENDPOINT: CATEGORIES", "INFO")
    log("="*70, "INFO")

    try:
        cursor = conn.cursor()

        # Obtener categorías de PostgreSQL
        cursor.execute("""
            SELECT id, name, description
            FROM categories
            WHERE deleted IS NULL OR deleted = 0
            LIMIT 5
        """)

        categories = []
        for row in cursor.fetchall():
            categories.append({
                'id': row[0],
                'name': row[1],
                'description': row[2] or ''
            })

        log(f"Categorías encontradas en PostgreSQL: {len(categories)}", "INFO")

        if not categories:
            log("No hay categorías para probar", "WARNING")
            return

        # Preparar payload
        payload = {'categories': categories}
        log(f"Payload: {json.dumps(payload, indent=2)}", "INFO")

        # Enviar a API
        response = requests.post(
            f"{API_BASE_URL}/sync-batch/categories",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json=payload,
            timeout=30
        )

        log(f"Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            result = response.json()
            log("✅ Endpoint funcionando correctamente", "SUCCESS")
            log(f"Respuesta: {json.dumps(result, indent=2)}", "INFO")
            return True
        else:
            log(f"❌ Error en endpoint", "ERROR")
            log(f"Respuesta: {response.text}", "ERROR")
            return False

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return False

def test_product_endpoint(conn, token):
    """Probar endpoint de productos"""
    log("\n" + "="*70, "INFO")
    log("PROBANDO ENDPOINT: PRODUCTS", "INFO")
    log("="*70, "INFO")

    try:
        cursor = conn.cursor()

        # Obtener productos de PostgreSQL
        cursor.execute("""
            SELECT p.id, p.name, p.description, p.price, p.cost_price,
                   p.unit_id, p.category_id, p.tax_id
            FROM products p
            WHERE (p.deleted IS NULL OR p.deleted = 0)
            LIMIT 5
        """)

        products = []
        for row in cursor.fetchall():
            products.append({
                'id': row[0],
                'name': row[1],
                'description': row[2] or '',
                'price': float(row[3]) if row[3] else 0.0,
                'cost_price': float(row[4]) if row[4] else 0.0,
                'unit_id': row[5],
                'category_id': row[6],
                'tax_id': row[7]
            })

        log(f"Productos encontrados en PostgreSQL: {len(products)}", "INFO")

        if not products:
            log("No hay productos para probar", "WARNING")
            return

        # Preparar payload
        payload = {'products': products}
        log(f"Payload (primer producto): {json.dumps(products[0], indent=2)}", "INFO")

        # Enviar a API
        response = requests.post(
            f"{API_BASE_URL}/sync-batch/products",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json=payload,
            timeout=30
        )

        log(f"Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            result = response.json()
            log("✅ Endpoint funcionando correctamente", "SUCCESS")
            log(f"Respuesta: {json.dumps(result, indent=2)[:500]}", "INFO")
            return True
        else:
            log(f"❌ Error en endpoint", "ERROR")
            log(f"Respuesta: {response.text[:500]}", "ERROR")
            return False

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return False

def test_customer_endpoint(conn, token):
    """Probar endpoint de clientes"""
    log("\n" + "="*70, "INFO")
    log("PROBANDO ENDPOINT: CUSTOMERS", "INFO")
    log("="*70, "INFO")

    try:
        cursor = conn.cursor()

        # Obtener clientes de PostgreSQL
        cursor.execute("""
            SELECT id, name, fiscal_id, email, phone, address,
                   city, state, country, zip_code
            FROM customers
            WHERE (deleted IS NULL OR deleted = 0)
            LIMIT 5
        """)

        customers = []
        for row in cursor.fetchall():
            customers.append({
                'id': row[0],
                'name': row[1],
                'fiscal_id': row[2] or '',
                'email': row[3] or '',
                'phone': row[4] or '',
                'address': row[5] or '',
                'city': row[6] or '',
                'state': row[7] or '',
                'country': row[8] or '',
                'zip_code': row[9] or ''
            })

        log(f"Clientes encontrados en PostgreSQL: {len(customers)}", "INFO")

        if not customers:
            log("No hay clientes para probar", "WARNING")
            return

        # Preparar payload
        payload = {'customers': customers}
        log(f"Payload (primer cliente): {json.dumps(customers[0], indent=2)}", "INFO")

        # Enviar a API
        response = requests.post(
            f"{API_BASE_URL}/sync-batch/customers",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json=payload,
            timeout=30
        )

        log(f"Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            result = response.json()
            log("✅ Endpoint funcionando correctamente", "SUCCESS")
            log(f"Respuesta: {json.dumps(result, indent=2)[:500]}", "INFO")
            return True
        else:
            log(f"❌ Error en endpoint", "ERROR")
            log(f"Respuesta: {response.text[:500]}", "ERROR")
            return False

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return False

def test_seller_endpoint(conn, token):
    """Probar endpoint de vendedores"""
    log("\n" + "="*70, "INFO")
    log("PROBANDO ENDPOINT: SELLERS", "INFO")
    log("="*70, "INFO")

    try:
        cursor = conn.cursor()

        # Obtener vendedores de PostgreSQL
        cursor.execute("""
            SELECT id, name, email, phone, commission_percentage
            FROM sellers
            WHERE (deleted IS NULL OR deleted = 0)
            LIMIT 5
        """)

        sellers = []
        for row in cursor.fetchall():
            sellers.append({
                'id': row[0],
                'name': row[1],
                'email': row[2] or '',
                'phone': row[3] or '',
                'commission_percentage': float(row[4]) if row[4] else 0.0
            })

        log(f"Vendedores encontrados en PostgreSQL: {len(sellers)}", "INFO")

        if not sellers:
            log("No hay vendedores para probar", "WARNING")
            return

        # Preparar payload
        payload = {'sellers': sellers}
        log(f"Payload (primer vendedor): {json.dumps(sellers[0], indent=2)}", "INFO")

        # Enviar a API
        response = requests.post(
            f"{API_BASE_URL}/sync-batch/sellers",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json=payload,
            timeout=30
        )

        log(f"Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            result = response.json()
            log("✅ Endpoint funcionando correctamente", "SUCCESS")
            log(f"Respuesta: {json.dumps(result, indent=2)[:500]}", "INFO")
            return True
        else:
            log(f"❌ Error en endpoint", "ERROR")
            log(f"Respuesta: {response.text[:500]}", "ERROR")
            return False

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return False

def test_company_validation(token):
    """Probar validación de empresa"""
    log("\n" + "="*70, "INFO")
    log("PROBANDO ENDPOINT: COMPANY VALIDATION", "INFO")
    log("="*70, "INFO")

    try:
        payload = {
            'rif': 'J123456789',
            'email': 'test@test.com'
        }

        log(f"Payload: {json.dumps(payload, indent=2)}", "INFO")

        response = requests.post(
            f"{API_BASE_URL}/sync-batch/company/validate",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            json=payload,
            timeout=30
        )

        log(f"Status Code: {response.status_code}", "INFO")

        if response.status_code == 200:
            result = response.json()
            log("✅ Endpoint funcionando correctamente", "SUCCESS")
            log(f"Respuesta: {json.dumps(result, indent=2)}", "INFO")
            return True
        else:
            log(f"❌ Error en endpoint", "ERROR")
            log(f"Respuesta: {response.text}", "ERROR")
            return False

    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return False

# ==========================================
# MAIN
# ==========================================

def main():
    print("\n" + "="*70)
    print("  PRUEBA DE ENDPOINTS API - CHRYSAL SYNC SYSTEM")
    print("="*70)
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    print()

    # Conectar a PostgreSQL
    conn = connect_postgresql()
    if not conn:
        log("No se pudo conectar a PostgreSQL", "ERROR")
        sys.exit(1)

    # Login a API
    token = api_login()
    if not token:
        log("No se pudo hacer login en la API", "ERROR")
        conn.close()
        sys.exit(1)

    # Probar endpoints
    results = {}

    results['company'] = test_company_validation(token)
    results['categories'] = test_category_endpoint(conn, token)
    results['products'] = test_product_endpoint(conn, token)
    results['customers'] = test_customer_endpoint(conn, token)
    results['sellers'] = test_seller_endpoint(conn, token)

    # Resumen
    print("\n" + "="*70, "INFO")
    log("RESUMEN DE PRUEBAS", "INFO")
    log("="*70, "INFO")
    print()

    for endpoint, success in results.items():
        status = "✅ EXITOSO" if success else "❌ FALLÓ"
        color = "SUCCESS" if success else "ERROR"
        log(f"{endpoint.upper()}: {status}", color)

    print()
    total = len(results)
    passed = sum(results.values())
    log(f"Total: {passed}/{total} endpoints funcionando", "SUCCESS" if passed == total else "WARNING")

    # Cerrar conexión
    conn.close()

    print()
    print("="*70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        log(f"\n❌ Error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
