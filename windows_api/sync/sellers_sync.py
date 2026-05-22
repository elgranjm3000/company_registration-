"""
Sellers Sync Module
Sincronizador de vendedores de PostgreSQL a API REST
"""

from typing import Dict, List, Any
from .base import BaseSync


class SellersSync(BaseSync):
    """
    Sincronizador de vendedores usando API REST.

    Particularidad:
    - Los vendedores requieren un user asociado
    - El email es único globalmente (tabla users)
    - El password debe venir hasheado con bcrypt (formato $2y$ de Laravel)
    - La API crea el user automáticamente si no existe

    Flujo:
    1. Detecta cambios en tabla 'sellers' de PostgreSQL
    2. Compara hashes para identificar nuevos/modificados/eliminados
    3. Genera password bcrypt si es necesario
    4. Transforma al formato de la API
    5. Envía a la API en lotes
    6. Actualiza sync_hashes

    Uso:
        sync = SellersSync(
            pg_conn=pg_conn,
            api_client=sellers_client,
            company_id=27
        )
        sync.execute()
    """

    def __init__(self, pg_conn, api_client, company_id: int, logger=None):
        """
        Args:
            pg_conn: Conexión a PostgreSQL
            api_client: Instancia de SellersClient
            company_id: ID de la empresa
            logger: Logger opcional
        """
        super().__init__(pg_conn, api_client, company_id, logger)
        self.table_name = 'sellers'

    # =========================================================================
    # DETECCIÓN DE CAMBIOS
    # =========================================================================

    def detect_changes(self) -> Dict[str, List]:
        """
        Detectar cambios en vendedores comparando hashes.

        Returns:
            Dict con:
                {
                    'nuevos': [(code, description, email, ...), ...],
                    'modificados': [(code, description, email, ...), ...],
                    'eliminados': [{'code': 'V001'}, ...]
                }
        """
        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            # Verificar si hay vendedores en sync_hashes (primera vez?)
            self.pg_cursor.execute("""
                SELECT COUNT(*)
                FROM sync_hashes
                WHERE table_name = 'sellers'
                  AND company_id = %s
            """, (self.company_id,))

            count_in_hashes = self.pg_cursor.fetchone()[0]

            # CASO 1: Primera vez - no hay vendedores en sync_hashes
            if count_in_hashes == 0:
                self.info("🎯 Primera sincronización: obteniendo TODOS los vendedores")
                self.pg_cursor.execute("""
                    SELECT COUNT(*) FROM sellers
                """)
                total_sellers = self.pg_cursor.fetchone()[0]
                self.info(f"   Total vendedores en PostgreSQL: {total_sellers}")

                # Obtener todos los vendedores
                pending_codes = []
                if total_sellers > 0:
                    self.pg_cursor.execute("SELECT code FROM sellers")
                    pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            # CASO 2: Sincronización incremental - solo pending_sync
            else:
                # Verificar si hay vendedores con pending_sync = true
                self.pg_cursor.execute("""
                    SELECT COUNT(*)
                    FROM sync_hashes
                    WHERE table_name = 'sellers'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                count_pending = self.pg_cursor.fetchone()[0]

                if count_pending == 0:
                    self.info("No hay vendedores con pending_sync")
                    return cambios

                self.info(f"Se encontraron {count_pending} vendedores con pending_sync")

                # Obtener códigos de vendedores pendientes
                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'sellers'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            if not pending_codes:
                # Detectar eliminados (usando trigger deleted_at)
                # IMPORTANTE: Esto debe ejecutar SIEMPRE, incluso si no hay pending_codes
                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'sellers'
                      AND company_id = %s
                      AND deleted_at IS NOT NULL
                    ORDER BY deleted_at DESC
                """, (self.company_id,))

                eliminados = self.pg_cursor.fetchall()

                for (eliminado,) in eliminados:
                    cambios['eliminados'].append({'code': eliminado})
                    self.debug(f"  ❌ ELIMINADO: {eliminado}")

                self.info(f"{len(cambios['eliminados'])} vendedores eliminados detectados")
                return cambios

            # Construir filtro IN para query principal
            placeholders = ','.join(['%s'] * len(pending_codes))

            # Query de sellers
            # Nota: Tu BD usa user_code/code, no user_id/id
            query = f"""
                SELECT
                    s.code,
                    s.description,
                    u.email,
                    u.user_password,
                    u.status,
                    s.user_code
                FROM sellers s
                LEFT JOIN users u ON s.user_code = u.code
                WHERE s.code IN ({placeholders})
                  AND s.code IS NOT NULL AND s.code != '' AND s.code <> 'N/A'
                  AND s.description IS NOT NULL AND s.description != ''
                  AND u.email IS NOT NULL AND TRIM(u.email) <> '' AND TRIM(u.email) <> '@'
                ORDER BY s.code
            """

            self.pg_cursor.execute(query, pending_codes)
            sellers = self.pg_cursor.fetchall()

            self.info(f"Se recuperaron {len(sellers)} vendedores de PostgreSQL")

            claves_actuales = []

            # Detectar nuevos y modificados
            for seller in sellers:
                if not self.sync_running:
                    break

                code = seller[0]
                claves_actuales.append(code)

                # Generar hash actual
                hash_actual = self._generar_hash(seller)

                # Obtener hash guardado
                hash_guardado = self._obtener_hash_guardado(self.table_name, code)

                if hash_guardado is None:
                    # Nuevo
                    cambios['nuevos'].append(seller)
                    self.debug(f"  ✨ NUEVO: {code}")
                elif hash_guardado != hash_actual:
                    # Modificado
                    cambios['modificados'].append(seller)
                    self.debug(f"  🔄 MODIFICADO: {code}")

                # Guardar hash actual
                self._guardar_hash(self.table_name, code, hash_actual)

            # Detectar eliminados (usando trigger deleted_at)
            self.pg_cursor.execute("""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'sellers'
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
                f"Cambios en vendedores: {len(cambios['nuevos'])} nuevos, "
                f"{len(cambios['modificados'])} modificados, "
                f"{len(cambios['eliminados'])} eliminados"
            )

        except Exception as e:
            self.error(f"Error detectando cambios en vendedores: {e}")
            import traceback
            self.error(traceback.format_exc())
            self.pg_conn.rollback()

        return cambios

    # =========================================================================
    # TRANSFORMACIÓN
    # =========================================================================

    def transform_to_api(self, pg_record: tuple) -> Dict[str, Any]:
        """
        Transformar registro de PostgreSQL a formato de API REST.

        Args:
            pg_record: Tuple con campos de sellers:
                (code, description, email, user_password, status, user_code)

        Returns:
            Dict con formato esperado por la API:
                {
                    'code': 'V001',
                    'description': 'Juan Pérez',
                    'email': 'juan@email.com',
                    'password': '$2y$10$...',  # bcrypt hash
                    'status': 'active'
                }
        """
        # Extraer campos del tuple
        (
            code,            # 0
            description,     # 1
            email,           # 2
            password,        # 3 - user_password (puede ser NULL si es nuevo)
            status,          # 4 - '01' = active, '02' = inactive (o 'A'/'I')
            user_code        # 5 - No usado (interno de PG)
        ) = pg_record

        # Mapear status de PostgreSQL a API
        # PostgreSQL usa '01'/'02' o 'A'/'I', API usa 'active'/'inactive'
        status_map = {
            '01': 'active',
            '02': 'inactive',
            'A': 'active',
            'I': 'inactive',
            'active': 'active',
            'inactive': 'inactive'
        }
        api_status = status_map.get(status, 'active')

        # Generar password bcrypt si no existe
        # Nota: En producción, esto debería generar un password aleatorio
        # y enviarlo por email al usuario
        if not password:
            # Password por defecto: mismos últimos 6 dígitos del código
            # En producción, usar bcrypt.hashpw() con password aleatorio
            default_password = f"Temp{code[-6:]}" if len(code) >= 6 else f"Temp{code}123"
            password = self._generate_bcrypt_hash(default_password)
            self.warning(
                f"⚠️  No password found for seller {code}, "
                f"using default. CHANGE THIS IN PRODUCTION!"
            )

        # Validar email: usar email por defecto si es None
        # Nota: Los emails con valor '@', '' o solo espacios ya fueron filtrados en el query
        valid_email = email
        if not email:
            valid_email = f"{code.lower()}@temp.com"
            self.warning(
                f"⚠️  No valid email for seller {code}, using {valid_email}. CHANGE THIS IN PRODUCTION!"
            )

        return {
            'code': code,
            'description': description,
            'email': valid_email,
            'password': password,
            'status': api_status
        }

    def _generate_bcrypt_hash(self, password: str) -> str:
        """
        Generar hash bcrypt compatible con Laravel ($2y$ prefix).

        Args:
            password: Password en texto plano

        Returns:
            Hash bcrypt con formato $2y$10$...
        """
        try:
            import bcrypt

            # Laravel usa $2y$ prefix, bcrypt.py genera $2b$
            # Necesitamos reemplazar el prefix
            password_bytes = password.encode('utf-8')
            salt = bcrypt.gensalt(rounds=10)
            hashed = bcrypt.hashpw(password_bytes, salt)

            # Convertir $2b$ a $2y$ (formato Laravel)
            hashed_str = hashed.decode('utf-8')
            if hashed_str.startswith('$2b$'):
                hashed_str = '$2y$' + hashed_str[4:]

            return hashed_str

        except ImportError:
            self.error(
                "bcrypt module not installed. "
                "Install it: pip install bcrypt"
            )
            # Retornar un hash dummy para que falle la API
            return '$2y$10$NOTINSTALLED'

    # =========================================================================
    # SINCRONIZACIÓN A API
    # =========================================================================

    def sync_to_api(self, changes: Dict[str, List]) -> bool:
        """
        Sincronizar vendedores a la API REST con reintentos automáticos.

        Args:
            changes: Dict con nuevos y modificados

        Returns:
            True si exitoso, False si hubo errores
        """
        # Combinar nuevos y modificados
        todos_los_sellers = changes.get('nuevos', []) + changes.get('modificados', [])

        if not todos_los_sellers:
            self.info("No hay vendedores para sincronizar")
            return True

        self.info(f"Sincronizando {len(todos_los_sellers)} vendedores a la API...")

        # Transformar a formato de API
        sellers_api = [
            self.transform_to_api(seller)
            for seller in todos_los_sellers
        ]

        # Reintentos si falla todo el lote
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 2s, 4s, 8s
                    self.warning(
                        f"⚠️ Error sincronizando vendedores. "
                        f"Reintentando en {wait_time}s... (intento {attempt + 1}/{max_retries})"
                    )
                    import time
                    time.sleep(wait_time)

                # Enviar a API en lotes
                result = self.api_client.sync_batch(
                    company_id=self.company_id,
                    sellers=sellers_api
                )

                # Actualizar estadísticas
                self.stats['created'] = result.get('created', 0)
                self.stats['updated'] = result.get('updated', 0)
                self.stats['errors'] = result.get('errors', 0)

                if self.stats['errors'] == 0:
                    self.info(
                        f"✅ Vendedores sincronizados: {self.stats['created']} creados, "
                        f"{self.stats['updated']} actualizados"
                    )
                    return True
                else:
                    # Si hay errores en los datos, mostrar detalles
                    self.error(f"❌ Errores sincronizando vendedores: {self.stats['errors']}")

                    # Mostrar detalles de errores
                    error_details = result.get('error_details', [])
                    if error_details:
                        self.error(f"❌ Detalles de errores ({len(error_details)} vendedores fallaron):")
                        for idx, error in enumerate(error_details[:20], 1):
                            if isinstance(error, dict):
                                code = error.get('code', error.get('seller', {}).get('code', 'N/A'))
                                err_msg = error.get('error', error.get('message', 'Unknown error'))
                                self.error(f"   {idx}. ❌ Vendedor '{code}': {err_msg}")
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
                    self.error(f"❌ Error sincronizando vendedores después de {max_retries} intentos: {e}")
                    import traceback
                    self.error(traceback.format_exc())
                    return False

                # Si no es un error recuperable, no reintentar
                if not should_retry:
                    self.error(f"❌ Error sincronizando vendedores (no recuperable): {e}")
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
        Eliminar vendedores de la API REST.

        ⚠️ ADVERTENCIA: Esto también elimina los users asociados.

        Args:
            deleted_items: Lista de dicts con {'code': 'V001'}
        """
        if not deleted_items:
            return

        self.info(f"Eliminando {len(deleted_items)} vendedores de la API...")

        # Extraer códigos
        codes = [item['code'] for item in deleted_items]

        try:
            result = self.api_client.delete_batch(
                company_id=self.company_id,
                codes=codes
            )

            deleted = result.get('deleted', 0)
            self.stats['deleted'] = deleted

            self.info(f"✅ Eliminados {deleted} vendedores de la API")

            # Limpiar sync_hashes (eliminar registros con deleted_at)
            self.pg_cursor.execute("""
                DELETE FROM sync_hashes
                WHERE table_name = 'sellers'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
            """, (self.company_id,))
            filas_limpias = self.pg_cursor.rowcount
            self.pg_conn.commit()
            self.info(f"✅ Limpiados {filas_limpias} registros de sync_hashes")

        except Exception as e:
            self.error(f"❌ Error eliminando vendedores: {e}")

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def _extract_record_key(self, registro) -> str:
        """
        Extraer record_key de un registro de vendedor.

        Args:
            registro: Tuple (code, ...) o dict

        Returns:
            El code del vendedor
        """
        if isinstance(registro, tuple):
            return str(registro[0])  # code
        elif isinstance(registro, dict):
            return str(registro.get('code', ''))
        return str(registro)

    def _get_table_name(self) -> str:
        """Retornar nombre de la tabla para sync_hashes"""
        return 'sellers'
