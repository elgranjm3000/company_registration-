#!/usr/bin/env python3
"""
Test para verificar el payload que se envía al endpoint de customers
"""

import json
import sys
import os

# Agregar el directorio al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_customer_payload():
    """Test del payload de customers simulando datos de PostgreSQL"""

    print("="*70)
    print("TEST: Payload de Customers")
    print("="*70)

    # Simular datos de PostgreSQL (tuple)
    pg_record = (
        'V12345678',        # 0: code
        'Juan Pérez',       # 1: description
        'Calle 123',        # 2: address
        '12345678',         # 3: client_id
        'juan@email.com',   # 4: email
        '+58-414-1234567',  # 5: phone
        'Contacto',         # 6: contact
        '01'                # 7: status
    )

    print("\n1. DATOS DE POSTGRESQL (tuple):")
    print(f"   code: {pg_record[0]}")
    print(f"   description: {pg_record[1]}")
    print(f"   address: {pg_record[2]}")
    print(f"   client_id: {pg_record[3]}")
    print(f"   email: {pg_record[4]}")
    print(f"   phone: {pg_record[5]}")
    print(f"   contact: {pg_record[6]}")
    print(f"   status: {pg_record[7]}")

    # Simular transformación (igual que en customers_sync.py)
    code, description, address, client_id, email, phone, contact, status = pg_record

    name = description if description else (contact if contact else '')
    status_mapped = 'active' if status == '01' else 'inactive'

    # VALIDACIÓN: code no debe estar vacío
    codigo_final = code
    if not code or code.strip() == '':
        print(f"\n⚠️  WARNING: code VACÍO (usando client_id '{client_id}')")
        codigo_final = client_id if client_id else f"TEMP-{hash(client_id)}"

    payload_dict = {
        'codigo': codigo_final,
        'document_number': client_id,
        'name': name,
        'email': email if email else None,
        'phone': phone if phone else None,
        'address': address if address else None,
        'status': status_mapped
    }

    print("\n2. PAYLOAD TRANSFORMADO (dict):")
    print(f"   codigo: {payload_dict['codigo']}")
    print(f"   document_number: {payload_dict['document_number']}")
    print(f"   name: {payload_dict['name']}")
    print(f"   email: {payload_dict['email']}")
    print(f"   phone: {payload_dict['phone']}")
    print(f"   address: {payload_dict['address']}")
    print(f"   status: {payload_dict['status']}")

    # Payload completo para la API
    api_payload = {
        'company_id': 80,
        'customers': [payload_dict]
    }

    print("\n3. PAYLOAD COMPLETO PARA LA API (JSON):")
    print("="*70)
    print(json.dumps(api_payload, indent=2, ensure_ascii=False))
    print("="*70)

    # Verificar que el campo 'codigo' existe y tiene valor
    print("\n4. VERIFICACION:")
    if 'codigo' in api_payload['customers'][0]:
        codigo_valor = api_payload['customers'][0]['codigo']
        print(f"   ✅ Campo 'codigo' EXISTE")
        print(f"   ✅ Valor de 'codigo': '{codigo_valor}'")

        if codigo_valor and codigo_valor.strip() != '':
            print(f"   ✅ 'codigo' tiene valor VÁLIDO")
        else:
            print(f"   ❌ 'codigo' está VACÍO")
    else:
        print(f"   ❌ Campo 'codigo' NO EXISTE")

    if 'document_number' in api_payload['customers'][0]:
        doc_number = api_payload['customers'][0]['document_number']
        print(f"   ✅ Campo 'document_number' EXISTE")
        print(f"   ✅ Valor de 'document_number': '{doc_number}'")
    else:
        print(f"   ❌ Campo 'document_number' NO EXISTE")

    print("\n" + "="*70)
    print("¿Este payload es IDÉNTICO al que usas en Postman?")
    print("="*70)

if __name__ == '__main__':
    test_customer_payload()
