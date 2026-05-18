"""
Products Sync Module
Sincronizador de productos de PostgreSQL a API REST
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import BaseSync


def safe_float(value) -> float:
    """
    Convertir valor a float de forma segura.

    Args:
        value: Cualquier valor

    Returns:
        Float o 0.0 si no se puede convertir
    """
    if isinstance(value, memoryview):
        try:
            value = value.tobytes().decode('utf-8')
        except Exception:
            return 0.0
    try:
        return float(value) if value is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


class ProductsSync(BaseSync):
    """
    Sincronizador de productos usando API REST.

    Flujo:
    1. Detecta cambios en tabla 'products' de PostgreSQL
    2. Compara hashes para identificar nuevos/modificados/eliminados
    3. Obtiene mapa de categorías desde la API
    4. Transforma al formato de la API
    5. Envía a la API en lotes
    6. Actualiza sync_hashes

    Uso:
        sync = ProductsSync(
            pg_conn=pg_conn,
            api_client=products_client,
            company_id=27
        )
        sync.execute()
    """

    def __init__(self, pg_conn, api_client, company_id: int, logger=None, categories_map=None):
        """
        Args:
            pg_conn: Conexión a PostgreSQL
            api_client: Instancia de ProductsClient
            company_id: ID de la empresa
            logger: Logger opcional
            categories_map: Mapa de categorías {department_name: category_id} opcional.
                           Si se proporciona, se usa directamente sin consultar la API.
        """
        super().__init__(pg_conn, api_client, company_id, logger)
        self.table_name = 'products'

        # Cache de categorías {department_name: category_id}
        # Puede venir como parámetro o se construye desde la API
        self._categories_map = categories_map

    # =========================================================================
    # DETECCIÓN DE CAMBIOS
    # =========================================================================

    def detect_changes(self) -> Dict[str, List]:
        """
        Detectar cambios en productos comparando hashes.

        Returns:
            Dict con:
                {
                    'nuevos': [(code, unit, description, ...), ...],
                    'modificados': [(code, unit, description, ...), ...],
                    'eliminados': [{'code': 'ABC'}, ...]
                }
        """
        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            # Verificar si hay productos en sync_hashes (primera vez?)
            self.pg_cursor.execute("""
                SELECT COUNT(*)
                FROM sync_hashes
                WHERE table_name = 'products'
                  AND company_id = %s
            """, (self.company_id,))

            count_in_hashes = self.pg_cursor.fetchone()[0]

            # CASO 1: Primera vez - no hay productos en sync_hashes
            if count_in_hashes == 0:
                self.info("🎯 Primera sincronización: obteniendo TODOS los productos")
                self.pg_cursor.execute("""
                    SELECT COUNT(*) FROM products
                """)
                total_products = self.pg_cursor.fetchone()[0]
                self.info(f"   Total productos en PostgreSQL: {total_products}")

                # Obtener todos los productos
                pending_codes = []
                if total_products > 0:
                    self.pg_cursor.execute("SELECT code FROM products")
                    pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            # CASO 2: Sincronización incremental - solo pending_sync
            else:
                # Verificar si hay productos con pending_sync = true
                self.pg_cursor.execute("""
                    SELECT COUNT(*)
                    FROM sync_hashes
                    WHERE table_name = 'products'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                count_pending = self.pg_cursor.fetchone()[0]

                if count_pending == 0:
                    self.info("No hay productos con pending_sync")
                    # NO RETORNAR AQUÍ - Continuar para verificar eliminados

                # Obtener códigos de productos pendientes
                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'products'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            # Continuar solo si hay códigos pendientes para procesar
            # Si no hay, saltar directamente a la detección de eliminados
            if pending_codes:
                # Construir filtro IN para query principal
                placeholders = ','.join(['%s'] * len(pending_codes))

                # Query complejo con todos los joins necesarios
                query = f"""
                    SELECT DISTINCT ON (a.code)
                        a.code,
                        b.unit,
                        a.description,
                        a.short_name,
                        a.department,
                        i.description as department_name,
                        b.product_code,
                        h.description as unidad,
                        COALESCE(c.total_stock, 0) AS stock,
                        a.product_type,
                        a.coin,
                        f.description AS description_coin,
                        COALESCE(b.maximum_price, b.higher_price, 0) AS price,
                        CASE
                            WHEN b.offer_price IS NULL
                            THEN 0
                            ELSE b.offer_price
                        END AS cost,
                        CASE
                            WHEN b.higher_price IS NULL
                            THEN 0
                            ELSE b.higher_price
                        END AS higher_price,
                        CASE
                            WHEN a.minimal_stock IS NULL
                            THEN 0
                            ELSE a.minimal_stock
                        END AS min_stock,
                        CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status,
                        d.image_type,
                        d.product_image,
                        a.sale_tax,
                        e.aliquot,
                        a.buy_tax,
                        g.aliquot AS buy_aliquot,
                        b.unitary_cost,
                        a.allow_decimal
                    FROM products a
                    LEFT JOIN (
                        SELECT product_code, SUM(stock) as total_stock
                        FROM products_stock
                        GROUP BY product_code
                    ) c ON a.code = c.product_code
                    LEFT JOIN products_units b ON a.code = b.product_code
                    LEFT JOIN products_image d ON d.main_code = a.code
                    LEFT JOIN taxes e ON e.code = a.sale_tax
                    LEFT JOIN taxes g ON g.code = a.buy_tax
                    LEFT JOIN coin f ON f.code = a.coin
                    LEFT JOIN units h ON h.code = b.unit
                    LEFT JOIN department i ON a.department = i.code
                    WHERE a.code IN ({placeholders})
                      AND a.code IS NOT NULL
                      AND a.code != ''
                      AND a.product_type <> 'C'
                      AND b.unit != ''
                      AND b.main_unit = true
                    ORDER BY a.code, b.maximum_price DESC
                """

                self.pg_cursor.execute(query, pending_codes)
                productos = self.pg_cursor.fetchall()

                self.info(f"Se recuperaron {len(productos)} productos de PostgreSQL")

                claves_actuales = []

                # Detectar nuevos y modificados
                for producto in productos:
                    if not self.sync_running:
                        break

                    code = producto[0]
                    claves_actuales.append(code)

                    # Generar hash actual
                    hash_actual = self._generar_hash(producto)

                    # Obtener hash guardado
                    hash_guardado = self._obtener_hash_guardado(self.table_name, code)

                    # Extraer coin del producto (índice 10 según el query)
                    coin_actual = producto[10] if len(producto) > 10 else None

                    if hash_guardado is None:
                        # Nuevo
                        cambios['nuevos'].append(producto)
                        self.debug(f"  ✨ NUEVO: {code}")
                    elif hash_guardado != hash_actual:
                        # Modificado
                        cambios['modificados'].append(producto)
                        self.debug(f"  🔄 MODIFICADO: {code}")

                    # Guardar hash actual con last_sync_data (incluye coin)
                    data_sync = {
                        'coin': coin_actual,
                        'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self._guardar_hash(self.table_name, code, hash_actual, data_sync)

            # Detectar eliminados (usando trigger deleted_at)
            self.pg_cursor.execute("""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'products'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
                ORDER BY deleted_at DESC
            """, (self.company_id,))

            eliminados = self.pg_cursor.fetchall()

            for (eliminado,) in eliminados:
                cambios['eliminados'].append({'code': eliminado})
                self.debug(f"  ❌ ELIMINADO: {eliminado}")

            self.pg_conn.commit()

            self.info(
                f"Cambios en productos: {len(cambios['nuevos'])} nuevos, "
                f"{len(cambios['modificados'])} modificados, "
                f"{len(cambios['eliminados'])} eliminados"
            )

        except Exception as e:
            self.error(f"Error detectando cambios en productos: {e}")
            import traceback
            self.error(traceback.format_exc())
            self.pg_conn.rollback()

        return cambios

    # =========================================================================
    # CONVERSIÓN DE MONEDA
    # =========================================================================

    def _obtener_tipo_cambio_ves_usd(self) -> Optional[float]:
        """
        Obtener tipo de cambio VES → USD desde la tabla coin.

        Returns:
            Tipo de cambio (sales_aliquot de coin '02') o None si no está disponible
        """
        try:
            # Buscar el tipo de cambio en la tabla coin
            self.pg_cursor.execute("""
                SELECT sales_aliquot
                FROM coin
                WHERE code = '02'
                LIMIT 1
            """)

            result = self.pg_cursor.fetchone()
            if result and result[0]:
                tipo_cambio = float(result[0])
                self.info(f"💱 Tipo de cambio VES→USD: {tipo_cambio:.2f}")
                return tipo_cambio

            # Valor por defecto si no se encuentra
            self.warning("⚠️  No se pudo obtener tipo de cambio de tabla coin, usando 36.5 por defecto")
            return 36.5

        except Exception as e:
            self.error(f"Error obteniendo tipo de cambio: {e}")
            return 36.5  # Valor por defecto

    def _convertir_ves_a_usd(self, monto: float, tipo_cambio: float) -> float:
        """
        Convertir monto de VES a USD.

        Args:
            monto: Monto en VES
            tipo_cambio: Tipo de cambio (ej: 36.5 VES por USD)

        Returns:
            Monto en USD
        """
        return round(monto / tipo_cambio, 4)

    def _convertir_usd_a_ves(self, monto: float, tipo_cambio: float) -> float:
        """
        Convertir monto de USD a VES.

        Args:
            monto: Monto en USD
            tipo_cambio: Tipo de cambio (ej: 36.5 VES por USD)

        Returns:
            Monto en VES
        """
        return round(monto * tipo_cambio, 2)

    # =========================================================================
    # TRANSFORMACIÓN
    # =========================================================================

    def transform_to_api(self, pg_record: tuple) -> Dict[str, Any]:
        """
        Transformar registro de PostgreSQL a formato de API REST.

        Args:
            pg_record: Tuple con todos los campos del JOIN de productos

        Returns:
            Dict con formato esperado por la API:
                {
                    'code': 'ABC123',
                    'name': 'Producto Ejemplo',
                    'description': 'Descripción',
                    'price': 150.00,
                    'cost': 100.00,
                    'higher_price': 180.00,
                    'coin': 'USD',
                    'description_coin': 'Dólares americanos',
                    'stock': 50,
                    'min_stock': 10,
                    'category_id': 5,
                    'status': 'active',
                    'weight': 1.0,
                    'unitary_cost': 100.00,
                    'buy_tax': '0',
                    'buy_aliquot': 0.0,
                    'sale_tax': '16',
                    'aliquot': 16.0
                }
        """
        # Extraer campos del tuple
        (
            code,                    # 0
            unit,                    # 1
            description,             # 2
            short_name,              # 3
            department,              # 4 - Código de departamento
            department_name,         # 5 - Nombre de departamento (para mapear a categoría)
            product_code,            # 6
            unidad,                  # 7
            stock,                   # 8
            product_type,            # 9
            coin,                    # 10
            description_coin,        # 11
            price,                   # 12
            cost,                    # 13
            higher_price,            # 14
            min_stock,               # 15
            status,                  # 16
            image_type,              # 17
            product_image,           # 18
            sale_tax,                # 19
            aliquot,                 # 20
            buy_tax,                 # 21
            buy_aliquot,             # 22
            unitary_cost,            # 23
            allow_decimal            # 24
        ) = pg_record

        # =====================================================================
        # CONVERTIR PRECIOS SI ESTÁN EN VES ('01')
        # =====================================================================
        tipo_cambio = None

        # Mapeo de códigos de moneda (PostgreSQL usa '01'/'02' o 'USD'/'VES')
        coin_map = {
            '01': 'VES',
            '02': 'USD',
            'VES': 'VES',
            'USD': 'USD'
        }

        # Normalizar código de moneda
        coin_normalizado = coin_map.get(coin, coin) if coin else 'USD'

        # Siempre convertir de VES a USD cuando coin = '01' o 'VES'
        if coin_normalizado in ['VES', '01']:
            self.info(f"  💱 Producto en VES detectado: {code} - Convirtiendo a USD")

            # Obtener tipo de cambio
            tipo_cambio = self._obtener_tipo_cambio_ves_usd()

            if tipo_cambio:
                self.info(f"     💱 Convirtiendo precios VES→USD (tasa: {tipo_cambio:.2f})")
                price = self._convertir_ves_a_usd(safe_float(price), tipo_cambio)
                cost = self._convertir_ves_a_usd(safe_float(cost), tipo_cambio)
                higher_price = self._convertir_ves_a_usd(safe_float(higher_price), tipo_cambio)
                unitary_cost = self._convertir_ves_a_usd(safe_float(unitary_cost), tipo_cambio)
                self.info(f"     → Price: {price:.4f} USD | Cost: {cost:.4f} USD")

                # Cambiar coin a USD para enviar a la API
                coin_normalizado = 'USD'

        # =====================================================================
        # CONTINUAR CON TRANSFORMACIÓN NORMAL
        # =====================================================================

        # category_id es el código del department de PostgreSQL
        # Ej: 'GENERAL', 'ELECTRONICA', 'ALIMENTOS'
        category_id = department if department else 'GENERAL'

        # Log para diagnóstico: mostrar category_id asignado
        self.debug(f"   📦 Producto '{code}' → department_code: '{department}' → category_id: '{category_id}'")

        # Construir nombre (usar short_name si hay, sino description)
        name = (short_name[:255] if short_name else '')[:255]
        if not name:
            name = (description[:255] if description else '')[:255]

        # Mapeo de moneda a descripción
        coin_descriptions = {
            'USD': 'Dólares americanos',
            'VES': 'Bolívares',
            'EUR': 'Euros',
            '': 'Dólares americanos',
            None: 'Dólares americanos'
        }

        # Limpiar description_coin: si es N/A, vacío o None, usar el mapeo
        valid_description_coin = description_coin
        if not description_coin or description_coin.strip() in ['', 'N/A', 'N/A']:
            valid_description_coin = coin_descriptions.get(coin, 'Dólares americanos')

        # Codificar imagen en base64 para enviar en JSON
        product_image_encoded = None
        if product_image:
            import base64
            # Manejar bytes o memoryview
            if isinstance(product_image, (bytes, memoryview)):
                # Si es memoryview, convertir a bytes primero
                if isinstance(product_image, memoryview):
                    product_image = product_image.tobytes()

                # Log para diagnóstico
                image_bytes_len = len(product_image)
                self.debug(f"   🖼️ Imagen detectada para {code}: {image_bytes_len} bytes, tipo: {type(product_image).__name__}")

                product_image_encoded = base64.b64encode(product_image).decode('utf-8')

                # Log del resultado de codificación
                self.debug(f"   📦 Imagen codificada: {len(product_image_encoded)} caracteres (base64)")
                self.debug(f"   🏷️ image_type: {image_type}")
                # Mostrar primeros 50 chars del base64 para verificar
                self.debug(f"   🔍 Preview base64: {product_image_encoded[:50]}...")
            else:
                self.warning(f"   ⚠️ Tipo de imagen no soportado para {code}: {type(product_image)}")

        return {
            'code': code,
            'name': name,
            'description': description if description else None,
            'price': float(safe_float(price)),
            'cost': float(safe_float(cost)),
            'higher_price': float(safe_float(higher_price)),
            'coin': coin if coin else 'USD',
            'description_coin': valid_description_coin,
            'stock': float(safe_float(stock)),
            'min_stock': float(safe_float(min_stock)),
            'category_id': category_id,
            'status': status,
            'weight': 1.0,  # Valor default (no viene de PostgreSQL)
            'unitary_cost': float(safe_float(unitary_cost)),
            'buy_tax': str(buy_tax) if buy_tax else '0',
            'buy_aliquot': float(safe_float(buy_aliquot)),
            'sale_tax': str(sale_tax) if sale_tax else '16',
            'aliquot': float(safe_float(aliquot)),
            'product_type': product_type if product_type else 'P',  # Tipo de producto (P=Producto, C=Combo, etc.)
            'unidad': unidad if unidad else 'Unidad',  # Descripción de la unidad de medida
            'allow_decimal': bool(allow_decimal) if allow_decimal is not None else False,  # Permite decimales (booleano)
            'image_type': image_type,
            'product_image': product_image_encoded
        }

    def _get_category_id(self, department_name: str) -> int:
        """
        Obtener category_id para un department_name.

        Usa el mapa proporcionado o lo construye desde la API.

        Args:
            department_name: Nombre de departamento de PostgreSQL

        Returns:
            ID de la categoría o 1 si no encuentra
        """
        if self._categories_map is None:
            # Construir mapa de categorías desde la API
            self.info("📋 Building categories map from API...")
            self._categories_map = self.api_client.get_categories_map(self.company_id)
            self.info(f"📋 Categories map built with {len(self._categories_map)} entries")

            # Mostrar categorías disponibles para diagnóstico
            if self._categories_map:
                self.info(f"📋 Available categories in API:")
                for name, cat_id in sorted(self._categories_map.items()):
                    self.info(f"   - '{name}' → ID: {cat_id}")
            else:
                self.warning("⚠️ No categories found in API! All products will fail!")

        # Buscar category_id por nombre (department_name)
        category_id = self._categories_map.get(department_name)

        if not category_id:
            self.warning(
                f"⚠️ Category NOT FOUND for department '{department_name}'"
            )
            self.warning(
                f"⚠️ Using default category_id=1 (may not exist in API)"
            )
            self.warning(
                f"⚠️ Available categories: {list(self._categories_map.keys())[:10]}"
            )
            return 1

        return category_id

    # =========================================================================
    # SINCRONIZACIÓN A API
    # =========================================================================

    def sync_to_api(self, changes: Dict[str, List]) -> bool:
        """
        Sincronizar productos a la API REST con reintentos automáticos.

        Args:
            changes: Dict con nuevos y modificados

        Returns:
            True si exitoso, False si hubo errores
        """
        # Combinar nuevos y modificados
        todos_los_products = changes.get('nuevos', []) + changes.get('modificados', [])

        if not todos_los_products:
            self.info("No hay productos para sincronizar")
            return True

        self.info(f"Sincronizando {len(todos_los_products)} productos a la API...")

        # Transformar a formato de API
        products_api = [
            self.transform_to_api(prod)
            for prod in todos_los_products
        ]

        # Reintentos si falla todo el lote
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 2s, 4s, 8s
                    self.warning(
                        f"⚠️ Error sincronizando productos. "
                        f"Reintentando en {wait_time}s... (intento {attempt + 1}/{max_retries})"
                    )
                    import time
                    time.sleep(wait_time)

                # Enviar a API en lotes
                result = self.api_client.sync_batch(
                    company_id=self.company_id,
                    products=products_api
                )

                # Actualizar estadísticas
                self.stats['created'] = result.get('created', 0)
                self.stats['updated'] = result.get('updated', 0)
                self.stats['errors'] = result.get('errors', 0)

                if self.stats['errors'] == 0:
                    self.info(
                        f"✅ Productos sincronizados: {self.stats['created']} creados, "
                        f"{self.stats['updated']} actualizados"
                    )
                    return True
                else:
                    # Si hay errores en los datos, mostrar detalles
                    self.error(f"❌ Errores sincronizando productos: {self.stats['errors']}")

                    # Mostrar detalles de errores
                    error_details = result.get('error_details', [])
                    if error_details:
                        self.error(f"❌ Detalles de errores ({len(error_details)} productos fallaron):")
                        for idx, error in enumerate(error_details[:20], 1):  # Mostrar primeros 20
                            if isinstance(error, dict):
                                code = error.get('code', error.get('product', {}).get('code', 'N/A'))
                                err_msg = error.get('error', error.get('message', 'Unknown error'))

                                # Si es error de categoría, mostrar el category_id enviado
                                extra_info = ""
                                if 'category' in err_msg.lower() and 'product' in error:
                                    product_data = error.get('product', {})
                                    sent_category_id = product_data.get('category_id', 'N/A')
                                    department = product_data.get('department', 'N/A')
                                    extra_info = f" [enviado category_id={sent_category_id} para department='{department}']"

                                self.error(f"   {idx}. ❌ Producto '{code}': {err_msg}{extra_info}")
                            else:
                                self.error(f"   {idx}. ❌ {error}")

                        if len(error_details) > 20:
                            self.error(f"   ... y {len(error_details) - 20} errores más")

                    return False

            except Exception as e:
                # Verificar si es un error que vale la pena reintentar (errores 5xx, timeout, etc)
                error_str = str(e).lower()
                should_retry = any([
                    '500' in error_str or '502' in error_str or '503' in error_str or '504' in error_str,
                    'timeout' in error_str,
                    'connection' in error_str,
                    'server error' in error_str,
                    'temporarily' in error_str
                ])

                # Último intento falló
                if attempt >= max_retries - 1:
                    self.error(f"❌ Error sincronizando productos después de {max_retries} intentos: {e}")
                    import traceback
                    self.error(traceback.format_exc())
                    return False

                # Si no es un error recuperable, no reintentar
                if not should_retry:
                    self.error(f"❌ Error sincronizando productos (no recuperable): {e}")
                    import traceback
                    self.error(traceback.format_exc())
                    return False

                # Para otros errores, el loop continuará y reintentará
                continue

    # =========================================================================
    # ELIMINACIÓN
    # =========================================================================

    def delete_from_api(self, deleted_items: List) -> None:
        """
        Eliminar productos de la API REST.

        Args:
            deleted_items: Lista de dicts con {'code': 'ABC'}
        """
        if not deleted_items:
            return

        self.info(f"Eliminando {len(deleted_items)} productos de la API...")

        # Extraer códigos
        codes = [item['code'] for item in deleted_items]

        try:
            result = self.api_client.delete_batch(
                company_id=self.company_id,
                codes=codes
            )

            deleted = result.get('deleted', 0)
            self.stats['deleted'] = deleted

            self.info(f"✅ Eliminados {deleted} productos de la API")

            # Limpiar sync_hashes (eliminar registros con deleted_at)
            self.pg_cursor.execute("""
                DELETE FROM sync_hashes
                WHERE table_name = 'products'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
            """, (self.company_id,))
            filas_limpias = self.pg_cursor.rowcount
            self.pg_conn.commit()
            self.info(f"✅ Limpiados {filas_limpias} registros de sync_hashes")

        except Exception as e:
            self.error(f"❌ Error eliminando productos: {e}")

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def _extract_record_key(self, registro) -> str:
        """
        Extraer record_key de un registro de producto.

        Args:
            registro: Tuple (code, ...) o dict

        Returns:
            El code del producto
        """
        if isinstance(registro, tuple):
            return str(registro[0])  # code
        elif isinstance(registro, dict):
            return str(registro.get('code', ''))
        return str(registro)

    def _get_table_name(self) -> str:
        """Retornar nombre de la tabla para sync_hashes"""
        return 'products'
