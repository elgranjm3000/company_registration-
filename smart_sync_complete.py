"""
MÓDULO: Smart Sync Complete
Sincronización inteligente PostgreSQL → MySQL con detección de cambios
Usa tabla sync_hashes en PostgreSQL para almacenar estado

Autor: Sistema de Sincronización
Fecha: 2025-01-22
Versión: 1.0
"""

import psycopg2
import pymysql  # Cambiado de mysql.connector a pymysql (100% Python puro)
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import sys
import os

# Importar logger de errores de MySQL (SILENCIOSO - solo guarda en archivo)
try:
    from mysql_error_logger import get_mysql_error_logger, log_mysql_error, log_mysql_batch_error
    MYSQL_ERROR_LOGGER_AVAILABLE = True
except ImportError:
    MYSQL_ERROR_LOGGER_AVAILABLE = False

# Importar funciones existentes de app.py
def laravel_hash_make(password):
    """Generar hash compatible con Laravel Hash::make()"""
    import bcrypt
    if isinstance(password, str):
        password = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password, salt)
    laravel_hash = hashed.decode('utf-8').replace('$2b$', '$2y$')
    return laravel_hash

def safe_float(value):
    """Convertir a float de forma segura"""
    if isinstance(value, memoryview):
        try:
            value = value.tobytes().decode('utf-8')
        except Exception:
            return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


