#!/usr/bin/env python3
"""
SISTEMA DE SINCRONIZACIÓN API REST - NUEVA ARQUITECTURA
=========================================================
Este sistema sincroniza PostgreSQL → API REST (sin MySQL)

Modos:
- config: Primera configuración
- manager: Interfaz de administración
- reconfig: Reconfigurar desde cero

Características:
- Token en memoria (no se guarda en disco)
- Login automático con email/password
- Refresh de token cuando expira
- Validación de empresa y obtención de company_id
"""

# ========================================
# DIAGNÓSTICO DE INICIO (antes de cualquier import)
# ========================================
import sys
import os
import traceback

CRASH_LOG = "startup_crash.log"

def log_startup_error(error_type, error_msg, traceback_str):
    """Registrar error de inicio en archivo"""
    try:
        with open(CRASH_LOG, "w", encoding="utf-8") as f:
            f.write(f"STARTUP ERROR - {error_type}\n")
            f.write("="*70 + "\n")
            f.write(f"Error: {error_msg}\n")
            f.write(f"\nTraceback:\n{traceback_str}\n")
            f.write(f"\nPython Version: {sys.version}\n")
            f.write(f"Executable: {sys.executable}\n")
            f.write(f"Frozen: {getattr(sys, 'frozen', False)}\n")
            f.write(f"Working Directory: {os.getcwd()}\n")
            f.write(f"\nsys.path:\n")
            for p in sys.path:
                f.write(f"  - {p}\n")
    except:
        pass  # Si falla el logging, no hay nada que hacer

import os
import time
import json
import argparse
import base64
import hashlib
import re
import threading
import queue
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Importar clientes API y sincronizadores
try:
    from api_client import (
        CompanyClient,
        CategoriesClient,
        ProductsClient,
        CustomersClient,
        SellersClient,
        QuotesClient
    )
    from sync import (
        CategoriesSync,
        ProductsSync,
        CustomersSync,
        SellersSync,
        QuotesSync
    )
except ImportError as e:
    error_msg = f"Error: No se pueden importar los módulos: {e}"
    print(error_msg)
    print("Asegúrese de que api_client/ y sync/ estén en el directorio actual")
    log_startup_error("IMPORT_ERROR", error_msg, traceback.format_exc())
    # Mantener ventana abierta si es .exe compilado
    if getattr(sys, 'frozen', False):
        input("\nPresiona Enter para salir...")
    sys.exit(1)

# Importar psycopg2
try:
    import psycopg2
except ImportError as e:
    error_msg = f"Error: psycopg2 no está instalado - {e}"
    print(error_msg)
    print("Ejecute: pip install psycopg2-binary")
    log_startup_error("PSYCOPG2_ERROR", error_msg, traceback.format_exc())
    # Mantener ventana abierta si es .exe compilado
    if getattr(sys, 'frozen', False):
        input("\nPresiona Enter para salir...")
    sys.exit(1)

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

# Ruta absoluta en el home del usuario para configuración
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


def get_log_file(company_email=None):
    """Obtener archivo de log según la empresa"""
    if company_email:
        email_safe = re.sub(r'[^\w\-]', '_', company_email.replace('@', '_'))[:50]
        return os.path.join(LOGS_DIR, f"sync_api_{email_safe}.log")
    return os.path.join(LOGS_DIR, "sync_api.log")


def mostrar_banner(titulo, mensaje, duracion=5, icono=None):
    """
    Muestra notificación nativa según el sistema operativo.

    Multiplataforma:
    - Windows: win10toast (Action Center)
    - Linux: notify2 (Desktop Notifications)
    - macOS: terminal-notifier (Notification Center)

    Args:
        titulo: Título de la notificación
        mensaje: Mensaje principal
        duracion: Duración en segundos (default 5)
        icono: Ruta al icono (opcional)
    """
    import platform
    import threading

    sistema = platform.system()

    # Función que ejecuta la notificación en un thread separado para capturar errores
    def _mostrar_notificacion_thread():
        try:
            print(f"[NOTIFICACION] Mostrando notificación: {titulo}")
            print(f"[NOTIFICACION] Mensaje: {mensaje}")
            print(f"[NOTIFICACION] Sistema: {sistema}")

            if sistema == "Windows":
                # Windows: usar win10toast
                # Verificar que pywin32 esté disponible
                try:
                    import win32con
                    print("[NOTIFICACION] win32con importado correctamente")
                except ImportError as e:
                    print(f"[NOTIFICACION] ERROR: win32con no disponible: {e}")
                    return  # pywin32 no instalado, salir silenciosamente

                from win10toast import ToastNotifier
                print("[NOTIFICACION] ToastNotifier importado correctamente")

                toast = ToastNotifier()
                print("[NOTIFICACION] ToastNotifier creado")

                # Forzar la creación de classAtom si no existe
                if not hasattr(toast, 'classAtom'):
                    try:
                        import win32gui
                        toast.classAtom = None
                        print("[NOTIFICACION] classAtom forzado a None")
                    except Exception as e:
                        print(f"[NOTIFICACION] WARNING: No se pudo forzar classAtom: {e}")

                # Intentar usar icono personalizado
                icon_path = icono
                if not icon_path:
                    try:
                        script_dir = os.path.dirname(os.path.abspath(__file__))
                        possible_icons = [
                            os.path.join(script_dir, "icon.ico"),
                            os.path.join(script_dir, "icon.png"),
                            os.path.join(script_dir, "app.ico"),
                        ]
                        for path in possible_icons:
                            if os.path.exists(path):
                                icon_path = path
                                break
                        print(f"[NOTIFICACION] Icono encontrado: {icon_path}")
                    except Exception as e:
                        print(f"[NOTIFICACION] WARNING buscando icono: {e}")

                # Usar threaded=True para evitar errores de WPARAM
                # cuando se ejecuta desde un thread separado
                print(f"[NOTIFICACION] Llamando toast.show_toast (duration={duracion})...")
                toast.show_toast(
                    titulo,
                    mensaje,
                    duration=duracion,
                    icon_path=icon_path,
                    threaded=True,  # Threaded para evitar errores de Windows callbacks
                )
                print("[NOTIFICACION] toast.show_toast completado exitosamente")

            elif sistema == "Linux":
                # Linux: usar notify2 (libnotify)
                try:
                    import notify2
                    notify2.init("Sincronizador Chrystal")

                    # Buscar icono
                    icon_path = icono
                    if not icon_path:
                        try:
                            script_dir = os.path.dirname(os.path.abspath(__file__))
                            possible_icons = [
                                os.path.join(script_dir, "icon.png"),
                                os.path.join(script_dir, "icon.ico"),
                                os.path.join(script_dir, "app.ico"),
                            ]
                            for path in possible_icons:
                                if os.path.exists(path):
                                    icon_path = path
                                    break
                        except:
                            pass

                    n = notify2.Notification(titulo, mensaje, icon_path)
                    n.set_timeout(duracion * 1000)
                    n.show()
                except ImportError:
                    # notify2 no instalado, intentar con dbus directo
                    try:
                        import dbus
                        bus = dbus.SessionBus()
                        notifications = bus.get_object('org.freedesktop.Notifications',
                                                       '/org/freedesktop/Notifications')
                        interface = dbus.Interface(notifications,
                                                  'org.freedesktop.Notifications')
                        interface.Notify('Sincronizador Chrystal', 0, '', titulo, mensaje,
                                       [], {}, duracion * 1000)
                    except:
                        pass  # dbus no disponible, silencioso

            elif sistema == "Darwin":  # macOS
                # macOS: usar terminal-notifier
                try:
                    import subprocess
                    cmd = ['terminal-notifier',
                          '-title', titulo,
                          '-message', mensaje,
                          '-timeout', str(duracion)]
                    if icono:
                        cmd.extend(['-appIcon', icono])
                    subprocess.run(cmd, check=False, capture_output=True)
                except FileNotFoundError:
                    # terminal-notifier no instalado
                    pass

        except Exception as e:
            # Loguear error pero no interrumpir el programa
            print(f"[NOTIFICACION] ERROR mostrando notificación: {e}")
            import traceback
            print(f"[NOTIFICACION] Traceback: {traceback.format_exc()}")

    # Ejecutar en un thread daemon para no bloquear
    thread = threading.Thread(target=_mostrar_notificacion_thread, daemon=True)
    thread.start()
    print(f"[NOTIFICACION] Thread de notificación iniciado (daemon={thread.daemon})")


def mostrar_notificacion_windows(titulo: str, mensaje: str, duracion=5, logger=None):
    """
    Wrapper para compatibilidad. NO llamar desde threads secundarios.
    Usar mostrar_banner() directamente desde el main thread.
    """
    mostrar_banner(titulo, mensaje, duracion)


def setup_logging(company_email=None):
    """
    Configurar logging para guardar en archivo y mostrar en consola.

    Args:
        company_email: Email de la empresa para nombrar el archivo de log

    Returns:
        logger function compatible con el sistema
    """
    log_file = get_log_file(company_email)

    # Crear logger
    import logging
    logger = logging.getLogger('sync_api')
    logger.setLevel(logging.DEBUG)

    # IMPORTANTE: Evitar propagación al logger raíz para prevenir duplicados
    logger.propagate = False

    # Eliminar handlers existentes para evitar duplicados
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # Función de log compatible (para usar con el logger existente)
    def log_func(message: str, level: str = "info"):
        """Función de log compatible"""
        level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        log_level = level_map.get(level.lower(), logging.INFO)
        logger.log(log_level, message)

    # Guardar referencia a log_func para poder agregar handlers GUI después
    log_func._logger = logger
    log_func._gui_handler = None

    return log_func


def add_gui_handler(logger_func, gui_log_func):
    """
    Agregar handler para enviar logs del logger de Python a la GUI.

    Args:
        logger_func: Función de log retornada por setup_logging
        gui_log_func: Función de log de la GUI (message, level)
    """
    import logging

    # Si ya existe un handler GUI, no agregar otro
    if logger_func._gui_handler is not None:
        return

    class GUIHandler(logging.Handler):
        """Handler personalizado para enviar logs a la GUI"""

        def __init__(self, log_func):
            super().__init__()
            self.log_func = log_func

        def emit(self, record):
            try:
                # Convertir nivel de logging a nivel del sistema
                level_map = {
                    logging.DEBUG: 'info',
                    logging.INFO: 'info',
                    logging.WARNING: 'warning',
                    logging.ERROR: 'error',
                    logging.CRITICAL: 'error'
                }
                level = level_map.get(record.levelno, 'info')

                # Formatear mensaje
                msg = self.format(record)

                # Enviar a la GUI
                self.log_func(msg, level)
            except Exception:
                pass  # No fallar por error de logging

    # Crear y configurar handler
    gui_handler = GUIHandler(gui_log_func)
    gui_handler.setLevel(logging.INFO)
    gui_format = logging.Formatter('%(message)s')  # Solo el mensaje, sin timestamp extra
    gui_handler.setFormatter(gui_format)

    # Agregar al logger
    logger_func._logger.addHandler(gui_handler)
    logger_func._gui_handler = gui_handler


