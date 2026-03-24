"""
Base Sync Module
Clase base abstracta para sincronizadores de PostgreSQL a API REST.
Implementa el patrón Template Method para reutilizar lógica común.
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime


class BaseSync(ABC):
    """
    Clase base abstracta para sincronizadores.

    Flujo de sincronización (Template Method):
    1. Conectar a PostgreSQL
    2. Detectar cambios desde sync_hashes
    3. Transformar registros de PostgreSQL a formato de API
    4. Sincronizar a la API REST
    5. Actualizar sync_hashes

    Uso:
        class CategoriesSync(BaseSync):
            def detect_changes(self):
                # Detectar cambios en categories
                pass

            def transform_to_api(self, pg_record):
                # Transformar registro a formato API
                pass

            def sync_to_api(self, changes):
                # Enviar a API
                pass
    """

    def __init__(
        self,
        pg_conn,
        api_client,
        company_id: int,
        logger=None
    ):
        """
        Args:
            pg_conn: Conexión a PostgreSQL (ya establecida)
            api_client: Cliente de la API REST (CategoriesClient, ProductsClient, etc.)
            company_id: ID de la empresa
            logger: Logger opcional (puede ser logging.Logger o una función log(message, level))
        """
        self.pg_conn = pg_conn
        self.pg_cursor = pg_conn.cursor()
        self.api_client = api_client
        self.company_id = company_id

        # Logger - Wrapper que funciona con logging.Logger o función simple
        if logger is None:
            self._logger = logging.getLogger(self.__class__.__name__)
            self._logger_func = None
        elif callable(logger):
            # Es una función log(message, level)
            self._logger = None
            self._logger_func = logger
        else:
            # Es un objeto logging.Logger
            self._logger = logger
            self._logger_func = None

        # Estadísticas de esta sincronización
        self.stats = {
            'created': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 0
        }

        # Flag para detener sincronización
        self.sync_running = True

    # =========================================================================
    # LOGGER WRAPPER
    # =========================================================================

    def _log(self, message: str, level: str = "info"):
        """
        Método interno de logging que funciona con ambos tipos de logger.

        Args:
            message: Mensaje a loggear
            level: Nivel de log (debug, info, warning, error, critical)
        """
        if self._logger_func:
            # Usar función log(message, level)
            self._logger_func(message, level)
        elif self._logger:
            # Usar logging.Logger
            log_method = getattr(self._logger, level, self._logger.info)
            log_method(message)

    def debug(self, message: str):
        """Log debug message."""
        self._log(message, "debug")

    def info(self, message: str):
        """Log info message."""
        self._log(message, "info")

    def warning(self, message: str):
        """Log warning message."""
        self._log(message, "warning")

    def error(self, message: str):
        """Log error message."""
        self._log(message, "error")

    def critical(self, message: str):
        """Log critical message."""
        self._log(message, "critical")

    # =========================================================================
    # MÉTODOS ABSTRACTOS (deben implementar las subclases)
    # =========================================================================

    @abstractmethod
    def detect_changes(self) -> Dict[str, List]:
        """
        Detectar cambios desde PostgreSQL usando sync_hashes.

        Returns:
            Dict con:
                {
                    'nuevos': [registro1, registro2, ...],
                    'modificados': [registro3, ...],
                    'eliminados': [registro4, ...]
                }
        """
        pass

    @abstractmethod
    def transform_to_api(self, pg_record: tuple) -> Dict[str, Any]:
        """
        Transformar registro de PostgreSQL a formato de API REST.

        Args:
            pg_record: Tuple con datos de PostgreSQL

        Returns:
            Dict con datos formateados para la API
        """
        pass

    @abstractmethod
    def sync_to_api(self, changes: Dict[str, List]) -> bool:
        """
        Sincronizar cambios a la API REST.

        Args:
            changes: Dict con nuevos, modificados, eliminados

        Returns:
            True si exitoso, False si hubo errores
        """
        pass

    # =========================================================================
    # MÉTODOS CONCRETOS (compartidos por todas las subclases)
    # =========================================================================

    def execute(self) -> bool:
        """
        Ejecutar sincronización completa (Template Method).

        Este método define el esqueleto del algoritmo de sincronización,
        delegando los pasos específicos a las subclases.

        Returns:
            True si exitoso, False si hubo errores
        """
        try:
            self.info("=" * 70)
            self.info(f"Starting {self.__class__.__name__}")
            self.info("=" * 70)

            # 1. Detectar cambios
            self.info("🔍 Step 1: Detecting changes...")
            changes = self.detect_changes()

            total_changes = (
                len(changes.get('nuevos', [])) +
                len(changes.get('modificados', [])) +
                len(changes.get('eliminados', []))
            )

            if total_changes == 0:
                self.info("✨ No changes detected")
                return True

            self.info(
                f"📊 Changes detected: "
                f"{len(changes.get('nuevos', []))} new, "
                f"{len(changes.get('modificados', []))} modified, "
                f"{len(changes.get('eliminados', []))} deleted"
            )

            # 2. Sincronizar nuevos y modificados
            if changes.get('nuevos') or changes.get('modificados'):
                self.info("🚀 Step 2: Syncing to API...")
                success = self.sync_to_api(changes)

                if not success:
                    self.error("❌ Sync to API failed")
                    return False

            # 3. Eliminar (si hay)
            if changes.get('eliminados'):
                self.info("🗑️  Step 3: Deleting from API...")
                self.delete_from_api(changes['eliminados'])

            # 4. Actualizar sync_hashes
            self.info("💾 Step 4: Updating sync_hashes...")
            self._update_sync_hashes(changes)

            # 5. Resumen
            self._print_summary()

            return True

        except Exception as e:
            self.error(f"❌ Sync failed: {e}")
            import traceback
            self.error(traceback.format_exc())
            return False

    def delete_from_api(self, deleted_items: List) -> None:
        """
        Eliminar registros de la API.
        Sobreescribir en subclases si es necesario.

        Args:
            deleted_items: Lista de registros eliminados
        """
        pass

    def _print_summary(self):
        """Imprimir resumen de sincronización"""
        self.info("")
        self.info("=" * 70)
        self.info("SYNC SUMMARY")
        self.info("=" * 70)
        self.info(
            f"Created: {self.stats['created']}, "
            f"Updated: {self.stats['updated']}, "
            f"Deleted: {self.stats['deleted']}, "
            f"Errors: {self.stats['errors']}"
        )
        self.info("=" * 70)

    # =========================================================================
    # UTILIDADES PARA sync_hashes
    # =========================================================================

    def _generar_hash(self, registro: tuple) -> str:
        """
        Generar hash MD5 de un registro para detectar cambios.

        Args:
            registro: Tuple con datos del registro

        Returns:
            Hash MD5 como string hexadecimal
        """
        try:
            # Convertir el registro a string
            registro_str = str(registro)
            return hashlib.md5(registro_str.encode('utf-8')).hexdigest()
        except Exception as e:
            self.error(f"Error generating hash: {e}")
            return hashlib.md5(str(registro[0]).encode()).hexdigest()

    def _obtener_hash_guardado(self, table_name: str, record_key: str) -> Optional[str]:
        """
        Obtener hash guardado en sync_hashes.

        Args:
            table_name: Nombre de la tabla ('categories', 'products', etc.)
            record_key: Clave del registro

        Returns:
            Hash guardado o None si no existe
        """
        try:
            self.pg_cursor.execute("""
                SELECT record_hash
                FROM sync_hashes
                WHERE table_name = %s
                  AND record_key = %s
                  AND company_id = %s
            """, (table_name, record_key, self.company_id))

            result = self.pg_cursor.fetchone()
            return result[0] if result else None

        except Exception as e:
            self.error(f"Error getting saved hash: {e}")
            return None

    def _obtener_last_sync_data(self, table_name: str, record_key: str) -> Optional[Dict]:
        """
        Obtener last_sync_data guardado en sync_hashes.

        Args:
            table_name: Nombre de la tabla ('products', etc.)
            record_key: Clave del registro

        Returns:
            Dict con last_sync_data o None si no existe
        """
        try:
            self.pg_cursor.execute("""
                SELECT last_sync_data
                FROM sync_hashes
                WHERE table_name = %s
                  AND record_key = %s
                  AND company_id = %s
            """, (table_name, record_key, self.company_id))

            result = self.pg_cursor.fetchone()
            if result and result[0]:
                import json
                return json.loads(result[0])
            return None

        except Exception as e:
            self.error(f"Error getting last_sync_data: {e}")
            return None

    def _guardar_hash(
        self,
        table_name: str,
        record_key: str,
        record_hash: str,
        last_sync_data: Optional[Dict] = None
    ) -> None:
        """
        Guardar o actualizar hash en sync_hashes.

        Args:
            table_name: Nombre de la tabla
            record_key: Clave del registro
            record_hash: Hash MD5 del registro
            last_sync_data: Dict opcional con datos adicionales (ej: coin, status)
        """
        try:
            import json

            # Convertir last_sync_data a JSON string
            last_sync_json = json.dumps(last_sync_data) if last_sync_data else None

            # Intentar UPDATE primero
            self.pg_cursor.execute("""
                UPDATE sync_hashes
                SET record_hash = %s,
                    last_sync_data = %s,
                    updated_at = NOW()
                WHERE table_name = %s
                  AND record_key = %s
                  AND company_id = %s
            """, (record_hash, last_sync_json, table_name, record_key, self.company_id))

            # Si no afectó ninguna fila, hacer INSERT con pending_sync = TRUE
            if self.pg_cursor.rowcount == 0:
                self.pg_cursor.execute("""
                    INSERT INTO sync_hashes (
                        table_name, record_key, record_hash, company_id,
                        last_sync_data, pending_sync, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
                """, (table_name, record_key, record_hash, self.company_id, last_sync_json))

            self.pg_conn.commit()

        except Exception as e:
            self.error(f"Error saving hash: {e}")
            self.pg_conn.rollback()

    def _obtener_hashes_masivo(self, table_name: str, record_keys: List[str]) -> Dict[str, str]:
        """
        Obtener hashes guardados para múltiples registros de una sola vez (OPTIMIZADO).

        En lugar de hacer N queries individuales, hace 1 solo query con IN.

        Args:
            table_name: Nombre de la tabla
            record_keys: Lista de record_keys a buscar

        Returns:
            Dict {record_key: record_hash}
        """
        try:
            if not record_keys:
                return {}

            # Construir placeholders IN
            placeholders = ','.join(['%s'] * len(record_keys))

            self.pg_cursor.execute(f"""
                SELECT record_key, record_hash
                FROM sync_hashes
                WHERE table_name = %s
                  AND record_key IN ({placeholders})
                  AND company_id = %s
            """, [table_name] + record_keys + [self.company_id])

            # Convertir a diccionario para búsqueda O(1)
            hashes_dict = {row[0]: row[1] for row in self.pg_cursor.fetchall()}

            return hashes_dict

        except Exception as e:
            self.error(f"Error obteniendo hashes masivo: {e}")
            return {}

    def _guardar_hashes_masivo(
        self,
        table_name: str,
        hashes_data: List[Tuple[str, str]]  # [(record_key, record_hash), ...]
    ) -> None:
        """
        Guardar o actualizar múltiples hashes de una sola vez usando executemany (OPTIMIZADO).

        En lugar de hacer N queries individuales, hace 1 solo executemany.

        Args:
            table_name: Nombre de la tabla
            hashes_data: Lista de tuplas (record_key, record_hash)
        """
        try:
            if not hashes_data:
                return

            from datetime import datetime

            # Preparar datos para INSERT/UPDATE masivo
            data_to_insert = []
            current_time = datetime.now()

            for record_key, record_hash in hashes_data:
                data_to_insert.append((
                    table_name,
                    record_key,
                    record_hash,
                    self.company_id,
                    current_time
                ))

            # Usar INSERT ... ON CONFLICT DO UPDATE para upsert masivo
            self.pg_cursor.executemany("""
                INSERT INTO sync_hashes (
                    table_name, record_key, record_hash, company_id, updated_at
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (table_name, record_key, company_id)
                DO UPDATE SET
                    record_hash = EXCLUDED.record_hash,
                    updated_at = EXCLUDED.updated_at
            """, data_to_insert)

            self.pg_conn.commit()

        except Exception as e:
            self.error(f"Error guardando hashes masivo: {e}")
            self.pg_conn.rollback()

    def _update_sync_hashes(self, changes: Dict[str, List]) -> None:
        """
        Actualizar sync_hashes después de sincronizar exitosamente.
        Marca pending_sync = FALSE para los registros sincronizados.

        Args:
            changes: Dict con nuevos, modificados
        """
        try:
            # Marcar nuevos y modificados como sincronizados
            todos = changes.get('nuevos', []) + changes.get('modificados', [])

            if not todos:
                return

            # Actualizar cada registro
            for registro in todos:
                # Extraer record_key (varía según la entidad)
                record_key = self._extract_record_key(registro)

                self.pg_cursor.execute("""
                    UPDATE sync_hashes
                    SET pending_sync = FALSE,
                        updated_at = NOW()
                    WHERE table_name = %s
                      AND record_key = %s
                      AND company_id = %s
                """, (self._get_table_name(), record_key, self.company_id))

            self.pg_conn.commit()

            self.debug(f"Updated {len(todos)} sync_hashes records")

        except Exception as e:
            self.error(f"Error updating sync_hashes: {e}")
            self.pg_conn.rollback()

    def _extract_record_key(self, registro) -> str:
        """
        Extraer record_key de un registro.
        Sobreescribir en subclases según la entidad.

        Args:
            registro: Registro (puede ser tuple o dict)

        Returns:
            Record key como string
        """
        # Default: primer elemento del tuple
        if isinstance(registro, tuple):
            return str(registro[0])
        elif isinstance(registro, dict):
            return str(registro.get('id', registro.get('code', '')))
        return str(registro)

    def _get_table_name(self) -> str:
        """
        Obtener nombre de la tabla para sync_hashes.
        Sobreescribir en subclases.

        Returns:
            Nombre de la tabla ('categories', 'products', etc.)
        """
        return 'unknown'
