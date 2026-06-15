#!/usr/bin/env python3
# PYVER: Python 3.9+
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

from __future__ import annotations

# ========================================
# VERSIÓN DE LA APLICACIÓN
# ========================================
APP_VERSION = "1.0.0"

# ========================================
# DIAGNÓSTICO DE INICIO (antes de cualquier import)
# ========================================
import sys
import os
import traceback

# Forzar UTF-8 en stdout para evitar UnicodeEncodeError con emojis en Windows (cp1252)
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

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
                            os.path.join(script_dir, "logo.ico"),  # Nuevo logo
                            os.path.join(script_dir, "logo.png"),
                            os.path.join(script_dir, "icon.ico"),  # Legacy
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
                        icon_path = None

                # Usar threaded=True para evitar errores de WPARAM
                # cuando se ejecuta desde un thread separado
                print(f"[NOTIFICACION] Llamando toast.show_toast (duration={duracion})...")

                # Solo pasar icon_path si existe y es válido
                # Si no existe, win10toast usará el icono por defecto de Windows
                if icon_path and os.path.exists(icon_path):
                    toast.show_toast(
                        titulo,
                        mensaje,
                        duration=duracion,
                        icon_path=icon_path,
                        threaded=True,
                    )
                else:
                    print("[NOTIFICACION] Sin icono, usando icono por defecto de Windows")
                    toast.show_toast(
                        titulo,
                        mensaje,
                        duration=duracion,
                        threaded=True,
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


def set_window_favicon(window):
    """
    Establecer el favicon (icono) para una ventana Tkinter.

    Args:
        window: Ventana Tkinter (root o Toplevel)
    """
    try:
        # Obtener directorio del script
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Buscar logo.ico en varios lugares
        possible_paths = [
            os.path.join(script_dir, 'logo.ico'),
            os.path.join(script_dir, 'windows_api', 'logo.ico'),
        ]

        # Si está empaquetado como exe, buscar en directorio del ejecutable
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            possible_paths.insert(0, os.path.join(exe_dir, 'logo.ico'))

        # Buscar el primer icono que exista
        icon_path = None
        for path in possible_paths:
            if os.path.exists(path):
                icon_path = path
                print(f"[DEBUG] Icono encontrado: {icon_path}")
                break

        # Establecer icono si se encontró
        if icon_path:
            window.iconbitmap(icon_path)
            print(f"[DEBUG] Iconbitmap aplicado: {icon_path}")
        else:
            print(f"[WARNING] No se encontró logo.ico en: {possible_paths}")
    except Exception as e:
        # Mostrar error para depuración
        print(f"[ERROR] Error en set_window_favicon: {e}")
        import traceback
        traceback.print_exc()


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


def _get_chrystal_version(postgres_config: dict) -> str | None:
    """Obtiene la versión del sistema Chrystal desde PostgreSQL.

    Consulta la tabla system_version, columna system_vesion.

    Args:
        postgres_config: Diccionario con credenciales de PostgreSQL

    Returns:
        Versión del sistema como string, o None si no se puede obtener
    """
    try:
        import psycopg2
        conn = psycopg2.connect(**postgres_config, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT system_vesion FROM system_version LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            return str(row[0])
    except Exception:
        pass
    return None


def _get_hdd_serial() -> str | None:
    """Obtiene el serial único del disco duro (no cambia al formatear).

    En Windows usa wmic para obtener el serial físico del disco.
    En Linux/macOS lee /etc/machine-id como fallback.

    Returns:
        Serial del disco como string, o None si no se puede obtener
    """
    import sys as _sys
    import subprocess as _sp
    try:
        if _sys.platform == 'win32':
            result = _sp.run(
                'wmic diskdrive get serialnumber',
                capture_output=True, text=True, shell=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                if len(lines) > 1:
                    return lines[-1]
        else:
            with open('/etc/machine-id') as _f:
                return _f.read().strip()
    except Exception:
        pass
    return None


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
    def ping_api_key(self, api_key: str, chrystal_version: str | None = None) -> dict:
        """
        Validar API Key mediante endpoint ping y obtener info de la empresa.

        Args:
            api_key: API Key del sistema Chrystal
            chrystal_version: Versión del sistema Chrystal desde PostgreSQL (opcional)

        Returns:
            Dict con success, company_id, company_data, rif, email
        """
        try:
            import requests

            self._log("🔑 Validando API Key...")

            _hdd_serial_ping = _get_hdd_serial()
            _ping_headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'X-App-Version': APP_VERSION,
                'X-App-Type': 'sincronizador',
                'X-App-Type-Chrystal': 'chrystal',
                'X-Device-UUID': _hdd_serial_ping or 'unknown',
                'X-App-ApiKey': api_key,
            }
            # Solo enviar X-App-Version-Chrystal si tenemos la versión real desde PostgreSQL
            if chrystal_version:
                _ping_headers['X-App-Version-Chrystal'] = chrystal_version

            response = requests.get(
                f"{self.base_url}/sync-client/ping",
                headers=_ping_headers,
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

            # Manejo específico para 403 (acceso bloqueado/suspendido)
            if response.status_code == 403:
                try:
                    error_data = response.json()
                    api_message = error_data.get('message', '')
                    self._log(f"❌ Acceso denegado (403): {api_message}", "error")
                    return {
                        'success': False,
                        'error': api_message or 'Acceso suspendido. Contacte a su proveedor.'
                    }
                except:
                    return {
                        'success': False,
                        'error': 'Acceso suspendido. Contacte a su proveedor para reactivar el servicio.'
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



    def validate_company(self, rif: str, email: str, chrystal_version: str | None = None) -> dict:
        """
        Validar empresa y obtener company_id.

        Args:
            rif: RIF de la empresa
            email: Email de la empresa
            chrystal_version: Versión del sistema Chrystal (de tabla system_version)

        Returns:
            Dict con success, company_id, company_data
        """
        try:
            import requests

            self._log(f"🏢 Validando empresa: {rif}")

            if not self.api_key:
                return {'success': False, 'error': 'No hay API Key configurada.'}

            _hdd_serial = _get_hdd_serial()
            _json_body = {
                'rif': rif,
                'email': email,
                'uuid_hard_drive': _hdd_serial or 'unknown',
                'app_version_chrystal': chrystal_version or APP_VERSION,
            }

            response = requests.post(
                f"{self.base_url}/sync-client/company/validate",
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'X-App-Version': APP_VERSION,
                    'X-App-Type': 'sincronizador',
                    'X-App-Type-Chrystal': 'chrystal',
                    'X-App-Version-Chrystal': APP_VERSION,
                    'X-Device-UUID': _hdd_serial or 'unknown',
                    'X-App-ApiKey': self.api_key,
                },
                json=_json_body,
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

            # VERIFICAR: ¿Los triggers ya existen? Si sí, saltar creación para evitar bloqueos en Win11
            print("[DEBUG] Verificando si triggers ya existen...")
            try:
                # Verificar que la conexión existe antes de consultar
                if not self.pg_conn or not self.pg_cursor:
                    print("[DEBUG] No hay conexión PostgreSQL, creando triggers sin verificación...")
                    self._crear_triggers_desde_sql()
                else:
                    triggers_check = """
                        SELECT COUNT(*) FROM information_schema.triggers
                        WHERE trigger_name LIKE 'tr_%_sync_hashes';
                    """
                    self.pg_cursor.execute(triggers_check)
                    trigger_count = self.pg_cursor.fetchone()[0]
                    print(f"[DEBUG] Triggers existentes: {trigger_count}")

                    # Si hay al menos 4 triggers principales, asumir que ya están todos creados
                    if trigger_count >= 4:
                        print("[DEBUG] ✅ Triggers ya existen ({trigger_count}), saltando creación para evitar bloqueos")
                        print("[DEBUG] Triggers creados/actualizados (skipped - already exist)")
                    else:
                        print("[DEBUG] Creando/actualizando triggers...")
                        self._crear_triggers_desde_sql()
                        print("[DEBUG] Triggers creados/actualizados")
            except Exception as check_error:
                print(f"[DEBUG] Error verificando triggers: {check_error}")
                import traceback
                traceback.print_exc()
                print("[DEBUG] Intentando crear triggers de todas formas...")
                try:
                    self._crear_triggers_desde_sql()
                    print("[DEBUG] Triggers creados/actualizados")
                except Exception as create_error:
                    print(f"[ERROR] Error crítico creando triggers: {create_error}")
                    import traceback
                    traceback.print_exc()
                    # NO propagar el error para no cerrar el sistema

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
                SET pending_sync = TRUE, deleted_at = NULL, updated_at = NOW()
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
                SET pending_sync = TRUE, deleted_at = NULL, updated_at = NOW()
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
            deleted_at = NULL,
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
-- PRODUCTS IMAGE - Trigger específico para detectar cambios en product_image
-- ===========================================================================

-- Función para marcar sync cuando cambia product_image (INSERT, UPDATE, DELETE)
CREATE OR REPLACE FUNCTION trigger_mark_product_image_updated()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
    v_product_code VARCHAR(50);
BEGIN
    -- Obtener el company_id desde sync_config
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    -- Si no existe, usar 1 como fallback
    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    -- Determinar el código del producto según la operación
    -- INSERT/UPDATE: usar NEW.main_code
    -- DELETE: usar OLD.main_code (porque NEW no existe en DELETE)
    IF TG_OP = 'DELETE' THEN
        v_product_code := OLD.main_code;
    ELSE
        v_product_code := NEW.main_code;
    END IF;

    -- Verificar si ya existe el registro
    SELECT COUNT(*) INTO v_exists
    FROM sync_hashes
    WHERE table_name = 'products'
    AND record_key = v_product_code
    AND company_id = v_company_id;

    -- Marcar como pending_sync
    IF v_exists > 0 THEN
        UPDATE sync_hashes
        SET pending_sync = TRUE,
            deleted_at = NULL,
            updated_at = NOW()
        WHERE table_name = 'products'
        AND record_key = v_product_code
        AND company_id = v_company_id;
    ELSE
        INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
        VALUES ('products', v_product_code, md5(v_product_code::text), TRUE, v_company_id, NOW());
    END IF;

    -- Retornar según la operación
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Trigger que se dispara cuando cambia la imagen en products_image (INSERT, UPDATE, DELETE)
DROP TRIGGER IF EXISTS tr_product_image_mark_updated ON products_image;
CREATE TRIGGER tr_product_image_mark_updated
    AFTER INSERT OR UPDATE OR DELETE ON products_image
    FOR EACH ROW
    EXECUTE PROCEDURE trigger_mark_product_image_updated();


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
            deleted_at = NULL,
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
            deleted_at = NULL,
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
-- SELLERS PASSWORD - Detectar cambios de password en users
-- ===========================================================================

-- Función para marcar vendedor pendiente cuando cambia su password
CREATE OR REPLACE FUNCTION trigger_mark_seller_password_updated()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
BEGIN
    SELECT value INTO v_company_id
    FROM sync_config
    WHERE key = 'company_id';

    IF v_company_id IS NULL THEN
        v_company_id := 1;
    END IF;

    UPDATE sync_hashes
    SET pending_sync = TRUE,
        updated_at = NOW()
    WHERE table_name = 'sellers'
      AND record_key = (SELECT code FROM sellers WHERE user_code = OLD.code LIMIT 1)
      AND company_id = v_company_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_users_mark_seller_password_updated ON users;
CREATE TRIGGER tr_users_mark_seller_password_updated
    AFTER UPDATE OF user_password ON users
    FOR EACH ROW
    WHEN (OLD.user_password IS DISTINCT FROM NEW.user_password)
    EXECUTE PROCEDURE trigger_mark_seller_password_updated();

-- Función para marcar seller cuando cambia email
CREATE OR REPLACE FUNCTION trigger_mark_seller_email_updated()
RETURNS TRIGGER AS $$
DECLARE v_company_id INTEGER;
BEGIN
    SELECT value INTO v_company_id FROM sync_config WHERE key = 'company_id';
    IF v_company_id IS NULL THEN v_company_id := 1; END IF;

    UPDATE sync_hashes SET pending_sync = TRUE, updated_at = NOW()
    WHERE table_name = 'sellers'
      AND record_key = (SELECT code FROM sellers WHERE user_code = OLD.code LIMIT 1)
      AND company_id = v_company_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_users_mark_seller_email_updated ON users;
CREATE TRIGGER tr_users_mark_seller_email_updated
    AFTER UPDATE OF email ON users
    FOR EACH ROW
    WHEN (OLD.email IS DISTINCT FROM NEW.email)
    EXECUTE PROCEDURE trigger_mark_seller_email_updated();

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

-- ===========================================================================
-- SALES OPERATION (QUOTES - APROBADOS LOCALMENTE)
-- ===========================================================================

-- Función para detectar pending → FALSE en sales_operation
-- Cuando el POS local procesa un presupuesto, marca pending = FALSE
-- Este trigger lo detecta y lo marca en sync_hashes para enviar approved a la API
CREATE OR REPLACE FUNCTION trigger_mark_sales_operation_approved()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id INTEGER;
    v_exists INTEGER;
BEGIN
    -- Solo cuando cambia pending de TRUE a FALSE
    IF OLD.pending = TRUE AND NEW.pending = FALSE THEN

        -- Obtener el company_id desde sync_config
        SELECT value INTO v_company_id
        FROM sync_config
        WHERE key = 'company_id';

        IF v_company_id IS NULL THEN
            v_company_id := 1;
        END IF;

        -- Verificar si ya existe el registro en sync_hashes
        SELECT COUNT(*) INTO v_exists
        FROM sync_hashes
        WHERE table_name = 'quotes_approved'
          AND record_key = NEW.document_no::text
          AND company_id = v_company_id;

        IF v_exists > 0 THEN
            UPDATE sync_hashes
            SET pending_sync = TRUE,
                updated_at = NOW()
            WHERE table_name = 'quotes_approved'
              AND record_key = NEW.document_no::text
              AND company_id = v_company_id;
        ELSE
            INSERT INTO sync_hashes (table_name, record_key, record_hash, pending_sync, company_id, updated_at)
            VALUES ('quotes_approved', NEW.document_no::text, md5(NEW.document_no::text), TRUE, v_company_id, NOW());
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_sales_operation_mark_approved ON sales_operation;
CREATE TRIGGER tr_sales_operation_mark_approved
    AFTER UPDATE OF pending ON sales_operation
    FOR EACH ROW
    WHEN (OLD.pending = TRUE AND NEW.pending = FALSE AND NEW.document_no LIKE 'W%')
    EXECUTE PROCEDURE trigger_mark_sales_operation_approved();
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

            # IMPORTANTE: Agregar timeout de 5 segundos por statement para evitar bloqueos
            # Esto es crítico en Windows 11 donde statements pueden colgarse
            print(f"[DEBUG] Configurando statement_timeout=5s para evitar bloqueos...")
            self.pg_cursor.execute("SET statement_timeout = 5000")  # 5 segundos en ms

            # Ejecutar cada statement individualmente
            for i, statement in enumerate(statements, 1):
                if statement.strip():  # Solo ejecutar si no está vacío
                    # Mostrar primer fragmento del statement para identificación
                    stmt_preview = statement.split()[0:3]
                    stmt_preview = ' '.join(stmt_preview) if stmt_preview else 'EMPTY'
                    print(f"[DEBUG] Ejecutando statement {i}/{len(statements)}: {stmt_preview}...")
                    try:
                        self.pg_cursor.execute(statement)
                        print(f"[DEBUG] Statement {i} OK")
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

            # Obtener versión del sistema Chrystal desde PostgreSQL
            chrystal_ver = _get_chrystal_version(self.postgres_config)

            # Obtener UUID del dispositivo (serial de disco)
            _device_uuid = _get_hdd_serial()

            # Crear clientes
            self.categories_client = CategoriesClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger,
                app_version=APP_VERSION,
                chrystal_version=chrystal_ver,
                device_uuid=_device_uuid
            )

            self.products_client = ProductsClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger,
                app_version=APP_VERSION,
                chrystal_version=chrystal_ver,
                device_uuid=_device_uuid
            )

            self.customers_client = CustomersClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger,
                app_version=APP_VERSION,
                chrystal_version=chrystal_ver,
                device_uuid=_device_uuid
            )

            self.sellers_client = SellersClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger,
                app_version=APP_VERSION,
                chrystal_version=chrystal_ver,
                device_uuid=_device_uuid
            )

            self.quotes_client = QuotesClient(
                base_url=base_url,
                api_key=api_key,
                logger=api_logger,
                app_version=APP_VERSION,
                chrystal_version=chrystal_ver,
                device_uuid=_device_uuid
            )

            self._log("✅ Clientes API inicializados")
            return True

        except Exception as e:
            import traceback
            error_detail = str(e)
            self._log(f"❌ Error inicializando clientes API: {error_detail}", "error")
            print(traceback.format_exc())
            with open("primera_sync_log.txt", "a") as f:
                f.write(f"\n[ERROR] initialize_api_clients: {error_detail}\n")
                f.write(traceback.format_exc() + "\n")
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

        # Detectar presupuestos aprobados localmente (pending → FALSE)
        # y enviar status=approved a la API
        quotes_sync.sync_approved_quotes()

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

        # Detectar presupuestos aprobados localmente
        quotes_sync.sync_approved_quotes()

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

        self.sync_interval_var = tk.StringVar(value=existing_config.get('sync_interval_minutes', '0'))

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
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'X-App-Version': APP_VERSION,
                    'X-App-Type': 'sincronizador'
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
                            "Su email de empresa no está configurado en Chrystal.\n\n"
                            "Por favor verifique y luego intente de nuevo la verificación.")
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
            elif response.status_code == 403:
                error_detail = response.json()
                error_msg = error_detail.get('message', error_detail.get('error', 'Error desconocido'))
                print(f"[DEBUG] Detalle error 403: {error_msg}")
                messagebox.showerror("❌ Error de acceso", error_msg)
                self.log("❌ Acceso denegado (403)")
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
            messagebox.showerror("❌ Error de Conexión",
                "La API no responde. Por favor verifique su conexión a internet e intente nuevamente.")
            self.log("❌ API: Timeout")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("❌ Error de Conexión",
                "No se puede conectar con el servidor.\n\n"
                "Por favor verifique su conexión a internet e intente nuevamente.")
            self.log("❌ API: Error de conexión")
        except Exception as e:
            messagebox.showerror("❌ Error",
                "Ocurrió un error inesperado al validar la API Key.\n\n"
                "Por favor intente nuevamente. Si el problema persiste, contacte soporte.")
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

        if interval_minutes == 0:
            messagebox.showerror(
                "⚠️ Intervalo no válido",
                "El intervalo de sincronización debe ser mayor a 0 minutos.\n\n"
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
                        _cv_ping = _get_chrystal_version({
                            'host': config.get('postgres_host', ''),
                            'port': config.get('postgres_port', ''),
                            'database': config.get('postgres_database', ''),
                            'user': config.get('postgres_user', ''),
                            'password': config.get('postgres_password', ''),
                        })
                        ping_result = auth_manager.ping_api_key(
                            config['api_key'], chrystal_version=_cv_ping
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
                set_window_favicon(sync_window)
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
                        _cv_ping = _get_chrystal_version({
                            'host': config.get('postgres_host', ''),
                            'port': config.get('postgres_port', ''),
                            'database': config.get('postgres_database', ''),
                            'user': config.get('postgres_user', ''),
                            'password': config.get('postgres_password', ''),
                        })
                        auth_manager.ping_api_key(config['api_key'], chrystal_version=_cv_ping)
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
        set_window_favicon(sync_window)
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

                            def cerrar_sync_y_continuar():
                                try:
                                    if sync_window.winfo_exists():
                                        sync_window.destroy()
                                except:
                                    pass

                            sync_window.after(2000, cerrar_sync_y_continuar)

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
                _cv_ping = _get_chrystal_version({
                    'host': config['postgres_host'],
                    'port': config['postgres_port'],
                    'database': config['postgres_database'],
                    'user': config['postgres_user'],
                    'password': config['postgres_password'],
                })
                ping_result = auth_manager.ping_api_key(config['api_key'], chrystal_version=_cv_ping)
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
        set_window_favicon(sync_window)
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

        # Protección contra múltiples clicks simultáneos
        self._auth_in_progress = False
        self._manager_open = False
        self._logs_open = False
        self._operation_lock = None  # Thread lock para operaciones críticas

        # Configurar auto-inicio al encender el equipo
        self.configurar_auto_inicio()

    def crear_icono(self):
        """Crea icono para la bandeja del sistema usando el logo"""
        try:
            from PIL import Image
            import sys

            # Determinar el directorio base para encontrar logo.png
            # Si está compilado con PyInstaller, usar sys._MEIPASS
            if getattr(sys, 'frozen', False):
                # Ejecutable compilado: sys._MEIPASS es el dir de datos desempaquetados
                base_dir = sys._MEIPASS
            else:
                # Desarrollo: usar el directorio del script
                base_dir = os.path.dirname(os.path.abspath(__file__))

            # Buscar logo.png en el directorio base
            logo_path = os.path.join(base_dir, 'logo.png')

            # Si no existe, intentar en windows_api/ (solo en desarrollo)
            if not os.path.exists(logo_path):
                logo_path = os.path.join(base_dir, 'windows_api', 'logo.png')

            # Cargar y redimensionar logo a 64x64
            if os.path.exists(logo_path):
                image = Image.open(logo_path)
                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                return image
            else:
                print(f"[WARNING] logo.png no encontrado en: {base_dir}")
                # Fallback: crear imagen simple si no hay logo
                from PIL import ImageDraw
                image = Image.new('RGB', (64, 64), color='white')
                draw = ImageDraw.Draw(image)
                draw.ellipse([10, 10, 54, 54], fill='#3498db', outline='#2980b9', width=3)
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
        """Pide autenticacion en proceso separado, reintenta si la clave es incorrecta.

        Returns:
            bool: True si autenticacion exitosa, False si cancelo
        """
        import subprocess
        import json
        import tempfile
        import os
        import sys
        import time

        error_msg = ""

        while True:
            # Archivo temporal para resultado del proceso hijo
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
                result_path = f.name

            try:
                # Determinar como ejecutar el dialogo en proceso separado
                cmd_args = ['--auth-dialog', result_path]
                if error_msg:
                    cmd_args += ['--auth-error', error_msg]

                if getattr(sys, 'frozen', False):
                    args = [sys.executable] + cmd_args
                else:
                    args = [sys.executable, __file__] + cmd_args

                creationflags = 0
                if sys.platform == 'win32':
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=creationflags
                )

                if result.returncode != 0:
                    print(f"[AUTH] Error en proceso de autenticacion (codigo {result.returncode})")
                    if result.stderr:
                        print(f"[AUTH] stderr: {result.stderr}")
                    return False

                # Leer resultado del proceso hijo
                try:
                    with open(result_path, 'r') as f:
                        data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError) as e:
                    print(f"[AUTH] Error leyendo resultado: {e}")
                    return False

                email = data.get('email', '')
                password = data.get('password', '')

                if not email or not password:
                    print("[AUTH] Autenticacion cancelada por el usuario")
                    return False

                # Validar credenciales contra la API
                import requests
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

                        # Validar rol
                        role = user.get('role')
                        if role not in ['admin', 'cajero']:
                            mostrar_banner(
                                "Acceso Denegado",
                                f"Rol no autorizado: {role}\nSolo administradores y cajeros.",
                                duracion=10
                            )
                            return False

                        # Guardar credenciales
                        self.api_token = user_data.get('token')
                        self.user_email = email
                        self.api_password = password
                        return True

                # Error de autenticacion - preparar mensaje y reintentar
                error_msg = "Clave incorrecta. Intente de nuevo."
                try:
                    error_data = response.json()
                    server_msg = error_data.get('message', '')
                    if server_msg:
                        error_msg = f"Clave incorrecta: {server_msg}"
                except Exception:
                    pass

                print(f"[AUTH] Credenciales invalidas, reintentando...")
                # Pequena pausa antes de mostrar el dialogo otra vez
                time.sleep(0.5)
                # Continuar el loop para mostrar el dialogo con el error

            except subprocess.TimeoutExpired:
                print("[AUTH] Tiempo de espera agotado")
                mostrar_banner("Error", "Tiempo de espera agotado en autenticacion.", duracion=10)
                return False
            except Exception as e:
                print(f"[AUTH] Error en autenticacion: {e}")
                import traceback
                traceback.print_exc()
                mostrar_banner("Error", f"Error en autenticacion:\n{str(e)}", duracion=10)
                return False
            finally:
                try:
                    os.unlink(result_path)
                except Exception:
                    pass

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
            _cv_ping = _get_chrystal_version({
                'host': self.config['postgres_host'],
                'port': self.config['postgres_port'],
                'database': self.config['postgres_database'],
                'user': self.config['postgres_user'],
                'password': self.config['postgres_password'],
            })
            ping_result = auth_manager.ping_api_key(api_key, chrystal_version=_cv_ping)
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
        print("[DEBUG] bucle_sincronizacion: Iniciando...")
        print(f"[DEBUG] bucle_sincronizacion: sync_running={self.sync_running}")

        interval = int(self.config.get('sync_interval_minutes', 30))
        print(f"⏱️  Intervalo de sincronización: {interval} minutos")
        print(f"[DEBUG] bucle_sincronizacion: Intervalo configurado: {interval} minutos")

        # Primera sincronización inmediata
        print(f"[DEBUG] bucle_sincronizacion: Verificando sync_running para primera sync...")
        if self.sync_running:
            print("🔄 Ejecutando primera sincronización al inicio...")
            try:
                self.ejecutar_sincronizacion()
                print("[DEBUG] bucle_sincronizacion: Primera sincronización completada")
            except Exception as e:
                print(f"[ERROR] bucle_sincronizacion: Error en primera sincronización: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[WARNING] bucle_sincronizacion: sync_running=False, saltando primera sync")

        # Bucle
        print(f"[DEBUG] bucle_sincronizacion: Iniciando bucle infinito...")
        iteration = 0
        while self.sync_running:
            try:
                iteration += 1
                print(f"[DEBUG] bucle_sincronizacion: Iteración {iteration}, esperando {interval} minutos...")
                time.sleep(interval * 60)
                print(f"[DEBUG] bucle_sincronizacion: Despertó de sleep, sync_running={self.sync_running}")
                if self.sync_running:
                    print(f"🔄 Ejecutando sincronización automática #{iteration}...")
                    try:
                        self.ejecutar_sincronizacion()
                        print(f"[DEBUG] bucle_sincronizacion: Sincronización #{iteration} completada")
                    except Exception as e:
                        print(f"[ERROR] bucle_sincronizacion: Error en sync #{iteration}: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"[DEBUG] bucle_sincronizacion: sync_running=False, saliendo del bucle")
                    break
            except KeyboardInterrupt:
                print(f"[DEBUG] bucle_sincronizacion: KeyboardInterrupt detectado")
                break
        print(f"[DEBUG] bucle_sincronizacion: Bucle terminado")

    def abrir_manager(self):
        """Abre ventana del manager con PySide6 en proceso separado."""
        if self._manager_open:
            print("⚠️ La ventana del Manager ya está abierta")
            return

        # Autenticar (solo durante el diálogo, no bloquea otras acciones después)
        if self._auth_in_progress:
            print("⚠️ Ya hay una autenticación en progreso, espere...")
            return
        self._auth_in_progress = True
        try:
            if not self.reautenticar_usuario():
                print("❌ Acceso a manager denegado: autenticación fallida o cancelada")
                return
        finally:
            self._auth_in_progress = False

        # Si llegó aquí, autenticación exitosa
        print("abrir_manager: Autenticación exitosa, abriendo Manager...")
        self._manager_open = True
        try:
            import subprocess
            import json
            import sys
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
                config_path = f.name

            try:
                # Escribir configuración desencriptada para el subprocess
                cfg_for_manager = {
                    'api_url': self.config.get('api_url', ''),
                    'api_key': getattr(self, 'api_key', self.config.get('api_key', '')),
                    'company_rif': self.config.get('company_rif', ''),
                    'company_email': self.config.get('company_email', ''),
                    'company_name': self.config.get('company_name', ''),
                    'postgres_host': self.config.get('postgres_host', ''),
                    'postgres_port': self.config.get('postgres_port', ''),
                    'postgres_database': self.config.get('postgres_database', ''),
                    'postgres_user': self.config.get('postgres_user', ''),
                    'postgres_password': self.config.get('postgres_password', ''),
                    'sync_interval_minutes': self.config.get('sync_interval_minutes', '30'),
                    'company_id': getattr(self, 'api_key', None)
                }
                with open(config_path, 'w') as f:
                    json.dump(cfg_for_manager, f)

                if getattr(sys, 'frozen', False):
                    args = [sys.executable, '--manager-window', config_path]
                else:
                    args = [sys.executable, __file__, '--manager-window', config_path]

                creationflags = 0
                if sys.platform == 'win32':
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

                subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=3600,
                    creationflags=creationflags
                )

            finally:
                try:
                    os.unlink(config_path)
                except Exception:
                    pass

        except subprocess.TimeoutExpired:
            print("[MANAGER] Timeout, el manager se cerró por tiempo")
        except Exception as e:
            print(f"[ERROR] abrir_manager: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._manager_open = False

    def ver_logs(self):
        """Abre ventana de logs con PySide6 en proceso separado."""
        if self._logs_open:
            print("⚠️ La ventana de Logs ya está abierta")
            return

        # Autenticar (solo durante el diálogo)
        if self._auth_in_progress:
            print("⚠️ Ya hay una autenticación en progreso, espere...")
            return
        self._auth_in_progress = True
        try:
            if not self.reautenticar_usuario():
                print("❌ Acceso a logs denegado: autenticación fallida o cancelada")
                return
        finally:
            self._auth_in_progress = False

        # Si llegó aquí, autenticación exitosa
        self._logs_open = True
        try:
            import subprocess
            import sys

            log_file = get_log_file(self.config.get('company_email'))

            if getattr(sys, 'frozen', False):
                args = [sys.executable, '--log-window', log_file]
            else:
                args = [sys.executable, __file__, '--log-window', log_file]

            creationflags = 0
            if sys.platform == 'win32':
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=120,
                creationflags=creationflags
            )

            if result.returncode != 0:
                print(f"[LOGS] Error en proceso de logs (código {result.returncode})")

        except Exception as e:
            print(f"Error abriendo logs: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._logs_open = False

    def sincronizar_ahora(self):
        """Ejecuta sincronización manual desde el menú con protección contra múltiples clicks"""
        if self.is_syncing:
            print("⚠️ Ya hay una sincronización en progreso")
            return

        # Autenticar (solo durante el diálogo)
        if self._auth_in_progress:
            print("⚠️ Ya hay una autenticación en progreso, espere...")
            return
        self._auth_in_progress = True
        try:
            if not self.reautenticar_usuario():
                print("❌ Sincronización cancelada: autenticación fallida o cancelada")
                return
        finally:
            self._auth_in_progress = False

        # Si llegó aquí, autenticación exitosa
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

        print("[DEBUG] Creando thread de sincronización...")
        thread = threading.Thread(target=sync_thread_wrapper, daemon=False)
        thread.start()
        print("[DEBUG] Thread de sincronización iniciado (daemon=False)")

    def abrir_config(self):
        """Abre ventana de configuración con autenticación"""
        import threading
        threading.Thread(target=self._abrir_config_thread, daemon=True).start()

    def _abrir_config_thread(self):
        """Abre config con PySide6 en proceso separado."""
        # Verificar autenticación antes de abrir config
        if not self.reautenticar_usuario():
            print("❌ Acceso a configuración denegado: autenticación fallida o cancelada")
            return

        try:
            import subprocess
            import json
            import sys
            import tempfile

            from config_encryption import encrypt_config, decrypt_config

            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
                result_path = f.name

            try:
                if getattr(sys, 'frozen', False):
                    args = [sys.executable, '--config-window', result_path]
                else:
                    args = [sys.executable, __file__, '--config-window', result_path]

                creationflags = 0
                if sys.platform == 'win32':
                    creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

                subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    creationflags=creationflags
                )

                # Leer resultado
                try:
                    with open(result_path, 'r') as f:
                        data = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    data = {}

                if data.get('saved'):
                    # Encriptar y guardar configuración
                    config_data = {k: v for k, v in data.items() if k != 'saved'}
                    config_encrypted = encrypt_config(config_data)
                    import json as _json
                    with open(CONFIG_FILE, 'w') as f:
                        _json.dump(config_encrypted, f, indent=2)
                    print("✅ Configuración guardada desde PySide6")
                else:
                    print("ℹ️ Configuración cancelada por el usuario")

            finally:
                os.unlink(result_path)

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
        """Muestra confirmación con PySide6 en proceso separado y sale"""
        import subprocess, tempfile, json as _json, os, sys

        _cf_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as _f:
                _cf_path = _f.name
            _cf_args = ([sys.executable, '--confirm-dialog', _cf_path]
                       if getattr(sys, 'frozen', False)
                       else [sys.executable, __file__, '--confirm-dialog', _cf_path])
            subprocess.run(_cf_args, capture_output=True, text=True, timeout=60)
            try:
                with open(_cf_path) as _f:
                    _cf_data = _json.load(_f)
            except Exception:
                _cf_data = {}
        except Exception:
            _cf_data = {}
        finally:
            if _cf_path and os.path.exists(_cf_path):
                try: os.unlink(_cf_path)
                except: pass

        if _cf_data.get('confirmed'):
            print("\n👋 Deteniendo servicio...")
            self.sync_running = False
            if self.icon:
                self.icon.stop()
            os._exit(0)
        else:
            print("❌ Salida cancelada")

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
            tooltip_text = f"""Sync API System v{APP_VERSION}
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

            # Notificación de inicio
            try:
                mostrar_banner(
                    "🔄 Sync API System",
                    f"System Tray iniciado\n{self.config.get('company_rif', '')}",
                    duracion=3
                )
            except Exception:
                pass

            # Ejecutar icono con bucle de reinicio automático
            # run() es bloqueante y procesa los mensajes de Windows.
            # Si el icono desaparece (Explorer crash, etc.), run() retorna
            # y el bucle lo reinicia automáticamente.
            log_debug("✅ Servicio iniciado en la bandeja del sistema")
            log_debug("💡 El icono está en la barra de tareas (junto al reloj)")
            log_debug("💡 Clic derecho para ver opciones")
            log_debug("")
            log_debug("[DEBUG] Llamando a icon.run() (bloqueante)...")

            self.sync_running = True
            reintentos = 0
            while self.sync_running:
                try:
                    self.icon.run()
                except Exception as e:
                    log_debug(f"[WARNING] Icono detenido inesperadamente: {e}")

                if self.sync_running:
                    reintentos += 1
                    log_debug(f"[DEBUG] El icono se detuvo (reintento #{reintentos}), reiniciando en 3 segundos...")
                    import time
                    time.sleep(3)

            log_debug("[DEBUG] sync_running=False, saliendo del bucle principal")

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
        _cv_ping = _get_chrystal_version({
            'host': config.get('postgres_host', ''),
            'port': config.get('postgres_port', ''),
            'database': config.get('postgres_database', ''),
            'user': config.get('postgres_user', ''),
            'password': config.get('postgres_password', ''),
        })
        result = auth_manager.ping_api_key(api_key, chrystal_version=_cv_ping)
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

                _cv_ping = _get_chrystal_version({
                    'host': config.get('postgres_host', ''),
                    'port': config.get('postgres_port', ''),
                    'database': config.get('postgres_database', ''),
                    'user': config.get('postgres_user', ''),
                    'password': config.get('postgres_password', ''),
                })
                auth_manager.ping_api_key(api_key, chrystal_version=_cv_ping)
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

def _get_window_icon():
    """Retorna QIcon del logo si existe, None si no."""
    import os
    import sys as _sys

    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible = [
        os.path.join(script_dir, 'windows_api', 'logo.ico'),
        os.path.join(script_dir, 'logo.ico'),
    ]
    if getattr(_sys, 'frozen', False):
        exe_dir = os.path.dirname(_sys.executable)
        possible.insert(0, os.path.join(exe_dir, 'logo.ico'))

    for p in possible:
        if os.path.exists(p):
            from PySide6.QtGui import QIcon
            return QIcon(p)
    return None


def _handle_auth_dialog(result_path: str, error_message: str = "") -> None:
    """Muestra dialogo de autenticacion con PySide6 en proceso separado.

    Args:
        result_path: Ruta donde guardar el resultado JSON
        error_message: Mensaje de error opcional a mostrar (ej: "Clave incorrecta")
    """
    import sys

    # Mutex propio para evitar múltiples ventanas de credenciales
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW(None, False, "ChrystalAuthDialog-InstanceMutex")
            if ctypes.get_last_error() == 183:
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "La ventana de credenciales ya está abierta.\n"
                    "Revise la barra de tareas.",
                    "Sincronizador Chrystal",
                    0x10 | 0x0
                )
                return
        except Exception:
            pass

    import json
    from PySide6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton
    )
    from PySide6.QtCore import Qt

    class AuthDialog(QDialog):
        """Dialogo de autenticacion moderno con PySide6."""

        def __init__(self, error_msg: str = "") -> None:
            super().__init__()
            self.setWindowTitle("Sincronizador - Verificar Identidad")
            icon = _get_window_icon()
            if icon:
                self.setWindowIcon(icon)
            self.setFixedSize(420, 300)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            self.setStyleSheet("""
                QDialog { background-color: #f5f5f5; }
                QLabel { font-size: 12px; color: #333; }
                QLineEdit {
                    padding: 8px; font-size: 13px;
                    border: 1px solid #ccc; border-radius: 4px;
                    background: white;
                }
                QLineEdit:focus { border-color: #2E7D32; }
            """)

            layout = QVBoxLayout()
            layout.setSpacing(10)
            layout.setContentsMargins(24, 20, 24, 20)

            # Titulo
            title = QLabel("Verificacion Requerida")
            title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1a1a1a;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            # Error message (si hay)
            if error_msg:
                err_label = QLabel(error_msg)
                err_label.setStyleSheet("color: red; font-weight: bold; font-size: 13px; background: #ffebee; padding: 8px; border-radius: 4px;")
                err_label.setAlignment(Qt.AlignCenter)
                err_label.setWordWrap(True)
                layout.addWidget(err_label)

            # Instruccion
            instr = QLabel("Ingrese sus credenciales de administrador:")
            instr.setAlignment(Qt.AlignCenter)
            layout.addWidget(instr)

            # Email
            layout.addWidget(QLabel("Email:"))
            self.email_input = QLineEdit()
            self.email_input.setPlaceholderText("usuario@ejemplo.com")
            layout.addWidget(self.email_input)

            # Contrasena
            layout.addWidget(QLabel("Contrasena:"))
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setPlaceholderText("********")
            layout.addWidget(self.password_input)

            # Botones
            btn_layout = QHBoxLayout()

            accept_btn = QPushButton("Aceptar")
            accept_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2E7D32; color: white;
                    font-weight: bold; padding: 8px 24px;
                    border-radius: 4px; font-size: 13px; border: none;
                }
                QPushButton:hover { background-color: #1B5E20; }
                QPushButton:pressed { background-color: #145214; }
            """)
            accept_btn.clicked.connect(self.accept)
            btn_layout.addWidget(accept_btn)

            cancel_btn = QPushButton("Cancelar")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #C62828; color: white;
                    font-weight: bold; padding: 8px 24px;
                    border-radius: 4px; font-size: 13px; border: none;
                }
                QPushButton:hover { background-color: #B71C1C; }
                QPushButton:pressed { background-color: #8E0000; }
            """)
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)

            layout.addLayout(btn_layout)
            self.setLayout(layout)

            # Enter navega entre campos y acepta
            self.email_input.returnPressed.connect(self.password_input.setFocus)
            self.password_input.returnPressed.connect(self.accept)

            # Foco inicial
            if error_msg:
                self.password_input.setFocus()
                self.password_input.selectAll()
            else:
                self.email_input.setFocus()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dialog = AuthDialog(error_msg=error_message)
    if dialog.exec() == QDialog.Accepted:
        email = dialog.email_input.text().strip()
        password = dialog.password_input.text().strip()
        with open(result_path, 'w') as f:
            json.dump({"email": email, "password": password}, f)
    else:
        with open(result_path, 'w') as f:
            json.dump({"email": "", "password": ""}, f)


def _handle_log_window(log_file: str) -> None:
    """Muestra visor de logs con PySide6 en proceso separado.

    Args:
        log_file: Ruta al archivo de logs a mostrar
    """
    import sys
    import os
    from PySide6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QTextEdit, QPushButton
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    class LogDialog(QDialog):
        """Ventana de visualización de logs con PySide6."""

        def __init__(self, log_path: str) -> None:
            super().__init__()
            self.setWindowTitle("📊 Logs del Sistema - Visor")
            icon = _get_window_icon()
            if icon:
                self.setWindowIcon(icon)
            self.resize(900, 700)
            self.setMinimumSize(500, 300)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            self.setStyleSheet("""
                QDialog { background-color: #f0f0f0; }
                QTextEdit {
                    font-family: Consolas, "Courier New", monospace;
                    font-size: 10px;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border: 1px solid #333;
                }
            """)

            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # Header oscuro
            header = QLabel("📊 Logs del Sistema")
            header.setStyleSheet("""
                QLabel {
                    background-color: #2c3e50;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 14px 20px;
                }
            """)
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)

            # Área de texto con los logs
            self.text_edit = QTextEdit()
            self.text_edit.setReadOnly(True)
            self.text_edit.setFont(QFont("Consolas", 10))

            # Cargar contenido del archivo
            if os.path.exists(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    if not content.strip():
                        content = "El archivo de logs está vacío."
                except Exception as e:
                    content = f"Error cargando logs: {e}"
            else:
                content = f"No hay archivo de logs aún.\nUbicación esperada: {log_path}"

            self.text_edit.setText(content)
            self.text_edit.verticalScrollBar().setValue(
                self.text_edit.verticalScrollBar().maximum()
            )
            layout.addWidget(self.text_edit)

            # Botón cerrar
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(10, 10, 10, 10)

            close_btn = QPushButton("❌ Cerrar")
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #C62828; color: white;
                    font-weight: bold; padding: 8px 32px;
                    border-radius: 4px; font-size: 12px; border: none;
                }
                QPushButton:hover { background-color: #B71C1C; }
                QPushButton:pressed { background-color: #8E0000; }
            """)
            close_btn.clicked.connect(self.accept)
            btn_layout.addStretch()
            btn_layout.addWidget(close_btn)
            btn_layout.addStretch()

            layout.addLayout(btn_layout)
            self.setLayout(layout)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dialog = LogDialog(log_file)
    dialog.exec()


def _handle_config_window(result_path: str) -> None:
    """Muestra ventana de configuración con PySide6 en proceso separado.

    Args:
        result_path: Ruta donde guardar el resultado JSON con la configuración
    """
    import sys
    import os
    import json
    from PySide6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLabel, QLineEdit, QPushButton, QTabWidget, QWidget,
        QMessageBox, QFrame, QSpinBox
    )
    from PySide6.QtCore import Qt

    # Cargar configuración existente si hay
    CONFIG_FILE_CFG = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")
    existing_config = {}
    if os.path.exists(CONFIG_FILE_CFG):
        try:
            with open(CONFIG_FILE_CFG, 'r') as f:
                cfg_enc = json.load(f)
            from config_encryption import decrypt_config
            existing_config = decrypt_config(cfg_enc)
        except Exception:
            pass

    class ConfigDialog(QDialog):
        """Ventana de configuración con PySide6."""

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("⚙️ Configuración del Sincronizador API")
            icon = _get_window_icon()
            if icon:
                self.setWindowIcon(icon)
            self.resize(600, 550)
            self.setMinimumSize(500, 450)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

            # Variables del formulario
            self.api_url = existing_config.get('api_url', 'https://chrystal.com.ve/mobiletest/public/api')
            self.api_key = ''
            self.pg_host = existing_config.get('postgres_host', 'localhost')
            self.pg_port = str(existing_config.get('postgres_port', '5432'))
            self.pg_database = existing_config.get('postgres_database', '')
            self.pg_user = existing_config.get('postgres_user', 'postgres')
            self.pg_password = ''
            self.sync_interval = str(existing_config.get('sync_interval_minutes', '30'))

            # Datos de empresa (del ping)
            self.company_rif = ''
            self.company_email = ''
            self.company_name = ''

            self._build_ui()
            self._apply_styles()

        def _apply_styles(self) -> None:
            self.setStyleSheet("""
                QDialog { background-color: #f5f5f5; }
                QTabWidget::pane { border: 1px solid #ccc; background: white; }
                QTabBar::tab {
                    padding: 8px 16px; font-size: 12px;
                    border: 1px solid #ccc; border-bottom: none;
                    background: #e0e0e0; margin-right: 2px;
                }
                QTabBar::tab:selected { background: white; font-weight: bold; }
                QLineEdit {
                    padding: 6px; font-size: 12px;
                    border: 1px solid #ccc; border-radius: 3px;
                    background: white;
                }
                QLineEdit:focus { border-color: #2E7D32; }
                QPushButton { font-size: 12px; padding: 6px 16px; }
                QLabel { font-size: 12px; }
            """)

        def _build_ui(self) -> None:
            layout = QVBoxLayout()
            layout.setContentsMargins(12, 12, 12, 12)

            # Título
            title = QLabel("⚙️ Configuración del Sincronizador API")
            title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1a1a1a; padding: 4px 0;")
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)

            # Tabs
            tabs = QTabWidget()
            tabs.addTab(self._build_pg_tab(), "🐘 PostgreSQL")
            tabs.addTab(self._build_api_tab(), "🔐 API Key")
            tabs.addTab(self._build_config_tab(), "⚙️ Configuración")
            layout.addWidget(tabs)

            # Botones
            btn_layout = QHBoxLayout()
            save_btn = QPushButton("💾 Guardar y Salir")
            save_btn.setStyleSheet("""
                QPushButton { background-color: #2E7D32; color: white;
                    font-weight: bold; padding: 8px 24px; border-radius: 4px; border: none; }
                QPushButton:hover { background-color: #1B5E20; }
            """)
            save_btn.clicked.connect(self._on_save)
            btn_layout.addWidget(save_btn)

            cancel_btn = QPushButton("❌ Cancelar")
            cancel_btn.setStyleSheet("""
                QPushButton { background-color: #C62828; color: white;
                    font-weight: bold; padding: 8px 24px; border-radius: 4px; border: none; }
                QPushButton:hover { background-color: #B71C1C; }
            """)
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)

            layout.addLayout(btn_layout)
            self.setLayout(layout)

        def _build_pg_tab(self) -> QWidget:
            tab = QWidget()
            form = QFormLayout()
            form.setContentsMargins(16, 16, 16, 16)
            form.setSpacing(8)

            self.pg_host_edit = QLineEdit(self.pg_host)
            self.pg_host_edit.setPlaceholderText("localhost")
            form.addRow("Host:", self.pg_host_edit)

            self.pg_port_edit = QLineEdit(self.pg_port)
            self.pg_port_edit.setPlaceholderText("5432")
            form.addRow("Port:", self.pg_port_edit)

            self.pg_db_edit = QLineEdit(self.pg_database)
            self.pg_db_edit.setPlaceholderText("chrystal_db")
            form.addRow("Database:", self.pg_db_edit)

            self.pg_user_edit = QLineEdit(self.pg_user)
            self.pg_user_edit.setPlaceholderText("postgres")
            form.addRow("User:", self.pg_user_edit)

            self.pg_pass_edit = QLineEdit(self.pg_password)
            self.pg_pass_edit.setEchoMode(QLineEdit.Password)
            self.pg_pass_edit.setPlaceholderText("••••••••")
            form.addRow("Password:", self.pg_pass_edit)

            test_btn = QPushButton("🧪 Probar Conexión PostgreSQL")
            test_btn.setStyleSheet(
                "QPushButton { background-color: #1976D2; color: white;"
                " border: none; border-radius: 3px; padding: 6px 12px; }"
                " QPushButton:hover { background-color: #1565C0; }")
            test_btn.clicked.connect(self._test_pg)
            form.addRow("", test_btn)

            self.pg_status = QLabel("")
            form.addRow("", self.pg_status)

            tab.setLayout(form)
            return tab

        def _build_api_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(8)

            form = QFormLayout()
            self.api_key_edit = QLineEdit()
            self.api_key_edit.setEchoMode(QLineEdit.Password)
            self.api_key_edit.setPlaceholderText("Ingrese la API Key")
            form.addRow("API Key:", self.api_key_edit)
            layout.addLayout(form)

            test_btn = QPushButton("🧪 Probar API Key")
            test_btn.setStyleSheet(
                "QPushButton { background-color: #1976D2; color: white;"
                " border: none; border-radius: 3px; padding: 6px 12px; }"
                " QPushButton:hover { background-color: #1565C0; }")
            test_btn.clicked.connect(self._test_api)
            layout.addWidget(test_btn)

            self.api_status = QLabel("")
            layout.addWidget(self.api_status)

            # Datos de empresa
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color: #ccc;")
            layout.addWidget(sep)

            emp_label = QLabel("Datos de la Empresa")
            emp_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
            layout.addWidget(emp_label)

            self.emp_name_label = QLabel("Empresa: --")
            self.emp_name_label.setStyleSheet("font-size: 12px;")
            layout.addWidget(self.emp_name_label)
            self.emp_rif_label = QLabel("RIF: --")
            layout.addWidget(self.emp_rif_label)
            self.emp_email_label = QLabel("Email: --")
            layout.addWidget(self.emp_email_label)

            tab.setLayout(layout)
            return tab

        def _build_config_tab(self) -> QWidget:
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(16, 16, 16, 16)
            layout.setSpacing(8)

            form = QFormLayout()
            self.interval_spin = QSpinBox()
            self.interval_spin.setMinimum(0)
            self.interval_spin.setMaximum(1440)
            self.interval_spin.setValue(0)
            self.interval_spin.setSuffix(" minutos (0 = preguntar al guardar)")
            self.interval_spin.setFixedWidth(160)
            form.addRow("Intervalo de sincronización:", self.interval_spin)
            layout.addLayout(form)

            info = QLabel("ℹ️ El sistema se sincronizará automáticamente cada X minutos.")
            info.setStyleSheet("color: gray; font-size: 11px;")
            layout.addWidget(info)

            layout.addStretch()
            tab.setLayout(layout)
            return tab

        def _test_pg(self) -> None:
            """Probar conexión PostgreSQL."""
            host = self.pg_host_edit.text().strip()
            port = self.pg_port_edit.text().strip()
            db = self.pg_db_edit.text().strip()
            user = self.pg_user_edit.text().strip()
            password = self.pg_pass_edit.text().strip()

            if not all([host, port, db, user]):
                self.pg_status.setText("❌ Complete Host, Puerto, Database y Usuario")
                self.pg_status.setStyleSheet("color: red;")
                return

            self.pg_status.setText("⏳ Probando conexión...")
            self.pg_status.setStyleSheet("color: blue;")
            QApplication.processEvents()

            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=host, port=int(port), database=db,
                    user=user, password=password, connect_timeout=10
                )
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM products")
                count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                self.pg_status.setText(f"✅ Conexión exitosa ({count:,} productos)")
                self.pg_status.setStyleSheet("color: green;")
            except Exception as e:
                self.pg_status.setText(f"❌ Error: {str(e)[:80]}")
                self.pg_status.setStyleSheet("color: red;")

        def _test_api(self) -> None:
            """Probar API Key contra ping."""
            api_key = self.api_key_edit.text().strip()
            if not api_key:
                self.api_status.setText("❌ Ingrese la API Key")
                self.api_status.setStyleSheet("color: red;")
                return

            self.api_status.setText("⏳ Probando API Key...")
            self.api_status.setStyleSheet("color: blue;")
            QApplication.processEvents()

            try:
                import requests

                # Obtener versión Chrystal desde PostgreSQL si hay credenciales
                _pg_cfg = {
                    'host': self.pg_host_edit.text().strip(),
                    'port': self.pg_port_edit.text().strip(),
                    'database': self.pg_db_edit.text().strip(),
                    'user': self.pg_user_edit.text().strip(),
                    'password': self.pg_pass_edit.text().strip(),
                }
                _cv = _get_chrystal_version(_pg_cfg)

                _chrystal_headers = {'X-App-Type-Chrystal': 'chrystal'}
                if _cv:
                    _chrystal_headers['X-App-Version-Chrystal'] = _cv

                _hdd_serial_test = _get_hdd_serial()
                _device_headers = {
                    'X-Device-UUID': _hdd_serial_test or 'unknown',
                    'X-App-ApiKey': api_key,
                }

                response = requests.get(
                    f"{self.api_url}/sync-client/ping",
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'X-App-Version': APP_VERSION,
                        'X-App-Type': 'sincronizador',
                        **_chrystal_headers,
                        **_device_headers,
                    },
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    if data.get('success'):
                        rd = data.get('data', {})
                        self.company_name = rd.get('empresa', '')
                        self.company_rif = rd.get('rif', '')
                        self.company_email = rd.get('email', '')

                        self.emp_name_label.setText(f"Empresa: {self.company_name or '--'}")
                        self.emp_rif_label.setText(f"RIF: {self.company_rif or '--'}")
                        self.emp_email_label.setText(f"Email: {self.company_email or '--'}")

                        self.api_status.setText("API Key valida")
                        self.api_status.setStyleSheet("color: green;")
                    else:
                        msg = data.get('message', data.get('error', 'Error'))
                        self.api_status.setText(f"API Key invalida: {msg}")
                        self.api_status.setStyleSheet("color: red;")
                else:
                    try:
                        err_data = response.json()
                        err_msg = err_data.get('message') or err_data.get('error') or f"HTTP {response.status_code}"
                    except Exception:
                        err_msg = f"HTTP {response.status_code}"
                    self.api_status.setText(f"Error: {err_msg}")
                    self.api_status.setStyleSheet("color: red;")
            except Exception as e:
                self.api_status.setText(f"❌ Error: {str(e)[:80]}")
                self.api_status.setStyleSheet("color: red;")

        def _on_save(self) -> None:
            """Validar y guardar configuración."""
            api_key = self.api_key_edit.text().strip()
            pg_host = self.pg_host_edit.text().strip()
            pg_port = self.pg_port_edit.text().strip()
            pg_db = self.pg_db_edit.text().strip()
            pg_user = self.pg_user_edit.text().strip()
            pg_pass = self.pg_pass_edit.text().strip()
            interval = str(self.interval_spin.value())

            if not api_key or not pg_db:
                QMessageBox.warning(self, "Advertencia", "API Key y Database son obligatorios")
                return

            if int(interval) <= 0:
                QMessageBox.warning(self, "Intervalo requerido",
                    "Debe establecer un intervalo de sincronizacion.\n\n"
                    "Indique cada cuantos minutos desea que el sistema sincronice automaticamente.")
                return

            if not self.company_rif or not self.company_email:
                QMessageBox.warning(self, "Advertencia",
                    "Debe probar la API Key primero para obtener los datos de la empresa.")
                return

            self._run_verification({
                'api_url': self.api_url,
                'api_key': api_key,
                'postgres_host': pg_host,
                'postgres_port': pg_port,
                'postgres_database': pg_db,
                'postgres_user': pg_user,
                'postgres_password': pg_pass,
                'company_rif': self.company_rif,
                'company_email': self.company_email,
                'company_name': self.company_name,
                'sync_interval_minutes': interval,
                'configured': True,
                'first_run': False
            })

        def _run_verification(self, config: dict) -> None:
            """Ejecuta verificación en 3 pasos con feedback en UI."""
            from PySide6.QtWidgets import QProgressDialog

            progress = QProgressDialog("Verificando configuración...", None, 0, 3, self)
            progress.setWindowTitle("⏳ Verificando")
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.show()
            QApplication.processEvents()

            try:
                # PASO 1: PostgreSQL
                progress.setLabelText("🔌 Conectando a PostgreSQL...")
                QApplication.processEvents()
                import psycopg2
                pg_conn = psycopg2.connect(
                    host=config['postgres_host'],
                    port=config['postgres_port'],
                    database=config['postgres_database'],
                    user=config['postgres_user'],
                    password=config['postgres_password'],
                    connect_timeout=10
                )
                pg_conn.close()
                progress.setValue(1)
                QApplication.processEvents()

                # Obtener versión Chrystal desde PostgreSQL (ya verificada en paso 1)
                _cv = _get_chrystal_version({
                    'host': config['postgres_host'],
                    'port': config['postgres_port'],
                    'database': config['postgres_database'],
                    'user': config['postgres_user'],
                    'password': config['postgres_password'],
                })
                _chrystal_headers = {'X-App-Type-Chrystal': 'chrystal'}
                if _cv:
                    _chrystal_headers['X-App-Version-Chrystal'] = _cv

                _hdd_serial_run = _get_hdd_serial()
                _device_headers = {
                    'X-Device-UUID': _hdd_serial_run or 'unknown',
                    'X-App-ApiKey': config['api_key'],
                }

                # PASO 2: API Key
                progress.setLabelText("Validando API Key...")
                QApplication.processEvents()
                import requests
                ping = requests.get(
                    f"{config['api_url']}/sync-client/ping",
                    headers={'Authorization': f'Bearer {config["api_key"]}',
                            'Content-Type': 'application/json',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'X-App-Version': APP_VERSION,
                            'X-App-Type': 'sincronizador',
                            **_chrystal_headers,
                            **_device_headers},
                    timeout=30
                )
                if ping.status_code not in [200, 201]:
                    try:
                        err_data = ping.json()
                        err_msg = err_data.get('message', '') or err_data.get('error', '')
                    except Exception:
                        err_data = {}
                        err_msg = ''

                    if ping.status_code == 403:
                        api_msg = err_data.get('message', '') if err_data else ''
                        detail = api_msg or "La API Key esta suspendida o bloqueada. Contacte a su proveedor."
                        raise Exception(f"Acceso denegado (HTTP 403): {detail}")

                    raise Exception(f"API Key invalida (HTTP {ping.status_code}): {err_msg or 'Revise la API Key y la URL'}")
                ping_data = ping.json()
                if not ping_data.get('success'):
                    raise Exception(f"API Key invalida: {ping_data.get('message', 'Error')}")
                progress.setValue(2)
                QApplication.processEvents()

                # PASO 3: Validar empresa
                progress.setLabelText("Validando empresa...")
                QApplication.processEvents()
                _hdd_serial = _get_hdd_serial()
                validate = requests.post(
                    f"{config['api_url']}/sync-client/company/validate",
                    headers={'Authorization': f'Bearer {config["api_key"]}',
                            'Content-Type': 'application/json',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'X-App-Version': APP_VERSION,
                            'X-App-Type': 'sincronizador',
                            **_chrystal_headers,
                            **_device_headers},
                    json={
                        'rif': config['company_rif'],
                        'email': config['company_email'],
                        'uuid_hard_drive': _hdd_serial or 'unknown',
                        'app_version_chrystal': _cv or APP_VERSION,
                    },
                    timeout=30
                )
                if validate.status_code not in [200, 201]:
                    try:
                        err_msg = validate.json().get('message', '') or validate.json().get('error', '')
                    except Exception:
                        err_msg = ''
                    raise Exception(f"Validacion empresa fallo (HTTP {validate.status_code}): {err_msg or 'Revise RIF y email'}")
                val_data = validate.json()
                if not val_data.get('success'):
                    raise Exception(f"Validacion empresa fallo: {val_data.get('message', 'Error')}")
                progress.setValue(3)
                QApplication.processEvents()

                progress.close()

                # Exito
                result_data = {k: v for k, v in config.items()}
                result_data['saved'] = True
                with open(result_path, 'w') as f:
                    json.dump(result_data, f, indent=2)
                self.accept()

            except Exception as e:
                progress.close()
                import traceback as _tb
                _tb.print_exc()
                print(f"Error de verificacion: {e}", file=sys.stderr)
                QMessageBox.critical(self, "Error de Verificacion",
                    f"La verificacion fallo:\n\n{str(e)}\n\n"
                    "La configuracion NO se guardo.")
                return

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dialog = ConfigDialog()
    dialog.exec()


