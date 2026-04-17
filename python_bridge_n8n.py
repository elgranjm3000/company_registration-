#!/usr/bin/env python3
"""
Python Bridge para PostgreSQL → n8n

Este servicio escucha las notificaciones LISTEN/NOTIFY de PostgreSQL y las envía
a un webhook de n8n en tiempo real.

Uso:
    python python_bridge_n8n.py

Archivos de configuración:
    - bridge_config.json (crear desde bridge_config.json.example)

Requisitos:
    pip install psycopg2-binary requests
"""

import psycopg2
import psycopg2.extensions
import select
import requests
import json
import time
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bridge_n8n.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


# ============================================================================
# CLASE PRINCIPAL DEL BRIDGE
# ============================================================================

class PostgreSQLToN8nBridge:
    """Bridge que escucha PostgreSQL y envía notificaciones a n8n"""

    def __init__(self, config_path: str = 'bridge_config.json'):
        """
        Inicializar el bridge

        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.config = self.load_config(config_path)
        self.pg_conn: Optional[psycopg2.extensions.connection] = None
        self.running = False

        # Mapeo de tablas a sus columnas principales
        self.table_mappings = {
            'products': {
                'primary_key': 'id',
                'columns': ['id', 'name', 'price', 'cost', 'stock', 'active', 'company_id']
            },
            'clients': {
                'primary_key': 'id',
                'columns': ['id', 'name', 'email', 'phone', 'address', 'active', 'company_id']
            },
            'sellers': {
                'primary_key': 'id',
                'columns': ['id', 'name', 'email', 'commission', 'active', 'company_id']
            },
            'sales_operations': {
                'primary_key': 'id',
                'columns': ['id', 'customer_id', 'seller_id', 'total', 'date', 'status', 'company_id']
            }
        }

        # Contadores
        self.stats = {
            'notifications_received': 0,
            'notifications_sent': 0,
            'notifications_failed': 0,
            'start_time': None
        }

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Cargar configuración desde archivo JSON"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"✅ Configuración cargada desde {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"❌ Archivo de configuración no encontrado: {config_path}")
            logger.error(f"   Crea bridge_config.json desde bridge_config.json.example")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando configuración: {e}")
            sys.exit(1)

    def connect_postgresql(self) -> bool:
        """Conectar a PostgreSQL"""
        try:
            pg_config = self.config['postgresql']

            self.pg_conn = psycopg2.connect(
                host=pg_config['host'],
                port=pg_config.get('port', 5432),
                database=pg_config['database'],
                user=pg_config['user'],
                password=pg_config['password'],
                connect_timeout=10
            )

            self.pg_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

            logger.info(f"✅ Conectado a PostgreSQL: {pg_config['database']}")
            return True

        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            return False

    def listen_notifications(self):
        """Escuchar notificaciones LISTEN/NOTIFY de PostgreSQL"""
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute("LISTEN n8n_sync")
            logger.info("🔊 Escuchando notificaciones 'n8n_sync'...")

            self.pg_conn.notifies = []

            while self.running:
                # Esperar notificaciones con timeout de 5 segundos
                if select.select([self.pg_conn], [], [], 5) == ([], [], []):
                    continue

                self.pg_conn.poll()

                # Procesar todas las notificaciones pendientes
                while self.pg_conn.notifies:
                    notify = self.pg_conn.notifies.pop(0)
                    self.process_notification(notify)

        except KeyboardInterrupt:
            logger.info("\n⚠️  Interrumpido por usuario")
        except Exception as e:
            logger.error(f"❌ Error escuchando notificaciones: {e}")
            raise

    def process_notification(self, notify):
        """Procesar una notificación de PostgreSQL"""
        self.stats['notifications_received'] += 1

        try:
            # Parsear payload JSON
            payload = json.loads(notify.payload)

            logger.info(f"📨 Notificación recibida:")
            logger.info(f"   Tabla: {payload['table_name']}")
            logger.info(f"   Operación: {payload['operation']}")
            logger.info(f"   Record ID: {payload['record_id']}")

            # Obtener datos completos del registro
            record_data = self.get_record_data(
                payload['table_name'],
                payload['record_id']
            )

            # Crear payload completo para n8n
            n8n_payload = {
                'table_name': payload['table_name'],
                'operation': payload['operation'],
                'record_id': payload['record_id'],
                'timestamp': payload['timestamp'],
                'company_id': record_data.get('company_id'),
                'record_data': record_data
            }

            # Enviar a n8n
            success = self.send_to_n8n(n8n_payload)

            if success:
                self.stats['notifications_sent'] += 1
            else:
                self.stats['notifications_failed'] += 1

        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parseando JSON de notificación: {e}")
            logger.error(f"   Payload: {notify.payload}")
            self.stats['notifications_failed'] += 1

        except Exception as e:
            logger.error(f"❌ Error procesando notificación: {e}")
            import traceback
            traceback.print_exc()
            self.stats['notifications_failed'] += 1

    def get_record_data(self, table_name: str, record_id: int) -> Dict[str, Any]:
        """Obtener datos completos de un registro"""
        try:
            if table_name not in self.table_mappings:
                logger.warning(f"⚠️  Tabla no mapeada: {table_name}")
                return {'id': record_id}

            mapping = self.table_mappings[table_name]
            columns = mapping['columns']
            primary_key = mapping['primary_key']

            cursor = self.pg_conn.cursor()

            query = f"SELECT {', '.join(columns)} FROM {table_name} WHERE {primary_key} = %s"
            cursor.execute(query, (record_id,))

            row = cursor.fetchone()

            if row:
                # Convertir a diccionario
                record_data = dict(zip(columns, row))
                logger.debug(f"   Datos obtenidos: {record_data}")
                return record_data
            else:
                logger.warning(f"⚠️  Registro no encontrado: {table_name}.{record_id}")
                return {'id': record_id}

        except Exception as e:
            logger.error(f"❌ Error obteniendo datos del registro: {e}")
            return {'id': record_id}

    def send_to_n8n(self, payload: Dict[str, Any]) -> bool:
        """Enviar payload al webhook de n8n"""
        try:
            webhook_url = self.config['n8n']['webhook_url']

            logger.info(f"📤 Enviando a n8n...")
            logger.debug(f"   Payload: {json.dumps(payload, indent=2)}")

            response = requests.post(
                webhook_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'PostgreSQL-Bridge/1.0'
                },
                timeout=self.config['n8n'].get('timeout', 10)
            )

            if response.status_code == 200:
                logger.info(f"✅ Enviado a n8n exitosamente")
                return True
            else:
                logger.warning(f"⚠️  n8n respondió con status {response.status_code}")
                logger.warning(f"   Response: {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout conectando a n8n")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Error de conexión a n8n: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error enviando a n8n: {e}")
            return False

    def print_stats(self):
        """Imprimir estadísticas"""
        if self.stats['start_time']:
            uptime = datetime.now() - self.stats['start_time']
            logger.info("=" * 70)
            logger.info("📊 ESTADÍSTICAS:")
            logger.info(f"   Tiempo ejecutando: {uptime}")
            logger.info(f"   Notificaciones recibidas: {self.stats['notifications_received']}")
            logger.info(f"   Notificaciones enviadas: {self.stats['notifications_sent']}")
            logger.info(f"   Notificaciones fallidas: {self.stats['notifications_failed']}")
            logger.info("=" * 70)

    def start(self):
        """Iniciar el bridge"""
        logger.info("=" * 70)
        logger.info("🚀 INICIANDO POSTGRESQL → n8n BRIDGE")
        logger.info("=" * 70)

        if not self.connect_postgresql():
            logger.error("❌ No se pudo conectar a PostgreSQL")
            sys.exit(1)

        self.running = True
        self.stats['start_time'] = datetime.now()

        try:
            self.listen_notifications()
        finally:
            self.print_stats()
            self.stop()

    def stop(self):
        """Detener el bridge"""
        logger.info("🛑 Deteniendo bridge...")
        self.running = False

        if self.pg_conn:
            self.pg_conn.close()
            logger.info("✅ Conexión PostgreSQL cerrada")


# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

def main():
    """Función principal"""

    # Verificar que existe el archivo de configuración
    config_path = 'bridge_config.json'

    if not os.path.exists(config_path):
        logger.error(f"❌ No existe el archivo de configuración: {config_path}")
        logger.error(f"   Cópialo desde bridge_config.json.example y configúralo")
        sys.exit(1)

    # Crear e iniciar bridge
    bridge = PostgreSQLToN8nBridge(config_path)

    try:
        bridge.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrumpido por usuario")
        bridge.print_stats()
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
