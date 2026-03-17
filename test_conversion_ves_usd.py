#!/usr/bin/env python3
"""
Script de prueba para conversión de VES a USD en productos

Este script prueba:
1. Obtener tipo de cambio con ExchangeRate API
2. Convertir precios de VES a USD
3. Verificar la conversión funciona correctamente
"""

import sys
import os
import requests

def obtener_tipo_cambio():
    """Obtener tipo de cambio VES a USD"""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'rates' in data and 'VES' in data['rates']:
                return float(data['rates']['VES'])
        return None
    except Exception as e:
        print(f"Error obteniendo tipo de cambio: {e}")
        return None


def test_tipo_cambio():
    """Probar obtener tipo de cambio"""
    print("=" * 80)
    print("🧪 PRUEBA DE OBTENCIÓN DE TIPO DE CAMBIO VES → USD")
    print("=" * 80)
    print()

    print("📡 Consultando ExchangeRate API...")
    tipo_cambio = obtener_tipo_cambio()

    if tipo_cambio:
        print(f"   ✅ Tipo de cambio obtenido: {tipo_cambio:.2f} VES/USD")
    else:
        print(f"   ❌ No se pudo obtener el tipo de cambio")

    print("\n" + "=" * 80)
    print("✅ PRUEBA DE TIPO DE CAMBIO COMPLETADA")
    print("=" * 80)


def test_conversion():
    """Probar conversión de montos"""
    print("\n" + "=" * 80)
    print("🧪 PRUEBA DE CONVERSIÓN DE MONTOS VES → USD")
    print("=" * 80)
    print()

    tipo_cambio = obtener_tipo_cambio()

    if not tipo_cambio:
        print("⚠️ No se pudo obtener tipo de cambio, usando valor de prueba: 417.36")
        tipo_cambio = 417.36

    print(f"💰 Tipo de cambio: {tipo_cambio:.2f} VES/USD")
    print()

    # Casos de prueba
    casos = [
        (1000, "Producto básico"),
        (2500.50, "Precio con decimales"),
        (10000, "Producto costoso"),
        (417.36, "Equivalente a 1 USD"),
        (0, "Precio cero"),
        (None, "Precio nulo"),
    ]

    print("📊 Casos de prueba:")
    print("-" * 80)
    for monto_ves, descripcion in casos:
        if monto_ves is None:
            print(f"{descripcion:25} | {str(monto_ves):15} VES → None")
        elif monto_ves == 0:
            print(f"{descripcion:25} | {monto_ves:15.2f} VES → 0.0000 USD (sin conversión)")
        else:
            monto_usd = round(monto_ves / tipo_cambio, 4)
            print(f"{descripcion:25} | {monto_ves:15.2f} VES → {monto_usd:.4f} USD")

    print("-" * 80)
    print("\n✅ PRUEBA DE CONVERSIÓN COMPLETADA")


def test_producto_ejemplo():
    """Probar con un producto de ejemplo"""
    print("\n" + "=" * 80)
    print("🧪 PRUEBA CON PRODUCTO DE EJEMPLO")
    print("=" * 80)
    print()

    tipo_cambio = obtener_tipo_cambio()

    if not tipo_cambio:
        tipo_cambio = 417.36

    print(f"💰 Tipo de cambio usado: {tipo_cambio:.2f} VES/USD")
    print()

    # Producto de ejemplo en Bolívares
    producto = {
        'code': 'TEST-001',
        'description': 'Producto de prueba en Bolívares',
        'coin': '01',  # Bolívares
        'price': 5000.00,    # Precio en VES
        'cost': 3000.00,     # Costo en VES
        'higher_price': 5500.00,  # Precio mayor en VES
        'unitary_cost': 2800.00   # Costo unitario en VES
    }

    print("📦 Producto en PostgreSQL (Bolívares):")
    print(f"   Code: {producto['code']}")
    print(f"   Description: {producto['description']}")
    print(f"   Coin: {producto['coin']} (01 = Bolívares)")
    print(f"   Price: {producto['price']:.2f} VES")
    print(f"   Cost: {producto['cost']:.2f} VES")
    print(f"   Higher Price: {producto['higher_price']:.2f} VES")
    print(f"   Unitary Cost: {producto['unitary_cost']:.2f} VES")
    print()

    # Convertir a USD
    price_usd = round(producto['price'] / tipo_cambio, 4)
    cost_usd = round(producto['cost'] / tipo_cambio, 4)
    higher_price_usd = round(producto['higher_price'] / tipo_cambio, 4)
    unitary_cost_usd = round(producto['unitary_cost'] / tipo_cambio, 4)

    print("💱 Producto convertido a MySQL (Dólares):")
    print(f"   Code: {producto['code']}")
    print(f"   Description: {producto['description']}")
    print(f"   Price: {price_usd:.4f} USD ✅")
    print(f"   Cost: {cost_usd:.4f} USD ✅")
    print(f"   Higher Price: {higher_price_usd:.4f} USD ✅")
    print(f"   Unitary Cost: {unitary_cost_usd:.4f} USD ✅")
    print()

    print("=" * 80)
    print("✅ PRUEBA CON PRODUCTO COMPLETADA")
    print("=" * 80)


if __name__ == "__main__":
    test_tipo_cambio()
    test_conversion()
    test_producto_ejemplo()

    print("\n" + "=" * 80)
    print("🎉 TODAS LAS PRUEBAS COMPLETADAS")
    print("=" * 80)
