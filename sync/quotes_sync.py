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

    def _ensure_station_exists(self, station_mac: str) -> str:
        """Verificar que la MAC existe en stations, si no, insertarla. Retorna el code de la estación."""
        try:
            # Verificar si ya existe
            self.pg_cursor.execute("""
                SELECT code FROM stations WHERE code = %s LIMIT 1
            """, (station_mac,))

            result = self.pg_cursor.fetchone()
            if result:
                station_code = result[0]
                self._log(f"     ✅ Estación ya existe: {station_mac} → code={station_code}", "debug")
                return station_code
            else:
                # Insertar nueva estación
                self.pg_cursor.execute("""
                    INSERT INTO stations (code, description, sale_point)
                    VALUES (%s, %s, %s)
                    RETURNING code
                """, (station_mac, station_mac, '00'))
                self.pg_conn.commit()
                new_code = self.pg_cursor.fetchone()[0]
                self._log(f"     ➕ Estación insertada: {station_mac} → code={new_code}", "info")
                return new_code
        except Exception as e:
            self._log(f"     ⚠️ Error verificando estación: {e}", "warning")
            return station_mac  # Retornar el MAC original en caso de error

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
        station_mac = self._get_mac_address()

        # Verificar/insertar MAC en tabla stations y obtener el code
        station = self._ensure_station_exists(station_mac)

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

        # Vendedor - Usar seller.code directamente, o '00' si no existe
        seller_code = seller.get('code') if seller.get('code') else '00'
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
        total_tax_cost = 0.0     # TOTAL COSTO IMPUESTOS
        total_cost = 0.0         # TOTAL COSTO CON IMPUESTO
        total_exempt = 0.0       # TOTAL EXENTO

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

            # Si el item no tiene impuesto (tax_amount = 0), es exento
            if item_tax == 0:
                total_exempt += item_net

            # ✅ CORRECCIÓN: Calcular costos como se hace en sales_operation_details (líneas 422-424)
            product = item.get('product', {})
            unitary_cost = round(float(product.get('unitary_cost', 0)) if product else 0.0, 4)
            buy_aliquot = float(product.get('buy_aliquot', 0)) if product else 0.0

            # Los mismos cálculos que en _insertar_item():
            item_total_net_cost = round(unitary_cost * quantity, 2)  # línea 422
            item_total_tax_cost = round(unitary_cost * (buy_aliquot / 100) * quantity, 2) if buy_aliquot > 0 else 0.0  # línea 423
            item_total_cost = round(item_total_net_cost + item_total_tax_cost, 2)  # línea 424

            # Sumar al total (será usado en sales_operation_coins)
            total_net_cost += item_total_net_cost
            total_tax_cost += item_total_tax_cost
            total_cost += item_total_cost

        # Insertar sales_operation (encabezado)
        sql_operation = """
            INSERT INTO sales_operation (
                operation_type, document_no, document_no_internal, emission_date, register_date, expiration_date,
                client_code, client_id, client_name, client_name_fiscal, client_address, client_phone,
                seller, credit_days, wait, begin_used, station, store, locations,
                total_amount, total_net_details, total_tax_details, total_details,
                percent_discount, discount, percent_freight, freight_tax, freight_aliquot,
                total_net, total_tax, total,
                total_net_cost, total_tax_cost, total_cost, total_exempt,
                shopping_order_date, shopping_order_document_no,
                pending, canceled, coin_code,
                address_send, contact_send, phone_send
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
            seller_code,  # seller (code del vendedor o '00')
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
            '01',  # freight_tax
            16,  # freight_aliquot
            total_net_details,  # total_net (TOTAL DE NETO SIN IMPUESTOS)
            total_tax_details,  # total_tax (TOTAL DE IMPUESTOS)
            total,  # total (total con impuesto)
            total_net_cost,  # total_net_cost (TOTAL COSTO NETO SIN IMPUESTOS)
            total_tax_cost,  # total_tax_cost (TOTAL COSTO IMPUESTOS)
            total_cost,  # total_cost (TOTAL DE COSTO CON IMPUESTO)
            total_exempt,  # total_exempt (TOTAL EXENTO)
            shopping_order_date,  # shopping_order_date (fecha actual yyyy-mm-dd)
            '',  # shopping_order_document_no (vacío)
            True,  # pending
            False,  # canceled
            '02',  # coin_code (código de moneda)
            '',  # address_send (vacío)
            '',  # contact_send (vacío)
            ''   # phone_send (vacío)
        ))

        correlative = self.pg_cursor.fetchone()[0]
        self._log(f"     Insertada venta #{correlative}", "debug")

        # Insertar monedas de la operación (sales_operation_coins)
        self._insertar_sales_operation_coins(
            correlative, quote,
            total_net_details, total_tax_details, total_details, discount_amount,
            total_net_cost, total_tax_cost, total_cost, total_exempt
        )

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

        # Obtener description del producto
        description_product = product.get('description', '') if product else item.get('name', '')

        # Buscar unit y conversion_factor en products_units usando product_code
        unit = None
        conversion_factor = 1.0
        if code_product:
            try:
                self.pg_cursor.execute("""
                    SELECT correlative, conversion_factor FROM products_units WHERE product_code = %s LIMIT 1
                """, (code_product,))
                result = self.pg_cursor.fetchone()
                if result:
                    unit = result[0]
                    if result[1]:
                        conversion_factor = float(result[1])
            except Exception as e:
                self._log(f"     ⚠️ Error buscando datos en products_units: {e}", "warning")

        # Obtener datos del producto
        unitary_cost = round(float(product.get('unitary_cost', 0)) if product else 0.0, 4)  # 4 decimales
        sale_tax = product.get('sale_tax', '01') if product else '01'  # Ya viene como '01', '02', etc.
        sale_aliquot = float(product.get('aliquot', 0)) if product else 0.0
        buy_aliquot = float(product.get('buy_aliquot', 0)) if product else 0.0
        product_type = product.get('product_type', '') if product else ''

        # Datos del item
        quantity = float(item.get('quantity', 0))
        unit_price = float(item.get('unit_price', 0))
        discount_amount = float(item.get('discount_amount', 0))
        tax_amount = float(item.get('tax_amount', 0))
        item_total = float(item.get('total', 0))

        # Calcular subtotal (precio * cantidad)
        subtotal = unit_price * quantity

        # Calcular total_net y total_tax
        total_net = subtotal - discount_amount  # TOTAL NETO SIN IMPUESTO
        total_tax = tax_amount  # TOTAL CON IMPUESTO

        # Calcular pending_amount (igual a amount)
        pending_amount = quantity

        # buy_tax: código de tipo de impuesto
        buy_tax = '01'  # IVA General por defecto

        # Calcular costos según fórmula de smart_sync_complete.py
        total_net_cost = round(unitary_cost * quantity, 2)  # unitary_cost * cantidad
        total_tax_cost = round(unitary_cost * (buy_aliquot / 100) * quantity, 2) if buy_aliquot > 0 else 0.0  # unitary_cost * buy_aliquot/100 * cantidad
        total_cost = round(total_net_cost + total_tax_cost, 2)  # total_net_cost + total_tax_cost

        # Calcular gross
        total_net_gross = subtotal  # subtotal del item
        total_tax_gross = tax_amount  # impuesto del item
        total_gross = item_total  # total del item

        sql_detalle = """
            INSERT INTO sales_operation_details (
                main_correlative, code_product, description_product, description,
                amount, price, discount, total, coin_code,
                store, locations,
                unit, conversion_factor, unit_type, unitary_cost, sale_tax, sale_aliquot,
                total_net_cost, total_tax_cost, total_cost,
                total_net_gross, total_tax_gross, total_gross,
                total_net, total_tax, pending_amount, buy_tax, buy_aliquot, product_type
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING line
        """

        self.pg_cursor.execute(sql_detalle, (
            main_correlative,
            code_product,
            description_product,
            '',  # description = string vacío
            quantity,
            unit_price,
            discount_amount,
            item_total,
            '02',  # coin_code (USD)
            '00',  # store
            '00',  # locations
            unit,
            conversion_factor,
            0,  # unit_type
            unitary_cost,
            sale_tax,
            sale_aliquot,
            total_net_cost,
            total_tax_cost,
            total_cost,
            total_net_gross,
            total_tax_gross,
            total_gross,
            total_net,
            total_tax,
            pending_amount,
            buy_tax,
            buy_aliquot,
            product_type
        ))

        # Obtener el line del detalle insertado
        line = self.pg_cursor.fetchone()[0]

        self._log(f"     Insertado ítem: {item.get('name')}", "debug")

        # Insertar en sales_operation_details_coins
        self._insertar_detail_coins(main_correlative, line, unitary_cost, unit_price,
                                    total_net_cost, total_tax_cost, total_cost,
                                    total_net_gross, total_tax_gross, total_gross,
                                    discount_amount, total_net, tax_amount, item_total)

    def _insertar_detail_coins(self, main_correlative: int, line: int,
                               unitary_cost: float, price: float,
                               total_net_cost: float, total_tax_cost: float, total_cost: float,
                               total_net_gross: float, total_tax_gross: float, total_gross: float,
                               discount: float, total_net: float, total_tax: float, total: float):
        """Insertar en sales_operation_details_coins (USD '02' y Bolívares '01')"""
        try:
            # Obtener tasa de cambio desde tabla coin
            bcv_rate = self._get_bcv_rate()

            sql_detail_coins = """
                INSERT INTO sales_operation_details_coins (
                    main_correlative, main_line, unitary_cost, price,
                    total_net_cost, total_tax_cost, total_cost,
                    total_net_gross, total_tax_gross, total_gross,
                    discount, total_net, total_tax, total, coin_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            # Insertar en USD ('02')
            self.pg_cursor.execute(sql_detail_coins, (
                main_correlative,
                line,
                unitary_cost,
                price,
                total_net_cost,
                total_tax_cost,
                total_cost,
                total_net_gross,
                total_tax_gross,
                total_gross,
                discount,
                total_net,
                total_tax,
                total,
                '02'  # USD
            ))

            # Calcular valores en Bolívares
            unitary_cost_bcv = round(unitary_cost * bcv_rate, 2)
            price_bcv = round(price * bcv_rate, 2)
            total_net_cost_bcv = round(total_net_cost * bcv_rate, 2)
            total_tax_cost_bcv = round(total_tax_cost * bcv_rate, 2)
            total_cost_bcv = round(total_cost * bcv_rate, 2)
            total_net_gross_bcv = round(total_net_gross * bcv_rate, 2)
            total_tax_gross_bcv = round(total_tax_gross * bcv_rate, 2)
            total_gross_bcv = round(total_gross * bcv_rate, 2)
            discount_bcv = round(discount * bcv_rate, 2)
            total_net_bcv = round(total_net * bcv_rate, 2)
            total_tax_bcv = round(total_tax * bcv_rate, 2)
            total_bcv = round(total * bcv_rate, 2)

            # Insertar en Bolívares ('01')
            self.pg_cursor.execute(sql_detail_coins, (
                main_correlative,
                line,
                unitary_cost_bcv,
                price_bcv,
                total_net_cost_bcv,
                total_tax_cost_bcv,
                total_cost_bcv,
                total_net_gross_bcv,
                total_tax_gross_bcv,
                total_gross_bcv,
                discount_bcv,
                total_net_bcv,
                total_tax_bcv,
                total_bcv,
                '01'  # Bolívares
            ))

            self._log(f"     Insertado en sales_operation_details_coins (USD y BS, tasa={bcv_rate})", "debug")

        except Exception as e:
            self._log(f"     ⚠️ Error insertando en sales_operation_details_coins: {e}", "warning")

    def _get_bcv_rate(self) -> float:
        """Obtener tasa de cambio BCV desde tabla coin"""
        try:
            self.pg_cursor.execute("""
                SELECT sales_aliquot
                FROM coin
                WHERE code = '02'
                LIMIT 1
            """)

            result = self.pg_cursor.fetchone()
            if result and result[0]:
                return float(result[0])

            # Valor por defecto si no se encuentra
            self._log(f"     ⚠️ No se encontró tasa BCV en tabla coin, usando default 170", "warning")
            return 170.0

        except Exception as e:
            self._log(f"     ⚠️ Error obteniendo tasa BCV: {e}, usando default 170", "warning")
            return 170.0

    def _insertar_impuestos(self, correlative: int, quote: dict):
        """Insertar impuestos del quote en sales_operation_taxes y sales_operation_taxes_coins

        Agrupa los ítems por tipo de impuesto (sale_tax) e inserta un registro por cada tipo.
        """
        from decimal import Decimal
        from collections import defaultdict

        items = quote.get('items', [])

        if not items:
            self._log(f"     No hay ítems para procesar impuestos", "debug")
            return

        # Agrupar ítems por sale_tax (tipo de impuesto)
        taxes_by_type = defaultdict(lambda: {
            'taxable': 0.0,
            'tax': 0.0,
            'aliquot': 0.0,
            'count': 0
        })

        # Procesar cada ítem
        for item in items:
            product = item.get('product', {})
            sale_tax = product.get('sale_tax', '01') if product else '01'
            sale_aliquot = float(product.get('aliquot', 0)) if product else 0.0

            # Calcular subtotal del ítem (precio * cantidad - descuento)
            quantity = float(item.get('quantity', 0))
            unit_price = float(item.get('unit_price', 0))
            discount_amount = float(item.get('discount_amount', 0))
            tax_amount = float(item.get('tax_amount', 0))

            subtotal = (unit_price * quantity) - discount_amount

            # Acumular por tipo de impuesto
            taxes_by_type[sale_tax]['taxable'] += subtotal
            taxes_by_type[sale_tax]['tax'] += tax_amount
            taxes_by_type[sale_tax]['aliquot'] = sale_aliquot
            taxes_by_type[sale_tax]['count'] += 1

        # Obtener tasa BCV
        bcv_rate = self._get_bcv_rate()

        # Insertar un registro por cada tipo de impuesto
        sql_tax = """
            INSERT INTO sales_operation_taxes (
                main_correlative, taxe_code, aliquot, taxable, tax, tax_type
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING line
        """

        sql_tax_coins = """
            INSERT INTO sales_operation_taxes_coins (
                main_correlative, main_line, main_taxe_code, taxable, tax, coin_code
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        for tax_code, values in sorted(taxes_by_type.items()):
            taxable_amount = round(values['taxable'], 2)
            tax_amount = round(values['tax'], 2)
            aliquot = values['aliquot']
            count = values['count']

            # Solo insertar si hay monto de impuesto
            if tax_amount > 0:
                self._log(f"     Insertando impuesto tipo={tax_code}: aliquot={aliquot:.2f}%, taxable={taxable_amount:.2f}, tax={tax_amount:.2f}, ítems={count}", "debug")

                # Insertar en sales_operation_taxes y obtener line
                self.pg_cursor.execute(sql_tax, (
                    correlative,
                    tax_code,
                    aliquot,
                    taxable_amount,
                    tax_amount,
                    1  # tax_type
                ))

                tax_line = self.pg_cursor.fetchone()[0]

                # Insertar en USD ('02')
                self.pg_cursor.execute(sql_tax_coins, (
                    correlative,
                    tax_line,
                    tax_code,
                    taxable_amount,
                    tax_amount,
                    '02'  # USD
                ))

                # Insertar en Bolívares ('01')
                taxable_amount_bcv = round(taxable_amount * bcv_rate, 2)
                tax_amount_bcv = round(tax_amount * bcv_rate, 2)

                self.pg_cursor.execute(sql_tax_coins, (
                    correlative,
                    tax_line,
                    tax_code,
                    taxable_amount_bcv,
                    tax_amount_bcv,
                    '01'  # Bolívares
                ))

        total_types = len([v for v in taxes_by_type.values() if v['tax'] > 0])
        self._log(f"     Insertados {total_types} tipos de impuestos en sales_operation_taxes", "debug")

    def _insertar_sales_operation_coins(self, correlative: int, quote: dict,
                                       total_net_details: float, total_tax_details: float,
                                       total_details: float, discount_amount: float,
                                       total_net_cost: float, total_tax_cost: float,
                                       total_cost: float, total_exempt: float):
        """Insertar monedas de la operación (USD y Bolívares)"""
        self._log(f"     🔝 Iniciando inserción en sales_operation_coins para correlative={correlative}", "debug")

        # Totales del quote (para referencia)
        subtotal = float(quote.get('subtotal', 0))
        tax_amount = float(quote.get('tax_amount', 0))
        total = float(quote.get('total', 0))

        self._log(f"     📊 Montos a procesar: net={total_net_details}, tax={total_tax_details}, total={total_details}, discount={discount_amount}", "debug")

        # SQL para insertar en sales_operation_coins
        sql_coins = """
            INSERT INTO sales_operation_coins (
                main_correlative, coin_code, factor_type, buy_aliquot, sales_aliquot,
                total_net_details, total_tax_details, total_details,
                discount, freight, total_net, total_tax, total,
                credit, cash,
                total_net_cost, total_tax_cost, total_cost,
                total_operation,
                total_retention_tax, total_retention_municipal, total_retention_islr,
                retention_tax_prorration, retention_islr_prorration, retention_municipal_prorration,
                total_exempt
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Insertar en USD (coin_code = '02')
        try:
            self._log(f"     💵 Insertando USD (coin_code='02')...", "debug")

            # Obtener aliquots de la tabla coin
            self.pg_cursor.execute("""
                SELECT buy_aliquot, sales_aliquot, factor_type
                FROM coin
                WHERE code = %s
            """, ('02',))
            result_coin = self.pg_cursor.fetchone()

            if result_coin:
                buy_aliquot_usd = result_coin[0]
                sales_aliquot_usd = result_coin[1]
                factor_type_usd = result_coin[2]
                self._log(f"     ✅ Coin USD encontrado: buy={buy_aliquot_usd}, sales={sales_aliquot_usd}, factor={factor_type_usd}", "debug")
            else:
                # Valores por defecto si no encuentra la moneda
                buy_aliquot_usd = 1.0
                sales_aliquot_usd = 1.0
                factor_type_usd = 1
                self._log(f"     ⚠️ Coin USD NO encontrado, usando defaults", "warning")

            self.pg_cursor.execute(sql_coins, (
                correlative,           # main_correlative
                '02',                 # coin_code (USD)
                factor_type_usd,      # factor_type de la tabla coin
                buy_aliquot_usd,      # buy_aliquot de la tabla coin
                sales_aliquot_usd,    # sales_aliquot de la tabla coin
                total_net_details,    # total_net_details (directo, viene en USD)
                total_tax_details,    # total_tax_details (directo, viene en USD)
                total_details,        # total_details (directo, viene en USD)
                discount_amount,      # discount
                0.0,                  # freight
                total_net_details - discount_amount,  # total_net
                total_tax_details,    # total_tax
                total_details,        # total
                0.0,                  # credit
                0.0,                  # cash
                total_net_cost,       # total_net_cost
                total_tax_cost,       # total_tax_cost
                total_cost,           # total_cost
                0.0,                  # total_operation (SIEMPRE 0)
                0.0,                  # total_retention_tax
                0.0,                  # total_retention_municipal
                0.0,                  # total_retention_islr
                0.0,                  # retention_tax_prorration
                0.0,                  # retention_islr_prorration
                0.0,                  # retention_municipal_prorration
                total_exempt          # total_exempt
            ))
            self._log(f"     ✅ Insertado en sales_operation_coins (USD, buy_aliquot={buy_aliquot_usd}, sales_aliquot={sales_aliquot_usd})", "debug")
        except Exception as e:
            self._log(f"     ❌ Error insertando en sales_operation_coins (USD): {e}", "error")
            import traceback
            self._log(f"     Stack trace: {traceback.format_exc()}", "error")

        # Insertar en Bolívares (coin_code = '01')
        try:
            self._log(f"     🪙 Insertando Bs (coin_code='01')...", "debug")

            # Obtener aliquots de la tabla coin para Bs (para guardar en la tabla)
            self.pg_cursor.execute("""
                SELECT buy_aliquot, sales_aliquot, factor_type
                FROM coin
                WHERE code = %s
            """, ('01',))  # Buscar coin_code='01' en tabla coin
            result_coin_bs = self.pg_cursor.fetchone()

            # Obtener sales_aliquot de USD (para conversión de montos)
            self.pg_cursor.execute("""
                SELECT sales_aliquot
                FROM coin
                WHERE code = %s
            """, ('02',))  # Buscar sales_aliquot de USD para convertir
            result_coin_usd = self.pg_cursor.fetchone()

            if result_coin_bs:
                buy_aliquot_bs = result_coin_bs[0]      # buy_aliquot de Bs
                sales_aliquot_bs = result_coin_bs[1]    # sales_aliquot de Bs
                factor_type_bs = result_coin_bs[2]      # factor_type de Bs
                self._log(f"     ✅ Coin Bs encontrado: buy={buy_aliquot_bs}, sales={sales_aliquot_bs}, factor={factor_type_bs}", "debug")
            else:
                # Valores por defecto si no encuentra la moneda
                buy_aliquot_bs = 1.0
                sales_aliquot_bs = 1.0
                factor_type_bs = 0
                self._log(f"     ⚠️ Coin Bs NO encontrado, usando defaults", "warning")

            # Obtener tasa de conversión de USD
            sales_aliquot_usd = result_coin_usd[0] if result_coin_usd else 1.0
            self._log(f"     📊 Tasa USD para conversión: {sales_aliquot_usd}", "debug")

            # Calcular montos en Bolívares usando sales_aliquot de USD
            total_net_details_bs = round(total_net_details * sales_aliquot_usd, 2)
            total_tax_details_bs = round(total_tax_details * sales_aliquot_usd, 2)
            total_details_bs = round(total_details * sales_aliquot_usd, 2)
            discount_amount_bs = round(discount_amount * sales_aliquot_usd, 2)

            # Calcular costos en Bolívares
            total_net_cost_bs = round(total_net_cost * sales_aliquot_usd, 2)
            total_tax_cost_bs = round(total_tax_cost * sales_aliquot_usd, 2)
            total_cost_bs = round(total_cost * sales_aliquot_usd, 2)
            total_exempt_bs = round(total_exempt * sales_aliquot_usd, 2)

            self.pg_cursor.execute(sql_coins, (
                correlative,               # main_correlative
                '01',                     # coin_code (Bolívares)
                factor_type_bs,           # factor_type de la tabla coin (Bs)
                buy_aliquot_bs,           # buy_aliquot de Bs
                sales_aliquot_bs,         # sales_aliquot de Bs
                total_net_details_bs,     # total_net_details (convertido a Bs)
                total_tax_details_bs,     # total_tax_details (convertido a Bs)
                total_details_bs,         # total_details (convertido a Bs)
                discount_amount_bs,      # discount (convertido a Bs)
                0.0,                      # freight
                total_net_details_bs - discount_amount_bs,  # total_net (convertido a Bs)
                total_tax_details_bs,     # total_tax (convertido a Bs)
                total_details_bs,         # total (convertido a Bs)
                0.0,                      # credit
                0.0,                      # cash
                total_net_cost_bs,        # total_net_cost (convertido a Bs)
                total_tax_cost_bs,        # total_tax_cost (convertido a Bs)
                total_cost_bs,            # total_cost (convertido a Bs)
                0.0,                      # total_operation (SIEMPRE 0)
                0.0,                      # total_retention_tax
                0.0,                      # total_retention_municipal
                0.0,                      # total_retention_islr
                0.0,                      # retention_tax_prorration
                0.0,                      # retention_islr_prorration
                0.0,                      # retention_municipal_prorration
                total_exempt_bs           # total_exempt (convertido a Bs)
            ))
            self._log(f"     ✅ Insertado en sales_operation_coins (Bs, sales_aliquot_bs={sales_aliquot_bs}, tasa_usd={sales_aliquot_usd})", "debug")
        except Exception as e:
            self._log(f"     ❌ Error insertando en sales_operation_coins (Bs): {e}", "error")
            import traceback
            self._log(f"     Stack trace: {traceback.format_exc()}", "error")

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
