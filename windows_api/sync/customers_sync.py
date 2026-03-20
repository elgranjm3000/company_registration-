"""
Customers Sync Module
Sincronizador de clientes de PostgreSQL a API REST
"""

from typing import Dict, List, Any
from .base import BaseSync


class CustomersSync(BaseSync):
    """
    Sincronizador de clientes usando API REST.

    Flujo:
    1. Detecta cambios en tabla 'clients' de PostgreSQL
    2. Compara hashes para identificar nuevos/modificados/eliminados
    3. Transforma al formato de la API
    4. Envía a la API en lotes
    5. Actualiza sync_hashes

    Uso:
        sync = CustomersSync(
            pg_conn=pg_conn,
            api_client=customers_client,
            company_id=27
        )
        sync.execute()
    """

    def __init__(self, pg_conn, api_client, company_id: int, logger=None):
        """
        Args:
            pg_conn: Conexión a PostgreSQL
            api_client: Instancia de CustomersClient
            company_id: ID de la empresa
            logger: Logger opcional
        """
        super().__init__(pg_conn, api_client, company_id, logger)
        self.table_name = 'customers'

    # =========================================================================
    # DETECCIÓN DE CAMBIOS
    # =========================================================================

    def detect_changes(self) -> Dict[str, List]:
        """
        Detectar cambios en clientes comparando hashes.

        Returns:
            Dict con:
                {
                    'nuevos': [(code, description, address, ...), ...],
                    'modificados': [(code, description, address, ...), ...],
                    'eliminados': [{'code': 'ABC'}, ...]
                }
        """
        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            # Verificar si hay clientes en sync_hashes (primera vez?)
            self.pg_cursor.execute("""
                SELECT COUNT(*)
                FROM sync_hashes
                WHERE table_name = 'customers'
                  AND company_id = %s
            """, (self.company_id,))

            count_in_hashes = self.pg_cursor.fetchone()[0]

            # CASO 1: Primera vez - no hay clientes en sync_hashes
            if count_in_hashes == 0:
                self.info("🎯 Primera sincronización: obteniendo TODOS los clientes")
                self.pg_cursor.execute("""
                    SELECT COUNT(*) FROM clients
                """)
                total_customers = self.pg_cursor.fetchone()[0]
                self.info(f"   Total clientes en PostgreSQL: {total_customers}")

                # Obtener todos los clientes
                pending_codes = []
                if total_customers > 0:
                    self.pg_cursor.execute("SELECT code FROM clients")
                    pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            # CASO 2: Sincronización incremental - solo pending_sync
            else:
                # Verificar si hay clientes con pending_sync = true
                self.pg_cursor.execute("""
                    SELECT COUNT(*)
                    FROM sync_hashes
                    WHERE table_name = 'customers'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                count_pending = self.pg_cursor.fetchone()[0]

                if count_pending == 0:
                    self.info("No hay clientes con pending_sync")
                    return cambios

                self.info(f"Se encontraron {count_pending} clientes con pending_sync")

                # Obtener códigos de clientes pendientes
                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'customers'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (self.company_id,))

                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

            if not pending_codes:
                return cambios

            # Construir filtro IN para query principal
            placeholders = ','.join(['%s'] * len(pending_codes))

            # Query de clients (más simple que products, sin joins complejos)
            query = f"""
                SELECT
                    code,
                    description,
                    address,
                    client_id,
                    email,
                    phone,
                    contact,
                    status
                FROM clients
                WHERE code IN ({placeholders})
                  AND code IS NOT NULL AND code != ''
                  AND description IS NOT NULL AND description != ''
                ORDER BY code
            """

            self.pg_cursor.execute(query, pending_codes)
            customers = self.pg_cursor.fetchall()

            self.info(f"Se recuperaron {len(customers)} clientes de PostgreSQL")

            claves_actuales = []

            # Detectar nuevos y modificados
            for customer in customers:
                if not self.sync_running:
                    break

                code = customer[0]
                claves_actuales.append(code)

                # Generar hash actual
                hash_actual = self._generar_hash(customer)

                # Obtener hash guardado
                hash_guardado = self._obtener_hash_guardado(self.table_name, code)

                if hash_guardado is None:
                    # Nuevo
                    cambios['nuevos'].append(customer)
                    self.debug(f"  ✨ NUEVO: {code}")
                elif hash_guardado != hash_actual:
                    # Modificado
                    cambios['modificados'].append(customer)
                    self.debug(f"  🔄 MODIFICADO: {code}")

                # Guardar hash actual
                self._guardar_hash(self.table_name, code, hash_actual)

            # Detectar eliminados (usando trigger deleted_at)
            self.pg_cursor.execute("""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'customers'
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
                f"Cambios en clientes: {len(cambios['nuevos'])} nuevos, "
                f"{len(cambios['modificados'])} modificados, "
                f"{len(cambios['eliminados'])} eliminados"
            )

        except Exception as e:
            self.error(f"Error detectando cambios en clientes: {e}")
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
            pg_record: Tuple con campos de clients:
                (code, description, address, client_id, email, phone, contact, status)

        Returns:
            Dict con formato esperado por la API:
                {
                    'codigo': 'V12345678',          # code de PostgreSQL
                    'document_number': '12345678',   # client_id de PostgreSQL
                    'name': 'Juan Pérez',
                    'email': 'juan@email.com',
                    'phone': '+58-414-1234567',
                    'address': 'Calle 123',
                    'status': 'active'
                }
        """
        # Extraer campos del tuple
        (
            code,            # 0 - Usar como document_number
            description,     # 1 - Usar como name
            address,         # 2
            client_id,       # 3 - No usado (interno de PG)
            email,           # 4
            phone,           # 5
            contact,         # 6
            status           # 7 - Status del cliente
        ) = pg_record

        # Usar contact como name si no hay description
        name = description if description else (contact if contact else '')

        # Mapear status de PostgreSQL a formato API
        # Asumimos: '01' = active, otro = inactive
        status_mapped = 'active' if status == '01' else 'inactive'

        # VALIDACIÓN: code no debe estar vacío
        codigo_final = code
        if not code or code.strip() == '':
            self.warning(
                f"⚠️  Cliente con code VACÍO (usando client_id '{client_id}' como codigo)"
            )
            codigo_final = client_id if client_id else f"TEMP-{hash(client_id)}"

        return {
            'codigo': codigo_final,             # code de PostgreSQL (o client_id si code está vacío)
            'document_number': client_id,       # client_id de PostgreSQL
            'name': name,
            'email': email if email else None,
            'phone': phone if phone else None,
            'address': address if address else None,
            'status': status_mapped
        }

    # =========================================================================
    # SINCRONIZACIÓN A API
    # =========================================================================

    def sync_to_api(self, changes: Dict[str, List]) -> bool:
        """
        Sincronizar clientes a la API REST con reintentos automáticos.

        Args:
            changes: Dict con nuevos y modificados

        Returns:
            True si exitoso, False si hubo errores
        """
        # Combinar nuevos y modificados
        todos_los_customers = changes.get('nuevos', []) + changes.get('modificados', [])

        if not todos_los_customers:
            self.info("No hay clientes para sincronizar")
            return True

        self.info(f"Sincronizando {len(todos_los_customers)} clientes a la API...")

        # Transformar a formato de API
        customers_api = [
            self.transform_to_api(cust)
            for cust in todos_los_customers
        ]

        # DEBUG: Mostrar payload que se va a enviar
        self.info(f"\n{'='*70}")
        self.info(f"📤 ENVIANDO CLIENTES A LA API")
        self.info(f"{'='*70}")
        self.info(f"Company ID: {self.company_id}")
        self.info(f"Total clientes: {len(customers_api)}")
        if len(customers_api) > 0:
            self.info(f"\n📋 Primer cliente (ejemplo):")
            import json
            self.info(json.dumps(customers_api[0], indent=2, ensure_ascii=False))
        self.info(f"{'='*70}\n")

        # Reintentos si falla todo el lote
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 2 ** attempt  # 2s, 4s, 8s
                    self.warning(
                        f"⚠️ Error sincronizando clientes. "
                        f"Reintentando en {wait_time}s... (intento {attempt + 1}/{max_retries})"
                    )
                    import time
                    time.sleep(wait_time)

                # Enviar a API en lotes
                result = self.api_client.sync_batch(
                    company_id=self.company_id,
                    customers=customers_api
                )

                # Actualizar estadísticas
                self.stats['created'] = result.get('created', 0)
                self.stats['updated'] = result.get('updated', 0)
                self.stats['errors'] = result.get('errors', 0)

                if self.stats['errors'] == 0:
                    self.info(
                        f"✅ Clientes sincronizados: {self.stats['created']} creados, "
                        f"{self.stats['updated']} actualizados"
                    )
                    return True
                else:
                    # Si hay errores en los datos, mostrar detalles
                    self.error(f"❌ Errores sincronizando clientes: {self.stats['errors']}")

                    # Mostrar detalles de errores
                    error_details = result.get('error_details', [])
                    if error_details:
                        self.error(f"❌ Detalles de errores ({len(error_details)} clientes fallaron):")
                        for idx, error in enumerate(error_details[:20], 1):
                            if isinstance(error, dict):
                                doc = error.get('document_number', error.get('customer', {}).get('document_number', 'N/A'))
                                err_msg = error.get('error', error.get('message', 'Unknown error'))
                                self.error(f"   {idx}. ❌ Cliente '{doc}': {err_msg}")
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
                    self.error(f"❌ Error sincronizando clientes después de {max_retries} intentos: {e}")
                    import traceback
                    self.error(traceback.format_exc())
                    return False

                # Si no es un error recuperable, no reintentar
                if not should_retry:
                    self.error(f"❌ Error sincronizando clientes (no recuperable): {e}")
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
        Eliminar clientes de la API REST.

        Args:
            deleted_items: Lista de dicts con {'code': 'ABC'}
        """
        if not deleted_items:
            return

        self.info(f"Eliminando {len(deleted_items)} clientes de la API...")

        # Extraer códigos (usados como document_number)
        document_numbers = [item['code'] for item in deleted_items]

        try:
            result = self.api_client.delete_batch(
                company_id=self.company_id,
                documents=document_numbers
            )

            deleted = result.get('deleted', 0)
            self.stats['deleted'] = deleted

            self.info(f"✅ Eliminados {deleted} clientes de la API")

            # Limpiar sync_hashes (eliminar registros con deleted_at)
            self.pg_cursor.execute("""
                DELETE FROM sync_hashes
                WHERE table_name = 'customers'
                  AND company_id = %s
                  AND deleted_at IS NOT NULL
            """, (self.company_id,))
            filas_limpias = self.pg_cursor.rowcount
            self.pg_conn.commit()
            self.info(f"✅ Limpiados {filas_limpias} registros de sync_hashes")

        except Exception as e:
            self.error(f"❌ Error eliminando clientes: {e}")

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def _extract_record_key(self, registro) -> str:
        """
        Extraer record_key de un registro de cliente.

        Args:
            registro: Tuple (code, ...) o dict

        Returns:
            El code del cliente (usado como document_number)
        """
        if isinstance(registro, tuple):
            return str(registro[0])  # code
        elif isinstance(registro, dict):
            return str(registro.get('code', ''))
        return str(registro)

    # =========================================================================
    # SINCRONIZACIÓN DESDE API REST → POSTGRESQL
    # =========================================================================

    def detect_new_from_api(self) -> List[Dict]:
        """
        Detectar NUEVOS clientes en la API REST que no existen en PostgreSQL.

        Returns:
            Lista de dicts con clientes nuevos desde la API
        """
        nuevos_clientes = []

        try:
            self.info("\n" + "="*70)
            self.info("📥 DETECTANDO NUEVOS CLIENTES DESDE API REST")
            self.info("="*70)

            # 1. Obtener todos los clientes desde la API
            self.info(f"Obteniendo clientes de la API REST (company_id={self.company_id})...")
            clientes_api = list(self.api_client.get_all(company_id=self.company_id))
            self.info(f"   Total clientes en API: {len(clientes_api)}")

            # 2. Obtener códigos existentes en PostgreSQL
            self.pg_cursor.execute("SELECT code FROM clients")
            codigos_pg = {row[0] for row in self.pg_cursor.fetchall()}
            self.info(f"   Total clientes en PostgreSQL: {len(codigos_pg)}")

            # 3. Detectar nuevos (existen en API pero no en PG)
            for cliente_api in clientes_api:
                codigo_api = cliente_api.get('codigo')

                if codigo_api and codigo_api not in codigos_pg:
                    nuevos_clientes.append(cliente_api)
                    self.info(f"   ✨ NUEVO detectado: {codigo_api} - {cliente_api.get('name')}")

            self.info(f"\n📊 Total nuevos clientes detectados: {len(nuevos_clientes)}")
            self.info("="*70 + "\n")

            return nuevos_clientes

        except Exception as e:
            self.error(f"❌ Error detectando nuevos desde API: {e}")
            import traceback
            self.error(traceback.format_exc())
            return []

    def sync_new_from_api(self, nuevos_clientes: List[Dict]) -> int:
        """
        Insertar NUEVOS clientes desde la API REST a PostgreSQL.

        Args:
            nuevos_clientes: Lista de clientes nuevos desde la API

        Returns:
            Cantidad de clientes insertados
        """
        if not nuevos_clientes:
            self.info("No hay nuevos clientes para insertar desde la API")
            return 0

        try:
            cantidad = len(nuevos_clientes)
            self.info("\nInsertando {} nuevos clientes a PostgreSQL...".format(cantidad))

            insertados = 0

            for cliente in nuevos_clientes:
                try:
                    # Mapear estado de API a PostgreSQL
                    status_pg = '01' if cliente.get('status') == 'active' else '02'

                    # Insertar en PostgreSQL
                    self.pg_cursor.execute("""
                        INSERT INTO clients (
                            code, description, address, client_id,
                            email, phone, contact, status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        cliente.get('codigo'),          # code
                        cliente.get('name'),            # description
                        cliente.get('address'),         # address
                        cliente.get('document_number'), # client_id
                        cliente.get('email'),           # email
                        cliente.get('phone'),           # phone
                        cliente.get('name'),            # contact (usar name)
                        status_pg                       # status
                    ))

                    insertados += 1
                    self.info(f"   ✅ Insertado: {cliente.get('codigo')} - {cliente.get('name')}")

                except Exception as e:
                    self.error(f"   ❌ Error insertando {cliente.get('codigo')}: {e}")
                    continue

            # Commit de todos los inserts
            self.pg_conn.commit()
            self.info(f"\n✅ Total insertados: {insertados} de {len(nuevos_clientes)}")

            # Actualizar sync_hashes (marcar como sincronizados)
            self._update_sync_hashes_after_insert(nuevos_clientes)

            return insertados

        except Exception as e:
            self.error(f"❌ Error insertando nuevos desde API: {e}")
            self.pg_conn.rollback()
            return 0

    def _update_sync_hashes_after_insert(self, clientes: List[Dict]):
        """
        Actualizar sync_hashes después de insertar clientes desde la API.

        Args:
            clientes: Lista de clientes insertados
        """
        try:
            for cliente in clientes:
                codigo = cliente.get('codigo')

                # Generar hash del cliente
                # Simular el tuple de PostgreSQL para generar el hash
                pg_tuple = (
                    codigo,                           # code
                    cliente.get('name'),              # description
                    cliente.get('address'),           # address
                    cliente.get('document_number'),   # client_id
                    cliente.get('email'),             # email
                    cliente.get('phone'),             # phone
                    cliente.get('name'),              # contact
                    '01' if cliente.get('status') == 'active' else '02'  # status
                )

                hash_valor = self._generar_hash(pg_tuple)

                # Insertar en sync_hashes como ya sincronizado
                self.pg_cursor.execute("""
                    INSERT INTO sync_hashes (
                        table_name, record_key, company_id,
                        record_hash, pending_sync, synced_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (table_name, record_key, company_id)
                    DO UPDATE SET
                        record_hash = EXCLUDED.record_hash,
                        pending_sync = FALSE,
                        synced_at = NOW()
                """, (
                    'customers',
                    codigo,
                    self.company_id,
                    hash_valor,
                    False  # pending_sync = FALSE porque ya viene de la API
                ))

            self.pg_conn.commit()
            self.info(f"✅ Actualizados {len(clientes)} registros en sync_hashes")

        except Exception as e:
            self.error(f"⚠️  Error actualizando sync_hashes: {e}")
            self.pg_conn.rollback()

    def _get_table_name(self) -> str:
        """Retornar nombre de la tabla para sync_hashes"""
        return 'customers'

    # =========================================================================
    # MÉTODO PRINCIPAL DE SINCRONIZACIÓN BIDIRECCIONAL
    # =========================================================================

    def execute(self) -> Dict[str, int]:
        """
        Ejecutar sincronización completa bidireccional:
        1. PostgreSQL → API REST (cambios locales)
        2. API REST → PostgreSQL (nuevos clientes del backend)

        Returns:
            Dict con estadísticas:
            {
                'to_api_created': 0,
                'to_api_updated': 0,
                'to_api_deleted': 0,
                'from_api_new': 0
            }
        """
        stats = {
            'to_api_created': 0,
            'to_api_updated': 0,
            'to_api_deleted': 0,
            'from_api_new': 0
        }

        try:
            self.info("\n" + "="*70)
            self.info("🔄 SINCRONIZACIÓN BIDIRECCIONAL DE CLIENTES")
            self.info("="*70)

            # ===================================================================
            # PASO 1: PostgreSQL → API REST (cambios locales)
            # ===================================================================
            self.info("\n📤 PASO 1: Sincronizando cambios LOCALES a la API REST...")
            self.info("-"*70)

            cambios = self.detect_changes()

            # Sincronizar nuevos y modificados
            if cambios['nuevos'] or cambios['modificados']:
                self.sync_to_api(cambios)
                stats['to_api_created'] = self.stats.get('created', 0)
                stats['to_api_updated'] = self.stats.get('updated', 0)

            # Sincronizar eliminados
            if cambios['eliminados']:
                self.delete_from_api(cambios['eliminados'])
                stats['to_api_deleted'] = self.stats.get('deleted', 0)

            # ===================================================================
            # PASO 2: API REST → PostgreSQL (nuevos desde backend)
            # ===================================================================
            self.info("\n📥 PASO 2: Detectando NUEVOS clientes desde API REST...")
            self.info("-"*70)

            nuevos_desde_api = self.detect_new_from_api()

            if nuevos_desde_api:
                insertados = self.sync_new_from_api(nuevos_desde_api)
                stats['from_api_new'] = insertados

            # ===================================================================
            # RESUMEN
            # ===================================================================
            self.info("\n" + "="*70)
            self.info("✅ SINCRONIZACIÓN BIDIRECCIONAL COMPLETADA")
            self.info("="*70)
            self.info(f"📤 A API REST: {stats['to_api_created']} creados, {stats['to_api_updated']} actualizados, {stats['to_api_deleted']} eliminados")
            self.info(f"📥 DESDE API: {stats['from_api_new']} nuevos clientes importados")
            self.info("="*70 + "\n")

            return stats

        except Exception as e:
            self.error(f"❌ Error en sincronización bidireccional: {e}")
            import traceback
            self.error(traceback.format_exc())
            return stats
