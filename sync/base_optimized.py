"""
SOLUCIÓN: Optimizar detección de cambios con procesamiento por lotes

En lugar de hacer 50,980 queries individuales, hacer:
- 1 query para obtener todos los hashes
- 1 query masivo para guardar todos los hashes
"""

# ===========================================================================
# MÉTODO 1: Obtener todos los hashes de una vez
# ===========================================================================

def _obtener_hashes_masivo(self, table_name: str, record_keys: List[str]) -> Dict[str, str]:
    """
    Obtener hashes guardados para múltiples registros de una sola vez.

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


# ===========================================================================
# MÉTODO 2: Guardar hashes en lote con executemany
# ===========================================================================

def _guardar_hashes_masivo(
    self,
    table_name: str,
    hashes_data: List[Tuple[str, str]]  # [(record_key, record_hash), ...]
) -> None:
    """
    Guardar o actualizar múltiples hashes de una sola vez usando executemany.

    Args:
        table_name: Nombre de la tabla
        hashes_data: Lista de tuplas (record_key, record_hash)
    """
    try:
        if not hashes_data:
            return

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


# ===========================================================================
# MÉTODO 3: detect_changes() optimizado
# ===========================================================================

def detect_changes_optimized(self) -> Dict[str, List]:
    """
    Detectar cambios en clientes comparando hashes (OPTIMIZADO).

    En lugar de 100,000+ queries individuales, hace solo 3 queries:
    - 1 para obtener clientes pendientes
    - 1 para obtener todos los hashes de esos clientes
    - 1 para guardar todos los hashes actualizados

    Returns:
        Dict con: {'nuevos': [...], 'modificados': [...], 'eliminados': [...]}
    """
    cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

    try:
        # 1. Obtener códigos con pending_sync
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

        self.info(f"📊 Procesando {len(pending_codes)} clientes con pending_sync...")

        # 2. Obtener clientes de PostgreSQL
        placeholders = ','.join(['%s'] * len(pending_codes))

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

        self.info(f"   ✅ Recuperados {len(customers)} clientes de PostgreSQL")

        # 3. ✅ OBTENER TODOS LOS HASHES DE UNA VEZ
        self.info(f"   📥 Obteniendo hashes guardados...")
        record_keys = [customer[0] for customer in customers]
        hashes_guardados = self._obtener_hashes_masivo('customers', record_keys)

        self.info(f"   ✅ Obtenidos {len(hashes_guardados)} hashes guardados")

        # 4. Detectar cambios y preparar datos para guardar
        hashes_para_guardar = []

        for i, customer in enumerate(customers):
            # Mostrar progreso cada 5000 clientes
            if (i + 1) % 5000 == 0:
                self.info(f"   🔄 Procesando {i + 1}/{len(customers)} clientes...")

            code = customer[0]
            hash_actual = self._generar_hash(customer)

            # Buscar hash guardado en el diccionario (O(1))
            hash_guardado = hashes_guardados.get(code)

            if hash_guardado is None:
                cambios['nuevos'].append(customer)
            elif hash_guardado != hash_actual:
                cambios['modificados'].append(customer)

            # Preparar para guardar en lote
            hashes_para_guardar.append((code, hash_actual))

        # 5. ✅ GUARDAR TODOS LOS HASHES DE UNA VEZ
        self.info(f"   💾 Guardando {len(hashes_para_guardar)} hashes...")
        self._guardar_hashes_masivo('customers', hashes_para_guardar)
        self.info(f"   ✅ Hashes guardados")

        # 6. Detectar eliminados
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

        self.info(
            f"Cambios: {len(cambios['nuevos'])} nuevos, "
            f"{len(cambios['modificados'])} modificados, "
            f"{len(cambios['eliminados'])} eliminados"
        )

        return cambios

    except Exception as e:
        self.error(f"❌ Error detectando cambios: {e}")
        import traceback
        self.error(traceback.format_exc())
        return cambios


# ===========================================================================
# COMPARACIÓN DE RENDIMIENTO
# ===========================================================================

"""
MÉTODO ACTUAL (lento):
- 50,980 clientes con pending_sync
- 50,980 queries SELECT para obtener hashes
- 50,980 queries UPDATE/INSERT para guardar hashes
- Total: ~102,000 queries
- Tiempo estimado: 5-10 minutos

MÉTODO OPTIMIZADO:
- 50,980 clientes con pending_sync
- 1 query SELECT para obtener todos los hashes
- 1 query executemany para guardar todos los hashes
- Total: ~3 queries
- Tiempo estimado: 10-30 segundos

MEJORA: 10-20x más rápido
"""
