#!/usr/bin/env python3
"""
Script de Diagnóstico para Error 401 en Customers
Verifica el flujo completo de autenticación para el endpoint de customers
"""

import os
import sys
import json
from pathlib import Path

# Agregar directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

def diagnosticar_customers():
    """Diagnosticar autenticación para endpoint de customers"""

    print("="*70)
    print("🔍 DIAGNÓSTICO DE AUTENTICACIÓN - CUSTOMERS")
    print("="*70)

    # 1. Cargar configuración
    print("\n📋 Paso 1: Cargar y desencriptar configuración")
    print("-" * 70)

    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")

    try:
        from config_encryption import decrypt_config

        with open(CONFIG_FILE, 'r') as f:
            config_encrypted = json.load(f)

        print(f"✅ Configuración cargada")
        print(f"   - API Email (encriptado): {config_encrypted.get('api_email', 'N/A')[:30]}...")
        print(f"   - API Password (encriptado): {config_encrypted.get('api_password', 'N/A')[:30]}...")

        # Desencriptar
        config = decrypt_config(config_encrypted)

        api_password = config.get('api_password')
        if not api_password:
            print(f"\n❌ ERROR: api_password está vacío después de desencriptar")
            return

        print(f"\n✅ Password desencriptado correctamente")
        print(f"   - Longitud: {len(api_password)} caracteres")
        print(f"   - Empieza con 'enc:': {api_password.startswith('enc:')}")

    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Login
    print("\n📋 Paso 2: Login a la API")
    print("-" * 70)

    try:
        from sync_system_api import APIAuthManager

        auth_manager = APIAuthManager(
            base_url=config['api_url'],
            logger=None
        )

        print(f"🔐 Haciendo login...")
        login_result = auth_manager.login(config['api_email'], api_password)

        if not login_result.get('success'):
            print(f"\n❌ Login falló:")
            print(f"   Error: {login_result.get('error', 'Error desconocido')}")
            return

        print(f"\n✅ Login exitoso")

        # Verificar token
        api_token = auth_manager.api_token
        if not api_token:
            print(f"\n❌ ERROR: No se obtuvo token del login")
            return

        print(f"\n✅ Token obtenido:")
        print(f"   - Longitud: {len(api_token)} caracteres")
        print(f"   - Primeros 15: {api_token[:15]}...")
        print(f"   - Últimos 15: ...{api_token[-15:]}")
        print(f"   - Tipo: {type(api_token)}")

        # Verificar si el token parece estar encriptado
        if api_token.startswith('enc:'):
            print(f"\n⚠️  ADVERTENCIA: El token empieza con 'enc:'")
            print(f"   El token podría estar encriptado cuando no debería")

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
            print(f"\n❌ Validación falló: {validate_result.get('error', 'Error desconocido')}")
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

    # 4. Crear CustomersClient
    print("\n📋 Paso 4: Crear CustomersClient")
    print("-" * 70)

    try:
        from api_client import CustomersClient

        customers_client = CustomersClient(
            base_url=config['api_url'],
            api_key=api_token,
            logger=None
        )

        print(f"✅ CustomersClient creado")
        print(f"   - api_key pasada: {'Sí' if api_token else 'No'} (longitud: {len(api_token) if api_token else 0})")

        # Verificar el header Authorization en la sesión
        auth_header = customers_client.session.headers.get('Authorization', 'NO ENCONTRADO')
        print(f"   - Header Authorization: {auth_header[:30]}...")

        if 'Bearer' not in auth_header:
            print(f"\n⚠️  ADVERTENCIA: Header Authorization no tiene formato Bearer")
            print(f"   Formato esperado: Bearer <token>")
            print(f"   Formato actual: {auth_header}")

    except Exception as e:
        print(f"❌ Error creando cliente: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5. Probar GET /sync-batch/customers
    print("\n📋 Paso 5: Probar GET /sync-batch/customers")
    print("-" * 70)

    try:
        import requests

        url = f"{config['api_url']}/sync-batch/customers"
        params = {'company_id': company_id}

        print(f"URL: {url}")
        print(f"Params: {params}")
        print(f"\n📡 Enviando request...")

        response = customers_client.session.get(
            url,
            params=params,
            timeout=10
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            print(f"✅ GET Customers funcionó")
            data = response.json()
            print(f"   - success: {data.get('success', False)}")
            if 'data' in data:
                print(f"   - data: {type(data['data'])}")

        elif response.status_code == 401:
            print(f"❌ 401 Unauthorized - Token inválido o expirado")
            try:
                error_data = response.json()
                print(f"   - message: {error_data.get('message', 'N/A')}")
                print(f"   - error: {error_data.get('error', 'N/A')}")
            except:
                print(f"   - Response: {response.text[:200]}")

        elif response.status_code == 403:
            print(f"❌ 403 Forbidden - Sin permisos")
            try:
                error_data = response.json()
                print(f"   - message: {error_data.get('message', 'N/A')}")
                print(f"   - error: {error_data.get('error', 'N/A')}")
            except:
                print(f"   - Response: {response.text[:200]}")

        elif response.status_code == 500:
            print(f"❌ 500 Internal Server Error")
            print(f"   - Response: {response.text[:200]}")

        else:
            print(f"⚠️  Código inesperado: {response.status_code}")
            print(f"   - Response: {response.text[:200]}")

    except Exception as e:
        print(f"❌ Error en request: {e}")
        import traceback
        traceback.print_exc()
        return

    # 6. Probar POST /sync-batch/customers (si hay clientes)
    print("\n📋 Paso 6: Probar POST /sync-batch/customers")
    print("-" * 70)

    try:
        import psycopg2

        # Conectar a PostgreSQL
        pg_config = {
            'host': config['postgres_host'],
            'port': config['postgres_port'],
            'database': config['postgres_database'],
            'user': config['postgres_user'],
            'password': config['postgres_password']
        }

        print(f"Conectando a PostgreSQL...")
        pg_conn = psycopg2.connect(**pg_config)
        pg_cursor = pg_conn.cursor()

        # Obtener un cliente de prueba
        pg_cursor.execute("""
            SELECT code, description, address, rif, email, phone, status
            FROM clients
            LIMIT 1
        """)
        customer = pg_cursor.fetchone()

        if customer:
            print(f"✅ Cliente encontrado en PostgreSQL")

            # Transformar a formato de API
            customer_api = {
                'document_number': customer[0] or '',
                'name': customer[1] or '',
                'email': customer[3] or '',
                'phone': customer[4] or '',
                'address': customer[2] or '',
                'status': customer[6] if customer[6] else 'active'
            }

            print(f"\n📤 Enviando cliente a la API...")
            print(f"   Document: {customer_api['document_number']}")
            print(f"   Name: {customer_api['name']}")

            response = customers_client.session.post(
                f"{config['api_url']}/sync-batch/customers",
                json={
                    'company_id': company_id,
                    'customers': [customer_api]
                },
                timeout=10
            )

            print(f"\nStatus Code: {response.status_code}")

            if response.status_code in [200, 201]:
                print(f"✅ POST Customers funcionó")
                data = response.json()
                print(f"   - success: {data.get('success', False)}")
                print(f"   - created: {data.get('created', 0)}")
                print(f"   - updated: {data.get('updated', 0)}")
                print(f"   - errors: {data.get('errors', 0)}")

            elif response.status_code == 401:
                print(f"❌ 401 Unauthorized - Token inválido")
                try:
                    error_data = response.json()
                    print(f"   - message: {error_data.get('message', 'N/A')}")
                    print(f"   - error: {error_data.get('error', 'N/A')}")
                except:
                    print(f"   - Response: {response.text[:300]}")

            elif response.status_code == 422:
                print(f"❌ 422 Validation Error - Datos inválidos")
                try:
                    error_data = response.json()
                    print(f"   - message: {error_data.get('message', 'N/A')}")
                    print(f"   - error: {error_data.get('error', 'N/A')}")
                except:
                    print(f"   - Response: {response.text[:300]}")

            else:
                print(f"⚠️  Código: {response.status_code}")
                print(f"   - Response: {response.text[:300]}")

        else:
            print(f"⚠️  No hay clientes en PostgreSQL para probar")

        pg_conn.close()

    except Exception as e:
        print(f"❌ Error probando POST: {e}")
        import traceback
        traceback.print_exc()

    # Resumen
    print("\n" + "="*70)
    print("📊 RESUMEN DEL DIAGNÓSTICO")
    print("="*70)
    print(f"✅ Configuración: Cargada y desencriptada")
    print(f"✅ Login: Exitoso")
    print(f"✅ Token: Obtenido (longitud: {len(api_token)})")
    print(f"✅ Empresa: Validada (ID: {company_id})")
    print(f"✅ CustomersClient: Creado con token")
    print(f"✅ Headers: Authorization configurado")
    print(f"\n💡 Si ves errores 401:")
    print(f"   1. Verifica que el token no esté expirado")
    print(f"   2. Verifica que el token sea correcto (no vacío, no None)")
    print(f"   3. Verifica que el header tenga formato 'Bearer <token>'")
    print(f"   4. Contacta al administrador de la API si el token es válido pero rechaza")
    print("="*70)

if __name__ == '__main__':
    try:
        diagnosticar_customers()
    except KeyboardInterrupt:
        print("\n\n⚠️  Diagnóstico interrumpido")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🏁 Diagnóstico finalizado")
        input("\nPresiona Enter para salir...")
