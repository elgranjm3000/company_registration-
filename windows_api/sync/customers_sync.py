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
                ORDER BY code
            """

            self.pg_cursor.execute(query, pending_codes)
            customers = self.pg_cursor.fetchall()

            self.info(f"Se recuperaron {len(customers)} clientes de PostgreSQL")

            # ✅ OPTIMIZACIÓN: Obtener todos los hashes de una vez
            self.info(f"   📥 Obteniendo hashes guardados (modo optimizado)...")
            record_keys = [customer[0] for customer in customers]
            hashes_guardados = self._obtener_hashes_masivo(self.table_name, record_keys)
            self.info(f"   ✅ Obtenidos {len(hashes_guardados)} hashes")

            # Detectar nuevos y modificados
            hashes_para_guardar = []  # Preparar para guardado masivo

            for i, customer in enumerate(customers):
                if not self.sync_running:
                    break

                # Mostrar progreso cada 5000 clientes
                if (i + 1) % 5000 == 0:
                    self.info(f"   🔄 Procesando {i + 1}/{len(customers)} clientes...")

                code = customer[0]

                # Generar hash actual
                hash_actual = self._generar_hash(customer)

                # Buscar hash guardado en diccionario (O(1))
                hash_guardado = hashes_guardados.get(code)

                if hash_guardado is None:
                    # Nuevo
                    cambios['nuevos'].append(customer)
                elif hash_guardado != hash_actual:
                    # Modificado
                    cambios['modificados'].append(customer)

                # Preparar para guardado masivo
                hashes_para_guardar.append((code, hash_actual))

            # ✅ OPTIMIZACIÓN: Guardar todos los hashes de una vez
            if hashes_para_guardar:
                self.info(f"   💾 Guardando {len(hashes_para_guardar)} hashes (modo optimizado)...")
                self._guardar_hashes_masivo(self.table_name, hashes_para_guardar)
                self.info(f"   ✅ Hashes guardados")

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

        # Si name sigue vacío, usar document_number o code como último fallback
        # (name es required en el backend)
        if not name or name.strip() == '':
            name = client_id if client_id else code

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

        # Limpiar espacios en blanco de todos los campos
        # Email se envía tal cual (incluyendo '@' si ese es el valor en BD)
        email_clean = (email or '').strip()

        return {
            'codigo': (codigo_final or '').strip(),             # Eliminar espacios al inicio/final
            'document_number': (client_id or '').strip(),       # Eliminar espacios al inicio/final
            'name': (name or '').strip(),
            'email': email_clean,
            'phone': (phone or '').strip() if phone else None,
            'address': (address or '').strip() if address else None,
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

                # DEBUG: Validar campos antes de enviar
                self.info(f"\n{'='*70}")
                self.info(f"📤 VALIDANDO CLIENTES ANTES DE ENVIAR")
                self.info(f"{'='*70}")
                self.info(f"Total clientes a enviar: {len(customers_api)}")

                sin_name = []
                sin_doc_number = []
                for i, cust in enumerate(customers_api):
                    if not cust.get('name') or cust.get('name').strip() == '':
                        sin_name.append(i)
                    if not cust.get('document_number') or cust.get('document_number').strip() == '':
                        sin_doc_number.append(i)

                if sin_name:
                    self.warning(f"   ⚠️  {len(sin_name)} clientes sin name (índices: {sin_name[:10]}...)")
                if sin_doc_number:
                    self.warning(f"   ⚠️  {len(sin_doc_number)} clientes sin document_number (índices: {sin_doc_number[:10]}...)")
                else:
                    self.info(f"   ✅ Todos los clientes tienen los campos requeridos")
                self.info(f"{'='*70}\n")

                # Enviar a API en lotes
                result = self.api_client.sync_batch(
                    company_id=self.company_id,
                    customers=customers_api
                )

                # DEBUG: Mostrar respuesta del backend
                self.info(f"\n{'='*70}")
                self.info(f"📥 RESPUESTA DEL BACKEND")
                self.info(f"{'='*70}")
                self.info(f"Enviados: {len(customers_api)}")
                self.info(f"Created: {result.get('created', 0)}")
                self.info(f"Updated: {result.get('updated', 0)}")
                self.info(f"Errors: {result.get('errors', 0)}")
                self.info(f"Total procesados: {result.get('created', 0) + result.get('updated', 0) + result.get('errors', 0)}")

                diferencia = len(customers_api) - (result.get('created', 0) + result.get('updated', 0) + result.get('errors', 0))
                if diferencia != 0:
                    self.warning(f"⚠️  DIFERENCIA: {diferencia} clientes no fueron procesados")

                if result.get('error_details'):
                    self.info(f"\n❌ Detalles de errores:")
                    for i, error in enumerate(result.get('error_details', [])[:10], 1):
                        self.error(f"   {i}. {error}")

                self.info(f"{'='*70}\n")

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
        Usa from_date para solo descargar clientes modificados desde la última sincronización.

        Returns:
            Lista de dicts con clientes nuevos desde la API
        """
        nuevos_clientes = []

        try:
            self.info("\n" + "="*70)
            self.info("📥 DETECTANDO NUEVOS CLIENTES DESDE API REST")
            self.info("="*70)

            # 1. Obtener fecha de última sincronización
            from_date = self._get_last_sync_date()

            # 2. Obtener clientes desde la API con from_date (optimizado)
            if from_date:
                self.info(f"Obteniendo clientes modificados desde: {from_date}")
                clientes_api = list(self.api_client.get_all(
                    company_id=self.company_id,
                    from_date=from_date  # ✅ Solo modificados desde esta fecha
                ))
            else:
                self.info(f"Obteniendo TODOS los clientes (primera sincronización)")
                clientes_api = list(self.api_client.get_all(
                    company_id=self.company_id
                ))

            self.info(f"   Total clientes obtenidos de API: {len(clientes_api)}")

            # 2. Obtener códigos YA SINCRONIZADOS desde sync_hashes (con TRIM para eliminar espacios)
            self.pg_cursor.execute("""
                SELECT TRIM(record_key) as record_key
                FROM sync_hashes
                WHERE table_name = 'customers'
                  AND company_id = %s
                  AND deleted_at IS NULL
            """, (self.company_id,))
            codigos_sincronizados = {row[0] for row in self.pg_cursor.fetchall()}
            self.info(f"   Total clientes ya sincronizados: {len(codigos_sincronizados)}")

            # 3. Detectar nuevos (existen en API pero NO están en sync_hashes)
            for cliente_api in clientes_api:
                codigo_api = (cliente_api.get('codigo') or '').strip()

                if codigo_api and codigo_api not in codigos_sincronizados:
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
                            email, phone, contact, name_fiscal, status, generic_client,
                            country, province, city, town, area_sales, seller, client_group,
                            credit_days, credit_limit, discount
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        cliente.get('codigo'),          # code
                        cliente.get('name'),            # description
                        cliente.get('address'),         # address
                        cliente.get('document_number'), # client_id
                        cliente.get('email'),           # email
                        cliente.get('phone'),           # phone
                        cliente.get('contact'),         # contact (campo del API)
                        cliente.get('document_type'),   # name_fiscal (document_type del API)
                        status_pg,                      # status
                        False,                          # generic_client
                        '00',                           # country
                        '00',                           # province
                        '00',                           # city
                        '00',                           # town
                        '00',                           # area_sales
                        '00',                           # seller
                        '00',                           # client_group
                        0,                              # credit_days
                        0,                              # credit_limit
                        0                               # discount
                    ))

                    insertados += 1
                    self.info(f"   ✅ Insertado: {cliente.get('codigo')} - {cliente.get('name')}")

                except Exception as e:
                    self.error(f"   ❌ Error insertando {cliente.get('codigo')}: {e}")
                    continue

            # Commit de todos los inserts
            self.pg_conn.commit()
            self.info(f"\n✅ Total insertados: {insertados} de {len(nuevos_clientes)}")

            # Actualizar estadísticas
            self.stats['created'] += insertados

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

    def _get_last_sync_date(self) -> str:
        """
        Obtener fecha de última sincronización desde sync_config.

        Returns:
            Fecha en formato ISO o None si es primera vez
        """
        try:
            self.pg_cursor.execute("""
                SELECT value
                FROM sync_config
                WHERE key = %s
            """, ('customers_last_sync_from_api',))

            result = self.pg_cursor.fetchone()

            if result and result[0]:
                last_date = result[0]
                self.info(f"   📅 Última sincronización desde API: {last_date}")
                return last_date
            else:
                self.info(f"   📅 Primera sincronización desde API (sin from_date)")
                return None

        except Exception as e:
            self.warning(f"   ⚠️  Error obteniendo última fecha: {e}")
            return None

    def _save_last_sync_date(self):
        """
        Guardar fecha actual en sync_config como última sincronización desde API.
        """
        try:
            from datetime import datetime

            # Fecha actual en formato ISO para API
            current_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000000Z')

            self.pg_cursor.execute("""
                INSERT INTO sync_config (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key)
                DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
            """, ('customers_last_sync_from_api', current_date))

            self.pg_conn.commit()
            self.info(f"   ✅ Fecha de sincronización guardada: {current_date}")

        except Exception as e:
            self.warning(f"   ⚠️  Error guardando fecha: {e}")

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
                success = self.sync_to_api(cambios)
                stats['to_api_created'] = self.stats.get('created', 0)
                stats['to_api_updated'] = self.stats.get('updated', 0)

                # Si la sincronización fue exitosa, marcar como sincronizados en sync_hashes
                if success and (self.stats.get('created', 0) > 0 or self.stats.get('updated', 0) > 0):
                    self._update_sync_hashes(cambios)
                    self.info(f"✅ Actualizados {len(cambios['nuevos']) + len(cambios['modificados'])} registros en sync_hashes")

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

                # ✅ GUARDAR fecha después de sincronizar exitosamente
                if insertados > 0:
                    self._save_last_sync_date()

            # ===================================================================
            # RESUMEN
            # ===================================================================
            self.info("\n" + "="*70)
            self.info("✅ SINCRONIZACIÓN BIDIRECCIONAL COMPLETADA")
            self.info("="*70)
            self.info(f"📤 A API REST: {stats['to_api_created']} creados, {stats['to_api_updated']} actualizados, {stats['to_api_deleted']} eliminados")
            self.info(f"📥 DESDE API: {stats['from_api_new']} nuevos clientes importados")
            self.info(f"📅 Próxima sincronización usará from_date (solo modificados)")
            self.info("="*70 + "\n")

            return stats

        except Exception as e:
            self.error(f"❌ Error en sincronización bidireccional: {e}")
            import traceback
            self.error(traceback.format_exc())
            return stats
