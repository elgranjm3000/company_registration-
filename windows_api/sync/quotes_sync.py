"""
Sincronización de Quotes (API REST → PostgreSQL)
"""

from typing import Dict, List, Any
from datetime import datetime
import hashlib
import json


class QuotesSync:
    """Sincronización de quotes desde la API REST hacia PostgreSQL"""

    def __init__(self, pg_conn, pg_cursor, company_id: int, quotes_client, logger=None):
        """
        Args:
            pg_conn: Conexión a PostgreSQL
            pg_cursor: Cursor de PostgreSQL
            company_id: ID de la empresa
            quotes_client: Cliente API de Quotes
            logger: Función de log opcional
        """
        self.pg_conn = pg_conn
        self.pg_cursor = pg_cursor
        self.company_id = company_id
        self.quotes_client = quotes_client
        self.logger = logger or self._default_logger
        self.stats = {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0}

    def _default_logger(self, msg: str, level: str = "info"):
        """Logger por defecto"""
        print(f"[{level.upper()}] {msg}")

    def _log(self, msg: str, level: str = "info"):
        """Log message"""
        self.logger(msg, level)

    def _get_mac_address(self) -> str:
        """Obtener la MAC address del equipo"""
        import uuid
        try:
            mac = uuid.getnode()
            # Convertir a formato hexadecimal con separadores
            mac_address = ':'.join(("%012X" % mac)[i:i+2] for i in range(0, 12, 2))
            return mac_address
        except Exception:
            return '00:00:00:00:00:00'  # Valor por defecto si falla

    def _ensure_station_exists(self, station_mac: str):
        """Verificar que la MAC existe en stations, si no, insertarla"""
        try:
            # Verificar si ya existe
            self.pg_cursor.execute("""
                SELECT code FROM stations WHERE code = %s LIMIT 1
            """, (station_mac,))

            result = self.pg_cursor.fetchone()
            if result:
                self._log(f"     ✅ Estación ya existe: {station_mac}", "debug")
            else:
                # Insertar nueva estación
                self.pg_cursor.execute("""
                    INSERT INTO stations (code, description, sale_point)
                    VALUES (%s, %s, %s)
                """, (station_mac, station_mac, '00'))
                self.pg_conn.commit()
                self._log(f"     ➕ Estación insertada: {station_mac}", "info")
        except Exception as e:
            self._log(f"     ⚠️ Error verificando estación: {e}", "warning")

    def _generar_hash_quote(self, quote: dict) -> str:
        """Generar hash MD5 de un quote para detectar cambios"""
        # Datos relevantes para el hash
        datos_relevantes = {
            'id': quote.get('id'),
            'quote_number': quote.get('quote_number'),
            'subtotal': quote.get('subtotal'),
            'tax_amount': quote.get('tax_amount'),
            'discount_amount': quote.get('discount_amount'),
            'total': quote.get('total'),
            'status': quote.get('status'),
            'items': quote.get('items', [])
        }
        return hashlib.md5(json.dumps(datos_relevantes, sort_keys=True).encode()).hexdigest()

    def detect_changes(self) -> Dict[str, List]:
        """Detectar cotizaciones en estado draft pendientes de sincronización desde la API"""
        self._log("💰 Detectando cotizaciones en estado draft pendientes de sincronización...", "info")

        cambios = {'nuevos': [], 'existentes': []}

        try:
            # Obtener quotes en estado draft de la API
            quotes_api = self.quotes_client.get_pending_quotes(self.company_id)

            if not quotes_api:
                self._log("   No hay cotizaciones en estado draft", "info")
                return cambios

            self._log(f"   Cotizaciones encontradas: {len(quotes_api)}", "info")

            for quote in quotes_api:
                quote_id = quote.get('id')
                quote_number = quote.get('quote_number')

                # Verificar si ya existe en sync_hashes
                self.pg_cursor.execute("""
                    SELECT record_hash FROM sync_hashes
                    WHERE table_name = 'quotes'
                      AND record_key = %s
                      AND company_id = %s
                """, (str(quote_id), self.company_id))

                resultado = self.pg_cursor.fetchone()

                if resultado is None:
                    # Nuevo quote
                    cambios['nuevos'].append(quote)
                    self._log(f"  ✨ NUEVA: Cotización #{quote_id} ({quote_number})", "info")
                else:
                    cambios['existentes'].append(quote)
                    self._log(f"  ⏭️  EXISTE: Cotización #{quote_id} ({quote_number})", "debug")

            self._log(f"✅ Cotizaciones detectadas: {len(cambios['nuevos'])} nuevas", "info")

        except Exception as e:
            self._log(f"Error detectando cotizaciones: {e}", "error")
            self.stats['errors'] += 1

        return cambios

    def sync_to_postgresql(self, changes: Dict[str, List]) -> bool:
        """Sincronizar quotes a PostgreSQL"""
        nuevos_quotes = changes.get('nuevos', [])

        if not nuevos_quotes:
            self._log("No hay cotizaciones nuevas para sincronizar", "info")
            return True

        self._log(f"Sincronizando {len(nuevos_quotes)} cotizaciones a PostgreSQL...", "info")

        for quote in nuevos_quotes:
            try:
                self._insertar_quote_completo(quote)
                self.stats['created'] += 1

                # Actualizar status en la API REST
                quote_id = quote.get('id')
                quote_number = quote.get('quote_number')

                # Marcar como 'approved' en la API
                if self.quotes_client.update_quote_status(quote_id, self.company_id, 'approved'):
                    self._log(f"  ✅ Estado actualizado en API: Cotización #{quote_id} ({quote_number}) → approved", "info")
                else:
                    self._log(f"  ⚠️ No se pudo actualizar estado en API: Cotización #{quote_id}", "warning")

                # Guardar en sync_hashes
                self._guardar_hash(quote)

                self._log(f"  ✅ Cotización #{quote_id} sincronizada completamente", "info")

            except Exception as e:
                self._log(f"  ❌ Error sincronizando cotización #{quote.get('id')}: {e}", "error")
                self.stats['errors'] += 1

        return self.stats['errors'] == 0

    def _insertar_quote_completo(self, quote: dict) -> int:
        """Insertar quote completo en PostgreSQL (sales_operation)"""
        from decimal import Decimal

        # Datos básicos del quote
        quote_id = quote.get('id')
        quote_number = quote.get('quote_number')
        customer = quote.get('customer') or {}
        seller = quote.get('seller') or {}
        items = quote.get('items') or []

        # Fechas
        emission_date = self._parse_date(quote.get('quote_date'))
        register_date = self._parse_date(quote.get('created_at'))
        expiration_date = self._parse_date(quote.get('valid_until'))

        # MAC Address del equipo
        station = self._get_mac_address()

        # Verificar/insertar MAC en tabla stations
        self._ensure_station_exists(station)

        # Fecha actual para shopping_order_date
        from datetime import date
        shopping_order_date = date.today()  # Formato yyyy-mm-dd

        # Cliente - Buscar code en tabla clients usando el document_number
        customer_document_number = customer.get('document_number') or ''  # RIF del cliente
        customer_code_api = customer.get('code') or ''  # Código del cliente desde la API
        customer_name = customer.get('name') or ''
        client_code = customer_document_number  # Por defecto usar el document_number si no se encuentra
        client_name = customer_name or ''
        client_name_fiscal = 0  # Valor por defecto
        client_address = customer.get('address') or ''
        client_phone = customer.get('phone') or ''

        # Debug: Mostrar datos del cliente recibidos
        self._log(f"     Datos cliente API - Document_Number: '{customer_document_number}', Code: '{customer_code_api}', Name: '{customer_name}'", "debug")

        # Buscar cliente en tabla clients por el campo code (que contiene el RIF)
        client_found = False

        # Prioridad: usar customer.document_number primero (RIF), luego customer.code de la API
        search_value = customer_document_number if customer_document_number else customer_code_api

        if search_value:
            try:
                self.pg_cursor.execute("""
                    SELECT code, name_fiscal FROM clients WHERE code = %s LIMIT 1
                """, (search_value,))
                result = self.pg_cursor.fetchone()
                if result:
                    client_code = result[0]
                    client_name_fiscal = result[1] if result[1] is not None else 0
                    client_found = True
                    self._log(f"     ✅ Cliente encontrado: {search_value} → Code {client_code}, name_fiscal={client_name_fiscal}", "info")
                else:
                    self._log(f"     ⚠️ Cliente no encontrado con code/RIF: {search_value}", "warning")
            except Exception as e:
                self._log(f"     ❌ Error buscando cliente: {e}", "error")

        # Si no se encontró, abortar esta cotización
        if not client_found:
            self._log(f"     ❌ ERROR: No se pudo encontrar el cliente en la tabla clients. Document_Number='{customer_document_number}', Code API='{customer_code_api}'", "error")
            raise Exception(f"Cliente no encontrado en tabla clients. Document_Number='{customer_document_number}', Code='{customer_code_api}'")

        # Vendedor - Usar seller.code directamente, o NULL si no existe
        seller_code = seller.get('code') if seller.get('code') else None
        seller_name = seller.get('name') or ''  # Solo para mostrar, no se usa en FK

        # Totales
        total_amount = 0.0  # Suma de cantidades de items
        tax_amount = float(quote.get('tax_amount', 0))
        discount_amount = float(quote.get('discount_amount', 0))
        total = float(quote.get('total', 0))

        # Calcular totales de items
        total_net_details = 0.0  # TOTAL NETO SIN IMPUESTOS
        total_tax_details = 0.0  # TOTAL DE IMPUESTOS
        total_details = 0.0      # TOTAL DETALLES CON DESCUENTOS INCLUIDO
        total_net_cost = 0.0     # TOTAL COSTO NETO SIN IMPUESTOS

        for item in items:
            unit_price = float(item.get('unit_price', 0))
            quantity = float(item.get('quantity', 0))
            item_discount = float(item.get('discount_amount', 0))
            item_tax = float(item.get('tax_amount', 0))

            # Sumar cantidad de items
            total_amount += quantity

            # Total del item sin impuesto: (precio * cantidad) - descuento
            item_net = (unit_price * quantity) - item_discount

            total_net_details += item_net           # Sumar al total neto
            total_tax_details += item_tax            # Sumar impuestos
            total_details += item_net + item_tax    # Sumar con impuesto (total con descuento incluido)

            # Para costos, usar el mismo cálculo si no hay costo específico
            total_net_cost += item_net

        # Insertar sales_operation (encabezado)
        sql_operation = """
            INSERT INTO sales_operation (
                operation_type, document_no, document_no_internal, emission_date, register_date, expiration_date,
                client_code, client_id, client_name, client_name_fiscal, client_address, client_phone,
                seller, credit_days, wait, begin_used, station, store, locations,
                total_amount, total_net_details, total_tax_details, total_details,
                percent_discount, discount, percent_freight,
                total_net, total_tax, total,
                total_net_cost,
                shopping_order_date,
                pending, canceled, coin_code,
                address_send, contact_send, phone_send
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING correlative
        """

        self.pg_cursor.execute(sql_operation, (
            'BUDGET',  # operation_type
            str(quote_number),  # document_no
            str(quote_number),  # document_no_internal (mismo que document_no)
            emission_date,  # emission_date
            register_date,  # register_date
            expiration_date,  # expiration_date
            client_code,  # client_code
            customer_document_number,  # client_id (RIF)
            client_name,  # client_name
            client_name_fiscal,  # client_name_fiscal
            client_address,  # client_address
            client_phone,  # client_phone
            seller_code,  # seller (code del vendedor o NULL)
            0,  # credit_days
            False,  # wait
            True,  # begin_used
            station,  # station (MAC address)
            '00',  # store
            '00',  # locations
            total_amount,  # total_amount (suma de cantidades de items)
            total_net_details,  # total_net_details (TOTAL NETO SIN IMPUESTOS)
            total_tax_details,  # total_tax_details (TOTAL DE IMPUESTOS)
            total_details,  # total_details (TOTAL DETALLES CON DESCUENTOS INCLUIDO)
            0,  # percent_discount
            0,  # discount
            0,  # percent_freight
            total_net_details,  # total_net (TOTAL DE NETO SIN IMPUESTOS)
            total_tax_details,  # total_tax (TOTAL DE IMPUESTOS)
            total,  # total (total con impuesto)
            total_net_cost,  # total_net_cost (TOTAL COSTO NETO SIN IMPUESTOS)
            shopping_order_date,  # shopping_order_date (fecha actual yyyy-mm-dd)
            True,  # pending
            False,  # canceled
            '02',  # coin_code (código de moneda)
            '',  # address_send (vacío)
            '',  # contact_send (vacío)
            ''   # phone_send (vacío)
        ))

        correlative = self.pg_cursor.fetchone()[0]
        self._log(f"     Insertada venta #{correlative}", "debug")

        # Insertar items (sales_operation_details)
        for item in items:
            self._insertar_item(correlative, item, quote_number)

        # Insertar impuestos (sales_operation_taxes y sales_operation_taxes_coins)
        self._insertar_impuestos(correlative, quote)

        self.pg_conn.commit()
        return correlative

    def _insertar_item(self, main_correlative: int, item: dict, quote_number: str):
        """Insertar item del quote en sales_operation_details"""
        product = item.get('product', {})
        code_product = product.get('code') if product else None

        sql_detalle = """
            INSERT INTO sales_operation_details (
                main_correlative, code_product, description_product, description,
                amount, price, discount, total_tax, total, coin_code
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        self.pg_cursor.execute(sql_detalle, (
            main_correlative,
            code_product,
            item.get('name', ''),
            item.get('name', ''),
            float(item.get('quantity', 0)),
            float(item.get('unit_price', 0)),
            float(item.get('discount_amount', 0)),
            float(item.get('tax_amount', 0)),
            float(item.get('total', 0)),
            '02'  # coin_code (USD)
        ))

        self._log(f"     Insertado ítem: {item.get('name')}", "debug")

    def _insertar_impuestos(self, correlative: int, quote: dict):
        """Insertar impuestos del quote en sales_operation_taxes y sales_operation_taxes_coins"""
        from decimal import Decimal

        # Obtener datos del impuesto
        quote_tax_amount = float(quote.get('tax_amount', 0))
        quote_subtotal = float(quote.get('subtotal', 0))
        quote_discount = float(quote.get('discount_amount', 0))

        # Solo insertar si hay impuestos
        if quote_tax_amount > 0 and quote_subtotal > 0:
            # Calcular alícuota
            quote_aliquot = (quote_tax_amount / quote_subtotal * 100)

            # Base imponible (subtotal menos descuento)
            taxable_amount = quote_subtotal - quote_discount

            # Código de impuesto (IVA General 16%)
            tax_code = '01'

            self._log(f"     Insertando impuesto: aliquot={quote_aliquot:.2f}%, taxable={taxable_amount:.2f}, tax={quote_tax_amount:.2f}", "debug")

            # Insertar en sales_operation_taxes
            sql_tax = """
                INSERT INTO sales_operation_taxes (
                    main_correlative, taxe_code, aliquot, taxable, tax, tax_type
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            self.pg_cursor.execute(sql_tax, (
                correlative,
                tax_code,
                quote_aliquot,
                taxable_amount,
                quote_tax_amount,
                1  # tax_type
            ))

            # Insertar en sales_operation_taxes_coins (solo USD '02')
            sql_tax_coins = """
                INSERT INTO sales_operation_taxes_coins (
                    main_correlative, main_taxe_code, taxable, tax, coin_code
                ) VALUES (%s, %s, %s, %s, %s)
            """

            self.pg_cursor.execute(sql_tax_coins, (
                correlative,
                tax_code,
                taxable_amount,
                quote_tax_amount,
                '02'  # coin_code (USD)
            ))

            self._log(f"     Insertado impuesto en sales_operation_taxes y sales_operation_taxes_coins", "debug")
        else:
            self._log(f"     No hay impuestos para insertar (tax_amount={quote_tax_amount})", "debug")

    def _guardar_hash(self, quote: dict):
        """Guardar hash en sync_hashes"""
        quote_id = quote.get('id')
        hash_value = self._generar_hash_quote(quote)

        self.pg_cursor.execute("""
            INSERT INTO sync_hashes (table_name, record_key, record_hash, company_id, pending_sync, deleted_at)
            VALUES ('quotes', %s, %s, %s, FALSE, NULL)
        """, (str(quote_id), hash_value, self.company_id))

        self.pg_conn.commit()

    def _parse_date(self, date_str: str) -> datetime:
        """Parsear fecha desde formato API"""
        if not date_str:
            return datetime.now()

        try:
            # Formato API: "2026-03-14T10:30:00.000000Z"
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(date_str)
        except:
            return datetime.now()

    def get_stats(self) -> Dict[str, int]:
        """Obtener estadísticas de sincronización"""
        return self.stats
