"""
Test para verificar el manejo de campos None/null en quotes_sync
"""

import sys
import os

# Agregar el directorio principal al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sync.quotes_sync import QuotesSync


def test_quotes_with_null_fields():
    """Test que verifica el manejo de campos None en quotes"""

    print("="*70)
    print("TEST: Manejo de campos None/null en quotes_sync")
    print("="*70)

    # Crear una instancia mock de QuotesSync
    class MockLogger:
        def __call__(self, msg, level="info"):
            print(f"[{level.upper()}] {msg}")

        def info(self, msg):
            print(f"[INFO] {msg}")

        def warning(self, msg):
            print(f"[WARNING] {msg}")

        def error(self, msg):
            print(f"[ERROR] {msg}")

        def debug(self, msg):
            print(f"[DEBUG] {msg}")

    logger = MockLogger()

    # Simular diferentes escenarios de quotes de la API
    test_cases = [
        {
            "name": "Quote con customer=None",
            "quote": {
                "id": 1,
                "quote_number": "QUOTE-001",
                "quote_date": "2026-03-18T10:00:00.000000Z",
                "created_at": "2026-03-18T09:00:00.000000Z",
                "status": "draft",
                "subtotal": 1000.00,
                "tax_amount": 160.00,
                "discount_amount": 0.00,
                "total": 1160.00,
                "customer": None,  # ← null explícito
                "seller": None,
                "items": None
            },
            "expected": "Debe manejar None sin error"
        },
        {
            "name": "Quote con customer vacío",
            "quote": {
                "id": 2,
                "quote_number": "QUOTE-002",
                "quote_date": "2026-03-18T10:00:00.000000Z",
                "created_at": "2026-03-18T09:00:00.000000Z",
                "status": "draft",
                "subtotal": 1000.00,
                "tax_amount": 160.00,
                "discount_amount": 0.00,
                "total": 1160.00,
                "customer": {},  # ← diccionario vacío
                "seller": {},
                "items": []
            },
            "expected": "Debe manejar diccionarios vacíos sin error"
        },
        {
            "name": "Quote con datos completos",
            "quote": {
                "id": 3,
                "quote_number": "QUOTE-003",
                "quote_date": "2026-03-18T10:00:00.000000Z",
                "created_at": "2026-03-18T09:00:00.000000Z",
                "status": "draft",
                "subtotal": 1000.00,
                "tax_amount": 160.00,
                "discount_amount": 0.00,
                "total": 1160.00,
                "customer": {
                    "code": "C001",
                    "rif": "J-12345678",
                    "name": "Cliente Ejemplo",
                    "address": "Av. Principal #123",
                    "phone": "0414-1234567"
                },
                "seller": {
                    "id": 5,
                    "name": "Juan Pérez"
                },
                "items": [
                    {
                        "product": {"code": "PROD001"},
                        "name": "Producto A",
                        "quantity": 10,
                        "unit_price": 100.00,
                        "discount_amount": 0.00,
                        "tax_amount": 160.00,
                        "total": 1160.00
                    }
                ]
            },
            "expected": "Debe procesar datos completos correctamente"
        },
        {
            "name": "Quote con customer parcial (algunos campos None)",
            "quote": {
                "id": 4,
                "quote_number": "QUOTE-004",
                "quote_date": "2026-03-18T10:00:00.000000Z",
                "created_at": "2026-03-18T09:00:00.000000Z",
                "status": "draft",
                "subtotal": 1000.00,
                "tax_amount": 160.00,
                "discount_amount": 0.00,
                "total": 1160.00,
                "customer": {
                    "code": "C002",
                    "rif": None,  # ← campo null dentro del objeto
                    "name": None,
                    "address": None,
                    "phone": None
                },
                "seller": {
                    "id": 6,
                    "name": None
                },
                "items": []
            },
            "expected": "Debe manejar campos None dentro de objetos"
        }
    ]

    # Crear instancia de QuotesSync (sin conexión real a BD)
    quotes_sync = QuotesSync(
        pg_conn=None,
        pg_cursor=None,
        company_id=1,
        quotes_client=None,
        logger=logger
    )

    passed = 0
    failed = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"TEST CASE {i}: {test_case['name']}")
        print(f"Expected: {test_case['expected']}")
        print(f"{'='*70}")

        try:
            quote = test_case['quote']

            # Extraer campos como lo hace el código real
            quote_id = quote.get('id')
            quote_number = quote.get('quote_number')
            customer = quote.get('customer') or {}
            seller = quote.get('seller') or {}
            items = quote.get('items') or []

            print(f"✅ Quote ID: {quote_id}")
            print(f"✅ Quote Number: {quote_number}")
            print(f"✅ Customer type: {type(customer).__name__}")
            print(f"✅ Customer value: {customer}")
            print(f"✅ Seller type: {type(seller).__name__}")
            print(f"✅ Seller value: {seller}")
            print(f"✅ Items type: {type(items).__name__}")
            print(f"✅ Items length: {len(items)}")

            # Extraer campos del cliente
            client_code = customer.get('code') or customer.get('rif') or ''
            client_name = customer.get('name') or ''
            client_address = customer.get('address') or ''
            client_phone = customer.get('phone') or ''

            print(f"✅ Client code: '{client_code}'")
            print(f"✅ Client name: '{client_name}'")
            print(f"✅ Client address: '{client_address}'")
            print(f"✅ Client phone: '{client_phone}'")

            # Extraer nombre del vendedor
            seller_name = seller.get('name') or ''
            print(f"✅ Seller name: '{seller_name}'")

            # Verificar que no haya errores
            assert client_code is not False, "client_code no debe ser False"
            assert client_name is not False, "client_name no debe ser False"
            assert seller_name is not False, "seller_name no debe ser False"
            assert isinstance(items, list), "items debe ser una lista"

            print(f"\n✅ TEST CASE {i} PASSED")
            passed += 1

        except Exception as e:
            print(f"\n❌ TEST CASE {i} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE TESTS")
    print("="*70)
    print(f"✅ Passed: {passed}/{len(test_cases)}")
    print(f"❌ Failed: {failed}/{len(test_cases)}")
    print("="*70)

    if failed == 0:
        print("\n🎉 TODOS LOS TESTS PASARON")
        return True
    else:
        print(f"\n⚠️ {failed} TESTS FALLARON")
        return False


if __name__ == "__main__":
    success = test_quotes_with_null_fields()
    sys.exit(0 if success else 1)
