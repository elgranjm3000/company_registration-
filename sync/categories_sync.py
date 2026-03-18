"""
Categories Sync Module
Sincronizador de categorías de PostgreSQL a API REST
"""

from typing import Dict, List, Any
from .base import BaseSync


class CategoriesSync(BaseSync):
    """
    Sincronizador de categorías usando API REST.

    Flujo:
    1. Detecta cambios en tabla 'department' de PostgreSQL
    2. Compara hashes para identificar nuevos/modificados/eliminados
    3. Transforma al formato de la API
    4. Envía a la API en lotes
    5. Actualiza sync_hashes

    Uso:
        sync = CategoriesSync(
            pg_conn=pg_conn,
            api_client=categories_client,
            company_id=27
        )
        sync.execute()
    """

    def __init__(self, pg_conn, api_client, company_id: int, logger=None):
        """
        Args:
            pg_conn: Conexión a PostgreSQL
            api_client: Instancia de CategoriesClient
            company_id: ID de la empresa
            logger: Logger opcional
        """
        super().__init__(pg_conn, api_client, company_id, logger)
        self.table_name = 'categories'

        # Mapa de categorías {name: id} poblado después del sync
        self.categories_map = {}

    # =========================================================================
    # DETECCIÓN DE CAMBIOS
    # =========================================================================

    def detect_changes(self) -> Dict[str, List]:
        """
        Detectar cambios en categorías comparando hashes.

        Returns:
            Dict con:
                {
                    'nuevos': [(code, description), ...],
                    'modificados': [(code, description), ...],
                    'eliminados': [{'code': 'ABC'}, ...]
                }
        """
        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            # Obtener todas las categorías desde PostgreSQL
            self.pg_cursor.execute("""
                SELECT code, description
                FROM department
                WHERE code IS NOT NULL AND code != ''
                ORDER BY code
            """)

            categories = self.pg_cursor.fetchall()

            if not categories:
                self.warning("No se encontraron categorías en PostgreSQL")
                return cambios

            self.info(f"Se encontraron {len(categories)} categorías en PostgreSQL")

            claves_actuales = []

            # Detectar nuevos y modificados
            for idx, category in enumerate(categories, 1):
                if not self.sync_running:
                    break

                code = category[0]
                claves_actuales.append(code)

                # Generar hash actual
                hash_actual = self._generar_hash(category)

                # Obtener hash guardado
                hash_guardado = self._obtener_hash_guardado(self.table_name, code)

                if hash_guardado is None:
                    # Nuevo
                    cambios['nuevos'].append(category)
                    self.debug(f"  ✨ NUEVO: {code}")
                elif hash_guardado != hash_actual:
                    # Modificado
                    cambios['modificados'].append(category)
                    self.debug(f"  🔄 MODIFICADO: {code}")

                # Guardar hash actual
                self._guardar_hash(self.table_name, code, hash_actual)

            # Detectar eliminados (están en sync_hashes pero no en PostgreSQL)
            if claves_actuales:
                placeholders = ','.join(['%s'] * len(claves_actuales))

                self.pg_cursor.execute(f"""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = %s
                      AND company_id = %s
                      AND record_key NOT IN ({placeholders})
                """, [self.table_name, self.company_id] + claves_actuales)

                eliminados = self.pg_cursor.fetchall()

                for (eliminado,) in eliminados:
                    cambios['eliminados'].append({'code': eliminado})
                    self.debug(f"  ❌ ELIMINADO: {eliminado}")

            self.pg_conn.commit()

            self.info(
                f"Cambios en categorías: {len(cambios['nuevos'])} nuevos, "
                f"{len(cambios['modificados'])} modificados, "
                f"{len(cambios['eliminados'])} eliminados"
            )

        except Exception as e:
            self.error(f"Error detectando cambios en categorías: {e}")
            self.pg_conn.rollback()

        return cambios

    # =========================================================================
    # TRANSFORMACIÓN
    # =========================================================================

    def transform_to_api(self, pg_record: tuple) -> Dict[str, Any]:
        """
        Transformar registro de PostgreSQL a formato de API REST.

        Args:
            pg_record: Tuple (code, description) de department

        Returns:
            Dict con formato esperado por la API:
                {
                    'name': 'Electrónica',
                    'description': 'Productos electrónicos',
                    'status': 'active'
                }
        """
        code, description = pg_record

        return {
            'name': code,
            'description': description if description else None,
            'status': 'active'
        }

    # =========================================================================
    # SINCRONIZACIÓN A API
    # =========================================================================

    def sync_to_api(self, changes: Dict[str, List]) -> bool:
        """
        Sincronizar categorías a la API REST con reintentos automáticos.

        Args:
            changes: Dict con nuevos y modificados

        Returns:
            True si exitoso, False si hubo errores
        """
        # Combinar nuevos y modificados
        todos_los_categories = changes.get('nuevos', []) + changes.get('modificados', [])

        if not todos_los_categories:
            self.info("No hay categorías para sincronizar")
            return True

        self.info(f"Sincronizando {len(todos_los_categories)} categorías a la API...")

        # Transformar a formato de API
        categories_api = [
            self.transform_to_api(cat)
            for cat in todos_los_categories
        ]

        # Mostrar categorías que se sincronizarán
        self.info(f"📋 Categories to sync ({len(categories_api)}):")
        for cat in categories_api[:20]:  # Mostrar primeras 20
            self.info(f"   - '{cat['name']}' → {cat.get('description', 'No description')}")
        if len(categories_api) > 20:
            self.info(f"   ... and {len(categories_api) - 20} more")

        # Reintentos si falla todo el lote
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 2s, 4s, 8s
                    self.warning(
                        f"⚠️ Error sincronizando categorías. "
                        f"Reintentando en {wait_time}s... (intento {attempt + 1}/{max_retries})"
                    )
                    import time
                    time.sleep(wait_time)

                # Enviar a API en lotes
                result = self.api_client.sync_batch(
                    company_id=self.company_id,
                    categories=categories_api
                )

                # Actualizar estadísticas
                self.stats['created'] = result.get('created', 0)
                self.stats['updated'] = result.get('updated', 0)
                self.stats['errors'] = result.get('errors', 0)

                if self.stats['errors'] == 0:
                    self.info(
                        f"✅ Categorías sincronizadas: {self.stats['created']} creadas, "
                        f"{self.stats['updated']} actualizadas"
                    )

                    # Capturar el mapa de categorías desde el response de la API
                    # La API retorna las categorías con sus IDs en 'data'
                    sync_data = result.get('data', [])

                    if sync_data:
                        # Construir mapa {name: id} desde las categorías sincronizadas
                        self.categories_map = {
                            cat['name']: cat['id']
                            for cat in sync_data
                            if 'name' in cat and 'id' in cat
                        }

                        self.info(f"📋 Categories map construido con {len(self.categories_map)} entradas desde sync")

                        # Mostrar mapa para diagnóstico
                        if self.categories_map:
                            self.info(f"📋 Mapa de categorías (department → category_id):")
                            for name, cat_id in sorted(self.categories_map.items()):
                                self.info(f"   '{name}' → ID: {cat_id}")
                    else:
                        self.warning("⚠️ La API no retornó 'data' con las categorías, usando GET fallback")
                        # Fallback: obtener el mapa vía GET
                        self.categories_map = self.api_client.get_categories_map(self.company_id)

                    return True
                else:
                    # Si hay errores en los datos, mostrar detalles
                    self.error(f"❌ Errores sincronizando categorías: {self.stats['errors']}")

                    # Mostrar detalles de errores
                    error_details = result.get('error_details', [])
                    if error_details:
                        self.error(f"❌ Detalles de errores ({len(error_details)} categorías fallaron):")
                        for idx, error in enumerate(error_details[:20], 1):
                            if isinstance(error, dict):
                                name = error.get('name', error.get('category', {}).get('name', 'N/A'))
                                err_msg = error.get('error', error.get('message', 'Unknown error'))
                                self.error(f"   {idx}. ❌ Categoría '{name}': {err_msg}")
                            else:
                                self.error(f"   {idx}. ❌ {error}")

                        if len(error_details) > 20:
                            self.error(f"   ... y {len(error_details) - 20} errores más")

                    return False

            except Exception as e:
                # Verificar si es un error que vale la pena reintentar
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
                    self.error(f"❌ Error sincronizando categorías después de {max_retries} intentos: {e}")
                    import traceback
                    self.error(traceback.format_exc())
                    return False

                # Si no es un error recuperable, no reintentar
                if not should_retry:
                    self.error(f"❌ Error sincronizando categorías (no recuperable): {e}")
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
        Eliminar categorías de la API REST.

        Args:
            deleted_items: Lista de dicts con {'code': 'ABC'}
        """
        if not deleted_items:
            return

        self.info(f"Eliminando {len(deleted_items)} categorías de la API...")

        # Extraer nombres (codes)
        nombres = [item['code'] for item in deleted_items]

        try:
            result = self.api_client.delete_batch(
                company_id=self.company_id,
                names=nombres
            )

            deleted = result.get('deleted', 0)
            self.stats['deleted'] = deleted

            self.info(f"✅ Eliminadas {deleted} categorías de la API")

        except Exception as e:
            self.error(f"❌ Error eliminando categorías: {e}")

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def _extract_record_key(self, registro) -> str:
        """
        Extraer record_key de un registro de categoría.

        Args:
            registro: Tuple (code, description) o dict

        Returns:
            El code de la categoría
        """
        if isinstance(registro, tuple):
            return str(registro[0])  # code
        elif isinstance(registro, dict):
            return str(registro.get('code', ''))
        return str(registro)

    def _get_table_name(self) -> str:
        """Retornar nombre de la tabla para sync_hashes"""
        return 'categories'
