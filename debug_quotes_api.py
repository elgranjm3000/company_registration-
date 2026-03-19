"""
Test para ver qué devuelve realmente el endpoint de quotes de la API
"""

import sys
import os
import json
import requests


def test_quotes_api_endpoint():
    """Test que muestra qué devuelve el endpoint de quotes"""

    print("="*70)
    print("TEST: Endpoint /api/sync-batch/quotes")
    print("="*70)

    # Leer configuración
    config_file = "sync_config_api.json"
    if not os.path.exists(config_file):
        print(f"\n❌ ERROR: No existe el archivo {config_file}")
        print("Primero debes configurar el sistema.")
        return False

    with open(config_file, 'r') as f:
        config = json.load(f)

    api_url = config.get('api_url')
    api_email = config.get('api_email')

    # Pedir password
    import getpass
    api_password = getpass.getpass("Ingrese el password de la API: ")

    print(f"\n📡 Conectando a: {api_url}")
    print(f"📧 Email: {api_email}")

    try:
        # Paso 1: Login
        print("\n🔐 Haciendo login...")
        login_url = f"{api_url}/login"
        login_data = {
            'email': api_email,
            'password': api_password
        }

        login_response = requests.post(login_url, json=login_data, timeout=30)
        print(f"✅ Status Code: {login_response.status_code}")

        if login_response.status_code != 200:
            print(f"❌ Error de login: {login_response.text}")
            return False

        login_result = login_response.json()
        if not login_result.get('success'):
            print(f"❌ Error de login: {login_result.get('error')}")
            return False

        token = login_result.get('token')
        company_id = login_result.get('user', {}).get('company_id')
        print(f"✅ Login exitoso")
        print(f"🏢 Company ID: {company_id}")

        # Paso 2: Llamar al endpoint de quotes
        print("\n" + "="*70)
        print("📡 Llamando al endpoint: GET /api/sync-batch/quotes")
        print("="*70)

        quotes_url = f"{api_url}/sync-batch/quotes"
        params = {
            'company_id': company_id,
            'status': 'draft'
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        print(f"\nURL: {quotes_url}")
        print(f"Parámetros: {params}")
        print(f"\n📡 Enviando request...")

        response = requests.get(quotes_url, params=params, headers=headers, timeout=30)

        print(f"\n✅ Status Code: {response.status_code}")
        print(f"✅ Response Time: {response.elapsed.total_seconds():.2f}s")

        # Mostrar headers de respuesta
        print(f"\n📋 Response Headers:")
        for key, value in list(response.headers.items())[:10]:
            print(f"   {key}: {value}")

        # Parsear JSON
        try:
            data = response.json()
        except:
            print(f"\n❌ Error: La respuesta no es JSON válido")
            print(f"Respuesta cruda:\n{response.text[:500]}")
            return False

        # Mostrar estructura completa
        print(f"\n" + "="*70)
        print("📦 ESTRUCTURA JSON DE LA RESPUESTA")
        print("="*70)

        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Análisis específico del customer
        if 'quotes' in data and len(data['quotes']) > 0:
            print(f"\n" + "="*70)
            print("🔍 ANÁLISIS DEL OBJETO CUSTOMER")
            print("="*70)

            first_quote = data['quotes'][0]
            customer = first_quote.get('customer', {})

            print(f"\n👤 Campos del objeto 'customer':")
            if customer:
                for key, value in customer.items():
                    print(f"   • {key}: {value} (tipo: {type(value).__name__})")
            else:
                print("   ⚠️ El objeto 'customer' está vacío o es None")

            # Verificar campos específicos
            print(f"\n🔎 Verificación de campos importantes:")
            print(f"   ¿Tiene 'rif'?              {'✅ SÍ' if 'rif' in customer else '❌ NO'}")
            print(f"   ¿Tiene 'code'?             {'✅ SÍ' if 'code' in customer else '❌ NO'}")
            print(f"   ¿Tiene 'document_number'?  {'✅ SÍ' if 'document_number' in customer else '❌ NO'}")
            print(f"   ¿Tiene 'tax_id'?           {'✅ SÍ' if 'tax_id' in customer else '❌ NO'}")
            print(f"   ¿Tiene 'identification'?    {'✅ SÍ' if 'identification' in customer else '❌ NO'}")
            print(f"   ¿Tiene 'name'?              {'✅ SÍ' if 'name' in customer else '❌ NO'}")

            # Valores
            print(f"\n📝 Valores:")
            print(f"   rif:              '{customer.get('rif', 'N/A')}'")
            print(f"   code:             '{customer.get('code', 'N/A')}'")
            print(f"   document_number:  '{customer.get('document_number', 'N/A')}'")
            print(f"   name:             '{customer.get('name', 'N/A')}'")

        print(f"\n" + "="*70)
        print("✅ TEST COMPLETADO")
        print("="*70)

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_quotes_api_endpoint()
    sys.exit(0 if success else 1)