def _handle_manager_window(config_path: str) -> None:
    """Muestra ventana de administración con PySide6 en proceso separado.

    Args:
        config_path: Ruta al archivo JSON con la configuración
    """
    import sys
    import os
    import json
    import time
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QFormLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
        QMessageBox, QGroupBox, QGridLayout, QSpinBox
    )
    from PySide6.QtCore import Qt, QTimer, QThread, Signal
    from PySide6.QtGui import QFont

    # Cargar configuración
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error cargando configuración para manager: {e}")
        return

    api_key = config.get('api_key', '')
    log_file = None
    if config.get('company_email'):
        email_safe = config['company_email'].replace('@', '_').replace('.', '_')
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", f"sync_api_{email_safe}.log")

    # --- Sync worker thread ---
    class SyncWorker(QThread):
        finished = Signal(dict)
        log_msg = Signal(str, str)

        def __init__(self, entity: str | None, config_data: dict) -> None:
            super().__init__()
            self.entity = entity
            self.config = config_data

        def run(self) -> None:
            def logger(msg: str, level: str = "info") -> None:
                self.log_msg.emit(msg, level)

            try:
                auth = APIAuthManager(self.config['api_url'], logger)
                _cv_ping = _get_chrystal_version({
                    'host': self.config['postgres_host'],
                    'port': self.config['postgres_port'],
                    'database': self.config['postgres_database'],
                    'user': self.config['postgres_user'],
                    'password': self.config['postgres_password'],
                })
                auth.ping_api_key(self.config['api_key'], chrystal_version=_cv_ping)
                auth.validate_company(self.config['company_rif'], self.config['company_email'])

                sync_mgr = APISyncManager(
                    postgres_config={
                        'host': self.config['postgres_host'],
                        'port': self.config['postgres_port'],
                        'database': self.config['postgres_database'],
                        'user': self.config['postgres_user'],
                        'password': self.config['postgres_password']
                    },
                    auth_manager=auth,
                    logger=logger
                )

                if not sync_mgr.connect_postgresql():
                    self.finished.emit({'success': False, 'error': 'Conexión PostgreSQL falló'})
                    return

                if not sync_mgr.initialize_api_clients():
                    self.finished.emit({'success': False, 'error': 'Clientes API fallaron'})
                    return

                if self.entity:
                    self.log_msg.emit(f"\n🔄 SINCRONIZANDO {self.entity.upper()}...", "info")
                    result = getattr(sync_mgr, f'sync_{self.entity}')()
                else:
                    self.log_msg.emit("\n🔄 SINCRONIZANDO TODO...", "info")
                    result = sync_mgr.sync_all()

                sync_mgr.close()
                self.finished.emit(result if isinstance(result, dict) else {'success': True})

            except Exception as e:
                self.finished.emit({'success': False, 'error': str(e)})

    class ManagerWindow(QMainWindow):
        """Ventana principal de administración con PySide6."""

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(f"Sincronizador API REST - Manager")
            icon = _get_window_icon()
            if icon:
                self.setWindowIcon(icon)
            self.resize(850, 700)
            self.setMinimumSize(700, 500)

            self.sync_worker: SyncWorker | None = None
            self._build_ui()
            self._apply_styles()

            self._log_timer = QTimer()
            self._log_timer.timeout.connect(self._poll_logs)
            self._log_timer.start(2000)
            self._last_log_size = 0
            self._poll_logs()

        def _apply_styles(self) -> None:
            self.setStyleSheet("""
                QMainWindow { background-color: #f5f5f5; }
                QGroupBox {
                    font-weight: bold; border: 1px solid #ccc;
                    border-radius: 4px; margin-top: 8px; padding: 12px 8px 8px 8px;
                    background: white;
                }
                QGroupBox::title {
                    subcontrol-origin: margin; left: 10px;
                    padding: 0 6px; color: #333;
                }
                QPushButton { font-size: 12px; padding: 6px 14px; border-radius: 3px; }
                QTextEdit { font-family: Consolas, monospace; font-size: 10px; background: #1e1e1e; color: #d4d4d4; border: 1px solid #333; }
                QSpinBox { padding: 4px; font-size: 12px; }
            """)

        def _build_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(6)

            header = QLabel(f"🔄 Sincronizador API REST - Manager")
            header.setStyleSheet(
                "background-color: #2c3e50; color: white; font-size: 16px;"
                " font-weight: bold; padding: 14px; border-radius: 4px;")
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)

            if config.get('company_rif'):
                info = QLabel(f"🏢 {config['company_rif']}  |  📧 {config.get('company_email', '')}")
                info.setStyleSheet("font-size: 11px; padding: 4px;")
                info.setAlignment(Qt.AlignCenter)
                layout.addWidget(info)

            row = QHBoxLayout()
            status_group = QGroupBox("📊 Estado del Sistema")
            status_layout = QVBoxLayout()
            self.lbl_status = QLabel("🟢 ACTIVO")
            self.lbl_status.setStyleSheet("font-size: 14px; font-weight: bold; color: green;")
            status_layout.addWidget(self.lbl_status)
            self.lbl_last_sync = QLabel("Última sync: --")
            status_layout.addWidget(self.lbl_last_sync)
            status_group.setLayout(status_layout)
            row.addWidget(status_group)

            stats_group = QGroupBox("📈 Estadísticas")
            stats_layout = QVBoxLayout()
            self.lbl_stats = QLabel("Categories: 0 | Products: 0 | Customers: 0 | Sellers: 0 | Quotes: 0")
            stats_layout.addWidget(self.lbl_stats)
            self.lbl_progress = QLabel("")
            self.lbl_progress.setStyleSheet("color: blue;")
            stats_layout.addWidget(self.lbl_progress)
            stats_group.setLayout(stats_layout)
            row.addWidget(stats_group)
            layout.addLayout(row)

            interval_group = QGroupBox("⏱️ Intervalo de Sincronización Automática")
            interval_layout = QHBoxLayout()
            current_interval = config.get('sync_interval_minutes', '30')
            interval_layout.addWidget(QLabel(f"Intervalo actual: {current_interval} minutos"))
            interval_layout.addWidget(QLabel("Nuevo (minutos):"))
            self.interval_spin = QSpinBox()
            self.interval_spin.setMinimum(1)
            self.interval_spin.setMaximum(1440)
            self.interval_spin.setValue(int(current_interval) if str(current_interval).isdigit() else 30)
            self.interval_spin.setFixedWidth(80)
            interval_layout.addWidget(self.interval_spin)
            save_interval_btn = QPushButton("💾 Guardar")
            save_interval_btn.setStyleSheet(
                "QPushButton { background-color: #2E7D32; color: white; border: none; }"
                " QPushButton:hover { background-color: #1B5E20; }")
            save_interval_btn.clicked.connect(self._save_interval)
            interval_layout.addWidget(save_interval_btn)
            interval_group.setLayout(interval_layout)
            layout.addWidget(interval_group)

            entity_group = QGroupBox("Sincronización por Entidad")
            entity_grid = QGridLayout()
            entities = [
                ("📁 Categories", "categories"),
                ("📦 Products", "products"),
                ("👥 Customers", "customers"),
                ("👔 Sellers", "sellers"),
                ("💰 Quotes", "quotes"),
            ]
            for i, (label, entity) in enumerate(entities):
                btn = QPushButton(label)
                btn.setStyleSheet(
                    "QPushButton { background-color: #1976D2; color: white; border: none; }"
                    " QPushButton:hover { background-color: #1565C0; }")
                btn.clicked.connect(lambda checked, e=entity: self._run_sync(e))
                entity_grid.addWidget(btn, 0, i)
            entity_group.setLayout(entity_grid)
            layout.addWidget(entity_group)

            action_layout = QHBoxLayout()
            sync_all_btn = QPushButton("🔄 Sincronizar Todo")
            sync_all_btn.setStyleSheet(
                "QPushButton { background-color: #F57C00; color: white; font-weight: bold; border: none; }"
                " QPushButton:hover { background-color: #E65100; }")
            sync_all_btn.clicked.connect(lambda: self._run_sync(None))
            action_layout.addWidget(sync_all_btn)

            logs_btn = QPushButton("📋 Ver Logs")
            logs_btn.clicked.connect(self._open_logs)
            action_layout.addWidget(logs_btn)

            reconfig_btn = QPushButton("🔄 Reconfigurar")
            reconfig_btn.clicked.connect(self._reconfig)
            action_layout.addWidget(reconfig_btn)

            salir_btn = QPushButton("❌ Salir")
            salir_btn.setStyleSheet(
                "QPushButton { background-color: #C62828; color: white; border: none; }"
                " QPushButton:hover { background-color: #B71C1C; }")
            salir_btn.clicked.connect(self.close)
            action_layout.addWidget(salir_btn)
            layout.addLayout(action_layout)

            log_group = QGroupBox("📝 Logs en Tiempo Real")
            log_layout = QVBoxLayout()
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setFont(QFont("Consolas", 10))
            log_layout.addWidget(self.log_text)
            log_group.setLayout(log_layout)
            layout.addWidget(log_group, stretch=1)

        def _poll_logs(self) -> None:
            if not log_file or not os.path.exists(log_file):
                return
            try:
                current_size = os.path.getsize(log_file)
                if current_size == self._last_log_size:
                    return
                self._last_log_size = current_size
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                self.log_text.setPlainText(content)
                self.log_text.verticalScrollBar().setValue(
                    self.log_text.verticalScrollBar().maximum()
                )
            except Exception:
                pass

        def _log(self, message: str, level: str = "info") -> None:
            self.log_text.append(message)
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )

        def _run_sync(self, entity: str | None) -> None:
            if self.sync_worker and self.sync_worker.isRunning():
                QMessageBox.warning(self, "Aviso", "Ya hay una sincronización en progreso")
                return

            self.lbl_progress.setText("⏳ Sincronizando..." if entity else "⏳ Sincronizando todo...")
            entity_name = entity.upper() if entity else "TODO"
            self._log(f"\n🔄 INICIANDO SINCRONIZACIÓN {entity_name}...")

            self.sync_worker = SyncWorker(entity, config)
            self.sync_worker.log_msg.connect(self._log)
            self.sync_worker.finished.connect(self._on_sync_finished)
            self.sync_worker.start()

        def _on_sync_finished(self, result: dict) -> None:
            self.lbl_progress.setText("")
            if result.get('success'):
                self._log("✅ Sincronización completada exitosamente")
            else:
                err = result.get('error', 'Error desconocido')
                self._log(f"❌ Error: {err}", "error")
                QMessageBox.warning(self, "⚠️ Error", f"Sincronización falló:\n{err}")

        def _save_interval(self) -> None:
            interval = str(self.interval_spin.value())

            # Guardar solo en archivo de configuracion
            try:
                import os
                cfg_path = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")
                if os.path.exists(cfg_path):
                    from config_encryption import decrypt_config, encrypt_config
                    with open(cfg_path, 'r') as f:
                        enc_data = json.load(f)
                    cfg_data = decrypt_config(enc_data)
                    cfg_data['sync_interval_minutes'] = interval
                    new_enc = encrypt_config(cfg_data)
                    with open(cfg_path, 'w') as f:
                        json.dump(new_enc, f, indent=2)
            except Exception as e:
                QMessageBox.critical(self, "Error",
                    f"No se pudo guardar el intervalo:\n{e}")
                return

            QMessageBox.information(self, "Intervalo guardado",
                f"Intervalo actualizado a {interval} minutos.\n\n"
                "IMPORTANTE: Para que el cambio tenga efecto debe:\n"
                "  1. Cerrar completamente el programa\n"
                "  2. Volver a iniciarlo")

            self._log(f"Intervalo actualizado a {interval} minutos (requiere reinicio)")

        def _open_logs(self) -> None:
            if not log_file:
                QMessageBox.information(self, "Logs", "No hay archivo de logs configurado")
                return
            import subprocess
            sp_args = ([sys.executable, '--log-window', log_file]
                      if getattr(sys, 'frozen', False)
                      else [sys.executable, __file__, '--log-window', log_file])
            subprocess.run(sp_args, capture_output=True, text=True, timeout=120,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)

        def _reconfig(self) -> None:
            if QMessageBox.question(self, "Reconfigurar",
                    "¿Está seguro de reconfigurar desde cero?\nSe borrará la configuración actual.",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
                QMessageBox.information(self, "Reconfiguración",
                    "Configuración eliminada.\nEjecute --mode config para reconfigurar.")
                self.close()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ManagerWindow()
    window.show()
    app.exec()


def _handle_launcher_window(result_path: str) -> None:
    """Muestra menú principal con PySide6 en proceso separado.

    Args:
        result_path: Ruta donde guardar el resultado JSON
    """
    import sys
    import os
    import json
    import subprocess
    from PySide6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QMessageBox
    )
    from PySide6.QtCore import Qt

    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".chrystal_sync_config.json")

    class LauncherDialog(QDialog):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Sincronizador API REST - Chrystal")
            icon = _get_window_icon()
            if icon:
                self.setWindowIcon(icon)
            self.setFixedSize(600, 500)
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            self.setStyleSheet("""
                QDialog { background-color: #ecf0f1; }
                QPushButton {
                    font-size: 13px; padding: 12px 24px;
                    border-radius: 4px; border: none; font-weight: bold;
                }
                QPushButton:hover { opacity: 0.9; }
            """)

            self.has_config = os.path.exists(CONFIG_FILE)
            self.action = "exit"  # tray | exit
            self._build_ui()
            self._update_buttons()

        def _build_ui(self) -> None:
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            # --- Header ---
            header = QLabel("🔄 Sincronizador API REST")
            header.setStyleSheet(
                "background-color: #2c3e50; color: white; font-size: 20px;"
                " font-weight: bold; padding: 24px;")
            header.setAlignment(Qt.AlignCenter)
            header.setFixedHeight(100)
            layout.addWidget(header)

            subtitle = QLabel("Sistema de Sincronización Chrystal")
            subtitle.setStyleSheet(
                "background-color: #2c3e50; color: #bdc3c7;"
                " font-size: 11px; padding: 0 0 16px 0; margin-top: -10px;")
            subtitle.setAlignment(Qt.AlignCenter)
            layout.addWidget(subtitle)

            # --- Warning ---
            self.warning_label = QLabel(
                "⚠️ Primera vez: Debe configurar el sistema antes de usarlo")
            self.warning_label.setStyleSheet(
                "background-color: #fff3cd; color: #856404;"
                " font-size: 11px; font-weight: bold; padding: 14px 20px;"
                " margin: 10px 20px 0 20px; border: 1px solid #ffc107;"
                " border-radius: 4px;")
            layout.addWidget(self.warning_label)

            # --- Buttons ---
            btn_container = QVBoxLayout()
            btn_container.setAlignment(Qt.AlignCenter)
            btn_container.setSpacing(8)
            btn_container.setContentsMargins(40, 20, 40, 10)

            self.btn_config = QPushButton("⚙️ CONFIGURAR SISTEMA")
            self.btn_config.setStyleSheet(
                "QPushButton { background-color: #3498db; color: white; min-width: 320px; }"
                " QPushButton:hover { background-color: #2980b9; }")
            self.btn_config.clicked.connect(self._on_config)
            btn_container.addWidget(self.btn_config)

            self.btn_manager = QPushButton("🖥️ ABRIR MANAGER")
            self.btn_manager.setStyleSheet(
                "QPushButton { background-color: #2ecc71; color: white; min-width: 320px; }"
                " QPushButton:hover { background-color: #27ae60; }")
            self.btn_manager.clicked.connect(self._on_manager)
            btn_container.addWidget(self.btn_manager)

            self.btn_tray = QPushButton("📬 MODO SYSTEM TRAY")
            self.btn_tray.setStyleSheet(
                "QPushButton { background-color: #9b59b6; color: white; min-width: 320px; }"
                " QPushButton:hover { background-color: #8e44ad; }")
            self.btn_tray.clicked.connect(self._on_tray)
            btn_container.addWidget(self.btn_tray)

            self.btn_sync = QPushButton("🔄 SINCRONIZAR AHORA")
            self.btn_sync.setStyleSheet(
                "QPushButton { background-color: #e67e22; color: white; min-width: 320px; }"
                " QPushButton:hover { background-color: #d35400; }")
            self.btn_sync.clicked.connect(self._on_sync)
            btn_container.addWidget(self.btn_sync)

            self.btn_reconfig = QPushButton("🔧 RECONFIGURAR")
            self.btn_reconfig.setStyleSheet(
                "QPushButton { background-color: #95a5a6; color: white; min-width: 320px; }"
                " QPushButton:hover { background-color: #7f8c8d; }")
            self.btn_reconfig.clicked.connect(self._on_reconfig)
            btn_container.addWidget(self.btn_reconfig)

            layout.addLayout(btn_container)

            # --- Salir ---
            exit_layout = QHBoxLayout()
            exit_layout.setContentsMargins(40, 0, 40, 10)
            self.btn_exit = QPushButton("❌ Salir")
            self.btn_exit.setStyleSheet(
                "QPushButton { background-color: #C62828; color: white; min-width: 100px; }"
                " QPushButton:hover { background-color: #B71C1C; }")
            self.btn_exit.clicked.connect(self.reject)
            exit_layout.addStretch()
            exit_layout.addWidget(self.btn_exit)
            layout.addLayout(exit_layout)

            # --- Footer ---
            footer = QLabel("v1.0 - Sistema de Sincronización PostgreSQL → API REST")
            footer.setStyleSheet("color: #7f8c8d; font-size: 9px; padding: 6px;")
            footer.setAlignment(Qt.AlignCenter)
            layout.addWidget(footer)

            self.setLayout(layout)

        def _update_buttons(self) -> None:
            self.has_config = os.path.exists(CONFIG_FILE)
            self.warning_label.setVisible(not self.has_config)
            self.btn_manager.setEnabled(self.has_config)
            self.btn_tray.setEnabled(self.has_config)
            self.btn_sync.setEnabled(self.has_config)
            self.btn_reconfig.setEnabled(self.has_config)

        def _run_subprocess(self, args: list[str], wait: bool = True):
            creationflags = 0
            if sys.platform == 'win32':
                creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            try:
                if wait:
                    result = subprocess.run(args, capture_output=True, text=True, timeout=600,
                                           creationflags=creationflags)
                    return result.returncode
                else:
                    subprocess.Popen(args, creationflags=creationflags)
                    return None
            except Exception as e:
                print(f"Error launching subprocess: {e}")
                return -1

        def _exe_args(self, *extra: str) -> list[str]:
            if getattr(sys, 'frozen', False):
                return [sys.executable, *extra]
            return [sys.executable, __file__, *extra]

        def _on_config(self) -> None:
            self._run_subprocess(self._exe_args('--mode', 'config'), wait=True)
            self._update_buttons()

        def _on_manager(self) -> None:
            import tempfile
            cfg_data = {}
            if os.path.exists(CONFIG_FILE):
                try:
                    from config_encryption import decrypt_config
                    with open(CONFIG_FILE) as f:
                        cfg_data = decrypt_config(json.load(f))
                except Exception:
                    cfg_data = {}
            cfg_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
                    cfg_path = f.name
                    json.dump(cfg_data, f)
                self._run_subprocess(self._exe_args('--manager-window', cfg_path), wait=True)
            except Exception as e:
                print(f"Error en manager: {e}")
            finally:
                if cfg_path:
                    try: os.unlink(cfg_path)
                    except: pass

        def _on_tray(self) -> None:
            self.action = "tray"
            self._run_subprocess(self._exe_args('--mode', 'tray'), wait=False)
            self.accept()

        def _on_sync(self) -> None:
            self._run_subprocess(self._exe_args('--mode', 'sync'), wait=True)

        def _on_reconfig(self) -> None:
            if QMessageBox.question(self, "Reconfigurar",
                    "¿Está seguro que desea borrar la configuración?\n\n"
                    "Tendrá que configurar el sistema nuevamente.",
                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
                self._update_buttons()
                self._on_config()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    dialog = LauncherDialog()
    dialog.exec()

    with open(result_path, 'w') as f:
        json.dump({"action": dialog.action}, f)


def _handle_confirm_dialog(result_path: str) -> None:
    """Muestra diálogo de confirmación Sí/No con PySide6 en proceso separado.

    Args:
        result_path: Ruta donde guardar el resultado JSON
    """
    import sys
    import json
    from PySide6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton
    )
    from PySide6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dialog = QDialog()
    dialog.setWindowTitle("Confirmar")
    icon = _get_window_icon()
    if icon:
        dialog.setWindowIcon(icon)
    dialog.setFixedSize(400, 160)
    dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
    dialog.setStyleSheet("""
        QDialog { background-color: #f5f5f5; }
        QLabel { font-size: 13px; color: #333; }
        QPushButton { font-size: 13px; padding: 8px 24px; border-radius: 4px; border: none; font-weight: bold; }
    """)

    layout = QVBoxLayout()
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(16)

    msg = QLabel(
        "¿Estás seguro que deseas salir del\n"
        "Sistema de Sincronización?\n\n"
        "Esto detendrá la sincronización automática."
    )
    msg.setAlignment(Qt.AlignCenter)
    layout.addWidget(msg)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch()

    yes_btn = QPushButton("✅ Sí, salir")
    yes_btn.setStyleSheet(
        "QPushButton { background-color: #C62828; color: white; }"
        " QPushButton:hover { background-color: #B71C1C; }")
    yes_btn.clicked.connect(lambda: (
        open(result_path, 'w').write(json.dumps({"confirmed": True})),
        dialog.accept()
    ))
    btn_layout.addWidget(yes_btn)

    no_btn = QPushButton("❌ Cancelar")
    no_btn.setStyleSheet(
        "QPushButton { background-color: #555; color: white; }"
        " QPushButton:hover { background-color: #444; }")
    no_btn.clicked.connect(lambda: (
        open(result_path, 'w').write(json.dumps({"confirmed": False})),
        dialog.reject()
    ))
    btn_layout.addWidget(no_btn)

    btn_layout.addStretch()
    layout.addLayout(btn_layout)
    dialog.setLayout(layout)

    dialog.exec()


