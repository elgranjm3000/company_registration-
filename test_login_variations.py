#!/usr/bin/env python3
"""
Script para probar diferentes variaciones de login y encontrar el error 500
"""

import requests
import json

API_BASE_URL = "https://chrystal.com.ve/mobile/public/api"
API_EMAIL = "admin@test.com"
API_PASSWORD = "password"

print("="*70)
print("  PROBANDO DIFERENTES VARIACIONES DE LOGIN")
print("="*70)
print()

# Variación 1: Sin force_logout
print("1. LOGIN SIN force_logout")
print("-" * 70)
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
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ EXITO!")
        print(json.dumps(response.json(), indent=2)[:300])
    elif response.status_code >= 500:
        print(f"❌ Error del servidor")
        print(f"Respuesta: {response.text[:300]}")
    else:
        print(f"⚠️  {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")
print()

# Variación 2: Con device_name pero sin force_logout
print("2. LOGIN CON device_name (sin force_logout)")
print("-" * 70)
try:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        json={
            'email': API_EMAIL,
            'password': API_PASSWORD,
            'device_name': 'sync-system'
        },
        timeout=30
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ EXITO!")
        print(json.dumps(response.json(), indent=2)[:300])
    elif response.status_code >= 500:
        print(f"❌ Error del servidor")
        print(f"Respuesta: {response.text[:300]}")
    else:
        print(f"⚠️  {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")
print()

# Variación 3: Con force_logout=False
print("3. LOGIN CON force_logout=False")
print("-" * 70)
try:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        json={
            'email': API_EMAIL,
            'password': API_PASSWORD,
            'device_name': 'sync-system',
            'force_logout': False
        },
        timeout=30
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ EXITO!")
        print(json.dumps(response.json(), indent=2)[:300])
    elif response.status_code >= 500:
        print(f"❌ Error del servidor")
        print(f"Respuesta: {response.text[:300]}")
    else:
        print(f"⚠️  {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")
print()

# Variación 4: La original (con force_logout=True)
print("4. LOGIN ORIGINAL (con force_logout=True)")
print("-" * 70)
try:
    response = requests.post(
        f"{API_BASE_URL}/auth/login",
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        },
        json={
            'email': API_EMAIL,
            'password': API_PASSWORD,
            'force_logout': True
        },
        timeout=30
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ EXITO!")
        print(json.dumps(response.json(), indent=2)[:300])
    elif response.status_code >= 500:
        print(f"❌ Error del servidor")
        print(f"Respuesta: {response.text[:300]}")
    else:
        print(f"⚠️  {response.text[:200]}")
except Exception as e:
    print(f"❌ Error: {e}")
print()

print("="*70)
