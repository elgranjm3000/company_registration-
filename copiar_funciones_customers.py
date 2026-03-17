#!/usr/bin/env python3
"""Copiar funciones de sincronización de customers desde MySQL a sync_system.py"""

import re

# Archivos
archivo_wp = 'windows_package/smart_sync_complete.py'
archivo_ss = 'sync_system.py'

# Leer contenido
with open(archivo_wp, 'r', encoding='utf-8') as f:
    contenido_wp = f.read()

with open(archivo_ss, 'r', encoding='utf-8') as f:
    contenido_ss = f.read()

# ===================================================================
# 1. Extraer funciones de windows_package
# ===================================================================
print("Extrayendo funciones de windows_package/smart_sync_complete.py...")

# Buscar _generar_hash_customer_mysql
patron_hash = r'(    def _generar_hash_customer_mysql\(self, customer: dict\) -> str:.*?return hashlib\.md5\(datos_hash\.encode\(\)\)\.hexdigest\(\)\n)'
match_hash = re.search(patron_hash, contenido_wp, re.DOTALL)
if match_hash:
    func_hash = match_hash.group(1)
    print(f"✅ Extraída _generar_hash_customer_mysql ({len(func_hash)} chars)")
else:
    print("❌ NO encontrada _generar_hash_customer_mysql")
    func_hash = ""

# Buscar detectar_cambios_customers_mysql
patron_detectar = r'(    def detectar_cambios_customers_mysql\(self\) -> Dict\[str, List\]:.*?        return cambios\n)\n\n    def _generar_hash_product_mysql'
match_detectar = re.search(patron_detectar, contenido_wp, re.DOTALL)
if match_detectar:
    func_detectar = match_detectar.group(1)
    print(f"✅ Extraída detectar_cambios_customers_mysql ({len(func_detectar)} chars)")
else:
    print("❌ NO encontrada detectar_cambios_customers_mysql")
    func_detectar = ""

# Buscar sincronizar_customers_postgresql
patron_sync = r'(    def sincronizar_customers_postgresql\(self, cambios: Dict\[str, List\]\):.*?self\.stats\[.customers.\]\[.errores.\] \+= 1\n)\n\n    def sincronizar_categories_mysql'
match_sync = re.search(patron_sync, contenido_wp, re.DOTALL)
if match_sync:
    func_sync = match_sync.group(1)
    print(f"✅ Extraída sincronizar_customers_postgresql ({len(func_sync)} chars)")
else:
    print("❌ NO encontrada sincronizar_customers_postgresql")
    func_sync = ""

# ===================================================================
# 2. Insertar funciones en sync_system.py
# ===================================================================
print("\nInsertando funciones en sync_system.py...")

# Insertar _generar_hash_customer_mysql después de _generar_hash_product_mysql
if func_hash and 'def _generar_hash_customer_mysql' not in contenido_ss:
    patron_insert_hash = r'(    def _generar_hash_product_mysql.*?return hashlib\.md5\(datos_hash\.encode\(\)\)\.hexdigest\(\)\n)\n\n    # ====================================================================\n    # DETECCIÓN DE CAMBIOS - CUSTOMERS'
    if re.search(patron_insert_hash, contenido_ss, re.DOTALL):
        contenido_ss = re.sub(
            patron_insert_hash,
            r'\1\n' + func_hash + '\n\n    # ====================================================================\n    # DETECCIÓN DE CAMBIOS - CUSTOMERS',
            contenido_ss,
            flags=re.DOTALL
        )
        print("✅ Insertada _generar_hash_customer_mysql")
    else:
        print("❌ NO encontrado punto de inserción para _generar_hash_customer_mysql")
else:
    print("ℹ️ _generar_hash_customer_mysql ya existe o no se extrajo")

# Insertar detectar_cambios_customers_mysql después de detectar_cambios_products_mysql
if func_detectar and 'def detectar_cambios_customers_mysql' not in contenido_ss:
    patron_insert_detectar = r'(        return cambios\n\n    )def _generar_hash_product_mysql'
    if re.search(patron_insert_detectar, contenido_ss):
        contenido_ss = re.sub(
            patron_insert_detectar,
            r'\1' + func_detectar + '\n\n    def _generar_hash_product_mysql',
            contenido_ss
        )
        print("✅ Insertada detectar_cambios_customers_mysql")
    else:
        print("❌ NO encontrado punto de inserción para detectar_cambios_customers_mysql")
else:
    print("ℹ️ detectar_cambios_customers_mysql ya existe o no se extrajo")

