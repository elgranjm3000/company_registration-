#!/usr/bin/env python3
"""
Script para probar el batch_size óptimo para MySQL remoto
Prueba con diferentes tamaños de batch y mide el tiempo de ejecución
"""

import pymysql
import time
import sys

# Configuración MySQL
MYSQL_CONFIG = {
    'host': '91.238.160.176',
    'port': 3306,
    'user': 'chrystal_app',
    'password': 'muentes123.',
    'database': 'chrystal_movil',
    'charset': 'utf8mb4'
}

# Batch sizes a probar
BATCH_SIZES = [100, 500, 1000, 2500, 5000, 10000]
REGISTROS_A_INSERTAR = 1000  # Cantidad de registros de prueba

def crear_datos_prueba(cantidad, company_id=160, category_id=6560):
    """Genera datos de prueba para insertar"""
    datos = []
    for i in range(cantidad):
        datos.append((
            company_id,  # company_id (usar 160, 162, o 168)
            f'TEST{i:06d}',
            f'Producto de prueba {i}',
            f'Descripción del producto {i}' * 5,  # ~200 chars
            10.50 + i,
            5.25 + i,
            100 + i,
            10,
            category_id,  # category_id (usar 6560 para company_id=160)
            'active',
            'product',
            '{}',  # images JSON
            15.75 + i,
            '',  # sale_tax
            16,  # aliquot
            '02',  # coin (USD)
            'USD',
            6.30 + i,
            '',  # buy_tax
            0,  # buy_aliquot
            'PZ',
            False
        ))
    return datos

def probar_batch_size(batch_size, company_id=160, category_id=6560):
    """Prueba un tamaño específico de batch"""
    print(f"\n{'='*60}")
    print(f"🧪 Probando batch_size = {batch_size}")
    print(f"{'='*60}")

    datos = crear_datos_prueba(REGISTROS_A_INSERTAR, company_id, category_id)

    query = """
    INSERT INTO products (
        company_id, code, name, description, price, cost, stock, min_stock,
        category_id, status, product_type, images, higher_price, sale_tax,
        aliquot, coin, description_coin, unitary_cost, buy_tax, buy_aliquot,
        unidad, allow_decimal, created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, NOW(), NOW()
    )
    """

    try:
        conn = pymysql.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # Limpiar datos de prueba anteriores
        cursor.execute("DELETE FROM products WHERE code LIKE 'TEST%'")
        conn.commit()

        # Medir tiempo de inserción
        start_time = time.time()

        batches = 0
        for i in range(0, len(datos), batch_size):
            lote = datos[i:i + batch_size]
            cursor.executemany(query, lote)
            conn.commit()
            batches += 1

        elapsed = time.time() - start_time

        # Limpiar datos de prueba
        cursor.execute("DELETE FROM products WHERE code LIKE 'TEST%'")
        conn.commit()

        cursor.close()
        conn.close()

        # Calcular estadísticas
        total_time = elapsed
        avg_time_per_batch = total_time / batches
        avg_time_per_record = total_time / len(datos)

        print(f"✅ ÉXITO")
        print(f"   Registros:     {len(datos):,}")
        print(f"   Batch size:    {batch_size:,}")
        print(f"   Batches:       {batches}")
        print(f"   Tiempo total:  {total_time:.2f} segundos")
        print(f"   Tiempo/batch:  {avg_time_per_batch:.3f} segundos")
        print(f"   Tiempo/registro: {avg_time_per_record*1000:.2f} ms")

        return {
            'batch_size': batch_size,
            'success': True,
            'total_time': total_time,
            'batches': batches,
            'avg_time_per_batch': avg_time_per_batch,
            'avg_time_per_record': avg_time_per_record
        }

    except Exception as e:
        print(f"❌ ERROR: {str(e)[:200]}")
        return {
            'batch_size': batch_size,
            'success': False,
            'error': str(e)
        }

def main():
    """Función principal"""
    print("🧪 PRUEBA DE BATCH_SIZE ÓPTIMO PARA MYSQL REMOTO")
    print(f"📍 Servidor: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
    print(f"📊 Registros a insertar: {REGISTROS_A_INSERTAR:,}")

    resultados = []

    for batch_size in BATCH_SIZES:
        resultado = probar_batch_size(batch_size, company_id=160, category_id=6560)
        resultados.append(resultado)
        time.sleep(1)  # Pausa entre pruebas

    # Resumen
    print(f"\n{'='*60}")
    print("📊 RESUMEN DE RESULTADOS")
    print(f"{'='*60}")
    print(f"{'Batch Size':<12} {'Tiempo':<12} {'Batches':<10} {'ms/rec':<10} {'Estado':<10}")
    print(f"{'-'*60}")

    for r in resultados:
        if r['success']:
            print(f"{r['batch_size']:<12} "
                  f"{r['total_time']:<12.2f} "
                  f"{r['batches']:<10} "
                  f"{r['avg_time_per_record']*1000:<10.2f} "
                  f"✅ OK")
        else:
            print(f"{r['batch_size']:<12} "
                  f"{'N/A':<12} "
                  f"{'N/A':<10} "
                  f"{'N/A':<10} "
                  f"❌ ERROR")

    # Recomendación
    print(f"\n{'='*60}")
    print("💡 RECOMENDACIÓN")
    print(f"{'='*60}")

    exitosos = [r for r in resultados if r['success']]
    if exitosos:
        # El batch_size más rápido que funcionó
        mas_rapido = min(exitosos, key=lambda x: x['avg_time_per_record'])
        print(f"✅ Batch_size más rápido: {mas_rapido['batch_size']}")
        print(f"   Tiempo por registro: {mas_rapido['avg_time_per_record']*1000:.2f} ms")

        # El batch_size más grande que funcionó
        mas_grande = max(exitosos, key=lambda x: x['batch_size'])
        print(f"✅ Batch_size más grande: {mas_grande['batch_size']}")

        # Recomendación conservadora
        print(f"\n🎯 Recomendación CONSERVADORA: {min(500, mas_rapido['batch_size'])}")
        print(f"   (Menor riesgo de timeouts en conexión remota)")
    else:
        print("❌ Ningún batch_size funcionó. Revisa:")
        print("   - Conexión a Internet")
        print("   - Configuración del firewall")
        print("   - Configuración del servidor MySQL")

if __name__ == '__main__':
    main()
