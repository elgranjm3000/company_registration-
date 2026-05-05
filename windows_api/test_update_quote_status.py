"""
Test simple para verificar la actualización de status de quotes en la API

Este script prueba directamente el endpoint de actualización de status.
"""

import sys
import os
import json
import requests

# Configuración - AJUSTAR ESTOS VALORES
API_URL = "https://chrystal.net/api"  # Cambiar a tu API URL
COMPANY_ID = 124  # Cambiar a tu company_id
QUOTE_ID = None  # Se obtendrá automáticamente del primer quote en draft
TOKEN = None  # Se obtendrá automáticamente

def get_auth_token(email, password):
    """Obtener token de autenticación"""
    print("📝 Autenticando con la API...")

    url = f"{API_URL}/login"
    payload = {
        "email": email,
        "password": password
    }

    print(f"   URL: {url}")
    print(f"   Email: {email}")

    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            token = data.get('token') or data.get('access_token')
            if token:
                print(f"✅ Token obtenido: {token[:30]}...")
            return token
        else:
            print(f"❌ Error en login: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Excepción en login: {e}")
        return None


def get_draft_quotes(token, company_id):
    """Obtener quotes en estado draft"""
    print()
    print("📝 Obteniendo quotes en estado 'draft'...")

    url = f"{API_URL}/sync-batch/quotes/pending"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {
        "company_id": company_id
    }

    print(f"   URL: {url}")
    print(f"   Company ID: {company_id}")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            quotes = data.get('data') or data.get('quotes') or []

            print(f"✅ Encontrados {len(quotes)} quotes en draft:")
            for idx, quote in enumerate(quotes[:5], 1):
                print(f"   {idx}. ID={quote.get('id')} | Number={quote.get('quote_number')} | Status={quote.get('status')}")

            return quotes
        else:
            print(f"❌ Error obteniendo quotes: {response.text}")
            return []

    except Exception as e:
        print(f"❌ Excepción obteniendo quotes: {e}")
        import traceback
        print(traceback.format_exc())
        return []