class SmartSyncComplete:
    """
    Módulo de sincronización inteligente con tabla de hashes

    Uso:
        sync = SmartSyncComplete(app, postgresql_config, mysql_config, company_rif, company_email)
        sync.inicializar_tabla_hashes()
        sync.ejecutar_sync_completa()
    """

    def __init__(self, app, postgresql_config: dict, mysql_config: dict, company_rif: str, company_email: str, company_name: str = '', progress_callback=None, log_callback=None):
        """
        Inicializar módulo de sincronización

        Args:
            app: Instancia de CompleteSyncApp o ServiceApp
            postgresql_config: Dict con configuración PostgreSQL
            mysql_config: Dict con configuración MySQL
            company_rif: RIF de la empresa
            company_email: Email de la empresa
            company_name: Nombre de la empresa (opcional)
            progress_callback: Función callback para reportar progreso (opcional)
                              Recibe dict: {'entity': 'products', 'current': 8, 'total': 1800}
            log_callback: Función callback para enviar logs a la UI (opcional)
                         Recibe: (message: str, log_type: str)
        """
        self.app = app
        self.postgresql_config = postgresql_config
        self.mysql_config = mysql_config
        self.company_rif = company_rif
        self.company_email = company_email
        self.company_name = company_name  # ✅ Agregado
        self.company_id = None  # Se obtendrá dinámicamente de MySQL
        self.sync_running = True
        self.progress_callback = progress_callback  # Callback para reportar progreso
        self.log_callback = log_callback  # Callback para enviar logs a la UI
        self.progress_active = False  # Flag para saber si hay un contador activo

        # Mensaje de error específico para mostrar en messagebox
        self.error_message = None  # Se llena cuando hay un error específico

        # Información de progreso accesible desde la UI
        self.progress_info = {
            'entity': '',      # 'products', 'customers', 'categories', etc.
            'current': 0,      # Progreso actual
            'total': 0,        # Total a procesar
            'percentage': 0.0  # Porcentaje completado
        }

        # Estadísticas
        self.stats = {
            'products': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'customers': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'sellers': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'categories': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'quotes': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0, 'estados_actualizados': 0}
        }

        # 🔍 Logger de errores de MySQL (SILENCIOSO - solo guarda en archivo)
        self.mysql_error_logger = None
        if MYSQL_ERROR_LOGGER_AVAILABLE:
            try:
                self.mysql_error_logger = get_mysql_error_logger()
            except Exception:
                pass

        # Conexiones a bases de datos
        self.pg_conn = None
        self.pg_cursor = None
        self.mysql_conn = None
        self.mysql_cursor = None

        # Configurar logging a archivo
        self.log_file = None
        self._setup_file_logging()

        # Sistema de notificaciones
        self.notificaciones_habilitadas = True
        self._verificar_sistema_notificaciones()

        # Tipo de cambio VES a USD (paralelo)
        self.tipo_cambio_ves_usd = None  # Se obtendrá de pyDolarVenezuela
        self.tipo_cambio_obtenido_at = None  # Timestamp de cuando se obtuvo el tipo de cambio

    def _reportar_progreso(self, entity: str, current: int, total: int):
        """
        Reporta progreso de sincronización al callback

        Args:
            entity: Nombre de la entidad ('products', 'customers', 'categories', 'sellers', 'quotes')
            current: Número actual de registros procesados
            total: Total de registros a procesar
        """
        try:
            if total > 0:
                percentage = round((current / total) * 100, 1)

                # Actualizar progress_info (accesible desde la UI)
                self.progress_info = {
                    'entity': entity,
                    'current': current,
                    'total': total,
                    'percentage': percentage
                }

                # Activar flag de progreso al inicio
                if current == 1:
                    self.progress_active = True

                # Mostrar progreso en consola SIEMPRE (visible para el usuario)
                # Usar carriage return para sobrescribir la línea y crear efecto de contador
                import sys
                entity_name = entity.upper()

                # Calcular frecuencia de actualización según el total
                # Para muchos registros, actualizar cada 10; para pocos, actualizar siempre
                if total > 100:
                    update_freq = 10
                elif total > 50:
                    update_freq = 5
                else:
                    update_freq = 1

                # Solo mostrar si es múltiplo de la frecuencia o es el último
                if current % update_freq == 0 or current == total:
                    sys.stdout.write(f"\r  📊 {entity_name}: {current}/{total} ({percentage}%)")
                    sys.stdout.flush()

                # También llamar al callback si existe (para interfaz gráfica)
                if self.progress_callback:
                    try:
                        self.progress_callback({
                            'entity': entity,
                            'current': current,
                            'total': total,
                            'percentage': percentage
                        })
                    except Exception as e:
                        # Silencioso para no interrumpir la sincronización
                        pass

                # Imprimir salto de línea al completar y desactivar flag
                if current == total:
                    print()  # Salto de línea al terminar
                    self.progress_active = False  # Desactivar flag al terminar
        except Exception as e:
            # Error en el reporte de progreso - no interrumpir sincronización
            pass

    def get_progress_info(self):
        """
        Obtener información actual del progreso de sincronización
        Útil para que la interfaz gráfica consulte el estado

        Returns:
            Dict con {entity, current, total, percentage}
        """
        return self.progress_info.copy() if self.progress_info else {
            'entity': '',
            'current': 0,
            'total': 0,
            'percentage': 0.0
        }

    def _setup_file_logging(self):
        """
        Configurar logging a archivo
        Crea directorio 'logs' si no existe
        Archivo: logs/sync_YYYYMMDD_HHMMSS.txt
        """
        try:
            # Crear directorio de logs si no existe
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                self._print_to_console(f"Directorio de logs creado: {log_dir}")

            # Crear nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = f"sync_{timestamp}.txt"
            log_path = os.path.join(log_dir, log_filename)

            # Abrir archivo de log
            self.log_file = open(log_path, 'a', encoding='utf-8')

            # Escribir cabecera del archivo
            self._write_to_log_file("=" * 70)
            self._write_to_log_file(f"SINCRONIZACIÓN PostgreSQL ↔ MySQL")
            self._write_to_log_file(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._write_to_log_file(f"Empresa RIF: {self.company_rif}")
            self._write_to_log_file(f"Empresa Email: {self.company_email}")
            self._write_to_log_file("=" * 70)
            self._write_to_log_file("")

            self._print_to_console(f"📝 Log archivo: {log_path}")

        except Exception as e:
            self._print_to_console(f"⚠️ Error creando archivo de log: {str(e)}")

    def _write_to_log_file(self, mensaje: str):
        """Escribir mensaje al archivo de log"""
        if self.log_file:
            try:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.log_file.write(f"[{timestamp}] {mensaje}\n")
                self.log_file.flush()  # Forzar escritura inmediata
            except Exception as e:
                self._print_to_console(f"⚠️ Error escribiendo log: {str(e)}")

    def _print_to_console(self, mensaje: str):
        """Imprimir a consola (fallback)"""
        print(mensaje)

    def _verificar_sistema_notificaciones(self):
        """Verifica si el sistema de notificaciones está disponible (solo Windows)"""
        import platform

        # Solo intentar cargar notificaciones en Windows
        if platform.system() != 'Windows':
            self.toast = None
            self.notificaciones_habilitadas = False
            return  # Silencioso en Linux/Mac - no es un error

        try:
            from win10toast import ToastNotifier
            self.toast = ToastNotifier()
            self._log("Sistema de notificaciones disponible", "info")
        except ImportError:
            self.toast = None
            self.notificaciones_habilitadas = False
            # No mostrar warning en Windows si no está instalado - es opcional
        except Exception as e:
            self.toast = None
            self.notificaciones_habilitadas = False
            # Silencioso - las notificaciones son opcionales

    def _mostrar_notificacion(self, titulo: str, mensaje: str, duracion: int = 5):
        """
        Muestra notificación de Windows

        Args:
            titulo: Título de la notificación
            mensaje: Mensaje de la notificación
            duracion: Duración en segundos (por defecto 5)
        """
        if not self.notificaciones_habilitadas or not self.toast:
            return

        try:
            self.toast.show_toast(
                title=titulo,
                message=mensaje,
                duration=duracion,
                threaded=True  # No bloquear el hilo principal
            )
        except Exception as e:
            self._log(f"Error mostrando notificación: {str(e)}", "warning")

    def _notificar_nuevos_presupuestos(self, cantidad: int):
        """Notifica cuando hay nuevos presupuestos"""
        if cantidad > 0:
            self._mostrar_notificacion(
                titulo="🔄 Sync System - Nuevos Presupuestos",
                mensaje=f"Tienes {cantidad} nuevo(s) presupuesto(s) de MySQL sincronizados",
                duracion=10
            )

    def _close_log_file(self):
        """Cerrar archivo de log y escribir resumen final"""
        if self.log_file:
            try:
                # Escribir resumen final
                self._write_to_log_file("")
                self._write_to_log_file("=" * 70)
                self._write_to_log_file("FIN DE SINCRONIZACIÓN")
                self._write_to_log_file(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                # Escribir estadísticas si existen
                if hasattr(self, 'stats') and self.stats:
                    self._write_to_log_file("")
                    self._write_to_log_file("ESTADÍSTICAS FINALES:")
                    for entidad, stats in self.stats.items():
                        if stats.get('nuevos') or stats.get('modificados') or stats.get('errores'):
                            self._write_to_log_file(
                                f"  {entidad.capitalize()}: "
                                f"{stats.get('nuevos', 0)} nuevos, "
                                f"{stats.get('modificados', 0)} modificados, "
                                f"{stats.get('errores', 0)} errores"
                            )

                self._write_to_log_file("=" * 70)
                self._write_to_log_file("")

                # Cerrar archivo
                self.log_file.close()
                self.log_file = None
                self._print_to_console("📝 Archivo de log cerrado")
            except Exception as e:
                self._print_to_console(f"⚠️ Error cerrando archivo de log: {str(e)}")

    def _log(self, mensaje: str, tipo: str = 'info'):
        """
        Enviar log a través de la app y al archivo

        Args:
            mensaje: Mensaje a loggear
            tipo: Tipo de log (info, success, warning, error, debug)
        """
        # Enviar al callback si existe (método directo)
        if self.log_callback:
            self.log_callback(mensaje, tipo)
        # Enviar a la interfaz gráfica (si existe)
        elif hasattr(self.app, 'log_message'):
            self.app.log_message(mensaje, tipo)
        else:
            # Fallback para uso sin interfaz gráfica
            # NO imprimir logs DEBUG en consola cuando hay un contador activo
            # para no interrumpir el carriage return (\r) del contador
            if not (self.progress_active and tipo == 'debug'):
                self._print_to_console(f"[{tipo.upper()}] {mensaje}")

        # SIEMPRE escribir al archivo de log
        log_prefix = {
            'info': 'ℹ️  INFO',
            'success': '✅ SUCCESS',
            'warning': '⚠️  WARNING',
            'error': '❌ ERROR',
            'debug': '🔍 DEBUG'
        }.get(tipo, 'INFO')

        self._write_to_log_file(f"{log_prefix}: {mensaje}")

    # ====================================================================
    # INICIALIZACIÓN
    # ====================================================================

    def inicializar_tabla_hashes(self) -> bool:
        """
        Crear tabla sync_hashes si no existe

        También crea:
        - Columna deleted_at para tracking de eliminaciones
        - Trigger para marcar productos eliminados automáticamente

        Returns:
            True si se creó o ya existía, False si hubo error
        """
        # No mostrar mensaje técnico - es transparente para el usuario

        try:
            self.pg_conn = psycopg2.connect(**self.postgresql_config)
            self.pg_cursor = self.pg_conn.cursor()

            create_table_query = """
            CREATE TABLE IF NOT EXISTS sync_hashes (
                id SERIAL PRIMARY KEY,
                table_name VARCHAR(50) NOT NULL,
                record_key VARCHAR(100) NOT NULL,
                record_hash VARCHAR(32) NOT NULL,
                last_sync_data TEXT,
                synced_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                company_id INTEGER,
                UNIQUE(table_name, record_key, company_id)
            );
            """

            self.pg_cursor.execute(create_table_query)

            # Crear índices de forma compatible con PostgreSQL 9
            # (PostgreSQL 9 no soporta CREATE INDEX IF NOT EXISTS)
            self._crear_indice_sync_hashes()

            # Agregar columna deleted_at si no existe
            self._agregar_columna_deleted_at()

            # Agregar columna pending_sync si no existe (para optimización de UPDATE)
            self._agregar_columna_pending_sync()

            # Crear tabla de configuración para almacenar company_id
            self._crear_tabla_sync_config()

            # NOTA: NO actualizamos company_id aquí porque aún no hay conexión a MySQL
            # Se actualizará en ejecutar_sync_completa() después de conectar

            # Crear triggers de eliminación para todas las entidades
            self._crear_trigger_eliminacion_products()
            self._crear_trigger_eliminacion_categories()
            self._crear_trigger_eliminacion_customers()
            self._crear_trigger_eliminacion_sellers()

            # Crear triggers de UPDATE para optimizar detección de cambios
            self._crear_trigger_actualizacion_products()
            self._crear_trigger_actualizacion_customers()

            self.pg_conn.commit()

            # No mostrar mensaje de éxito - es transparente para el usuario
            return True

        except Exception as e:
            self._log(f"❌ Error creando tabla sync_hashes: {str(e)}", "error")
            return False

    def _agregar_columna_deleted_at(self):
        """
        Agrega la columna deleted_at a sync_hashes si no existe
        """
        try:
            # Verificar si la columna existe
            self.pg_cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'sync_hashes'
                AND column_name = 'deleted_at'
            """)
            existe = self.pg_cursor.fetchone()

            if not existe:
                # Agregar columna
                self.pg_cursor.execute("""
                    ALTER TABLE sync_hashes
                    ADD COLUMN deleted_at TIMESTAMP NULL
                """)
                self.pg_conn.commit()
                # Silencioso - transparente para el usuario
        except Exception as e:
            # Si hay error, continuar (la columna podría ya existir)
            self.pg_conn.rollback()

    def _agregar_columna_pending_sync(self):
        """
        Agrega la columna pending_sync a sync_hashes si no existe
        Esta columna se usa para optimizar la detección de cambios con triggers UPDATE
        """
        try:
            # Verificar si la columna existe
            self.pg_cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'sync_hashes'
                AND column_name = 'pending_sync'
            """)
            existe = self.pg_cursor.fetchone()

            if not existe:
                # Agregar columna
                self.pg_cursor.execute("""
                    ALTER TABLE sync_hashes
                    ADD COLUMN pending_sync BOOLEAN DEFAULT FALSE
                """)
                self.pg_conn.commit()

                # Crear índice para optimizar queries de pending_sync
                try:
                    self.pg_cursor.execute("""
                        CREATE INDEX idx_sync_hashes_pending_sync
                        ON sync_hashes(pending_sync, table_name, company_id)
                        WHERE pending_sync = TRUE
                    """)
                    self.pg_conn.commit()
                except Exception as idx_error:
                    # El índice podría ya existir
                    self.pg_conn.rollback()

                self._log("   ✅ Campo pending_sync agregado para optimizar detección de cambios", "info")
        except Exception as e:
            # Si hay error, continuar (la columna podría ya existir)
            self.pg_conn.rollback()

    def _crear_tabla_sync_config(self):
        """
        Crea la tabla sync_config para almacenar configuración de sincronización
        Incluye el company_id que deben usar los triggers UPDATE
        """
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS sync_config (
                key VARCHAR(100) PRIMARY KEY,
                value INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            self.pg_cursor.execute(create_table_query)
            self.pg_conn.commit()
        except Exception as e:
            self.pg_conn.rollback()

    def _actualizar_company_id_en_config(self):
        """
        Actualiza el company_id en sync_config desde MySQL
        Los triggers UPDATE leen este valor para usar el company_id correcto

        Compatible con PostgreSQL 9.1+ (no usa ON CONFLICT)
        """
        try:
            # Obtener company_id desde MySQL
            company_id = self._get_company_id_from_companies()
            if not company_id:
                # Si no se puede obtener, usar un valor por defecto
                company_id = 1

            # Verificar si ya existe el registro
            self.pg_cursor.execute("""
                SELECT value FROM sync_config WHERE key = 'current_company_id'
            """)
            existe = self.pg_cursor.fetchone()

            if existe:
                # Ya existe: Actualizar
                update_query = """
                UPDATE sync_config
                SET value = %s, updated_at = NOW()
                WHERE key = 'current_company_id'
                """
                self.pg_cursor.execute(update_query, (company_id,))
            else:
                # No existe: Insertar
                insert_query = """
                INSERT INTO sync_config (key, value, updated_at)
                VALUES ('current_company_id', %s, NOW())
                """
                self.pg_cursor.execute(insert_query, (company_id,))

            self.pg_conn.commit()

            self._log(f"   ✅ Company_id configurado en sync_config: {company_id}", "debug")
        except Exception as e:
            # Si hay error, continuar (no es crítico)
            self.pg_conn.rollback()
            self._log(f"   ⚠️ Error actualizando company_id en config: {str(e)}", "warning")

    def _crear_trigger_eliminacion_products(self):
        """
        Crea el trigger que marca productos como eliminados en sync_hashes
        """
        try:
            # Crear función del trigger
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_product_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Marcar el registro en sync_hashes como eliminado
                UPDATE sync_hashes
                SET deleted_at = NOW()
                WHERE table_name = 'products'
                AND record_key = OLD.code;

                -- Si no existe en sync_hashes, insertar el registro marcado como eliminado
                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                    VALUES ('products', OLD.code, md5(OLD.code::text), NOW());
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            # Crear trigger (compatible con PostgreSQL 9.1+: EXECUTE PROCEDURE)
            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_products_mark_deleted_sync_hashes ON products;

            CREATE TRIGGER tr_products_mark_deleted_sync_hashes
                AFTER DELETE ON products
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_product_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
            # Silencioso - transparente para el usuario

        except Exception as e:
            # Si hay error, continuar (el trigger podría ya existir)
            self.pg_conn.rollback()

    def _crear_trigger_eliminacion_categories(self):
        """
        Crea el trigger que marca department (categories en MySQL) como eliminados en sync_hashes

        NOTA: En PostgreSQL la tabla se llama 'department', en MySQL es 'categories'
        """
        try:
            # Crear función del trigger
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_department_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            BEGIN
                -- Marcar el registro en sync_hashes como eliminado
                UPDATE sync_hashes
                SET deleted_at = NOW()
                WHERE table_name = 'categories'
                AND record_key = OLD.code;

                -- Si no existe en sync_hashes, insertar el registro marcado como eliminado
                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                    VALUES ('categories', OLD.code, md5(OLD.code::text), NOW());
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            # Crear trigger en tabla department (compatible con PostgreSQL 9.1+: EXECUTE PROCEDURE)
            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_department_mark_deleted_sync_hashes ON department;

            CREATE TRIGGER tr_department_mark_deleted_sync_hashes
                AFTER DELETE ON department
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_department_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
            # Silencioso - transparente para el usuario

        except Exception as e:
            # Si hay error, continuar (el trigger podría ya existir)
            self.pg_conn.rollback()

    def _crear_trigger_eliminacion_customers(self):
        """
        Crea el trigger que marca clients (customers en MySQL) como eliminados en sync_hashes

        NOTA: En PostgreSQL la tabla se llama 'clients', en MySQL es 'customers'
        """
        try:
            # Eliminar trigger y función antiguos si existen
            # Esto asegura que siempre se use la versión más reciente
            drop_query = """
            -- Eliminar el trigger primero (depende de la función)
            DROP TRIGGER IF EXISTS tr_clients_mark_deleted_sync_hashes ON clients;

            -- Eliminar la función antigua completamente
            DROP FUNCTION IF EXISTS trigger_mark_client_deleted_sync_hashes();
            """
            self.pg_cursor.execute(drop_query)

            # Crear función del trigger con la versión corregida
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_client_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_exists INTEGER;
            BEGIN
                -- Verificar si ya existe el registro en sync_hashes
                SELECT COUNT(*) INTO v_exists
                FROM sync_hashes
                WHERE table_name = 'customers'
                AND record_key = OLD.code;

                -- Si existe, actualizar deleted_at
                IF v_exists > 0 THEN
                    UPDATE sync_hashes
                    SET deleted_at = NOW()
                    WHERE table_name = 'customers'
                    AND record_key = OLD.code;
                ELSE
                    -- Si no existe, insertar nuevo registro con deleted_at
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                    VALUES ('customers', OLD.code, md5(OLD.code::text), NOW());
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            # Crear trigger en tabla clients (compatible con PostgreSQL 9.1+: EXECUTE PROCEDURE)
            create_trigger_query = """
            CREATE TRIGGER tr_clients_mark_deleted_sync_hashes
                AFTER DELETE ON clients
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_client_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()

            # Log de éxito
            self._log("   ✅ Trigger de eliminación de clientes creado/actualizado", "info")

        except Exception as e:
            # Si hay error, continuar (el trigger podría ya existir)
            self.pg_conn.rollback()

    def _crear_trigger_eliminacion_sellers(self):
        """
        Crea el trigger que marca sellers como eliminados en sync_hashes
        """
        try:
            # Eliminar trigger y función antiguos si existen
            # Esto asegura que siempre se use la versión más reciente
            drop_query = """
            -- Eliminar el trigger primero (depende de la función)
            DROP TRIGGER IF EXISTS tr_sellers_mark_deleted_sync_hashes ON sellers;

            -- Eliminar la función antigua completamente
            DROP FUNCTION IF EXISTS trigger_mark_seller_deleted_sync_hashes();
            """
            self.pg_cursor.execute(drop_query)

            # Crear función del trigger con la versión corregida
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_seller_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_exists INTEGER;
            BEGIN
                -- Verificar si ya existe el registro en sync_hashes
                SELECT COUNT(*) INTO v_exists
                FROM sync_hashes
                WHERE table_name = 'sellers'
                AND record_key = OLD.email;

                -- Si existe, actualizar deleted_at
                IF v_exists > 0 THEN
                    UPDATE sync_hashes
                    SET deleted_at = NOW()
                    WHERE table_name = 'sellers'
                    AND record_key = OLD.email;
                ELSE
                    -- Si no existe, insertar nuevo registro con deleted_at
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at)
                    VALUES ('sellers', OLD.email, md5(OLD.email::text), NOW());
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            # Crear trigger (compatible con PostgreSQL 9.1+: EXECUTE PROCEDURE)
            create_trigger_query = """
            CREATE TRIGGER tr_sellers_mark_deleted_sync_hashes
                AFTER DELETE ON sellers
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_seller_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()

            # Log de éxito
            self._log("   ✅ Trigger de eliminación de vendedores creado/actualizado", "info")

        except Exception as e:
            # Si hay error, continuar (el trigger podría ya existir)
            self.pg_conn.rollback()

    def _crear_indice_sync_hashes(self):
        """
        Crear índices de sync_hashes de forma compatible con PostgreSQL 9
        PostgreSQL 9 no soporta CREATE INDEX IF NOT EXISTS
        """
        indices = [
            ("idx_sync_hashes_lookup", "CREATE INDEX idx_sync_hashes_lookup ON sync_hashes(table_name, record_key, company_id)"),
            ("idx_sync_hashes_table", "CREATE INDEX idx_sync_hashes_table ON sync_hashes(table_name, company_id)")
        ]

        for nombre_idx, query in indices:
            try:
                self.pg_cursor.execute(query)
                self.pg_conn.commit()  # Commit después de crear índice
                # No mostrar mensaje de creación - es transparente para el usuario
            except Exception as e:
                # Silenciar todos los errores de índices (no son relevantes para el usuario)
                error_msg = str(e).lower()
                if "already exists" in error_msg:
                    # El índice ya existe - es normal, no hacer nada
                    self.pg_conn.rollback()  # Rollback para limpiar la transacción abortada
                else:
                    # Otro error de índice - silenciar también (no relevante para el usuario)
                    self.pg_conn.rollback()  # Rollback para limpiar la transacción abortada

    def _crear_trigger_actualizacion_products(self):
        """
        Crea el trigger que marca productos como actualizados en sync_hashes
        Esto optimiza la detección de cambios: solo se sincronizan los productos con pending_sync = true

        Compatible con PostgreSQL 9.1+ (no usa ON CONFLICT)

        El trigger lee el company_id desde sync_config (se mantiene sincronizado con MySQL)
        """
        try:
            # Crear función del trigger
            # Lee el company_id desde sync_config para usar el valor correcto
            # Compatible con PostgreSQL 9.1: Usa SELECT + IF/THEN en lugar de ON CONFLICT
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_product_updated_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
                v_exists INTEGER;
            BEGIN
                -- Obtener el company_id desde sync_config
                SELECT value INTO v_company_id
                FROM sync_config
                WHERE key = 'current_company_id';

                -- Si no existe, usar 1 como fallback
                IF v_company_id IS NULL THEN
                    v_company_id := 1;
                END IF;

                -- Verificar si ya existe el registro
                SELECT 1 INTO v_exists
                FROM sync_hashes
                WHERE table_name = 'products'
                  AND record_key = NEW.code
                  AND company_id = v_company_id
                LIMIT 1;

                IF v_exists = 1 THEN
                    -- Ya existe: Actualizar
                    UPDATE sync_hashes
                    SET pending_sync = TRUE,
                        updated_at = NOW()
                    WHERE table_name = 'products'
                      AND record_key = NEW.code
                      AND company_id = v_company_id;
                ELSE
                    -- No existe: Insertar
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
                    VALUES ('products', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            # Crear trigger (compatible con PostgreSQL 9.1+: EXECUTE PROCEDURE)
            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_products_mark_updated_sync_hashes ON products;

            CREATE TRIGGER tr_products_mark_updated_sync_hashes
                AFTER UPDATE ON products
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_product_updated_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
            self._log("   ✅ Trigger de actualización de productos creado", "info")

        except Exception as e:
            # Si hay error, continuar (el trigger podría ya existir)
            self.pg_conn.rollback()
            self._log(f"   ⚠️ Error creando trigger UPDATE de products: {str(e)}", "warning")

    def _crear_trigger_actualizacion_customers(self):
        """
        Crea el trigger que marca clientes como actualizados en sync_hashes
        Esto optimiza la detección de cambios: solo se sincronizan los clientes con pending_sync = true

        Compatible con PostgreSQL 9.1+ (no usa ON CONFLICT)

        El trigger lee el company_id desde sync_config (se mantiene sincronizado con MySQL)
        """
        try:
            # Crear función del trigger
            # Compatible con PostgreSQL 9.1: Usa SELECT + IF/THEN en lugar de ON CONFLICT
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_client_updated_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
                v_exists INTEGER;
            BEGIN
                -- Obtener el company_id desde sync_config
                SELECT value INTO v_company_id
                FROM sync_config
                WHERE key = 'current_company_id';

                -- Si no existe, usar 1 como fallback
                IF v_company_id IS NULL THEN
                    v_company_id := 1;
                END IF;

                -- Verificar si ya existe el registro
                SELECT 1 INTO v_exists
                FROM sync_hashes
                WHERE table_name = 'customers'
                  AND record_key = NEW.code
                  AND company_id = v_company_id
                LIMIT 1;

                IF v_exists = 1 THEN
                    -- Ya existe: Actualizar
                    UPDATE sync_hashes
                    SET pending_sync = TRUE,
                        updated_at = NOW()
                    WHERE table_name = 'customers'
                      AND record_key = NEW.code
                      AND company_id = v_company_id;
                ELSE
                    -- No existe: Insertar
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
                    VALUES ('customers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            # Crear trigger (compatible con PostgreSQL 9.1+: EXECUTE PROCEDURE)
            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_clients_mark_updated_sync_hashes ON clients;

            CREATE TRIGGER tr_clients_mark_updated_sync_hashes
                AFTER UPDATE ON clients
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_client_updated_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
            self._log("   ✅ Trigger de actualización de clientes creado", "info")

        except Exception as e:
            # Si hay error, continuar (el trigger podría ya existir)
            self.pg_conn.rollback()
            self._log(f"   ⚠️ Error creando trigger UPDATE de clients: {str(e)}", "warning")

    def _conectar_bases_datos(self) -> bool:
        """
        Establecer conexiones con PostgreSQL y MySQL

        Returns:
            True si ambas conexiones exitosas
        """
        try:
            # Conectar PostgreSQL
            try:
                self.pg_conn = psycopg2.connect(**self.postgresql_config)
                self.pg_cursor = self.pg_conn.cursor()
                self._log("✅ Conectado a PostgreSQL", "success")
            except Exception as e:
                self._log(f"❌ Error conectando PostgreSQL: {type(e).__name__}: {str(e)}", "error")
                # Datos de conexión ocultos por seguridad
                return False

            # Conectar MySQL (usando pymysql - 100% Python puro)
            try:
                self.mysql_conn = pymysql.connect(
                    host=self.mysql_config['host'],
                    port=int(self.mysql_config.get('port', 3306)),
                    user=self.mysql_config['user'],
                    password=self.mysql_config['password'],
                    database=self.mysql_config['database'],
                    charset='utf8mb4'
                )
                self.mysql_cursor = self.mysql_conn.cursor()
                self._log("✅ Conectado a MySQL (pymysql)", "success")
                # Datos de conexión ocultos por seguridad
            except Exception as e:
                self._log(f"❌ Error conectando MySQL: {type(e).__name__}: {str(e)}", "error")
                # Datos de conexión ocultos por seguridad

                # Mostrar error detallado de pymysql
                if hasattr(e, 'args') and e.args:
                    self._log(f"   Error: {e.args[0] if e.args else str(e)}", "error")

                return False

            return True

        except Exception as e:
            self._log(f"❌ Error general conectando bases de datos: {type(e).__name__}: {str(e)}", "error")
            return False

    def _obtener_company_id(self) -> bool:
        """
        Obtener company_id desde MySQL basado en RIF y email

        Flujo de validación cruzada:
        1. Verificar que existe en tabla 'acceso' de MySQL (RIF y email coincidentes)
        2. Verificar que existe en tabla 'company' de PostgreSQL (por email)
        3. Si existe en ambas, buscar en 'companies' de MySQL
        4. Si existe en companies de MySQL, usar ese ID
        5. Si no existe en companies de MySQL, crear nueva empresa

        Returns:
            True si se encontró o creó el company_id, False si no
        """
        try:
            if not self.mysql_cursor:
                self._log("❌ No hay conexión a MySQL para obtener company_id", "error")
                return False

            self._log(f"🔍 Buscando empresa: RIF={self.company_rif}, Email={self.company_email}", "info")

            # [PASO 1] Verificar que existe en tabla 'acceso' con RIF y email coincidente
            self._log("  🔍 Verificando tabla 'acceso' (RIF y email)...", "debug")
            query_acceso = """
            SELECT id_fiscal, correo_electronico
            FROM acceso
            WHERE id_fiscal = %s AND correo_electronico = %s
            LIMIT 1
            """

            self.mysql_cursor.execute(query_acceso, (self.company_rif, self.company_email))
            acceso = self.mysql_cursor.fetchone()

            if not acceso:
                # ❌ NO existe en acceso con ese RIF y email - DETENER proceso
                self._log("", "error")
                self._log("❌ ERROR: No se encontraron datos coincidentes en tabla 'acceso'", "error")
                self._log(f"   RIF buscado: {self.company_rif}", "error")
                self._log(f"   Email buscado: {self.company_email}", "error")
                self._log("", "error")
                self._log("   💡 La empresa debe estar registrada en 'acceso' con RIF y email coincidentes", "warning")
                self._log("   💡 Verifica que el RIF y email sean correctos", "warning")

                # Guardar mensaje de error para messagebox
                self.error_message = (
                    f"Empresa NO encontrada en la tabla 'acceso' de MySQL\n\n"
                    f"RIF: {self.company_rif}\n"
                    f"Email: {self.company_email}\n\n"
                    f"La empresa debe estar registrada primero en el sistema."
                )
                return False

            self._log("  ✅ Empresa encontrada en tabla 'acceso' (RIF y email coinciden)", "success")

            # [PASO 2] Verificar que existe en tabla 'company' de PostgreSQL (por email)
            self._log("  🔍 Verificando tabla 'company' en PostgreSQL (por email)...", "debug")
            if not self.pg_cursor:
                self._log("❌ No hay conexión a PostgreSQL para verificar company", "error")
                return False

            query_pg_company = """
            SELECT c.id, c.email, c.address, c.phone
            FROM company c
            WHERE LOWER(c.email) = LOWER(%s)
            LIMIT 1
            """

            self.pg_cursor.execute(query_pg_company, (self.company_email,))
            pg_company = self.pg_cursor.fetchone()

            if not pg_company:
                # ❌ NO existe en company de PostgreSQL - DETENER proceso
                self._log("", "error")
                self._log("❌ ERROR: No se encontraron datos en tabla 'company' de PostgreSQL", "error")
                self._log(f"   Email buscado: {self.company_email}", "error")
                self._log("", "error")
                self._log("   💡 La empresa debe estar registrada en la tabla 'company' de PostgreSQL", "warning")
                self._log("   💡 Verifica que el email sea correcto", "warning")

                # Guardar mensaje de error para messagebox
                self.error_message = (
                    f"Empresa NO encontrada en la tabla 'company' de PostgreSQL\n\n"
                    f"Email: {self.company_email}\n\n"
                    f"La empresa debe estar registrada en PostgreSQL con este email."
                )
                return False

            self._log("  ✅ Empresa encontrada en tabla 'company' de PostgreSQL", "success")
            self._log(f"     ID: {pg_company[0]}", "debug")

            # Guardar datos de PostgreSQL para uso posterior
            self._pg_company_data = {
                'id': pg_company[0],
                'email': pg_company[1],
                'address': pg_company[2],
                'phone': pg_company[3]
            }

            # [PASO 3] Buscar si ya existe en tabla 'companies' de MySQL
            self._log("  🔍 Buscando en tabla 'companies'...", "debug")
            query_companies = """
            SELECT id, name
            FROM companies
            WHERE rif = %s
            LIMIT 1
            """

            self.mysql_cursor.execute(query_companies, (self.company_rif,))
            company = self.mysql_cursor.fetchone()

            if company:
                # ✅ Existe en companies - usar ese ID
                self.company_id = company[0]
                company_name = company[1]
                self._log(f"✅ Empresa encontrada: {company_name} (ID: {self.company_id})", "success")
                return True
            else:
                # ⚠️ NO existe en companies - crear nueva empresa
                self._log("  ⚠️ Empresa no encontrada en 'companies', creando registro...", "info")
                self._log("  💡 Validaciones superadas: acceso (MySQL) ✓ y company (PostgreSQL) ✓", "debug")

                # Usar datos ya obtenidos de PostgreSQL (del PASO 2)
                address = self._pg_company_data.get('address')
                phone = self._pg_company_data.get('phone')

                # Usar el nombre del formulario (company_name) o el RIF como fallback
                company_name = self.company_name if hasattr(self, 'company_name') and self.company_name else self.company_rif

                # Insertar nueva empresa (como app.py líneas 718-737)
                insert_query = """
                INSERT INTO companies (
                    address, phone, rif, email, name, key_system_items_id, status, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, 1, 'active', NOW(), NOW()
                )
                """

                self.mysql_cursor.execute(insert_query, (
                    address,
                    phone,
                    self.company_rif,
                    self.company_email.lower(),
                    company_name
                ))

                self.mysql_conn.commit()
                self.company_id = self.mysql_cursor.lastrowid

                self._log(f"✅ Nueva empresa creada: {company_name} (ID: {self.company_id})", "success")
                return True

        except Exception as e:
            self._log(f"❌ Error obteniendo company_id: {type(e).__name__}: {str(e)}", "error")

            # Mostrar detalles del error si es de MySQL (pymysql)
            if hasattr(e, 'args') and e.args:
                self._log(f"   Error: {e.args[0]}", "error")

            return False

    def _get_company_id_from_companies(self) -> Optional[int]:
        """
        Obtener company_id directamente desde tabla companies de MySQL
        Se usa en todas las funciones EXCEPTO al crear la empresa nueva

        Returns:
            company_id o None si no existe
        """
        try:
            if not self.mysql_cursor:
                self._log("❌ No hay conexión a MySQL para obtener company_id", "error")
                return None

            query = """
            SELECT id
            FROM companies
            WHERE rif = %s AND email = %s
            LIMIT 1
            """

            self.mysql_cursor.execute(query, (self.company_rif, self.company_email.lower()))
            result = self.mysql_cursor.fetchone()

            if result:
                return result[0]
            else:
                self._log(f"❌ No se encontró company_id en companies para RIF={self.company_rif}, Email={self.company_email}", "error")
                return None

        except Exception as e:
            self._log(f"❌ Error obteniendo company_id desde companies: {e}", "error")
            return None

    def _obtener_datos_postgres_para_empresa(self) -> Optional[dict]:
        """
        Obtener datos adicionales de PostgreSQL para la empresa
        Igual que app.py líneas 607-628
        """
        try:
            if not self.pg_cursor:
                return None

            query = """
            SELECT
                c.address,
                c.phone,
                COALESCE(
                    CASE
                        WHEN c.description IS NOT NULL AND c.description != ''
                        THEN decode(c.description, 'base64')::text
                        ELSE c.description
                    END,
                    ''
                ) as rif_data,
                COALESCE(e.account, c.email, '') as email
            FROM company c
            LEFT JOIN emails e ON c.email = e.account
            WHERE LOWER(c.email) = LOWER(%s)
            ORDER BY c.id
            LIMIT 1
            """

            self.pg_cursor.execute(query, (self.company_email,))
            result = self.pg_cursor.fetchone()

            if result:
                return {
                    'address': result[0],
                    'phone': result[1],
                    'rif_data': result[2],
                    'email': result[3]
                }
            return None

        except Exception as e:
            self._log(f"  ⚠️ Error obteniendo datos de PostgreSQL: {str(e)}", "warning")
            return None

    def _cerrar_conexiones(self):
        """Cerrar todas las conexiones"""
        try:
            if self.pg_cursor:
                self.pg_cursor.close()
            if self.pg_conn:
                self.pg_conn.close()
            if self.mysql_cursor:
                self.mysql_cursor.close()
            if self.mysql_conn:
                self.mysql_conn.close()
        except Exception as e:
            self._log(f"Error cerrando conexiones: {str(e)}", "warning")

    # ====================================================================
    # GENERACIÓN DE HASHES
    # ====================================================================

    def _generar_hash_product(self, product: tuple) -> str:
        """
        Generar hash MD5 para un producto

        Args:
            product: Tupla con 23 campos (code, unit, description, short_name,
                               department, product_code, unidad, stock, product_type,
                               coin, description_coin, price, cost, higher_price,
                               min_stock, status, image_type, product_image,
                               sale_tax, aliquot, buy_tax, buy_aliquot, unitary_cost)

        Returns:
            Hash MD5 hexadecimal
        """
        try:
            # Campos clave para detectar cambios (TODOS los campos del producto)
            # NUEVO ORDER con 23 campos (se agregaron unit, product_code, unidad)
            campos = (
                str(product[0]) if product[0] else '',  # code
                str(product[1]) if product[1] else '',  # unit (AGREGADO)
                str(product[2]) if product[2] else '',  # description
                str(product[3]) if product[3] else '',  # short_name
                str(product[4]) if product[4] else '',  # department
                str(product[5]) if product[5] else '',  # product_code (AGREGADO)
                str(product[6]) if product[6] else '',  # unidad (AGREGADO)
                str(float(product[7]) if product[7] else 0),  # stock
                str(product[8]) if product[8] else '',  # product_type
                str(product[9]) if product[9] else '',  # coin
                str(product[10]) if product[10] else '',  # description_coin
                str(safe_float(product[11])),           # price
                str(safe_float(product[12])),           # cost
                str(safe_float(product[13])),           # higher_price
                str(safe_float(product[14])),           # min_stock
                str(product[15]) if product[15] else '',  # status
                str(product[16]) if product[16] else '',  # image_type (AGREGADO)
                str(product[17]) if product[17] else '',  # product_image (AGREGADO)
                str(product[18]) if product[18] else '',  # sale_tax
                str(product[19]) if product[19] else '',  # aliquot
                str(product[20]) if product[20] else '',  # buy_tax
                str(safe_float(product[21]) if product[21] else 0),  # buy_aliquot
                str(safe_float(product[22]) if product[22] else 0)   # unitary_cost
            )

            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except Exception as e:
            self._log(f"Error generando hash de producto: {str(e)}", "error")
            return hashlib.md5(str(product[0]).encode()).hexdigest()

    def _generar_hash_customer(self, customer: tuple) -> str:
        """Generar hash MD5 para un cliente"""
        try:
            campos = (
                str(customer[0]) if customer[0] else '',  # code
                str(customer[1]) if customer[1] else '',  # description
                str(customer[4]) if customer[4] else '',  # email
                str(customer[5]) if customer[5] else ''   # phone
            )
            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except:
            return hashlib.md5(str(customer[0]).encode()).hexdigest()

    def _generar_hash_seller(self, seller: tuple) -> str:
        """Generar hash MD5 para un vendedor (sin password para detección de cambios)"""
        try:
            campos = (
                str(seller[0]) if seller[0] else '',  # seller_code
                str(seller[1]) if seller[1] else '',  # description
                str(seller[2]) if seller[2] else '',  # status
                str(safe_float(seller[3])),           # percent_sales
                str(safe_float(seller[4])),           # percent_receivable
                str(seller[5]) if seller[5] else '',  # inkeeper
                str(seller[6]) if seller[6] else '',  # user_code
                str(safe_float(seller[7])),           # percent_gerencial_debit_note
                str(safe_float(seller[8])),           # percent_gerencial_credit_note
                str(safe_float(seller[9])),           # percent_returned_check
                str(seller[10]) if seller[10] else ''  # email
                # NO incluimos password porque bcrypt genera hash diferente cada vez
            )
            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except Exception as e:
            self._log(f"Error generando hash de seller: {str(e)}", "error")
            return hashlib.md5(str(seller[0]).encode()).hexdigest()

    def _generar_hash_category(self, category: tuple) -> str:
        """Generar hash MD5 para una categoría"""
        try:
            campos = (
                str(category[0]) if category[0] else '',  # code
                str(category[1]) if category[1] else ''   # description
            )
            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except:
            return hashlib.md5(str(category[0]).encode()).hexdigest()

    # ====================================================================
    # OBTENER HASH GUARDADO
    # ====================================================================

    def _obtener_hash_guardado(self, table_name: str, record_key: str) -> Optional[Tuple]:
        """
        Obtener hash guardado de sync_hashes

        Args:
            table_name: Nombre de tabla
            record_key: Clave del registro

        Returns:
            Tupla (record_hash, updated_at) o None si no existe
        """
        try:
            query = """
            SELECT record_hash, updated_at
            FROM sync_hashes
            WHERE table_name = %s
              AND record_key = %s
              AND company_id = %s
            """

            company_id = self._get_company_id_from_companies()
            if not company_id:
                return False
            self.pg_cursor.execute(query, (table_name, record_key, company_id))
            return self.pg_cursor.fetchone()
        except Exception as e:
            self._log(f"Error obteniendo hash guardado: {str(e)}", "error")
            return None

    def _guardar_hash(self, table_name: str, record_key: str,
                      record_hash: str, data: dict = None):
        """
        Guardar o actualizar hash en sync_hashes
        Compatible con PostgreSQL 9 (no usa ON CONFLICT)

        Args:
            table_name: Nombre de tabla
            record_key: Clave del registro
            record_hash: Hash MD5
            data: Datos opcionales en JSON
        """
        try:
            # Convertir Decimals a float para serialización JSON
            if data:
                data_json = json.dumps(data, default=str)
            else:
                data_json = None

            # Enfoque compatible con PostgreSQL 9:
            # 1. Primero intentar UPDATE
            # 2. Si no afecta ninguna fila, hacer INSERT

            update_query = """
            UPDATE sync_hashes
            SET record_hash = %s,
                last_sync_data = %s,
                updated_at = NOW(),
                pending_sync = FALSE
            WHERE table_name = %s
              AND record_key = %s
              AND company_id = %s
            """

            self.pg_cursor.execute(update_query,
                                 (record_hash, data_json, table_name, record_key, self._get_company_id_from_companies()))

            # Si el UPDATE no afectó ninguna fila, hacer INSERT
            if self.pg_cursor.rowcount == 0:
                insert_query = """
                INSERT INTO sync_hashes (table_name, record_key, record_hash, last_sync_data, company_id, updated_at, pending_sync)
                VALUES (%s, %s, %s, %s, %s, NOW(), FALSE)
                """
                self.pg_cursor.execute(insert_query,
                                     (table_name, record_key, record_hash, data_json, self._get_company_id_from_companies()))

        except Exception as e:
            self._log(f"Error guardando hash: {str(e)}", "error")

    def _eliminar_hash(self, table_name: str, record_key: str):
        """Eliminar hash de sync_hashes (para registros eliminados)"""
        try:
            query = """
            DELETE FROM sync_hashes
            WHERE table_name = %s
              AND record_key = %s
              AND company_id = %s
            """
            company_id = self._get_company_id_from_companies()
            if not company_id:
                return False
            self.pg_cursor.execute(query, (table_name, record_key, company_id))
        except Exception as e:
            self._log(f"Error eliminando hash: {str(e)}", "error")

    def _create_image_json(self, image_type, product_image):
        """
        Crear JSON para el campo images
        Copiado de app.py
        """
        import base64
        try:
            # Si no hay imagen, retornar None o JSON vacío
            if not product_image and not image_type:
                return None

            # Procesar product_image según su tipo
            processed_image = None
            if product_image:
                if isinstance(product_image, memoryview):
                    # Convertir memoryview a bytes, luego a base64
                    image_bytes = product_image.tobytes()
                    processed_image = base64.b64encode(image_bytes).decode('utf-8')
                elif isinstance(product_image, bytes):
                    # Convertir bytes directamente a base64
                    processed_image = base64.b64encode(product_image).decode('utf-8')
                else:
                    # Si ya es string u otro tipo, usarlo directamente
                    processed_image = str(product_image)

            # Crear el diccionario JSON
            image_data = {
                "type": image_type if image_type else None,
                "product_image": processed_image,
                "description": "products"
            }

            # Convertir a JSON string
            return json.dumps(image_data, ensure_ascii=False)

        except Exception as e:
            self._log(f"Error creando JSON de imagen: {str(e)}", "warning")
            return None

    def _obtener_tipo_cambio_ves_usd(self, forzar_actualizacion=False):
        """
        Obtener tipo de cambio VES a USD usando API de ExchangeRate

        Args:
            forzar_actualizacion: Si True, actualiza el caché aunque sea reciente

        Returns:
            float con el tipo de cambio (ej: 417.36) o None si hay error
        """
        from datetime import datetime, timedelta
        import requests

        try:
            # Verificar si tenemos un tipo de cambio válido y reciente (menos de 1 hora)
            if not forzar_actualizacion and self.tipo_cambio_ves_usd and self.tipo_cambio_obtenido_at:
                edad = datetime.now() - self.tipo_cambio_obtenido_at
                if edad < timedelta(hours=1):
                    self._log(f"  💰 Usando tipo de cambio en caché: {self.tipo_cambio_ves_usd:.2f} VES/USD (edad: {edad.seconds//60} min)", "debug")
                    return self.tipo_cambio_ves_usd

            self._log("  💰 Obteniendo tipo de cambio VES→USD desde ExchangeRate API...", "info")

            # Usar ExchangeRate API (gratis, sin API key)
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'rates' in data and 'VES' in data['rates']:
                    tipo_cambio = float(data['rates']['VES'])

                    if tipo_cambio > 0:
                        self.tipo_cambio_ves_usd = tipo_cambio
                        self.tipo_cambio_obtenido_at = datetime.now()
                        self._log(f"  ✅ Tipo de cambio obtenido: {tipo_cambio:.2f} VES/USD", "success")
                        return tipo_cambio
                    else:
                        self._log(f"  ⚠️ Tipo de cambio inválido: {tipo_cambio}", "warning")
                else:
                    self._log("  ⚠️ La API no devolvió la tasa VES", "warning")
            else:
                self._log(f"  ⚠️ Error en API: status {response.status_code}", "warning")

            self._log("  ❌ No se pudo obtener el tipo de cambio", "error")
            return None

        except Exception as e:
            self._log(f"  ❌ Error en _obtener_tipo_cambio_ves_usd: {str(e)}", "error")
            return None

    def _convertir_ves_a_usd(self, monto_ves: float, tipo_cambio: float = None) -> float:
        """
        Convertir monto de VES a USD

        Args:
            monto_ves: Monto en Bolívares
            tipo_cambio: Tipo de cambio (opcional, usa el caché si no se proporciona)

        Returns:
            float con el monto en USD o el monto original si no se puede convertir
        """
        if monto_ves is None or monto_ves <= 0:
            return monto_ves

        try:
            # Obtener tipo de cambio si no se proporciona
            if tipo_cambio is None:
                tipo_cambio = self._obtener_tipo_cambio_ves_usd()

            if tipo_cambio and tipo_cambio > 0:
                monto_usd = monto_ves / tipo_cambio
                return round(monto_usd, 4)  # 4 decimales para precios
            else:
                return monto_ves
        except Exception as e:
            self._log(f"  ⚠️ Error convirtiendo {monto_ves} VES a USD: {str(e)}", "warning")
            return monto_ves

    # ====================================================================
    # SYSTEM LOGS - REGISTRO DE ACTIVIDAD
    # ====================================================================

    def _get_public_ip(self):
        """
        Obtener la IP pública del equipo

        Returns:
            str con la IP pública o None si no se puede obtener
        """
        try:
            import urllib.request
            import urllib.error

            # Servicios para obtener IP pública (orden de preferencia)
            services = [
                'https://api.ipify.org',
                'https://icanhazip.com',
                'https://ifconfig.me/ip'
            ]

            for service in services:
                try:
                    with urllib.request.urlopen(service, timeout=5) as response:
                        ip = response.read().decode('utf-8').strip()
                        if ip:
                            self._log(f"IP pública obtenida: {ip}", "debug")
                            return ip
                except:
                    continue

            self._log("No se pudo obtener IP pública", "warning")
            return None
        except Exception as e:
            self._log(f"Error obteniendo IP pública: {str(e)}", "warning")
            return None

    def _get_mac_address(self):
        """
        Obtener la MAC address del equipo

        Returns:
            str con la MAC address o None si no se puede obtener
        """
        try:
            import uuid
            # Obtener MAC address de la primera interfaz disponible
            mac = uuid.getnode()
            mac_address = ':'.join([f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8)][::-1])

            if mac_address != '00:00:00:00:00:00':
                self._log(f"MAC address obtenida: {mac_address}", "debug")
                return mac_address
            else:
                return None
        except Exception as e:
            self._log(f"Error obteniendo MAC address: {str(e)}", "warning")
            return None

    def _get_geolocation(self, ip_address):
        """
        Obtener geolocalización a partir de la IP

        Args:
            ip_address: Dirección IP pública

        Returns:
            tuple (lat, lng) o (None, None) si no se puede obtener
        """
        if not ip_address:
            return None, None

        try:
            import urllib.request

            # Usar ip-api.com (gratis, sin API key para uso no comercial)
            url = f'http://ip-api.com/json/{ip_address}?fields=status,lat,lon'

            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))

                if data.get('status') == 'success':
                    lat = data.get('lat')
                    lon = data.get('lon')
                    if lat is not None and lon is not None:
                        self._log(f"Geolocalización obtenida: {lat}, {lon}", "debug")
                        return lat, lon

            return None, None
        except Exception as e:
            self._log(f"Error obteniendo geolocalización: {str(e)}", "warning")
            return None, None

    def _log_to_system_logs(self, action: str, record_key: str, operation: str = 'SYNC', lat: float = None, lng: float = None):
        """
        Registrar actividad en system_logs de MySQL (un registro por key)

        Args:
            action: Entidad que se está modificando ('products', 'customers', etc.)
            record_key: ID del registro individual que se sincroniza
            operation: Tipo de operación ('CREATE', 'UPDATE', 'DELETE', 'SYNC')
            lat: Latitud (opcional)
            lng: Longitud (opcional)
        """
        try:
            # Obtener información del sistema
            ip_address = self._get_public_ip()
            mac_address = self._get_mac_address()

            # Si no se proporciona lat/lng, intentar obtener desde IP
            if lat is None or lng is None:
                lat, lng = self._get_geolocation(ip_address)

            # Convertir IP a varbinary(16) para MySQL
            ip_bytes = None
            if ip_address:
                try:
                    import ipaddress
                    ip_obj = ipaddress.ip_address(ip_address)
                    ip_bytes = ip_obj.packed
                except:
                    pass

            # Asegurar que record_key no sea NULL (campo NOT NULL en MySQL)
            if record_key is None:
                record_key = ''

            # Combinar action y operation: "products - CREATE"
            action_full = f"{action} - {operation}"

            # Insertar en system_logs con ST_GeomFromText para el campo POINT
            if lat is not None and lng is not None:
                # MySQL POINT: POINT(lng, lat) - notar que va longitud primero
                insert_query = """
                INSERT INTO system_logs (
                    user_id,
                    action,
                    record_key,
                    ip_address,
                    mac_address,
                    location,
                    lat,
                    lng,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, ST_GeomFromText(%s), %s, %s, NOW()
                )
                """
                location_point = f'POINT({lng} {lat})'

                self.mysql_cursor.execute(insert_query, (
                    self.company_rif,  # user_id = RIF de la empresa
                    action_full,
                    record_key,
                    ip_bytes,
                    mac_address,
                    location_point,
                    lat,
                    lng
                ))
            else:
                # Sin geolocalización
                insert_query = """
                INSERT INTO system_logs (
                    user_id,
                    action,
                    record_key,
                    ip_address,
                    mac_address,
                    lat,
                    lng,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                """

                self.mysql_cursor.execute(insert_query, (
                    self.company_rif,  # user_id = RIF
                    action_full,
                    record_key,
                    ip_bytes,
                    mac_address,
                    lat,
                    lng
                ))

            self.mysql_conn.commit()

            self._log(f"System log registrado: action={action_full}, key={record_key}, ip={ip_address}", "debug")

        except Exception as e:
            self._log(f"Error registrando en system_logs: {str(e)}", "warning")
            # No interrumpir la sincronización por errores de logging

    def _log_to_system_logs_batch(self, action: str, record_keys: list, operation: str = 'SYNC', lat: float = None, lng: float = None):
        """
        Registrar múltiples registros en system_logs (uno por cada key)

        Args:
            action: Entidad que se está modificando ('products', 'customers', etc.)
            record_keys: Lista de IDs de registros a sincronizar
            operation: Tipo de operación ('CREATE', 'UPDATE', 'DELETE', 'SYNC')
            lat: Latitud (opcional)
            lng: Longitud (opcional)
        """
        if not record_keys:
            # Si no hay keys, registrar un log vacío
            self._log_to_system_logs(action, '', operation, lat, lng)
            return

        # Obtener información del sistema una sola vez
        ip_address = self._get_public_ip()
        mac_address = self._get_mac_address()

        if lat is None or lng is None:
            lat, lng = self._get_geolocation(ip_address)

        # Registrar cada key individualmente
        for key in record_keys:
            self._log_to_system_logs(action, key, operation, lat, lng)

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - PRODUCTS
    # ====================================================================

    def detectar_cambios_products(self) -> Dict[str, List]:
        """
        Detectar cambios en products comparando hashes

        OPTIMIZADO: Si hay productos con pending_sync = true, solo procesa esos.
        Si no hay ninguno (fallback), procesa todos los productos (compatibilidad).

        Returns:
            Dict con 'nuevos', 'modificados', 'eliminados'
        """
        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return {'nuevos': [], 'modificados': [], 'eliminados': []}

        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            # 🔍 PASO 1: Verificar si hay productos con pending_sync = true
            self.pg_cursor.execute("""
                SELECT COUNT(*)
                FROM sync_hashes
                WHERE table_name = 'products'
                  AND company_id = %s
                  AND pending_sync = TRUE
                  AND deleted_at IS NULL
            """, (company_id,))
            count_pending = self.pg_cursor.fetchone()[0]

            # 📋 PASO 2: Obtener productos según estrategia
            if count_pending > 0:
                # Estrategia optimizada: Solo productos con pending_sync
                self._log(f"Detectando cambios en products... ({count_pending} pendientes)", "info")

                # Obtener códigos de productos pendientes
                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'products'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (company_id,))
                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

                # Construir filtro IN para query principal
                placeholders = ','.join(['%s'] * len(pending_codes))

                query = f"""
                SELECT DISTINCT ON (a.code)
                    a.code,
                    b.unit,
                    a.description,
                    a.short_name,
                    a.department,
                    b.product_code,
                    h.description as unidad,
                    COALESCE(c.total_stock, 0) AS stock,
                    a.product_type,
                    a.coin,
                    f.description AS description_coin,
                    COALESCE(b.maximum_price, b.higher_price, 0) AS price,
                    CASE
                        WHEN b.offer_price IS NULL
                        THEN 0
                        ELSE b.offer_price
                    END AS cost,
                    CASE
                        WHEN b.higher_price IS NULL
                        THEN 0
                        ELSE b.higher_price
                    END AS higher_price,
                    CASE
                        WHEN a.minimal_stock IS NULL
                        THEN 0
                        ELSE a.minimal_stock
                    END AS min_stock,
                    CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status,
                    d.image_type,
                    d.product_image,
                    a.sale_tax,
                    e.aliquot,
                    a.buy_tax,
                    g.aliquot AS buy_aliquot,
                    b.unitary_cost,
                    a.allow_decimal
                FROM products a
                LEFT JOIN (
                    SELECT product_code, SUM(stock) as total_stock
                    FROM products_stock
                    GROUP BY product_code
                ) c ON a.code = c.product_code
                LEFT JOIN products_units b ON a.code = b.product_code
                LEFT JOIN products_image d ON d.main_code = a.code
                LEFT JOIN taxes e ON e.code = a.sale_tax
                LEFT JOIN taxes g ON g.code = a.buy_tax
                LEFT JOIN coin f ON f.code = a.coin
                LEFT JOIN units h ON h.code = b.unit
                WHERE a.code IN ({placeholders})
                  AND a.code IS NOT NULL
                  AND a.code != ''
                  AND a.product_type <> 'C'
                  AND b.unit != ''
                ORDER BY a.code, b.maximum_price DESC;
                """

                self.pg_cursor.execute(query, pending_codes)
                productos = self.pg_cursor.fetchall()

                self._log(f"   🔍 Procesando {len(productos)} productos con cambios pendientes", "debug")
            else:
                # Fallback: Procesar todos los productos (comportamiento original)
                self._log("Detectando cambios en products... (escaneo completo)", "info")

                query = """
                SELECT DISTINCT ON (a.code)
                    a.code,
                    b.unit,
                    a.description,
                    a.short_name,
                    a.department,
                    b.product_code,
                    h.description as unidad,
                    COALESCE(c.total_stock, 0) AS stock,
                    a.product_type,
                    a.coin,
                    f.description AS description_coin,
                    COALESCE(b.maximum_price, b.higher_price, 0) AS price,
                    CASE
                        WHEN b.offer_price IS NULL
                        THEN 0
                        ELSE b.offer_price
                    END AS cost,
                    CASE
                        WHEN b.higher_price IS NULL
                        THEN 0
                        ELSE b.higher_price
                    END AS higher_price,
                    CASE
                        WHEN a.minimal_stock IS NULL
                        THEN 0
                        ELSE a.minimal_stock
                    END AS min_stock,
                    CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END AS status,
                    d.image_type,
                    d.product_image,
                    a.sale_tax,
                    e.aliquot,
                    a.buy_tax,
                    g.aliquot AS buy_aliquot,
                    b.unitary_cost,
                    a.allow_decimal
                FROM products a
                LEFT JOIN (
                    SELECT product_code, SUM(stock) as total_stock
                    FROM products_stock
                    GROUP BY product_code
                ) c ON a.code = c.product_code
                LEFT JOIN products_units b ON a.code = b.product_code
                LEFT JOIN products_image d ON d.main_code = a.code
                LEFT JOIN taxes e ON e.code = a.sale_tax
                LEFT JOIN taxes g ON g.code = a.buy_tax
                LEFT JOIN coin f ON f.code = a.coin
                LEFT JOIN units h ON h.code = b.unit
                WHERE a.code IS NOT NULL
                  AND a.code != ''
                  AND a.product_type <> 'C'
                  AND b.unit != ''
                ORDER BY a.code, b.maximum_price DESC;
                """

                self.pg_cursor.execute(query)
                productos = self.pg_cursor.fetchall()

            claves_actuales = []

            for producto in productos:
                if not self.sync_running:
                    break

                code = producto[0]
                claves_actuales.append(code)

                # Generar hash actual
                hash_actual = self._generar_hash_product(producto)

                # Buscar hash guardado CON last_sync_data (para detectar reactivaciones)
                query_hash = """
                SELECT record_hash, last_sync_data
                FROM sync_hashes
                WHERE table_name = 'products'
                  AND record_key = %s
                  AND company_id = %s
                """
                self.pg_cursor.execute(query_hash, (code, company_id))
                hash_guardado_full = self.pg_cursor.fetchone()

                hash_guardado = hash_guardado_full[0] if hash_guardado_full else None
                last_sync_data = hash_guardado_full[1] if hash_guardado_full else None

                # Verificar si estaba inactivo (reactivación)
                data_parseado = {}
                if last_sync_data:
                    try:
                        data_parseado = json.loads(last_sync_data) if isinstance(last_sync_data, str) else last_sync_data
                    except:
                        data_parseado = {}

                estaba_inactivo = data_parseado.get('status') == 'inactive'
                inactive_since = data_parseado.get('inactive_since')

                if hash_guardado is None:
                    # Nuevo producto (nunca sincronizado)
                    cambios['nuevos'].append(producto)
                    self._log(f"  ✨ NUEVO: {code}", "debug")
                    self._guardar_hash('products', code, hash_actual)
                elif estaba_inactivo:
                    # Producto REACTIVADO
                    self._log(f"  ✅ REACTIVADO: {code} (inactivo desde {inactive_since})", "info")

                    # Guardar historial de reactivación en last_sync_data
                    info_reactivacion = {
                        'status': 'active',
                        'inactive_since': inactive_since,
                        'reactivated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self._guardar_hash('products', code, hash_actual, info_reactivacion)
                    cambios['modificados'].append(producto)  # Sincronizar a MySQL
                elif hash_guardado != hash_actual:
                    # Producto modificado (sin cambio de status)
                    cambios['modificados'].append(producto)
                    self._log(f"  🔄 MODIFICADO: {code}", "debug")

                    # Guardar hash con status actual en last_sync_data
                    data_sync = {
                        'status': producto[12],  # status (active/inactive)
                        'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self._guardar_hash('products', code, hash_actual, data_sync)
                else:
                    # Sin cambios, solo actualizar timestamp pero MANTENER last_sync_data
                    # No actualizar last_sync_data para no perder el status guardado
                    # IMPORTANTE: Limpiar pending_sync porque ya se procesó
                    update_query = """
                    UPDATE sync_hashes
                    SET updated_at = NOW(),
                        pending_sync = FALSE
                    WHERE table_name = %s
                      AND record_key = %s
                      AND company_id = %s
                    """
                    self.pg_cursor.execute(update_query, ('products', code, company_id))

            # Detectar productos inactivos (eliminados del query pero con hash guardado)
            if claves_actuales:
                placeholders = ','.join(['%s'] * len(claves_actuales))
                query_eliminados = f"""
                SELECT record_key, last_sync_data
                FROM sync_hashes
                WHERE table_name = 'products'
                  AND company_id = %s
                  AND record_key NOT IN ({placeholders})
                """

                self.pg_cursor.execute(query_eliminados, [company_id] + claves_actuales)
                eliminados = self.pg_cursor.fetchall()

                for (code, last_sync_data) in eliminados:
                    # Verificar si ya estaba marcado como inactivo
                    data_parseado = {}
                    if last_sync_data:
                        try:
                            data_parseado = json.loads(last_sync_data) if isinstance(last_sync_data, str) else last_sync_data
                        except:
                            data_parseado = {}

                    ya_estaba_inactivo = data_parseado.get('status') == 'inactive'

                    # Marcar como inactivo en sync_hashes (MANTENER el registro)
                    info_inactividad = {
                        'status': 'inactive',
                        'inactive_since': data_parseado.get('inactive_since', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                        'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                    # Usar hash especial para productos inactivos
                    hash_inactivo = hashlib.md5(f"INACTIVE_{code}".encode()).hexdigest()
                    self._guardar_hash('products', code, hash_inactivo, info_inactividad)

                    cambios['eliminados'].append({'code': code})
                    if ya_estaba_inactivo:
                        self._log(f"  🔄 Permanece INACTIVO: {code}", "debug")
                    else:
                        self._log(f"  📴 Marcar como INACTIVO: {code}", "info")

            # Commit hashes
            self.pg_conn.commit()

            self._log(f"Productos: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en products: {str(e)}", "error")

        return cambios

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - PRODUCTS MYSQL → POSTGRESQL
    # ====================================================================

    def detectar_cambios_products_mysql(self) -> Dict[str, List]:
        """
        Detectar cambios en products de MySQL para sincronizar a PostgreSQL

        Returns:
            Dict con 'nuevos', 'modificados'
        """
        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return {'nuevos': [], 'modificados': []}

        self._log("Detectando cambios en products (MySQL → PostgreSQL)...", "info")

        cambios = {
            'nuevos': [],
            'modificados': []
        }

        try:
            # Obtener products de MySQL
            query = """
            SELECT
                id,
                code,
                name,
                description,
                price,
                cost,
                higher_price,
                coin,
                description_coin,
                min_stock,
                category_id,
                status,
                product_type,
                sale_tax,
                aliquot,
                created_at,
                updated_at
            FROM products
            WHERE company_id = %s
            ORDER BY id
            """

            self.mysql_cursor.execute(query, (company_id,))
            products_mysql = self.mysql_cursor.fetchall()

            # Convertir a diccionarios
            columnas = [
                'id', 'code', 'name', 'description', 'price', 'cost',
                'higher_price', 'coin', 'description_coin', 'min_stock',
                'category_id', 'status', 'product_type', 'sale_tax',
                'aliquot', 'created_at', 'updated_at'
            ]

            products_dict = []
            for fila in products_mysql:
                product_dict = dict(zip(columnas, fila))
                products_dict.append(product_dict)

            self._log(f"   📋 Products encontrados en MySQL: {len(products_dict)}", "info")

            if not products_dict:
                self._log("   ℹ️ No hay products en MySQL para esta empresa", "info")
                return cambios

            # Mostrar códigos de products encontrados
            codigos_encontrados = [p['code'] for p in products_dict]
            self._log(f"   🔍 Códigos: {codigos_encontrados[:10]}{'...' if len(codigos_encontrados) > 10 else ''}", "debug")

            for product in products_dict:
                if not self.sync_running:
                    break

                product_id = product['id']
                product_code = product['code']

                # Generar hash actual
                hash_actual = self._generar_hash_product_mysql(product)

                # Buscar hash guardado en sync_hashes (PostgreSQL)
                hash_guardado = self._obtener_hash_guardado('products_mysql', str(product_id))

                self._log(f"   🔍 Product #{product_id} ({product_code}): hash_guardado={hash_guardado[0][:8] if hash_guardado else 'None'}", "debug")

                if hash_guardado is None:
                    # Nuevo product
                    cambios['nuevos'].append(product)
                    self._log(f"  ✨ NUEVO: Product #{product_id} ({product_code})", "info")
                elif hash_guardado[0] != hash_actual:
                    # Product modificado
                    cambios['modificados'].append(product)
                    self._log(f"  🔄 MODIFICADO: Product #{product_id} ({product_code})", "info")

                # NOTA: El hash se guarda DESPUÉS de sincronizar exitosamente
                # en sincronizar_products_postgresql()

            self._log(f"✅ Products detectados: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en products de MySQL: {str(e)}", "error")
            self.stats['products']['errores'] += 1

        return cambios

    def detectar_cambios_customers_mysql(self) -> Dict[str, List]:
        """
        Detectar cambios en customers de MySQL para sincronizar a PostgreSQL

        Returns:
            Dict con 'nuevos', 'modificados'
        """
        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return {'nuevos': [], 'modificados': []}

        self._log("Detectando cambios en customers (MySQL → PostgreSQL)...", "info")

        cambios = {
            'nuevos': [],
            'modificados': []
        }

        try:
            # Obtener customers de MySQL
            query = """
            SELECT
                id,
                document_number,
                name,
                address,
                email,
                phone,
                contact,
                created_at,
                updated_at
            FROM customers
            WHERE company_id = %s
            ORDER BY id
            """

            self.mysql_cursor.execute(query, (company_id,))
            customers_mysql = self.mysql_cursor.fetchall()

            # Convertir a diccionarios
            columnas = [
                'id', 'document_number', 'name', 'address', 'email', 'phone', 'contact',
                'created_at', 'updated_at'
            ]

            customers_dict = []
            for fila in customers_mysql:
                customer_dict = dict(zip(columnas, fila))
                customers_dict.append(customer_dict)

            self._log(f"   📋 Customers encontrados en MySQL: {len(customers_dict)}", "info")

            if not customers_dict:
                self._log("   ℹ️ No hay customers en MySQL para esta empresa", "info")
                return cambios

            # Mostrar códigos de customers encontrados
            codigos_encontrados = [c['document_number'] for c in customers_dict]
            self._log(f"   🔍 Códigos: {codigos_encontrados[:10]}{'...' if len(codigos_encontrados) > 10 else ''}", "debug")

            for customer in customers_dict:
                if not self.sync_running:
                    break

                customer_id = customer['id']
                customer_code = customer['document_number']

                # Generar hash actual
                hash_actual = self._generar_hash_customer_mysql(customer)

                # Buscar hash guardado en sync_hashes (PostgreSQL)
                hash_guardado = self._obtener_hash_guardado('customers_mysql', str(customer_id))

                self._log(f"   🔍 Customer #{customer_id} ({customer_code}): hash_guardado={hash_guardado[0][:8] if hash_guardado else 'None'}", "debug")

                if hash_guardado is None:
                    # Nuevo customer
                    cambios['nuevos'].append(customer)
                    self._log(f"  ✨ NUEVO: Customer #{customer_id} ({customer_code})", "info")
                elif hash_guardado[0] != hash_actual:
                    # Customer modificado
                    cambios['modificados'].append(customer)
                    self._log(f"  🔄 MODIFICADO: Customer #{customer_id} ({customer_code})", "info")

                # NOTA: El hash se guarda DESPUÉS de sincronizar exitosamente
                # en sincronizar_customers_postgresql()

            self._log(f"✅ Customers detectados: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en customers de MySQL: {str(e)}", "error")
            self.stats['customers']['errores'] += 1

        return cambios

    def _generar_hash_product_mysql(self, product: dict) -> str:
        """
        Generar hash MD5 de un product de MySQL

        Args:
            product: Diccionario con datos del product

        Returns:
            Hash MD5 hexadecimal
        """
        import hashlib

        # Campos relevantes para el hash
        campos_hash = [
            product['code'],
            product['name'],
            str(product['price']),
            str(product['cost']),
            str(product.get('higher_price', 0)),
            product.get('coin', ''),
            product.get('description_coin', ''),
            str(product.get('min_stock', 0)),
            str(product.get('category_id', '')),
            product.get('status', 'active'),
            product.get('product_type', 'finished'),
            product.get('sale_tax', ''),
            str(product.get('aliquot', 0))
        ]

        datos_hash = "|".join(str(c) for c in campos_hash)
        return hashlib.md5(datos_hash.encode()).hexdigest()

    def _generar_hash_customer_mysql(self, customer: dict) -> str:
        """
        Generar hash MD5 de un customer de MySQL

        Args:
            customer: Diccionario con datos del customer

        Returns:
            Hash MD5 hexadecimal
        """
        import hashlib

        # Campos relevantes para el hash
        campos_hash = [
            customer['document_number'],  # code en PostgreSQL
            customer['name'],  # description en PostgreSQL
            customer.get('address', ''),
            customer.get('email', ''),
            customer.get('phone', ''),
            customer.get('contact', '')
        ]

        datos_hash = "|".join(str(c) for c in campos_hash)
        return hashlib.md5(datos_hash.encode()).hexdigest()

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - CUSTOMERS
    # ====================================================================

    def detectar_cambios_customers(self) -> Dict[str, List]:
        """
        Detectar cambios en customers

        OPTIMIZADO: Si hay customers con pending_sync = true, solo procesa esos.
        Si no hay ninguno (fallback), procesa todos los customers (compatibilidad).
        """
        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return {'nuevos': [], 'modificados': [], 'eliminados': []}

        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            # 🔍 PASO 1: Verificar si hay customers con pending_sync = true
            self.pg_cursor.execute("""
                SELECT COUNT(*)
                FROM sync_hashes
                WHERE table_name = 'customers'
                  AND company_id = %s
                  AND pending_sync = TRUE
                  AND deleted_at IS NULL
            """, (company_id,))
            count_pending = self.pg_cursor.fetchone()[0]

            # 📋 PASO 2: Obtener customers según estrategia
            if count_pending > 0:
                # Estrategia optimizada: Solo customers con pending_sync
                self._log(f"Detectando cambios en customers... ({count_pending} pendientes)", "info")

                # Obtener códigos de customers pendientes
                self.pg_cursor.execute("""
                    SELECT record_key
                    FROM sync_hashes
                    WHERE table_name = 'customers'
                      AND company_id = %s
                      AND pending_sync = TRUE
                      AND deleted_at IS NULL
                """, (company_id,))
                pending_codes = [row[0] for row in self.pg_cursor.fetchall()]

                # Construir filtro IN para query principal
                placeholders = ','.join(['%s'] * len(pending_codes))

                query = f"""
                SELECT
                    code,
                    description,
                    address,
                    client_id,
                    email,
                    phone,
                    contact
                FROM clients
                WHERE code IN ({placeholders})
                  AND code IS NOT NULL AND code != ''
                  AND description IS NOT NULL AND description != ''
                ORDER BY code
                """

                self.pg_cursor.execute(query, pending_codes)
                clientes = self.pg_cursor.fetchall()

                self._log(f"   🔍 Procesando {len(clientes)} customers con cambios pendientes", "debug")
            else:
                # Fallback: Procesar todos los customers (comportamiento original)
                self._log("Detectando cambios en customers... (escaneo completo)", "info")

                query = """
                SELECT
                    code,
                    description,
                    address,
                    client_id,
                    email,
                    phone,
                    contact
                FROM clients
                WHERE code IS NOT NULL AND code != ''
                  AND description IS NOT NULL AND description != ''
                ORDER BY code
                """

                self.pg_cursor.execute(query)
                clientes = self.pg_cursor.fetchall()

            claves_actuales = []

            for cliente in clientes:
                if not self.sync_running:
                    break

                code = cliente[0]
                claves_actuales.append(code)

                hash_actual = self._generar_hash_customer(cliente)
                hash_guardado = self._obtener_hash_guardado('customers', code)

                if hash_guardado is None:
                    cambios['nuevos'].append(cliente)
                    self._log(f"  ✨ NUEVO: {code}", "debug")
                elif hash_guardado[0] != hash_actual:
                    cambios['modificados'].append(cliente)
                    self._log(f"  🔄 MODIFICADO: {code}", "debug")

                self._guardar_hash('customers', code, hash_actual)

            # Detectar eliminados
            if claves_actuales:
                placeholders = ','.join(['%s'] * len(claves_actuales))
                query_eliminados = f"""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'customers'
                  AND company_id = %s
                  AND record_key NOT IN ({placeholders})
                """

                self.pg_cursor.execute(query_eliminados, [company_id] + claves_actuales)
                eliminados = self.pg_cursor.fetchall()

                for (eliminado,) in eliminados:
                    cambios['eliminados'].append({'code': eliminado})
                    self._log(f"  ❌ ELIMINADO: {eliminado}", "warning")
                    # NO eliminar el hash aquí - dejar que _eliminar_customers_mysql_cuando_faltan_en_postgresql() lo haga
                    # self._eliminar_hash('customers', eliminado)

            self.pg_conn.commit()

            self._log(f"Clientes: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en customers: {str(e)}", "error")

        return cambios

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - CATEGORIES
    # ====================================================================

    def detectar_cambios_categories(self) -> Dict[str, List]:
        """Detectar cambios en categories"""
        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return {'nuevos': [], 'modificados': [], 'eliminados': []}

        self._log("Detectando cambios en categories...", "info")

        cambios = {'nuevos': [], 'modificados': [], 'eliminados': []}

        try:
            query = """
            SELECT code, description
            FROM department
            WHERE code IS NOT NULL AND code != ''
            ORDER BY code
            """

            self.pg_cursor.execute(query)
            categories = self.pg_cursor.fetchall()

            claves_actuales = []

            for category in categories:
                if not self.sync_running:
                    break

                code = category[0]
                claves_actuales.append(code)

                hash_actual = self._generar_hash_category(category)
                hash_guardado = self._obtener_hash_guardado('categories', code)

                if hash_guardado is None:
                    cambios['nuevos'].append(category)
                    self._log(f"  ✨ NUEVO: {code}", "debug")
                elif hash_guardado[0] != hash_actual:
                    cambios['modificados'].append(category)
                    self._log(f"  🔄 MODIFICADO: {code}", "debug")

                self._guardar_hash('categories', code, hash_actual)

            # Detectar eliminados
            if claves_actuales:
                placeholders = ','.join(['%s'] * len(claves_actuales))
                query_eliminados = f"""
                SELECT record_key
                FROM sync_hashes
                WHERE table_name = 'categories'
                  AND company_id = %s
                  AND record_key NOT IN ({placeholders})
                """

                self.pg_cursor.execute(query_eliminados, [company_id] + claves_actuales)
                eliminados = self.pg_cursor.fetchall()

                for (eliminado,) in eliminados:
                    cambios['eliminados'].append({'code': eliminado})
                    self._log(f"  ❌ ELIMINADO: {eliminado}", "warning")
                    # NO eliminar el hash aquí - dejar que _eliminar_categories_mysql_cuando_faltan_en_postgresql() lo haga
                    # self._eliminar_hash('categories', eliminado)

            self.pg_conn.commit()

            self._log(f"Departamentos: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en categories: {str(e)}", "error")

        return cambios

    # ====================================================================
    # DETECCIÓN DE CAMBIOS - QUOTES (MySQL → PostgreSQL)
    # ====================================================================

    def _verificar_y_sincronizar_customer(self, customer_id: int, customer_doc: str,
                                          customer_name: str, customer_email: str,
                                          customer_phone: str, customer_address: str):
        """
        Verificar si un customer existe en PostgreSQL y sincronizarlo si no existe

        Args:
            customer_id: ID del customer en MySQL
            customer_doc: Document number (RIF/Cédula)
            customer_name: Nombre del customer
            customer_email: Email del customer
            customer_phone: Teléfono del customer
            customer_address: Dirección del customer
        """
        try:
            # Verificar si existe en PostgreSQL
            self.pg_cursor.execute(
                "SELECT code FROM clients WHERE code = %s",
                (customer_doc,)
            )
            existe = self.pg_cursor.fetchone()

            if existe:
                self._log(f"  👤 Customer {customer_doc} ya existe en PostgreSQL", "debug")
                return

            # No existe, insertar
            self._log(f"  ✨ Sincronizando customer {customer_doc} a PostgreSQL...", "info")

            # Compatible con PostgreSQL 9.1 - Verificar si existe antes de insertar
            self.pg_cursor.execute(
                "SELECT code FROM clients WHERE code = %s",
                (customer_doc,)
            )
            if not self.pg_cursor.fetchone():
                # Usar valores genéricos para columnas con restricciones
                sql_insert = """
                INSERT INTO clients (
                    code, description, address, email, phone, contact,
                    country, province, city, client_type, area_sales,
                    seller, client_group
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                self.pg_cursor.execute(sql_insert, (
                    customer_doc,        # code
                    customer_name[:255], # description
                    customer_address[:255] if customer_address else '',
                    customer_email[:255] if customer_email else '',
                    customer_phone[:50] if customer_phone else '',
                    customer_name[:100],  # contact
                    '00',                # country (LOCAL)
                    '00',                # province (LOCAL)
                    '00',                # city (LOCAL)
                    '01',                # client_type (Juridico)
                    '00',                # area_sales
                    '00',                # seller
                    '00'                 # client_group (GENERICO)
                ))

                self.pg_conn.commit()
                self._log(f"  ✅ Customer {customer_doc} sincronizado a PostgreSQL", "info")
            else:
                self._log(f"  ℹ️ Customer {customer_doc} ya existe en PostgreSQL (omitiendo)", "debug")

        except Exception as e:
            self._log(f"  ⚠️ Error sincronizando customer {customer_doc}: {str(e)}", "warning")
            self.pg_conn.rollback()

    def _verificar_y_sincronizar_products_quote(self, quote_id: int):
        """
        Verificar y sincronizar todos los products de un quote antes de insertarlo

        Args:
            quote_id: ID del quote en MySQL
        """
        try:
            # Obtener todos los products del quote con sus datos
            self.mysql_cursor.execute("""
                SELECT DISTINCT
                    p.id, p.code, p.name, p.description, p.price, p.cost,
                    p.product_type, p.status
                FROM quote_items qi
                JOIN products p ON p.id = qi.product_id
                WHERE qi.quote_id = %s
            """, (quote_id,))

            products_mysql = self.mysql_cursor.fetchall()

            if not products_mysql:
                return

            self._log(f"  📦 Verificando {len(products_mysql)} products del quote...", "debug")

            for product in products_mysql:
                product_id, product_code, product_name, product_desc, product_price, product_cost, product_type, product_status = product

                # Verificar si existe en PostgreSQL
                self.pg_cursor.execute(
                    "SELECT code FROM products WHERE code = %s",
                    (product_code,)
                )
                existe = self.pg_cursor.fetchone()

                if existe:
                    continue

                # No existe, sincronizar
                self._log(f"  ✨ Sincronizando product {product_code} a PostgreSQL...", "info")

                # Compatible con PostgreSQL 9.1 - Ya verificamos arriba que no existe
                # Obtener valores válidos para columnas con restricciones
                self.pg_cursor.execute("SELECT code FROM status WHERE code != '00' LIMIT 1")
                status_row = self.pg_cursor.fetchone()
                status_valido = status_row[0] if status_row else '01'

                # Insertar product
                sql_insert = """
                INSERT INTO products (
                    code, description, minimal_sale, maximal_sale,
                    status, product_type, sale_price
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """

                self.pg_cursor.execute(sql_insert, (
                    product_code,
                    (product_desc or product_name)[:255],
                    float(product_cost) if product_cost else 0,
                    float(product_price) if product_price else 0,
                    status_valido,
                    product_type if product_type else 'finished',
                    int(float(product_price) * 100) if product_price else 0
                ))

                self._log(f"  ✅ Product {product_code} sincronizado", "debug")

            self.pg_conn.commit()

        except Exception as e:
            self._log(f"  ⚠️ Error sincronizando products del quote: {str(e)}", "warning")
            self.pg_conn.rollback()

    def _generar_hash_quote(self, quote: dict) -> str:
        """
        Generar hash MD5 para un quote (desde MySQL)
        Los quotes van de MySQL → PostgreSQL (dirección opuesta)
        """
        try:
            # Campos clave para detectar cambios
            campos = (
                str(quote.get('id', '')),
                str(quote.get('quote_number', '')),
                str(quote.get('customer_id', '')),
                str(safe_float(quote.get('subtotal', 0))),
                str(safe_float(quote.get('tax', 0))),
                str(safe_float(quote.get('tax_amount', 0))),
                str(safe_float(quote.get('discount', 0))),
                str(safe_float(quote.get('total', 0))),
                str(quote.get('status', 'pending'))
            )

            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except Exception as e:
            self._log(f"Error generando hash de quote: {str(e)}", "error")
            return hashlib.md5(str(quote.get('id', '')).encode()).hexdigest()

    def detectar_cambios_quotes(self) -> Dict[str, List]:
        """
        Detectar cambios en quotes (MySQL → PostgreSQL)

        Returns:
            Dict con 'nuevos', 'modificados', 'actualizaciones_estado'
        """
        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return {'nuevos': [], 'modificados': [], 'actualizaciones_estado': []}

        self._log("", "info")
        self._log("💰 DETECTANDO CAMBIOS EN QUOTES (MySQL → PostgreSQL)...", "info")

        cambios = {
            'nuevos': [],
            'modificados': [],
            'actualizaciones_estado': []  # Quotes que cambiaron de status
        }

        try:
            # Obtener quotes de MySQL
            query = """
            SELECT
                id,
                quote_number,
                customer_id,
                company_id,
                user_seller_id,
                subtotal,
                tax,
                tax_amount,
                discount,
                discount_amount,
                total,
                bcv_rate,
                status,
                created_at,
                updated_at
            FROM quotes
            WHERE company_id = %s
            ORDER BY id
            """

            self.mysql_cursor.execute(query, (company_id,))
            quotes_mysql = self.mysql_cursor.fetchall()

            # Convertir a diccionarios para facilitar manejo
            columnas = [
                'id', 'quote_number', 'customer_id', 'company_id',
                'user_seller_id', 'subtotal', 'tax', 'tax_amount',
                'discount', 'discount_amount', 'total', 'bcv_rate',
                'status', 'created_at', 'updated_at'
            ]

            quotes_dict = []
            for fila in quotes_mysql:
                quote_dict = dict(zip(columnas, fila))
                quotes_dict.append(quote_dict)

            self._log(f"   📋 Quotes encontrados en MySQL: {len(quotes_dict)}", "info")

            if not quotes_dict:
                self._log("   ℹ️ No hay quotes en MySQL para esta empresa", "info")
                return cambios

            # Mostrar IDs de quotes encontrados
            ids_encontrados = [q['id'] for q in quotes_dict]
            self._log(f"   🔍 IDs encontrados: {ids_encontrados}", "info")

            ids_actuales = []

            for quote in quotes_dict:
                if not self.sync_running:
                    break

                quote_id = quote['id']
                quote_number = quote['quote_number']
                ids_actuales.append(str(quote_id))

                # Generar hash actual
                hash_actual = self._generar_hash_quote(quote)

                # Buscar hash guardado en sync_hashes (PostgreSQL)
                hash_guardado = self._obtener_hash_guardado('quotes', str(quote_id))

                self._log(f"   🔍 Quote #{quote_id} ({quote_number}): hash_guardado={hash_guardado[0][:8] if hash_guardado else 'None'}", "debug")

                if hash_guardado is None:
                    # Nuevo quote
                    cambios['nuevos'].append(quote)
                    self._log(f"  ✨ NUEVO: Quote #{quote_id} ({quote_number})", "info")
                elif hash_guardado[0] != hash_actual:
                    # Quote modificado
                    cambios['modificados'].append(quote)
                    self._log(f"  🔄 MODIFICADO: Quote #{quote_id} ({quote_number})", "info")

                # NOTA: El hash se guarda DESPUÉS de sincronizar exitosamente
                # en sincronizar_quotes_postgresql()

            self._log(f"✅ Quotes detectados: {len(cambios['nuevos'])} nuevos, "
                      f"{len(cambios['modificados'])} modificados", "info")

        except Exception as e:
            self._log(f"Error detectando cambios en quotes: {str(e)}", "error")
            self.stats['quotes']['errores'] += 1

        return cambios

    # ====================================================================
    # SINCRONIZACIÓN DE QUOTES A POSTGRESQL
    # ====================================================================

    def sincronizar_quotes_postgresql(self, cambios: Dict[str, List]):
        """
        Sincronizar quotes de MySQL a PostgreSQL

        Los quotes se migran a sales_operation en PostgreSQL
        """
        if not cambios.get('nuevos') and not cambios.get('modificados'):
            self._log("✅ Quotes: No hay cambios para sincronizar", "info")
            return

        total_nuevos = len(cambios.get('nuevos', []))
        total_modificados = len(cambios.get('modificados', []))

        self._log("", "info")
        self._log("💰 SINCRONIZANDO QUOTES (MySQL → PostgreSQL)...", "info")
        self._log(f"   📋 Nuevos: {total_nuevos} | Modificados: {total_modificados}", "info")

        # Registrar en system_logs (CREATE para nuevos, UPDATE para modificados)
        # COMENTADO: Tarda mucho guardando en system_logs
        nuevos_quotes = [str(q['id']) for q in cambios.get('nuevos', [])]
        modificados_quotes = [str(q['id']) for q in cambios.get('modificados', [])]

        # if nuevos_quotes:
        #     self._log_to_system_logs_batch('quotes', nuevos_quotes, 'CREATE')
        # if modificados_quotes:
        #     self._log_to_system_logs_batch('quotes', modificados_quotes, 'UPDATE')

        try:
            # Obtener MAC address para la estación
            import uuid
            mac = ':'.join(('%012X' % uuid.getnode())[i:i+2] for i in range(0, 12, 2))

            # Procesar quotes nuevos y modificados
            quotes_a_procesar = cambios.get('nuevos', []) + cambios.get('modificados', [])

            for quote in quotes_a_procesar:
                if not self.sync_running:
                    break

                # Iniciar transacción individual para cada quote
                try:
                    quote_id = quote['id']

                    self._log(f"  Procesando quote #{quote_id}...", "debug")

                    # Insertar directamente en PostgreSQL (sin verificar si existe)
                    # El sistema de hashes sync_hashes detectará duplicados
                    correlativo = self._insertar_quote_postgresql(quote, mac)

                    # Guardar el correlative en el hash para futuras referencias
                    if correlativo:
                        quote_con_correlative = quote.copy()
                        quote_con_correlative['_postgres_correlative'] = correlativo
                        hash_nuevo = self._generar_hash_quote(quote)
                        self._guardar_hash('quotes', str(quote_id), hash_nuevo, quote_con_correlative)

                    # Commit exitoso de este quote
                    self.pg_conn.commit()
                    self.stats['quotes']['nuevos'] += 1

                except Exception as e:
                    # Si es error de duplicado (unique constraint), ignorar silenciosamente
                    error_msg = str(e).lower()
                    if 'duplicate' in error_msg or 'unique' in error_msg:
                        self._log(f"  ℹ️ Quote #{quote_id} ya existe en PostgreSQL (omitiendo)", "debug")
                        self.pg_conn.rollback()
                    else:
                        # Otro error, registrar con traceback completo
                        import traceback
                        self._log(f"Error procesando quote {quote.get('id')}: {str(e)}", "error")
                        self._log(f"TRACEBACK:\n{traceback.format_exc()}", "error")
                        self.pg_conn.rollback()  # Rollback para que no afecte siguientes quotes
                        self.stats['quotes']['errores'] += 1

            # Resumen final
            self._log(f"✅ Quotes completados: {self.stats['quotes']['nuevos']} nuevos, "
                      f"{self.stats['quotes']['modificados']} modificados, "
                      f"{self.stats['quotes']['errores']} errores", "success")

            # Notificar si hay nuevos presupuestos
            if self.stats['quotes']['nuevos'] > 0:
                self._notificar_nuevos_presupuestos(self.stats['quotes']['nuevos'])

        except Exception as e:
            self._log(f"Error sincronizando quotes a PostgreSQL: {str(e)}", "error")
            self.stats['quotes']['errores'] += 1

    def _insertar_quote_postgresql(self, quote: dict, mac: str) -> int:
        """
        Insertar un quote completo en PostgreSQL

        Args:
            quote: Datos del quote desde MySQL
            mac: MAC address (no usado, para compatibilidad)

        Returns:
            El correlative generado por PostgreSQL, o None si falló
        """
        from datetime import datetime, timedelta

        # Verificar/obtener station válida
        station = self._obtener_station_valida(mac)

        # Preparar fecha
        emission_date = quote.get('created_at')
        if emission_date is None:
            emission_date = datetime.now()
        elif isinstance(emission_date, str):
            emission_date = datetime.fromisoformat(emission_date.replace('Z', '+00:00'))

        # Obtener datos del customer desde MySQL
        self.mysql_cursor.execute(
            "SELECT name, email, phone, document_number, address FROM customers WHERE id = %s",
            (quote['customer_id'],)
        )
        customer = self.mysql_cursor.fetchone()

        if customer:
            customer_name, customer_email, customer_phone, customer_doc, customer_address = customer

            # VERIFICAR Y SINCRONIZAR CUSTOMER A POSTGRESQL si no existe
            self._verificar_y_sincronizar_customer(quote['customer_id'], customer_doc, customer_name, customer_email, customer_phone, customer_address)

            # Obtener name_fiscal desde clients de PostgreSQL
            self.pg_cursor.execute(
                "SELECT name_fiscal FROM clients WHERE code = %s",
                (customer_doc,)
            )
            client_fiscal_result = self.pg_cursor.fetchone()
            client_name_fiscal = client_fiscal_result[0] if client_fiscal_result else 0
        else:
            customer_name = "Cliente Migrado"
            customer_email = ""
            customer_phone = ""
            customer_doc = f"MIG-{quote['customer_id']}"
            customer_address = ""
            client_name_fiscal = 0

        # VERIFICAR Y SINCRONIZAR PRODUCTS DEL QUOTE antes de insertar
        self._verificar_y_sincronizar_products_quote(quote['id'])

        # Calcular la suma total de cantidades (quantity) de los items
        self.mysql_cursor.execute(
            "SELECT SUM(quantity) FROM quote_items WHERE quote_id = %s",
            (quote['id'],)
        )
        total_quantity_result = self.mysql_cursor.fetchone()
        total_quantity = safe_float(total_quantity_result[0]) if total_quantity_result and total_quantity_result[0] else 0

        # Calcular costos reales desde los productos (NO usar precio)
        self.mysql_cursor.execute("""
            SELECT qi.quantity, p.cost, qi.product_id, p.code
            FROM quote_items qi
            JOIN products p ON p.id = qi.product_id
            WHERE qi.quote_id = %s
        """, (quote['id'],))

        items_costos = self.mysql_cursor.fetchall()

        # Calcular totales basados en el COSTO (no en el precio)
        total_net_cost = 0
        total_tax_cost = 0

        for quantity, cost, product_id, product_code in items_costos:
            qty = safe_float(quantity)
            prod_cost = safe_float(cost if cost else 0)

            # Calcular costo neto del item
            item_net_cost = qty * prod_cost

            # Obtener sale_tax desde PostgreSQL para calcular tax_cost
            self.pg_cursor.execute(
                "SELECT sale_tax FROM products WHERE code = %s",
                (product_code,)
            )
            pg_product = self.pg_cursor.fetchone()

            # Calcular tax_cost basado en sale_tax (16% para gravados, 0 para exentos)
            if pg_product and pg_product[0]:
                product_sale_tax = pg_product[0]
                if product_sale_tax == '01':
                    # Producto gravado: tax_cost = 16% del net_cost
                    item_tax_cost = item_net_cost * 0.16
                else:
                    # Producto exento u otro: tax_cost = 0
                    item_tax_cost = 0
            else:
                # Si no encuentra el producto, asumir gravado
                item_tax_cost = item_net_cost * 0.16

            total_net_cost += item_net_cost
            total_tax_cost += item_tax_cost

        total_cost_calculado = total_net_cost + total_tax_cost

        # Calcular total_exempt (suma de precios de productos exentos)
        self.mysql_cursor.execute("""
            SELECT qi.subtotal
            FROM quote_items qi
            JOIN products p ON p.id = qi.product_id
            WHERE qi.quote_id = %s
            AND (p.sale_tax IS NULL OR p.sale_tax = '' OR p.sale_tax = 'EX')
        """, (quote['id'],))

        exempt_items = self.mysql_cursor.fetchall()
        total_exempt = safe_float(sum(item[0] for item in exempt_items)) if exempt_items else 0

        # Insertar sales_operation (SIN correlative - dejar que PostgreSQL lo genere)
        # NOTA: total_net_cost, total_tax_cost, total_cost se calcularán después de insertar detalles
        sql_operation = """
        INSERT INTO public.sales_operation (
            operation_type, document_no, emission_date,
            register_date, client_code, client_name, client_id, client_name_fiscal,
            client_address, client_phone, seller, credit_days,
            expiration_date, description, store, locations, user_code,
            station, total_amount, total_net_details, total_tax_details,
            total_details, total_exempt, percent_discount, discount, total_net,
            total_tax, total, credit, cash, coin_code, canceled,
            pending, wait, total_net_cost, total_tax_cost, total_cost,
            freight_tax, freight_aliquot, document_no_internal,
            control_no, operation_comments, type_price
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING correlative
        """

        document_no = str(quote['quote_number'])
        bcv_rate = safe_float(quote.get('bcv_rate', 0))
        if bcv_rate == 0:
            bcv_rate = 170  # Valor default

        # Calcular todos los valores ANTES de pasarlos al execute
        # para evitar problemas de formateo de strings con símbolos %
        client_code = customer_doc or 'ND'
        client_id = customer_doc or f"MIG-{quote['id']}"
        client_address_final = customer_address or 'Dirección migrada'
        client_phone_final = customer_phone or 'S-N'

        quote_total = safe_float(quote.get('total', 0))
        quote_subtotal = safe_float(quote.get('subtotal', 0))
        quote_tax_amount = safe_float(quote.get('tax_amount', 0))
        quote_discount = safe_float(quote.get('discount', 0))
        quote_discount_amount = safe_float(quote.get('discount_amount', 0))

        total_net = quote_subtotal - quote_discount_amount
        expiration = emission_date + timedelta(days=1)

        # Ejecutar query con costos en 0 (se calcularán después de insertar detalles)
        self.pg_cursor.execute(sql_operation, (
            'BUDGET',                  # operation_type
            document_no,               # document_no
            emission_date,             # emission_date
            emission_date,             # register_date
            client_code,               # client_code
            customer_name,             # client_name
            client_id,                 # client_id
            client_name_fiscal,        # client_name_fiscal (desde clients.name_fiscal)
            client_address_final,      # client_address
            client_phone_final,        # client_phone
            '00',                      # seller
            1,                         # credit_days
            expiration,                # expiration_date
            '',                        # description
            '00',                      # store
            '00',                      # locations
            '00',                      # user_code
            station,                   # station (válida)
            total_quantity,            # total_amount (suma de cantidades de items)
            quote_subtotal,            # total_net_details
            quote_tax_amount,          # total_tax_details
            quote_total,               # total_details
            total_exempt,              # total_exempt (suma de precios de productos exentos)
            quote_discount,            # percent_discount
            quote_discount_amount,     # discount
            total_net,                 # total_net
            quote_tax_amount,          # total_tax
            quote_total,               # total
            0.0,                       # credit
            0.0,                       # cash
            '02',                      # coin_code (Dólar)
            False,                     # canceled
            True,                      # pending (rechazado al inicio, requiere aprobación)
            False,                     # wait (no está en espera)
            0.0,                       # total_net_cost (se calculará después)
            0.0,                       # total_tax_cost (se calculará después)
            0.0,                       # total_cost (se calculará después)
            '01',                      # freight_tax
            16,                        # freight_aliquot
            document_no,               # document_no_internal
            '',                        # control_no
            '',                        # operation_comments
            2                          # type_price (2 = precio normal)
        ))

        # Recuperar el correlative generado por PostgreSQL
        result = self.pg_cursor.fetchone()
        if result and result[0]:
            correlativo = result[0]
            self._log(f"  Quote #{quote['id']} insertado con correlative={correlativo} (auto-generado)", "debug")

            # Insertar monedas (sales_operation_coins) - pasando costos y exempt
            self._insertar_quote_monedas(correlativo, quote, bcv_rate,
                                          total_net_cost, total_tax_cost,
                                          total_cost_calculado, total_exempt)

            # Insertar items del quote
            self._insertar_quote_items(correlativo, quote, bcv_rate)

            # Insertar impuestos
            self._insertar_quote_taxes(correlativo, quote, bcv_rate)

            # Actualizar sales_operation con sumatorias de los detalles
            self._actualizar_costos_desde_detalles(correlativo)
        else:
            self._log(f"  WARNING: No se pudo obtener correlative para quote #{quote['id']}", "warning")
            correlativo = None

        # Retornar el correlative generado
        return correlativo

    def _actualizar_costos_desde_detalles(self, correlative: int):
        """
        Actualizar total_net_cost, total_tax_cost, total_cost en sales_operation
        con las sumatorias de sales_operation_details

        Args:
            correlative: Correlative del sales_operation
        """
        try:
            # Calcular sumatorias desde los detalles
            self.pg_cursor.execute("""
                UPDATE sales_operation
                SET
                    total_net_cost = (
                        SELECT COALESCE(SUM(total_net_cost), 0)
                        FROM sales_operation_details
                        WHERE main_correlative = %s
                    ),
                    total_tax_cost = (
                        SELECT COALESCE(SUM(total_tax_cost), 0)
                        FROM sales_operation_details
                        WHERE main_correlative = %s
                    ),
                    total_cost = (
                        SELECT COALESCE(SUM(total_cost), 0)
                        FROM sales_operation_details
                        WHERE main_correlative = %s
                    )
                WHERE correlative = %s
                RETURNING total_net_cost, total_tax_cost, total_cost
            """, (correlative, correlative, correlative, correlative))

            result = self.pg_cursor.fetchone()
            if result:
                tnc, ttc, tc = result
                self._log(f"  ✅ Costos actualizados desde detalles: net_cost={tnc:.2f}, tax_cost={ttc:.2f}, cost={tc:.2f}", "debug")

            self.pg_conn.commit()

        except Exception as e:
            self._log(f"  ⚠️ Error actualizando costos desde detalles: {str(e)}", "warning")
            self.pg_conn.rollback()

    def _obtener_station_valida(self, mac: str) -> str:
        """
        Obtener una station válida para el quote

        Args:
            mac: MAC address generada (no usada, tabla stations no tiene mac)

        Returns:
            Código de station válido (existente en tabla stations)
        """
        try:
            # Buscar cualquier station existente
            self.pg_cursor.execute(
                "SELECT code FROM stations LIMIT 1"
            )
            result = self.pg_cursor.fetchone()

            if result:
                station_code = result[0]
                self._log(f"  ℹ️ Usando station: {station_code}", "debug")
                return station_code

            # Si no hay ninguna, usar station por defecto '00'
            self._log("  ⚠️ No hay stations en tabla, usando '00' por defecto", "warning")
            return '00'

        except Exception as e:
            self._log(f"Error obteniendo station: {str(e)}, usando '00'", "warning")
            return '00'

    def _insertar_quote_monedas(self, correlativo: int, quote: dict, bcv_rate: float,
                                total_net_cost: float = 0, total_tax_cost: float = 0,
                                total_cost: float = 0, total_exempt: float = 0):
        """Insertar monedas del quote (sales_operation_coins)"""
        subtotal = safe_float(quote.get('subtotal', 0))
        tax_amount = safe_float(quote.get('tax_amount', 0))
        total = safe_float(quote.get('total', 0))
        discount_amount = safe_float(quote.get('discount_amount', 0))

        # Cálculos en bolívares
        subtotal_bcv = subtotal * bcv_rate
        tax_amount_bcv = tax_amount * bcv_rate
        total_bcv = total * bcv_rate
        discount_amount_bcv = discount_amount * bcv_rate

        # Calcular totales netos ANTES del execute
        total_net_usd = subtotal - discount_amount
        total_net_bcv = subtotal_bcv - discount_amount_bcv

        # Calcular costos en bolívares
        total_net_cost_bcv = total_net_cost * bcv_rate
        total_tax_cost_bcv = total_tax_cost * bcv_rate
        total_cost_bcv = total_cost * bcv_rate
        total_exempt_bcv = total_exempt * bcv_rate

        sql_coins = """
        INSERT INTO public.sales_operation_coins (
            main_correlative, coin_code, factor_type, buy_aliquot,
            sales_aliquot, total_net_details, total_tax_details,
            total_details, discount, freight, total_net, total_tax,
            total, credit, cash, total_net_cost, total_tax_cost,
            total_cost, total_exempt, total_operation
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Moneda dólar (02) - factor_type=1, aliquot=tasa BCV
        self.pg_cursor.execute(sql_coins, (
            correlativo, '02', 1, bcv_rate, bcv_rate,
            subtotal, tax_amount, total, discount_amount, 0.0,
            total_net_usd, tax_amount, total, 0.0, 0.0,
            total_net_cost, total_tax_cost, total_cost, total_exempt, 0.0
        ))

        # Moneda bolívar (01) - factor_type=0 (moneda base), aliquot=1.0
        self.pg_cursor.execute(sql_coins, (
            correlativo, '01', 0, 1.0, 1.0,
            subtotal_bcv, tax_amount_bcv, total_bcv, discount_amount_bcv, 0.0,
            total_net_bcv, tax_amount_bcv, total_bcv, 0.0, 0.0,
            total_net_cost_bcv, total_tax_cost_bcv, total_cost_bcv, total_exempt_bcv, 0.0
        ))

    def _insertar_quote_items(self, correlativo: int, quote: dict, bcv_rate: float):
        """Insertar items del quote (sales_operation_details)"""
        # Obtener items del quote con datos de products de MySQL
        query_items = """
        SELECT
            qi.description, qi.name, qi.subtotal, qi.unit, qi.unit_price, qi.total,
            qi.tax_amount, qi.discount_amount, qi.discount_percentage, qi.quantity,
            qi.product_id,
            p.code AS product_code,
            p.unitary_cost,
            p.aliquot AS sale_aliquot,
            p.buy_aliquot,
            p.product_type,
            qi.type_price
        FROM quote_items qi
        JOIN products p ON p.id = qi.product_id
        WHERE qi.quote_id = %s
        ORDER BY qi.id
        """

        self.mysql_cursor.execute(query_items, (quote['id'],))
        items = self.mysql_cursor.fetchall()

        for item in items:
            (description, name, subtotal, unit, unit_price, total,
             tax_amount, discount_amount, discount_percentage, quantity,
             product_id, product_code, unitary_cost, sale_aliquot, buy_aliquot, product_type, type_price) = item

            # Si no hay código de producto, usar migración
            if not product_code:
                product_code = f"MIG-{product_id}"
                unitary_cost = 0
                sale_aliquot = 16
                buy_aliquot = 16
                product_type = 'finished'

            # Obtener sale_tax desde PostgreSQL (tabla products)
            self.pg_cursor.execute(
                "SELECT sale_tax FROM products WHERE code = %s",
                (product_code,)
            )
            pg_product = self.pg_cursor.fetchone()
            product_sale_tax = pg_product[0] if pg_product else '01'

            # Obtener correlative Y unit_type desde products_units
            self.pg_cursor.execute(
                "SELECT correlative, unit_type FROM products_units WHERE product_code = %s LIMIT 1",
                (product_code,)
            )
            unit_result = self.pg_cursor.fetchone()
            if unit_result:
                product_unit = unit_result[0]  # correlative
                product_unit_type = unit_result[1]  # unit_type
            else:
                # Si no existe, buscar cualquier unit genérica
                self.pg_cursor.execute(
                    "SELECT correlative, unit_type FROM products_units ORDER BY correlative LIMIT 1"
                )
                generic_unit = self.pg_cursor.fetchone()
                product_unit = generic_unit[0] if generic_unit else 304  # fallback correlative
                product_unit_type = generic_unit[1] if generic_unit else 0  # fallback unit_type

            # Calcular todos los valores ANTES del execute
            qty = safe_float(quantity)
            up = safe_float(unit_price)
            ta = safe_float(tax_amount)
            sub = safe_float(subtotal)
            disc_amt = safe_float(discount_amount)
            disc_pct = safe_float(discount_percentage)
            tot = safe_float(total)

            # Calcular tax percent
            if sub > 0:
                tax_percent = (ta / sub * 100)
            else:
                tax_percent = 0

            # Valores de MySQL
            uc = safe_float(unitary_cost) if unitary_cost else 0
            sa = safe_float(sale_aliquot) if sale_aliquot else 16
            ba = safe_float(buy_aliquot) if buy_aliquot else 16

            # Calcular costos según nueva fórmula:
            unitary_cost_final = uc  # unitary_cost de MySQL
            total_net_cost = uc * qty  # total_net_cost = unitary_cost * cantidad
            total_tax_cost = uc * (ba / 100) * qty  # total_tax_cost = unitary_cost * buy_aliquot/100 * cantidad
            total_cost = total_net_cost + total_tax_cost  # total_cost = total_net_cost + total_tax_cost

            total_net = sub - disc_amt  # Precio neto (para ventas)

            # Pre-calcular descripción (evitar inline 'or')
            description_product = name if name else 'Producto migrado'

            # Insertar detalle
            sql_detail = """
            INSERT INTO public.sales_operation_details (
                main_correlative, code_product, description, description_product, amount,
                store, locations, unit, conversion_factor, unit_type, unitary_cost,
                sale_tax, sale_aliquot, price, total_net_cost, total_tax_cost,
                total_cost, total_net_gross, total_tax_gross, total_gross,
                percent_discount, discount, total_net, total_tax, total,
                coin_code, buy_aliquot, buy_tax, pending_amount, product_type, type_price
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING line
            """

            # Ejecutar INSERT con todos los valores pre-calculados
            self.pg_cursor.execute(sql_detail, (
                correlativo,
                product_code,
                '',                 # description (vacío '')
                description_product,
                qty,
                '00',
                '00',
                product_unit,       # unit (correlative de products_units)
                1.0,                # conversion_factor
                product_unit_type,  # unit_type (desde products_units)
                unitary_cost_final, # unitary_cost de MySQL
                product_sale_tax,   # sale_tax (desde products)
                sa,                 # sale_aliquot de MySQL
                up,
                total_net_cost,     # unitary_cost * cantidad
                total_tax_cost,     # unitary_cost * buy_aliquot/100 * cantidad
                total_cost,         # total_net_cost + total_tax_cost
                sub,
                ta,
                tot,
                disc_pct,
                disc_amt,
                total_net,
                ta,
                tot,
                '02',     # coin_code (dólar)
                ba,       # buy_aliquot de MySQL
                '01',     # buy_tax (general)
                qty,      # pending_amount = amount
                product_type,  # product_type de MySQL
                type_price  # type_price de quote_items
            ))

            line = self.pg_cursor.fetchone()[0]

            # Insertar monedas del detalle (pasando los nuevos valores)
            self._insertar_item_monedas(correlativo, line, item, bcv_rate, unitary_cost_final, product_code, product_sale_tax, total_net_cost, total_tax_cost, total_cost)

    def _insertar_item_monedas(self, correlativo: int, line: int, item: tuple, bcv_rate: float,
                                unitary_cost: float, product_code: str, product_sale_tax: str,
                                total_net_cost: float, total_tax_cost: float, total_cost: float):
        """Insertar monedas de un item"""
        (description, name, subtotal, unit, unit_price, total,
         tax_amount, discount_amount, discount_percentage, quantity,
         product_id, product_code_mysql, unitary_cost_mysql, sale_aliquot_mysql,
         buy_aliquot_mysql, product_type_mysql, type_price) = item

        # Calcular todos los valores ANTES del execute
        unit_price_f = safe_float(unit_price)
        quantity_f = safe_float(quantity)
        sub = safe_float(subtotal)
        ta = safe_float(tax_amount)
        tot = safe_float(total)
        disc = safe_float(discount_amount)

        # Usar los valores calculados que vienen como parámetros (de MySQL)
        # unitary_cost, total_net_cost, total_tax_cost, total_cost ya vienen calculados

        total_net = sub - disc

        sql_detail_coins = """
        INSERT INTO public.sales_operation_details_coins (
            main_correlative, main_line, unitary_cost, price,
            total_net_cost, total_tax_cost, total_cost,
            total_net_gross, total_tax_gross, total_gross,
            discount, total_net, total_tax, total, coin_code
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        self.pg_cursor.execute(sql_detail_coins, (
            correlativo, line,
            unitary_cost,       # unitary_cost de MySQL
            unit_price_f,
            total_net_cost,    # de MySQL (unitary_cost * cantidad)
            total_tax_cost,    # de MySQL (unitary_cost * buy_aliquot/100 * cantidad)
            total_cost,        # de MySQL (total_net_cost + total_tax_cost)
            sub,
            ta,
            tot,
            disc,
            total_net,
            ta,
            tot,
            '02'  # dólar
        ))

        # Bolívares
        subtotal_bcv = sub * bcv_rate
        tax_amount_bcv = ta * bcv_rate
        total_bcv = tot * bcv_rate
        discount_amount_bcv = disc * bcv_rate

        # Calcular valores en bolívares
        unitary_cost_bcv = unit_price_f * 0.8 * bcv_rate
        price_bcv = unit_price_f * bcv_rate
        total_net_cost_bcv = quantity_f * unit_price_f * 0.8 * bcv_rate
        total_tax_cost_bcv = tax_amount_bcv * 0.8
        total_cost_bcv = total_net_cost_bcv + total_tax_cost_bcv
        total_net_bcv = subtotal_bcv - discount_amount_bcv

        self.pg_cursor.execute(sql_detail_coins, (
            correlativo, line,
            unitary_cost_bcv,
            price_bcv,
            total_net_cost_bcv,
            total_tax_cost_bcv,
            total_cost_bcv,
            subtotal_bcv,
            tax_amount_bcv,
            total_bcv,
            discount_amount_bcv,
            total_net_bcv,
            tax_amount_bcv,
            total_bcv,
            '01'  # bolívar
        ))

    def _insertar_quote_taxes(self, correlativo: int, quote: dict, bcv_rate: float):
        """Insertar impuestos del quote (sales_operation_taxes)"""
        subtotal = safe_float(quote.get('subtotal', 0))
        tax_amount = safe_float(quote.get('tax_amount', 0))
        discount_amount = safe_float(quote.get('discount_amount', 0))
        bcv = safe_float(quote.get('bcv_rate', 0))
        if bcv == 0:
            bcv = 170

        # Obtener aliquot directamente desde MySQL (campo tax)
        # El campo tax en MySQL YA contiene el porcentaje (ej: 16.00)
        aliquot = safe_float(quote.get('tax', 0))

        if tax_amount > 0 and subtotal > 0:
            # Base imponible
            taxable_amount = subtotal - discount_amount

            tax_code = '01'  # IVA General

            # Insertar impuesto
            sql_tax = """
            INSERT INTO public.sales_operation_taxes (
                main_correlative, taxe_code, aliquot, taxable, tax, tax_type
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            self.pg_cursor.execute(sql_tax, (
                correlativo, tax_code, aliquot, taxable_amount, tax_amount, 1
            ))

            # Insertar moneda del impuesto (dólar)
            sql_tax_coins = """
            INSERT INTO public.sales_operation_taxes_coins (
                main_correlative, main_taxe_code, taxable, tax, coin_code
            ) VALUES (%s, %s, %s, %s, %s)
            """

            self.pg_cursor.execute(sql_tax_coins, (
                correlativo, tax_code, taxable_amount, tax_amount, '02'
            ))

            # Bolívares
            taxable_amount_bcv = taxable_amount * bcv
            tax_amount_bcv = tax_amount * bcv

            self.pg_cursor.execute(sql_tax_coins, (
                correlativo, tax_code, taxable_amount_bcv, tax_amount_bcv, '01'
            ))

    def _actualizar_status_quote_postgresql(self, quote: dict):
        """
        Actualizar status de quote en PostgreSQL basado en MySQL

        MySQL status → PostgreSQL pending
        'approved' → pending = false
        'rejected' → pending = true
        """
        try:
            quote_number = str(quote['quote_number'])
            status_mysql = quote.get('status', 'pending')

            # Determinar pending
            pending = (status_mysql != 'approved')

            # Actualizar en PostgreSQL
            update_query = """
            UPDATE public.sales_operation
            SET pending = %s
            WHERE document_no = %s
              AND operation_type = 'BUDGET'
            """

            self.pg_cursor.execute(update_query, (pending, quote_number))

            if self.pg_cursor.rowcount > 0:
                self.stats['quotes']['estados_actualizados'] += 1
                self._log(f"  🔄 Status actualizado: Quote #{quote['id']} → {status_mysql}", "debug")

        except Exception as e:
            self._log(f"Error actualizando status del quote: {str(e)}", "error")

    def _sincronizar_estados_quotes_mysql(self):
        """
        Sincronizar estados de PostgreSQL → MySQL
        Actualiza el campo 'status' en MySQL basado en 'pending' de PostgreSQL

        PostgreSQL pending → MySQL status
        pending = false → status = 'approved'
        pending = true → status = 'rejected'
        """
        try:
            self._log("Sincronizando estados de quotes (PostgreSQL → MySQL)...", "info")

            # Obtener todos los sales_operation tipo BUDGET de PostgreSQL
            query_pg = """
            SELECT
                so.document_no,
                so.pending,
                so.correlative
            FROM public.sales_operation so
            WHERE so.operation_type = 'BUDGET'
            ORDER BY so.correlative
            """

            self.pg_cursor.execute(query_pg)
            operations = self.pg_cursor.fetchall()

            if not operations:
                self._log("  No se encontraron presupuestos para sincronizar estados", "info")
                return

            estados_actualizados = 0

            for op in operations:
                try:
                    document_no, pending, correlative = op

                    # Determinar status basado en pending
                    new_status = 'rejected' if pending else 'approved'

                    # Actualizar en MySQL
                    update_mysql = """
                    UPDATE quotes
                    SET status = %s, updated_at = NOW()
                    WHERE quote_number = %s
                    """

                    self.mysql_cursor.execute(update_mysql, (new_status, str(document_no)))

                    if self.mysql_cursor.rowcount > 0:
                        estados_actualizados += 1
                        self.stats['quotes']['estados_actualizados'] += 1
                        self._log(f"  🔄 Quote #{document_no} (correlative {correlative}): "
                                f"pending={pending} → status='{new_status}'", "debug")

                        # Actualizar sync_hashes con el nuevo status
                        # Primero obtener el quote completo de MySQL para generar el hash
                        query_quote_mysql = """
                        SELECT id, quote_number, customer_id, subtotal, tax,
                               tax_amount, discount, total, status
                        FROM quotes
                        WHERE quote_number = %s
                        LIMIT 1
                        """
                        self.mysql_cursor.execute(query_quote_mysql, (str(document_no),))
                        quote_result = self.mysql_cursor.fetchone()

                        if quote_result:
                            # Crear diccionario con los datos del quote
                            quote_dict = {
                                'id': quote_result[0],
                                'quote_number': quote_result[1],
                                'customer_id': quote_result[2],
                                'subtotal': float(quote_result[3]) if quote_result[3] else 0,
                                'tax': float(quote_result[4]) if quote_result[4] else 0,
                                'tax_amount': float(quote_result[5]) if quote_result[5] else 0,
                                'discount': float(quote_result[6]) if quote_result[6] else 0,
                                'total': float(quote_result[7]) if quote_result[7] else 0,
                                'status': quote_result[8]
                            }

                            # Generar hash y guardar en sync_hashes
                            nuevo_hash = self._generar_hash_quote(quote_dict)
                            quote_dict['_postgres_correlative'] = correlative
                            self._guardar_hash('quotes', str(quote_dict['id']), nuevo_hash, quote_dict)

                except Exception as e:
                    self._log(f"  ❌ Error actualizando quote #{op[0] if op else 'unknown'}: {str(e)}", "error")

            self.mysql_conn.commit()
            self.pg_conn.commit()

            if estados_actualizados > 0:
                self._log(f"✅ Estados sincronizados: {estados_actualizados} quotes actualizados", "success")
            else:
                self._log("ℹ️  No hubo cambios de estados para sincronizar", "info")

        except Exception as e:
            self._log(f"Error sincronizando estados de quotes: {str(e)}", "error")
            self.stats['quotes']['errores'] += 1

    # ====================================================================
    # SINCRONIZACIÓN DE CAMBIOS A MYSQL
    # ====================================================================

    def sincronizar_products_mysql(self, cambios: Dict[str, List]):
        """Sincronizar cambios de products a MySQL usando BATCH INSERTS para mejor rendimiento"""
        if not any(cambios.values()):
            return

        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return

        self._log("Sincronizando changes de products a MySQL...", "info")

        # Registrar en system_logs (CREATE para nuevos, UPDATE para modificados)
        # COMENTADO: Tarda mucho guardando en system_logs
        nuevos_products = [p[0] for p in cambios['nuevos']]
        modificados_products = [p[0] for p in cambios['modificados']]

        # if nuevos_products:
        #     self._log_to_system_logs_batch('products', nuevos_products, 'CREATE')
        # if modificados_products:
        #     self._log_to_system_logs_batch('products', modificados_products, 'UPDATE')

        # Calcular total para progreso
        total_cambios = len(cambios['nuevos']) + len(cambios['modificados'])
        current_count = 0

        try:
            # Crear mapeo de categorías existentes en MySQL
            self.mysql_cursor.execute("SELECT name, id FROM categories WHERE company_id = %s",
                                     (company_id,))
            category_mapping = dict(self.mysql_cursor.fetchall())

            # 🔍 DEBUG: Verificar si hay categorías en MySQL
            self._log(f"  🔍 Categorías encontradas en MySQL: {len(category_mapping)}", "info")
            if not category_mapping:
                self._log("  ❌ ERROR CRÍTICO: NO hay categorías en MySQL", "error")
                self._log("     Los productos NO se pueden insertar sin una categoría", "error")
                self._log("     Solución: Sincroniza categories primero o crea al menos una categoría en MySQL", "error")
            else:
                self._log(f"  ✅ Categorías disponibles: {', '.join(list(category_mapping.keys())[:5])}{'...' if len(category_mapping) > 5 else ''}", "info")

            products_sin_categoria = 0

            # Verificar si hay productos en Bolívares (coin='01') para obtener tipo de cambio
            # Índices del producto: 0=code, 1=unit_code, 2=description, 3=short_name, 4=department,
            #                       5=product_code_pg, 6=unidad, 7=stock, 8=product_type, 9=coin, ...
            hay_productos_ves = any(
                p[9] == '01'  # coin es el índice 9
                for p in cambios['nuevos'] + cambios['modificados']
            )

            tipo_cambio = None
            if hay_productos_ves:
                self._log("  💰 Detectados productos en Bolívares, obteniendo tipo de cambio...", "info")
                tipo_cambio = self._obtener_tipo_cambio_ves_usd()

            # ====================================================================
            # NUEVOS - BATCH INSERT
            # ====================================================================
            total_nuevos = len(cambios['nuevos'])
            if total_nuevos > 0:
                self._log(f"  📦 Preparando BATCH INSERT de {total_nuevos} productos NUEVOS...", "info")

                # Recolectar todos los datos para batch insert
                batch_data = []
                productos_a_procesar = []

                for idx, producto in enumerate(cambios['nuevos'], 1):
                    if not self.sync_running:
                        break

                    try:
                        # Desempaquetar con todos los campos
                        (code, unit_code, description, short_name, department, product_code_pg,
                         unidad, stock, product_type, coin, description_coin, price, cost, higher_price,
                         min_stock, status, image_type, product_image, sale_tax, aliquot, buy_tax, buy_aliquot, unitary_cost, allow_decimal) = producto

                        # DEBUG: Mostrar coin para depuración
                        if code == 'TESTVES':
                            self._log(f"  🔍 DEBUG TESTVES: coin='{coin}', price={price}, cost={cost}, higher_price={higher_price}", "info")

                        # 🔧 MANEJO DE VALORES NULL - Usar valores por defecto
                        # Si department es NULL o vacío, intentar usar una categoría por defecto
                        if not department or department.strip() == '':
                            # Buscar la primera categoría disponible en MySQL
                            if category_mapping:
                                department = list(category_mapping.keys())[0]
                                self._log(f"  ℹ️ Product {code}: usando categoría por defecto '{department}'", "debug")
                            else:
                                self._log(f"  ⚠️ Product {code} omitido: no hay categorías disponibles en MySQL", "warning")
                                products_sin_categoria += 1
                                continue

                        # Verificar que la categoría existe en MySQL
                        if department not in category_mapping:
                            self._log(f"  ⚠️ Product {code} omitido: categoría '{department}' no existe en MySQL", "warning")
                            products_sin_categoria += 1
                            continue

                        category_id = category_mapping[department]

                        # Si coin es NULL o vacío, usar '02' (USD) como valor por defecto
                        if not coin or coin.strip() == '':
                            coin = '02'  # USD por defecto
                            self._log(f"  ℹ️ Product {code}: usando moneda por defecto '02' (USD)", "debug")

                        # Si description_coin es NULL, usar descripción genérica
                        if not description_coin or description_coin.strip() == '':
                            description_coin = 'USD' if coin == '02' else 'VES'
                            self._log(f"  ℹ️ Product {code}: usando descripción de moneda por defecto '{description_coin}'", "debug")

                        # Manejar campos NULL que son NOT NULL en MySQL
                        if not sale_tax or sale_tax.strip() == '':
                            sale_tax = ''  # Valor vacío permitido
                        if aliquot is None or aliquot == 0:
                            aliquot = 0  # 0% IVA por defecto
                        if not buy_tax or buy_tax.strip() == '':
                            buy_tax = ''  # Valor vacío permitido
                        if buy_aliquot is None or buy_aliquot == 0:
                            buy_aliquot = 0  # 0% IVA por defecto

                        # Manejo de allow_decimal (booleano)
                        if allow_decimal is None:
                            allow_decimal = False  # Por defecto no permite decimales

                        # 🔧 MANEJO DE short_name NULL - Usar description como fallback
                        # MySQL exige que 'name' no sea NULL
                        if not short_name or (isinstance(short_name, str) and short_name.strip() == ''):
                            if description and description.strip():
                                short_name = description[:100]  # Usar description (max 100 chars)
                                self._log(f"  ℹ️ Product {code}: usando description como short_name", "debug")
                            else:
                                short_name = code  # Último recurso: usar el code
                                self._log(f"  ℹ️ Product {code}: usando code como short_name (último recurso)", "debug")

                        # Crear JSON de imagen
                        image_json = self._create_image_json(image_type, product_image)

                        # 💰 CONVERTIR DE VES A USD si coin='01'
                        final_price = safe_float(price)
                        final_cost = safe_float(cost)
                        final_higher_price = safe_float(higher_price)
                        final_unitary_cost = safe_float(unitary_cost) if unitary_cost else 0

                        if coin == '01' and tipo_cambio:
                            final_price = self._convertir_ves_a_usd(final_price, tipo_cambio)
                            final_cost = self._convertir_ves_a_usd(final_cost, tipo_cambio)
                            final_higher_price = self._convertir_ves_a_usd(final_higher_price, tipo_cambio)
                            final_unitary_cost = self._convertir_ves_a_usd(final_unitary_cost, tipo_cambio)

                            if idx == 1:  # Solo mostrar el primer producto como ejemplo
                                self._log(f"  💱 Conversión VES→USD: {code} - {price:.2f} VES → {final_price:.4f} USD (tasa: {tipo_cambio:.2f})", "info")

                        # Preparar datos para batch insert
                        batch_data.append((
                            company_id,
                            code,
                            short_name,
                            description if description else None,
                            final_price,
                            final_cost,
                            float(stock) if stock else 0,
                            int(min_stock) if min_stock else 0,
                            category_id,
                            status,
                            product_type,
                            image_json,
                            final_higher_price,
                            sale_tax,  # Ya tiene valor por defecto si era NULL
                            aliquot,   # Ya tiene valor por defecto si era NULL
                            coin,  # Ya tiene valor por defecto si era NULL
                            description_coin,  # Ya tiene valor por defecto si era NULL
                            final_unitary_cost,
                            buy_tax,  # Ya tiene valor por defecto si era NULL
                            buy_aliquot,  # Ya tiene valor por defecto si era NULL
                            unidad,  # Unidad de medida
                            allow_decimal  # Permite decimales (boolean)
                        ))

                        productos_a_procesar.append((idx, code))

                    except Exception as e:
                        self._log(f"  ⚠️ Error preparando producto {producto[0] if producto else 'unknown'}: {str(e)[:100]}", "warning")
                        self.stats['products']['errores'] += 1

                # Ejecutar BATCH INSERT
                if batch_data:
                    self._log(f"  🚀 Ejecutando BATCH INSERT de {len(batch_data)} productos...", "info")
                    start_time = time.time()

                    insert_query = """
                    INSERT INTO products (
                        company_id, code, name, description, price, cost, stock, min_stock,
                        category_id, status, product_type, images, higher_price, sale_tax,
                        aliquot, coin, description_coin, unitary_cost, buy_tax, buy_aliquot,
                        unidad, allow_decimal, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        description = VALUES(description),
                        price = VALUES(price),
                        cost = VALUES(cost),
                        stock = VALUES(stock),
                        min_stock = VALUES(min_stock),
                        category_id = VALUES(category_id),
                        status = VALUES(status),
                        product_type = VALUES(product_type),
                        images = VALUES(images),
                        higher_price = VALUES(higher_price),
                        sale_tax = VALUES(sale_tax),
                        aliquot = VALUES(aliquot),
                        coin = VALUES(coin),
                        description_coin = VALUES(description_coin),
                        unitary_cost = VALUES(unitary_cost),
                        buy_tax = VALUES(buy_tax),
                        buy_aliquot = VALUES(buy_aliquot),
                        unidad = VALUES(unidad),
                        allow_decimal = VALUES(allow_decimal),
                        updated_at = NOW()
                    """

                    try:
                        self.mysql_cursor.executemany(insert_query, batch_data)
                        rows_affected = self.mysql_cursor.rowcount
                        self._log(f"  📊 executemany afectó {rows_affected} filas", "info")

                        self.mysql_conn.commit()
                        self._log(f"  ✅ Commit ejecutado correctamente", "info")

                    except Exception as insert_error:
                        # 🔍 GUARDAR ERROR EN ARCHIVO (SILENCIOSO - no mostrar al usuario)
                        if self.mysql_error_logger:
                            self.mysql_error_logger.log_batch_error(
                                operation="BATCH INSERT products",
                                batch_data=batch_data,
                                error=insert_error
                            )

                        # Mostrar mensaje simple al usuario
                        self._log(f"  ⚠️ Error al insertar productos en MySQL (ver log en carpeta logs/mysql_errors/)", "warning")
                        self.mysql_conn.rollback()
                        raise

                    elapsed = time.time() - start_time
                    self.stats['products']['nuevos'] += len(batch_data)
                    self._log(f"  ✅ BATCH INSERT completado: {len(batch_data)} productos en {elapsed:.2f}s ({elapsed/len(batch_data)*1000:.1f} ms/promedio)", "success")

                    # Reportar progreso
                    for idx, code in productos_a_procesar:
                        self._reportar_progreso('products', idx, total_cambios)

            # ====================================================================
            # MODIFICADOS - BATCH UPDATE
            # ====================================================================
            total_modificados = len(cambios['modificados'])
            if total_modificados > 0:
                self._log(f"  📦 Preparando BATCH UPDATE de {total_modificados} productos MODIFICADOS...", "info")

                # Recolectar todos los datos para batch update
                batch_data = []
                productos_a_procesar = []

                for idx, producto in enumerate(cambios['modificados'], 1):
                    if not self.sync_running:
                        break

                    try:
                        # Desempaquetar con todos los campos
                        (code, unit_code, description, short_name, department, product_code_pg,
                         unidad, stock, product_type, coin, description_coin, price, cost, higher_price,
                         min_stock, status, image_type, product_image, sale_tax, aliquot, buy_tax, buy_aliquot, unitary_cost, allow_decimal) = producto

                        # DEBUG: Mostrar coin para depuración
                        if code == 'TESTVES':
                            self._log(f"  🔍 DEBUG TESTVES: coin='{coin}', price={price}, cost={cost}, higher_price={higher_price}", "info")

                        # 🔧 MANEJO DE VALORES NULL - Usar valores por defecto
                        # Si department es NULL o vacío, intentar usar una categoría por defecto
                        if not department or department.strip() == '':
                            # Buscar la primera categoría disponible en MySQL
                            if category_mapping:
                                department = list(category_mapping.keys())[0]
                                self._log(f"  ℹ️ Product {code} (modificado): usando categoría por defecto '{department}'", "debug")
                            else:
                                self._log(f"  ⚠️ Product {code} omitido: no hay categorías disponibles en MySQL", "warning")
                                products_sin_categoria += 1
                                continue

                        # Verificar que la categoría existe en MySQL
                        if department not in category_mapping:
                            self._log(f"  ⚠️ Product {code} omitido: categoría '{department}' no existe en MySQL", "warning")
                            products_sin_categoria += 1
                            continue

                        category_id = category_mapping[department]

                        # Si coin es NULL o vacío, usar '02' (USD) como valor por defecto
                        if not coin or coin.strip() == '':
                            coin = '02'  # USD por defecto
                            self._log(f"  ℹ️ Product {code} (modificado): usando moneda por defecto '02' (USD)", "debug")

                        # Si description_coin es NULL, usar descripción genérica
                        if not description_coin or description_coin.strip() == '':
                            description_coin = 'USD' if coin == '02' else 'VES'
                            self._log(f"  ℹ️ Product {code} (modificado): usando descripción de moneda por defecto '{description_coin}'", "debug")

                        # Manejar campos NULL que son NOT NULL en MySQL
                        if not sale_tax or sale_tax.strip() == '':
                            sale_tax = ''  # Valor vacío permitido
                        if aliquot is None or aliquot == 0:
                            aliquot = 0  # 0% IVA por defecto
                        if not buy_tax or buy_tax.strip() == '':
                            buy_tax = ''  # Valor vacío permitido
                        if buy_aliquot is None or buy_aliquot == 0:
                            buy_aliquot = 0  # 0% IVA por defecto

                        # Manejo de allow_decimal (booleano)
                        if allow_decimal is None:
                            allow_decimal = False  # Por defecto no permite decimales

                        # 🔧 MANEJO DE short_name NULL - Usar description como fallback
                        # MySQL exige que 'name' no sea NULL
                        if not short_name or (isinstance(short_name, str) and short_name.strip() == ''):
                            if description and description.strip():
                                short_name = description[:100]  # Usar description (max 100 chars)
                                self._log(f"  ℹ️ Product {code}: usando description como short_name", "debug")
                            else:
                                short_name = code  # Último recurso: usar el code
                                self._log(f"  ℹ️ Product {code}: usando code como short_name (último recurso)", "debug")

                        # Crear JSON de imagen
                        image_json = self._create_image_json(image_type, product_image)

                        # 💰 CONVERTIR DE VES A USD si coin='01'
                        final_price = safe_float(price)
                        final_cost = safe_float(cost)
                        final_higher_price = safe_float(higher_price)
                        final_unitary_cost = safe_float(unitary_cost) if unitary_cost else 0

                        if coin == '01' and tipo_cambio:
                            final_price = self._convertir_ves_a_usd(final_price, tipo_cambio)
                            final_cost = self._convertir_ves_a_usd(final_cost, tipo_cambio)
                            final_higher_price = self._convertir_ves_a_usd(final_higher_price, tipo_cambio)
                            final_unitary_cost = self._convertir_ves_a_usd(final_unitary_cost, tipo_cambio)

                        # Preparar datos para batch update (mismo formato que insert)
                        batch_data.append((
                            company_id,
                            code,
                            short_name,
                            description if description else None,
                            final_price,
                            final_cost,
                            float(stock) if stock else 0,
                            int(min_stock) if min_stock else 0,
                            category_id,
                            status,
                            product_type,
                            image_json,
                            final_higher_price,
                            sale_tax,  # Ya tiene valor por defecto si era NULL
                            aliquot,   # Ya tiene valor por defecto si era NULL
                            coin,  # Ya tiene valor por defecto si era NULL
                            description_coin,  # Ya tiene valor por defecto si era NULL
                            final_unitary_cost,
                            buy_tax,  # Ya tiene valor por defecto si era NULL
                            buy_aliquot,  # Ya tiene valor por defecto si era NULL
                            unidad,  # Unidad de medida
                            allow_decimal  # Permite decimales (boolean)
                        ))

                        productos_a_procesar.append((idx, code))

                    except Exception as e:
                        self._log(f"  ⚠️ Error preparando producto {producto[0] if producto else 'unknown'}: {str(e)[:100]}", "warning")
                        self.stats['products']['errores'] += 1

                # Ejecutar BATCH UPDATE
                if batch_data:
                    self._log(f"  🚀 Ejecutando BATCH UPDATE de {len(batch_data)} productos...", "info")
                    start_time = time.time()

                    # Usamos INSERT ... ON DUPLICATE KEY UPDATE para actualizar
                    update_query = """
                    INSERT INTO products (
                        company_id, code, name, description, price, cost, stock, min_stock,
                        category_id, status, product_type, images, higher_price, sale_tax,
                        aliquot, coin, description_coin, unitary_cost, buy_tax, buy_aliquot,
                        unidad, allow_decimal, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                    )
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name),
                        description = VALUES(description),
                        price = VALUES(price),
                        cost = VALUES(cost),
                        stock = VALUES(stock),
                        min_stock = VALUES(min_stock),
                        category_id = VALUES(category_id),
                        status = VALUES(status),
                        product_type = VALUES(product_type),
                        images = VALUES(images),
                        higher_price = VALUES(higher_price),
                        sale_tax = VALUES(sale_tax),
                        aliquot = VALUES(aliquot),
                        coin = VALUES(coin),
                        description_coin = VALUES(description_coin),
                        unitary_cost = VALUES(unitary_cost),
                        buy_tax = VALUES(buy_tax),
                        buy_aliquot = VALUES(buy_aliquot),
                        unidad = VALUES(unidad),
                        allow_decimal = VALUES(allow_decimal),
                        updated_at = NOW()
                    """

                    try:
                        self.mysql_cursor.executemany(update_query, batch_data)
                        rows_affected = self.mysql_cursor.rowcount
                        self._log(f"  📊 executemany afectó {rows_affected} filas", "info")

                        self.mysql_conn.commit()
                        self._log(f"  ✅ Commit ejecutado correctamente", "info")

                    except Exception as update_error:
                        # 🔍 GUARDAR ERROR EN ARCHIVO (SILENCIOSO - no mostrar al usuario)
                        if self.mysql_error_logger:
                            self.mysql_error_logger.log_batch_error(
                                operation="BATCH UPDATE products",
                                batch_data=batch_data,
                                error=update_error
                            )

                        # Mostrar mensaje simple al usuario
                        self._log(f"  ⚠️ Error al actualizar productos en MySQL (ver log en carpeta logs/mysql_errors/)", "warning")
                        self.mysql_conn.rollback()
                        raise

                    elapsed = time.time() - start_time
                    self.stats['products']['modificados'] += len(batch_data)
                    self._log(f"  ✅ BATCH UPDATE completado: {len(batch_data)} productos en {elapsed:.2f}s ({elapsed/len(batch_data)*1000:.1f} ms/promedio)", "success")

                    # Reportar progreso
                    for idx, code in productos_a_procesar:
                        idx_adjusted = total_nuevos + idx
                        self._reportar_progreso('products', idx_adjusted, total_cambios)

            # Reportar productos omitidos
            if products_sin_categoria > 0:
                self._log(f"  ⚠️ {products_sin_categoria} productos omitidos por categoría inexistente", "warning")

            self.mysql_conn.commit()
            self._log(f"✅ Products sincronizados: {self.stats['products']['nuevos']} nuevos, "
                      f"{self.stats['products']['modificados']} modificados", "success")

            # Sincronizar productos inactivos/reactivados
            self._sincronizar_status_products_mysql(cambios['eliminados'])

        except Exception as e:
            # 🔍 GUARDAR ERROR EN ARCHIVO (SILENCIOSO - no mostrar al usuario)
            if self.mysql_error_logger:
                self.mysql_error_logger.log_error(
                    operation="Sincronización products a MySQL",
                    error=e,
                    context=f"Productos nuevos: {len(cambios.get('nuevos', []))}, "
                           f"Productos modificados: {len(cambios.get('modificados', []))}"
                )

            # Mostrar mensaje simple al usuario
            self._log(f"⚠️ Error al sincronizar products (ver log en carpeta logs/mysql_errors/)", "warning")
            self.stats['products']['errores'] += 1

            # Si es un error de conexión, propagar hacia arriba para detener la sincronización
            error_msg = str(e).lower()
            if any(err in error_msg for err in ['connection', 'timeout', 'mysql', 'database', 'operational']):
                self._log("❌ Error crítico de conexión - deteniendo sincronización", "error")
                raise  # Propagar el error para que ejecutar_sync_completa lo maneje

    def _sincronizar_status_products_mysql(self, productos_inactivos: List[Dict]):
        """
        Sincroniza cambios de status (active/inactive) de products a MySQL

        Args:
            productos_inactivos: Lista de productos inactivos detectados
        """
        if not productos_inactivos:
            return

        self._log(f"Sincronizando {len(productos_inactivos)} productos inactivos/reactivados a MySQL...", "info")

        try:
            for producto in productos_inactivos:
                code = producto['code']

                # Actualizar status a 'inactive' en MySQL
                update_query = """
                UPDATE products
                SET status = 'inactive',
                    updated_at = NOW()
                WHERE company_id = %s
                  AND code = %s
                """

                self.mysql_cursor.execute(update_query, (company_id, code))

                if self.mysql_cursor.rowcount > 0:
                    self._log(f"  🔄 Status actualizado: {code} → inactive", "debug")
                    self.stats['products']['eliminados'] += 1

            self.mysql_conn.commit()
            self._log(f"✅ Status sincronizados: {len(productos_inactivos)} productos", "success")

        except Exception as e:
            self._log(f"Error sincronizando status de products: {str(e)}", "error")

    def sincronizar_customers_mysql(self, cambios: Dict[str, List]):
        """Sincronizar cambios de customers a MySQL"""
        if not any(cambios.values()):
            return

        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return

        self._log("Sincronizando cambios de customers a MySQL...", "info")

        # Registrar en system_logs (CREATE para nuevos, UPDATE para modificados)
        # COMENTADO: Tarda mucho guardando en system_logs
        nuevos_customers = [c[0] for c in cambios['nuevos']]
        modificados_customers = [c[0] for c in cambios['modificados']]

        # if nuevos_customers:
        #     self._log_to_system_logs_batch('customers', nuevos_customers, 'CREATE')
        # if modificados_customers:
        #     self._log_to_system_logs_batch('customers', modificados_customers, 'UPDATE')

        # Calcular total para progreso
        total_cambios = len(cambios['nuevos']) + len(cambios['modificados'])
        current_count = 0

        try:
            # Nuevos
            total_nuevos = len(cambios['nuevos'])
            if total_nuevos > 0:
                self._log(f"  👥 Insertando {total_nuevos} customers NUEVOS...", "info")

            for idx, cliente in enumerate(cambios['nuevos'], 1):
                if not self.sync_running:
                    break

                try:
                    code, description, address, client_id, email, phone, contact = cliente

                    if not email or email.strip() == '':
                        email = f"customer_{code}@temp.local"

                    # VERIFICAR si existe ANTES de insertar
                    check_query = """
                    SELECT id
                    FROM customers
                    WHERE company_id = %s AND document_number = %s
                    """
                    self.mysql_cursor.execute(check_query, (company_id, code))
                    existe = self.mysql_cursor.fetchone()

                    if existe:
                        # Ya existe - ACTUALIZAR
                        update_query = """
                        UPDATE customers SET
                            name = %s,
                            email = %s,
                            address = %s,
                            phone = %s,
                            contact = %s,
                            updated_at = NOW()
                        WHERE company_id = %s AND document_number = %s
                        """
                        self.mysql_cursor.execute(update_query, (
                            description, email, address if address else None,
                            phone if phone else None, contact if contact else None,
                            company_id, code
                        ))
                        self._log(f"  🔄 Customer {code} ya existía, actualizado", "debug")
                        self.stats['customers']['modificados'] += 1
                    else:
                        # No existe - INSERTAR
                        insert_query = """
                        INSERT INTO customers (
                            company_id, name, email, document_number, address, phone, contact,
                            status, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """
                        self.mysql_cursor.execute(insert_query, (
                            company_id, description, email, code,
                            address if address else None, phone if phone else None,
                            contact if contact else None, 'active'
                        ))
                        self.stats['customers']['nuevos'] += 1

                    # Commit cada 50 customers para no acumular transacción enorme
                    if idx % 50 == 0:
                        self.mysql_conn.commit()
                        self._log(f"  ✅ Commit parcial: {idx}/{total_nuevos} customers procesados", "debug")

                    # Reportar progreso después de insertar exitosamente
                    self._reportar_progreso('customers', idx, total_cambios)

                except Exception as e:
                    # Error con un customer específico - continuar con los demás
                    self._log(f"  ⚠️ Error procesando customer {code}: {str(e)[:100]}", "warning")
                    self.stats['customers']['errores'] += 1

                    # Reportar progreso aunque haya error
                    self._reportar_progreso('customers', idx, total_cambios)

            # Commit final de los nuevos
            if total_nuevos > 0:
                self.mysql_conn.commit()
                self._log(f"  ✅ Commit final: {self.stats['customers']['nuevos']}/{total_nuevos} customers nuevos insertados", "success")

            # Modificados
            total_modificados = len(cambios['modificados'])
            if total_modificados > 0:
                self._log(f"  👥 Actualizando {total_modificados} customers MODIFICADOS...", "info")

            for idx, cliente in enumerate(cambios['modificados'], 1):
                if not self.sync_running:
                    break

                try:
                    code, description, address, client_id, email, phone, contact = cliente

                    if not email or email.strip() == '':
                        email = f"customer_{code}@temp.local"

                    update_query = """
                    UPDATE customers SET
                        name = %s, email = %s, address = %s, phone = %s,
                        contact = %s, updated_at = NOW()
                    WHERE company_id = %s AND document_number = %s
                    """

                    self.mysql_cursor.execute(update_query, (
                        description, email, address if address else None,
                        phone if phone else None, contact if contact else None,
                        company_id, code
                    ))

                    self.stats['customers']['modificados'] += 1
                    # Commit cada 50 customers
                    if idx % 50 == 0:
                        self.mysql_conn.commit()
                        self._log(f"  ✅ Commit parcial: {idx}/{total_modificados} customers actualizados", "debug")

                    # Reportar progreso después de actualizar exitosamente (ajustar idx para continuar desde los nuevos)
                    idx_adjusted = total_nuevos + idx
                    self._reportar_progreso('customers', idx_adjusted, total_cambios)

                except Exception as e:
                    # Error con un customer específico - continuar con los demás
                    self._log(f"  ⚠️ Error actualizando customer {code}: {str(e)[:100]}", "warning")
                    self.stats['customers']['errores'] += 1

                    # Reportar progreso aunque haya error
                    idx_adjusted = total_nuevos + idx
                    self._reportar_progreso('customers', idx_adjusted, total_cambios)

            # Commit final de los modificados
            if total_modificados > 0:
                self.mysql_conn.commit()
                self._log(f"  ✅ Commit final: {self.stats['customers']['modificados']}/{total_modificados} customers modificados actualizados", "success")

            self._log(f"✅ Customers sincronizados: {self.stats['customers']['nuevos']} nuevos, "
                      f"{self.stats['customers']['modificados']} modificados, {self.stats['customers']['errores']} errores", "success")

        except Exception as e:
            self._log(f"Error sincronizando customers a MySQL: {str(e)}", "error")
            self.stats['customers']['errores'] += 1

            # Si es un error de conexión, propagar hacia arriba para detener la sincronización
            error_msg = str(e).lower()
            if any(err in error_msg for err in ['connection', 'timeout', 'mysql', 'database', 'operational']):
                self._log("❌ Error crítico de conexión - deteniendo sincronización", "error")
                raise  # Propagar el error para que ejecutar_sync_completa lo maneje

    # ====================================================================
    # SINCRONIZACIÓN DE PRODUCTS (MYSQL → POSTGRESQL)
    # ====================================================================

    def _eliminar_productos_mysql_cuando_faltan_en_postgresql(self):
        """
        Elimina productos de MySQL cuando fueron eliminados de PostgreSQL

        Lógica MEJORADA con TRIGGER:
        1. El trigger en PostgreSQL marca automáticamente los productos eliminados
        2. Solo leemos sync_hashes donde deleted_at IS NOT NULL
        3. Eliminamos esos productos de MySQL
        4. Limpiamos el registro de sync_hashes

        Esto es MUY eficiente porque:
        - No recorre todos los productos de MySQL
        - Solo procesa los productos que realmente fueron eliminados
        - El trigger hace el trabajo automáticamente
        """
        try:
            # Obtener company_id desde companies
            company_id = self._get_company_id_from_companies()
            if not company_id:
                self._log("   ❌ No se pudo obtener company_id", "error")
                return

            self._log("", "info")
            self._log("🗑️ VERIFICANDO PRODUCTOS ELIMINADOS EN POSTGRESQL...", "info")

            # Consulta eficiente: solo productos marcados como eliminados por el trigger
            query = """
            SELECT record_key
            FROM sync_hashes
            WHERE table_name = 'products'
            AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """
            self.pg_cursor.execute(query)
            productos_eliminados = self.pg_cursor.fetchall()

            if not productos_eliminados:
                self._log("   ℹ️ No hay productos eliminados que procesar", "info")
                return

            self._log(f"   📋 Encontrados {len(productos_eliminados)} productos eliminados en PostgreSQL", "info")

            productos_a_eliminar = []

            # PASO 1: Verificar cuáles productos existen en MySQL
            for (product_code,) in productos_eliminados:
                if not self.sync_running:
                    break

                # Buscar el producto en MySQL
                self.mysql_cursor.execute(
                    "SELECT id FROM products WHERE code = %s AND company_id = %s",
                    (product_code, company_id)
                )
                producto_mysql = self.mysql_cursor.fetchone()

                if producto_mysql:
                    product_id = producto_mysql[0]
                    productos_a_eliminar.append((product_id, product_code))
                    self._log(f"   🗑️ Producto {product_code} (ID: {product_id}) será eliminado de MySQL", "debug")
                else:
                    # Ya no existe en MySQL, solo limpiar sync_hashes
                    self._log(f"   ℹ️ Producto {product_code} ya no existe en MySQL", "debug")

            # PASO 2: Eliminar productos de MySQL
            if productos_a_eliminar:
                self._log(f"   🗑️ Eliminando {len(productos_a_eliminar)} productos de MySQL...", "info")

                for product_id, product_code in productos_a_eliminar:
                    try:
                        # Eliminar de MySQL
                        delete_query = """
                        DELETE FROM products
                        WHERE id = %s AND company_id = %s
                        """
                        self.mysql_cursor.execute(delete_query, (product_id, company_id))

                        self._log(f"   ✅ Producto {product_code} eliminado de MySQL", "info")

                    except Exception as e:
                        self._log(f"   ❌ Error eliminando product {product_code} de MySQL: {e}", "error")
                        self.stats['products']['errores'] += 1

                # Commit cambios en MySQL
                self.mysql_conn.commit()

                self._log(f"   ✅ {len(productos_a_eliminar)} productos eliminados de MySQL", "success")

                # Actualizar estadísticas
                self.stats['products']['eliminados'] = self.stats.get('products', {}).get('eliminados', 0) + len(productos_a_eliminar)
            else:
                self._log("   ℹ️ No hay productos que eliminar de MySQL (ya fueron limpiados)", "info")

            # PASO 3: Limpiar registros de sync_hashes (incluyendo los que ya no existen en MySQL)
            self._log("   🧹 Limpiando registros de sync_hashes...", "info")
            self.pg_cursor.execute(
                "DELETE FROM sync_hashes WHERE table_name = 'products' AND deleted_at IS NOT NULL"
            )
            filas_limpias = self.pg_cursor.rowcount
            self.pg_conn.commit()
            self._log(f"   ✅ {filas_limpias} registros eliminados de sync_hashes", "info")

        except Exception as e:
            self._log(f"Error verificando productos eliminados: {e}", "error")
            import traceback
            self._log(f"TRACEBACK:\n{traceback.format_exc()}", "error")

    def _eliminar_customers_mysql_cuando_faltan_en_postgresql(self):
        """
        Elimina customers de MySQL cuando fueron eliminados de PostgreSQL

        Lógica MEJORADA con TRIGGER:
        1. El trigger en PostgreSQL marca automáticamente los customers eliminados
        2. Solo leemos sync_hashes donde deleted_at IS NOT NULL
        3. Eliminamos esos customers de MySQL
        4. Limpiamos el registro de sync_hashes
        """
        try:
            # Obtener company_id desde companies
            company_id = self._get_company_id_from_companies()
            if not company_id:
                self._log("   ❌ No se pudo obtener company_id", "error")
                return

            self._log("", "info")
            self._log("🗑️ VERIFICANDO CUSTOMERS ELIMINADOS EN POSTGRESQL...", "info")
            self._log(f"   🔍 Company ID: {company_id}", "debug")

            # 🔍 DIAGNÓSTICO: Verificar si el trigger existe
            self.pg_cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_trigger
                    WHERE tgname = 'tr_clients_mark_deleted_sync_hashes'
                )
            """)
            trigger_existe = self.pg_cursor.fetchone()[0]
            self._log(f"   🔍 Trigger existe: {trigger_existe}", "debug")

            # Consulta eficiente: solo customers marcados como eliminados por el trigger
            query = """
            SELECT record_key
            FROM sync_hashes
            WHERE table_name = 'customers'
            AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """
            self.pg_cursor.execute(query)
            customers_eliminados = self.pg_cursor.fetchall()

            self._log(f"   🔍 Total customers marcados como eliminados: {len(customers_eliminados)}", "debug")
            if customers_eliminados:
                for (code,) in customers_eliminados[:5]:  # Mostrar primeros 5
                    self._log(f"      - code={code}", "debug")

            if not customers_eliminados:
                self._log("   ℹ️ No hay customers eliminados que procesar", "info")
                self._log("   💡 Si borraste un cliente en PostgreSQL y no aparece aquí:", "info")
                self._log("      1. Verifica que el trigger esté creado", "info")
                self._log("      2. Verifica que el cliente realmente se borró (DELETE FROM clients)", "info")
                self._log("      3. Revisa la tabla sync_hashes manualmente", "info")
                return

            self._log(f"   📋 Encontrados {len(customers_eliminados)} customers eliminados en PostgreSQL", "info")

            customers_a_eliminar = []

            # PASO 1: Verificar cuáles customers existen en MySQL
            for (customer_code,) in customers_eliminados:
                if not self.sync_running:
                    break

                # Buscar el customer en MySQL
                self.mysql_cursor.execute(
                    "SELECT id, name FROM customers WHERE document_number = %s AND company_id = %s",
                    (customer_code, company_id)
                )
                customer_mysql = self.mysql_cursor.fetchone()

                if customer_mysql:
                    customer_id, customer_name = customer_mysql
                    customers_a_eliminar.append((customer_id, customer_code))
                    self._log(f"   🗑️ Customer {customer_code} (ID: {customer_id}, Name: {customer_name}) será eliminado de MySQL", "debug")
                else:
                    # Ya no existe en MySQL, solo limpiar sync_hashes
                    self._log(f"   ℹ️ Customer {customer_code} ya no existe en MySQL", "debug")

            # PASO 2: Eliminar customers de MySQL
            if customers_a_eliminar:
                self._log(f"   🗑️ Eliminando {len(customers_a_eliminar)} customers de MySQL...", "info")

                for customer_id, customer_code in customers_a_eliminar:
                    try:
                        # Eliminar de MySQL por ID (más eficiente)
                        delete_query = """
                        DELETE FROM customers
                        WHERE id = %s AND company_id = %s
                        """
                        self.mysql_cursor.execute(delete_query, (customer_id, company_id))

                        self._log(f"   ✅ Customer {customer_code} eliminado de MySQL", "info")

                    except Exception as e:
                        self._log(f"   ❌ Error eliminando customer {customer_code} de MySQL: {e}", "error")
                        self.stats['customers']['errores'] += 1

                # Commit cambios en MySQL
                self.mysql_conn.commit()
                self._log(f"   ✅ {len(customers_a_eliminar)} customers eliminados de MySQL", "success")

                # Actualizar estadísticas
                self.stats['customers']['eliminados'] = self.stats.get('customers', {}).get('eliminados', 0) + len(customers_a_eliminar)
            else:
                self._log("   ℹ️ No hay customers que eliminar de MySQL (ya fueron limpiados)", "info")

            # PASO 3: Limpiar registros de sync_hashes (incluyendo los que ya no existen en MySQL)
            self._log("   🧹 Limpiando registros de sync_hashes...", "info")

            # 3.1 Limpiar registros de customers (PostgreSQL → MySQL)
            self.pg_cursor.execute(
                "DELETE FROM sync_hashes WHERE table_name = 'customers' AND deleted_at IS NOT NULL"
            )
            filas_limpias_customers = self.pg_cursor.rowcount
            self.pg_conn.commit()
            self._log(f"   ✅ {filas_limpias_customers} registros 'customers' eliminados de sync_hashes", "debug")

            # 3.2 También limpiar registros de customers_mysql para evitar re-sincronización desde MySQL
            # Buscar los IDs de MySQL correspondientes a los códigos eliminados
            filas_limpias_customers_mysql = 0
            if customers_a_eliminar:
                # Obtener los customer_ids que eliminamos de MySQL
                customer_ids_eliminados = [str(cid) for (cid, _) in customers_a_eliminar]

                if customer_ids_eliminados:
                    # Eliminar registros de customers_mysql correspondientes
                    placeholders_ids = ','.join(['%s'] * len(customer_ids_eliminados))
                    query_delete_mysql = f"""
                    DELETE FROM sync_hashes
                    WHERE table_name = 'customers_mysql'
                    AND record_key IN ({placeholders_ids})
                    """
                    self.pg_cursor.execute(query_delete_mysql, customer_ids_eliminados)
                    filas_limpias_customers_mysql = self.pg_cursor.rowcount
                    self.pg_conn.commit()
                    if filas_limpias_customers_mysql > 0:
                        self._log(f"   ✅ {filas_limpias_customers_mysql} registros 'customers_mysql' eliminados de sync_hashes", "info")

            filas_limpias = filas_limpias_customers + filas_limpias_customers_mysql
            self._log(f"   ✅ Total {filas_limpias} registros eliminados de sync_hashes", "info")

        except Exception as e:
            self._log(f"Error verificando customers eliminados: {e}", "error")
            import traceback
            self._log(f"TRACEBACK:\n{traceback.format_exc()}", "error")

    def _eliminar_sellers_mysql_cuando_faltan_en_postgresql(self):
        """
        Elimina sellers de MySQL cuando fueron eliminados de PostgreSQL

        Lógica MEJORADA con TRIGGER:
        1. El trigger en PostgreSQL marca automáticamente los sellers eliminados
        2. Solo leemos sync_hashes donde deleted_at IS NOT NULL
        3. Eliminamos esos sellers de MySQL
        4. Limpiamos el registro de sync_hashes
        """
        try:
            # Obtener company_id desde companies
            company_id = self._get_company_id_from_companies()
            if not company_id:
                self._log("   ❌ No se pudo obtener company_id", "error")
                return

            self._log("", "info")
            self._log("🗑️ VERIFICANDO SELLERS ELIMINADOS EN POSTGRESQL...", "info")

            # Consulta eficiente: solo sellers marcados como eliminados por el trigger
            query = """
            SELECT record_key
            FROM sync_hashes
            WHERE table_name = 'sellers'
            AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """
            self.pg_cursor.execute(query)
            sellers_eliminados = self.pg_cursor.fetchall()

            if not sellers_eliminados:
                self._log("   ℹ️ No hay sellers eliminados que procesar", "info")
                return

            self._log(f"   📋 Encontrados {len(sellers_eliminados)} sellers eliminados en PostgreSQL", "info")

            sellers_a_eliminar = []

            # PASO 1: Verificar cuáles sellers existen en MySQL
            for (seller_email,) in sellers_eliminados:
                if not self.sync_running:
                    break

                # Buscar el seller en MySQL por code (email en PG)
                self.mysql_cursor.execute(
                    "SELECT id FROM sellers WHERE code = %s AND company_id = %s",
                    (seller_email, company_id)
                )
                seller_mysql = self.mysql_cursor.fetchone()

                if seller_mysql:
                    seller_id = seller_mysql[0]
                    sellers_a_eliminar.append((seller_id, seller_email))
                    self._log(f"   🗑️ Seller {seller_email} (ID: {seller_id}) será eliminado de MySQL", "debug")
                else:
                    # Ya no existe en MySQL, solo limpiar sync_hashes
                    self._log(f"   ℹ️ Seller {seller_email} ya no existe en MySQL", "debug")

            # PASO 2: Eliminar sellers de MySQL
            if sellers_a_eliminar:
                self._log(f"   🗑️ Eliminando {len(sellers_a_eliminar)} sellers de MySQL...", "info")

                for seller_id, seller_email in sellers_a_eliminar:
                    try:
                        # Eliminar de MySQL
                        delete_query = """
                        DELETE FROM sellers
                        WHERE id = %s AND company_id = %s
                        """
                        self.mysql_cursor.execute(delete_query, (seller_id, company_id))

                        self._log(f"   ✅ Seller {seller_email} eliminado de MySQL", "info")

                    except Exception as e:
                        self._log(f"   ❌ Error eliminando seller {seller_email} de MySQL: {e}", "error")
                        self.stats['sellers']['errores'] += 1

                # Commit cambios en MySQL
                self.mysql_conn.commit()

                self._log(f"   ✅ {len(sellers_a_eliminar)} sellers eliminados de MySQL", "success")

                # Actualizar estadísticas
                self.stats['sellers']['eliminados'] = self.stats.get('sellers', {}).get('eliminados', 0) + len(sellers_a_eliminar)
            else:
                self._log("   ℹ️ No hay sellers que eliminar de MySQL (ya fueron limpiados)", "info")

            # PASO 3: Limpiar registros de sync_hashes (incluyendo los que ya no existen en MySQL)
            self._log("   🧹 Limpiando registros de sync_hashes...", "info")
            self.pg_cursor.execute(
                "DELETE FROM sync_hashes WHERE table_name = 'sellers' AND deleted_at IS NOT NULL"
            )
            filas_limpias = self.pg_cursor.rowcount
            self.pg_conn.commit()
            self._log(f"   ✅ {filas_limpias} registros eliminados de sync_hashes", "info")

        except Exception as e:
            self._log(f"Error verificando sellers eliminados: {e}", "error")
            import traceback
            self._log(f"TRACEBACK:\n{traceback.format_exc()}", "error")

    def sincronizar_products_postgresql(self, cambios: Dict[str, List]):
        """
        Sincronizar products de MySQL a PostgreSQL

        NOTA: PostgreSQL es la fuente de verdad para products.
        Solo se INSERTAN products que no existen (ej: creados desde quotes),
        pero NUNCA se ACTUALIZAN products existentes desde MySQL.

        Args:
            cambios: Dict con 'nuevos' y 'modificados'
        """
        if not cambios.get('nuevos') and not cambios.get('modificados'):
            self._log("✅ Productos: No hay cambios para sincronizar (MySQL → PG)", "info")
            return

        total_nuevos = len(cambios.get('nuevos', []))
        total_modificados = len(cambios.get('modificados', []))

        # IGNORAR modificados - PostgreSQL es la fuente de verdad
        if total_modificados > 0:
            self._log(f"   ℹ️ Ignorando {total_modificados} products modificados en MySQL (PostgreSQL es la fuente de verdad)", "info")

        if total_nuevos == 0:
            return

        self._log("", "info")
        self._log("📦 SINCRONIZANDO PRODUCTS NUEVOS (MySQL → PostgreSQL)...", "info")
        self._log(f"   📋 Nuevos: {total_nuevos} (modificados ignorados)", "info")

        try:
            # Obtener valores válidos para columnas con restricciones
            self.pg_cursor.execute("SELECT code FROM status WHERE code != '00' LIMIT 1")
            status_row = self.pg_cursor.fetchone()
            status_valido = status_row[0] if status_row else '01'

            # Procesar SOLO products nuevos (ignorar modificados)
            products_a_procesar = cambios.get('nuevos', [])
            total_a_procesar = len(products_a_procesar)
            current_count = 0

            for product in products_a_procesar:
                if not self.sync_running:
                    break

                product_id = product['id']
                product_code = product['code']
                current_count += 1

                try:
                    # Verificar si ya existe
                    self.pg_cursor.execute(
                        "SELECT code FROM products WHERE code = %s",
                        (product_code,)
                    )
                    existe = self.pg_cursor.fetchone()

                    if existe:
                        # Ya existe - IGNORAR (PostgreSQL es la fuente de verdad)
                        self._log(f"  ℹ️ Product {product_code} ya existe en PostgreSQL (omitiendo)", "debug")

                        # Guardar hash para no volver a procesarlo
                        hash_nuevo = self._generar_hash_product_mysql(product)
                        self._guardar_hash('products_mysql', str(product_id), hash_nuevo, product)
                        continue

                    # No existe - INSERTAR
                    self._log(f"  ✨ Insertando product {product_code}...", "debug")

                    # Manejar valores NULL correctamente
                    description = product.get('description') or ''
                    cost = product.get('cost')
                    price = product.get('price')
                    product_type = product.get('product_type') or 'finished'

                    # Convertir a float, usar 0 si es None
                    try:
                        cost_val = float(cost) if cost is not None else 0.0
                    except (ValueError, TypeError):
                        cost_val = 0.0

                    try:
                        price_val = float(price) if price is not None else 0.0
                    except (ValueError, TypeError):
                        price_val = 0.0

                    # Calcular sale_price (en centimos)
                    sale_price_cents = int(price_val * 100) if price_val > 0 else 0

                    # Compatible con PostgreSQL 9.1 - Ya verificamos arriba que no existe
                    sql_insert = """
                    INSERT INTO products (
                        code, description, minimal_sale, maximal_sale,
                        status, product_type, sale_price
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    self.pg_cursor.execute(sql_insert, (
                        product_code,
                        description[:255] if description else '',
                        cost_val,
                        price_val,
                        status_valido,
                        product_type,
                        sale_price_cents
                    ))

                    self.pg_conn.commit()

                    # Actualizar estadísticas y reportar progreso
                    self.stats['products']['nuevos'] += 1
                    self._reportar_progreso('products', current_count, total_a_procesar)

                    # Guardar hash DESPUÉS de insertar
                    hash_nuevo = self._generar_hash_product_mysql(product)
                    self._guardar_hash('products_mysql', str(product_id), hash_nuevo, product)

                except Exception as e:
                    error_msg = str(e).lower()
                    if 'duplicate' in error_msg or 'unique' in error_msg:
                        self._log(f"  ℹ️ Product {product_code} ya existe (omitiendo)", "debug")
                        self.pg_conn.rollback()
                    else:
                        import traceback
                        self._log(f"Error procesando product {product_code}: {str(e)}", "error")
                        self._log(f"TRACEBACK:\n{traceback.format_exc()}", "error")
                        self.pg_conn.rollback()
                        self.stats['products']['errores'] += 1

            self._log(f"✅ Products completados: {self.stats['products']['nuevos']} nuevos insertados, "
                      f"{self.stats['products']['errores']} errores", "success")

        except Exception as e:
            self._log(f"Error sincronizando products a PostgreSQL: {str(e)}", "error")
            self.stats['products']['errores'] += 1

    def sincronizar_customers_postgresql(self, cambios: Dict[str, List]):
        """
        Sincronizar customers de MySQL a PostgreSQL

        NOTA: PostgreSQL es la fuente de verdad para customers.
        Solo se INSERTAN customers que no existen,
        pero NUNCA se ACTUALIZAN customers existentes desde MySQL.

        Args:
            cambios: Dict con 'nuevos' y 'modificados'
        """
        if not cambios.get('nuevos') and not cambios.get('modificados'):
            self._log("✅ Clientes: No hay cambios para sincronizar (MySQL → PG)", "info")
            return

        total_nuevos = len(cambios.get('nuevos', []))
        total_modificados = len(cambios.get('modificados', []))

        # IGNORAR modificados - PostgreSQL es la fuente de verdad
        if total_modificados > 0:
            self._log(f"   ℹ️ Ignorando {total_modificados} customers modificados en MySQL (PostgreSQL es la fuente de verdad)", "info")

        if total_nuevos == 0:
            return

        self._log("", "info")
        self._log("👥 SINCRONIZANDO CUSTOMERS NUEVOS (MySQL → PostgreSQL)...", "info")
        self._log(f"   📋 Nuevos: {total_nuevos} (modificados ignorados)", "info")

        try:
            # Procesar SOLO customers nuevos (ignorar modificados)
            customers_a_procesar = cambios.get('nuevos', [])
            total_a_procesar = len(customers_a_procesar)
            current_count = 0

            for customer in customers_a_procesar:
                if not self.sync_running:
                    break

                customer_id = customer['id']
                customer_code = customer['document_number']
                current_count += 1

                try:
                    # Verificar si ya existe
                    self.pg_cursor.execute(
                        "SELECT code FROM clients WHERE code = %s",
                        (customer_code,)
                    )
                    existe = self.pg_cursor.fetchone()

                    if existe:
                        # Ya existe - IGNORAR (PostgreSQL es la fuente de verdad)
                        self._log(f"  ℹ️ Customer {customer_code} ya existe en PostgreSQL (omitiendo)", "debug")

                        # Guardar hash para no volver a procesarlo
                        hash_nuevo = self._generar_hash_customer_mysql(customer)
                        self._guardar_hash('customers_mysql', str(customer_id), hash_nuevo, customer)
                        continue

                    # No existe - INSERTAR
                    self._log(f"  ✨ Insertando customer {customer_code}...", "debug")

                    # Manejar valores NULL correctamente
                    name = customer.get('name', '')
                    address = customer.get('address')
                    email = customer.get('email')
                    phone = customer.get('phone')
                    contact = customer.get('contact')

                    # Generar email temporal si no existe
                    if not email or email.strip() == '':
                        email = f"customer_{customer_code}@temp.local"

                    # Insertar en tabla clients de PostgreSQL con valores por defecto
                    sql_insert = """
                    INSERT INTO clients (
                        code, description, address, email, phone, contact,
                        client_id, country, province, city, town, area_sales,
                        seller, client_group, credit_days, credit_limit,
                        discount, client_type, sale_price, status,
                        name_fiscal, generic_client
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    self.pg_cursor.execute(sql_insert, (
                        customer_code,                           # code
                        name[:255] if name else '',              # description
                        address,                                 # address
                        email,                                   # email
                        phone,                                   # phone
                        contact,                                 # contact
                        customer_code,                           # client_id = code
                        '00',                                    # country
                        '00',                                    # province
                        '00',                                    # city
                        '00',                                    # town
                        '00',                                    # area_sales
                        '00',                                    # seller
                        '00',                                    # client_group
                        0,                                       # credit_days
                        0,                                       # credit_limit
                        0,                                       # discount
                        '01',                                    # client_type
                        0,                                       # sale_price
                        '01',                                    # status
                        0,                                       # name_fiscal
                        True                                     # generic_client
                    ))

                    self.pg_conn.commit()

                    # Actualizar estadísticas y reportar progreso
                    self.stats['customers']['nuevos'] += 1
                    self._reportar_progreso('customers', current_count, total_a_procesar)

                    # Guardar hash DESPUÉS de insertar
                    hash_nuevo = self._generar_hash_customer_mysql(customer)
                    self._guardar_hash('customers_mysql', str(customer_id), hash_nuevo, customer)

                except Exception as e:
                    error_msg = str(e).lower()
                    if 'duplicate' in error_msg or 'unique' in error_msg:
                        self._log(f"  ℹ️ Customer {customer_code} ya existe (omitiendo)", "debug")
                        self.pg_conn.rollback()
                    else:
                        import traceback
                        self._log(f"Error procesando customer {customer_code}: {str(e)}", "error")
                        self._log(f"TRACEBACK:\n{traceback.format_exc()}", "error")
                        self.pg_conn.rollback()
                        self.stats['customers']['errores'] += 1

            self._log(f"✅ Customers completados: {self.stats['customers']['nuevos']} nuevos insertados, "
                      f"{self.stats['customers']['errores']} errores", "success")

        except Exception as e:
            self._log(f"Error sincronizando customers a PostgreSQL: {str(e)}", "error")
            self.stats['customers']['errores'] += 1

    def sincronizar_categories_mysql(self, cambios: Dict[str, List]):
        """Sincronizar cambios de categories a MySQL"""
        if not any(cambios.values()):
            return

        # Obtener company_id desde companies
        company_id = self._get_company_id_from_companies()
        if not company_id:
            self._log("   ❌ No se pudo obtener company_id", "error")
            return

        self._log("Sincronizando cambios de categories a MySQL...", "info")

        # Registrar en system_logs (CREATE para nuevos, UPDATE para modificados)
        # COMENTADO: Tarda mucho guardando en system_logs
        nuevos_categories = [c[0] for c in cambios['nuevos']]
        modificados_categories = [c[0] for c in cambios['modificados']]

        # if nuevos_categories:
        #     self._log_to_system_logs_batch('categories', nuevos_categories, 'CREATE')
        # if modificados_categories:
        #     self._log_to_system_logs_batch('categories', modificados_categories, 'UPDATE')

        # Calcular total para progreso
        total_cambios = len(cambios['nuevos']) + len(cambios['modificados'])
        current_count = 0

        try:
            # Nuevos
            total_nuevos = len(cambios['nuevos'])
            if total_nuevos > 0:
                self._log(f"  📁 Insertando {total_nuevos} categories NUEVAS...", "info")

            for idx, (code, description) in enumerate(cambios['nuevos'], 1):
                if not self.sync_running:
                    break

                try:
                    insert_query = """
                    INSERT INTO categories (company_id, name, description, status, created_at, updated_at)
                    VALUES (%s, %s, %s, 'active', NOW(), NOW())
                    """

                    self.mysql_cursor.execute(insert_query, (
                        company_id, code, description if description else None
                    ))

                    self.stats['categories']['nuevos'] += 1
                    current_count += 1
                    self._reportar_progreso('categories', current_count, total_cambios)

                    # Commit cada 50 categories para no acumular transacción enorme
                    if idx % 50 == 0:
                        self.mysql_conn.commit()
                        self._log(f"  ✅ Commit parcial: {idx}/{total_nuevos} categories insertadas", "debug")

                except Exception as e:
                    # Error con un category específico - continuar con los demás
                    error_msg = str(e).lower()
                    if 'duplicate' in error_msg or 'unique' in error_msg:
                        self._log(f"  ℹ️ Category {code} ya existe (omitiendo)", "debug")
                    else:
                        self._log(f"  ⚠️ Error insertando category {code}: {str(e)[:100]}", "warning")
                        self.stats['categories']['errores'] += 1

            # Commit final de los nuevos
            if total_nuevos > 0:
                self.mysql_conn.commit()
                self._log(f"  ✅ Commit final: {self.stats['categories']['nuevos']}/{total_nuevos} categories nuevas insertadas", "success")

            # Modificados
            total_modificados = len(cambios['modificados'])
            if total_modificados > 0:
                self._log(f"  📁 Actualizando {total_modificados} categories MODIFICADAS...", "info")

            for idx, (code, description) in enumerate(cambios['modificados'], 1):
                if not self.sync_running:
                    break

                try:
                    update_query = """
                    UPDATE categories SET description = %s, updated_at = NOW()
                    WHERE company_id = %s AND name = %s
                    """

                    self.mysql_cursor.execute(update_query, (
                        description if description else None, company_id, code
                    ))

                    self.stats['categories']['modificados'] += 1
                    current_count += 1
                    self._reportar_progreso('categories', current_count, total_cambios)

                    # Commit cada 50 categories
                    if idx % 50 == 0:
                        self.mysql_conn.commit()
                        self._log(f"  ✅ Commit parcial: {idx}/{total_modificados} categories actualizadas", "debug")

                except Exception as e:
                    # Error con un category específico - continuar con los demás
                    self._log(f"  ⚠️ Error actualizando category {code}: {str(e)[:100]}", "warning")
                    self.stats['categories']['errores'] += 1

            # Commit final de los modificados
            if total_modificados > 0:
                self.mysql_conn.commit()
                self._log(f"  ✅ Commit final: {self.stats['categories']['modificados']}/{total_modificados} categories modificadas actualizadas", "success")

            self._log(f"✅ Categories sincronizados: {self.stats['categories']['nuevos']} nuevos, "
                      f"{self.stats['categories']['modificados']} modificados, {self.stats['categories']['errores']} errores", "success")

        except Exception as e:
            self._log(f"Error sincronizando categories a MySQL: {str(e)}", "error")
            self.stats['categories']['errores'] += 1

            # Si es un error de conexión, propagar hacia arriba para detener la sincronización
            error_msg = str(e).lower()
            if any(err in error_msg for err in ['connection', 'timeout', 'mysql', 'database', 'operational']):
                self._log("❌ Error crítico de conexión - deteniendo sincronización", "error")
                raise  # Propagar el error para que ejecutar_sync_completa lo maneje

    # ====================================================================
    # SINCRONIZACIÓN DE SELLERS
    # ====================================================================

    def _sincronizar_sellers(self):
        """
        Sincronizar sellers desde PostgreSQL a MySQL
        Usa SmartSellersSyncModule para la sincronización
        """
        # Registrar en system_logs (sincronización completa)
        # COMENTADO: Tarda mucho guardando en system_logs
        # self._log_to_system_logs('sellers', '', 'SYNC')

        try:
            # Agregar directorio actual al sys.path para encontrar el módulo
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)

            from smart_sellers_sync_module import SmartSellersSyncModule

            # Preparar configuraciones
            postgresql_config = {
                'host': self.postgresql_config['host'],
                'port': self.postgresql_config['port'],
                'database': self.postgresql_config['database'],
                'user': self.postgresql_config['user'],
                'password': self.postgresql_config['password']
            }

            mysql_config = {
                'host': self.mysql_config['host'],
                'port': int(self.mysql_config['port']),
                'database': self.mysql_config['database'],
                'user': self.mysql_config['user'],
                'password': self.mysql_config['password']
            }

            # Crear módulo de sellers
            sellers_sync = SmartSellersSyncModule(self)

            # Conectar
            if not sellers_sync.conectar_postgresql(postgresql_config):
                self._log("❌ No se pudo conectar a PostgreSQL para sellers", "error")
                self.stats['sellers']['errores'] += 1
                sellers_sync.cerrar()
                return

            if not sellers_sync.conectar_mysql(mysql_config):
                self._log("❌ No se pudo conectar a MySQL para sellers", "error")
                self.stats['sellers']['errores'] += 1
                sellers_sync.cerrar()
                return

            # Ejecutar sincronización y obtener estadísticas
            resultado = sellers_sync.ejecutar_sync()

            # Cerrar conexiones
            sellers_sync.cerrar()

            # Actualizar estadísticas (solo si resultado es un dict)
            if isinstance(resultado, dict):
                self.stats['sellers']['nuevos'] = resultado.get('nuevos', 0)
                self.stats['sellers']['modificados'] = resultado.get('actualizados', 0)
                self.stats['sellers']['errores'] = resultado.get('errores', 0)

                if resultado.get('exito', False):
                    self._log("✅ Sellers sincronizados correctamente", "success")
                else:
                    self._log("⚠️  Sincronización de sellers completada con errores", "warning")

        except ImportError:
            self._log("❌ Módulo smart_sellers_sync_module no encontrado", "error")
            self.stats['sellers']['errores'] += 1
        except Exception as e:
            self._log(f"❌ Error sincronizando sellers: {str(e)}", "error")
            self.stats['sellers']['errores'] += 1

    # ====================================================================
    # MÉTODO PRINCIPAL
    # ====================================================================

    def ejecutar_sync_completa(self) -> bool:
        """
        Ejecutar sincronización completa detectando cambios

        Returns:
            True si exitoso, False si hubo errores
        """
        inicio = datetime.now()

        self._log("", "info")
        self._log("╔════════════════════════════════════════════════════════════════╗", "info")
        self._log("║          SINCRONIZACIÓN INTELIGENTE CON TABLA DE HASHES          ║", "info")
        self._log("╚════════════════════════════════════════════════════════════════╝", "info")
        self._log("", "info")

        try:
            # Conectar bases de datos
            if not self._conectar_bases_datos():
                return False

            # Obtener company_id desde MySQL
            if not self._obtener_company_id():
                self._log("❌ No se pudo obtener el company_id. Verifica RIF y email en la configuración.", "error")
                return False

            # Actualizar company_id en sync_config (ahora que ya hay conexión a MySQL)
            self._actualizar_company_id_en_config()

            # Detectar cambios en cada entidad
            self._log("🔍 STEP 1: Detectando cambios en products...", "debug")
            cambios_products = self.detectar_cambios_products()

            self._log("🔍 STEP 2: Detectando cambios en customers...", "debug")
            cambios_customers = self.detectar_cambios_customers()

            self._log("🔍 STEP 3: Detectando cambios en categories...", "debug")
            cambios_categories = self.detectar_cambios_categories()

            # IMPORTANTE: Eliminar de MySQL ANTES de detectar cambios desde MySQL
            # Esto evita que se re-sincronicen elementos que fueron eliminados de PostgreSQL
            self._log("", "info")
            self._log("🗑️ ELIMINANDO DE MYSQL LO QUE FALTA EN POSTGRESQL...", "info")
            self._log("🗑️ ELIMINANDO PRODUCTOS MARCADOS COMO BORRADOS...", "info")
            self._eliminar_productos_mysql_cuando_faltan_en_postgresql()
            self._log("🗑️ ELIMINANDO CUSTOMERS MARCADOS COMO BORRADOS...", "info")
            self._eliminar_customers_mysql_cuando_faltan_en_postgresql()
            self._log("🗑️ ELIMINANDO CATEGORIES MARCADAS COMO BORRADAS...", "info")
            self._eliminar_categories_mysql_cuando_faltan_en_postgresql()
            self._log("🗑️ ELIMINACIÓN DE MYSQL COMPLETADA", "debug")

            # Detectar cambios en products de MySQL (para sincronizar a PostgreSQL)
            # AHORA se detecta DESPUÉS de eliminar, así no se detectan los eliminados
            self._log("🔍 STEP 4: Detectando cambios en products (MySQL → PostgreSQL)...", "debug")
            cambios_products_mysql = self.detectar_cambios_products_mysql()

            # Detectar cambios en customers de MySQL (para sincronizar a PostgreSQL)
            # AHORA se detecta DESPUÉS de eliminar, así no se detectan los eliminados
            self._log("🔍 STEP 5: Detectando cambios en customers (MySQL → PostgreSQL)...", "debug")
            cambios_customers_mysql = self.detectar_cambios_customers_mysql()

            # Detectar cambios en quotes (MySQL → PostgreSQL)
            self._log("🔍 STEP 6: Detectando cambios en quotes...", "debug")
            cambios_quotes = self.detectar_cambios_quotes()
            self._log("🔍 STEP 6 COMPLETADO", "debug")

            # Sincronizar sellers siempre (no usa hash, sincronización completa)
            self._log("", "info")
            self._log("👤 SINCRONIZANDO SELLERS...", "info")
            self._sincronizar_sellers()
            # Eliminar de MySQL los sellers que fueron eliminados de PostgreSQL
            self._eliminar_sellers_mysql_cuando_faltan_en_postgresql()

            # Verificar si hay cambios (después de eliminar)
            total_cambios = (
                len(cambios_products['nuevos']) + len(cambios_products['modificados']) +
                len(cambios_customers['nuevos']) + len(cambios_customers['modificados']) +
                len(cambios_categories['nuevos']) + len(cambios_categories['modificados']) +
                len(cambios_quotes['nuevos']) + len(cambios_quotes['modificados']) +
                len(cambios_products_mysql['nuevos']) + len(cambios_products_mysql['modificados']) +
                len(cambios_customers_mysql['nuevos']) + len(cambios_customers_mysql['modificados'])
            )

            if total_cambios == 0:
                self._log("✨ No hay cambios que sincronizar", "success")
                return True

            # SINCRONIZAR EN ORDEN CORRECTO (dependencias primero)
            # 1. Categories (requerido por products)
            self._log("", "info")
            self._log("📦 SINCRONIZANDO CATEGORIES...", "info")
            self.sincronizar_categories_mysql(cambios_categories)

            # 2. Products (dependen de categories)
            self._log("", "info")
            self._log("📦 SINCRONIZANDO PRODUCTS...", "info")
            self.sincronizar_products_mysql(cambios_products)

            # 3. Customers (independiente)
            self._log("", "info")
            self._log("👥 SINCRONIZANDO CUSTOMERS...", "info")
            self.sincronizar_customers_mysql(cambios_customers)

            # 4. Products de MySQL → PostgreSQL (ANTES de quotes para que existan)
            # Sincronizar nuevos productos
            self.sincronizar_products_postgresql(cambios_products_mysql)

            # 5. Customers de MySQL → PostgreSQL (ANTES de quotes para que existan)
            # Sincronizar nuevos customers
            self.sincronizar_customers_postgresql(cambios_customers_mysql)

            # 6. Quotes a PostgreSQL (dirección opuesta, requiere products y customers)
            self.sincronizar_quotes_postgresql(cambios_quotes)

            # Sincronizar estados de quotes (PostgreSQL → MySQL)
            self._log("", "info")
            self._log("🔄 SINCRONIZANDO ESTADOS DE QUOTES...", "info")
            self._sincronizar_estados_quotes_mysql()

            # Reporte final
            duracion = (datetime.now() - inicio).total_seconds()

            # Guardar duración para que esté disponible para notificaciones externas
            self.duracion_sync = duracion
            self._log("", "info")
            self._log("╔════════════════════════════════════════════════════════════════╗", "info")
            self._log("║                    RESUMEN DE SINCRONIZACIÓN                    ║", "info")
            self._log("╚════════════════════════════════════════════════════════════════╝", "info")
            self._log(f"Productos:   {self.stats['products']['nuevos']} nuevos, "
                      f"{self.stats['products']['modificados']} modificados, "
                      f"{self.stats['products'].get('eliminados', 0)} eliminados", "success")
            self._log(f"Clientes:  {self.stats['customers']['nuevos']} nuevos, "
                      f"{self.stats['customers']['modificados']} modificados, "
                      f"{self.stats['customers'].get('eliminados', 0)} eliminados", "success")
            self._log(f"Departamentos: {self.stats['categories']['nuevos']} nuevos, "
                      f"{self.stats['categories']['modificados']} modificados, "
                      f"{self.stats['categories'].get('eliminados', 0)} eliminados", "success")
            self._log(f"Vendedores:    {self.stats['sellers']['nuevos']} nuevos, "
                      f"{self.stats['sellers']['modificados']} actualizados, "
                      f"{self.stats['sellers'].get('eliminados', 0)} eliminados", "success")
            self._log(f"Quotes:     {self.stats['quotes']['nuevos']} nuevos (MySQL→PG), "
                      f"{self.stats['quotes']['estados_actualizados']} estados actualizados", "success")
            self._log(f"Duración:   {duracion:.2f} segundos", "info")
            self._log("", "info")

            if sum(s['errores'] for s in self.stats.values()) == 0:
                self._log("✅ SINCRONIZACIÓN COMPLETADA CON ÉXITO", "success")
                # Mostrar notificación toast de Windows con todas las entidades
                parts = []

                # Products (productos)
                products_total = self.stats['products']['nuevos'] + self.stats['products']['modificados']
                if products_total > 0 or self.stats['products'].get('eliminados', 0) > 0:
                    part = f"Productos: {products_total} nuevos/modificados"
                    if self.stats['products'].get('eliminados', 0) > 0:
                        part += f", {self.stats['products'].get('eliminados', 0)} eliminados"
                    parts.append(part)

                # Customers (clientes)
                customers_total = self.stats['customers']['nuevos'] + self.stats['customers']['modificados']
                if customers_total > 0 or self.stats['customers'].get('eliminados', 0) > 0:
                    part = f"Clientes: {customers_total} nuevos/modificados"
                    if self.stats['customers'].get('eliminados', 0) > 0:
                        part += f", {self.stats['customers'].get('eliminados', 0)} eliminados"
                    parts.append(part)

                # Sellers (vendedores)
                sellers_total = self.stats['sellers']['nuevos'] + self.stats['sellers']['modificados']
                if sellers_total > 0 or self.stats['sellers'].get('eliminados', 0) > 0:
                    part = f"Vendedores: {sellers_total} nuevos/modificados"
                    if self.stats['sellers'].get('eliminados', 0) > 0:
                        part += f", {self.stats['sellers'].get('eliminados', 0)} eliminados"
                    parts.append(part)

                # Categories (departamentos)
                categories_total = self.stats['categories']['nuevos'] + self.stats['categories']['modificados']
                if categories_total > 0 or self.stats['categories'].get('eliminados', 0) > 0:
                    part = f"Departamentos: {categories_total} nuevos/modificados"
                    if self.stats['categories'].get('eliminados', 0) > 0:
                        part += f", {self.stats['categories'].get('eliminados', 0)} eliminados"
                    parts.append(part)

                mensaje = " | ".join(parts) + f" | Duración: {duracion:.1f}s"

                self._mostrar_notificacion(
                    titulo="✅ Sincronización Completada",
                    mensaje=mensaje,
                    duracion=5
                )
            else:
                self._log("⚠️ SINCRONIZACIÓN COMPLETADA CON ERRORES", "warning")
                # Mostrar notificación toast con advertencia
                errores_count = sum(s['errores'] for s in self.stats.values())
                self._mostrar_notificacion(
                    titulo="⚠️ Sincronización con Errores",
                    mensaje=f"Completada con {errores_count} error(es). Revisa el log para detalles.",
                    duracion=10
                )

            return True

        except Exception as e:
            self._log(f"❌ Error durante sincronización: {str(e)}", "error")
            return False

        finally:
            self._cerrar_conexiones()
            self._close_log_file()  # Cerrar archivo de log

    def _eliminar_categories_mysql_cuando_faltan_en_postgresql(self):
        """
        Elimina categories de MySQL cuando fueron eliminados de PostgreSQL

        Lógica MEJORADA con TRIGGER:
        1. El trigger en PostgreSQL marca automáticamente las categories eliminadas
        2. Solo leemos sync_hashes donde deleted_at IS NOT NULL
        3. Eliminamos esas categories de MySQL
        4. Limpiamos el registro de sync_hashes
        """
        try:
            # Obtener company_id desde companies
            company_id = self._get_company_id_from_companies()
            if not company_id:
                self._log("   ❌ No se pudo obtener company_id", "error")
                return

            self._log("", "info")
            self._log("🗑️ VERIFICANDO CATEGORIES ELIMINADAS EN POSTGRESQL...", "info")

            # Consulta eficiente: solo categories marcadas como eliminadas por el trigger
            query = """
            SELECT record_key
            FROM sync_hashes
            WHERE table_name = 'categories'
            AND deleted_at IS NOT NULL
            ORDER BY deleted_at DESC
            """
            self.pg_cursor.execute(query)
            categories_eliminadas = self.pg_cursor.fetchall()

            if not categories_eliminadas:
                self._log("   ℹ️ No hay categories eliminadas que procesar", "info")
                return

            self._log(f"   📋 Encontradas {len(categories_eliminadas)} categories eliminadas en PostgreSQL", "info")

            categories_a_eliminar = []

            # PASO 1: Verificar cuáles categories existen en MySQL
            for (category_code,) in categories_eliminadas:
                if not self.sync_running:
                    break

                # Buscar la category en MySQL por name (no por code, MySQL usa name)
                self.mysql_cursor.execute(
                    "SELECT id FROM categories WHERE name = %s AND company_id = %s",
                    (category_code, company_id)
                )
                category_mysql = self.mysql_cursor.fetchone()

                if category_mysql:
                    category_id = category_mysql[0]
                    categories_a_eliminar.append((category_id, category_code))
                    self._log(f"   🗑️ Category {category_code} (ID: {category_id}) será eliminada de MySQL", "debug")
                else:
                    # Ya no existe en MySQL, solo limpiar sync_hashes
                    self._log(f"   ℹ️ Category {category_code} ya no existe en MySQL", "debug")

            # PASO 2: Eliminar categories de MySQL
            if categories_a_eliminar:
                self._log(f"   🗑️ Eliminando {len(categories_a_eliminar)} categories de MySQL...", "info")

                for category_id, category_code in categories_a_eliminar:
                    try:
                        # Eliminar de MySQL
                        delete_query = """
                        DELETE FROM categories
                        WHERE id = %s AND company_id = %s
                        """
                        self.mysql_cursor.execute(delete_query, (category_id, company_id))

                        self._log(f"   ✅ Category {category_code} eliminada de MySQL", "info")

                    except Exception as e:
                        self._log(f"   ❌ Error eliminando category {category_code} de MySQL: {e}", "error")
                        self.stats['categories']['errores'] = self.stats.get('categories', {}).get('errores', 0) + 1

                # Commit cambios en MySQL
                self.mysql_conn.commit()

                self._log(f"   ✅ {len(categories_a_eliminar)} categories eliminadas de MySQL", "success")

                # Actualizar estadísticas
                self.stats['categories']['eliminados'] = self.stats.get('categories', {}).get('eliminados', 0) + len(categories_a_eliminar)
            else:
                self._log("   ℹ️ No hay categories que eliminar de MySQL (ya fueron limpiadas)", "info")

            # PASO 3: Limpiar registros de sync_hashes (incluyendo los que ya no existen en MySQL)
            self._log("   🧹 Limpiando registros de sync_hashes...", "info")
            self.pg_cursor.execute(
                "DELETE FROM sync_hashes WHERE table_name = 'categories' AND deleted_at IS NOT NULL"
            )
            filas_limpias = self.pg_cursor.rowcount
            self.pg_conn.commit()
            self._log(f"   ✅ {filas_limpias} registros eliminados de sync_hashes", "info")

        except Exception as e:
            self._log(f"Error verificando categories eliminadas: {e}", "error")
            import traceback
            self._log(f"TRACEBACK:\n{traceback.format_exc()}", "error")


# ====================================================================
# CLASE ADAPTER PARA SERVICIO (Sin interfaz gráfica)
# ====================================================================

class ServiceApp:
    """
    Adapter para usar SmartSyncComplete sin interfaz Tkinter
    Compatible con servicio de Windows
    """

    def __init__(self, postgresql_config: dict, mysql_config: dict, company_id: int):
        self.postgresql_config = postgresql_config
        self.mysql_config = mysql_config
        self.company_id = company_id
        self.sync_running = True

        # Configurar logging
        logging.basicConfig(
            filename='sync_service.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='a'
        )

    def log_message(self, mensaje: str, tipo: str = 'info'):
        """Log usando logging module"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prefijos = {
            'error': '❌ ERROR:',
            'success': '✅ ÉXITO:',
            'warning': '⚠️ ADVERTENCIA:',
            'info': 'ℹ️ INFO:',
            'debug': '🔍 DEBUG:'
        }

        prefix = prefijos.get(tipo, 'ℹ️ INFO:')
        log_msg = f"[{timestamp}] {prefix} {mensaje}"

        # Usar logging según el tipo
        if tipo == 'error':
            logging.error(log_msg)
        elif tipo == 'warning':
            logging.warning(log_msg)
        elif tipo == 'success':
            logging.info(log_msg)
        else:
            logging.info(log_msg)


# ====================================================================
# EJEMPLO DE USO
# ====================================================================

if __name__ == "__main__":
    # Ejemplo de uso standalone (para pruebas)
    from dotenv import load_dotenv
    import os

    load_dotenv()

    # Configuración
    postgresql_config = {
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD')
    }

    mysql_config = {
        'host': os.getenv('DB_HOST_MYSQL'),
        'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
        'user': os.getenv('DB_USER_MYSQL'),
        'password': os.getenv('DB_PASSWORD_MYSQL')
    }

    # Configuración de empresa (según logs)
    company_rif = 'J502741283'
    company_email = 'multiserviciosleblanc@gmail.com'
    company_id = 27  # ID de empresa en PostgreSQL

    # Crear app
    app = ServiceApp(postgresql_config, mysql_config, company_id)

    # Crear módulo de sync
    sync = SmartSyncComplete(app, postgresql_config, mysql_config, company_rif, company_email)

    # Inicializar tabla (primera vez)
    sync.inicializar_tabla_hashes()

    # Ejecutar sincronización
    sync.ejecutar_sync_completa()