# Insertar sincronizar_customers_postgresql antes de sincronizar_categories_mysql
if func_sync and 'def sincronizar_customers_postgresql' not in contenido_ss:
    patron_insert_sync = r'(    )def sincronizar_categories_mysql'
    if re.search(patron_insert_sync, contenido_ss):
        contenido_ss = re.sub(
            patron_insert_sync,
            r'\1' + func_sync + '\n\n    def sincronizar_categories_mysql',
            contenido_ss
        )
        print("✅ Insertada sincronizar_customers_postgresql")
    else:
        print("❌ NO encontrado punto de inserción para sincronizar_customers_postgresql")
else:
    print("ℹ️ sincronizar_customers_postgresql ya existe o no se extrajo")

# ===================================================================
# 3. Actualizar flujo principal
# ===================================================================
print("\nActualizando flujo principal...")

# Agregar STEP 5: Detectar customers_mysql
if 'cambios_customers_mysql = self.detectar_cambios_customers_mysql()' not in contenido_ss:
    patron_step5 = r'(            cambios_products_mysql = self\.detectar_cambios_products_mysql\(\)\n\n)'
    if re.search(patron_step5, contenido_ss):
        contenido_ss = re.sub(
            patron_step5,
            r'\1            # Detectar cambios en customers de MySQL (para sincronizar a PostgreSQL)\n            self._log("🔍 STEP 5: Detectando cambios en customers (MySQL → PostgreSQL)...", "debug")\n            cambios_customers_mysql = self.detectar_cambios_customers_mysql()\n\n',
            contenido_ss
        )
        print("✅ Agregado STEP 5: Detectar customers_mysql")
    else:
        print("❌ NO encontrado punto para STEP 5")
else:
    print("ℹ️ STEP 5 ya existe")

# Actualizar STEP 5 quotes → STEP 6
contenido_ss = contenido_ss.replace(
    'self._log("🔍 STEP 5: Detectando cambios en quotes...", "debug")',
    'self._log("🔍 STEP 6: Detectando cambios en quotes...", "debug")'
)
contenido_ss = contenido_ss.replace(
    'self._log("🔍 STEP 5 COMPLETADO", "debug")',
    'self._log("🔍 STEP 6 COMPLETADO", "debug")'
)
print("✅ Actualizado STEP 5 → STEP 6")

# Agregar cambios_customers_mysql al total_cambios
if "len(cambios_customers_mysql['nuevos'])" not in contenido_ss:
    patron_total = r"(            total_cambios = \(\n                len\(cambios_products\['nuevos'\]\) \+ len\(cambios_products\['modificados'\]\) \+\n                len\(cambios_customers\['nuevos'\]\) \+ len\(cambios_customers\['modificados'\]\) \+\n                len\(cambios_categories\['nuevos'\]\) \+ len\(cambios_categories\['modificados'\]\) \+\n                len\(cambios_quotes\['nuevos'\]\) \+ len\(cambios_quotes\['modificados'\]\) \+\n                len\(cambios_products_mysql\['nuevos'\]\) \+ len\(cambios_products_mysql\['modificados'\]\)\n            \))"
    if re.search(patron_total, contenido_ss):
        contenido_ss = re.sub(
            patron_total,
            r'\1                + len(cambios_customers_mysql["nuevos"]) + len(cambios_customers_mysql["modificados"])\n            )',
            contenido_ss
        )
        print("✅ Agregado cambios_customers_mysql a total_cambios")
    else:
        print("❌ NO encontrado total_cambios")
else:
    print("ℹ️ cambios_customers_mysql ya está en total_cambios")

# Agregar sincronización de customers_postgresql
if 'self.sincronizar_customers_postgresql(cambios_customers_mysql)' not in contenido_ss:
    patron_sync_insert = r'(            self\.sincronizar_products_postgresql\(cambios_products_mysql\)\n\n            # \d+\. Quotes a PostgreSQL)'
    if re.search(patron_sync_insert, contenido_ss):
        contenido_ss = re.sub(
            patron_sync_insert,
            r'\1            # 5. Customers de MySQL → PostgreSQL (ANTES de quotes para que existan)\n            # Sincronizar nuevos customers\n            self.sincronizar_customers_postgresql(cambios_customers_mysql)\n\n            # 6. Quotes a PostgreSQL (dirección opuesta, requiere products y customers)',
            contenido_ss
        )
        print("✅ Agregada sincronización de customers_postgresql")
    else:
        print("❌ NO encontrado punto para sincronización")
else:
    print("ℹ️ Sincronización de customers_postgresql ya existe")

# ===================================================================
# 4. Guardar archivo
# ===================================================================
with open(archivo_ss, 'w', encoding='utf-8') as f:
    f.write(contenido_ss)

print("\n✅ Archivo sync_system.py actualizado exitosamente")
