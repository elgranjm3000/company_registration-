"""
Stores Sync Module
Sincronizador de stores de PostgreSQL a API REST
"""

from typing import Dict, List, Any
from .base import BaseSync


class StoresSync(BaseSync):
    """
    Sincronizador de stores usando API REST.

    Flujo:
    1. Detecta cambios en tabla 'store' de PostgreSQL
    2. Compara hashes para identificar nuevos/modificados/eliminados
    3. Transforma al formato de la API
    4. Envía a la API en lotes
    5. Actualiza sync_hashes

    Uso:
        sync = StoresSync(
            pg_conn=pg_conn,
            api_client=stores_client,
            company_id=27
        )
        sync.execute()
    """

    def __init__(self, pg_conn, api_client, company_id: int, logger=None):
        super().__init__(pg_conn, api_client, company_id, logger)
        self.table_name = 'stores'

    def detect_changes(self) -> Dict[str, List]:
        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            self.pg_cursor.execute("""
                SELECT COUNT(*)
                FROM sync_hashes
                WHERE table_name = 'stores'
                  AND company_id = %s
            """, (self.company_id,))

            count_in_hashes = self.pg_cursor.fetchone()[0]

            if count_in_hashes == 0:
                self.info("Primera sincronización: obteniendo TODOS los stores")
                self.pg_cursor.execute("SELECT code FROM store")
                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]
            else:
                self.pg_cursor.execute("""
                    SELECT COUNT(*)
                    FROM sync_hashes
                    WHERE table_name = 'stores'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                count_pending = self.pg_cursor.fetchone()[0]

                if count_pending == 0:
                    self.pg_cursor.execute("""
                        SELECT record_key
                        FROM sync_hashes
                        WHERE table_name = 'stores'
                          AND company_id = %s
                          AND deleted_at IS NOT NULL
                        ORDER BY deleted_at DESC
                    """, (self.company_id,))

                    eliminados = self.pg_cursor.fetchall()
                    for (eliminado,) in eliminados:
                        cambios['eliminados'].append({'code': eliminado})

                    if eliminados:
                        self.info(f"{len(eliminados)} stores eliminados detectados")
                    else:
                        self.info("No hay stores con pending_sync")
                    return cambios

                self.info(f"Se encontraron {count_pending} stores con pending_sync")

                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'stores'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            if not pending_codes:
                return cambios

            placeholders = ','.join(['%s'] * len(pending_codes))

            query = f"""
                SELECT code, description
                FROM store
                WHERE code IN ({placeholders})
                  AND code IS NOT NULL AND code != ''
                ORDER BY code
            """

            self.pg_cursor.execute(query, pending_codes)
            stores = self.pg_cursor.fetchall()

            self.info(f"Se recuperaron {len(stores)} stores de PostgreSQL")

            for store in stores:
                if not self.sync_running:
                    break

                code = store[0]
                hash_actual = self._generar_hash(store)
                hash_guardado = self._obtener_hash_guardado(self.table_name, code)

                if hash_guardado is None:
                    cambios['nuevos'].append(store)
                elif hash_guardado != hash_actual:
                    cambios['modificados'].append(store)

                cambios.setdefault('_hashes', []).append({
                    'code': code,
                    'hash': hash_actual,
                })

            self.pg_cursor.execute("""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'stores'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
                ORDER BY deleted_at DESC
            """, (self.company_id,))

            for (eliminado,) in self.pg_cursor.fetchall():
                cambios['eliminados'].append({'code': eliminado})

            self.pg_conn.commit()

            self.info(
                f"Cambios en stores: {len(cambios['nuevos'])} nuevos, "
                f"{len(cambios['modificados'])} modificados, "
                f"{len(cambios['eliminados'])} eliminados"
            )

        except Exception as e:
            self.error(f"Error detectando cambios en stores: {e}")
            import traceback
            self.error(traceback.format_exc())
            self.pg_conn.rollback()

        return cambios

    def transform_to_api(self, pg_record: tuple) -> Dict[str, Any]:
        code, description = pg_record

        return {
            'code': code,
            'description': description if description else ''
        }

    def sync_to_api(self, changes: Dict[str, List]) -> bool:
        todos = changes.get('nuevos', []) + changes.get('modificados', [])

        if not todos:
            self.info("No hay stores para sincronizar")
            return True

        self.info(f"Sincronizando {len(todos)} stores a la API...")

        stores_api = [self.transform_to_api(s) for s in todos]

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    import time
                    time.sleep(2 ** attempt)

                result = self.api_client.sync_batch(
                    company_id=self.company_id,
                    stores=stores_api
                )

                self.stats['created'] = result.get('created', 0)
                self.stats['updated'] = result.get('updated', 0)
                self.stats['errors'] = result.get('errors', 0)

                if self.stats['errors'] == 0:
                    self.info(f"Stores sincronizados: {self.stats['created']} creados, "
                              f"{self.stats['updated']} actualizados")
                    return True
                else:
                    self.error(f"Errores sincronizando stores: {self.stats['errors']}")
                    return False

            except Exception as e:
                if attempt >= max_retries - 1:
                    self.error(f"Error sincronizando stores: {e}")
                    return False

        return False

    def delete_from_api(self, deleted_items: List) -> None:
        if not deleted_items:
            return

        self.info(f"Eliminando {len(deleted_items)} stores de la API...")
        codes = [item['code'] for item in deleted_items]

        try:
            result = self.api_client.delete_batch(
                company_id=self.company_id,
                codes=codes
            )

            self.stats['deleted'] = result.get('deleted', 0)
            self.info(f"Eliminados {self.stats['deleted']} stores de la API")

            self.pg_cursor.execute("""
                DELETE FROM sync_hashes
                WHERE table_name = 'stores'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
            """, (self.company_id,))
            self.pg_conn.commit()

        except Exception as e:
            self.error(f"Error eliminando stores: {e}")

    def _extract_record_key(self, registro) -> str:
        if isinstance(registro, tuple):
            return str(registro[0])
        elif isinstance(registro, dict):
            return str(registro.get('code', ''))
        return str(registro)

    def _get_table_name(self) -> str:
        return 'stores'
