#!/usr/bin/env python3
"""
Script para debuggear el problema del error 600 en la API
"""

import requests
import json

# Configuración - MODIFICA ESTOS VALORES
API_BASE_URL = "https://chrystal.com.ve/mobile/public/api"
API_EMAIL = "admin@test.com"
API_PASSWORD = "password"

print("="*70)
print("  DEBUG - PROBANDO CONEXIÓN API")
print("="*70)
print()
print(f"URL: {API_BASE_URL}")
print(f"Email: {API_EMAIL}")
print()

try:
    print("📤 Enviando petición de login...")
    print(f"   POST {API_BASE_URL}/auth/login")
    print()

    # Petición con máximo detalle
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        json={
            'email': API_EMAIL,
            'password': API_PASSWORD,
            'device_name': 'config-test',
            'force_logout': True
        },
        timeout=30
    )

    print(f"📥 RESPUESTA RECIBIDA")
    print(f"   Status Code: {response.status_code} (tipo: {type(response.status_code)})")
    print(f"   Reason: {response.reason}")
    print(f"   URL final: {response.url}")
    print(f"   Headers: {dict(response.headers)}")
    print()

    # Verificar si el status_code es válido
    if response.status_code >= 600:
        print("❌ ERROR: Status code >= 600 (INVÁLIDO)")
        print(f"   Esto indica un problema con la respuesta del servidor")
        print()

    # Mostrar contenido
    print("Contenido de la respuesta:")
    print("-" * 70)
    try:
        print(response.text[:500])
    except:
        print("No se pudo leer el contenido")

    print()

    # Intentar parsear JSON
    try:
        data = response.json()
        print("JSON parseado exitosamente:")
        print(json.dumps(data, indent=2))
    except:
        print("⚠️  No se pudo parsear como JSON")

    print()

except requests.exceptions.InvalidHeader as e:
    print(f"❌ ERROR: Header inválido - {e}")
except requests.exceptions.Timeout as e:
    print(f"❌ ERROR: Timeout - {e}")
except requests.exceptions.ConnectionError as e:
    print(f"❌ ERROR: Conexión - {e}")
except requests.exceptions.TooManyRedirects as e:
    print(f"❌ ERROR: Demasiados redirects - {e}")
except requests.exceptions.RequestException as e:
    print(f"❌ ERROR: Request exception - {e}")
    print(f"   Tipo: {type(e)}")
    print(f"   Response: {e.response}")
    if e.response is not None:
        print(f"   Status: {e.response.status_code}")
except Exception as e:
    print(f"❌ ERROR INESPERADO: {e}")
    print(f"   Tipo: {type(e)}")
    import traceback
    traceback.print_exc()

print()
print("="*70)