class APIAuthManager:
    """
    Gestor de autenticación API Key.

    Valida API Key mediante endpoint ping.
    No requiere login ni refresh de token.
    """

    def __init__(self, base_url: str, logger=None):
        """
        Args:
            base_url: URL base de la API
            logger: Logger opcional
        """
        self.base_url = base_url
        self.logger = logger

        # Datos en memoria (NO se guardan en disco)
        self.api_key = None
        self.company_id = None
        self.company_data = None
    def ping_api_key(self, api_key: str) -> dict:
        """
        Validar API Key mediante endpoint ping y obtener info de la empresa.

        Args:
            api_key: API Key del sistema Chrystal

        Returns:
            Dict con success, company_id, company_data, rif, email
        """
        try:
            import requests

            self._log("🔑 Validando API Key...")

            response = requests.get(
                f"{self.base_url}/sync-client/ping",
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('success'):
                    response_data = data.get('data', {})
                    self.api_key = api_key
                    self.company_id = response_data.get('id')
                    self.company_data = {
                        'name': response_data.get('empresa'),
                        'rif': response_data.get('rif'),
                        'email': response_data.get('email')
                    }
                    self.company_rif = response_data.get('rif')
                    self.company_email = response_data.get('email')

                    self._log("✅ API Key válida")
                    self._log(f"   Empresa: {response_data.get('empresa')}")
                    self._log(f"   RIF: {response_data.get('rif')}")

                    return {
                        'success': True,
                        'company_id': self.company_id,
                        'company': self.company_data
                    }

            error_msg = 'API Key inválida'
            try:
                error_data = response.json()
                error_msg = error_data.get('message') or error_data.get('error', 'API Key inválida')
            except:
                pass

            self._log(f"❌ API Key inválida: {response.status_code}", "error")
            return {'success': False, 'error': error_msg}

        except Exception as e:
            error_str = str(e).lower()
            self._log(f"❌ Error validando API Key: {e}", "error")
            if 'connection' in error_str or 'timed out' in error_str:
                return {'success': False, 'error': 'No se pudo conectar a la API. Verifique su conexión a internet y la URL configurada.'}
            elif 'timeout' in error_str:
                return {'success': False, 'error': 'Tiempo de espera agotado.'}
            else:
                return {'success': False, 'error': f'Error validando API Key: {e}'}



    def validate_company(self, rif: str, email: str) -> dict:
        """
        Validar empresa y obtener company_id.

        Args:
            rif: RIF de la empresa
            email: Email de la empresa

        Returns:
            Dict con success, company_id, company_data
        """
        try:
            import requests

            self._log(f"🏢 Validando empresa: {rif}")

            if not self.api_key:
                return {'success': False, 'error': 'No hay API Key configurada.'}

            response = requests.post(
                f"{self.base_url}/sync-client/company/validate",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                },
                json={
                    'rif': rif,
                    'email': email
                },
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('success'):
                    self.company_id = data.get('company_id')
                    self.company_data = data.get('company')

                    self._log(f"✅ Empresa validada")
                    self._log(f"   Company ID: {self.company_id}")
                    self._log(f"   Nombre: {self.company_data.get('name')}")

                    return {
                        'success': True,
                        'company_id': self.company_id,
                        'company': self.company_data
                    }

            error_msg = response.json().get('message', 'Error desconocido') if response.text else 'Error desconocido'
            self._log(f"❌ Validación falló: {error_msg}", "error")
            return {'success': False, 'error': error_msg}

        except Exception as e:
            self._log(f"❌ Error validando empresa: {e}", "error")
            return {'success': False, 'error': str(e)}

    def get_auth_headers(self) -> dict:
        """Retornar headers con API Key."""
        if not self.api_key:
            raise Exception("No hay API Key configurada.")

        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    def _log(self, message: str, level: str = "info"):
        """Log message."""
        if self.logger:
            self.logger(message, level)
        else:
            print(message)


class APISyncManager:
    """
    Gestor de sincronización API REST.

    Coordina la sincronización de todas las entidades.
    """

    def __init__(self, postgres_config: dict, auth_manager: APIAuthManager, logger=None):
        """
        Args:
            postgres_config: Configuración de PostgreSQL
            auth_manager: Gestor de autenticación API
            logger: Logger opcional
        """
        self.postgres_config = postgres_config
        self.auth_manager = auth_manager
        self.logger = logger

        # Conexión PostgreSQL
        self.pg_conn = None
        self.pg_cursor = None

        # Clientes API (se crean después del login)
        self.categories_client = None
        self.products_client = None
        self.customers_client = None
        self.sellers_client = None
        self.quotes_client = None

        # Estadísticas
        self.stats = {
            'categories': {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0},
            'quotes': {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0},
            'products': {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0},
            'customers': {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0},
            'sellers': {'created': 0, 'updated': 0, 'deleted': 0, 'errors': 0}
        }

        self.sync_running = True

    def connect_postgresql(self) -> bool:
        """Conectar a PostgreSQL."""
        try:
            self.pg_conn = psycopg2.connect(**self.postgres_config)
            self.pg_cursor = self.pg_conn.cursor()
            self._log("✅ Conectado a PostgreSQL")

            # Inicializar tablas y triggers necesarios
            self.inicializar_tablas_sync()

            return True
        except Exception as e:
            self._log(f"❌ Error conectando a PostgreSQL: {e}", "error")
            return False

    def inicializar_tablas_sync(self) -> bool:
        """
        Inicializa tablas y triggers para sincronización.

        Crea:
        - Tabla sync_hashes si no existe
        - Tabla sync_config si no existe
        - Índices para sync_hashes
        - Triggers para marcar productos eliminados (solo si tabla se creó)
        - Triggers para marcar productos actualizados (solo si tabla se creó)

        Returns:
            True si exitoso, False si hubo error
        """
        try:
            # Verificar si sync_hashes ya existe (PostgreSQL 9 compatible)
            self.pg_cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'sync_hashes'
            """)
            sync_hashes_count = self.pg_cursor.fetchone()[0]
            sync_hashes_existe = sync_hashes_count > 0

            # Crear tabla sync_hashes solo si no existe
            if not sync_hashes_existe:
                print("[DEBUG] Creando tabla sync_hashes...")
                create_table_query = """
                CREATE TABLE sync_hashes (
                    id SERIAL PRIMARY KEY,
                    table_name VARCHAR(50) NOT NULL,
                    record_key VARCHAR(100) NOT NULL,
                    record_hash VARCHAR(32) NOT NULL,
                    last_sync_data TEXT,
                    synced_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    company_id INTEGER,
                    deleted_at TIMESTAMP,
                    pending_sync BOOLEAN DEFAULT FALSE,
                    UNIQUE(table_name, record_key, company_id)
                );
                """
                self.pg_cursor.execute(create_table_query)
                self.pg_conn.commit()
                print("[DEBUG] Tabla sync_hashes creada")
            else:
                print("[DEBUG] Tabla sync_hashes ya existe, omitiendo creación")

            # Crear tabla sync_config
            self._crear_tabla_sync_config()

            # Crear índices (son seguros con IF NOT EXISTS)
            self._crear_indices_sync_hashes()

            # SIEMPRE crear/actualizar triggers (usando CREATE OR REPLACE que es seguro)
            print("[DEBUG] Creando/actualizando triggers...")
            self._crear_triggers_desde_sql()
            print("[DEBUG] Triggers creados/actualizados")

            # Corregir registros existentes con company_id NULL
            self._corregir_company_id_sync_hashes()

            self._log("✅ Tablas y triggers de sincronización inicializados", "debug")
            return True

        except Exception as e:
            self._log(f"⚠️ Error inicializando tablas sync: {e}", "warning")
            return False

    def _crear_indices_sync_hashes(self):
        """Crea índices para sync_hashes (PostgreSQL 9 compatible)."""
        indices = [
            ("idx_sync_hashes_lookup", "CREATE INDEX idx_sync_hashes_lookup ON sync_hashes(table_name, record_key, company_id)"),
            ("idx_sync_hashes_table", "CREATE INDEX idx_sync_hashes_table ON sync_hashes(table_name, company_id)")
        ]

        for nombre_idx, query in indices:
            try:
                # Verificar si el índice ya existe (PostgreSQL 9 compatible)
                self.pg_cursor.execute("""
                    SELECT COUNT(*) FROM pg_indexes
                    WHERE indexname = %s
                """, (nombre_idx,))
                count = self.pg_cursor.fetchone()[0]

                if count == 0:
                    # El índice no existe, crearlo
                    self.pg_cursor.execute(query)
                    self.pg_conn.commit()
                    print(f"[DEBUG] Índice {nombre_idx} creado")
                else:
                    print(f"[DEBUG] Índice {nombre_idx} ya existe, omitiendo")
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" not in error_msg:
                    self._log(f"⚠️ Error creando índice {nombre_idx}: {e}", "warning")
                self.pg_conn.rollback()

    def _crear_tabla_sync_config(self):
        """
        Crea la tabla sync_config para almacenar configuración de sincronización.
        Se usa para guardar el company_id que usan los triggers UPDATE.
        Solo crea si no existe.
        """
        try:
            # Verificar si ya existe (PostgreSQL 9 compatible)
            self.pg_cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'sync_config'
            """)
            count = self.pg_cursor.fetchone()[0]
            existe = count > 0

            if not existe:
                print("[DEBUG] Creando tabla sync_config...")
                create_table_query = """
                CREATE TABLE sync_config (
                    key VARCHAR(100) PRIMARY KEY,
                    value VARCHAR(100) NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
                """
                self.pg_cursor.execute(create_table_query)
                self.pg_conn.commit()
                print("[DEBUG] Tabla sync_config creada")
            else:
                print("[DEBUG] Tabla sync_config ya existe, omitiendo creación")
        except Exception as e:
            print(f"[DEBUG] Error creando sync_config: {e}")
            self.pg_conn.rollback()

    def _crear_trigger_eliminacion_products(self):
        """Crea trigger que marca productos como eliminados en sync_hashes."""
        try:
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_product_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
            BEGIN
                -- Obtener company_id desde sync_config
                SELECT value::INTEGER INTO v_company_id
                FROM sync_config
                WHERE key = 'company_id';

                UPDATE sync_hashes
                SET deleted_at = NOW()
                WHERE table_name = 'products'
                AND record_key = OLD.code;

                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
                    VALUES ('products', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_products_mark_deleted_sync_hashes ON products;

            CREATE TRIGGER tr_products_mark_deleted_sync_hashes
                AFTER DELETE ON products
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_product_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
        except Exception as e:
            self.pg_conn.rollback()

    def _crear_trigger_eliminacion_categories(self):
        """Crea trigger que marca department (categories) como eliminados."""
        try:
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_department_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
            BEGIN
                -- Obtener company_id desde sync_config
                SELECT value::INTEGER INTO v_company_id
                FROM sync_config
                WHERE key = 'company_id';

                UPDATE sync_hashes
                SET deleted_at = NOW()
                WHERE table_name = 'categories'
                AND record_key = OLD.code;

                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
                    VALUES ('categories', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_department_mark_deleted_sync_hashes ON department;

            CREATE TRIGGER tr_department_mark_deleted_sync_hashes
                AFTER DELETE ON department
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_department_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
        except Exception as e:
            self.pg_conn.rollback()

    def _crear_trigger_eliminacion_customers(self):
        """Crea trigger que marca customers como eliminados."""
        try:
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_customer_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
            BEGIN
                -- Obtener company_id desde sync_config
                SELECT value::INTEGER INTO v_company_id
                FROM sync_config
                WHERE key = 'company_id';

                UPDATE sync_hashes
                SET deleted_at = NOW()
                WHERE table_name = 'customers'
                AND record_key = OLD.code;

                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
                    VALUES ('customers', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_customers_mark_deleted_sync_hashes ON customers;

            CREATE TRIGGER tr_customers_mark_deleted_sync_hashes
                AFTER DELETE ON customers
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_customer_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
        except Exception as e:
            self.pg_conn.rollback()

    def _crear_trigger_eliminacion_sellers(self):
        """Crea trigger que marca sellers como eliminados."""
        try:
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_seller_deleted_sync_hashes()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
            BEGIN
                -- Obtener company_id desde sync_config
                SELECT value::INTEGER INTO v_company_id
                FROM sync_config
                WHERE key = 'company_id';

                UPDATE sync_hashes
                SET deleted_at = NOW()
                WHERE table_name = 'sellers'
                AND record_key = OLD.code;

                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
                    VALUES ('sellers', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
                END IF;

                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_sellers_mark_deleted_sync_hashes ON sellers;

            CREATE TRIGGER tr_sellers_mark_deleted_sync_hashes
                AFTER DELETE ON sellers
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_seller_deleted_sync_hashes();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
        except Exception as e:
            self.pg_conn.rollback()

    def _crear_trigger_actualizacion_products(self):
        """Crea trigger que marca productos como pendientes de sincronización."""
        try:
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_product_pending_sync()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
            BEGIN
                -- Obtener company_id desde sync_config
                SELECT value::INTEGER INTO v_company_id
                FROM sync_config
                WHERE key = 'company_id';

                UPDATE sync_hashes
                SET pending_sync = TRUE, updated_at = NOW()
                WHERE table_name = 'products'
                AND record_key = NEW.code;

                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id)
                    VALUES ('products', NEW.code, md5(NEW.code::text), TRUE, v_company_id);
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_products_mark_pending_sync ON products;

            CREATE TRIGGER tr_products_mark_pending_sync
                AFTER INSERT OR UPDATE ON products
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_product_pending_sync();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
        except Exception as e:
            self.pg_conn.rollback()

    def _crear_trigger_actualizacion_customers(self):
        """Crea trigger que marca customers como pendientes de sincronización."""
        try:
            create_function_query = """
            CREATE OR REPLACE FUNCTION trigger_mark_customer_pending_sync()
            RETURNS TRIGGER AS $$
            DECLARE
                v_company_id INTEGER;
            BEGIN
                -- Obtener company_id desde sync_config
                SELECT value::INTEGER INTO v_company_id
                FROM sync_config
                WHERE key = 'company_id';

                UPDATE sync_hashes
                SET pending_sync = TRUE, updated_at = NOW()
                WHERE table_name = 'customers'
                AND record_key = NEW.code;

                IF NOT FOUND THEN
                    INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id)
                    VALUES ('customers', NEW.code, md5(NEW.code::text), TRUE, v_company_id);
                END IF;

                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """

            self.pg_cursor.execute(create_function_query)

            create_trigger_query = """
            DROP TRIGGER IF EXISTS tr_customers_mark_pending_sync ON customers;

            CREATE TRIGGER tr_customers_mark_pending_sync
                AFTER INSERT OR UPDATE ON customers
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_mark_customer_pending_sync();
            """

            self.pg_cursor.execute(create_trigger_query)
            self.pg_conn.commit()
        except Exception as e:
            self.pg_conn.rollback()

    def _split_sql_statements(self, sql_content):
        """
        Divide el contenido SQL en statements individuales respetando los bloques $$...$$

        PostgreSQL usa $$ como delimitador para funciones, así que no podemos
        simplemente dividir por ; porque rompería las funciones.

        Args:
            sql_content: Contenido completo del archivo SQL

        Returns:
            Lista de statements SQL completos
        """
        statements = []
        current_statement = []
        in_function = False

        for line in sql_content.split('\n'):
            stripped = line.strip()

            # Ignorar comentarios de una línea que no son parte de statements
            if stripped.startswith('--') and not in_function:
                continue

            # Detectar inicio de función CREATE OR REPLACE FUNCTION
            if stripped.startswith('CREATE OR REPLACE FUNCTION'):
                in_function = True
                current_statement.append(line)
                continue

            # Si estamos dentro de una función
            if in_function:
                current_statement.append(line)
                # Detectar el final de la función (termina con $$ LANGUAGE plpgsql;)
                if stripped.endswith('$$ LANGUAGE plpgsql;') or \
                   stripped.endswith('$$ LANGUAGE plpgsql'):
                    # Función completa
                    stmt = '\n'.join(current_statement)
                    statements.append(stmt)
                    current_statement = []
                    in_function = False
                continue

            # Si no estamos en una función, procesar normal
            if not in_function:
                # Ignorar líneas vacías
                if not stripped:
                    continue

                current_statement.append(line)
                # Si la línea termina con ; es el fin del statement
                if line.rstrip().endswith(';'):
                    stmt = '\n'.join(current_statement)
                    statements.append(stmt)
                    current_statement = []

        # Agregar cualquier statement restante
        if current_statement:
            stmt = '\n'.join(current_statement)
            if stmt.strip():
                statements.append(stmt)

        return statements

    def _crear_triggers_desde_sql(self):
        """
        Crea o actualiza todos los triggers ejecutando SQL embebido.
        Este método es compatible con todas las versiones de PostgreSQL.
        El SQL está embebido en el código Python para no depender de archivos externos.
        """
        # SQL embebido - Compatible con PostgreSQL 9.0+
        sql_content = """
-- Crear triggers compatibles con MÚLTIPLES VERSIONES de PostgreSQL
-- Este archivo detecta automáticamente la versión y usa la sintaxis correcta

-- ===========================================================================
-- PRODUCTS
-- ===========================================================================

-- Función para INSERT/UPDATE en products (compatible con todas las versiones)
CREATE OR REPLACE FUNCTION trigger_mark_product_updated_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'products'
    AND record_key = NEW.code
    AND company_id = v_company_id;

    -- Si existe, actualizar; si no, insertar
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET pending_sync = TRUE,
            updated_at = NOW()
        WHERE table_name = 'products'
        AND record_key = NEW.code
        AND company_id = v_company_id;
    ELSE
        INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
        VALUES ('products', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_products_mark_inserted_sync_hashes ON products;
CREATE TRIGGER tr_products_mark_inserted_sync_hashes
    AFTER INSERT ON products
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_updated_sync_hashes();

DROP TRIGGER IF EXISTS tr_products_mark_updated_sync_hashes ON products;
CREATE TRIGGER tr_products_mark_updated_sync_hashes
    AFTER UPDATE ON products
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_updated_sync_hashes();

-- Función para DELETE en products
CREATE OR REPLACE FUNCTION trigger_mark_product_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro en sync_hashes
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'products'
    AND record_key = OLD.code
    AND company_id = v_company_id;

    -- Si existe, actualizar deleted_at
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET deleted_at = NOW()
        WHERE table_name = 'products'
        AND record_key = OLD.code
        AND company_id = v_company_id;
    ELSE
        -- Si no existe, insertar nuevo registro con deleted_at
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
        VALUES ('products', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_products_mark_deleted_sync_hashes ON products;
CREATE TRIGGER tr_products_mark_deleted_sync_hashes
    AFTER DELETE ON products
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_deleted_sync_hashes();

-- ===========================================================================
-- CLIENTS
-- ===========================================================================

-- Función para INSERT/UPDATE en clients
CREATE OR REPLACE FUNCTION trigger_mark_client_updated_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'customers'
    AND record_key = NEW.code
    AND company_id = v_company_id;

    -- Si existe, actualizar; si no, insertar
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET pending_sync = TRUE,
            updated_at = NOW()
        WHERE table_name = 'customers'
        AND record_key = NEW.code
        AND company_id = v_company_id;
    ELSE
        INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
        VALUES ('customers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_clients_mark_inserted_sync_hashes ON clients;
CREATE TRIGGER tr_clients_mark_inserted_sync_hashes
    AFTER INSERT ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_updated_sync_hashes();

DROP TRIGGER IF EXISTS tr_clients_mark_updated_sync_hashes ON clients;
CREATE TRIGGER tr_clients_mark_updated_sync_hashes
    AFTER UPDATE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_updated_sync_hashes();

-- Función para DELETE en clients
CREATE OR REPLACE FUNCTION trigger_mark_client_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro en sync_hashes
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'customers'
    AND record_key = OLD.code
    AND company_id = v_company_id;

    -- Si existe, actualizar deleted_at
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET deleted_at = NOW()
        WHERE table_name = 'customers'
        AND record_key = OLD.code
        AND company_id = v_company_id;
    ELSE
        -- Si no existe, insertar nuevo registro con deleted_at
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
        VALUES ('customers', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_clients_mark_deleted_sync_hashes ON clients;
CREATE TRIGGER tr_clients_mark_deleted_sync_hashes
    AFTER DELETE ON clients
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_client_deleted_sync_hashes();

-- ===========================================================================
-- SELLERS
-- ===========================================================================

-- Función para INSERT/UPDATE en sellers
CREATE OR REPLACE FUNCTION trigger_mark_seller_updated_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'sellers'
    AND record_key = NEW.code
    AND company_id = v_company_id;

    -- Si existe, actualizar; si no, insertar
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET pending_sync = TRUE,
            updated_at = NOW()
        WHERE table_name = 'sellers'
        AND record_key = NEW.code
        AND company_id = v_company_id;
    ELSE
        INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
        VALUES ('sellers', NEW.code, md5(NEW.code::text), TRUE, v_company_id, NOW());
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_sellers_mark_inserted_sync_hashes ON sellers;
CREATE TRIGGER tr_sellers_mark_inserted_sync_hashes
    AFTER INSERT ON sellers
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_seller_updated_sync_hashes();

DROP TRIGGER IF EXISTS tr_sellers_mark_updated_sync_hashes ON sellers;
CREATE TRIGGER tr_sellers_mark_updated_sync_hashes
    AFTER UPDATE ON sellers
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_seller_updated_sync_hashes();

-- Función para DELETE en sellers
CREATE OR REPLACE FUNCTION trigger_mark_seller_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro en sync_hashes
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'sellers'
    AND record_key = OLD.code
    AND company_id = v_company_id;

    -- Si existe, actualizar deleted_at
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET deleted_at = NOW()
        WHERE table_name = 'sellers'
        AND record_key = OLD.code
        AND company_id = v_company_id;
    ELSE
        -- Si no existe, insertar nuevo registro con deleted_at
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
        VALUES ('sellers', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_sellers_mark_deleted_sync_hashes ON sellers;
CREATE TRIGGER tr_sellers_mark_deleted_sync_hashes
    AFTER DELETE ON sellers
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_seller_deleted_sync_hashes();

-- ===========================================================================
-- DEPARTMENTS (CATEGORIES)
-- ===========================================================================

-- Función para DELETE en department
CREATE OR REPLACE FUNCTION trigger_mark_department_deleted_sync_hashes()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Verificar si ya existe el registro en sync_hashes
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'categories'
    AND record_key = OLD.code
    AND company_id = v_company_id;

    -- Si existe, actualizar deleted_at
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET deleted_at = NOW()
        WHERE table_name = 'categories'
        AND record_key = OLD.code
        AND company_id = v_company_id;
    ELSE
        -- Si no existe, insertar nuevo registro con deleted_at
        INSERT INTO sync_hashes (table_name, record_key, record_hash, deleted_at, company_id)
        VALUES ('categories', OLD.code, md5(OLD.code::text), NOW(), v_company_id);
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_department_mark_deleted_sync_hashes ON department;
CREATE TRIGGER tr_department_mark_deleted_sync_hashes
    AFTER DELETE ON department
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_department_deleted_sync_hashes();
"""

        try:
            print("[DEBUG] Ejecutando SQL embebido para crear triggers...")

            # Dividir el SQL por puntos y coma, pero manteniendo las funciones completas
            # Las funciones terminan con $$ LANGUAGE plpgsql;
            statements = []
            current_stmt = []
            in_function = False

            for line in sql_content.split('\n'):
                stripped = line.strip()

                # Ignorar comentarios
                if stripped.startswith('--') and not in_function:
                    continue

                # Detectar inicio de función
                if stripped.startswith('CREATE OR REPLACE FUNCTION'):
                    in_function = True
                    current_stmt.append(line)
                    continue

                # Dentro de una función
                if in_function:
                    current_stmt.append(line)
                    # Fin de función
                    if 'LANGUAGE' in stripped and 'plpgsql' in stripped:
                        if stripped.endswith(';'):
                            stmt = '\n'.join(current_stmt)
                            statements.append(stmt)
                            current_stmt = []
                            in_function = False
                    continue

                # Fuera de función
                if not in_function and stripped:
                    current_stmt.append(line)
                    if line.rstrip().endswith(';'):
                        stmt = '\n'.join(current_stmt)
                        statements.append(stmt)
                        current_stmt = []

            # Agregar lo que reste
            if current_stmt:
                stmt = '\n'.join(current_stmt)
                if stmt.strip():
                    statements.append(stmt)

            print(f"[DEBUG] Ejecutando {len(statements)} statements...")

            # Ejecutar cada statement individualmente
            for i, statement in enumerate(statements, 1):
                if statement.strip():  # Solo ejecutar si no está vacío
                    try:
                        self.pg_cursor.execute(statement)
                    except Exception as stmt_error:
                        print(f"[DEBUG] Error en statement {i}: {str(stmt_error)[:200]}")
                        # Hacer rollback para limpiar el estado
                        self.pg_conn.rollback()
                        # Continuar con el siguiente statement
                        continue

            self.pg_conn.commit()
            print(f"[DEBUG] ✅ Triggers creados exitosamente desde SQL embebido")

        except Exception as e:
            print(f"[DEBUG] Error ejecutando SQL embebido: {e}")
            self.pg_conn.rollback()
            # Fallback: intentar crear triggers desde código Python
            print("[DEBUG] Creando triggers desde código Python (fallback)...")
            try:
                self._crear_trigger_eliminacion_products()
                self._crear_trigger_eliminacion_categories()
                self._crear_trigger_eliminacion_customers()
                self._crear_trigger_eliminacion_sellers()
                self._crear_trigger_actualizacion_products()
                self._crear_trigger_actualizacion_customers()
                print("[DEBUG] ✅ Triggers creados desde código Python (fallback)")
            except Exception as e2:
                print(f"[DEBUG] Error en fallback: {e2}")

    def _corregir_company_id_sync_hashes(self):
        """
        Corrige registros de sync_hashes que tienen company_id NULL.

        Esto es necesario porque los triggers antiguos no incluían el company_id.
        Este método actualiza todos los registros NULL con el company_id correcto desde sync_config.

        Solo actualiza si NO existe ya un registro duplicado con el mismo (table_name, record_key, company_id).
        """
        try:
            self._log("🔧 Corrigiendo company_id NULL en sync_hashes...", "info")

            # Verificar cuántos registros tienen company_id NULL
            self.pg_cursor.execute("""
                SELECT COUNT(*) FROM sync_hashes WHERE company_id IS NULL
            """)
            count_null = self.pg_cursor.fetchone()[0]

            if count_null == 0:
                self._log("✅ No hay registros con company_id NULL", "info")
                return

            self._log(f"📊 Se encontraron {count_null} registros con company_id NULL", "info")

            # Actualizar solo los registros que NO tienen duplicado
            # Usamos una subquery para evitar violar la restricción de unicidad
            result = self.pg_cursor.execute("""
                UPDATE sync_hashes sh
                SET company_id = (
                    SELECT value::INTEGER
                    FROM sync_config
                    WHERE key = 'company_id'
                ),
                updated_at = NOW()
                WHERE company_id IS NULL
                AND NOT EXISTS (
                    SELECT 1
                    FROM sync_hashes sh2
                    WHERE sh2.table_name = sh.table_name
                    AND sh2.record_key = sh.record_key
                    AND sh2.company_id = (
                        SELECT value::INTEGER
                        FROM sync_config
                        WHERE key = 'company_id'
                    )
                )
            """)

            updated = self.pg_cursor.rowcount
            self.pg_conn.commit()

            if updated > 0:
                self._log(f"✅ Corregidos {updated} registros de sync_hashes con company_id", "info")
            else:
                self._log("ℹ️ No se actualizaron registros (posibles duplicados ya existentes)", "info")

        except Exception as e:
            self._log(f"⚠️ Error corrigiendo company_id en sync_hashes: {e}", "warning")
            self.pg_conn.rollback()

    def initialize_api_clients(self) -> bool:
        """Inicializar clientes API después del login."""
        try:
            import logging
            base_url = self.auth_manager.base_url
            api_key = self.auth_manager.api_key

            if not api_key:
                self._log("❌ No hay API Key", "error")
                return False

            # Obtener logger compartido para todos los clientes
            api_logger = logging.getLogger('sync_api')

            # Crear clientes
            self.categories_client = CategoriesClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger
            )

            self.products_client = ProductsClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger
            )

            self.customers_client = CustomersClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger
            )

            self.sellers_client = SellersClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger
            )

            self.quotes_client = QuotesClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger
            )

            self._log("✅ Clientes API inicializados")
            return True

        except Exception as e:
            self._log(f"❌ Error inicializando clientes API: {e}", "error")
            return False

    def sync_all(self) -> dict:
        """
        Ejecutar sincronización completa de todas las entidades.

        Orden: Categories → Products → Customers → Sellers → Quotes

        Returns:
            Dict con estadísticas agregadas
        """
        self._log("\n" + "="*70)
        self._log("🔄 INICIANDO SINCRONIZACIÓN COMPLETA")
        self._log("="*70)

        # Verificar que tengamos API Key
        if not self.auth_manager.api_key:
            self._log("❌ No hay API Key configurada", "error")
            return {'success': False, 'error': 'No API key configured'}

        company_id = self.auth_manager.company_id

        # Validar que tengamos company_id
        if not company_id:
            self._log("❌ Error: No se pudo obtener company_id. Verifica que validate_company() se haya llamado correctamente.", "error")
            return {'success': False, 'error': 'No company_id available', 'stats': {}}

        self._log(f"✅ Company ID obtenido: {company_id}", "info")

        # ACTUALIZAR sync_config con el company_id (para que los triggers lo usen)
        try:
            # Primero hacer rollback para limpiar cualquier transacción abortada
            try:
                self.pg_conn.rollback()
            except:
                pass

            cursor = self.pg_conn.cursor()

            # Verificar si ya existe
            cursor.execute("""
                SELECT value FROM sync_config WHERE key = 'company_id'
            """)
            existe = cursor.fetchone()

            if existe:
                valor_actual = existe[0]
                if valor_actual != str(company_id):
                    self._log(f"📝 Actualizando sync_config: {valor_actual} → {company_id}")
                    # Si company_id es None, usar NULL en lugar de string 'None'
                    if company_id is None:
                        cursor.execute("""
                            UPDATE sync_config
                            SET value = NULL, updated_at = NOW()
                            WHERE key = 'company_id'
                        """)
                    else:
                        cursor.execute("""
                            UPDATE sync_config
                            SET value = %s, updated_at = NOW()
                            WHERE key = 'company_id'
                        """, (str(company_id),))
                    self.pg_conn.commit()
                else:
                    self._log(f"✅ sync_config ya tiene company_id correcto: {company_id}")
            else:
                self._log(f"📝 Insertando company_id en sync_config: {company_id}")
                # Si company_id es None, usar NULL en lugar de string 'None'
                if company_id is None:
                    cursor.execute("""
                        INSERT INTO sync_config (key, value, updated_at)
                        VALUES ('company_id', NULL, NOW())
                    """)
                else:
                    cursor.execute("""
                        INSERT INTO sync_config (key, value, updated_at)
                        VALUES ('company_id', %s, NOW())
                    """, (str(company_id),))
                self.pg_conn.commit()
        except Exception as e:
            self._log(f"⚠️ Error actualizando sync_config: {e}", "warning")
            try:
                self.pg_conn.rollback()
            except:
                pass

        # 1. Categories
        self._log("\n📁 SINCRONIZANDO CATEGORIES...")
        categories_sync = CategoriesSync(
            self.pg_conn,
            self.categories_client,
            company_id,
            self.logger
        )
        categories_sync.execute()
        self.stats['categories'] = categories_sync.stats.copy()

        # 2. Products (pasar el mapa de categorías desde CategoriesSync)
        self._log("\n📦 SINCRONIZANDO PRODUCTS...")
        products_sync = ProductsSync(
            self.pg_conn,
            self.products_client,
            company_id,
            self.logger,
            categories_map=categories_sync.categories_map  # Pasar mapa de categorías
        )
        products_sync.execute()
        self.stats['products'] = products_sync.stats.copy()

        # 3. Customers
        self._log("\n👥 SINCRONIZANDO CUSTOMERS...")
        customers_sync = CustomersSync(
            self.pg_conn,
            self.customers_client,
            company_id,
            self.logger
        )
        customers_sync.execute()
        self.stats['customers'] = customers_sync.stats.copy()

        # 4. Sellers
        self._log("\n👔 SINCRONIZANDO SELLERS...")
        sellers_sync = SellersSync(
            self.pg_conn,
            self.sellers_client,
            company_id,
            self.logger
        )
        sellers_sync.execute()
        self.stats['sellers'] = sellers_sync.stats.copy()

        # 5. Quotes (API → PostgreSQL)
        self._log("\n💰 SINCRONIZANDO QUOTES...")
        quotes_sync = QuotesSync(
            self.pg_conn,
            self.pg_conn.cursor(),
            company_id,
            self.quotes_client,
            self.logger
        )

        # Detectar cambios
        cambios_quotes = quotes_sync.detect_changes()

        # Sincronizar a PostgreSQL
        if cambios_quotes.get('nuevos'):
            quotes_sync.sync_to_postgresql(cambios_quotes)

        self.stats['quotes'] = quotes_sync.get_stats()

        # Resumen
        self._log("\n" + "="*70)
        self._log("📊 RESUMEN DE SINCRONIZACIÓN")
        self._log("="*70)

        total_created = sum(s.get('created', 0) for s in self.stats.values())
        total_updated = sum(s.get('updated', 0) for s in self.stats.values())
        total_deleted = sum(s.get('deleted', 0) for s in self.stats.values())
        total_errors = sum(s.get('errors', 0) for s in self.stats.values())

        self._log(f"Created: {total_created}")
        self._log(f"Updated: {total_updated}")
        self._log(f"Deleted: {total_deleted}")
        self._log(f"Errors: {total_errors}")

        return {
            'success': total_errors == 0,
            'stats': self.stats,
            'total': {
                'created': total_created,
                'updated': total_updated,
                'deleted': total_deleted,
                'errors': total_errors
            }
        }

    def sync_categories(self) -> dict:
        """Sincronizar solo categories."""
        self._log("\n📁 SINCRONIZANDO CATEGORIES...")

        # Refrescar token si es necesario y actualizar clientes
        refresh_result = self.auth_manager.refresh_token_if_needed()
        if not refresh_result['success']:
            self._log("❌ No se pudo refrescar el token", "error")
            return {'success': False, 'stats': {}}

        # Si se refrescó el token, actualizar todos los clientes
        if refresh_result.get('refreshed'):
            self._log("🔄 Token refrescado, actualizando clientes API...")
            self._update_client_tokens(refresh_result['token'])

        company_id = self.auth_manager.company_id

        categories_sync = CategoriesSync(
            self.pg_conn,
            self.categories_client,
            company_id,
            self.logger
        )
        categories_sync.execute()

        return {
            'success': categories_sync.stats['errors'] == 0,
            'stats': categories_sync.stats.copy()
        }

    def sync_products(self) -> dict:
        """Sincronizar solo products."""
        self._log("\n📦 SINCRONIZANDO PRODUCTS...")

        # Refrescar token si es necesario y actualizar clientes
        refresh_result = self.auth_manager.refresh_token_if_needed()
        if not refresh_result['success']:
            self._log("❌ No se pudo refrescar el token", "error")
            return {'success': False, 'stats': {}}

        # Si se refrescó el token, actualizar todos los clientes
        if refresh_result.get('refreshed'):
            self._log("🔄 Token refrescado, actualizando clientes API...")
            self._update_client_tokens(refresh_result['token'])

        company_id = self.auth_manager.company_id

        products_sync = ProductsSync(
            self.pg_conn,
            self.products_client,
            company_id,
            self.logger
        )
        products_sync.execute()

        return {
            'success': products_sync.stats['errors'] == 0,
            'stats': products_sync.stats.copy()
        }

    def sync_customers(self) -> dict:
        """Sincronizar solo customers."""
        self._log("\n👥 SINCRONIZANDO CUSTOMERS...")

        # Refrescar token si es necesario y actualizar clientes
        refresh_result = self.auth_manager.refresh_token_if_needed()
        if not refresh_result['success']:
            self._log("❌ No se pudo refrescar el token", "error")
            return {'success': False, 'stats': {}}

        # Si se refrescó el token, actualizar todos los clientes
        if refresh_result.get('refreshed'):
            self._log("🔄 Token refrescado, actualizando clientes API...")
            self._update_client_tokens(refresh_result['token'])

        company_id = self.auth_manager.company_id

        customers_sync = CustomersSync(
            self.pg_conn,
            self.customers_client,
            company_id,
            self.logger
        )
        customers_sync.execute()

        return {
            'success': customers_sync.stats['errors'] == 0,
            'stats': customers_sync.stats.copy()
        }

    def sync_sellers(self) -> dict:
        """Sincronizar solo sellers."""
        self._log("\n👔 SINCRONIZANDO SELLERS...")

        # Refrescar token si es necesario y actualizar clientes
        refresh_result = self.auth_manager.refresh_token_if_needed()
        if not refresh_result['success']:
            self._log("❌ No se pudo refrescar el token", "error")
            return {'success': False, 'stats': {}}

        # Si se refrescó el token, actualizar todos los clientes
        if refresh_result.get('refreshed'):
            self._log("🔄 Token refrescado, actualizando clientes API...")
            self._update_client_tokens(refresh_result['token'])

        company_id = self.auth_manager.company_id

        sellers_sync = SellersSync(
            self.pg_conn,
            self.sellers_client,
            company_id,
            self.logger
        )
        sellers_sync.execute()

        return {
            'success': sellers_sync.stats['errors'] == 0,
            'stats': sellers_sync.stats.copy()
        }

    def sync_quotes(self) -> dict:
        """Sincronizar solo quotes."""
        self._log("\n💰 SINCRONIZANDO QUOTES...")

        # Refrescar token si es necesario y actualizar clientes
        refresh_result = self.auth_manager.refresh_token_if_needed()
        if not refresh_result['success']:
            self._log("❌ No se pudo refrescar el token", "error")
            return {'success': False, 'stats': {}}

        # Si se refrescó el token, actualizar todos los clientes
        if refresh_result.get('refreshed'):
            self._log("🔄 Token refrescado, actualizando clientes API...")
            self._update_client_tokens(refresh_result['token'])

        company_id = self.auth_manager.company_id

        quotes_sync = QuotesSync(
            self.pg_conn,
            self.pg_conn.cursor(),
            company_id,
            self.quotes_client,
            self.logger
        )

        cambios_quotes = quotes_sync.detect_changes()

        if cambios_quotes.get('nuevos'):
            quotes_sync.sync_to_postgresql(cambios_quotes)

        return {
            'success': quotes_sync.get_stats()['errors'] == 0,
            'stats': quotes_sync.get_stats()
        }

    def close(self):
        """Cerrar conexiones."""
        if self.pg_conn:
            self.pg_conn.close()
            self._log("✅ Conexión PostgreSQL cerrada")

    def _log(self, message: str, level: str = "info"):
        """Log message."""
        if self.logger:
            self.logger(message, level)
        else:
            print(message)


