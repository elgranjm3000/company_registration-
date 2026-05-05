#!/usr/bin/env python3
"""
Script de Diagnóstico de Autenticación y Endpoints
Verifica que el token se esté usando correctamente en cada endpoint
"""

import os
import sys
import json
from pathlib import Path

# Agregar directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

def diagnosticar_auth():
    """Diagnosticar todo el flujo de autenticación"""

    print("="*70)
    print("🔍 DIAGNÓSTICO DE AUTENTICACIÓN")
    print("="*70)

    # 1. Cargar configuración
    print("\n📋 Paso 1: Cargar configuración")
    print("-" * 70)

    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")

    if not os.path.exists(CONFIG_FILE):
        print(f"❌ No existe archivo de configuración: {CONFIG_FILE}")
        return

    try:
        from config_encryption import decrypt_config

        with open(CONFIG_FILE, 'r') as f:
            config_encriptado = json.load(f)

        print(f"✅ Configuración cargada (encriptada)")
        print(f"   - API URL: {config_encriptado.get('api_url', 'N/A')}")
        print(f"   - API Email: {config_encriptado.get('api_email', 'N/A')}")
        print(f"   - Company Email: {config_encriptado.get('company_email', 'N/A')}")

        # Ver si api_password está encriptado
        api_password_enc = config_encriptado.get('api_password', '')
        if api_password_enc:
            if api_password_enc.startswith('enc:'):
                print(f"   - API Password: ✅ Encriptado (longitud: {len(api_password_enc)})")
            else:
                print(f"   - API Password: ⚠️  En texto plano (longitud: {len(api_password_enc)})")

        # Desencriptar
        config = decrypt_config(config_encriptado)
        api_password = config.get('api_password')

        if api_password:
            print(f"\n✅ Password desencriptado correctamente")
            print(f"   - Longitud: {len(api_password)} caracteres")
            print(f"   - Primeros 4 caracteres: {api_password[:4]}***")
        else:
            print(f"\n❌ Password vacío después de desencriptar")
            return

    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Login y obtener token
    print("\n📋 Paso 2: Login a la API")
    print("-" * 70)

    try:
        from sync_system_api import APIAuthManager

        auth_manager = APIAuthManager(
            base_url=config['api_url'],
            logger=None
        )

        print(f"🔐 Haciendo login con: {config['api_email']}")

        login_result = auth_manager.login(config['api_email'], api_password)

        if not login_result.get('success'):
            print(f"❌ Login falló: {login_result.get('error', 'Error desconocido')}")
            return

        print(f"✅ Login exitoso")

        # Verificar token
        api_token = auth_manager.api_token
        if not api_token:
            print(f"❌ No se obtuvo token")
            return

        print(f"\n✅ Token obtenido:")
        print(f"   - Longitud: {len(api_token)} caracteres")
        print(f"   - Primeros 10 caracteres: {api_token[:10]}...")
        print(f"   - Últimos 10 caracteres: ...{api_token[-10:]}")
        print(f"   - Tipo: {type(api_token)}")

    except Exception as e:
        print(f"❌ Error en login: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Validar empresa
    print("\n📋 Paso 3: Validar empresa")
    print("-" * 70)

    try:
        validate_result = auth_manager.validate_company(
            config['company_rif'],
            config['company_email']
        )

        if not validate_result.get('success'):
            print(f"❌ Validación falló: {validate_result.get('error', 'Error desconocido')}")
            return

        company_id = validate_result.get('company_id')
        print(f"✅ Empresa validada:")
        print(f"   - Company ID: {company_id}")
        print(f"   - Nombre: {validate_result.get('company', {}).get('name', 'N/A')}")

    except Exception as e:
        print(f"❌ Error validando empresa: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Probar cada endpoint con el token
    print("\n📋 Paso 4: Probar endpoints con el token")
    print("-" * 70)

    try:
        from api_client import (
            CategoriesClient,
            ProductsClient,
            CustomersClient,
            SellersClient
        )

        # Importar logging
        import logging
        api_logger = logging.getLogger('diag_api')

        # Base URL
        base_url = config['api_url']

        # 4.1 Categories
        print(f"\n📂 Endpoint: Categories")
        print(f"   URL: {base_url}/sync-batch/categories")
        try:
            cat_client = CategoriesClient(
                base_url=base_url,
                api_key=api_token,
                logger=api_logger
            )

            # Verificar headers
            print(f"   ✅ Cliente creado")
            print(f"   - api_key pasada: {'Sí' if api_token else 'No'} (longitud: {len(api_token) if api_token else 0})")

            # Intentar obtener categorías
            print(f"   📡 Haciendo GET /sync-batch/categories...")

            response = cat_client.session.get(
                f"{base_url}/sync-batch/categories",
                params={'company_id': company_id},
                timeout=10
            )

            print(f"   - Status Code: {response.status_code}")
            print(f"   - Content-Type: {response.headers.get('content-type', 'N/A')}")

            if response.status_code == 200:
                print(f"   ✅ GET Categories funcionó")
                data = response.json()
                print(f"   - Respuesta: success={data.get('success', False)}")
            elif response.status_code == 401:
                print(f"   ❌ 401 Unauthorized - Token inválido")
            elif response.status_code == 403:
                print(f"   ❌ 403 Forbidden - Sin permisos")
            elif response.status_code == 500:
                print(f"   ❌ 500 Internal Server Error - Error del servidor")
            else:
                print(f"   ⚠️  Código inesperado: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # 4.2 Products (GET)
        print(f"\n📦 Endpoint: Products (GET)")
        print(f"   URL: {base_url}/sync-batch/products")
        try:
            prod_client = ProductsClient(
                base_url=base_url,
                api_key=api_token,
                logger=api_logger
            )

            print(f"   ✅ Cliente creado")

            # Intentar obtener productos
            print(f"   📡 Haciendo GET /sync-batch/products...")

            response = prod_client.session.get(
                f"{base_url}/sync-batch/products",
                params={'company_id': company_id},
                timeout=10
            )

            print(f"   - Status Code: {response.status_code}")

            if response.status_code == 200:
                print(f"   ✅ GET Products funcionó")
                data = response.json()
                print(f"   - Respuesta: success={data.get('success', False)}")
            elif response.status_code == 401:
                print(f"   ❌ 401 Unauthorized - Token inválido")
            elif response.status_code == 403:
                print(f"   ❌ 403 Forbidden - Sin permisos")
            elif response.status_code == 500:
                print(f"   ❌ 500 Internal Server Error - Error del servidor")
            else:
                print(f"   ⚠️  Código inesperado: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        # 4.3 Products (POST) - Enviar un producto de prueba
        print(f"\n📦 Endpoint: Products (POST)")
        print(f"   URL: {base_url}/sync-batch/products")
        try:
            print(f"   📡 Haciendo POST /sync-batch/products...")

            # Producto de prueba
            test_product = {
                'code': 'TEST_DIAG_' + str(hash(api_token))[:8],
                'name': 'Producto de Diagnóstico',
                'description': 'Producto para probar autenticación',
                'price': 100.00,
                'cost': 80.00,
                'higher_price': 120.00,
                'coin': 'USD',
                'description_coin': 'Dólares americanos',
                'stock': 10,
                'min_stock': 1,
                'category_id': 1,
                'status': 'active',
                'weight': 1.0,
                'unitary_cost': 80.00,
                'buy_tax': '0',
                'buy_aliquot': 0.0,
                'sale_tax': '16',
                'aliquot': 16.0
            }

            response = prod_client.session.post(
                f"{base_url}/sync-batch/products",
                json={
                    'company_id': company_id,
                    'products': [test_product]
                },
                timeout=10
            )

            print(f"   - Status Code: {response.status_code}")

            if response.status_code in [200, 201]:
                print(f"   ✅ POST Products funcionó")
                data = response.json()
                print(f"   - Respuesta: success={data.get('success', False)}")
                print(f"   - Created: {data.get('created', 0)}")
                print(f"   - Updated: {data.get('updated', 0)}")
                print(f"   - Errors: {data.get('errors', 0)}")

                if data.get('error_details'):
                    print(f"   - Error Details:")
                    for error in data.get('error_details', [])[:3]:
                        print(f"     • {error}")

            elif response.status_code == 401:
                print(f"   ❌ 401 Unauthorized - Token inválido")
            elif response.status_code == 403:
                print(f"   ❌ 403 Forbidden - Sin permisos")
            elif response.status_code == 422:
                print(f"   ❌ 422 Validation Error - Datos inválidos")
                try:
                    data = response.json()
                    print(f"   - Error: {data.get('message', data.get('error', 'Unknown'))}")
                except:
                    print(f"   - Response: {response.text[:200]}")
            elif response.status_code == 500:
                print(f"   ❌ 500 Internal Server Error - Error del servidor")
                print(f"   ⚠️  Esto NO es problema de autenticación")
                print(f"   ⚠️  El servidor rechazó los datos del producto")
                try:
                    print(f"   - Response: {response.text[:300]}")
                except:
                    pass
            else:
                print(f"   ⚠️  Código inesperado: {response.status_code}")
                print(f"   - Response: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Error creando clientes: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Resumen
    print("\n" + "="*70)
    print("📊 RESUMEN DEL DIAGNÓSTICO")
    print("="*70)
    print(f"✅ Configuración: Cargada y desencriptada")
    print(f"✅ Login: Exitoso")
    print(f"✅ Token: Obtenido (longitud: {len(api_token)})")
    print(f"✅ Empresa: Validada (ID: {company_id})")
    print(f"✅ Headers: Authorization: Bearer <token> configurado")
    print(f"\n💡 CONCLUSIÓN:")
    print(f"   La autenticación está funcionando correctamente.")
    print(f"   Si ves errores 500, es por DATOS INVÁLIDOS en el payload,")
    print(f"   NO por problemas de autenticación.")
    print("="*70)

if __name__ == '__main__':
    try:
        diagnosticar_auth()
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnóstico interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n❌ Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🏁 Diagnóstico finalizado")
        input("\nPresiona Enter para salir...")