def update_quote_status(token, quote_id, company_id, new_status):
    """Actualizar status de un quote"""
    print()
    print("📝 Actualizando status del quote...")
    print(f"   Quote ID: {quote_id}")
    print(f"   Status actual: draft")
    print(f"   Nuevo status: {new_status}")
    print()

    url = f"{API_URL}/sync-batch/quotes/{quote_id}/status"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "company_id": company_id,
        "status": new_status
    }

    print("📡 REQUEST:")
    print(f"   URL: {url}")
    print(f"   Method: PUT")
    print(f"   Headers:")
    print(f"      Authorization: Bearer {token[:30]}...")
    print(f"      Content-Type: application/json")
    print(f"   Body:")
    print(f"      {json.dumps(payload, indent=6)}")
    print()

    try:
        print("⏳ Enviando request...")
        response = requests.put(url, headers=headers, json=payload, timeout=10)

        print(f"✅ RESPONSE RECIBIDA:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'content-length']:
                print(f"      {key}: {value}")
        print()

        # Mostrar body
        try:
            response_data = response.json()
            print(f"   Body:")
            print(f"      {json.dumps(response_data, indent=6)}")
        except:
            print(f"   Body (raw):")
            print(f"      {response.text[:500]}")

        print()

        # Analizar resultado
        if response.status_code == 200:
            print("✅ Status Code 200 - OK")
            print()

            if isinstance(response_data, dict):
                if response_data.get('success'):
                    print("✅ Response tiene 'success: true'")
                    print()
                    print("🎉 ÉXITO: El quote FUE ACTUALIZADO correctamente")
                    return True
                elif response_data.get('status') == new_status:
                    print(f"✅ Response tiene 'status: {new_status}'")
                    print()
                    print("🎉 ÉXITO: El quote FUE ACTUALIZADO correctamente")
                    return True
                else:
                    print("⚠️  Response NO indica éxito")
                    print(f"   'success': {response_data.get('success')}")
                    print(f"   'status': {response_data.get('status')}")
                    print()
                    print("❌ POSIBLE FALLO: El status puede no haberse actualizado")
                    return False
            else:
                print("⚠️  Response no es un diccionario")
                print()
                print("❌ No se puede verificar si se actualizó")
                return False

        elif response.status_code == 404:
            print("❌ Status Code 404 - NOT FOUND")
            print()
            print("⚠️  El endpoint NO EXISTE en tu API")
            print()
            print("💡 SOLUCIÓN: Debes crear este endpoint en tu backend:")
            print(f"      PUT {API_URL}/sync-batch/quotes/{{quote_id}}/status")
            print()
            print("   Expected body:")
            print("      {")
            print('          "company_id": 124,')
            print('          "status": "approved"')
            print("      }")
            return False

        elif response.status_code == 401:
            print("❌ Status Code 401 - UNAUTHORIZED")
            print()
            print("⚠️  Token inválido o expirado")
            return False

        elif response.status_code >= 500:
            print(f"❌ Status Code {response.status_code} - SERVER ERROR")
            print()
            print("⚠️  Error interno del servidor")
            return False

        else:
            print(f"❌ Status Code {response.status_code}")
            print()
            print("⚠️  Respuesta no esperada")
            return False

    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: La API no respondió en 10 segundos")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: No se pudo conectar a la API")
        print(f"   URL: {url}")
        return False
    except Exception as e:
        print(f"❌ EXCEPCIÓN: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def main():
    print("=" * 80)
    print("TEST: Actualización de Status de Quotes")
    print("=" * 80)
    print()

    # 1. Pedir credenciales
    print("📝 Paso 1: Ingresar credenciales")
    print()
    email = input("   Email: ").strip()
    password = input("   Password: ").strip()
    print()

    if not email or not password:
        print("❌ ERROR: Email y password son requeridos")
        return

    # 2. Autenticarse
    token = get_auth_token(email, password)
    if not token:
        print()
        print("❌ ERROR: No se pudo obtener el token")
        print("   Verifica tus credenciales e intenta nuevamente")
        return

    # 3. Obtener quotes en draft
    quotes = get_draft_quotes(token, COMPANY_ID)
    if not quotes:
        print()
        print("⚠️  No hay quotes en estado 'draft'")
        print("   No se puede probar la actualización de status")
        print()
        print("💡 TIP: Crea un quote en estado 'draft' en tu API primero")
        return

    # 4. Seleccionar primer quote
    test_quote = quotes[0]
    quote_id = test_quote.get('id')
    quote_number = test_quote.get('quote_number')

    print()
    print("📝 Paso 2: Seleccionar quote para probar")
    print()
    print(f"   Usando el primer quote encontrado:")
    print(f"   Quote ID: {quote_id}")
    print(f"   Quote Number: {quote_number}")
    print(f"   Status Actual: {test_quote.get('status')}")

    confirm = input(f"\n   ¿Probar con este quote? (s/n): ").strip().lower()
    if confirm != 's':
        print("   Test cancelado por el usuario")
        return

    # 5. Actualizar status
    result = update_quote_status(token, quote_id, COMPANY_ID, 'approved')

    print()
    print("=" * 80)
    print("RESULTADO DEL TEST")
    print("=" * 80)
    print()

    if result:
        print("✅ ÉXITO: La actualización de status COMPLETÓ sin errores")
        print()
        print("📋 Próximos pasos:")
        print("   1. Verifica en tu base de datos que el status cambió a 'approved'")
        print(f"   2. Query: SELECT * FROM quotes WHERE id = {quote_id}")
        print("   3. Si el status NO cambió, el endpoint necesita correcciones")
    else:
        print("❌ FALLO: La actualización de status FALLÓ")
        print()
        print("📋 Revisa:")
        print("   1. Los mensajes de error arriba")
        print("   2. Que el endpoint exista en tu API")
        print("   3. Los logs del servidor de tu API")

    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("⚠️  Test cancelado por el usuario")
    except Exception as e:
        print()
        print(f"❌ ERROR: {e}")
        import traceback
        print(traceback.format_exc())
