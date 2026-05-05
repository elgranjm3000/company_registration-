"""
SOLUCIÓN: Usar from_date para optimizar descarga de clientes desde la API

Este archivo muestra cómo implementar from_date para solo descargar
clientes modificados desde la última sincronización.
"""

# ===========================================================================
# MÉTODO 1: Guardar última fecha en sync_config
# ===========================================================================

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
            self.info(f"   📅 Última sincronización: {last_date}")
            return last_date
        else:
            self.info(f"   📅 Primera sincronización (sin from_date)")
            return None

    except Exception as e:
        self.warning(f"   ⚠️  Error obteniendo última fecha: {e}")
        return None


def _save_last_sync_date(self):
    """
    Guardar fecha actual en sync_config como última sincronización.
    """
    try:
        from datetime import datetime

        # Fecha actual en formato ISO para API
        # La API espera formato: 2024-03-13T10:00:00.000000Z
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


# ===========================================================================
# MÉTODO 2: Modificar detect_new_from_api() para usar from_date
# ===========================================================================

def detect_new_from_api_optimized(self) -> List[Dict]:
    """
    Detectar NUEVOS clientes en la API REST usando from_date.
    Solo descarga clientes modificados desde la última sincronización.

    Returns:
        Lista de dicts con clientes nuevos desde la API
    """
    nuevos_clientes = []

    try:
        self.info("\n" + "="*70)
        self.info("📥 DETECTANDO NUEVOS CLIENTES DESDE API REST (OPTIMIZADO)")
        self.info("="*70)

        # 1. Obtener fecha de última sincronización
        from_date = self._get_last_sync_date()

        # 2. Obtener clientes desde la API con from_date
        if from_date:
            self.info(f"Obteniendo clientes modificados desde: {from_date}")
            clientes_api = list(self.api_client.get_all(
                company_id=self.company_id,
                from_date=from_date  # ✅ SOLO modifica desde esta fecha
            ))
        else:
            self.info(f"Obteniendo TODOS los clientes (primera vez)")
            clientes_api = list(self.api_client.get_all(
                company_id=self.company_id
            ))

        self.info(f"   Total clientes obtenidos de API: {len(clientes_api)}")

        if not clientes_api:
            self.info(f"   ✨ No hay clientes nuevos/modificados")
            return []

        # 3. Obtener códigos YA SINCRONIZADOS desde sync_hashes
        self.pg_cursor.execute("""
            SELECT TRIM(record_key) as record_key
            FROM sync_hashes
            WHERE table_name = 'customers'
              AND company_id = %s
              AND deleted_at IS NULL
        """, (self.company_id,))
        codigos_sincronizados = {row[0] for row in self.pg_cursor.fetchall()}
        self.info(f"   Total clientes ya sincronizados: {len(codigos_sincronizados)}")

        # 4. Detectar nuevos (existen en API pero NO están en sync_hashes)
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


# ===========================================================================
# MÉTODO 3: Llamar a _save_last_sync_date() después de sincronizar exitosamente
# ===========================================================================

def execute_optimized(self) -> Dict[str, int]:
    """
    Ejecutar sincronización bidireccional optimizada con from_date.

    La diferencia clave es que guarda la fecha después de sincronizar
    exitosamente desde la API.
    """
    stats = {
        'to_api_created': 0,
        'to_api_updated': 0,
        'to_api_deleted': 0,
        'from_api_new': 0
    }

    try:
        self.info("\n" + "="*70)
        self.info("🔄 SINCRONIZACIÓN BIDIRECCIONAL DE CLIENTES (OPTIMIZADA)")
        self.info("="*70)

        # ===================================================================
        # PASO 1: PostgreSQL → API REST (cambios locales)
        # ===================================================================
        self.info("\n📤 PASO 1: Sincronizando cambios LOCALES a la API REST...")
        self.info("-"*70)

        cambios = self.detect_changes()

        if cambios['nuevos'] or cambios['modificados']:
            success = self.sync_to_api(cambios)
            stats['to_api_created'] = self.stats.get('created', 0)
            stats['to_api_updated'] = self.stats.get('updated', 0)

            if success and (self.stats.get('created', 0) > 0 or self.stats.get('updated', 0) > 0):
                self._update_sync_hashes(cambios)
                self.info(f"✅ Actualizados {len(cambios['nuevos']) + len(cambios['modificados'])} registros en sync_hashes")

        if cambios['eliminados']:
            self.delete_from_api(cambios['eliminados'])
            stats['to_api_deleted'] = self.stats.get('deleted', 0)

        # ===================================================================
        # PASO 2: API REST → PostgreSQL (nuevos desde backend) CON from_date
        # ===================================================================
        self.info("\n📥 PASO 2: Detectando NUEVOS clientes desde API REST...")
        self.info("-"*70)

        # ✅ Usar versión optimizada con from_date
        nuevos_desde_api = self.detect_new_from_api_optimized()

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


# ===========================================================================
# EJEMPLO DE USO
# ===========================================================================

"""
# ANTES (Sin from_date):
# - Descarga 60,000 clientes cada vez
# - Tarda 5-10 minutos
clientes_api = list(api_client.get_all(company_id=1))

# DESPUÉS (Con from_date):
# - Primera vez: Descarga 60,000 clientes
# - Segunda vez: Descarga solo 50 clientes modificados ayer
# - Tarda 10 segundos en lugar de 5 minutos

# Primera sincronización (sin from_date):
from_date = None  # No hay fecha anterior
clientes_api = list(api_client.get_all(company_id=1, from_date=from_date))
# → Descarga 60,000 clientes

# Guarda fecha: '2024-03-20T10:30:00.000000Z'
_save_last_sync_date()

# Segunda sincronización (con from_date):
from_date = '2024-03-20T10:30:00.000000Z'  # Fecha guardada
clientes_api = list(api_client.get_all(company_id=1, from_date=from_date))
# → Descarga solo 50 clientes modificados desde esa fecha
"""