def _check_single_instance() -> bool:
    """Evita múltiples instancias del programa.

    En Windows usa un mutex del sistema (CreateMutexW).
    En Linux/macOS usa un archivo de bloqueo.

    Returns:
        True si es la única instancia, False si ya hay otra corriendo.
    """
    import sys as _sys
    if _sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            mutex_name = "ChrystalSyncSystem-InstanceMutex"
            kernel32.CreateMutexW(None, False, mutex_name)
            if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
                # Notificar al usuario
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "El Sincronizador Chrystal ya está ejecutándose.\n\n"
                    "Revise la bandeja del sistema (System Tray).",
                    "Sincronizador Chrystal",
                    0x10 | 0x0  # MB_ICONHAND | MB_OK
                )
                return False
        except Exception:
            pass  # Si falla el mutex, permitir ejecución
    else:
        # Linux/macOS: lock file en /tmp
        import os as _os
        _lock = "/tmp/chrystal_sync.lock"
        try:
            _fd = _os.open(_lock, _os.O_CREAT | _os.O_EXCL | _os.O_RDWR)
            _os.close(_fd)
        except FileExistsError:
            print("Ya hay una instancia del Sincronizador Chrystal ejecutándose.")
            return False
        except Exception:
            pass
    return True


def main():
    """Función principal."""

    import sys
    if not _check_single_instance():
        return


    # Verificar si es ejecutable compilado y no hay argumentos
    # O si no se pasan argumentos explícitos
    is_exe = getattr(sys, 'frozen', False)
    no_args = len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[0].endswith('.exe'))

    if is_exe and no_args:
        # MODO AUTOMÁTICO para .exe
        # Dos caminos:
        #   1. Sin config  → autenticar → ConfigWindow (sync + tray en thread)
        #   2. Con config  → validar API Key → sync → tray bloqueante

        if not os.path.exists(CONFIG_FILE):
            # ---- CAMINO 1: PRIMERA CONFIGURACIÓN ----
            # Validar identidad del usuario (email/password) antes de configurar
            try:
                _cfg_first = {'api_url': 'https://chrystal.com.ve/mobiletest/public/api'}
                _tray_first = SystemTrayService(_cfg_first, None)
                if not _tray_first.reautenticar_usuario():
                    print("❌ Verificación de identidad fallida o cancelada")
                    return
            except Exception as e:
                print(f"❌ Error en verificación de identidad: {e}")
                return

            auth_result = autenticar_para_config()
            if not auth_result or not auth_result.get('success', False):
                print("❌ Acceso denegado: autenticación fallida o cancelada")
                return

            # Lanzar ConfigWindow con PySide6 en proceso separado
            import subprocess as _sp
            import json as _json
            import tempfile
            _result_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as _f:
                    _result_path = _f.name
                if getattr(sys, 'frozen', False):
                    _sp_args = [sys.executable, '--config-window', _result_path]
                else:
                    _sp_args = [sys.executable, __file__, '--config-window', _result_path]
                _sp.run(_sp_args, capture_output=True, text=True, timeout=300,
                        creationflags=getattr(_sp, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)
                try:
                    with open(_result_path) as _f:
                        _cfg_data = _json.load(_f)
                except Exception:
                    _cfg_data = {}
                if _cfg_data.get('saved'):
                    from config_encryption import encrypt_config
                    _encrypted = encrypt_config({k: v for k, v in _cfg_data.items() if k != 'saved'})
                    with open(CONFIG_FILE, 'w') as _f:
                        _json.dump(_encrypted, _f, indent=2)
                    print("✅ Configuración guardada")
            except Exception as _e:
                print(f"❌ Error en configuración: {_e}")
            finally:
                if _result_path and os.path.exists(_result_path):
                    os.unlink(_result_path)

            # Iniciar System Tray si hay configuración.
            if os.path.exists(CONFIG_FILE):
                print("\n" + "="*70)
                print("📬 INICIANDO SYSTEM TRAY...")
                print("="*70)
                try:
                    from config_encryption import decrypt_config
                    with open(CONFIG_FILE, 'r') as f:
                        _cfg_enc = json.load(f)
                    _cfg = decrypt_config(_cfg_enc)
                    _key = _cfg.get('api_key', '')
                    if _key:
                        print("🔐 Validando API Key...")
                        _auth = APIAuthManager(base_url=_cfg.get('api_url', 'https://chrystal.com.ve/mobiletest/public/api'))
                        _cv_ping = _get_chrystal_version({
                            'host': _cfg.get('postgres_host', ''),
                            'port': _cfg.get('postgres_port', ''),
                            'database': _cfg.get('postgres_database', ''),
                            'user': _cfg.get('postgres_user', ''),
                            'password': _cfg.get('postgres_password', ''),
                        })
                        _ping = _auth.ping_api_key(_key, chrystal_version=_cv_ping)
                        if _ping.get('success'):
                            _auth.validate_company(_cfg['company_rif'], _cfg['company_email'])
                            SystemTrayService(_cfg, _key).iniciar()
                        else:
                            print(f"❌ API Key inválida: {_ping.get('error', 'Error')}")
                    else:
                        print("❌ No hay API Key en la configuración")
                except Exception as e:
                    print(f"❌ Error iniciando System Tray: {e}")
                    import traceback
                    traceback.print_exc()
            return

        # ---- CAMINO 2: YA HAY CONFIGURACIÓN ----
        # Ir directamente a validar API Key, sincronizar e iniciar System Tray
        print("\n" + "="*70)
        print("📬 INICIANDO SYSTEM TRAY...")
        print("="*70)
        try:
            from config_encryption import decrypt_config
            with open(CONFIG_FILE, 'r') as f:
                _cfg_enc = json.load(f)
            _cfg = decrypt_config(_cfg_enc)
            _key = _cfg.get('api_key', '')
            if _key:
                print("🔐 Validando API Key...")
                _auth = APIAuthManager(base_url=_cfg.get('api_url', 'https://chrystal.com.ve/mobiletest/public/api'))
                _cv_ping = _get_chrystal_version({
                    'host': _cfg.get('postgres_host', ''),
                    'port': _cfg.get('postgres_port', ''),
                    'database': _cfg.get('postgres_database', ''),
                    'user': _cfg.get('postgres_user', ''),
                    'password': _cfg.get('postgres_password', ''),
                })
                _ping = _auth.ping_api_key(_key, chrystal_version=_cv_ping)
                if _ping.get('success'):
                    _auth.validate_company(_cfg['company_rif'], _cfg['company_email'])
                    SystemTrayService(_cfg, _key).iniciar()
                else:
                    print(f"❌ API Key inválida: {_ping.get('error', 'Error')}")
            else:
                print("❌ No hay API Key en la configuración")
        except Exception as e:
            print(f"❌ Error iniciando System Tray: {e}")
            import traceback
            traceback.print_exc()
        return

    # Modo normal con argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Sincronizador API REST")
    parser.add_argument("--mode", choices=["config", "manager", "reconfig", "sync", "service", "tray"],
                       default="manager", help="Modo de ejecución")
    parser.add_argument("--once", action="store_true",
                       help="En modo service, ejecutar una sola vez y salir")
    parser.add_argument("--auth-dialog", metavar="RESULT_PATH",
                       help=argparse.SUPPRESS)
    parser.add_argument("--auth-error", metavar="MSG",
                       help=argparse.SUPPRESS)
    parser.add_argument("--log-window", metavar="LOG_FILE",
                       help=argparse.SUPPRESS)
    parser.add_argument("--config-window", metavar="RESULT_PATH",
                       help=argparse.SUPPRESS)
    parser.add_argument("--manager-window", metavar="CONFIG_PATH",
                       help=argparse.SUPPRESS)
    parser.add_argument("--launcher-window", metavar="RESULT_PATH",
                       help=argparse.SUPPRESS)
    parser.add_argument("--confirm-dialog", metavar="RESULT_PATH",
                       help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Si se pasa --auth-dialog, mostrar diálogo en proceso propio y salir
    if args.auth_dialog:
        return _handle_auth_dialog(args.auth_dialog, args.auth_error or "")

    # Si se pasa --log-window, mostrar visor de logs en proceso propio y salir
    if args.log_window:
        return _handle_log_window(args.log_window)

    # Si se pasa --config-window, mostrar config en proceso propio y salir
    if args.config_window:
        return _handle_config_window(args.config_window)

    # Si se pasa --manager-window, mostrar manager en proceso propio y salir
    if args.manager_window:
        return _handle_manager_window(args.manager_window)

    # Si se pasa --launcher-window, mostrar menú principal en proceso propio y salir
    if args.launcher_window:
        return _handle_launcher_window(args.launcher_window)

    # Si se pasa --confirm-dialog, mostrar confirmación en proceso propio y salir
    if args.confirm_dialog:
        return _handle_confirm_dialog(args.confirm_dialog)

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
            # Lanzar ConfigWindow con PySide6 en proceso separado
            import subprocess as _sp
            import json as _json
            import tempfile
            _result_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as _f:
                    _result_path = _f.name
                _sp_args = ([sys.executable, '--config-window', _result_path]
                           if getattr(sys, 'frozen', False)
                           else [sys.executable, __file__, '--config-window', _result_path])
                _sp.run(_sp_args, capture_output=True, text=True, timeout=300,
                        creationflags=getattr(_sp, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)
                try:
                    with open(_result_path) as _f:
                        _cfg_data = _json.load(_f)
                except Exception:
                    _cfg_data = {}
                if _cfg_data.get('saved'):
                    from config_encryption import encrypt_config
                    _encrypted = encrypt_config({k: v for k, v in _cfg_data.items() if k != 'saved'})
                    with open(CONFIG_FILE, 'w') as _f:
                        _json.dump(_encrypted, _f, indent=2)
                    print("✅ Configuración guardada")
                else:
                    print("❌ Configuración no completada o cancelada")
                    sys.exit(1)
            except Exception as _e:
                print(f"❌ Error en configuración: {_e}")
                sys.exit(1)
            finally:
                if _result_path and os.path.exists(_result_path):
                    os.unlink(_result_path)

            # Iniciar System Tray
            if os.path.exists(CONFIG_FILE):
                print("\n" + "="*70)
                print("📬 INICIANDO SYSTEM TRAY...")
                print("="*70)
                try:
                    from config_encryption import decrypt_config
                    with open(CONFIG_FILE, 'r') as f:
                        _cfg_enc = json.load(f)
                    _cfg = decrypt_config(_cfg_enc)
                    _key = _cfg.get('api_key', '')
                    if _key:
                        print("🔐 Validando API Key...")
                        _auth = APIAuthManager(base_url=_cfg.get('api_url', 'https://chrystal.com.ve/mobiletest/public/api'))
                        _cv_ping = _get_chrystal_version({
                            'host': _cfg.get('postgres_host', ''),
                            'port': _cfg.get('postgres_port', ''),
                            'database': _cfg.get('postgres_database', ''),
                            'user': _cfg.get('postgres_user', ''),
                            'password': _cfg.get('postgres_password', ''),
                        })
                        _ping = _auth.ping_api_key(_key, chrystal_version=_cv_ping)
                        if _ping.get('success'):
                            _auth.validate_company(_cfg['company_rif'], _cfg['company_email'])
                            SystemTrayService(_cfg, _key).iniciar()
                        else:
                            print(f"❌ API Key inválida: {_ping.get('error', 'Error')}")
                    else:
                        print("❌ No hay API Key en la configuración")
                except Exception as e:
                    print(f"❌ Error iniciando System Tray: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            print("❌ Acceso a configuración denegado: autenticación fallida o cancelada")
            sys.exit(1)

    elif args.mode == "manager":
        # Manager con PySide6 en proceso separado
        import tempfile, subprocess as _sp_mgr
        _cfg_mgr = {}
        if os.path.exists(CONFIG_FILE):
            try:
                from config_encryption import decrypt_config
                with open(CONFIG_FILE) as _f:
                    _cfg_mgr = decrypt_config(json.load(_f))
            except Exception:
                _cfg_mgr = {}

        _cfg_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as _f:
                _cfg_path = _f.name
                json.dump(_cfg_mgr, _f)

            _mgr_args = ([sys.executable, '--manager-window', _cfg_path]
                       if getattr(sys, 'frozen', False)
                       else [sys.executable, __file__, '--manager-window', _cfg_path])
            _sp_mgr.run(_mgr_args, capture_output=True, text=True, timeout=None,
                       creationflags=getattr(_sp_mgr, 'CREATE_NO_WINDOW', 0) if sys.platform == 'win32' else 0)
        except Exception as _e:
            print(f"❌ Error en Manager: {_e}")
        finally:
            if _cfg_path:
                try: os.unlink(_cfg_path)
                except: pass

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
        _cv_ping = _get_chrystal_version({
            'host': config.get('postgres_host', ''),
            'port': config.get('postgres_port', ''),
            'database': config.get('postgres_database', ''),
            'user': config.get('postgres_user', ''),
            'password': config.get('postgres_password', ''),
        })
        ping_result = auth_manager.ping_api_key(config.get('api_key', api_key), chrystal_version=_cv_ping)
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
