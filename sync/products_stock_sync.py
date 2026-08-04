"""
Products Stock Sync Module
Sincronizador de stock de productos de PostgreSQL a API REST
"""

from typing import Dict, List, Any
from .base import BaseSync


class ProductsStockSync(BaseSync):
    """
    Sincronizador de products-stock usando API REST.

    Flujo:
    1. Detecta cambios en tabla 'product_stock' de PostgreSQL
    2. Compara hashes para identificar nuevos/modificados/eliminados
    3. Transforma al formato de la API
    4. Envía a la API en lotes
    5. Actualiza sync_hashes

    Uso:
        sync = ProductsStockSync(
            pg_conn=pg_conn,
            api_client=products_stock_client,
            company_id=27
        )
        sync.execute()
    """

    def __init__(self, pg_conn, api_client, company_id: int, logger=None):
        super().__init__(pg_conn, api_client, company_id, logger)
        self.table_name = 'products-stock'

    def _make_record_key(self, product_code: str, store: str, locations: str) -> str:
        """Crea una clave compuesta para el registro."""
        return f"{product_code}|{store}|{locations}"

    def detect_changes(self) -> Dict[str, List]:
        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            self.pg_cursor.execute("""
                SELECT COUNT(*)
                FROM sync_hashes
                WHERE table_name = 'products-stock'
                  AND company_id = %s
            """, (self.company_id,))

            count_in_hashes = self.pg_cursor.fetchone()[0]

            if count_in_hashes == 0:
                self.info("Primera sincronización: obteniendo TODOS los stocks")
                self.pg_cursor.execute("""
                    SELECT product_code, store, locations
                    FROM products_stock
                    WHERE product_code IS NOT NULL AND product_code != ''
                """)
                rows = self.pg_cursor.fetchall()
                pending_codes = [self._make_record_key(r[0], r[1], r[2] or '') for r in rows]
            else:
                self.pg_cursor.execute("""
                    SELECT COUNT(*)
                    FROM sync_hashes
                    WHERE table_name = 'products-stock'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                count_pending = self.pg_cursor.fetchone()[0]

                if count_pending == 0:
                    self.pg_cursor.execute("""
                        SELECT record_key
                        FROM sync_hashes
                        WHERE table_name = 'products-stock'
                          AND company_id = %s
                          AND deleted_at IS NOT NULL
                        ORDER BY deleted_at DESC
                    """, (self.company_id,))

                    for (eliminado,) in self.pg_cursor.fetchall():
                        cambios['eliminados'].append({'code': eliminado})

                    if cambios['eliminados']:
                        self.info(f"{len(cambios['eliminados'])} stocks eliminados detectados")
                    else:
                        self.info("No hay stocks con pending_sync")
                    return cambios

                self.info(f"Se encontraron {count_pending} stocks con pending_sync")

                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'products-stock'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            if not pending_codes:
                return cambios

            # Obtener todos los stocks y filtrar por pending_codes
            self.pg_cursor.execute("""
                SELECT product_code, store, locations, stock, ordered_stock, committed_stock
                FROM products_stock
                WHERE product_code IS NOT NULL AND product_code != ''
                ORDER BY product_code, store, locations
            """)

            all_stocks = self.pg_cursor.fetchall()

            # Filtrar los que están en pending_codes
            pending_set = set(pending_codes)
            stocks = [
                s for s in all_stocks
                if self._make_record_key(s[0], s[1], s[2] or '') in pending_set
            ]

            self.info(f"Se recuperaron {len(stocks)} stocks de PostgreSQL")

            for stock in stocks:
                if not self.sync_running:
                    break

                product_code, store, locations = stock[0], stock[1], stock[2] or ''
                code = self._make_record_key(product_code, store, locations)

                hash_actual = self._generar_hash(stock)
                hash_guardado = self._obtener_hash_guardado(self.table_name, code)

                if hash_guardado is None:
                    cambios['nuevos'].append(stock)
                elif hash_guardado != hash_actual:
                    cambios['modificados'].append(stock)

                cambios.setdefault('_hashes', []).append({
                    'code': code,
                    'hash': hash_actual,
                })

            self.pg_cursor.execute("""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'products-stock'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
                ORDER BY deleted_at DESC
            """, (self.company_id,))

            for (eliminado,) in self.pg_cursor.fetchall():
                cambios['eliminados'].append({'code': eliminado})

            self.pg_conn.commit()

            self.info(
                f"Cambios en stocks: {len(cambios['nuevos'])} nuevos, "
                f"{len(cambios['modificados'])} modificados, "
                f"{len(cambios['eliminados'])} eliminados"
            )

        except Exception as e:
            self.error(f"Error detectando cambios en stocks: {e}")
            import traceback
            self.error(traceback.format_exc())
            self.pg_conn.rollback()

        return cambios

    def transform_to_api(self, pg_record: tuple) -> Dict[str, Any]:
        (
            product_code,
            store,
            locations,
            stock,
            ordered_stock,
            committed_stock
        ) = pg_record

        return {
            'product_code': product_code if product_code else '',
            'store': store if store else '',
            'locations': locations if locations else '',
            'stock': int(stock) if stock else 0,
            'ordered_stock': int(ordered_stock) if ordered_stock else 0,
            'committed_stock': int(committed_stock) if committed_stock else 0
        }

    def sync_to_api(self, changes: Dict[str, List]) -> bool:
        todos = changes.get('nuevos', []) + changes.get('modificados', [])

        if not todos:
            self.info("No hay stocks para sincronizar")
            return True

        self.info(f"Sincronizando {len(todos)} stocks a la API...")

        stocks_api = [self.transform_to_api(s) for s in todos]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import time
                    time.sleep(2 ** attempt)

                result = self.api_client.sync_batch(
                    company_id=self.company_id,
                    stocks=stocks_api
                )

                self.stats['created'] = result.get('created', 0)
                self.stats['updated'] = result.get('updated', 0)
                self.stats['errors'] = result.get('errors', 0)

                if self.stats['errors'] == 0:
                    self.info(f"Stocks sincronizados: {self.stats['created']} creados, "
                              f"{self.stats['updated']} actualizados")
                    return True
                else:
                    self.error(f"Errores sincronizando stocks: {self.stats['errors']}")
                    return False

            except Exception as e:
                if attempt >= max_retries - 1:
                    self.error(f"Error sincronizando stocks: {e}")
                    return False

        return False

    def delete_from_api(self, deleted_items: List) -> None:
        if not deleted_items:
            return

        self.info(f"Eliminando {len(deleted_items)} stocks de la API...")
        codes = [item['code'] for item in deleted_items]

        try:
            result = self.api_client.delete_batch(
                company_id=self.company_id,
                codes=codes
            )

            self.stats['deleted'] = result.get('deleted', 0)
            self.info(f"Eliminados {self.stats['deleted']} stocks de la API")

            self.pg_cursor.execute("""
                DELETE FROM sync_hashes
                WHERE table_name = 'products-stock'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
            """, (self.company_id,))
            self.pg_conn.commit()

        except Exception as e:
            self.error(f"Error eliminando stocks: {e}")

    def _extract_record_key(self, registro) -> str:
        if isinstance(registro, tuple):
            return self._make_record_key(
                str(registro[0]),
                str(registro[1]),
                str(registro[2] or '')
            )
        elif isinstance(registro, dict):
            return self._make_record_key(
                str(registro.get('product_code', '')),
                str(registro.get('store', '')),
                str(registro.get('locations', ''))
            )
        return str(registro)

    def _get_table_name(self) -> str:
        return 'products-stock'
