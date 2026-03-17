#!/usr/bin/env python3
# Leer líneas de ambos archivos
with open('windows_package/smart_sync_complete.py', 'r') as f:
    lineas_wp = f.readlines()

with open('sync_system.py', 'r') as f:
    lineas_ss = f.readlines()

# Función para encontrar una función y extraer sus líneas
def extraer_funcion(lineas, nombre_funcion):
    inicio = None
    indentacion = None
    for i, linea in enumerate(lineas):
        if f'def {nombre_funcion}(' in linea:
            inicio = i
            indentacion = len(linea) - len(linea.lstrip())
            break

    if inicio is None:
        return None

    # Encontrar el fin de la función (siguiente función con misma o menor indentación)
    fin = inicio + 1
    for i in range(inicio + 1, len(lineas)):
        linea = lineas[i]
        if linea.strip() and not linea.strip().startswith('#'):
            indent_actual = len(linea) - len(linea.lstrip())
            if indent_actual <= indentacion and linea.strip().startswith('def '):
                fin = i
                break

    return lineas[inicio:fin]

# Extraer funciones
funciones = [
    '_generar_hash_customer_mysql',
    'detectar_cambios_customers_mysql',
    'sincronizar_customers_postgresql'
]

for func in funciones:
    lineas_func = extraer_funcion(lineas_wp, func)
    if lineas_func:
        print(f"✅ {func}: {len(lineas_func)} líneas")
    else:
        print(f"❌ {func}: NO encontrada")

# Ahora insertar en sync_system.py
print("\nInsertando funciones...")

# 1. Encontrar dónde insertar _generar_hash_customer_mysql
# (después de _generar_hash_product_mysql)
for i, linea in enumerate(lineas_ss):
    if 'def _generar_hash_product_mysql' in linea:
        # Encontrar el fin de esta función
        indent_product = len(linea) - len(linea.lstrip())
        for j in range(i+1, len(lineas_ss)):
            if lineas_ss[j].strip() and not lineas_ss[j].strip().startswith('#'):
                indent_actual = len(lineas_ss[j]) - len(lineas_ss[j].lstrip())
                if indent_actual <= indent_product:
                    # Insertar aquí
                    if 'def _generar_hash_customer_mysql' not in ''.join(lineas_ss):
                        lineas_func = extraer_funcion(lineas_wp, '_generar_hash_customer_mysql')
                        if lineas_func:
                            lineas_ss = lineas_ss[:j] + ['\n'] + lineas_func + lineas_ss[j:]
                            print(f"✅ Insertada _generar_hash_customer_mysql en línea {j}")
                    break
        break

# 2. Insertar detectar_cambios_customers_mysql
# (después de detectar_cambios_products_mysql)
for i, linea in enumerate(lineas_ss):
    if 'def detectar_cambios_products_mysql' in linea:
        # Encontrar el fin de esta función
        indent_product = len(linea) - len(linea.lstrip())
        for j in range(i+1, len(lineas_ss)):
            if lineas_ss[j].strip() and not lineas_ss[j].strip().startswith('#'):
                indent_actual = len(lineas_ss[j]) - len(lineas_ss[j].lstrip())
                if indent_actual <= indent_product:
                    # Insertar aquí
                    if 'def detectar_cambios_customers_mysql' not in ''.join(lineas_ss):
                        lineas_func = extraer_funcion(lineas_wp, 'detectar_cambios_customers_mysql')
                        if lineas_func:
                            lineas_ss = lineas_ss[:j] + ['\n'] + lineas_func + lineas_ss[j:]
                            print(f"✅ Insertada detectar_cambios_customers_mysql en línea {j}")
                    break
        break

# 3. Insertar sincronizar_customers_postgresql
# (antes de sincronizar_categories_mysql)
for i, linea in enumerate(lineas_ss):
    if 'def sincronizar_categories_mysql' in linea:
        if 'def sincronizar_customers_postgresql' not in ''.join(lineas_ss):
            lineas_func = extraer_funcion(lineas_wp, 'sincronizar_customers_postgresql')
            if lineas_func:
                lineas_ss = lineas_ss[:i] + lineas_func + ['\n'] + lineas_ss[i:]
                print(f"✅ Insertada sincronizar_customers_postgresql en línea {i}")
        break

# Guardar
with open('sync_system.py', 'w') as f:
    f.writelines(lineas_ss)

print("\n✅ Archivo guardado")
