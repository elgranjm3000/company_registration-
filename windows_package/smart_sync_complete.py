"""
MÓDULO: Smart Sync Complete
Sincronización inteligente PostgreSQL → MySQL con detección de cambios
Usa tabla sync_hashes en PostgreSQL para almacenar estado

Autor: Sistema de Sincronización
Fecha: 2025-01-22
Versión: 1.0
"""

import psycopg2
import mysql.connector
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import sys
import os

# Importar funciones existentes de app.py
def laravel_hash_make(password):
    """Generar hash compatible con Laravel Hash::make()"""
    import bcrypt
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password, salt)
    laravel_hash = hashed.decode('utf-8').replace('$2b$', '$2y$')
    return laravel_hash

def safe_float(value):
    """Convertir a float de forma segura"""
    if isinstance(value, memoryview):
        try:
            value = value.tobytes().decode('utf-8')
        except Exception:
            return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


class SmartSyncComplete:
    """
    Módulo de sincronización inteligente con tabla de hashes

    Uso:
        sync = SmartSyncComplete(app, postgresql_config, mysql_config, company_id)
        sync.inicializar_tabla_hashes()
        sync.ejecutar_sync_completa()
    """

    def __init__(self, app, postgresql_config: dict, mysql_config: dict, company_id: int):
        """
        Inicializar módulo de sincronización

        Args:
            app: Instancia de CompleteSyncApp o ServiceApp
            postgresql_config: Dict con configuración PostgreSQL
            mysql_config: Dict con configuración MySQL
            company_id: ID de compañía
        """
        self.app = app
        self.postgresql_config = postgresql_config
        self.mysql_config = mysql_config
        self.company_id = company_id
        self.sync_running = True

        # Estadísticas
        self.stats = {
            'products': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'customers': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'sellers': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'categories': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'quotes': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0, 'estados_actualizados': 0}
        }

        # Conexiones a bases de datos
        self.pg_conn = None
        self.pg_cursor = None
        self.mysql_conn = None
        self.mysql_cursor = None

    def _log(self, mensaje: str, tipo: str = 'info'):
        """Enviar log a través de la app"""
        if hasattr(self.app, 'log_message'):
            self.app.log_message(mensaje, tipo)
        else:
            # Fallback para uso sin interfaz gráfica
            log_func = getattr(logging, tipo.lower(), logging.info)
            log_func(mensaje)

    # ====================================================================
    # INICIALIZACIÓN
    # ====================================================================

    def inicializar_tabla_hashes(self) -> bool:
        """
        Crear tabla sync_hashes si no existe

        Returns:
            True si se creó o ya existía, False si hubo error
        """
        self._log("Verificando/creando tabla sync_hashes...", "info")

        try:
            self.pg_conn = psycopg2.connect(**self.postgresql_config)
            self.pg_cursor = self.pg_conn.cursor()

            create_table_query = """
            CREATE TABLE IF NOT EXISTS sync_hashes (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(50) NOT NULL,
                record_key VARCHAR(100) NOT NULL,
                record_hash VARCHAR(32) NOT NULL,
                last_sync_data JSONB,
                synced_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                company_id INTEGER,
                UNIQUE(table_name, record_key, company_id)
            );

            CREATE INDEX IF NOT EXISTS idx_sync_hashes_lookup
                ON sync_hashes(table_name, record_key, company_id);

            CREATE INDEX IF NOT EXISTS idx_sync_hashes_table
                ON sync_hashes(table_name, company_id);
            """

            self.pg_cursor.execute(create_table_query)
            self.pg_conn.commit()

            self._log("✅ Tabla sync_hashes lista", "success")
            return True

        except Exception as e:
            self._log(f"❌ Error creando tabla sync_hashes: {str(e)}", "error")
            return False

    def _conectar_bases_datos(self) -> bool:
        """
        Establecer conexiones con PostgreSQL y MySQL

        Returns:
            True si ambas conexiones exitosas
        """
        try:
            # Conectar PostgreSQL
            self.pg_conn = psycopg2.connect(**self.postgresql_config)
            self.pg_cursor = self.pg_conn.cursor()
            self._log("✅ Conectado a PostgreSQL", "success")

            # Conectar MySQL
            self.mysql_conn = mysql.connector.connect(**self.mysql_config)
            self.mysql_cursor = self.mysql_conn.cursor()
            self._log("✅ Conectado a MySQL", "success")

            return True

        except Exception as e:
            self._log(f"❌ Error conectando bases de datos: {str(e)}", "error")
            return False

    def _cerrar_conexiones(self):
        """Cerrar todas las conexiones"""
        try:
            if self.pg_cursor:
                self.pg_cursor.close()
            if self.pg_conn:
                self.pg_conn.close()
            if self.mysql_cursor:
                self.mysql_cursor.close()
            if self.mysql_conn:
                self.mysql_conn.close()
        except Exception as e:
            self._log(f"Error cerrando conexiones: {str(e)}", "warning")

    # ====================================================================
    # GENERACIÓN DE HASHES
    # ====================================================================

    def _generar_hash_product(self, product: tuple) -> str:
        """
        Generar hash MD5 para un producto

        Args:
            product: Tupla con (code, description, short_name, department,
                               price, cost, higher_price, min_stock, status)

        Returns:
            Hash MD5 hexadecimal
        """
        try:
            # Campos clave para detectar cambios
            campos = (
                str(product[0]) if product[0] else '',  # code
                str(product[1]) if product[1] else '',  # description
                str(product[2]) if product[2] else '',  # short_name
                str(product[3]) if product[3] else '',  # department
                str(safe_float(product[6])),            # price
                str(safe_float(product[7])),            # cost
                str(safe_float(product[8])),            # higher_price
                str(safe_float(product[9])),            # min_stock
                str(product[10]) if product[10] else ''  # status
            )

            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except Exception as e:
            self._log(f"Error generando hash de producto: {str(e)}", "error")
            return hashlib.md5(str(product[0]).encode()).hexdigest()

    def _generar_hash_customer(self, customer: tuple) -> str:
        """Generar hash MD5 para un cliente"""
        try:
            campos = (
                str(customer[0]) if customer[0] else '',  # code
                str(customer[1]) if customer[1] else '',  # description
                str(customer[4]) if customer[4] else '',  # email
                str(customer[5]) if customer[5] else ''   # phone
            )
            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except:
            return hashlib.md5(str(customer[0]).encode()).hexdigest()

    def _generar_hash_category(self, category: tuple) -> str:
        """Generar hash MD5 para una categoría"""
        try:
            campos = (
                str(category[0]) if category[0] else '',  # code
                str(category[1]) if category[1] else ''   # description
            )
            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except:
            return hashlib.md5(str(category[0]).encode()).hexdigest()

    # ====================================================================
    # OBTENER HASH GUARDADO
    # ====================================================================

    def _obtener_hash_guardado(self, table_name: str, record_key: str) -> Optional[Tuple]:
        """
        Obtener hash guardado de sync_hashes

        Args:
            table_name: Nombre de tabla
            record_key: Clave del registro

        Returns:
            Tupla (record_hash, updated_at) o None si no existe
        """
        try:
            query = """
            SELECT record_hash, updated_at
            FROM sync_hashes
            WHERE table_name = %s
              AND record_key = %s
              AND company_id = %s
            """

            self.pg_cursor.execute(query, (table_name, record_key, self.company_id))
            return self.pg_cursor.fetchone()
        except Exception as e:
            self._log(f"Error obteniendo hash guardado: {str(e)}", "error")
            return None

    def _guardar_hash(self, table_name: str, record_key: str,
                      record_hash: str, data: dict = None):
        """
        Guardar o actualizar hash en sync_hashes

        Args:
            table_name: Nombre de tabla
            record_key: Clave del registro
            record_hash: Hash MD5
            data: Datos opcionales en JSON
        """
        try:
            # Convertir Decimals a float para serialización JSON
            if data:
                data_json = json.dumps(data, default=str)
            else:
                data_json = None

            query = """
            INSERT INTO sync_hashes (table_name, record_key, record_hash, last_sync_data, company_id, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (table_name, record_key, company_id)
            DO UPDATE SET
                record_hash = EXCLUDED.record_hash,
                last_sync_data = EXCLUDED.last_sync_data,
                updated_at = NOW()
            """

            self.pg_cursor.execute(query, (table_name, record_key, record_hash, data_json, self.company_id))
        except Exception as e:
            self._log(f"Error guardando hash: {str(e)}", "error")

    def _eliminar_hash(self, table_name: str, record_key: str):
        """Eliminar hash de sync_hashes (para registros eliminados)"""
        try:
            query = """
            DELETE FROM sync_hashes
            WHERE table_name = %s
              AND record_key = %s
              AND company_id = %s
            """
            self.pg_cursor.execute(query, (table_name, record_key, self.company_id))
        except Exception as e:
            self._log(f"Error eliminando hash: {str(e)}", "error")

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - PRODUCTS
    # ====================================================================

    def detectar_cambios_products(self) -> Dict[str, List]:
        """
        Detectar cambios en products comparando hashes

        Returns:
            Dict con 'nuevos', 'modificados', 'eliminados'
        """
        self._log("Detectando cambios en products...", "info")

        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            # Obtener todos los productos de PostgreSQL
            query = """
            SELECT DISTINCT ON (a.code)
                a.code,
                a.description,
                a.short_name,
                a.department,
                c.stock,
                a.product_type,
                COALESCE(b.maximum_price, 0) as price,
                COALESCE(b.offer_price, 0) as cost,
                COALESCE(b.higher_price, 0) as higher_price,
                COALESCE(a.minimal_stock, 0) as min_stock,
                CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END as status
            FROM products a
            LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
            LEFT JOIN products_stock c ON a.code = c.product_code
            WHERE a.code IS NOT NULL AND a.code != ''
            ORDER BY a.code
            """

            self.pg_cursor.execute(query)
            productos = self.pg_cursor.fetchall()

            claves_actuales = []

            for producto in productos:
                if not self.sync_running:
                    break

                code = producto[0]
                claves_actuales.append(code)

                # Generar hash actual
                hash_actual = self._generar_hash_product(producto)

                # Buscar hash guardado
                hash_guardado = self._obtener_hash_guardado('products', code)

                if hash_guardado is None:
                    # Nuevo producto
                    cambios['nuevos'].append(producto)
                    self._log(f"  ✨ NUEVO: {code}", "debug")
                elif hash_guardado[0] != hash_actual:
                    # Producto modificado
                    cambios['modificados'].append(producto)
                    self._log(f"  🔄 MODIFICADO: {code}", "debug")

                # Guardar hash actualizado
                self._guardar_hash('products', code, hash_actual)

            # Detectar eliminados
            if claves_actuales:
                placeholders = ','.join(['%s'] * len(claves_actuales))
                query_eliminados = f"""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'products'
                  AND company_id = %s
                  AND record_key NOT IN ({placeholders})
                """

                self.pg_cursor.execute(query_eliminados, [self.company_id] + claves_actuales)
                eliminados = self.pg_cursor.fetchall()

                for (eliminado,) in eliminados:
                    cambios['eliminados'].append({'code': eliminado})
                    self._log(f"  ❌ ELIMINADO: {eliminado}", "warning")
                    self._eliminar_hash('products', eliminado)

            # Commit hashes
            self.pg_conn.commit()

            self._log(f"Products: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados, "
                      f"{len(cambios['eliminados'])} eliminados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en products: {str(e)}", "error")

        return cambios

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - CUSTOMERS
    # ====================================================================

    def detectar_cambios_customers(self) -> Dict[str, List]:
        """Detectar cambios en customers"""
        self._log("Detectando cambios en customers...", "info")

        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            query = """
            SELECT
                code,
                description,
                address,
                client_id,
                email,
                phone,
                contact
            FROM clients
            WHERE code IS NOT NULL AND code != ''
              AND description IS NOT NULL AND description != ''
            ORDER BY code
            """

            self.pg_cursor.execute(query)
            clientes = self.pg_cursor.fetchall()

            claves_actuales = []

            for cliente in clientes:
                if not self.sync_running:
                    break

                code = cliente[0]
                claves_actuales.append(code)

                hash_actual = self._generar_hash_customer(cliente)
                hash_guardado = self._obtener_hash_guardado('customers', code)

                if hash_guardado is None:
                    cambios['nuevos'].append(cliente)
                    self._log(f"  ✨ NUEVO: {code}", "debug")
                elif hash_guardado[0] != hash_actual:
                    cambios['modificados'].append(cliente)
                    self._log(f"  🔄 MODIFICADO: {code}", "debug")

                self._guardar_hash('customers', code, hash_actual)

            # Detectar eliminados
            if claves_actuales:
                placeholders = ','.join(['%s'] * len(claves_actuales))
                query_eliminados = f"""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'customers'
                  AND company_id = %s
                  AND record_key NOT IN ({placeholders})
                """

                self.pg_cursor.execute(query_eliminados, [self.company_id] + claves_actuales)
                eliminados = self.pg_cursor.fetchall()

                for (eliminado,) in eliminados:
                    cambios['eliminados'].append({'code': eliminado})
                    self._log(f"  ❌ ELIMINADO: {eliminado}", "warning")
                    self._eliminar_hash('customers', eliminado)

            self.pg_conn.commit()

            self._log(f"Customers: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados, "
                      f"{len(cambios['eliminados'])} eliminados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en customers: {str(e)}", "error")

        return cambios

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - CATEGORIES
    # ====================================================================

    def detectar_cambios_categories(self) -> Dict[str, List]:
        """Detectar cambios en categories"""
        self._log("Detectando cambios en categories...", "info")

        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            query = """
            SELECT code, description
            FROM department
            WHERE code IS NOT NULL AND code != ''
            ORDER BY code
            """

            self.pg_cursor.execute(query)
            categories = self.pg_cursor.fetchall()

            claves_actuales = []

            for category in categories:
                if not self.sync_running:
                    break

                code = category[0]
                claves_actuales.append(code)

                hash_actual = self._generar_hash_category(category)
                hash_guardado = self._obtener_hash_guardado('categories', code)

                if hash_guardado is None:
                    cambios['nuevos'].append(category)
                    self._log(f"  ✨ NUEVO: {code}", "debug")
                elif hash_guardado[0] != hash_actual:
                    cambios['modificados'].append(category)
                    self._log(f"  🔄 MODIFICADO: {code}", "debug")

                self._guardar_hash('categories', code, hash_actual)

            # Detectar eliminados
            if claves_actuales:
                placeholders = ','.join(['%s'] * len(claves_actuales))
                query_eliminados = f"""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'categories'
                  AND company_id = %s
                  AND record_key NOT IN ({placeholders})
                """

                self.pg_cursor.execute(query_eliminados, [self.company_id] + claves_actuales)
                eliminados = self.pg_cursor.fetchall()

                for (eliminado,) in eliminados:
                    cambios['eliminados'].append({'code': eliminado})
                    self._log(f"  ❌ ELIMINADO: {eliminado}", "warning")
                    self._eliminar_hash('categories', eliminado)

            self.pg_conn.commit()

            self._log(f"Categories: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados, "
                      f"{len(cambios['eliminados'])} eliminados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en categories: {str(e)}", "error")

        return cambios

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - QUOTES (MySQL → PostgreSQL)
    # ====================================================================

    def _generar_hash_quote(self, quote: dict) -> str:
        """
        Generar hash MD5 para un quote (desde MySQL)
        Los quotes van de MySQL → PostgreSQL (dirección opuesta)
        """
        try:
            # Campos clave para detectar cambios
            campos = (
                str(quote.get('id', '')),
                str(quote.get('quote_number', '')),
                str(quote.get('customer_id', '')),
                str(safe_float(quote.get('subtotal', 0))),
                str(safe_float(quote.get('tax', 0))),
                str(safe_float(quote.get('tax_amount', 0))),
                str(safe_float(quote.get('discount', 0))),
                str(safe_float(quote.get('total', 0))),
                str(quote.get('status', 'pending'))
            )

            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except Exception as e:
            self._log(f"Error generando hash de quote: {str(e)}", "error")
            return hashlib.md5(str(quote.get('id', '')).encode()).hexdigest()

    def detectar_cambios_quotes(self) -> Dict[str, List]:
        """
        Detectar cambios en quotes (MySQL → PostgreSQL)

        Returns:
            Dict con 'nuevos', 'modificados', 'actualizaciones_estado'
        """
        self._log("Detectando cambios en quotes (MySQL → PostgreSQL)...", "info")

        cambios = {
            'nuevos': [],
            'modificados': [],
            'actualizaciones_estado': []  # Quotes que cambiaron de status
        }

        try:
            # Obtener quotes de MySQL
            query = """
            SELECT
                id,
                quote_number,
                customer_id,
                company_id,
                user_seller_id,
                subtotal,
                tax,
                tax_amount,
                discount,
                discount_amount,
                total,
                bcv_rate,
                status,
                created_at,
                updated_at
            FROM quotes
            WHERE company_id = %s
            ORDER BY id
            """

            self.mysql_cursor.execute(query, (self.company_id,))
            quotes_mysql = self.mysql_cursor.fetchall()

            # Convertir a diccionarios para facilitar manejo
            columnas = [
                'id', 'quote_number', 'customer_id', 'company_id',
                'user_seller_id', 'subtotal', 'tax', 'tax_amount',
                'discount', 'discount_amount', 'total', 'bcv_rate',
                'status', 'created_at', 'updated_at'
            ]

            quotes_dict = []
            for fila in quotes_mysql:
                quote_dict = dict(zip(columnas, fila))
                quotes_dict.append(quote_dict)

            ids_actuales = []

            for quote in quotes_dict:
                if not self.sync_running:
                    break

                quote_id = quote['id']
                ids_actuales.append(str(quote_id))

                # Generar hash actual
                hash_actual = self._generar_hash_quote(quote)

                # Buscar hash guardado en sync_hashes (PostgreSQL)
                hash_guardado = self._obtener_hash_guardado('quotes', str(quote_id))

                if hash_guardado is None:
                    # Nuevo quote
                    cambios['nuevos'].append(quote)
                    self._log(f"  ✨ NUEVO: Quote #{quote_id} ({quote['quote_number']})", "debug")
                elif hash_guardado[0] != hash_actual:
                    # Quote modificado
                    cambios['modificados'].append(quote)
                    self._log(f"  🔄 MODIFICADO: Quote #{quote_id} ({quote['quote_number']})", "debug")

                # Guardar hash actualizado
                self._guardar_hash('quotes', str(quote_id), hash_actual, quote)

            # Commit hashes en PostgreSQL
            self.pg_conn.commit()

            self._log(f"Quotes: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en quotes: {str(e)}", "error")
            self.stats['quotes']['errores'] += 1

        return cambios

    # ====================================================================
    # SINCRONIZACIÓN DE QUOTES A POSTGRESQL
    # ====================================================================

    def sincronizar_quotes_postgresql(self, cambios: Dict[str, List]):
        """
        Sincronizar quotes de MySQL a PostgreSQL

        Los quotes se migran a sales_operation en PostgreSQL
        """
        if not cambios.get('nuevos') and not cambios.get('modificados'):
            return

        self._log("Sincronizando quotes a PostgreSQL...", "info")

        try:
            # Obtener MAC address para la estación
            import uuid
            mac = ':'.join(('%012X' % uuid.getnode())[i:i+2] for i in range(0, 12, 2))

            OFFSET_CORRELATIVO = 50000

            # Procesar quotes nuevos y modificados
            quotes_a_procesar = cambios.get('nuevos', []) + cambios.get('modificados', [])

            for quote in quotes_a_procesar:
                if not self.sync_running:
                    break

                # Iniciar transacción individual para cada quote
                try:
                    quote_id = quote['id']
                    correlativo = quote_id + OFFSET_CORRELATIVO

                    self._log(f"  Procesando quote #{quote_id}...", "debug")

                    # Verificar si ya existe en PostgreSQL
                    self.pg_cursor.execute(
                        "SELECT correlative FROM sales_operation WHERE document_no = %s LIMIT 1",
                        (str(quote['quote_number']),)
                    )
                    existe = self.pg_cursor.fetchone()

                    if existe:
                        # Ya existe, verificar si hay que actualizar status
                        self._actualizar_status_quote_postgresql(quote)
                        self.pg_conn.commit()  # Commit individual
                        continue

                    # Es nuevo, insertar completamente
                    self._insertar_quote_postgresql(quote, correlativo, mac)

                    # Commit exitoso de este quote
                    self.pg_conn.commit()
                    self.stats['quotes']['nuevos'] += 1

                except Exception as e:
                    # Rollback de este quote y continuar con el siguiente
                    self._log(f"Error procesando quote {quote.get('id')}: {str(e)}", "error")
                    self.pg_conn.rollback()  # Rollback para que no afecte siguientes quotes
                    self.stats['quotes']['errores'] += 1

            self._log(f"✅ Quotes sincronizados a PostgreSQL: {self.stats['quotes']['nuevos']} nuevos", "success")

        except Exception as e:
            self._log(f"Error sincronizando quotes a PostgreSQL: {str(e)}", "error")
            self.stats['quotes']['errores'] += 1

    def _insertar_quote_postgresql(self, quote: dict, correlativo: int, mac: str):
        """Insertar un quote completo en PostgreSQL"""
        from datetime import datetime, timedelta

        # Verificar/obtener station válida
        station = self._obtener_station_valida(mac)

        # Preparar fecha
        emission_date = quote.get('created_at')
        if emission_date is None:
            emission_date = datetime.now()
        elif isinstance(emission_date, str):
            emission_date = datetime.fromisoformat(emission_date.replace('Z', '+00:00'))

        # Obtener datos del customer desde MySQL
        self.mysql_cursor.execute(
            "SELECT name, email, phone, document_number, address FROM customers WHERE id = %s",
            (quote['customer_id'],)
        )
        customer = self.mysql_cursor.fetchone()

        if customer:
            customer_name, customer_email, customer_phone, customer_doc, customer_address = customer
        else:
            customer_name = "Cliente Migrado"
            customer_email = ""
            customer_phone = ""
            customer_doc = f"MIG-{quote['customer_id']}"
            customer_address = ""

        # Insertar sales_operation
        sql_operation = """
        INSERT INTO public.sales_operation (
            correlative, operation_type, document_no, emission_date,
            register_date, client_code, client_name, client_id,
            client_address, client_phone, seller, credit_days,
            expiration_date, description, store, locations, user_code,
            station, total_amount, total_net_details, total_tax_details,
            total_details, percent_discount, discount, total_net,
            total_tax, total, credit, cash, coin_code, canceled,
            pending, wait, total_net_cost, total_tax_cost, total_cost,
            freight_tax, freight_aliquot, document_no_internal,
            control_no, operation_comments
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        document_no = str(quote['quote_number'])
        bcv_rate = safe_float(quote.get('bcv_rate', 0))
        if bcv_rate == 0:
            bcv_rate = 170  # Valor default

        self.pg_cursor.execute(sql_operation, (
            correlativo,                                           # correlative
            'BUDGET',                                              # operation_type
            document_no,                                           # document_no
            emission_date,                                         # emission_date
            emission_date,                                         # register_date
            customer_doc or 'ND',                                  # client_code
            customer_name,                                         # client_name
            customer_doc or f"MIG-{quote['id']}",                  # client_id
            customer_address or 'Dirección migrada',               # client_address
            customer_phone or 'S-N',                               # client_phone
            '00',                                                  # seller
            1,                                                     # credit_days
            emission_date + timedelta(days=1),                     # expiration_date
            '',                                                    # description
            '00',                                                  # store
            '00',                                                  # locations
            '00',                                                  # user_code
            station,                                               # station (válida)
            safe_float(quote.get('total', 0)),                     # total_amount
            safe_float(quote.get('subtotal', 0)),                  # total_net_details
            safe_float(quote.get('tax_amount', 0)),                # total_tax_details
            safe_float(quote.get('total', 0)),                     # total_details
            safe_float(quote.get('discount', 0)),                  # percent_discount
            safe_float(quote.get('discount_amount', 0)),           # discount
            safe_float(quote.get('subtotal', 0)) - safe_float(quote.get('discount_amount', 0)),  # total_net
            safe_float(quote.get('tax_amount', 0)),                # total_tax
            safe_float(quote.get('total', 0)),                     # total
            0.0,                                                   # credit
            0.0,                                                   # cash
            '02',                                                  # coin_code (Dólar)
            False,                                                 # canceled
            True,                                                  # pending
            False,                                                 # wait
            safe_float(quote.get('subtotal', 0)),                  # total_net_cost
            safe_float(quote.get('tax_amount', 0)),                # total_tax_cost
            safe_float(quote.get('total', 0)),                     # total_cost
            '01',                                                  # freight_tax
            16,                                                    # freight_aliquot
            document_no,                                           # document_no_internal
            '',                                                    # control_no
            ''                                                     # operation_comments
        ))

        # Insertar monedas (sales_operation_coins)
        self._insertar_quote_monedas(correlativo, quote, bcv_rate)

        # Insertar items del quote
        self._insertar_quote_items(correlativo, quote, bcv_rate)

        # Insertar impuestos
        self._insertar_quote_taxes(correlativo, quote, bcv_rate)

    def _obtener_station_valida(self, mac: str) -> str:
        """
        Obtener una station válida para el quote

        Args:
            mac: MAC address generada (no usada, tabla stations no tiene mac)

        Returns:
            Código de station válido (existente en tabla stations)
        """
        try:
            # Buscar cualquier station existente
            self.pg_cursor.execute(
                "SELECT code FROM stations LIMIT 1"
            )
            result = self.pg_cursor.fetchone()

            if result:
                station_code = result[0]
                self._log(f"  ℹ️ Usando station: {station_code}", "debug")
                return station_code

            # Si no hay ninguna, usar station por defecto '00'
            self._log("  ⚠️ No hay stations en tabla, usando '00' por defecto", "warning")
            return '00'

        except Exception as e:
            self._log(f"Error obteniendo station: {str(e)}, usando '00'", "warning")
            return '00'

    def _insertar_quote_monedas(self, correlativo: int, quote: dict, bcv_rate: float):
        """Insertar monedas del quote (sales_operation_coins)"""
        subtotal = safe_float(quote.get('subtotal', 0))
        tax_amount = safe_float(quote.get('tax_amount', 0))
        total = safe_float(quote.get('total', 0))
        discount_amount = safe_float(quote.get('discount_amount', 0))

        # Cálculos en bolívares
        subtotal_bcv = subtotal * bcv_rate
        tax_amount_bcv = tax_amount * bcv_rate
        total_bcv = total * bcv_rate
        discount_amount_bcv = discount_amount * bcv_rate

        sql_coins = """
        INSERT INTO public.sales_operation_coins (
            main_correlative, coin_code, factor_type, buy_aliquot,
            sales_aliquot, total_net_details, total_tax_details,
            total_details, discount, freight, total_net, total_tax,
            total, credit, cash
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Moneda dólar (02)
        self.pg_cursor.execute(sql_coins, (
            correlativo, '02', 1, bcv_rate, bcv_rate,
            subtotal, tax_amount, total, discount_amount, 0.0,
            subtotal - discount_amount, tax_amount, total, 0.0, 0.0
        ))

        # Moneda bolívar (01)
        self.pg_cursor.execute(sql_coins, (
            correlativo, '01', 1, bcv_rate, bcv_rate,
            subtotal_bcv, tax_amount_bcv, total_bcv, discount_amount_bcv, 0.0,
            subtotal_bcv - discount_amount_bcv, tax_amount_bcv, total_bcv, 0.0, 0.0
        ))

    def _insertar_quote_items(self, correlativo: int, quote: dict, bcv_rate: float):
        """Insertar items del quote (sales_operation_details)"""
        # Obtener items del quote
        query_items = """
        SELECT
            description, name, subtotal, unit, unit_price, total,
            tax_amount, discount_amount, discount_percentage, quantity,
            product_id
        FROM quote_items
        WHERE quote_id = %s
        ORDER BY id
        """

        self.mysql_cursor.execute(query_items, (quote['id'],))
        items = self.mysql_cursor.fetchall()

        for item in items:
            (description, name, subtotal, unit, unit_price, total,
             tax_amount, discount_amount, discount_percentage, quantity,
             product_id) = item

            # Obtener código de producto
            self.mysql_cursor.execute(
                "SELECT code FROM products WHERE id = %s",
                (product_id,)
            )
            product_result = self.mysql_cursor.fetchone()
            product_code = product_result[0] if product_result else f"MIG-{product_id}"

            # Calcular tax percent
            if subtotal > 0:
                tax_percent = (tax_amount / subtotal * 100)
            else:
                tax_percent = 0

            # Insertar detalle
            sql_detail = """
            INSERT INTO public.sales_operation_details (
                main_correlative, code_product, description_product, amount,
                store, locations, unit, conversion_factor, unit_type, unitary_cost,
                sale_tax, sale_aliquot, price, total_net_cost, total_tax_cost,
                total_cost, total_net_gross, total_tax_gross, total_gross,
                percent_discount, discount, total_net, total_tax, total,
                coin_code, buy_aliquot, buy_tax, pending_amount
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING line
            """

            self.pg_cursor.execute(sql_detail, (
                correlativo,
                product_code,
                name or 'Producto migrado',
                safe_float(quantity),
                '00',
                '00',
                1,  # unit
                1.0,  # conversion_factor
                1,    # unit_type
                safe_float(unit_price) * 0.8,  # unitary_cost (80% del precio)
                '01',  # sale_tax
                tax_percent,
                safe_float(unit_price),
                safe_float(quantity) * safe_float(unit_price) * 0.8,
                safe_float(tax_amount) * 0.8,
                safe_float(quantity) * safe_float(unit_price) * 0.8 + safe_float(tax_amount) * 0.8,
                safe_float(subtotal),
                safe_float(tax_amount),
                safe_float(total),
                safe_float(discount_percentage),
                safe_float(discount_amount),
                safe_float(subtotal) - safe_float(discount_amount),
                safe_float(tax_amount),
                safe_float(total),
                '02',  # coin_code (dólar)
                16,    # buy_aliquot
                '01',  # buy_tax
                safe_float(quantity)
            ))

            line = self.pg_cursor.fetchone()[0]

            # Insertar monedas del detalle
            self._insertar_item_monedas(correlativo, line, item, bcv_rate)

    def _insertar_item_monedas(self, correlativo: int, line: int, item: tuple, bcv_rate: float):
        """Insertar monedas de un item"""
        (description, name, subtotal, unit, unit_price, total,
         tax_amount, discount_amount, discount_percentage, quantity,
         product_id) = item

        unit_price_f = safe_float(unit_price)
        quantity_f = safe_float(quantity)

        # Dólares
        sql_detail_coins = """
        INSERT INTO public.sales_operation_details_coins (
            main_correlative, main_line, unitary_cost, price,
            total_net_cost, total_tax_cost, total_cost,
            total_net_gross, total_tax_gross, total_gross,
            discount, total_net, total_tax, total, coin_code
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        self.pg_cursor.execute(sql_detail_coins, (
            correlativo, line,
            unit_price_f * 0.8,
            unit_price_f,
            quantity_f * unit_price_f * 0.8,
            safe_float(tax_amount) * 0.8,
            quantity_f * unit_price_f * 0.8 + safe_float(tax_amount) * 0.8,
            safe_float(subtotal),
            safe_float(tax_amount),
            safe_float(total),
            safe_float(discount_amount),
            safe_float(subtotal) - safe_float(discount_amount),
            safe_float(tax_amount),
            safe_float(total),
            '02'  # dólar
        ))

        # Bolívares
        subtotal_bcv = safe_float(subtotal) * bcv_rate
        tax_amount_bcv = safe_float(tax_amount) * bcv_rate
        total_bcv = safe_float(total) * bcv_rate
        discount_amount_bcv = safe_float(discount_amount) * bcv_rate

        self.pg_cursor.execute(sql_detail_coins, (
            correlativo, line,
            unit_price_f * 0.8 * bcv_rate,
            unit_price_f * bcv_rate,
            quantity_f * unit_price_f * 0.8 * bcv_rate,
            tax_amount_bcv * 0.8,
            quantity_f * unit_price_f * 0.8 * bcv_rate + tax_amount_bcv * 0.8,
            subtotal_bcv,
            tax_amount_bcv,
            total_bcv,
            discount_amount_bcv,
            subtotal_bcv - discount_amount_bcv,
            tax_amount_bcv,
            total_bcv,
            '01'  # bolívar
        ))

    def _insertar_quote_taxes(self, correlativo: int, quote: dict, bcv_rate: float):
        """Insertar impuestos del quote (sales_operation_taxes)"""
        subtotal = safe_float(quote.get('subtotal', 0))
        tax_amount = safe_float(quote.get('tax_amount', 0))
        discount_amount = safe_float(quote.get('discount_amount', 0))
        bcv = safe_float(quote.get('bcv_rate', 0))
        if bcv == 0:
            bcv = 170

        if tax_amount > 0 and subtotal > 0:
            # Calcular alícuota
            aliquot = (tax_amount / subtotal * 100)

            # Base imponible
            taxable_amount = subtotal - discount_amount

            tax_code = '01'  # IVA General

            # Insertar impuesto
            sql_tax = """
            INSERT INTO public.sales_operation_taxes (
                main_correlative, taxe_code, aliquot, taxable, tax, tax_type
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            self.pg_cursor.execute(sql_tax, (
                correlativo, tax_code, aliquot, taxable_amount, tax_amount, 1
            ))

            # Insertar moneda del impuesto (dólar)
            sql_tax_coins = """
            INSERT INTO public.sales_operation_taxes_coins (
                main_correlative, main_taxe_code, taxable, tax, coin_code
            ) VALUES (%s, %s, %s, %s, %s)
            """

            self.pg_cursor.execute(sql_tax_coins, (
                correlativo, tax_code, taxable_amount, tax_amount, '02'
            ))

            # Bolívares
            taxable_amount_bcv = taxable_amount * bcv
            tax_amount_bcv = tax_amount * bcv

            self.pg_cursor.execute(sql_tax_coins, (
                correlativo, tax_code, taxable_amount_bcv, tax_amount_bcv, '01'
            ))

    def _actualizar_status_quote_postgresql(self, quote: dict):
        """
        Actualizar status de quote en PostgreSQL basado en MySQL

        MySQL status → PostgreSQL pending
        'approved' → pending = false
        'rejected' → pending = true
        """
        try:
            quote_number = str(quote['quote_number'])
            status_mysql = quote.get('status', 'pending')

            # Determinar pending
            pending = (status_mysql != 'approved')

            # Actualizar en PostgreSQL
            update_query = """
            UPDATE public.sales_operation
            SET pending = %s
            WHERE document_no = %s
              AND operation_type = 'BUDGET'
            """

            self.pg_cursor.execute(update_query, (pending, quote_number))

            if self.pg_cursor.rowcount > 0:
                self.stats['quotes']['estados_actualizados'] += 1
                self._log(f"  🔄 Status actualizado: Quote #{quote['id']} → {status_mysql}", "debug")

        except Exception as e:
            self._log(f"Error actualizando status del quote: {str(e)}", "error")

    # ====================================================================
    # SINCRONIZACIÓN DE CAMBIOS A MYSQL
    # ====================================================================

    def sincronizar_products_mysql(self, cambios: Dict[str, List]):
        """Sincronizar cambios de products a MySQL"""
        if not any(cambios.values()):
            return

        self._log("Sincronizando changes de products a MySQL...", "info")

        try:
            # Crear mapeo de categorías
            self.mysql_cursor.execute("SELECT name, id FROM categories WHERE company_id = %s",
                                     (self.company_id,))
            category_mapping = dict(self.mysql_cursor.fetchall())

            # Nuevos
            for producto in cambios['nuevos']:
                if not self.sync_running:
                    break

                code = producto[0]
                category_id = category_mapping.get(producto[3], 1)

                insert_query = """
                INSERT INTO products (
                    company_id, code, name, description, price, cost, stock,
                    min_stock, category_id, status, product_type,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    description = VALUES(description),
                    price = VALUES(price),
                    cost = VALUES(cost),
                    stock = VALUES(stock),
                    min_stock = VALUES(min_stock),
                    category_id = VALUES(category_id),
                    status = VALUES(status),
                    updated_at = NOW()
                """

                self.mysql_cursor.execute(insert_query, (
                    self.company_id, code, producto[2], producto[1],
                    safe_float(producto[6]), safe_float(producto[7]),
                    producto[4] if producto[4] else 0,
                    int(producto[9]) if producto[9] else 0,
                    category_id, producto[10], producto[5]
                ))

                self.stats['products']['nuevos'] += 1

            # Modificados
            for producto in cambios['modificados']:
                if not self.sync_running:
                    break

                code = producto[0]
                category_id = category_mapping.get(producto[3], 1)

                update_query = """
                UPDATE products SET
                    name = %s, description = %s, price = %s, cost = %s,
                    stock = %s, min_stock = %s, category_id = %s, status = %s,
                    updated_at = NOW()
                WHERE company_id = %s AND code = %s
                """

                self.mysql_cursor.execute(update_query, (
                    producto[2], producto[1], safe_float(producto[6]),
                    safe_float(producto[7]), producto[4] if producto[4] else 0,
                    int(producto[9]) if producto[9] else 0, category_id,
                    producto[10], self.company_id, code
                ))

                self.stats['products']['modificados'] += 1

            # Eliminados (opcional - descomentar para activar)
            # for producto in cambios['eliminados']:
            #     if not self.sync_running:
            #         break
            #     code = producto['code']
            #     self.mysql_cursor.execute(
            #         "DELETE FROM products WHERE company_id = %s AND code = %s",
            #         (self.company_id, code)
            #     )
            #     self.stats['products']['eliminados'] += 1

            self.mysql_conn.commit()
            self._log(f"✅ Products sincronizados: {self.stats['products']['nuevos']} nuevos, "
                      f"{self.stats['products']['modificados']} modificados", "success")

        except Exception as e:
            self._log(f"Error sincronizando products a MySQL: {str(e)}", "error")
            self.stats['products']['errores'] += 1

    def sincronizar_customers_mysql(self, cambios: Dict[str, List]):
        """Sincronizar cambios de customers a MySQL"""
        if not any(cambios.values()):
            return

        self._log("Sincronizando cambios de customers a MySQL...", "info")

        try:
            # Nuevos
            for cliente in cambios['nuevos']:
                if not self.sync_running:
                    break

                code, description, address, client_id, email, phone, contact = cliente

                if not email or email.strip() == '':
                    email = f"customer_{code}@temp.local"

                insert_query = """
                INSERT INTO customers (
                    company_id, name, email, document_number, address, phone, contact,
                    status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """

                self.mysql_cursor.execute(insert_query, (
                    self.company_id, description, email, code,
                    address if address else None, phone if phone else None,
                    contact if contact else None, 'active'
                ))

                self.stats['customers']['nuevos'] += 1

            # Modificados
            for cliente in cambios['modificados']:
                if not self.sync_running:
                    break

                code, description, address, client_id, email, phone, contact = cliente

                if not email or email.strip() == '':
                    email = f"customer_{code}@temp.local"

                update_query = """
                UPDATE customers SET
                    name = %s, email = %s, address = %s, phone = %s,
                    contact = %s, updated_at = NOW()
                WHERE company_id = %s AND document_number = %s
                """

                self.mysql_cursor.execute(update_query, (
                    description, email, address if address else None,
                    phone if phone else None, contact if contact else None,
                    self.company_id, code
                ))

                self.stats['customers']['modificados'] += 1

            self.mysql_conn.commit()
            self._log(f"✅ Customers sincronizados: {self.stats['customers']['nuevos']} nuevos, "
                      f"{self.stats['customers']['modificados']} modificados", "success")

        except Exception as e:
            self._log(f"Error sincronizando customers a MySQL: {str(e)}", "error")
            self.stats['customers']['errores'] += 1

    def sincronizar_categories_mysql(self, cambios: Dict[str, List]):
        """Sincronizar cambios de categories a MySQL"""
        if not any(cambios.values()):
            return

        self._log("Sincronizando cambios de categories a MySQL...", "info")

        try:
            for code, description in cambios['nuevos']:
                if not self.sync_running:
                    break

                insert_query = """
                INSERT INTO categories (company_id, name, description, status, created_at, updated_at)
                VALUES (%s, %s, %s, 'active', NOW(), NOW())
                """

                self.mysql_cursor.execute(insert_query, (
                    self.company_id, code, description if description else None
                ))

                self.stats['categories']['nuevos'] += 1

            for code, description in cambios['modificados']:
                if not self.sync_running:
                    break

                update_query = """
                UPDATE categories SET description = %s, updated_at = NOW()
                WHERE company_id = %s AND name = %s
                """

                self.mysql_cursor.execute(update_query, (
                    description if description else None, self.company_id, code
                ))

                self.stats['categories']['modificados'] += 1

            self.mysql_conn.commit()
            self._log(f"✅ Categories sincronizados: {self.stats['categories']['nuevos']} nuevos, "
                      f"{self.stats['categories']['modificados']} modificados", "success")

        except Exception as e:
            self._log(f"Error sincronizando categories a MySQL: {str(e)}", "error")
            self.stats['categories']['errores'] += 1

    # ====================================================================
    # MÉTODO PRINCIPAL
    # ====================================================================

    def ejecutar_sync_completa(self) -> bool:
        """
        Ejecutar sincronización completa detectando cambios

        Returns:
            True si exitoso, False si hubo errores
        """
        inicio = datetime.now()

        self._log("", "info")
        self._log("╔════════════════════════════════════════════════════════════════╗", "info")
        self._log("║          SINCRONIZACIÓN INTELIGENTE CON TABLA DE HASHES          ║", "info")
        self._log("╚════════════════════════════════════════════════════════════════╝", "info")
        self._log("", "info")

        try:
            # Conectar bases de datos
            if not self._conectar_bases_datos():
                return False

            # Detectar cambios en cada entidad
            cambios_products = self.detectar_cambios_products()
            cambios_customers = self.detectar_cambios_customers()
            cambios_categories = self.detectar_cambios_categories()

            # Detectar cambios en quotes (MySQL → PostgreSQL)
            cambios_quotes = self.detectar_cambios_quotes()

            # Verificar si hay cambios
            total_cambios = (
                len(cambios_products['nuevos']) + len(cambios_products['modificados']) +
                len(cambios_customers['nuevos']) + len(cambios_customers['modificados']) +
                len(cambios_categories['nuevos']) + len(cambios_categories['modificados']) +
                len(cambios_quotes['nuevos']) + len(cambios_quotes['modificados'])
            )

            if total_cambios == 0:
                self._log("✨ No hay cambios que sincronizar", "success")
                return True

            # Sincronizar cambios a MySQL
            self.sincronizar_products_mysql(cambios_products)
            self.sincronizar_customers_mysql(cambios_customers)
            self.sincronizar_categories_mysql(cambios_categories)

            # Sincronizar quotes a PostgreSQL (dirección opuesta)
            self.sincronizar_quotes_postgresql(cambios_quotes)

            # Reporte final
            duracion = (datetime.now() - inicio).total_seconds()
            self._log("", "info")
            self._log("╔════════════════════════════════════════════════════════════════╗", "info")
            self._log("║                    RESUMEN DE SINCRONIZACIÓN                    ║", "info")
            self._log("╚════════════════════════════════════════════════════════════════╝", "info")
            self._log(f"Products:   {self.stats['products']['nuevos']} nuevos, "
                      f"{self.stats['products']['modificados']} modificados", "success")
            self._log(f"Customers:  {self.stats['customers']['nuevos']} nuevos, "
                      f"{self.stats['customers']['modificados']} modificados", "success")
            self._log(f"Categories: {self.stats['categories']['nuevos']} nuevos, "
                      f"{self.stats['categories']['modificados']} modificados", "success")
            self._log(f"Quotes:     {self.stats['quotes']['nuevos']} nuevos (MySQL→PG), "
                      f"{self.stats['quotes']['estados_actualizados']} estados actualizados", "success")
            self._log(f"Duración:   {duracion:.2f} segundos", "info")
            self._log("", "info")

            if sum(s['errores'] for s in self.stats.values()) == 0:
                self._log("✅ SINCRONIZACIÓN COMPLETADA CON ÉXITO", "success")
            else:
                self._log("⚠️ SINCRONIZACIÓN COMPLETADA CON ERRORES", "warning")

            return True

        except Exception as e:
            self._log(f"❌ Error durante sincronización: {str(e)}", "error")
            return False

        finally:
            self._cerrar_conexiones()


# ====================================================================
# CLASE ADAPTER PARA SERVICIO (Sin interfaz gráfica)
# ====================================================================

class ServiceApp:
    """
    Adapter para usar SmartSyncComplete sin interfaz Tkinter
    Compatible con servicio de Windows
    """

    def __init__(self, postgresql_config: dict, mysql_config: dict, company_id: int):
        self.postgresql_config = postgresql_config
        self.mysql_config = mysql_config
        self.company_id = company_id
        self.sync_running = True

        # Configurar logging
        logging.basicConfig(
            filename='sync_service.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='a'
        )

    def log_message(self, mensaje: str, tipo: str = 'info'):
        """Log usando logging module"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prefijos = {
            'error': '❌ ERROR:',
            'success': '✅ ÉXITO:',
            'warning': '⚠️ ADVERTENCIA:',
            'info': 'ℹ️ INFO:',
            'debug': '🔍 DEBUG:'
        }

        prefix = prefijos.get(tipo, 'ℹ️ INFO:')
        log_msg = f"[{timestamp}] {prefix} {mensaje}"

        # Usar logging según el tipo
        if tipo == 'error':
            logging.error(log_msg)
        elif tipo == 'warning':
            logging.warning(log_msg)
        elif tipo == 'success':
            logging.info(log_msg)
        else:
            logging.info(log_msg)


# ====================================================================
# EJEMPLO DE USO
# ====================================================================

if __name__ == "__main__":
    # Ejemplo de uso standalone (para pruebas)
    from dotenv import load_dotenv
    import os

    load_dotenv()

    # Configuración
    postgresql_config = {
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }

    mysql_config = {
        'host': os.getenv('DB_HOST_MYSQL'),
        'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
        'user': os.getenv('DB_USER_MYSQL'),
        'password': os.getenv('DB_PASSWORD_MYSQL')
    }

    company_id = 1  # O obtener de MySQL

    # Crear app
    app = ServiceApp(postgresql_config, mysql_config, company_id)

    # Crear módulo de sync
    sync = SmartSyncComplete(app, postgresql_config, mysql_config, company_id)

    # Inicializar tabla (primera vez)
    sync.inicializar_tabla_hashes()

    # Ejecutar sincronización
    sync.ejecutar_sync_completa()
