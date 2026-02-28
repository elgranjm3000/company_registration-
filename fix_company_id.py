#!/usr/bin/env python3
"""
Script para reemplazar self.company_id por company_id obtenido de _get_company_id_from_companies()
"""

import re

# Leer el archivo
with open('smart_sync_complete.py', 'r') as f:
    content = f.read()

# Funciones que necesitan el cambio (excluyendo __init__ y _obtener_company_id)
funciones_a_modificar = [
    'def detectar_cambios_products(',
    'def detectar_cambios_customers(',
    'def detectar_cambios_categories(',
    'def sincronizar_products_mysql(',
    'def sincronizar_customers_mysql(',
    'def sincronizar_sellers_mysql(',
    'def sincronizar_categories_mysql(',
    'def sincronizar_products_postgresql(',
    'def sincronizar_quotes_postgresql(',
]

# Función para agregar company_id al inicio de una función
def agregar_company_id(match):
    indent = match.group(1)
    funcion = match.group(2)

    # Agregar obtención de company_id después del docstring
    return f'''{indent}{funcion}
{indent}    # Obtener company_id desde companies
{indent}    company_id = self._get_company_id_from_companies()
{indent}    if not company_id:
{indent}        self._log("   ❌ No se pudo obtener company_id", "error")
{indent}        return
'''

# Buscar y modificar cada función
for funcion in funciones_a_modificar:
    # Patrón: encuentra la definición de la función
    patron = rf'(\s+)({funcion})'

    # Reemplazar
    content = re.sub(patron, agregar_company_id, content)

# Guardar el archivo
with open('smart_sync_complete.py', 'w') as f:
    f.write(content)

print("✅ Cambios aplicados")