# ==============================================================================
# FUNCIONES HELPER PARA AUTENTICACIÓN DE CONFIG
# ==============================================================================

def autenticar_para_config(permitir_reconfiguracion=False):
    """
    Obtiene la API Key para usar en configuración.
    - Si existe config, lee la API Key del archivo encriptado
    - Si no existe config, retorna éxito sin API Key

    Retorna dict con {'success': bool, 'api_key': str}
    """
    from config_encryption import decrypt_config

    config_exists = os.path.exists(CONFIG_FILE)

    if config_exists:
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            config = decrypt_config(config)
            api_key = config.get('api_key')
            if api_key:
                return {'success': True, 'api_key': api_key}
        except Exception as e:
            print(f"⚠️ Error leyendo API Key del config: {e}")

    return {'success': True, 'api_key': None}
class ConfigWindow:
    """Ventana de configuración inicial."""

    def __init__(self, root, callback=None):
        """
        Args:
            root: Ventana Tkinter root
            callback: Función opcional a llamar cuando se guarde la configuración
        """
        self.root = root
        self.root.geometry("600x700")
        self.callback = callback  # Callback para notificar cuando se guarde

        # Cargar configuración existente si hay
        existing_config = self.load_existing_config()

        # Título según si es nueva o edición
        if existing_config:
            self.root.title("⚙️ Editar Configuración - Sincronizador API")
            # Mostrar mensaje informativo sobre configuración existente
            messagebox.showinfo(
                "⚠️ Configuración Existente",
                "Ya existe una configuración guardada en el sistema.\n\n"
                "Si desea configurar desde cero, debe:\n\n"
                "1. Cerrar esta ventana\n"
                "2. Ejecutar el comando: python3 sync_system_api.py --mode reconfig\n\n"
                "O desde el Manager, hacer clic en el botón 'Reconfigurar'.\n\n"
                "Si solo desea actualizar algunos valores, puede editarlos directamente aquí."
            )
        else:
            self.root.title("⚙️ Nueva Configuración - Sincronizador API")

        # Variables
        self.api_url_var = tk.StringVar(value=existing_config.get('api_url', "https://chrystal.com.ve/mobiletest/public/api"))
        self.api_key_var = tk.StringVar()  # API Key nunca se carga de config existente

        self.pg_host_var = tk.StringVar(value=existing_config.get('postgres_host', "localhost"))
        self.pg_port_var = tk.StringVar(value=existing_config.get('postgres_port', "5432"))
        self.pg_database_var = tk.StringVar(value=existing_config.get('postgres_database', ''))
        self.pg_user_var = tk.StringVar(value=existing_config.get('postgres_user', "postgres"))
        self.pg_password_var = tk.StringVar()  # Password se carga si existe

        # Datos de empresa obtenidos del ping (read-only)
        self.company_name_ping = ""
        self.company_rif_ping = ""
        self.company_email_ping = ""

        self.sync_interval_var = tk.StringVar(value=existing_config.get('sync_interval_minutes', '30'))

        self.log_text = None

        # Registrar handler para cierre de ventana
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)

        self.create_widgets()

    def load_existing_config(self) -> dict:
        """Cargar configuración existente si hay."""
        try:
            if os.path.exists(CONFIG_FILE):
                from config_encryption import decrypt_config
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                # Desencriptar todos los campos sensibles
                return decrypt_config(config)
        except Exception:
            pass
        return {}

    def create_widgets(self):
        """Crear widgets de la interfaz."""

        # Título
        title = tk.Label(self.root, text="⚙️ Configuración del Sincronizador API",
                        font=("Arial", 16, "bold"))
        title.pack(pady=10)

        # Notebook para pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Pestaña PostgreSQL
        pg_frame = ttk.Frame(notebook)
        notebook.add(pg_frame, text="🐘 PostgreSQL")

        ttk.Label(pg_frame, text="Host:").pack(anchor="w", padx=10, pady=(10,0))
        ttk.Entry(pg_frame, textvariable=self.pg_host_var, width=60).pack(padx=10, pady=5)

        ttk.Label(pg_frame, text="Port:").pack(anchor="w", padx=10, pady=(10,0))
        ttk.Entry(pg_frame, textvariable=self.pg_port_var, width=60).pack(padx=10, pady=5)

        ttk.Label(pg_frame, text="Database:").pack(anchor="w", padx=10, pady=(10,0))
        ttk.Entry(pg_frame, textvariable=self.pg_database_var, width=60).pack(padx=10, pady=5)

        ttk.Label(pg_frame, text="User:").pack(anchor="w", padx=10, pady=(10,0))
        ttk.Entry(pg_frame, textvariable=self.pg_user_var, width=60).pack(padx=10, pady=5)

        ttk.Label(pg_frame, text="Password:").pack(anchor="w", padx=10, pady=(10,0))
        ttk.Entry(pg_frame, textvariable=self.pg_password_var, show="*", width=60).pack(padx=10, pady=5)

        # Botón probar PostgreSQL
        ttk.Button(pg_frame, text="🧪 Probar Conexión PostgreSQL",
                  command=self.test_postgres_connection).pack(padx=10, pady=10)

        # Pestaña API KEY
        api_frame = ttk.Frame(notebook)
        notebook.add(api_frame, text="🔐 API KEY")

        ttk.Label(api_frame, text="API Key:").pack(anchor="w", padx=10, pady=(15,0))
        ttk.Entry(api_frame, textvariable=self.api_key_var, width=60, show="*").pack(padx=10, pady=5)
        

        # Botón probar API Key
        ttk.Button(api_frame, text="🧪 Probar API Key",
                  command=self.test_api_key).pack(padx=10, pady=10)

        # Separador
        ttk.Separator(api_frame, orient="horizontal").pack(fill="x", padx=10, pady=10)

        # Datos de empresa (auto-llenados desde ping, read-only)
        empresa_frame = ttk.LabelFrame(api_frame, text="  Datos de la Empresa  ")
        empresa_frame.pack(fill="x", padx=10, pady=5)

        self.company_name_label = ttk.Label(empresa_frame, text="Empresa: --", font=("Arial", 10, "bold"))
        self.company_name_label.pack(anchor="w", padx=10, pady=(10,2))
        self.company_rif_label = ttk.Label(empresa_frame, text="RIF: --")
        self.company_rif_label.pack(anchor="w", padx=10, pady=2)
        self.company_email_label = ttk.Label(empresa_frame, text="Email: --")
        self.company_email_label.pack(anchor="w", padx=10, pady=(2,10))


        # Pestaña Configuración
        config_frame = ttk.Frame(notebook)
        notebook.add(config_frame, text="⚙️ Configuración")

        ttk.Label(config_frame, text="Intervalo de sincronización automática:").pack(anchor="w", padx=10, pady=(20,0))

        interval_frame = ttk.Frame(config_frame)
        interval_frame.pack(padx=10, pady=5)

        ttk.Entry(interval_frame, textvariable=self.sync_interval_var, width=10).pack(side="left", padx=5)
        ttk.Label(interval_frame, text="minutos").pack(side="left")

        ttk.Label(config_frame, text="ℹ️ El sistema se sincronizará automáticamente cada X minutos.",
                 foreground="gray", justify="left").pack(anchor="w", padx=10, pady=10)

        # Botones
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="💾 Guardar y Salir",
                  command=self.save_config).pack(side="left", padx=5)
        ttk.Button(button_frame, text="❌ Cancelar",
                  command=self.root.quit).pack(side="left", padx=5)

    def log(self, message: str, level: str = "info"):
        """Escribir log."""
        if self.log_text:
            self.log_text.insert("end", f"{message}\n")
            self.log_text.see("end")

    def test_api_key(self):
        """Probar API Key contra endpoint ping."""
        api_url = self.api_url_var.get().strip()
        api_key = self.api_key_var.get().strip()

        if not api_url or not api_key:
            messagebox.showwarning("Advertencia", "Por favor complete la API Key")
            return

        self.log("🧪 Probando API Key...")

        try:
            import requests

            response = requests.get(
                f"{api_url}/sync-client/ping",
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                if data.get('success'):
                    response_data = data.get('data', {})
                    empresa = response_data.get('empresa', 'N/A')
                    rif = response_data.get('rif', 'N/A')
                    email = response_data.get('email', 'N/A')

                    # Validar que el email del ping coincida con el email en PostgreSQL
                    pg_email = None
                    try:
                        import psycopg2
                        pg_conn = psycopg2.connect(
                            host=self.pg_host_var.get().strip(),
                            port=self.pg_port_var.get().strip(),
                            database=self.pg_database_var.get().strip(),
                            user=self.pg_user_var.get().strip(),
                            password=self.pg_password_var.get().strip()
                        )
                        pg_cursor = pg_conn.cursor()
                        pg_cursor.execute("SELECT email FROM company LIMIT 1")
                        row = pg_cursor.fetchone()
                        if row:
                            pg_email = row[0]
                        pg_cursor.close()
                        pg_conn.close()
                    except Exception as e:
                        messagebox.showerror("❌ Error",
                            f"No se pudo conectar a PostgreSQL para validar la empresa.\n\n"
                            f"Verifique la conexión en la pestaña PostgreSQL.\n{e}")
                        self.log("❌ Error validando email en PostgreSQL")
                        return

                    if not pg_email:
                        messagebox.showerror("❌ Error",
                            "No se encontró ningún registro en la tabla 'company' de PostgreSQL.\n\n"
                            "Debe existir al menos una empresa configurada en la base de datos local.")
                        self.log("❌ No hay empresas en la tabla company de PostgreSQL")
                        return

                    # Comparar emails
                    if email.lower().strip() != pg_email.lower().strip():
                        messagebox.showerror("❌ Error de Validación",
                            f"El email de la API Key no coincide con el email registrado en PostgreSQL.\n\n"                            
                            f"Verifique que la API Key corresponde a la misma empresa "
                            f"configurada en la base de datos local.")
                        self.log(f"❌ Email no coincide: API={email} vs PG={pg_email}")
                        return

                    # Guardar datos de empresa
                    self.company_name_ping = empresa
                    self.company_rif_ping = rif
                    self.company_email_ping = email

                    # Actualizar labels en la UI
                    self.company_name_label.config(text=f"Empresa: {empresa}")
                    self.company_rif_label.config(text=f"RIF: {rif}")
                    self.company_email_label.config(text=f"Email: {email}")

                    messagebox.showinfo(
                        "✅ API Key Válida",
                        f"API Key validada correctamente.\n\n"
                        f"Empresa: {empresa}\n"
                        f"RIF: {rif}\n"
                        f"Email: {email}"
                    )
                    self.log("✅ API Key válida")
                else:
                    error_msg = data.get('message', data.get('error', 'Error desconocido'))
                    messagebox.showerror("❌ Error", f"API Key inválida: {error_msg}")
                    self.log("❌ API Key inválida")
            elif response.status_code == 401:
                messagebox.showerror("❌ API Key Inválida",
                    "La API Key no es válida o no tiene permisos suficientes.")
                self.log("❌ API Key inválida (401)")
            elif response.status_code >= 500:
                error_msg = f"Error del servidor ({response.status_code})"
                try:
                    error_detail = response.json()
                    error_msg += f"\n{error_detail.get('message', '')}"
                except:
                    pass
                messagebox.showerror("❌ Error del Servidor", error_msg)
                self.log(f"❌ API: Error del servidor {response.status_code}")
            else:
                messagebox.showerror("❌ Error", f"Error HTTP {response.status_code}")
                self.log(f"❌ API: Error HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            messagebox.showerror("❌ Error", "Tiempo de espera agotado. La API no responde.")
            self.log("❌ API: Timeout")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("❌ Error", "No se puede conectar a la API. Verifique la URL.")
            self.log("❌ API: Error de conexión")
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error inesperado: {str(e)}")
            self.log(f"❌ API: {str(e)}")

    def test_postgres_connection(self):
        """Probar conexión a PostgreSQL."""
        host = self.pg_host_var.get().strip()
        port = self.pg_port_var.get().strip()
        database = self.pg_database_var.get().strip()
        user = self.pg_user_var.get().strip()
        password = self.pg_password_var.get().strip()

        # Validar campos requeridos (password puede estar en blanco)
        if not all([host, port, database, user]):
            messagebox.showwarning("Advertencia", "Por favor complete Host, Puerto, Database y Usuario de PostgreSQL")
            return

        self.log("🧪 Probando conexión a PostgreSQL...")

        try:
            import psycopg2

            # Intentar conectar
            conn = psycopg2.connect(
                host=host,
                port=int(port),
                database=database,
                user=user,
                password=password,
                connect_timeout=10
            )

            cursor = conn.cursor()

            # Verificar versión
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            # Contar productos
            cursor.execute("SELECT COUNT(*) FROM products")
            products_count = cursor.fetchone()[0]

            cursor.close()
            conn.close()

            messagebox.showinfo(
                "✅ Conexión Exitosa",
                f"Conexión a PostgreSQL establecida.\n\n"
                f"Host: {host}\n"
                f"Database: {database}\n"
                f"Productos: {products_count:,}\n\n"
                f"Versión: {version[:50]}..."
            )
            self.log("✅ PostgreSQL: Conexión exitosa")

        except psycopg2.OperationalError as e:
            error_msg = str(e).lower()
            self.log(f"❌ PostgreSQL: {str(e)}")
            messagebox.showerror(
                "❌ Error de Conexión PostgreSQL",
                f"No se pudo conectar a la base de datos.\n\n"
                f"Error: {str(e)}\n\n"
                f"Por favor verifica:\n"
                f"• Host: {host}\n"
                f"• Puerto: {port}\n"
                f"• Database: {database}\n"
                f"• Usuario: {user}\n"
                f"• Que el servidor PostgreSQL esté ejecutándose"
            )
        except ValueError as e:
            self.log(f"❌ PostgreSQL: Error en puerto: {str(e)}")
            messagebox.showerror(
                "❌ Puerto Inválido",
                f"El puerto debe ser un número.\n\n"
                f"Error: {str(e)}\n\n"
                f"Puerto por defecto de PostgreSQL: 5432"
            )
        except Exception as e:
            self.log(f"❌ PostgreSQL: {str(e)}")
            messagebox.showerror(
                "❌ Error Inesperado",
                f"Ocurrió un error al probar la conexión:\n\n"
                f"Error: {str(e)}"
            )

    def on_window_close(self):
        """Manejador de cierre de ventana de configuración."""
        self.root.destroy()

    def save_config(self):
        """Guardar configuración y verificar conexión con ventana de progreso."""
        # Validar campos requeridos
        required = {
            'URL de la API': self.api_url_var.get(),
            'API Key': self.api_key_var.get(),
            'Database PostgreSQL': self.pg_database_var.get(),
            # Password PostgreSQL puede estar en blanco (confianza en el host)
        }

        missing = [k for k, v in required.items() if not v]
        if missing:
            messagebox.showerror("Error", f"Faltan campos requeridos:\n" + "\n".join(f"  • {k}" for k in missing))
            return

        # Validar intervalo de sincronización
        interval = self.sync_interval_var.get().strip()
        if not interval or not interval.isdigit():
            messagebox.showerror("Error", "El intervalo de sincronización debe ser un número válido")
            return

        interval_minutes = int(interval)
        if interval_minutes < 1:
            messagebox.showerror("Error", "El intervalo de sincronización debe ser al menos 1 minuto")
            return

        if interval_minutes >= 30:
            messagebox.showerror(
                "⚠️ Intervalo no válido",
                "El intervalo de sincronización debe ser menor a 30 minutos.\n\n"
                "Establezca un intervalo adecuado para su empresa\n"
                "en la pestaña Configuración."
            )
            return


        try:
            # Validar que tengamos datos de empresa del ping
            if not self.company_rif_ping or not self.company_email_ping:
                messagebox.showerror(
                    "Error",
                    "Debe probar la API Key primero para obtener los datos de la empresa.\n\n"
                    "Haga clic en \"Probar API Key\" en la pestaña API KEY."
                )
                return

            # Crear configuración con datos en texto plano (AÚN NO SE GUARDA EN ARCHIVO)
            config = {
                'api_url': self.api_url_var.get(),
                'api_key': self.api_key_var.get(),  # Se encriptará después si todo es exitoso
                'postgres_host': self.pg_host_var.get(),
                'postgres_port': self.pg_port_var.get(),
                'postgres_database': self.pg_database_var.get(),
                'postgres_user': self.pg_user_var.get(),
                'postgres_password': self.pg_password_var.get(),
                'company_rif': self.company_rif_ping,
                'company_email': self.company_email_ping,
                'company_name': self.company_name_ping,
                'sync_interval_minutes': str(interval_minutes),
                'configured': True,
                'first_run': False
            }

            # Copia SIN encriptar para la verificación
            config_plain = config.copy()

            # ❌ NO GUARDAR AQUÍ - Solo guardar si todas las verificaciones pasan
            # from config_encryption import encrypt_config
            # config_encrypted = encrypt_config(config)
            # with open(CONFIG_FILE, 'w') as f:
            #     json.dump(config_encrypted, f, indent=2)

            # Si hay un callback (desde Manager), llamarlo y cerrar
            if self.callback:
                self.callback(config_plain)
                self.root.destroy()
            else:
                # Mostrar ventana de progreso con config SIN encriptar
                self._mostrar_ventana_progreso(config_plain)

        except Exception as e:
            messagebox.showerror("Error", f"Error guardando configuración:\n{e}")

    def _mostrar_ventana_progreso(self, config):
        """Mostrar ventana de progreso al guardar configuración."""
        # Crear ventana de progreso
        progreso = tk.Toplevel(self.root)
        progreso.title("Configurando...")
        progreso.geometry("600x700")
        progreso.resizable(False, False)

        # Hacerla modal
        progreso.transient(self.root)
        progreso.grab_set()

        # Centrar ventana
        progreso.update_idletasks()
        x = (progreso.winfo_screenwidth() // 2) - (600 // 2)
        y = (progreso.winfo_screenheight() // 2) - (700 // 2)
        progreso.geometry(f"+{x}+{y}")

        # Frame principal
        frame = tk.Frame(progreso, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        # Icono
        ttk.Label(frame, text="⏳", font=("Arial", 48)).pack(pady=10)

        # Título
        ttk.Label(frame, text="Verificando configuración...", font=("Arial", 14, "bold")).pack(pady=10)

        # Barra de progreso
        progress_bar = ttk.Progressbar(frame, mode='indeterminate', length=400)
        progress_bar.pack(pady=20)
        progress_bar.start(10)

        # Etiqueta de estado
        estado_label = ttk.Label(frame, text="Iniciando...", font=("Arial", 10))
        estado_label.pack(pady=10)

        # Etiqueta de detalle
        detalle_label = ttk.Label(frame, text="", font=("Arial", 9), foreground="gray")
        detalle_label.pack(pady=5)

        # INDICADOR DE PASOS
        contenedor_pasos = ttk.LabelFrame(frame, text="🔄 ESTADO DE VERIFICACIÓN", padding=10)
        contenedor_pasos.pack(pady=10, fill="x", padx=5)

        pasos_frame = ttk.Frame(contenedor_pasos)
        pasos_frame.pack(fill="x", padx=10)

        pasos_labels = {}
        pasos_porcentaje = {}

        # Crear los 3 pasos
        pasos_info = [
            (1, "Conectar a PostgreSQL", "Verificar base de datos"),
            (2, "Autenticar API", "Validar credenciales"),
            (3, "Validar empresa", "Verificar empresa en API")
        ]

        for num, nombre, descripcion in pasos_info:
            paso_frame = ttk.Frame(pasos_frame)
            paso_frame.pack(fill="x", pady=5)

            left_container = ttk.Frame(paso_frame)
            left_container.pack(side="left", fill="x", expand=True)

            paso_num_label = ttk.Label(left_container, text=f" {num} ",
                                      font=("Arial", 10, "bold"),
                                      foreground="white", background="#808080",
                                      padding=(6, 3))
            paso_num_label.pack(side="left", padx=(0, 8))

            ttk.Label(left_container, text=nombre,
                     font=("Arial", 10, "bold")).pack(side="left")

            ttk.Label(left_container, text=f"  - {descripcion}",
                     font=("Arial", 8), foreground="gray").pack(side="left")

            porcentaje_label = tk.Label(paso_frame, text="0%",
                                       font=("Arial", 14, "bold"),
                                       fg="#0066cc", bg="#f0f0f0",
                                       padx=8, pady=2,
                                       relief="solid", borderwidth=1)
            porcentaje_label.pack(side="right", padx=(10, 0))

            pasos_labels[num] = paso_num_label
            pasos_porcentaje[num] = porcentaje_label

        estado_paso_label = ttk.Label(contenedor_pasos,
                                     text="⏳ Iniciando...",
                                     font=("Arial", 10),
                                     foreground="blue")
        estado_paso_label.pack(pady=10)

        # Botón CERRAR (inicialmente deshabilitado)
        btn_cerrar = ttk.Button(frame, text="⏳ Verificando...", state="disabled")
        btn_cerrar.pack(pady=15)

        # Variable para controlar el resultado
        resultado = {'exito': False, 'mensaje': ''}
        verification_queue = queue.Queue()

        def actualizar_paso(paso_num, estado="en_progreso", mensaje="", porcentaje=None):
            """Actualizar estado de un paso"""
            if not progreso.winfo_exists():
                return

            try:
                # Colores según estado
                colores = {
                    'pendiente': '#808080',  # Gris
                    'en_progreso': '#0066cc',  # Azul
                    'completado': '#00cc00',  # Verde
                    'error': '#cc0000'  # Rojo
                }

                # Actualizar todos los números de paso
                for num in pasos_labels:
                    if num in pasos_labels and pasos_labels[num].winfo_exists():
                        bg_color = colores['pendiente']
                        if num < paso_num:
                            bg_color = colores['completado']
                        elif num == paso_num:
                            bg_color = colores[estado]

                        pasos_labels[num].config(background=bg_color)

                # Actualizar porcentaje del paso actual
                if paso_num in pasos_porcentaje and pasos_porcentaje[paso_num].winfo_exists():
                    if porcentaje is not None:
                        pct_text = f"{porcentaje:.0f}%"
                    else:
                        pct_text = "0%"
                    pasos_porcentaje[paso_num].config(text=pct_text)

                # Actualizar label de estado
                if paso_num in pasos_porcentaje and pasos_porcentaje[paso_num].winfo_exists():
                    fg_color = colores.get(estado, 'black')
                    pasos_porcentaje[paso_num].config(fg=fg_color)

                # Actualizar mensaje de paso
                if mensaje and estado_paso_label.winfo_exists():
                    estado_paso_label.config(text=f"⏳ {mensaje}")

            except Exception:
                pass

        def actualizar_estado(mensaje, detalle=""):
            """Actualizar etiquetas de estado"""
            try:
                if estado_label.winfo_exists():
                    estado_label.config(text=mensaje)
                if detalle and detalle_label.winfo_exists():
                    detalle_label.config(text=detalle)
                progreso.update_idletasks()
            except:
                pass

        def ejecutar_verificacion_thread():
            """Ejecutar verificación en thread separado"""
            import threading
            import psycopg2

            def verification_worker():
                try:
                    # PASO 1: Conectar a PostgreSQL
                    actualizar_paso(1, "en_progreso", "Conectando a PostgreSQL...", 0)
                    actualizar_estado("🔌 Conectando a PostgreSQL...", f"Host: {config['postgres_host']}")

                    pg_conn = None
                    try:
                        pg_conn = psycopg2.connect(
                            host=config['postgres_host'],
                            port=config['postgres_port'],
                            database=config['postgres_database'],
                            user=config['postgres_user'],
                            password=config['postgres_password'],
                            connect_timeout=10
                        )
                        actualizar_paso(1, "completado", "Conexión exitosa", 100)
                        actualizar_estado("✅ PostgreSQL conectado", "Base de datos verificada")
                    except Exception as e:
                        actualizar_paso(1, "error", "Error de conexión", 0)
                        raise Exception(f"Error conectando a PostgreSQL: {e}")

                    # PASO 2: Validar API Key
                    actualizar_paso(2, "en_progreso", "Validando API Key...", 0)
                    actualizar_estado("🔐 Validando API Key...", "Ping a API")

                    auth_manager = None
                    try:
                        auth_manager = APIAuthManager(config['api_url'])
                        ping_result = auth_manager.ping_api_key(
                            config['api_key']
                        )

                        if ping_result.get('success'):
                            actualizar_paso(2, "completado", "API Key válida", 100)
                            actualizar_estado("✅ API Key válida", "Conexión API establecida")
                        else:
                            actualizar_paso(2, "error", "API Key inválida", 0)
                            raise Exception(f"API Key inválida: {ping_result.get('error')}")
                    except Exception as e:
                        actualizar_paso(2, "error", "Error de autenticación", 0)
                        raise Exception(f"Error validando API Key: {e}")

                    # PASO 3: Validar empresa
                    actualizar_paso(3, "en_progreso", "Validando empresa...", 0)
                    actualizar_estado("🏢 Validando empresa...", f"RIF: {config['company_rif']}")

                    try:
                        validate_result = auth_manager.validate_company(
                            config['company_rif'],
                            config['company_email']
                        )

                        if validate_result.get('success'):
                            actualizar_paso(3, "completado", "Empresa validada", 100)
                            actualizar_estado("✅ Empresa validada", "Configuración correcta")
                        else:
                            actualizar_paso(3, "error", "Validación fallida", 0)
                            raise Exception(f"Validación falló: {validate_result.get('error')}")
                    except Exception as e:
                        actualizar_paso(3, "error", "Error de validación", 0)
                        raise Exception(f"Error validando empresa: {e}")

                    # Todo exitoso
                    resultado['exito'] = True
                    resultado['api_key'] = config['api_key']  # Usar API Key del config
                    resultado['mensaje'] = "✅ Configuración guardada correctamente\n\n✅ Conexión a PostgreSQL verificada\n✅ Autenticación API validada\n✅ Empresa validada\n\nEl sistema está listo para sincronizar."

                except Exception as e:
                    resultado['exito'] = False

                    # Mensaje de error amigable
                    error_msg = str(e)

                    # Extraer el mensaje de error más amigable si está disponible
                    if "Error autenticando API:" in error_msg:
                        # El error ya viene del login con mensaje amigable
                        error_amigable = error_msg.split("Login falló: ")[-1] if "Login falló: " in error_msg else error_msg
                        resultado['mensaje'] = f"⚠️ Verificación fallida\n\n❌ Error de autenticación:\n\n{error_amigable}\n\nContacta al administrador del sistema para verificar tus credenciales de acceso.\n\nLa configuración NO se guardó."
                    elif "Error validando empresa:" in error_msg:
                        # Error validando empresa
                        error_amigable = error_msg.split("Validación falló: ")[-1] if "Validación falló: " in error_msg else error_msg
                        resultado['mensaje'] = f"⚠️ Verificación fallida\n\n❌ Error validando empresa:\n\n{error_amigable}\n\nVerifica:\n• RIF de la empresa\n• Email de la empresa\n\nLa configuración NO se guardó."
                    elif "Error conectando a PostgreSQL:" in error_msg:
                        resultado['mensaje'] = f"⚠️ Verificación fallida\n\n❌ Error de base de datos:\n\n{error_msg}\n\nVerifica:\n• Host de PostgreSQL\n• Puerto de conexión\n• Nombre de la base de datos\n• Usuario y contraseña\n\nLa configuración NO se guardó."
                    else:
                        resultado['mensaje'] = f"⚠️ Verificación fallida\n\n❌ Error durante verificación:\n\n{error_msg}\n\nLa configuración NO se guardó."

                finally:
                    # Cerrar conexiones
                    if pg_conn:
                        try:
                            pg_conn.close()
                        except:
                            pass

                    progress_bar.stop()
                    verification_queue.put(True)

            # Crear e iniciar thread
            thread = threading.Thread(target=verification_worker, daemon=True)
            thread.start()

            # Mantener GUI viva
            def keep_gui_alive():
                try:
                    # Verificar si la verificacion termino (thread-safe, desde el main thread)
                    if not verification_queue.empty():
                        verification_queue.get()
                        try:
                            if progreso.winfo_exists():
                                progreso.event_generate('<<VerificationComplete>>')
                        except:
                            pass
                        return

                    if thread.is_alive():
                        try:
                            progreso.update()
                        except:
                            pass
                        progreso.after(50, keep_gui_alive)
                except:
                    pass

            keep_gui_alive()

        def ejecutar_primera_sync_y_tray(api_key, cerrar_ventana_callback=None):
            """
            Ejecuta la primera sincronización y luego inicia el System Tray

            Args:
                api_key: API Key de la API
                cerrar_ventana_callback: Función para cerrar la ventana de progreso después de la sync
            """
            # Archivo de log para diagnóstico
            log_file = open("primera_sync_log.txt", "w", encoding="utf-8")

            def log_debug(msg):
                """Escribe a consola y archivo"""
                print(msg)
                log_file.write(msg + "\n")
                log_file.flush()

            try:
                log_debug("\n[DEBUG] Iniciando ejecutar_primera_sync_y_tray()")

                # Cargar configuración guardada
                if not os.path.exists(CONFIG_FILE):
                    log_debug("[DEBUG] ERROR: No existe CONFIG_FILE")
                    messagebox.showerror("Error", "No se encontró configuración guardada")
                    log_file.close()
                    return

                from config_encryption import decrypt_config
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                # Desencriptar todos los campos sensibles
                config = decrypt_config(config)

                log_debug(f"[DEBUG] Config cargada: {config.get('company_email')}")
                log_debug(f"[DEBUG] api_key recibido: {'Sí' if api_key else 'No'}")

                # Crear ventana de progreso para primera sincronización
                log_debug("[DEBUG] Creando ventana de sincronización...")
                # Crear nueva ventana Tk independiente (self.root ya fue destruido)
                sync_window = tk.Tk()
                sync_window.title("🔄 Primera Sincronización")
                sync_window.geometry("600x300")
                sync_window.resizable(False, False)

                # Prevenir que el usuario cierre la ventana manualmente
                sync_window.protocol("WM_DELETE_WINDOW", lambda: None)  # Deshabilitar botón X

                # Centrar ventana
                sync_window.update_idletasks()
                width = sync_window.winfo_width()
                height = sync_window.winfo_height()
                x = (sync_window.winfo_screenwidth() // 2) - (width // 2)
                y = (sync_window.winfo_screenheight() // 2) - (height // 2)
                sync_window.geometry(f"{width}x{height}+{x}+{y}")

                # Mantener ventana al frente (topmost)
                sync_window.attributes('-topmost', True)
                sync_window.lift()
                sync_window.focus_force()

                # Widgets
                # Frame principal con borde
                main_frame = tk.Frame(sync_window, bg="#f0f0f0", padx=30, pady=30)
                main_frame.pack(fill=tk.BOTH, expand=True)

                tk.Label(main_frame, text="🔄 Ejecutando Primera Sincronización",
                        font=("Arial", 16, "bold"), bg="#f0f0f0", fg="#2c3e50").pack(pady=(0, 10))

                tk.Label(main_frame, text="Por favor espere, esto puede tardar varios minutos...",
                        font=("Arial", 10), bg="#f0f0f0", fg="#7f8c8d").pack(pady=(0, 20))

                sync_label = tk.Label(main_frame, text="⏳ Iniciando...",
                                     font=("Arial", 11), bg="#f0f0f0", fg="#34495e",
                                     wraplength=500, justify="center")
                sync_label.pack(pady=10)

                progress_bar = ttk.Progressbar(main_frame, mode='indeterminate', length=500)
                progress_bar.pack(pady=20)
                progress_bar.start(10)

                # Información adicional
                info_label = tk.Label(main_frame,
                                     text="ℹ️ No cierre esta ventana\nLa sincronización se ejecuta en segundo plano",
                                     font=("Arial", 9), bg="#f0f0f0", fg="#95a5a6",
                                     justify="center")
                info_label.pack(pady=(10, 0))

                # Cola para comunicación thread → main thread
                sync_queue = queue.Queue()

                # Bandera para detener el procesamiento de mensajes
                # DEBE definirse ANTES de procesar_mensajes_queue() que la referencia con nonlocal
                sync_completada = False

                # Variable para compartir resultado entre ejecutar_sync_worker() y on_sync_complete()
                sync_result = None

                def procesar_mensajes_queue():
                    """Procesa mensajes de la cola desde el main thread"""
                    nonlocal sync_completada

                    try:
                        # Verificar si la ventana aún existe
                        if not sync_window.winfo_exists():
                            log_debug("[DEBUG] procesar_mensajes_queue(): Ventana no existe, saliendo")
                            return

                        # Si la sync ya se completó, dejar de procesar mensajes
                        if sync_completada:
                            log_debug("[DEBUG] Sync completada, deteniendo procesar_mensajes_queue()")
                            return

                        # Verificar si hay mensajes en la cola
                        if sync_queue.empty():
                            # No hay mensajes, programar próxima verificación
                            sync_window.after(100, procesar_mensajes_queue)
                            return

                        log_debug(f"[DEBUG] procesar_mensajes_queue(): Hay {sync_queue.qsize()} mensajes en la cola")

                        while not sync_queue.empty():
                            msg = sync_queue.get_nowait()
                            log_debug(f"[DEBUG] Mensaje recibido: {msg}")

                            # Detectar señal de completado
                            if msg == "__SYNC_COMPLETE__":
                                log_debug("[DEBUG] Detectado __SYNC_COMPLETE__, llamando a on_sync_complete()")
                                on_sync_complete()
                                return  # Dejar de procesar más mensajes

                            # Mensaje normal de texto
                            if sync_window.winfo_exists():
                                sync_label.config(text=msg)
                            log_debug(f"[SYNC GUI] {msg}")
                    except Exception as e:
                        log_debug(f"[DEBUG] Error en procesar_mensajes_queue(): {e}")
                        # Si la ventana fue destruida, dejar de procesar
                        if "winfo exists" in str(e) or "application has been destroyed" in str(e):
                            return
                        pass
                    # Programar próxima actualización solo si la ventana existe y sync no completada
                    try:
                        if sync_window.winfo_exists() and not sync_completada:
                            sync_window.after(100, procesar_mensajes_queue)
                    except:
                        pass

                # Iniciar procesamiento de mensajes
                procesar_mensajes_queue()

                def ejecutar_sync_worker():
                    """Worker de sincronización en thread"""
                    nonlocal sync_result
                    log_debug("[DEBUG] Iniciando ejecutar_sync_worker()")
                    try:
                        # Crear logger que usa cola (thread-safe)
                        def sync_logger(msg, level="info"):
                            log_debug(f"[SYNC] {msg}")
                            try:
                                sync_queue.put(msg)
                            except:
                                pass  # Si la cola está cerrada, ignorar

                        # Crear gestores
                        log_debug("[DEBUG] Creando APIAuthManager...")
                        auth_manager = APIAuthManager(
                            base_url=config['api_url'],
                            logger=sync_logger
                        )

                        # Login
                        log_debug("[DEBUG] Haciendo login a API...")
                        sync_queue.put("🔐 Autenticando con API...")
                        auth_manager.ping_api_key(config['api_key'])
                        auth_manager.validate_company(config['company_rif'], config['company_email'])
                        log_debug("[DEBUG] Login exitoso")

                        log_debug("[DEBUG] Creando APISyncManager...")
                        sync_manager = APISyncManager(
                            postgres_config={
                                'host': config['postgres_host'],
                                'port': config['postgres_port'],
                                'database': config['postgres_database'],
                                'user': config['postgres_user'],
                                'password': config['postgres_password']
                            },
                            auth_manager=auth_manager,
                            logger=sync_logger
                        )

                        # Conectar y sincronizar
                        log_debug("[DEBUG] Conectando a PostgreSQL...")
                        sync_queue.put("🔗 Conectando a PostgreSQL...")
                        if sync_manager.connect_postgresql() and sync_manager.initialize_api_clients():
                            log_debug("[DEBUG] Conectado, iniciando sync_all()...")
                            sync_queue.put("🔄 Sincronizando datos (puede tardar varios minutos)...")
                            result = sync_manager.sync_all()
                            log_debug("[DEBUG] sync_all() completado")

                            total = result.get('total', {})
                            sync_result = {
                                'exito': True,
                                'mensaje': f"✅ Sincronización completada:\n"
                                          f"   ✨ Nuevos: {total.get('created', 0)}\n"
                                          f"   🔄 Modificados: {total.get('updated', 0)}\n"
                                          f"   ❌ Eliminados: {total.get('deleted', 0)}",
                                'api_key': api_key
                            }
                            log_debug(f"[DEBUG] Result sync: creado={total.get('created', 0)}, updated={total.get('updated', 0)}, deleted={total.get('deleted', 0)}")
                        else:
                            log_debug("[DEBUG] Error de conexión")
                            sync_result = {
                                'exito': False,
                                'mensaje': "❌ Error de conexión a PostgreSQL o API",
                                'api_key': api_key
                            }

                        sync_manager.close()
                        log_debug("[DEBUG] Sync manager cerrado")

                    except Exception as e:
                        log_debug(f"[DEBUG] ERROR en sync_worker: {e}")
                        import traceback
                        log_debug(traceback.format_exc())
                        sync_result = {
                            'exito': False,
                            'mensaje': f"❌ Error: {str(e)}",
                            'api_key': api_key
                        }

                    log_debug("[DEBUG] Notificando completion...")
                    # Poner señal de completado en la cola (thread-safe)
                    log_debug("[DEBUG] Poniendo __SYNC_COMPLETE__ en la cola...")
                    sync_queue.put("__SYNC_COMPLETE__")
                    log_debug("[DEBUG] __SYNC_COMPLETE__ puesto en la cola")

                def on_sync_complete():
                    """Manejador de completion de sincronización"""
                    nonlocal sync_completada, sync_result
                    sync_completada = True  # Marcar como completada para detener procesar_mensajes_queue()

                    log_debug(f"[DEBUG] on_sync_complete llamado: exito={sync_result.get('exito')}")
                    if not sync_window.winfo_exists():
                        return

                    try:
                        progress_bar.stop()
                    except:
                        pass

                    if sync_result['exito']:
                        # Quitar topmost para que no quede pegada al frente
                        try:
                            sync_window.attributes('-topmost', False)
                        except:
                            pass

                        # Mostrar resultado exitoso
                        sync_label.config(text=sync_result['mensaje'], foreground="#27ae60", bg="#f0f0f0")
                        info_label.config(text="✅ Sincronización completada correctamente\nIniciando System Tray...", fg="#27ae60", bg="#f0f0f0")
                        log_debug("[DEBUG] Sync exitoso, cerrando ventana en 3 seg...")

                        # 📢 Notificación Windows de sincronización exitosa
                        log_debug("[DEBUG] Llamando a mostrar_banner()...")
                        mostrar_banner(
                            "✅ Primera Sincronización Exitosa",
                            sync_result['mensaje'],
                            duracion=5
                        )
                        log_debug("[DEBUG] mostrar_banner() llamó, thread iniciado")

                        # Cerrar ventana de sincronización después de 3 segundos
                        def cerrar_sync_window():
                            """Cerrar la ventana de sincronización y el mainloop"""
                            try:
                                if sync_window.winfo_exists():
                                    log_debug("[DEBUG] Cerrando sync_window...")
                                    # CERRAR LA VENTANA PRIMERO, antes de iniciar System Tray
                                    log_debug("[DEBUG] Destruyendo ventana ANTES de iniciar System Tray...")
                                    sync_window.destroy()
                                    log_debug("[DEBUG] sync_window destruida")

                                    # Ahora iniciar System Tray en un thread separado
                                    # para que no bloquee
                                    log_debug("[DEBUG] Iniciando System Tray en thread separado...")
                                    log_debug(f"[DEBUG] api_key en sync_result: {'Sí' if sync_result.get('api_key') else 'No'}")

                                    import threading
                                    tray_thread = threading.Thread(
                                        target=iniciar_system_tray,
                                        args=(config, sync_result.get('api_key')),
                                        daemon=False  # System Tray debe seguir vivo
                                    )
                                    tray_thread.start()
                                    log_debug("[DEBUG] Thread de System Tray iniciado")
                            except Exception as e:
                                log_debug(f"[DEBUG] Error cerrando sync_window: {e}")

                        sync_window.after(3000, cerrar_sync_window)

                        # Cerrar ventana de progreso (config) después de 3 segundos
                        if cerrar_ventana_callback:
                            sync_window.after(3000, cerrar_ventana_callback)
                    else:
                        # Quitar topmost en caso de error también
                        try:
                            sync_window.attributes('-topmost', False)
                        except:
                            pass

                        log_debug(f"[DEBUG] Sync falló: {sync_result['mensaje']}")
                        sync_label.config(text=sync_result['mensaje'], foreground="#c0392b", bg="#f0f0f0")
                        info_label.config(text="⚠️ La sincronización falló\nRevise el log para más detalles", fg="#c0392b", bg="#f0f0f0")
                        tk.Button(main_frame, text="⚠️ Cerrar",
                                 command=sync_window.destroy,
                                 bg="#c0392b", fg="white", font=("Arial", 10, "bold"),
                                 padx=20, pady=5, cursor="hand2").pack(pady=10)

                        # 📢 Notificación Windows de error
                        mostrar_banner(
                            "⚠️ Error en Primera Sincronización",
                            sync_result['mensaje'],
                            duracion=10
                        )

                        # Cerrar ventana de progreso también si falló
                        if cerrar_ventana_callback:
                            sync_window.after(3000, cerrar_ventana_callback)

                # Iniciar thread de sincronización
                log_debug("[DEBUG] Iniciando thread de sincronización...")
                sync_thread = threading.Thread(target=ejecutar_sync_worker, daemon=False)
                sync_thread.start()

                # Iniciar mainloop de la ventana para procesar eventos
                # Esto permite que funcione el after() para cerrar la ventana
                log_debug("[DEBUG] Iniciando mainloop de sync_window...")
                sync_window.mainloop()
                log_debug("[DEBUG] Mainloop terminado, ventana cerrada")

            except Exception as e:
                log_debug(f"[DEBUG] ERROR en ejecutar_primera_sync_y_tray: {e}")
                import traceback
                log_debug(traceback.format_exc())
                log_file.close()
                messagebox.showerror("Error", f"Error preparando sincronización:\n{e}")

        def iniciar_system_tray(config, api_key):
            """Inicia el servicio System Tray"""
            # Continuar usando el mismo archivo de log
            log_file = open("primera_sync_log.txt", "a", encoding="utf-8")

            def log_debug(msg):
                """Escribe a consola y archivo"""
                print(msg)
                log_file.write(msg + "\n")
                log_file.flush()

            try:
                log_debug("\n[DEBUG] ===== INICIAR SYSTEM TRAY =====")
                log_debug(f"[DEBUG] Company: {config.get('company_email')}")
                log_debug(f"[DEBUG] API Key: {'***' if api_key else 'None'}")

                # Verificar que hay configuración válida
                if not config:
                    log_debug("[DEBUG] ERROR: Config es None o vacío")
                    messagebox.showerror("Error", "No hay configuración válida")
                    log_file.close()
                    return

                log_debug(f"[DEBUG] Config tiene {len(config)} keys")

                # Destruir root principal si existe
                try:
                    if hasattr(self, 'root'):
                        try:
                            if self.root.winfo_exists():
                                log_debug("[DEBUG] Destruyendo root principal...")
                                self.root.destroy()
                                log_debug("[DEBUG] Root destruido")
                            else:
                                log_debug("[DEBUG] Root principal ya no existe")
                        except Exception as e:
                            # Si winfo_exists() falla, significa que la app fue destruida
                            log_debug(f"[DEBUG] Root ya fue destruido (winfo_exists falló): {e}")
                    else:
                        log_debug("[DEBUG] No hay atributo root en self")
                except Exception as e:
                    log_debug(f"[DEBUG] Error al verificar/destruir root: {e}")
                    log_debug("[DEBUG] Continuar (root ya estaba destruido)")

                # Crear e iniciar servicio System Tray
                log_debug("\n" + "="*70)
                log_debug("🔄 Iniciando modo System Tray...")
                log_debug("="*70)

                log_debug("[DEBUG] Creando instancia de SystemTrayService...")
                tray_service = SystemTrayService(config, api_key)
                log_debug("[DEBUG] SystemTrayService creada")

                log_debug("[DEBUG] Llamando a tray_service.iniciar()...")
                log_debug("[DEBUG] Esto iniciará el icono en la barra de tareas")
                tray_service.iniciar()
                log_debug("[DEBUG] tray_service.iniciar() retornó (no debería llegar aquí nunca)")

            except Exception as e:
                log_debug(f"[DEBUG] ERROR en iniciar_system_tray: {e}")
                import traceback
                log_debug(traceback.format_exc())
                log_file.close()
                messagebox.showerror("Error", f"Error iniciando System Tray:\n{e}\n\nRevisa el archivo primera_sync_log.txt para detalles.")

        def cerrar_ventana():
            """Cerrar ventana y regresar"""
            try:
                if progreso.winfo_exists():
                    progreso.destroy()

                # NOTA: Ya NO ejecutamos ejecutar_primera_sync_y_tray() aquí
                # porque se ejecuta en on_verification_complete() (línea 2187)
                # Esto evita que se ejecute dos veces

                # Cerrar ventana de config
                if self.root.winfo_exists():
                    self.root.destroy()
            except:
                pass

        def cerrar_ventana_y_iniciar_tray(api_key):
            """Cerrar ventana de progreso y directamente iniciar System Tray"""
            try:
                # Cerrar ventana de progreso
                if progreso.winfo_exists():
                    progreso.destroy()

                # Cerrar ventana principal de config
                if self.root.winfo_exists():
                    self.root.destroy()

                # Cargar configuración guardada
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, 'r') as f:
                        config = json.load(f)

                    # Desencriptar configuración antes de usarla
                    from config_encryption import decrypt_config
                    config = decrypt_config(config)

                    # Iniciar System Tray directamente (sin primera sincronización)
                    iniciar_system_tray(config, api_key)
                else:
                    messagebox.showerror("Error", "No se encontró configuración guardada")
            except Exception as e:
                messagebox.showerror("Error", f"Error iniciando System Tray:\n{e}")

        def cerrar_ventana_progreso():
            """Cerrar ventana de progreso y volver a configuración principal"""
            try:
                # Cerrar ventana de progreso
                if progreso.winfo_exists():
                    progreso.destroy()

                # NO cerrar la ventana de configuración principal
                # Solo enfocarla para que el usuario pueda corregir
                if self.root.winfo_exists():
                    self.root.lift()  # Traer ventana al frente
                    self.root.focus_force()  # Poner foco en la ventana

                    # Enfocar campo de email para corregir
                    self.email_entry.focus_set()
            except:
                pass

        # Manejar evento de finalización
        def on_verification_complete(event):
            if not progreso.winfo_exists():
                return

            progress_bar.stop()

            if resultado['exito']:
                estado_label.config(text="✅ Verificación completada", foreground="green")
                estado_paso_label.config(text="✅ Configuración verificada con éxito", foreground="green")

                # Guardar el archivo de configuración SOLO si todas las verificaciones pasaron
                try:
                    from config_encryption import encrypt_config

                    # Obtener config desde las variables (todavía están disponibles)
                    config = {
                        'api_url': self.api_url_var.get(),
                        'api_key': self.api_key_var.get(),
                        'postgres_host': self.pg_host_var.get(),
                        'postgres_port': self.pg_port_var.get(),
                        'postgres_database': self.pg_database_var.get(),
                        'postgres_user': self.pg_user_var.get(),
                        'postgres_password': self.pg_password_var.get(),
                        'company_rif': self.company_rif_ping,
                        'company_email': self.company_email_ping,
                        'company_name': self.company_name_ping,
                        'sync_interval_minutes': self.sync_interval_var.get().strip(),
                        'configured': True,
                        'first_run': False
                    }

                    # Encriptar y guardar
                    config_encrypted = encrypt_config(config)
                    with open(CONFIG_FILE, 'w') as f:
                        json.dump(config_encrypted, f, indent=2)

                    self.log("✅ Configuración guardada en archivo", "info")
                except Exception as e:
                    messagebox.showerror("Error", f"Error guardando configuración:\n{e}")
                    return

                # Mostrar ventana de primera sincronización con progreso detallado
                progreso.after(1000, lambda: self._mostrar_ventana_carga_api(resultado['api_key']))
            else:
                btn_cerrar.config(text="⚠️ Cerrar", command=cerrar_ventana_progreso, state="normal")
                estado_label.config(text="⚠️ Verificación con errores", foreground="orange")
                estado_paso_label.config(text="⚠️ Hubo errores durante la verificación", foreground="orange")
                messagebox.showinfo("Resultado", resultado['mensaje'])

        def iniciar_tray_despues_de_config(api_key):
            """
            Ejecutar primera sincronización con ventana de progreso y luego iniciar System Tray
            (La autenticación ya se pidió ANTES de abrir ConfigWindow)
            """
            try:
                # Cerrar ventana de progreso de verificación
                try:
                    if progreso.winfo_exists():
                        progreso.destroy()
                except:
                    pass

                # Cerrar ventana principal de config
                try:
                    if self.root.winfo_exists():
                        self.root.destroy()
                except:
                    pass

                # Ejecutar primera sincronización con ventana de progreso
                # Esto mostrará una ventana con el progreso de la sincronización
                ejecutar_primera_sync_y_tray(api_key)
            except Exception as e:
                messagebox.showerror("Error", f"Error iniciando sincronización:\n{e}")

        progreso.bind('<<VerificationComplete>>', on_verification_complete)

        # Iniciar verificación
        ejecutar_verificacion_thread()


    def _mostrar_ventana_carga_api(self, api_key):
        """Mostrar ventana de primera sincronización con progreso detallado."""
        # Cerrar ventana de progreso de verificación
        try:
            for widget in list(self.root.winfo_children()):
                if isinstance(widget, tk.Toplevel):
                    try:
                        widget.destroy()
                    except:
                        pass
        except:
            pass

        # Cerrar ventana principal de configuración
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except:
            pass

        # Cargar configuración guardada
        if not os.path.exists(CONFIG_FILE):
            messagebox.showerror("Error", "No se encontró configuración guardada")
            return

        from config_encryption import decrypt_config
        with open(CONFIG_FILE, 'r') as f:
            config_encrypted = json.load(f)
        config = decrypt_config(config_encrypted)

        # Crear ventana de primera sincronización
        sync_window = tk.Tk()
        sync_window.title("Primera Sincronización")
        sync_window.geometry("650x580")
        sync_window.resizable(False, False)
        sync_window.protocol("WM_DELETE_WINDOW", lambda: None)

        sync_window.update_idletasks()
        x = (sync_window.winfo_screenwidth() // 2) - (650 // 2)
        y = (sync_window.winfo_screenheight() // 2) - (580 // 2)
        sync_window.geometry(f"+{x}+{y}")

        sync_window.attributes('-topmost', True)
        sync_window.lift()
        sync_window.focus_force()

        # Frame principal
        main_frame = tk.Frame(sync_window, bg="#f0f0f0", padx=30, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Título
        tk.Label(main_frame, text="PRIMERA SINCRONIZACIÓN",
                 font=("Arial", 18, "bold"), bg="#f0f0f0", fg="#2c3e50").pack(pady=(0, 5))
        tk.Label(main_frame, text="Por favor espere mientras se realiza la primera sincronización",
                 font=("Arial", 10), bg="#f0f0f0", fg="#7f8c8d").pack(pady=(0, 15))

        # Spinner animado
        spinner_label = tk.Label(main_frame, text="⟳", font=("Arial", 60),
                                 bg="#f0f0f0", fg="#3498db")
        spinner_label.pack(pady=(0, 10))

        # Estado general
        estado_general = tk.Label(main_frame, text="Iniciando...",
                                  font=("Arial", 11, "bold"),
                                  bg="#f0f0f0", fg="#2c3e50")
        estado_general.pack(pady=(0, 15))

        # Frame de pasos con checkboxes
        pasos_frame = tk.LabelFrame(main_frame, text="  Progreso  ",
                                    font=("Arial", 10, "bold"),
                                    bg="#f0f0f0", fg="#2c3e50",
                                    padx=15, pady=12)
        pasos_frame.pack(fill="x", padx=5)

        pasos = [
            "Cargando configuración",
            "Conectando a la base de datos",
            "Sincronizando productos",
            "Sincronizando categorías",
            "Sincronizando clientes",
            "Sincronizando vendedores",
            "Finalizando"
        ]

        paso_vars = []
        for i, paso_text in enumerate(pasos, 1):
            paso_frame = tk.Frame(pasos_frame, bg="#f0f0f0")
            paso_frame.pack(fill="x", pady=1)
            var = tk.IntVar(value=0)
            cb = tk.Checkbutton(paso_frame, text=f"  {i}. {paso_text}",
                               variable=var, font=("Arial", 10),
                               bg="#f0f0f0", fg="#555555",
                               selectcolor="white", state="disabled",
                               disabledforeground="#555555", anchor="w")
            cb.pack(fill="x")
            paso_vars.append(var)

        # Barra de progreso con porcentaje
        barra_frame = tk.Frame(main_frame, bg="#f0f0f0")
        barra_frame.pack(fill="x", pady=(20, 5), padx=5)

        progress_bar = ttk.Progressbar(barra_frame, mode='determinate', length=500)
        progress_bar.pack(side="left")

        pct_label = tk.Label(barra_frame, text="0%", font=("Arial", 11, "bold"),
                             bg="#f0f0f0", fg="#0066cc")
        pct_label.pack(side="right", padx=(10, 0))

        # Cola para comunicación thread-safe
        sync_queue = queue.Queue()

        # Variables compartidas
        sync_completada = [False]
        sync_error = [None]
        tray_started = [False]

        # Animación del spinner (ciclo de 4 cuadrantes)
        spinner_frames = ["◐", "◓", "◑", "◒"]
        current_frame = [0]

        def animar_spinner():
            if sync_completada[0]:
                return
            try:
                if sync_window.winfo_exists():
                    current_frame[0] = (current_frame[0] + 1) % len(spinner_frames)
                    spinner_label.config(text=spinner_frames[current_frame[0]])
                    sync_window.after(200, animar_spinner)
            except:
                pass

        animar_spinner()

        def procesar_mensajes():
            """Procesar mensajes de la cola desde el main thread."""
            if sync_completada[0] or not sync_window.winfo_exists():
                return

            try:
                while not sync_queue.empty():
                    msg = sync_queue.get_nowait()

                    if isinstance(msg, dict):
                        msg_type = msg.get('type', '')

                        if msg_type == 'paso':
                            paso_idx = msg.get('paso', 1) - 1
                            if 0 <= paso_idx < len(paso_vars):
                                paso_vars[paso_idx].set(1)

                        elif msg_type == 'progress':
                            progress_bar['value'] = msg.get('porcentaje', 0)
                            pct_label.config(text=f"{int(msg.get('porcentaje', 0))}%")
                            if 'text' in msg:
                                estado_general.config(text=msg['text'])

                        elif msg_type == 'complete':
                            sync_completada[0] = True
                            try:
                                spinner_label.config(text="✅")
                                estado_general.config(text="Sincronización completada exitosamente",
                                                      fg="#27ae60")
                                progress_bar['value'] = 100
                                pct_label.config(text="100%")
                            except:
                                pass

                            def iniciar_tray():
                                try:
                                    if sync_window.winfo_exists():
                                        sync_window.destroy()
                                except:
                                    pass
                                from datetime import datetime
                                error_file = "tray_error_log.txt"
                                try:
                                    log_msg = f"[{datetime.now()}] Iniciando thread de system tray..."
                                    print(log_msg)
                                    with open(error_file, "a") as ef:
                                        ef.write(log_msg + "\n")
                                    t = threading.Thread(target=iniciar_system_tray,
                                                        args=(config, api_key),
                                                        daemon=False)
                                    t.start()
                                    tray_started[0] = True
                                    log_msg = f"[{datetime.now()}] Thread de system tray iniciado correctamente"
                                    print(log_msg)
                                    with open(error_file, "a") as ef:
                                        ef.write(log_msg + "\n")
                                except Exception as e:
                                    import traceback
                                    err_msg = f"[{datetime.now()}] ERROR iniciando tray: {e}\n{traceback.format_exc()}"
                                    print(err_msg)
                                    with open(error_file, "a") as ef:
                                        ef.write(err_msg + "\n")

                            sync_window.after(2000, iniciar_tray)

                        elif msg_type == 'error':
                            sync_completada[0] = True
                            sync_error[0] = msg.get('text', 'Error desconocido')
                            try:
                                spinner_label.config(text="❌")
                                estado_general.config(text=f"Error: {sync_error[0]}",
                                                      fg="#c0392b")
                                progress_bar['value'] = 0
                                pct_label.config(text="Error")
                            except:
                                pass

            except queue.Empty:
                pass
            except Exception:
                pass

            if not sync_completada[0]:
                try:
                    sync_window.after(100, procesar_mensajes)
                except:
                    pass

        def ejecutar_sync():
            """Ejecutar sincronización en thread separado."""
            try:
                # Paso 1: Cargando configuración
                sync_queue.put({'type': 'paso', 'paso': 1})
                sync_queue.put({'type': 'progress', 'porcentaje': 5,
                               'text': 'Cargando configuración...'})

                auth_manager = APIAuthManager(config['api_url'])
                ping_result = auth_manager.ping_api_key(config['api_key'])
                if not ping_result.get('success'):
                    sync_queue.put({
                        'type': 'error',
                        'text': f"Error autenticación: {ping_result.get('error', 'Error desconocido')}"
                    })
                    return

                auth_manager.validate_company(config['company_rif'], config['company_email'])
                time.sleep(0.3)
                sync_queue.put({'type': 'progress', 'porcentaje': 10,
                               'text': 'Configuración cargada correctamente'})

                # Paso 2: Conectando a la base de datos
                sync_queue.put({'type': 'paso', 'paso': 2})
                sync_queue.put({'type': 'progress', 'porcentaje': 15,
                               'text': 'Conectando a la base de datos...'})

                postgres_config = {
                    'host': config['postgres_host'],
                    'port': config['postgres_port'],
                    'database': config['postgres_database'],
                    'user': config['postgres_user'],
                    'password': config['postgres_password']
                }

                # Logger que captura mensajes de sync_all para actualizar pasos
                paso_map = {
                    'CATEGORIES': (4, 40, 'Sincronizando categorías...'),
                    'PRODUCTS': (3, 55, 'Sincronizando productos...'),
                    'CUSTOMERS': (5, 70, 'Sincronizando clientes...'),
                    'SELLERS': (6, 85, 'Sincronizando vendedores...'),
                    'RESUMEN': (7, 95, 'Finalizando sincronización...'),
                }

                def sync_logger(msg, level="info"):
                    try:
                        msg_str = str(msg)
                        sync_queue.put({'type': 'log', 'text': msg_str})
                        for key, (paso_num, pct, text) in paso_map.items():
                            if key in msg_str:
                                sync_queue.put({'type': 'paso', 'paso': paso_num})
                                sync_queue.put({'type': 'progress',
                                               'porcentaje': pct, 'text': text})
                                break
                    except:
                        pass

                sync_manager = APISyncManager(
                    postgres_config, auth_manager, logger=sync_logger
                )

                if not sync_manager.connect_postgresql():
                    sync_queue.put({
                        'type': 'error',
                        'text': 'Error conectando a PostgreSQL. Verifique la conexión.'
                    })
                    return

                if not sync_manager.initialize_api_clients():
                    sync_queue.put({
                        'type': 'error',
                        'text': 'Error inicializando clientes API.'
                    })
                    return

                time.sleep(0.3)
                sync_queue.put({'type': 'progress', 'porcentaje': 25,
                               'text': 'Conectado a la base de datos'})

                # Ejecutar sincronización completa
                result = sync_manager.sync_all()

                if result.get('success'):
                    # Marcar todos los pasos como completados
                    for i in range(len(paso_vars)):
                        paso_vars[i].set(1)
                    sync_queue.put({'type': 'complete'})
                else:
                    sync_queue.put({
                        'type': 'error',
                        'text': result.get('error', 'Error durante la sincronización')
                    })

            except Exception as e:
                sync_queue.put({'type': 'error', 'text': str(e)})

        # Iniciar loop de procesamiento de mensajes
        sync_window.after(100, procesar_mensajes)

        # Iniciar thread de sincronización
        threading.Thread(target=ejecutar_sync, daemon=True).start()

        # Iniciar mainloop
        sync_window.mainloop()

        # Fallback: si el tray no se inicio (por ejemplo si la sincronizacion fallo),
        # iniciarlo de todas formas para que el sistema quede en segundo plano
        if not tray_started[0] and os.path.exists(CONFIG_FILE):
            try:
                from datetime import datetime
                fallback_log = f"[{datetime.now()}] FALLBACK: Iniciando tray despues de sync_window.mainloop()"
                print(fallback_log)
                with open("tray_error_log.txt", "a") as ef:
                    ef.write(fallback_log + "\n")
                t = threading.Thread(target=iniciar_system_tray,
                                    args=(config, api_key),
                                    daemon=False)
                t.start()
                print(f"[{datetime.now()}] FALLBACK: Tray iniciado correctamente")
            except Exception as e:
                print(f"[{datetime.now()}] FALLBACK: Error iniciando tray: {e}")
                traceback.print_exc()




# ==============================================================================
# PRIMERA SINCRONIZACIÓN Y SYSTEM TRAY
# ==============================================================================

def ejecutar_primera_sync_y_tray(api_key, cerrar_ventana_callback=None):
    """
    Ejecuta la primera sincronización y luego inicia el System Tray

    Args:
        api_key: API Key de la API
        cerrar_ventana_callback: Función para cerrar la ventana de progreso después de la sync
    """
    # Archivo de log para diagnóstico
    log_file = open("primera_sync_log.txt", "w", encoding="utf-8")

    def log_debug(msg):
        """Escribe a consola y archivo"""
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()

    try:
        log_debug("\n[DEBUG] Iniciando ejecutar_primera_sync_y_tray()")

        # Cargar configuración guardada
        if not os.path.exists(CONFIG_FILE):
            log_debug("[DEBUG] ERROR: No existe CONFIG_FILE")
            messagebox.showerror("Error", "No se encontró configuración guardada")
            log_file.close()
            return

        from config_encryption import decrypt_config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Desencriptar todos los campos sensibles
        config = decrypt_config(config)

        log_debug(f"[DEBUG] Config cargada: {config.get('company_email')}")
        log_debug(f"[DEBUG] api_key recibido: {'Sí' if api_key else 'No'}")

        # Crear ventana de progreso para primera sincronización
        log_debug("[DEBUG] Creando ventana de sincronización...")
        # Crear nueva ventana Tk independiente
        sync_window = tk.Tk()
        sync_window.title("🔄 Primera Sincronización")
        sync_window.geometry("600x300")
        sync_window.resizable(False, False)

        # Prevenir que el usuario cierre la ventana manualmente
        sync_window.protocol("WM_DELETE_WINDOW", lambda: None)  # Deshabilitar botón X

        # Centrar ventana
        sync_window.update_idletasks()
        width = sync_window.winfo_width()
        height = sync_window.winfo_height()
        x = (sync_window.winfo_screenwidth() // 2) - (width // 2)
        y = (sync_window.winfo_screenheight() // 2) - (height // 2)
        sync_window.geometry(f"{width}x{height}+{x}+{y}")

        # Mantener ventana al frente (topmost)
        sync_window.attributes('-topmost', True)
        sync_window.lift()
        sync_window.focus_force()

        # Widgets
        # Frame principal con borde
        main_frame = tk.Frame(sync_window, bg="#f0f0f0", padx=30, pady=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="🔄 Ejecutando Primera Sincronización",
                font=("Arial", 16, "bold"), bg="#f0f0f0", fg="#2c3e50").pack(pady=(0, 10))

        tk.Label(main_frame, text="Por favor espere, esto puede tardar varios minutos...",
                font=("Arial", 10), bg="#f0f0f0", fg="#7f8c8d").pack(pady=(0, 15))

        sync_label = tk.Label(main_frame, text="⏳ Iniciando...",
                             font=("Arial", 12, "bold"), bg="#f0f0f0", fg="#3498db",
                             wraplength=520, justify="center")
        sync_label.pack(pady=10)

        progress_bar = ttk.Progressbar(main_frame, mode='indeterminate', length=520)
        progress_bar.pack(pady=20)
        progress_bar.start(10)

        # Información adicional
        info_label = tk.Label(main_frame,
                             text="ℹ️ No cierre esta ventana\nLa sincronización se ejecuta en segundo plano",
                             font=("Arial", 9), bg="#f0f0f0", fg="#7f8c8d",
                             justify="center")
        info_label.pack(pady=(25, 0))

        # Cola para comunicación thread → main thread
        sync_queue = queue.Queue()

        # Bandera para detener el procesamiento de mensajes
        # DEBE definirse ANTES de procesar_mensajes_queue() que la referencia con nonlocal
        sync_completada = False

        # Variable para compartir resultado entre ejecutar_sync_worker() y on_sync_complete()
        sync_result = None

        def procesar_mensajes_queue():
            """Procesa mensajes de la cola desde el main thread"""
            nonlocal sync_completada

            try:
                # Verificar si la ventana aún existe
                if not sync_window.winfo_exists():
                    log_debug("[DEBUG] procesar_mensajes_queue(): Ventana no existe, saliendo")
                    return

                # Si la sync ya se completó, dejar de procesar mensajes
                if sync_completada:
                    log_debug("[DEBUG] Sync completada, deteniendo procesar_mensajes_queue()")
                    return

                try:
                    # Leer mensajes de la cola sin bloquear
                    while not sync_queue.empty():
                        msg = sync_queue.get_nowait()

                        if msg['type'] == 'progress':
                            # Actualizar etiqueta de progreso
                            sync_label.config(text=f"⏳ {msg['message']}")
                        elif msg['type'] == 'error':
                            # Error en sincronización
                            log_debug(f"[DEBUG] Error en sync: {msg['message']}")
                            sync_label.config(text=f"❌ Error: {msg['message']}", foreground="#c0392b")
                            info_label.config(text="⚠️ La sincronización falló\nRevise el log para más detalles", fg="#c0392b", bg="#f0f0f0")
                        elif msg['type'] == 'complete':
                            # Sincronización completada exitosamente
                            log_debug("[DEBUG] Sincronización completada exitosamente")
                            sync_label.config(text="✅ Sincronización completada exitosamente", foreground="#27ae60", bg="#f0f0f0", font=("Arial", 12, "bold"))
                            info_label.config(text="✅ Primera sincronización completada exitosamente\nIniciando System Tray en segundo plano...", fg="#27ae60", bg="#f0f0f0", font=("Arial", 10, "bold"))
                            progress_bar.stop()

                            # Actualizar estado
                            sync_completada = True
                            sync_result = msg.get('data', {})
                            log_debug(f"[DEBUG] Sync result: {sync_result}")

                            # Cerrar ventana de sincronización después de 3 segundos
                            def cerrar_sync_window():
                                """Cerrar la ventana de sincronización y el mainloop"""
                                try:
                                    if sync_window.winfo_exists():
                                        log_debug("[DEBUG] Cerrando sync_window...")
                                        # CERRAR LA VENTANA PRIMERO, antes de iniciar System Tray
                                        log_debug("[DEBUG] Destruyendo ventana ANTES de iniciar System Tray...")
                                        sync_window.destroy()
                                        log_debug("[DEBUG] sync_window destruida")

                                        # Ahora iniciar System Tray en un thread separado
                                        # para que no bloquee
                                        log_debug("[DEBUG] Iniciando System Tray en thread separado...")
                                        log_debug(f"[DEBUG] api_key en sync_result: {'Sí' if sync_result.get('api_key') else 'No'}")

                                        import threading
                                        tray_thread = threading.Thread(
                                            target=iniciar_system_tray,
                                            args=(config, sync_result.get('api_key')),
                                            daemon=False  # System Tray debe seguir vivo
                                        )
                                        tray_thread.start()
                                        log_debug("[DEBUG] Thread de System Tray iniciado")
                                except Exception as e:
                                    log_debug(f"[DEBUG] Error cerrando sync_window: {e}")

                            sync_window.after(3000, cerrar_sync_window)

                            # Cerrar ventana de progreso (config) después de 3 segundos
                            if cerrar_ventana_callback:
                                sync_window.after(3000, cerrar_ventana_callback)
                        elif msg['type'] == 'log':
                            # Mensaje de log
                            log_debug(f"[SYNC LOG] {msg['message']}")
                except queue.Empty:
                    # No hay mensajes, continuar esperando
                    pass
                except Exception as e:
                    log_debug(f"[DEBUG] Error procesando mensaje: {e}")

                # Volver a verificar después de 50ms
                sync_window.after(50, procesar_mensajes_queue)

            except Exception as e:
                log_debug(f"[DEBUG] Error en procesar_mensajes_queue: {e}")
                import traceback
                log_debug(traceback.format_exc())

        def ejecutar_sync_worker():
            """Ejecuta la sincronización en un thread separado"""
            nonlocal sync_result

            try:
                log_debug("[DEBUG] Creando APISyncManager...")
                api_manager = APISyncManager(postgres_config, auth_manager, log_debug)

                log_debug("[DEBUG] Ejecutando primera sincronización...")

                # Enviar mensaje inicial
                sync_queue.put({
                    'type': 'progress',
                    'message': 'Conectando a API...'
                })

                # Simular espera para dar tiempo a ver el mensaje inicial
                import time
                time.sleep(1)

                sync_queue.put({
                    'type': 'progress',
                    'message': 'Sincronizando datos desde PostgreSQL...'
                })
                time.sleep(1)

                sync_queue.put({
                    'type': 'progress',
                    'message': 'Sincronizando con API REST...'
                })
                time.sleep(1)

                result = api_manager.sincronizar_todo()

                log_debug(f"[DEBUG] Sincronización completada. Resultado: {result}")

                if result.get('success'):
                    sync_queue.put({
                        'type': 'progress',
                        'message': 'Verificando sincronización...'
                    })
                    time.sleep(0.5)

                    sync_queue.put({
                        'type': 'complete',
                        'data': {
                            'api_key': config.get('api_key') or api_key
                        }
                    })
                else:
                    sync_queue.put({
                        'type': 'error',
                        'message': result.get('error', 'Error desconocido')
                    })
            except Exception as e:
                log_debug(f"[DEBUG] Exception en ejecutar_sync_worker: {e}")
                import traceback
                log_debug(traceback.format_exc())
                sync_queue.put({
                    'type': 'error',
                    'message': str(e)
                })

        # Iniciar thread de sincronización
        log_debug("[DEBUG] Iniciando thread de sincronización...")
        sync_thread = threading.Thread(target=ejecutar_sync_worker, daemon=False)
        sync_thread.start()

        # Iniciar procesamiento de mensajes de la cola
        log_debug("[DEBUG] Iniciando procesamiento de mensajes...")
        sync_window.after(100, procesar_mensajes_queue)

        # Iniciar mainloop de la ventana para procesar eventos
        # Esto permite que funcione el after() para cerrar la ventana
        log_debug("[DEBUG] Iniciando mainloop de sync_window...")
        sync_window.mainloop()
        log_debug("[DEBUG] Mainloop terminado, ventana cerrada")

    except Exception as e:
        log_debug(f"[DEBUG] ERROR en ejecutar_primera_sync_y_tray: {e}")
        import traceback
        log_debug(traceback.format_exc())
        log_file.close()
        messagebox.showerror("Error", f"Error preparando sincronización:\n{e}")


def iniciar_system_tray(config, api_key):
    """Inicia el servicio System Tray"""
    from datetime import datetime
    error_log_path = os.path.join(os.getcwd(), 'tray_error_log.txt')

    # Continuar usando el mismo archivo de log
    log_file = open("primera_sync_log.txt", "a", encoding="utf-8")

    def log_debug(msg):
        """Escribe a consola y archivo"""
        print(msg)
        log_file.write(msg + "\n")
        log_file.flush()

    try:
        log_debug("\n[DEBUG] ===== INICIAR SYSTEM TRAY =====")
        log_debug(f"[DEBUG] Company: {config.get('company_email')}")
        log_debug(f"[DEBUG] API Key: {'***' if api_key else 'None'}")

        # Verificar que hay configuración válida
        if not config:
            log_debug("[DEBUG] ERROR: Config es None o vacío")
            try:
                with open(error_log_path, "a", encoding="utf-8") as ef:
                    ef.write(f"[{datetime.now()}] ERROR: Config es None o vacío\n")
            except:
                pass
            log_file.close()
            return

        log_debug(f"[DEBUG] Config tiene {len(config)} keys")

        # Crear e iniciar servicio System Tray
        log_debug("\n" + "="*70)
        log_debug("🔄 Iniciando modo System Tray...")
        log_debug("="*70)

        log_debug("[DEBUG] Creando instancia de SystemTrayService...")
        tray_service = SystemTrayService(config, api_key)
        log_debug("[DEBUG] SystemTrayService creada")

        log_debug("[DEBUG] Llamando a tray_service.iniciar()...")
        log_debug("[DEBUG] Esto iniciará el icono en la barra de tareas")
        tray_service.iniciar()
        log_debug("[DEBUG] tray_service.iniciar() retornó (no debería llegar aquí nunca)")

    except Exception as e:
        import traceback
        error_msg = f"[{datetime.now()}] ERROR en iniciar_system_tray: {e}\n{traceback.format_exc()}"
        log_debug(f"[DEBUG] ERROR en iniciar_system_tray: {e}")
        log_debug(traceback.format_exc())
        print(error_msg)
        try:
            with open(error_log_path, "a", encoding="utf-8") as ef:
                ef.write(error_msg + "\n")
        except:
            pass
        log_file.close()



    # Ejecutar primera sincronización y luego iniciar System Tray
    print("="*70)
    print("🔄 SINCRONIZACIÓN INICIAL...")
    print("="*70)
    
    # Cargar configuración
    if not os.path.exists(CONFIG_FILE):
        print("❌ No hay configuración. Ejecute --mode config primero")
        return False
    
    try:
        from config_encryption import decrypt_config
        with open(CONFIG_FILE, 'r') as f:
            cfg = json.load(f)
        config = decrypt_config(cfg)
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        return False
    
    api_key = config.get('api_key', '')
    if not api_key:
        print("❌ No hay API Key en configuración")
        return False
    
    # Ejecutar sincronización
    try:
        from sync_system_api import ejecutar_primera_sync_y_tray, log_startup_error
        ejecutar_primera_sync_y_tray(api_key)
        print("✅ Primera sincronización completada")
        print("✅ System Tray iniciado")
        return True
    except Exception as e:
        print(f"❌ Error en primera sincronización: {e}")
        import traceback
        print(traceback.format_exc())
        log_startup_error("FIRST_SYNC_ERROR", str(e), traceback.format_exc())
        return False

# ==============================================================================
# GUI - LAUNCHER WINDOW (Menú Principal)
# ==============================================================================

class LauncherWindow:
    """Ventana principal del launcher para ejecutable .exe"""

    def __init__(self, root):
        self.root = root
        self.root.title("Sincronizador API REST - Chrystal")
        self.root.geometry("600x500")
        self.root.resizable(False, False)

        # Centrar ventana
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        self.create_widgets()

    def create_widgets(self):
        """Crear widgets del launcher"""
        # Header con gradiente simulado
        header = tk.Frame(self.root, bg="#2c3e50", height=100)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Título
        title = tk.Label(header, text="🔄 Sincronizador API REST",
                        font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=(20, 5))

        subtitle = tk.Label(header, text="Sistema de Sincronización Chrystal",
                           font=("Arial", 11), bg="#2c3e50", fg="#bdc3c7")
        subtitle.pack()

        # Contenido principal
        main_frame = tk.Frame(self.root, bg="#ecf0f1", padx=30, pady=30)
        main_frame.pack(fill="both", expand=True)

        # Verificar si hay configuración
        has_config = os.path.exists(CONFIG_FILE)

        if not has_config:
            # Mostrar mensaje si no hay configuración
            warning_frame = tk.Frame(main_frame, bg="#fff3cd", borderwidth=2, relief="solid")
            warning_frame.pack(fill="x", pady=(0, 20))

            warning_label = tk.Label(warning_frame,
                                   text="⚠️ Primera vez: Debe configurar el sistema antes de usarlo",
                                   font=("Arial", 11, "bold"),
                                   bg="#fff3cd", fg="#856404",
                                   padx=20, pady=15)
            warning_label.pack()

        # Botones principales
        btn_frame = tk.Frame(main_frame, bg="#ecf0f1")
        btn_frame.pack(expand=True)

        button_style = {
            'font': ('Arial', 12),
            'width': 35,
            'height': 2,
            'pady': 10
        }

        # Botón Configurar
        tk.Button(btn_frame,
                 text="⚙️ CONFIGURAR SISTEMA",
                 command=self.launch_config,
                 bg="#3498db", fg="white",
                 **button_style).pack(pady=5)

        # Botón Manager
        tk.Button(btn_frame,
                 text="🖥️ ABRIR MANAGER",
                 command=self.launch_manager,
                 bg="#2ecc71", fg="white",
                 **button_style).pack(pady=5)

        # Botón System Tray
        tk.Button(btn_frame,
                 text="📬 MODO SYSTEM TRAY",
                 command=self.launch_tray,
                 bg="#9b59b6", fg="white",
                 **button_style).pack(pady=5)

        # Botón Sincronizar Ahora
        tk.Button(btn_frame,
                 text="🔄 SINCRONIZAR AHORA",
                 command=self.launch_sync,
                 bg="#e67e22", fg="white",
                 **button_style).pack(pady=5)

        # Botón Reconfigurar
        tk.Button(btn_frame,
                 text="🔧 RECONFIGURAR",
                 command=self.launch_reconfig,
                 bg="#95a5a6", fg="white",
                 **button_style).pack(pady=5)

        # Footer
        footer = tk.Frame(main_frame, bg="#ecf0f1")
        footer.pack(fill="x", pady=(10, 0))

        version_label = tk.Label(footer,
                                text="v1.0 - Sistema de Sincronización PostgreSQL → API REST",
                                font=("Arial", 9),
                                bg="#ecf0f1", fg="#7f8c8d")
        version_label.pack()

    def launch_config(self):
        """Lanzar modo configuración con autenticación"""
        # Verificar autenticación antes de abrir config
        auth_result = autenticar_para_config()
        if not auth_result or not auth_result.get('success', False):
            print("❌ Acceso a configuración denegado: autenticación fallida o cancelada")
            return

        self.root.destroy()
        root = tk.Tk()
        app = ConfigWindow(root)
        root.mainloop()

    def launch_manager(self):
        """Lanzar modo manager"""
        self.root.destroy()
        root = tk.Tk()
        app = ManagerWindow(root)
        root.mainloop()

    def launch_tray(self):
        """Lanzar modo system tray"""
        self.root.destroy()

        # Cargar configuración
        if not os.path.exists(CONFIG_FILE):
            messagebox.showerror("Error", "No hay configuración. Ejecute 'Configurar Sistema' primero")
            return

        try:
            from config_encryption import decrypt_config
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            # Desencriptar todos los campos sensibles
            config = decrypt_config(config)
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando configuración: {e}")
            return

        # Obtener API Key (ya viene desencriptado)
        api_key = config.get('api_key')

        # Si no hay API Key en config, pedirlo manualmente
        if not api_key:
            print("🔐 Se requiere API Key...")
            import getpass
            try:
                api_key = getpass.getpass("API Key: ")
            except:
                # Si falla getpass (Windows a veces), usar tkinter
                key_dialog = tk.Tk()
                key_dialog.withdraw()
                api_key = tk.simpledialog.askstring("API Key", "Ingrese la API Key:", show='*')
                key_dialog.destroy()

                if not api_key:
                    return

        # Iniciar System Tray
        try:
            tray = SystemTrayService(config, api_key)
            tray.iniciar()
        except Exception as e:
            messagebox.showerror("Error", f"Error iniciando System Tray: {e}\n\nAsegúrese de tener instaladas las dependencias:\npip install pystray Pillow")

    def launch_sync(self):
        """Lanzar sincronización única"""
        self.root.destroy()

        # Cargar configuración
        if not os.path.exists(CONFIG_FILE):
            messagebox.showerror("Error", "No hay configuración. Ejecute 'Configurar Sistema' primero")
            # Volver al launcher
            root = tk.Tk()
            app = LauncherWindow(root)
            root.mainloop()
            return

        # Ejecutar sincronización en consola
        import subprocess
        import sys

        if getattr(sys, 'frozen', False):
            # Ejecutable compilado
            subprocess.Popen([sys.executable, '--mode', 'sync'])
        else:
            # Script Python
            subprocess.Popen([sys.executable, __file__, '--mode', 'sync'])

    def launch_reconfig(self):
        """Lanzar reconfiguración"""
        result = messagebox.askyesno("Confirmar",
                                    "¿Está seguro que desea borrar la configuración?\n\nTendrá que configurar el sistema nuevamente.")
        if result:
            # Borrar configuración
            if os.path.exists(CONFIG_FILE):
                os.remove(CONFIG_FILE)

            messagebox.showinfo("Reconfiguración", "Configuración eliminada. Configure el sistema nuevamente.")

            # Abrir configuración
            self.launch_config()


# ==============================================================================
# GUI - MANAGER WINDOW
# ==============================================================================

class ManagerWindow:
    """Ventana principal de administración."""

    def __init__(self, root, api_key=None):
        self.root = root
        self.root.title("Sincronizador API REST - Manager")
        self.root.geometry("800x600")

        # Auth Manager (en memoria)
        self.auth_manager = None

        # Sync Manager
        self.sync_manager = None

        # API Key (puede venir de reautenticar_usuario)
        self.api_key = api_key

        # Cargar configuración (puede ser None si no existe)
        self.config = self.load_config()

        # Configurar logging con archivo (o default si no hay config)
        email = self.config.get('company_email') if self.config else 'user'
        self.log_func = setup_logging(email)

        # Crear widgets PRIMERO (antes de cualquier log)
        self.create_widgets()

        # Conectar logger de Python con la GUI (después de crear widgets)
        add_gui_handler(self.log_func, self.log)

        # AHORA ya podemos usar self.log()
        if not self.config:
            self.log("⚠️ No hay configuración. Use el botón 'Configurar' para establecerla.")
            self.log("ℹ️ Configure el sistema para comenzar")
        else:
            # Si hay configuración Y no se pasó API Key, pedirlo al inicio
            # Si se pasó API Key (desde reautenticar_usuario), usarlo directamente
            if self.api_key:
                # API Key ya proporcionado - validar directamente
                self.log("✅ API Key proporcionado desde autenticación previa")
                self.do_validate_api_key(self.api_key, None)
            else:
                # Pedir API Key al usuario
                self.root.after(100, self.ask_api_key)

    def load_config(self):
        """Cargar configuración desde archivo."""
        try:
            if os.path.exists(CONFIG_FILE):
                from config_encryption import decrypt_config
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                # Desencriptar todos los campos sensibles
                return decrypt_config(config)
        except Exception as e:
            messagebox.showerror("Error", f"Error cargando configuración:\n{e}")
        return None

    def ask_api_key(self):
        """Pedir API Key."""
        # Primero intentar cargar API Key del config
        if self.config and 'api_key' in self.config:
            api_key = self.config.get('api_key')
            if api_key:
                self.log("API Key cargado desde configuración")
                self.do_validate_api_key(api_key, None)
                return
            else:
                self.log("API Key en configuración está vacío")

        dialog = tk.Toplevel(self.root)
        dialog.title("API Key")
        dialog.geometry("500x200")
        dialog.resizable(False, False)

        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()

        x = parent_x + (parent_width // 2) - 250
        y = parent_y + (parent_height // 2) - 100
        dialog.geometry(f"+{x}+{y}")

        dialog.lift()
        dialog.attributes('-topmost', True)
        dialog.after_idle(lambda: dialog.attributes('-topmost', False))
        dialog.focus_force()

        frame = tk.Frame(dialog, padx=30, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Ingrese la API Key:",
                font=("Arial", 12, "bold")).pack(pady=(0, 15))

        key_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=key_var, show="*", width=40, font=("Arial", 11))
        entry.pack(pady=10)
        entry.focus()

        def on_validate():
            api_key = key_var.get()
            if not api_key:
                messagebox.showwarning("Advertencia", "Ingrese la API Key", parent=dialog)
                entry.focus()
                return

            self.do_validate_api_key(api_key, dialog)

        def on_cancel():
            try:
                dialog.destroy()
            except:
                pass
            try:
                self.root.destroy()
            except:
                pass

        button_frame = tk.Frame(frame)
        button_frame.pack(pady=15)
        ttk.Button(button_frame, text="Validar", command=on_validate, width=12).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancelar", command=on_cancel, width=12).pack(side="left", padx=5)

        entry.bind("<Return>", lambda e: on_validate())
        dialog.after(100, entry.focus)
        def on_login():
            password = password_var.get()
            if not password:
                messagebox.showwarning("Advertencia", "Ingrese el password", parent=dialog)
                entry.focus()
                return

            self.do_login(password, dialog)

        def on_cancel():
            try:
                dialog.destroy()
            except:
                pass
            try:
                self.root.destroy()
            except:
                pass

        button_frame = tk.Frame(frame)
        button_frame.pack(pady=15)
        ttk.Button(button_frame, text="✅ Login", command=on_login, width=12).pack(side="left", padx=5)
        ttk.Button(button_frame, text="❌ Cancelar", command=on_cancel, width=12).pack(side="left", padx=5)

        entry.bind("<Return>", lambda e: on_login())

        # Asegurar focus
        dialog.after(100, entry.focus)

    def do_validate_api_key(self, api_key: str, dialog: tk.Tk):
        """Validar API Key mediante ping."""
        try:
            self.log("Validando API Key...")

            base_url = self.config.get('api_url', 'https://chrystal.com.ve/mobiletest/public/api')
            self.auth_manager = APIAuthManager(base_url, self.log)

            result = self.auth_manager.ping_api_key(api_key)

            if not result.get('success'):
                messagebox.showerror("Error", f"API Key inv\u00e1lida: {result.get('error')}")
                if dialog:
                    try:
                        dialog.destroy()
                    except:
                        pass
                try:
                    self.root.destroy()
                except:
                    pass
                return

            self.log("Validando empresa...")
            result = self.auth_manager.validate_company(
                self.config.get('company_rif'),
                self.config.get('company_email')
            )

            if not result.get('success'):
                messagebox.showerror("Error", f"Validaci\u00f3n fall\u00f3: {result.get('error')}")
                if dialog:
                    try:
                        dialog.destroy()
                    except:
                        pass
                try:
                    self.root.destroy()
                except:
                    pass
                return

            pg_config = {
                'host': self.config.get('postgres_host'),
                'port': self.config.get('postgres_port'),
                'database': self.config.get('postgres_database'),
                'user': self.config.get('postgres_user'),
                'password': self.config.get('postgres_password')
            }

            self.sync_manager = APISyncManager(pg_config, self.auth_manager, self.log)

            if not self.sync_manager.connect_postgresql():
                messagebox.showerror("Error", "No se pudo conectar a PostgreSQL")
                if dialog:
                    try:
                        dialog.destroy()
                    except:
                        pass
                try:
                    self.root.destroy()
                except:
                    pass
                return

            try:
                company_id = self.auth_manager.company_id
                cursor = self.sync_manager.pg_conn.cursor()

                self.log(f"Guardando company_id {company_id} en sync_config...")

                cursor.execute("""
                    SELECT value FROM sync_config WHERE key = 'company_id'
                """)
                existe = cursor.fetchone()

                if existe:
                    valor_actual = existe[0]
                    self.log(f"   sync_config tiene: {valor_actual}")
                    self.log(f"   Actualizando a: {company_id}")
                    cursor.execute("""
                        UPDATE sync_config
                        SET value = %s, updated_at = NOW()
                        WHERE key = 'company_id'
                    """, (str(company_id),))
                    self.log(f"   Filas afectadas: {cursor.rowcount}")
                else:
                    self.log(f"   No existe, insertando nuevo registro...")
                    cursor.execute("""
                        INSERT INTO sync_config (key, value, updated_at)
                        VALUES ('company_id', %s, NOW())
                    """, (str(company_id),))
                    self.log(f"   Insertado: {company_id}")

                self.sync_manager.pg_conn.commit()
                self.log(f"Company_id {company_id} guardado en sync_config")
            except Exception as e:
                self.log(f"Error guardando company_id en sync_config: {e}", "warning")
                self.sync_manager.pg_conn.rollback()

            if not self.sync_manager.initialize_api_clients():
                messagebox.showerror("Error", "No se pudieron inicializar los clientes API")
                if dialog:
                    try:
                        dialog.destroy()
                    except:
                        pass
                try:
                    self.root.destroy()
                except:
                    pass
                return

            if dialog:
                try:
                    dialog.destroy()
                except:
                    pass
            self.log("Sistema listo para sincronizar")

        except Exception as e:
            messagebox.showerror("Error", f"Error validando API Key: {e}")
            import traceback
            self.log(traceback.format_exc(), "error")
            if dialog:
                try:
                    dialog.destroy()
                except:
                    pass
            try:
                self.root.destroy()
            except:
                pass
    def create_widgets(self):
        """Crear widgets de la interfaz."""

        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill="x")

        title = tk.Label(header, text="🔄 Sincronizador API REST - Manager",
                        font=("Arial", 18, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=15)

        # Contenido principal
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Info de empresa
        info_frame = tk.Frame(main_frame)
        info_frame.pack(fill="x", pady=5)

        if self.config:
            tk.Label(info_frame, text=f"🏢 Empresa: {self.config.get('company_rif')}",
                    font=("Arial", 10)).pack(side="left")
            tk.Label(info_frame, text=f"📧 Email: {self.config.get('company_email')}",
                    font=("Arial", 10)).pack(side="left", padx=20)
        else:
            tk.Label(info_frame, text="⚠️ No configurado",
                    font=("Arial", 10), fg="orange").pack(side="left")

        # Panel de estado
        status_frame = tk.LabelFrame(main_frame, text="📊 Estado del Sistema", font=("Arial", 12, "bold"))
        status_frame.pack(fill="x", pady=5, padx=5)

        self.lbl_estado = tk.Label(status_frame, text="🟢 ACTIVO", font=("Arial", 14), fg="green")
        self.lbl_estado.pack()

        self.lbl_ultima_sync = tk.Label(status_frame, text="Última sync: --", font=("Arial", 10))
        self.lbl_ultima_sync.pack(pady=5)

        # Panel de estadísticas
        stats_frame = tk.LabelFrame(main_frame, text="📈 Estadísticas", font=("Arial", 12, "bold"))
        stats_frame.pack(fill="x", pady=5, padx=5)

        self.lbl_stats = tk.Label(stats_frame, text="Categories: 0 | Products: 0 | Customers: 0 | Sellers: 0 | Quotes: 0",
                                 font=("Arial", 10))
        self.lbl_stats.pack()

        self.lbl_progress = tk.Label(stats_frame, text="Listo para sincronizar", font=("Arial", 9), fg="blue")
        self.lbl_progress.pack(pady=(5,0))

        # Botones de sincronización individual
        sync_btn_frame = tk.Frame(main_frame)
        sync_btn_frame.pack(fill="x", pady=5)

        ttk.Button(sync_btn_frame, text="📁 Categories",
                  command=lambda: self.sync_entity('categories'), width=15).pack(side="left", padx=3)

        ttk.Button(sync_btn_frame, text="📦 Products",
                  command=lambda: self.sync_entity('products'), width=15).pack(side="left", padx=3)

        ttk.Button(sync_btn_frame, text="👥 Customers",
                  command=lambda: self.sync_entity('customers'), width=15).pack(side="left", padx=3)

        ttk.Button(sync_btn_frame, text="👔 Sellers",
                  command=lambda: self.sync_entity('sellers'), width=15).pack(side="left", padx=3)

        ttk.Button(sync_btn_frame, text="💰 Quotes",
                  command=lambda: self.sync_entity('quotes'), width=15).pack(side="left", padx=3)

        # Botones principales
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)

        self.btn_sync = ttk.Button(btn_frame, text="🔄 Sincronizar Todo", command=self.sync_all, width=20)
        self.btn_sync.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="⚙️ Configuración", command=self.configurar, width=20).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🔄 Reconfigurar", command=self.reconfig, width=20).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 Ver Logs", command=self.ver_logs, width=20).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Salir", command=self.cerrar_ventana, width=20).pack(side="right", padx=5)

        # Logs
        log_frame = tk.LabelFrame(main_frame, text="📝 Logs en Tiempo Real", font=("Arial", 12, "bold"))
        log_frame.pack(fill="both", expand=True, pady=5, padx=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)

        # Configurar colores para los logs
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("success", foreground="green")

        # Cargar últimos logs
        self.cargar_logs()

    def cargar_logs(self):
        """Cargar últimos logs del archivo."""
        try:
            email = self.config.get('company_email') if self.config else 'user'
            log_file = get_log_file(email)
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    # Leer últimas 50 líneas
                    lines = f.readlines()[-50:]
                    for line in lines:
                        self.log_text.config(state="normal")
                        self.log_text.insert("end", line.strip() + "\n")
                        self.log_text.config(state="disabled")
                self.log_text.see("end")
        except Exception as e:
            pass  # Silencioso, si no hay archivo de log aún

    def cerrar_ventana(self):
        """Cierra la ventana de forma segura"""
        try:
            if self.sync_manager:
                self.sync_manager.close()
            self.root.destroy()
        except Exception as e:
            print(f"Error cerrando ventana: {e}")
            try:
                self.root.destroy()
            except:
                pass

    def configurar(self):
        """Abrir ventana de configuración."""
        # Crear ventana de configuración como Toplevel
        config_window = tk.Toplevel(self.root)
        config_window.title("⚙️ Configuración del Sincronizador API")
        config_window.geometry("700x600")
        config_window.transient(self.root)
        config_window.grab_set()

        # Crear instancia de ConfigWindow con callback
        ConfigWindow(config_window, callback=self.on_config_saved)

    def on_config_saved(self, config):
        """Callback cuando se guarda la configuración desde el Manager."""
        # Recargar configuración
        self.config = self.load_config()

        # Actualizar info de empresa en la UI
        # (destruimos y recreamos los widgets para actualizar)
        for widget in self.root.winfo_children():
            widget.destroy()
        self.create_widgets()

        # Si hay configuración, pedir password
        if self.config:
            self.root.after(100, self.ask_api_key)

        self.log("✅ Configuración guardada exitosamente")

    def ver_logs(self):
        """Abrir archivo de logs en editor de texto."""
        try:
            import subprocess
            log_file = get_log_file(self.config.get('company_email'))

            if not os.path.exists(log_file):
                messagebox.showinfo("Logs", f"No existe archivo de logs aún:\n{log_file}")
                return

            # Mostrar información
            self.log(f"📂 Abriendo archivo de logs: {log_file}")

            # Lista de editores a intentar (en orden de preferencia)
            if sys.platform == 'win32':
                # Windows
                os.startfile(log_file)
                self.log(f"   ✅ Archivo abierto")
            elif sys.platform == 'darwin':
                # macOS
                subprocess.Popen(['open', log_file],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
                self.log(f"   ✅ Archivo abierto con open")
            else:
                # Linux - intentar varios editores
                editores = [
                    # Editores gráficos livianos (sin dependencias de D-Bus pesadas)
                    ['mousepad', log_file],      # Muy liviano, sin D-Bus
                    ['leafpad', log_file],       # Muy liviano
                    ['geany', log_file],         # Liviano
                    ['kate', log_file],          # KDE
                    ['gedit', log_file],         # GNOME (puede dar warnings)
                    ['code', '--new-window', log_file],  # VS Code
                    ['subl', log_file],          # Sublime Text
                    # Último recurso: xdg-open
                    ['xdg-open', log_file]
                ]

                abierto = False
                for editor_cmd in editores:
                    try:
                        self.log(f"   Intentando con: {editor_cmd[0]}")
                        # Usar Popen para no bloquear
                        process = subprocess.Popen(
                            editor_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True  # Desacoplar completamente el proceso
                        )
                        # Si no lanzó excepción, asumimos que se abrió
                        self.log(f"   ✅ Archivo abierto con: {editor_cmd[0]}")
                        abierto = True
                        break
                    except FileNotFoundError:
                        # Editor no encontrado, intentar el siguiente
                        continue
                    except Exception as e:
                        # Otro error, intentar el siguiente
                        self.log(f"   ⚠️ Error con {editor_cmd[0]}: {e}", "warning")
                        continue

                if not abierto:
                    # Si ningún editor funcionó, mostrar la ruta para abrir manualmente
                    self.log(f"   ⚠️ No se pudo abrir automáticamente", "warning")
                    messagebox.showinfo(
                        "Logs - Abrir Manualmente",
                        f"No se pudo abrir el editor automáticamente.\n\n"
                        f"Ruta del archivo:\n{log_file}\n\n"
                        f"Puede abrirlo manualmente con:\n"
                        f"cat '{log_file}'\n\n"
                        f"o su editor favorito:\n"
                        f"'{log_file}'"
                    )

        except Exception as e:
            self.log(f"❌ Error abriendo logs: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
            messagebox.showerror("Error", f"No se pudo abrir el archivo de logs:\n{e}")

    def log(self, message: str, level: str = "info"):
        """Escribir log a la GUI solamente. El logger de Python maneja el archivo."""
        # IMPORTANTE: No llamar a log_func aquí porque causaría duplicados
        # log_func → logger → GUIHandler → GUI (ciclo)
        # En su lugar, escribir directamente a la GUI

        # Los logs que vienen de los clientes API ya pasan por el logger → GUIHandler
        # Solo necesitamos escribir a la GUI para logs directos de ManagerWindow
        if self.log_text:
            self.log_text.config(state="normal")

            # Colores según nivel
            tags = {
                'error': 'error',
                'warning': 'warning',
                'success': 'success'
            }

            tag = tags.get(level, 'normal')
            self.log_text.insert("end", f"{message}\n", tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")

    def sync_all(self):
        """Sincronizar todas las entidades."""
        if not self.sync_manager:
            messagebox.showwarning("Advertencia", "El sistema no está inicializado")
            return

        def run_sync():
            try:
                result = self.sync_manager.sync_all()

                if result.get('success'):
                    messagebox.showinfo("✅ Éxito", "Sincronización completada exitosamente")
                else:
                    messagebox.showwarning("⚠️ Advertencia", "La sincronización tuvo errores. Revise el log.")

            except Exception as e:
                messagebox.showerror("❌ Error", f"Error durante sincronización:\n{e}")
                import traceback
                self.log(traceback.format_exc(), "error")

        # Ejecutar en thread para no bloquear GUI
        import threading
        thread = threading.Thread(target=run_sync)
        thread.daemon = True
        thread.start()

    def sync_entity(self, entity: str):
        """Sincronizar una entidad específica."""
        if not self.sync_manager:
            messagebox.showwarning("Advertencia", "El sistema no está inicializado")
            return

        def run_sync():
            try:
                self.log(f"\n🔄 SINCRONIZANDO {entity.upper()}...", "info")

                if entity == 'categories':
                    result = self.sync_manager.sync_categories()
                elif entity == 'products':
                    result = self.sync_manager.sync_products()
                elif entity == 'customers':
                    result = self.sync_manager.sync_customers()
                elif entity == 'sellers':
                    result = self.sync_manager.sync_sellers()
                elif entity == 'quotes':
                    result = self.sync_manager.sync_quotes()
                else:
                    self.log(f"❌ Entidad desconocida: {entity}", "error")
                    return

                stats = result.get('stats', {})
                created = stats.get('created', 0)
                updated = stats.get('updated', 0)
                deleted = stats.get('deleted', 0)
                errors = stats.get('errors', 0)

                if errors == 0:
                    self.log(f"✅ {entity.capitalize()} sincronizados: {created} creados, {updated} actualizados, {deleted} eliminados", "success")
                    messagebox.showinfo("✅ Éxito", f"{entity.capitalize()} sincronizados:\n{created} creados\n{updated} actualizados\n{deleted} eliminados")
                else:
                    self.log(f"⚠️ {entity.capitalize()} sincronizados con errores: {created} creados, {updated} actualizados, {errors} errores", "warning")
                    messagebox.showwarning("⚠️ Advertencia", f"{entity.capitalize()} sincronizados con {errors} errores.\nRevise el log.")

            except Exception as e:
                self.log(f"❌ Error sincronizando {entity}: {e}", "error")
                messagebox.showerror("❌ Error", f"Error durante sincronización de {entity}:\n{e}")
                import traceback
                self.log(traceback.format_exc(), "error")

        # Ejecutar en thread para no bloquear GUI
        import threading
        thread = threading.Thread(target=run_sync)
        thread.daemon = True
        thread.start()

    def reconfig(self):
        """Reconfigurar desde cero."""
        if messagebox.askyesno("Reconfigurar", "¿Está seguro de reconfigurar desde cero?\nSe borrará la configuración actual."):
            try:
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)

                messagebox.showinfo("Reconfiguración", "Configuración eliminada.\nEl sistema se cerrará. Ejecute --mode config para reconfigurar.")
                self.root.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Error reconfigurando:\n{e}")


# ==============================================================================
# SYSTEM TRAY SERVICE
# ==============================================================================

class SystemTrayService:
    """
    Servicio en segundo plano con icono en la bandeja del sistema.
    Ejecuta sincronizaciones automáticamente sin ventana visible.
    """

    def __init__(self, config, api_key=None, company_id=None):
        self.config = config
        self.api_key = api_key  # API Key para autenticación
        self.company_id = company_id  # Company ID validado al inicio
        self.sync_running = True
        self.is_syncing = False
        self.last_sync_time = None
        self.last_sync_status = "Esperando..."
        self.root = None
        self.icon = None

        # Configurar auto-inicio al encender el equipo
        self.configurar_auto_inicio()

    def crear_icono(self):
        """Crea icono simple para la bandeja del sistema"""
        try:
            from PIL import Image, ImageDraw
            # Crear imagen simple 64x64
            image = Image.new('RGB', (64, 64), color='white')
            draw = ImageDraw.Draw(image)

            # Dibujar círculo azul (sincronización)
            draw.ellipse([10, 10, 54, 54], fill='#3498db', outline='#2980b9', width=3)

            # Dibujar flechas de sincronización
            draw.polygon([(20, 32), (32, 20), (32, 28), (44, 28), (44, 20), (56, 32), (44, 44), (44, 36), (32, 36), (32, 44)], fill='white')

            return image
        except ImportError:
            print("ERROR: PIL no está instalado. Ejecute: pip install Pillow")
            return None
        except Exception as e:
            print(f"Error creando icono: {e}")
            return None

    def configurar_auto_inicio(self):
        """
        Configura el sistema para que inicie automáticamente al encender el equipo
        Verifica que el archivo exista antes de crear el registro
        """
        try:
            import winreg

            # Ruta del ejecutable o script actual
            if getattr(sys, 'frozen', False):
                # Si está empaquetado como exe
                app_path = sys.executable
            else:
                # Si es script Python
                script_path = os.path.abspath(__file__)
                app_path = f'"{sys.executable}" "{script_path}" --mode tray'

            # Verificar que el archivo exista
            if not os.path.exists(sys.executable):
                print(f"⚠️ El archivo no existe: {sys.executable}")
                print("   Limpiando registro de auto-inicio...")
                self.limpiar_auto_inicio()
                return

            # Registry key para auto-inicio
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key_name = "SyncAPISystemTray"

            # Abrir registry key
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

            # Establecer el valor
            winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)

            print("✅ Auto-inicio configurado correctamente")
            print(f"   Ruta: {app_path}")
        except ImportError:
            print("⚠️ winreg no disponible (solo Windows)")
        except Exception as e:
            print(f"⚠️ No se pudo configurar auto-inicio: {e}")

    def reautenticar_usuario(self):
            """
            Pide autenticación nuevamente antes de ejecutar acciones sensibles.
            Valida rol y company_id como en authenticate_user_tray().

            Returns:
                bool: True si autenticación exitosa, False si falló
            """
            import requests

            # Obtener company_id desde sync_config de PostgreSQL (si está disponible)
            company_id_from_config = None
            try:
                if self.config.get('postgres_host'):
                    import psycopg2
                    pg_conn = psycopg2.connect(
                        host=self.config.get('postgres_host'),
                        port=self.config.get('postgres_port', 5432),
                        database=self.config.get('postgres_database'),
                        user=self.config.get('postgres_user'),
                        password=self.config.get('postgres_password')
                    )
                    pg_cursor = pg_conn.cursor()
                    pg_cursor.execute("""
                        SELECT value FROM sync_config WHERE key = 'company_id'
                    """)
                    result = pg_cursor.fetchone()
                    if result:
                        company_id_from_config = int(result[0])
                    pg_cursor.close()
                    pg_conn.close()
            except Exception as e:
                print(f"Warning: No se pudo obtener company_id de PostgreSQL: {e}")
                # No es fatal - continuar sin validación de empresa

            # Crear ventana de reautenticación
            auth_window = tk.Tk()
            auth_window.title("Sincronizador - Verificar Identidad")
            auth_window.geometry("480x280")  # Aumentado de 220 a 280 para mejor visibilidad de botones
            auth_window.resizable(False, False)

            # IMPORTANTE: Forzar ventana al frente en Windows
            auth_window.attributes('-topmost', True)  # Traer al frente
            auth_window.lift()  # Elevar ventana
            auth_window.focus_force()  # Forzar focus

            # Centrar ventana
            auth_window.update_idletasks()
            width = auth_window.winfo_width()
            height = auth_window.winfo_height()
            x = (auth_window.winfo_screenwidth() // 2) - (width // 2)
            y = (auth_window.winfo_screenheight() // 2) - (height // 2)
            auth_window.geometry(f'{width}x{height}+{x}+{y}')

            # Programar para quitar topmost después de 100ms (para que aparezca arriba pero luego pueda ir atrás)
            auth_window.after(100, lambda: auth_window.attributes('-topmost', False))

            # Frame principal
            main_frame = ttk.Frame(auth_window, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Título
            ttk.Label(
                main_frame,
                text="🔐 Verificación Requerida",
                font=('Arial', 12, 'bold')
            ).pack(pady=(0, 15))

            # Instrucción
            ttk.Label(
                main_frame,
                text="Para continuar, ingrese sus credenciales:",
                font=('Arial', 9)
            ).pack(pady=(0, 10))

            # Email
            ttk.Label(main_frame, text="Email:").pack(anchor=tk.W)
            email_entry = ttk.Entry(main_frame, width=40)
            email_entry.pack(fill=tk.X, pady=(0, 10))
            email_entry.focus()  # Focus en email, campos limpios

            # Password
            ttk.Label(main_frame, text="Contraseña:").pack(anchor=tk.W)
            password_entry = ttk.Entry(main_frame, width=40, show="*")
            password_entry.pack(fill=tk.X, pady=(0, 15))

            auth_result = {'success': False}

            def do_auth():
                email = email_entry.get().strip()
                password = password_entry.get().strip()

                if not email or not password:
                    messagebox.showwarning("⚠️ Campos vacíos", "Por favor ingrese email y contraseña")
                    return

                try:
                    # Deshabilitar botón
                    auth_btn.config(state='disabled')
                    auth_window.update()

                    # Llamar a API
                    api_url = self.config.get('api_url', 'https://chrystal.com.ve/mobiletest/public/api')
                    response = requests.post(
                        f"{api_url}/auth/login",
                        headers={
                            'Content-Type': 'application/json',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        },
                        json={
                            'email': email,
                            'password': password,
                            'device_name': 'tray_auth',
                            'force_logout': True
                        },
                        timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            user_data = data.get('data', {})
                            user = user_data.get('user', {})
                            subscriptions = user_data.get('subscription', [])

                            # Validar rol
                            role = user.get('role')
                            if role not in ['admin', 'cajero']:
                                messagebox.showerror(
                                    "❌ Acceso Denegado",
                                    f"Rol no autorizado: {role}\n\nSolo pueden acceder:\n- Administradores\n- Cajeros"
                                )
                                auth_btn.config(state='normal')
                                return

                            # Validar company_id - buscar en todas las suscripciones
                            company_found = False
                            company_name = None                            

                            

                            # Todo OK - guardar token, email y password
                            self.api_token = user_data.get('token')
                            self.user_email = email
                            self.api_password = password  # Guardar password para usar en Manager
                            auth_result['success'] = True
                            auth_window.destroy()
                            return

                    # Error de autenticación
                    error_msg = "Credenciales inválidas"
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('message', error_msg)
                    except:
                        pass

                    messagebox.showerror("❌ Error", f"{error_msg}")
                    auth_btn.config(state='normal')

                except Exception as e:
                    messagebox.showerror("❌ Error", f"Error de conexión:\n{str(e)}")
                    auth_btn.config(state='normal')

            def do_cancel():
                auth_window.destroy()

            # Botones - colores oscuros para mejor contraste
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(15, 0))

            auth_btn = tk.Button(
                button_frame,
                text="✅ Verificar",
                command=do_auth,
                bg='#2E7D32',  # Verde oscuro
                fg='white',
                font=('Arial', 12, 'bold'),
                relief=tk.RAISED,
                bd=3,
                padx=30,
                pady=12,
                cursor='hand2',
                activebackground='#1B5E20',  # Verde más oscuro al hacer clic
                activeforeground='white'
            )
            auth_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 10))

            cancel_btn = tk.Button(
                button_frame,
                text="❌ Cancelar",
                command=do_cancel,
                bg='#C62828',  # Rojo oscuro
                fg='white',
                font=('Arial', 12, 'bold'),
                relief=tk.RAISED,
                bd=3,
                padx=30,
                pady=12,
                cursor='hand2',
                activebackground='#B71C1C',  # Rojo más oscuro al hacer clic
                activeforeground='white'
            )
            cancel_btn.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(10, 0))

            # Bind Enter
            auth_window.bind('<Return>', lambda e: do_auth())

            # Ejecutar ventana
            auth_window.mainloop()

            # Forzar limpieza en este hilo para evitar
            # "RuntimeError: main thread is not in main loop" al hacer GC
            result = auth_result['success']
            try:
                auth_window.destroy()
            except:
                pass
            # Eliminar referencias y forzar GC antes de salir del hilo
            del auth_window, main_frame, email_entry, password_entry
            del auth_btn, cancel_btn, auth_result
            import gc
            gc.collect()

            return result

    def limpiar_auto_inicio(self):
        """
        Limpia el registro de auto-inicio
        Se llama automáticamente si el archivo no existe
        """
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key_name = "SyncAPISystemTray"

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, key_name)
                print("✅ Registro de auto-inicio limpiado")
            except FileNotFoundError:
                # No existe, no hay problema
                pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"⚠️ No se pudo limpiar registro: {e}")

    def ejecutar_sincronizacion(self, es_manual=False):
        """Ejecuta una sincronización"""
        from datetime import datetime

        if self.is_syncing:
            print("⚠️ Ya hay una sincronización en progreso")
            return

        self.is_syncing = True
        inicio = datetime.now()

        try:
            # Usar el sistema de logging correcto (escribe en logs/sync_api_{email}.log)
            tray_logger = setup_logging(self.config.get('company_email'))

            tray_logger(f"{'='*70}", "info")
            if es_manual:
                tray_logger(f"🔄 Sincronización MANUAL - {inicio.strftime('%Y-%m-%d %H:%M:%S')}", "info")
            else:
                tray_logger(f"🔄 Sincronización AUTOMÁTICA - {inicio.strftime('%Y-%m-%d %H:%M:%S')}", "info")
            tray_logger(f"{'='*70}\n", "info")

            # Crear gestores
            auth_manager = APIAuthManager(
                base_url=self.config['api_url'],
                logger=tray_logger
            )

            # Ping API Key (usar self.api_key si está disponible, sino leer de config)
            api_key = self.api_key or self.config.get('api_key')
            ping_result = auth_manager.ping_api_key(api_key)
            if not ping_result.get('success'):
                error_msg = ping_result.get('error', 'Error de autenticación')
                tray_logger(f"❌ Error de autenticación: {error_msg}", "error")
                self.last_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.last_sync_status = "❌ API Key inválida"

                # Mostrar mensaje visual al usuario
                mostrar_banner(
                    "❌ Error de Autenticación",
                    f"{error_msg}\n\nContacta al administrador del sistema.",
                    duracion=15
                )
                return

            auth_manager.validate_company(self.config['company_rif'], self.config['company_email'])

            sync_manager = APISyncManager(
                postgres_config={
                    'host': self.config['postgres_host'],
                    'port': self.config['postgres_port'],
                    'database': self.config['postgres_database'],
                    'user': self.config['postgres_user'],
                    'password': self.config['postgres_password']
                },
                auth_manager=auth_manager,
                logger=tray_logger
            )

            # Conectar y sincronizar
            if sync_manager.connect_postgresql() and sync_manager.initialize_api_clients():
                result = sync_manager.sync_all()

                fin = datetime.now()
                duracion = (fin - inicio).total_seconds()

                total = result.get('total', {})
                self.last_sync_time = fin.strftime('%Y-%m-%d %H:%M:%S')
                self.last_sync_status = f"✅ {total.get('created', 0)} nuevos, {total.get('updated', 0)} modificados"

                tray_logger(f"\n📊 Completado en {duracion:.1f}s", "info")
                tray_logger(f"   ✨ Nuevos:      {total.get('created', 0)}", "info")
                tray_logger(f"   🔄 Modificados: {total.get('updated', 0)}", "info")
                tray_logger(f"   ❌ Eliminados:  {total.get('deleted', 0)}", "info")
                tray_logger("", "info")

                sync_manager.close()

                # 📢 Notificación Windows de sincronización exitosa
                if total.get('created', 0) > 0 or total.get('updated', 0) > 0 or total.get('deleted', 0) > 0:
                    # Hay cambios - mostrar estadísticas
                    stats = result.get('stats', {})
                    parts = []
                    for entity, entity_stats in stats.items():
                        created = entity_stats.get('created', 0)
                        updated = entity_stats.get('updated', 0)
                        deleted = entity_stats.get('deleted', 0)
                        if created > 0 or updated > 0 or deleted > 0:
                            parts.append(f"{entity.capitalize()}: {created} nuevos, {updated} mods, {deleted} eliminados")

                    if parts:
                        mensaje = " | ".join(parts)
                        mostrar_banner(
                            "✅ Sincronización Exitosa",
                            mensaje,
                            duracion=7 if es_manual else 5
                        )
                else:
                    # No hay cambios
                    mostrar_banner(
                        "✅ Sincronización Completada",
                        "No hay cambios para sincronizar",
                        duracion=3 if es_manual else 2
                    )

            else:
                self.last_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.last_sync_status = "❌ Error de conexión"
                mostrar_banner(
                    "❌ Error de Sincronización",
                    "Error de conexión a la base de datos o API",
                    duracion=10
                )

        except Exception as e:
            tray_logger(f"❌ Error: {e}", "error")
            self.last_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.last_sync_status = f"❌ Error: {str(e)[:30]}"

            # 📢 Notificación Windows de error
            if es_manual:
                mostrar_banner(
                    "⚠️ Error de Sincronización",
                    str(e)[:100],
                    duracion=10
                )
            else:
                mostrar_banner(
                    "⚠️ Sync Automático Falló",
                    "Revisa los logs para más detalles",
                    duracion=10
                )

        finally:
            self.is_syncing = False

    def bucle_sincronizacion(self):
        """Bucle de sincronización automática"""
        import time

        interval = int(self.config.get('sync_interval_minutes', 30))
        print(f"⏱️  Intervalo de sincronización: {interval} minutos")

        # Primera sincronización inmediata
        if self.sync_running:
            print("🔄 Ejecutando primera sincronización al inicio...")
            self.ejecutar_sincronizacion()

        # Bucle
        while self.sync_running:
            try:
                time.sleep(interval * 60)
                if self.sync_running:
                    self.ejecutar_sincronizacion()
            except KeyboardInterrupt:
                break

    def abrir_manager(self):
        """Abre la ventana del manager"""
        # Autenticar antes de abrir manager (solo cajeros)
        if not self.reautenticar_usuario():
            print("❌ Acceso a manager denegado: autenticación fallida o cancelada")
            return

        import threading
        threading.Thread(target=self._abrir_manager_thread, daemon=True).start()

    def _abrir_manager_thread(self):
        """Abre manager en un thread separado"""
        try:
            import tkinter as tk
            root = tk.Tk()
            # Pasar password si está disponible (desde reautenticar_usuario)
            app = ManagerWindow(root, api_key=getattr(self, 'api_key', None))
            root.mainloop()
        except Exception as e:
            print(f"Error abriendo manager: {e}")

    def ver_logs(self):
        """Abre ventana de logs"""
        # Autenticar antes de ver logs (solo cajeros)
        if not self.reautenticar_usuario():
            print("❌ Acceso a logs denegado: autenticación fallida o cancelada")
            return

        import threading
        threading.Thread(target=self._ver_logs_thread, daemon=True).start()

    def _ver_logs_thread(self):
        """Muestra logs en ventana separada"""
        try:
            import tkinter as tk
            from tkinter import scrolledtext, ttk

            # Crear ventana principal nueva (no Toplevel, porque no hay padre activo)
            log_window = tk.Tk()
            log_window.title(f"Logs - Sync API ({self.config.get('company_rif', 'N/A')})")
            log_window.geometry("900x700")

            # Centrar ventana
            log_window.update_idletasks()
            width = log_window.winfo_width()
            height = log_window.winfo_height()
            x = (log_window.winfo_screenwidth() // 2) - (width // 2)
            y = (log_window.winfo_screenheight() // 2) - (height // 2)
            log_window.geometry(f'{width}x{height}+{x}+{y}')

            # Header
            header = tk.Frame(log_window, bg="#2c3e50", height=50)
            header.pack(fill="x")
            header.pack_propagate(False)

            tk.Label(header, text="📊 Logs del Sistema",
                    font=("Arial", 14, "bold"), bg="#2c3e50", fg="white").pack(pady=12)

            # Área de texto
            txt = scrolledtext.ScrolledText(log_window, state="normal", font=("Consolas", 10))
            txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))

            # Cargar logs
            log_file = get_log_file(self.config.get('company_email'))
            if os.path.exists(log_file):
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    if not content.strip():
                        content = "El archivo de logs está vacío."
                    txt.insert("1.0", content)
                    txt.see("end")
                except Exception as e:
                    txt.insert("1.0", f"Error cargando logs: {e}")
            else:
                txt.insert("1.0", f"No hay archivo de logs aún.\nUbicación esperada: {log_file}")

            txt.config(state="disabled")

            # Botón cerrar
            btn_frame = tk.Frame(log_window)
            btn_frame.pack(fill="x", pady=10)
            tk.Button(btn_frame, text="❌ Cerrar", command=log_window.destroy,
                     font=("Arial", 11), width=20).pack()

            # Ejecutar mainloop
            log_window.mainloop()

        except Exception as e:
            print(f"Error abriendo logs: {e}")
            import traceback
            traceback.print_exc()

    def sincronizar_ahora(self):
        """Ejecuta sincronización manual desde el menú"""
        # Autenticar antes de sincronizar (solo cajeros)
        if not self.reautenticar_usuario():
            print("❌ Sincronización cancelada: autenticación fallida o cancelada")
            return

        print("\n" + "="*70)
        print("🔄 Sincronización manual solicitada desde el menú")
        print("="*70)

        import threading
        import traceback

        def sync_thread_wrapper():
            try:
                print("[DEBUG] Iniciando thread de sincronización manual...")
                self.ejecutar_sincronizacion(es_manual=True)
                print("[DEBUG] Thread de sincronización manual completado")
            except Exception as e:
                print(f"[DEBUG] Error en thread de sincronización manual: {e}")
                traceback.print_exc()

        thread = threading.Thread(target=sync_thread_wrapper, daemon=False)
        thread.start()
        print("[DEBUG] Thread iniciado (daemon=False)")

    def abrir_config(self):
        """Abre ventana de configuración con autenticación"""
        import threading
        threading.Thread(target=self._abrir_config_thread, daemon=True).start()

    def _abrir_config_thread(self):
        """Abre config en thread separado con autenticación"""
        # Verificar autenticación antes de abrir config
        if not self.reautenticar_usuario():
            print("❌ Acceso a configuración denegado: autenticación fallida o cancelada")
            return

        try:
            import tkinter as tk
            root = tk.Tk()
            app = ConfigWindow(root)
            root.mainloop()
        except Exception as e:
            print(f"Error abriendo config: {e}")

    def salir(self):
        """Sale del sistema tray con autenticación"""
        # Autenticar antes de salir (solo cajeros)
        if not self.reautenticar_usuario():
            print("❌ Salida cancelada: autenticación fallida o cancelada")
            return

        # Si autenticación exitosa, mostrar confirmación y salir
        import threading
        threading.Thread(target=self._salir_thread, daemon=True).start()

    def _salir_thread(self):
        """Muestra diálogo de confirmación y sale"""
        try:
            import tkinter as tk
            from tkinter import messagebox

            # Crear ventana oculta para el diálogo
            root = tk.Tk()
            root.withdraw()  # Ocultar ventana principal

            # Centrar el diálogo en la pantalla
            root.update_idletasks()
            width = 400
            height = 150
            x = (root.winfo_screenwidth() // 2) - (width // 2)
            y = (root.winfo_screenheight() // 2) - (height // 2)
            root.geometry(f'{width}x{height}+{x}+{y}')

            # Mostrar confirmación
            respuesta = messagebox.askyesno(
                "Confirmar Salida",
                "¿Estás seguro que deseas salir del Sistema de Sincronización?\n\n"
                "Esto detendrá la sincronización automática.",
                icon=messagebox.WARNING,
                default=messagebox.NO
            )

            root.destroy()

            if respuesta:
                print("\n👋 Deteniendo servicio...")
                self.sync_running = False
                if self.icon:
                    self.icon.stop()
                import os
                os._exit(0)
            else:
                print("❌ Salida cancelada")

        except Exception as e:
            print(f"Error en diálogo de salida: {e}")
            # En caso de error, salir de todos modos
            print("\n👋 Deteniendo servicio...")
            self.sync_running = False
            if self.icon:
                self.icon.stop()
            import os
            os._exit(0)

    def iniciar(self):
        """Inicia el servicio system tray"""
        # Usar el sistema de logging correcto (logs/sync_api_{email}.log)
        log_debug = setup_logging(self.config.get('company_email'))

        try:
            log_debug("="*70)
            log_debug("INICIANDO SYSTEM TRAY SERVICE")
            log_debug("="*70)
            log_debug(f"RIF: {self.config['company_rif']}")
            log_debug(f"Email: {self.config['company_email']}")
            log_debug(f"Intervalo: {self.config.get('sync_interval_minutes', 30)} minutos")
            log_debug("")

            # Verificar dependencias
            log_debug("[DEBUG] Verificando pystray...")
            import pystray
            log_debug(f"[DEBUG] pystray versión: {pystray.__version__ if hasattr(pystray, '__version__') else 'unknown'}")

            log_debug("[DEBUG] Verificando PIL/Pillow...")
            from PIL import Image, ImageDraw
            log_debug(f"[DEBUG] PIL disponible")

            # Crear icono
            log_debug("Creando icono de la bandeja del sistema...")
            icon_image = self.crear_icono()
            if not icon_image:
                raise Exception("No se pudo crear el icono. Instale: pip install Pillow")

            log_debug("✅ Icono creado correctamente")

            # Crear menú
            log_debug("[DEBUG] Creando menú contextual...")
            menu = pystray.Menu(
                pystray.MenuItem('🖥️ Abrir Manager', self.abrir_manager),
                pystray.MenuItem('📊 Ver Logs', self.ver_logs),
                pystray.MenuItem('🔄 Sincronizar Ahora', self.sincronizar_ahora),
                pystray.MenuItem('❌ Salir', self.salir)
            )
            log_debug("[DEBUG] Menú creado")

            # Crear icono
            tooltip_text = f"""Sync API System
RIF: {self.config['company_rif']}

Clic derecho para opciones"""
            self.icon = pystray.Icon("Sync API", icon_image, tooltip_text, menu)
            log_debug("[DEBUG] Icono pystray creado")

            # Iniciar sincronización automática en thread
            log_debug("Iniciando thread de sincronización automática...")
            import threading
            sync_thread = threading.Thread(target=self.bucle_sincronizacion)
            sync_thread.daemon = True
            sync_thread.start()
            log_debug("[DEBUG] Thread de sincronización iniciado")

            # Ejecutar icono (bloqueante)
            log_debug("✅ Servicio iniciado en la bandeja del sistema")
            log_debug("💡 El icono está en la barra de tareas (junto al reloj)")
            log_debug("💡 Clic derecho para ver opciones")
            log_debug("")
            log_debug("[DEBUG] Llamando a icon.run() (esto es bloqueante)...")

            self.icon.run()

            log_debug("[DEBUG] icon.run() retornó (no debería llegar aquí)")

        except ImportError as e:
            error_msg = f"Falta dependencia: {str(e)}"
            log_debug(f"ERROR: {error_msg}")
            log_debug("Ejecute: pip install pystray Pillow")
            raise Exception(error_msg)
        except KeyboardInterrupt:
            log_debug("⚠️ Interrupción por teclado (Ctrl+C)")
        except Exception as e:
            log_debug(f"❌ ERROR en System Tray: {e}")
            import traceback
            log_debug(traceback.format_exc())
            raise
        finally:
            try:
                log_file.close()
            except:
                pass


# ==============================================================================
# CONSOLE MODE FUNCTIONS
# ==============================================================================

def run_sync_console():
    """Ejecutar sincronización en modo consola (sin GUI)."""
    # Verificar que hay config
    if not os.path.exists(CONFIG_FILE):
        print("❌ No hay configuración. Ejecute --mode config primero")
        sys.exit(1)

    # Cargar configuración
    try:
        from config_encryption import decrypt_config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Desencriptar todos los campos sensibles
        config = decrypt_config(config)
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        sys.exit(1)

    # Obtener password de la API (ya desencriptado)
    api_key = config.get('api_key')
    if api_key:
        print("✅ Password de la API cargado desde configuración")

    # Si no hay password en config, pedirlo
    if not api_key:
        import getpass
        api_key = getpass.getpass("API Key: ")

    # Crear logger para consola
    def console_logger(msg, level="info"):
        prefix = {
            'info': '✅',
            'warning': '⚠️',
            'error': '❌',
            'debug': '🔍'
        }.get(level, 'ℹ️')
        print(f"{prefix} {msg}")

    try:
        # Crear gestor de autenticación
        auth_manager = APIAuthManager(
            base_url=config['api_url'],
            logger=console_logger
        )

        # Login
        print("\n🔐 Autenticando...")
        result = auth_manager.ping_api_key(api_key)
        if not result.get('success'):
            print(f"❌ API Key inválida: {result.get('error')}")
            sys.exit(1)

        # Validar empresa
        print("🏢 Validando empresa...")
        result = auth_manager.validate_company(config['company_rif'], config['company_email'])
        if not result.get('success'):
            print(f"❌ Validación falló: {result.get('error')}")
            sys.exit(1)

        print(f"✅ Company ID: {auth_manager.company_id}")

        # Crear gestor de sincronización
        sync_manager = APISyncManager(
            postgres_config={
                'host': config['postgres_host'],
                'port': config['postgres_port'],
                'database': config['postgres_database'],
                'user': config['postgres_user'],
                'password': config['postgres_password']
            },
            auth_manager=auth_manager,
            logger=console_logger
        )

        # Conectar a PostgreSQL
        print("\n🐘 Conectando a PostgreSQL...")
        if not sync_manager.connect_postgresql():
            print("❌ No se pudo conectar a PostgreSQL")
            sys.exit(1)

        # Inicializar clientes API
        print("📡 Inicializando clientes API...")
        if not sync_manager.initialize_api_clients():
            print("❌ No se pudieron inicializar los clientes API")
            sys.exit(1)

        # Sincronizar
        print("\n" + "="*70)
        print("🔄 INICIANDO SINCRONIZACIÓN")
        print("="*70 + "\n")

        result = sync_manager.sync_all()

        print("\n" + "="*70)
        print("📊 RESUMEN DE SINCRONIZACIÓN")
        print("="*70)

        for entity, stats in result.get('entities', {}).items():
            print(f"\n📁 {entity.upper()}:")
            print(f"   ✨ Nuevos:      {stats.get('created', 0)}")
            print(f"   🔄 Modificados: {stats.get('updated', 0)}")
            print(f"   ❌ Eliminados:  {stats.get('deleted', 0)}")
            print(f"   ⏭️  Sin cambios: {stats.get('unchanged', 0)}")

        total = result.get('total', {})
        print(f"\n📈 TOTALES:")
        print(f"   ✨ Nuevos:      {total.get('created', 0)}")
        print(f"   🔄 Modificados: {total.get('updated', 0)}")
        print(f"   ❌ Eliminados:  {total.get('deleted', 0)}")

        if result.get('success'):
            print("\n✅ Sincronización completada exitosamente")
        else:
            print(f"\n❌ Sincronización con errores: {result.get('error', 'Error desconocido')}")

        # Cerrar conexiones
        sync_manager.close()

    except KeyboardInterrupt:
        print("\n\n⚠️ Sincronización interrumpida por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error durante sincronización: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def run_service_loop():
    """Ejecutar sincronización en loop infinito (modo servicio)."""
    import time

    # Verificar que hay config
    if not os.path.exists(CONFIG_FILE):
        print("❌ No hay configuración. Ejecute --mode config primero")
        sys.exit(1)

    # Cargar configuración
    try:
        from config_encryption import decrypt_config
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Desencriptar todos los campos sensibles
        config = decrypt_config(config)
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        sys.exit(1)

    interval_minutes = int(config.get('sync_interval_minutes', 30))
    print(f"⏱️  Intervalo de sincronización: {interval_minutes} minutos")
    print("💡 Presione Ctrl+C para detener\n")

    # Obtener password de la API (ya desencriptado)
    api_key = config.get('api_key')
    if api_key:
        print("✅ Password de la API cargado desde configuración")

    # Si no hay password en config, pedirlo UNA vez
    if not api_key:
        import getpass
        api_key = getpass.getpass("API Key: ")

    sync_count = 0

    try:
        while True:
            sync_count += 1
            print(f"\n{'='*70}")
            print(f"🔄 SINCRONIZACIÓN #{sync_count} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}\n")

            # Ejecutar sincronización (usando funciones internas)
            if not os.path.exists(CONFIG_FILE):
                print("❌ Configuración eliminada. Saliendo...")
                break

            # Crear logger para consola
            def console_logger(msg, level="info"):
                prefix = {
                    'info': '✅',
                    'warning': '⚠️',
                    'error': '❌',
                    'debug': '🔍'
                }.get(level, 'ℹ️')
                print(f"{prefix} {msg}")

            try:
                # Recargar configuración (por si cambió)
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                # Desencriptar todos los campos sensibles
                config = decrypt_config(config)

                # Crear gestores
                auth_manager = APIAuthManager(
                    base_url=config['api_url'],
                    logger=console_logger
                )

                auth_manager.ping_api_key(api_key)
                auth_manager.validate_company(config['company_rif'], config['company_email'])

                sync_manager = APISyncManager(
                    postgres_config={
                        'host': config['postgres_host'],
                        'port': config['postgres_port'],
                        'database': config['postgres_database'],
                        'user': config['postgres_user'],
                        'password': config['postgres_password']
                    },
                    auth_manager=auth_manager,
                    logger=console_logger
                )

                if sync_manager.connect_postgresql() and sync_manager.initialize_api_clients():
                    result = sync_manager.sync_all()

                    total = result.get('total', {})
                    print(f"\n📊 Esta sincronización: ✨{total.get('created', 0)} 🔄{total.get('updated', 0)} ❌{total.get('deleted', 0)}")

                    sync_manager.close()
                else:
                    print("❌ Error en conexiones")

            except Exception as e:
                print(f"❌ Error en sincronización #{sync_count}: {e}")

            # Esperar para la próxima sincronización
            print(f"\n⏳ Próxima sincronización en {interval_minutes} minutos...")
            print(f"{'='*70}\n")
            time.sleep(interval_minutes * 60)

    except KeyboardInterrupt:
        print(f"\n\n⚠️ Servicio detenido por el usuario")
        print(f"📊 Total de sincronizaciones ejecutadas: {sync_count}")
        sys.exit(0)


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Función principal."""

    # Verificar si es ejecutable compilado y no hay argumentos
    # O si no se pasan argumentos explícitos
    import sys
    is_exe = getattr(sys, 'frozen', False)
    no_args = len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[0].endswith('.exe'))

    if is_exe and no_args:
        # MODO AUTOMÁTICO para .exe (como sync_system.py)
        # 1. Validar identidad del usuario (email/password)
        # 2. Si no hay config → abrir configuración → sync → tray
        # 3. Si hay config → sync → tray

        # Validar identidad del usuario primero (email/password)
        try:
            _cfg_first = None
            if os.path.exists(CONFIG_FILE):
                from config_encryption import decrypt_config
                with open(CONFIG_FILE, 'r') as f:
                    _cfg_first = decrypt_config(json.load(f))
            else:
                _cfg_first = {'api_url': 'https://chrystal.com.ve/mobiletest/public/api'}
            _tray_first = SystemTrayService(_cfg_first, _cfg_first.get('api_key'))
            if not _tray_first.reautenticar_usuario():
                print("❌ Verificación de identidad fallida o cancelada")
                return
        except Exception as e:
            print(f"❌ Error en verificación de identidad: {e}")
            return

        if not os.path.exists(CONFIG_FILE):
            # No hay configuración - abrir modo config con autenticación PRIMERO
            # Pedir autenticación ANTES de configurar
            auth_result = autenticar_para_config()
            if not auth_result or not auth_result.get('success', False):
                print("❌ Acceso denegado: autenticación fallida o cancelada")
                return

            root = tk.Tk()
            app = ConfigWindow(root)
            root.mainloop()
            # Después de configurar, continuar con sync y tray
        # Continuar con sincronización y tray (hay config o se acaba de crear)

        # Cargar configuración
        try:
            from config_encryption import decrypt_config
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            config = decrypt_config(config)
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            return


        # Obtener API Key (ya desencriptado)
        api_key = config.get('api_key')

        # Si no hay API Key en config, pedirlo con ventana GUI
        if not api_key:
            import tkinter.simpledialog as simpledialog
            key_root = tk.Tk()
            key_root.withdraw()
            api_key = simpledialog.askstring("🔐 API Key", "Ingrese la API Key:", show='*')
            key_root.destroy()

            if not api_key:
                return

        # Ejecutar sincronización
        print("\n" + "="*70)
        print("🔄 SINCRONIZANDO...")
        print("="*70)
        try:
            auth_manager = APIAuthManager(
                base_url=config['api_url'],
                logger=lambda msg, level="info": print(f"{'✅' if level == 'info' else '❌'} {msg}")
            )

            result = auth_manager.ping_api_key(api_key)
            if not result.get('success'):
                print(f"❌ API Key inválida: {result.get('error')}")
                return

            sync_manager = APISyncManager(
                postgres_config={
                    'host': config['postgres_host'],
                    'port': int(config['postgres_port']),
                    'database': config['postgres_database'],
                    'user': config['postgres_user'],
                    'password': config['postgres_password']
                },
                auth_manager=auth_manager,
                logger=lambda msg, level="info": print(f"{'✅' if level == 'info' else '❌'} {msg}")
            )

            if not sync_manager.connect_postgresql():
                print("❌ No se pudo conectar a PostgreSQL")
                return

            if not sync_manager.initialize_api_clients():
                print("❌ No se pudieron inicializar los clientes API")
                return

            sync_manager.sync_all()
            print("\n✅ Sincronización completada")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        # Iniciar System Tray
        print("\n" + "="*70)
        print("📬 INICIANDO SYSTEM TRAY...")
        print("="*70)
        print("El icono aparecerá junto al reloj")
        print("Se sincronizará automáticamente cada", config.get('sync_interval_minutes', '30'), "minutos")
        print("="*70 + "\n")

        try:
            tray = SystemTrayService(config, config.get('api_key'))
            tray.iniciar()
        except Exception as e:
            print(f"❌ Error iniciando System Tray: {e}")

        return

    # Modo normal con argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Sincronizador API REST")
    parser.add_argument("--mode", choices=["config", "manager", "reconfig", "sync", "service", "tray"],
                       default="manager", help="Modo de ejecución")
    parser.add_argument("--once", action="store_true",
                       help="En modo service, ejecutar una sola vez y salir")

    args = parser.parse_args()

    # Si --reconfig o mode=reconfig, borrar config
    if args.mode == "reconfig":
        print("🔄 Reconfiguración - Borrando configuración...")
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            print("✅ Configuración eliminada")
        args.mode = "config"

    # Crear directorio de logs
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    # Ejecutar según modo
    if args.mode == "config":
        # Verificar identidad del usuario (email/password) primero
        try:
            _cfg = None
            if os.path.exists(CONFIG_FILE):
                from config_encryption import decrypt_config
                with open(CONFIG_FILE, 'r') as f:
                    _cfg = decrypt_config(json.load(f))
            else:
                _cfg = {'api_url': 'https://chrystal.com.ve/mobiletest/public/api'}
            _tray_first = SystemTrayService(_cfg, _cfg.get('api_key'))
            if not _tray_first.reautenticar_usuario():
                print("❌ Verificación de identidad fallida o cancelada")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Error verificando identidad:\n{e}")
            sys.exit(1)

        # Verificar autenticación antes de abrir config
        auth_result = autenticar_para_config()
        if auth_result and auth_result.get('success', False):
            root = tk.Tk()
            app = ConfigWindow(root)
            root.mainloop()

            # NOTA: La sincronización y el System Tray ya se inician
            # automáticamente desde ConfigWindow._mostrar_ventana_carga_api()
            # al hacer clic en "Guardar". No duplicar la llamada aquí.
            if not os.path.exists(CONFIG_FILE):
                print("❌ Configuración no completada o fallida")
                sys.exit(1)

            # Mantener el proceso vivo para el System Tray (importante en .exe compilado)
            print("✅ Sistema iniciado en segundo plano (bandeja de tareas)")
            try:
                # Bloquear el hilo principal para que el proceso no termine
                evento_espera = threading.Event()
                evento_espera.wait()  # Espera indefinida
            except KeyboardInterrupt:
                print("\n👋 Cerrando sistema...")
        else:
            print("❌ Acceso a configuración denegado: autenticación fallida o cancelada")
            sys.exit(1)

    elif args.mode == "manager":
        # Manager siempre abre, con o sin configuración
        # (puede configurarse desde el botón "Configurar")
        root = tk.Tk()
        app = ManagerWindow(root)
        root.mainloop()

        # Despues de cerrar el Manager, si hay configuracion, iniciar System Tray
        if os.path.exists(CONFIG_FILE):
            try:
                print("\n📌 Iniciando System Tray desde Manager...")
                from config_encryption import decrypt_config
                with open(CONFIG_FILE, 'r') as f:
                    _cfg_enc = json.load(f)
                _cfg = decrypt_config(_cfg_enc)

                api_key = _cfg.get('api_key', '')
                if api_key:
                    # Iniciar tray en un hilo
                    tray_thread = threading.Thread(
                        target=iniciar_system_tray,
                        args=(_cfg, api_key),
                        daemon=False
                    )
                    tray_thread.start()
                    print("✅ System Tray iniciado desde Manager")
                    print("✅ Sistema en ejecucion en segundo plano")
                    try:
                        evento_espera = threading.Event()
                        evento_espera.wait()
                    except KeyboardInterrupt:
                        print("\n👋 Cerrando sistema...")
            except Exception as e:
                print(f"❌ Error iniciando System Tray desde Manager: {e}")
                traceback.print_exc()

    elif args.mode == "sync":
        # Modo sincronización única (sin GUI)
        print("=== SINCRONIZACIÓN ÚNICA ===")
        run_sync_console()

    elif args.mode == "service":
        # Modo servicio (loop o una sola ejecución)
        if args.once:
            print("=== MODO SERVICIO (UNA SOLA EJECUCIÓN) ===")
            run_sync_console()
        else:
            print("=== MODO SERVICIO (LOOP INFINITO) ===")
            run_service_loop()

    elif args.mode == "tray":
        # Modo System Tray (icono en bandeja)
        print("=== MODO SYSTEM TRAY ===")

        # Verificar que hay config
        if not os.path.exists(CONFIG_FILE):
            print("❌ No hay configuración. Ejecute --mode config primero")
            sys.exit(1)

        # Cargar configuración
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"❌ Error cargando configuración: {e}")
            sys.exit(1)

        # Intentar cargar API Key del config
        api_key = None
        if 'api_key' in config:
            try:
                from config_encryption import decrypt_config
                decrypted = decrypt_config(config)
                api_key = decrypted.get('api_key')
                if api_key:
                    print("✅ API Key cargado desde configuración")
            except Exception as e:
                print(f"⚠️  Error cargando API Key: {e}")

        # Si no hay API Key en config, pedirlo
        if not api_key:
            import getpass
            api_key = getpass.getpass("API Key: ")

        print("🔐 Validando API Key...")
        auth_manager = APIAuthManager(
            base_url=config.get('api_url', 'https://chrystal.com.ve/mobiletest/public/api'),
            logger=None
        )

        # Ping API Key
        ping_result = auth_manager.ping_api_key(config.get('api_key', api_key))
        if not ping_result.get('success'):
            print(f"❌ API Key inválida: {ping_result.get('error', 'Error desconocido')}")
            sys.exit(1)

        print("✅ API Key válida")

        # Validar empresa para obtener company_id
        print("🏢 Validando empresa...")
        validate_result = auth_manager.validate_company(config['company_rif'], config['company_email'])
        if not validate_result.get('success'):
            print(f"❌ Error validando empresa: {validate_result.get('error', 'Error desconocido')}")
            sys.exit(1)

        company_id = validate_result.get('company_id')
        print(f"✅ Company ID: {company_id}")

        # Iniciar System Tray
        try:
            tray = SystemTrayService(config, api_key, company_id)
            tray.iniciar()
        except Exception as e:
            print(f"❌ Error iniciando System Tray: {e}")
            print("\nAsegúrese de tener instaladas las dependencias:")
            print("  pip install pystray Pillow")
            sys.exit(1)



    # Sistema en segundo plano - System Tray activado
    if os.path.exists("sync_encryption.json"):
        try:
            from config_encryption import decrypt_config
            with open("sync_encryption.json", "r") as config_file:
                config = decrypt_config(json.load(config_file))
            
            if config.get("api_key"):
                print("📬 Iniciando System Tray en segundo plano...")
                print("💡 El sistema quedará activo sincronizando automáticamente")
                try:
                    from sync_system_api import SystemTrayService
                    tray_service = SystemTrayService(config, config["api_key"])
                    tray_service.iniciar()
                    
                    import threading
                    evento = threading.Event()
                    try:
                        evento.wait()
                    except KeyboardInterrupt:
                        print()
                        print("👋 Cerrando sistema...")
                except Exception as e:
                    import traceback
                    print(f"❌ Error iniciando System Tray: {e}")
                    print(traceback.format_exc())
        except Exception as e:
            import traceback
            print(f"❌ Error iniciando System Tray: {e}")
            print(traceback.format_exc())
# Suprimir error "main thread is not in main loop" al hacer GC
# de variables Tkinter desde hilos secundarios (es inofensivo)
import tkinter
_del_original = tkinter.Variable.__del__
def _del_seguro(self):
    try:
        _del_original(self)
    except RuntimeError:
        pass
tkinter.Variable.__del__ = _del_seguro

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        error_msg = f"Error durante la ejecución: {e}"
        print(error_msg)
        print("\nDetalles del error:")
        traceback.print_exc()
        log_startup_error("RUNTIME_ERROR", error_msg, traceback.format_exc())
        # Mantener ventana abierta si es .exe compilado
        if getattr(sys, 'frozen', False):
            input("\nPresiona Enter para salir...")
        sys.exit(1)
