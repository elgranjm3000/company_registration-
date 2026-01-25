#!/usr/bin/env python3
"""
SISTEMA DE SINCRONIZACIÓN INTELIGENTE - EJECUTABLE ÚNICO
=========================================================
Este archivo contiene TODO el sistema en un solo ejecutable:
- Configuración GUI (primera ejecución)
- Servicio de Windows
- Interfaz de Administración

Autor: Sistema de Sincronización
Versión: 2.0
Fecha: 2025-01-23
"""

import os
import sys
import time
import json
import argparse
import base64
import hashlib
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Encriptación de credenciales
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    import warnings
    warnings.warn("cryptography no está instalado. Las credenciales estarán en base64 (menos seguro)")

# Detectar si estamos corriendo en PyInstaller
if getattr(sys, 'frozen', False):
    # Si está empaquetado, usar el directorio temporal de PyInstaller
    BASE_DIR = sys._MEIPASS
else:
    # Si está en desarrollo, usar el directorio del script
    try:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Si __file__ no está definido (ej: exec()), usar directorio actual
        BASE_DIR = os.path.abspath('.')

# Importar dependencias con manejo de errores
try:
    import psycopg2
    import pymysql
except ImportError as e:
    print(f"Error: Falta dependencia: {e}")
    print("Ejecute: pip install psycopg2-binary pymysql")
    sys.exit(1)

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

CONFIG_FILE = "sync_config.json"

# Crear directorio de logs
import os
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Archivo de log principal (en carpeta logs/)
LOG_FILE = os.path.join(LOGS_DIR, "sync_system.log")

# ==============================================================================
# UTILIDADES
# ==============================================================================

def log(mensaje="", nivel="INFO"):
    """Escribe log al archivo"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{nivel}] {mensaje}\n"
    print(log_line.strip())

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception as e:
        print(f"Error escribiendo log: {e}")

def crear_config_default():
    """Crea configuración por defecto"""
    return {
        # PostgreSQL (configurable por el usuario)
        "postgres_host": "localhost",
        "postgres_port": "5432",
        "postgres_database": "",
        "postgres_user": "postgres",
        "postgres_password": "",

        # MySQL (HARDCODED - oculto para el usuario)
        "mysql_host": "91.238.160.176",
        "mysql_port": "3306",
        "mysql_database": "chrystal_movil",
        "mysql_user": "chrystal_app",
        "mysql_password": "muentes123.",

        # Empresa (configurable por el usuario)
        "company_rif": "",
        "company_email": "",

        # Sincronización (configurable por el usuario)
        "sync_interval_minutes": "30",

        # Estado
        "configured": False,
        "first_run": True
    }

# ============================================================================
# FUNCIONES DE ENCRIPTACIÓN DE CREDENCIALES
# ============================================================================

def _generar_key():
    """
    Genera una key fija basada en un secreto incrustado en el código
    Esto permite que la key sea la misma en todas las ejecuciones
    """
    # Secreto fijo (no cambiar una vez en uso)
    secreto = "SyncSystem2024-KeyFija-MySQL-Creds".encode()
    # Generar key de 32 bytes para Fernet
    return base64.urlsafe_b64encode(hashlib.sha256(secreto).digest())

def encriptar_credencial(texto_plano):
    """Encripta una credencial usando Fernet (o base64 como fallback)"""
    if CRYPTO_AVAILABLE:
        key = _generar_key()
        f = Fernet(key)
        return f.encrypt(texto_plano.encode()).decode()
    else:
        # Fallback: base64 simple (menos seguro pero oculta el texto)
        return base64.b64encode(texto_plano.encode()).decode()

def desencriptar_credencial(texto_encriptado):
    """Desencripta una credencial"""
    if CRYPTO_AVAILABLE:
        key = _generar_key()
        f = Fernet(key)
        return f.decrypt(texto_encriptado.encode()).decode()
    else:
        # Fallback: base64
        return base64.b64decode(texto_encriptado.encode()).decode()

def obtener_config_mysql():
    """
    Retorna la configuración de MySQL con credenciales encriptadas
    Las credenciales están codificadas para no ser visibles en texto plano
    """
    return {
        'host': desencriptar_credencial("OTEuMjM4LjE2MC4xNzY="),
        'port': desencriptar_credencial("MzMwNg=="),
        'database': desencriptar_credencial("Y2hyeXN0YWxfbW92aWw="),
        'user': desencriptar_credencial("Y2hyeXN0YWxfYXBw"),
        'password': desencriptar_credencial("bXVlbnRlczEyMy4=")
    }

def cargar_config():
    """Carga configuración desde archivo"""
    if not os.path.exists(CONFIG_FILE):
        return crear_config_default()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error cargando config: {e}", "ERROR")
        return crear_config_default()

def guardar_config(config):
    """Guarda configuración a archivo"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        log(f"Error guardando config: {e}", "ERROR")
        return False

# ==============================================================================
# MÓDULO DE SINCRONIZACIÓN
# ==============================================================================

class SyncModule:
    """Módulo de sincronización"""

    def __init__(self, config):
        self.config = config
        self.pg_conn = None
        self.mysql_conn = None
        self.stats = {
            'products': {'nuevos': 0, 'modificados': 0},
            'customers': {'nuevos': 0, 'modificados': 0},
            'categories': {'nuevos': 0, 'modificados': 0},
            'quotes': {'nuevos': 0, 'errores': 0}
        }

    def log_message(self, mensaje: str, tipo: str = "info"):
        """
        Método compatible con SmartSyncComplete
        Muestra logs en consola con formato
        """
        prefijos = {
            'info': 'ℹ️ INFO',
            'success': '✅ SUCCESS',
            'warning': '⚠️ WARNING',
            'error': '❌ ERROR',
            'debug': '🔍 DEBUG'
        }

        prefijo = prefijos.get(tipo, 'ℹ️ INFO')
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {prefijo}: {mensaje}")

        # También guardar en archivo de log
        log(mensaje, tipo.upper())

    def conectar_postgresql(self):
        """Conecta a PostgreSQL"""
        try:
            self.pg_conn = psycopg2.connect(
                host=self.config['postgres_host'],
                port=int(self.config['postgres_port']),
                database=self.config['postgres_database'],
                user=self.config['postgres_user'],
                password=self.config['postgres_password']
            )
            log("Conectado a PostgreSQL", "INFO")
            return True
        except Exception as e:
            log(f"Error conectando PostgreSQL: {e}", "ERROR")
            return False

    def conectar_mysql(self):
        """Conecta a MySQL"""
        try:
            self.mysql_conn = pymysql.connect(
                host=self.config['mysql_host'],
                port=int(self.config['mysql_port']),
                database=self.config['mysql_database'],
                user=self.config['mysql_user'],
                password=self.config['mysql_password']
            )
            log("Conectado a MySQL", "INFO")
            return True
        except Exception as e:
            log(f"Error conectando MySQL: {e}", "ERROR")
            return False

    def verificar_conexiones(self):
        """Verifica que ambas conexiones funcionen"""
        if not self.pg_conn:
            if not self.conectar_postgresql():
                return False
        if not self.mysql_conn:
            if not self.conectar_mysql():
                return False
        return True

    def sincronizar(self):
        """Ejecuta sincronización completa"""
        log("=== INICIANDO SINCRONIZACIÓN ===", "INFO")

        if not self.verificar_conexiones():
            log("No se pueden establecer conexiones", "ERROR")
            return False

        # Importar el módulo de sincronización completo
        try:
            # Importar desde smart_sync_complete.py
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "smart_sync_complete",
                os.path.join(BASE_DIR, "smart_sync_complete.py")
            )
            sync_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_module)

            # Preparar configuraciones
            postgresql_config = {
                'host': self.config['postgres_host'],
                'port': self.config['postgres_port'],
                'database': self.config['postgres_database'],
                'user': self.config['postgres_user'],
                'password': self.config['postgres_password']
            }

            mysql_config = {
                'host': self.config['mysql_host'],
                'port': self.config['mysql_port'],
                'database': self.config['mysql_database'],
                'user': self.config['mysql_user'],
                'password': self.config['mysql_password']
            }

            # Crear instancia y ejecutar (self es el 'app')
            sync_system = sync_module.SmartSyncComplete(
                app=self,
                postgresql_config=postgresql_config,
                mysql_config=mysql_config,
                company_rif=self.config['company_rif'],
                company_email=self.config['company_email']
            )

            # Inicializar tabla sync_hashes si no existe
            if not sync_system.inicializar_tabla_hashes():
                log("Error: No se pudo inicializar la tabla sync_hashes", "ERROR")
                return False

            resultado = sync_system.ejecutar_sync_completa()

            log("=== SINCRONIZACIÓN COMPLETADA ===", "INFO")
            return resultado

        except Exception as e:
            log(f"Error en sincronización: {e}", "ERROR")
            return False

    def cerrar(self):
        """Cierra conexiones"""
        if self.pg_conn:
            self.pg_conn.close()
        if self.mysql_conn:
            self.mysql_conn.close()

# ==============================================================================
# GUI DE CONFIGURACIÓN (PRIMERA EJECUCIÓN)
# ==============================================================================

class ConfigWindow:
    """Ventana de configuración"""

    def __init__(self, root):
        self.root = root
        self.root.title("Configuración - Sistema de Sincronización")
        self.root.geometry("700x650")
        self.root.resizable(False, False)

        # Centrar ventana
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        self.config = cargar_config()
        self.crear_gui()

    def crear_gui(self):
        """Crea la interfaz gráfica"""

        # Título
        titulo = tk.Label(
            self.root,
            text="⚙️ Configuración del Sistema de Sincronización",
            font=("Arial", 16, "bold"),
            pady=10
        )
        titulo.pack()

        # Notebook para pestañas
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Pestaña PostgreSQL
        frame_pg = ttk.Frame(notebook)
        notebook.add(frame_pg, text="🐘 PostgreSQL")

        self.crear_campos_postgresql(frame_pg)

        # Pestaña MySQL (OCULTA - credenciales harcodeadas)
        # frame_mysql = ttk.Frame(notebook)
        # notebook.add(frame_mysql, text="🐬 MySQL")
        # self.crear_campos_mysql(frame_mysql)

        # Pestaña Empresa
        frame_empresa = ttk.Frame(notebook)
        notebook.add(frame_empresa, text="🏢 Empresa")

        self.crear_campos_empresa(frame_empresa)

        # Pestaña Configuración
        frame_conf = ttk.Frame(notebook)
        notebook.add(frame_conf, text="⏰ Configuración")

        self.crear_campos_configuracion(frame_conf)

        # Botones
        frame_botones = ttk.Frame(self.root)
        frame_botones.pack(fill="x", padx=10, pady=10)

        ttk.Button(frame_botones, text="💾 Guardar", command=self.guardar).pack(side="right", padx=5)
        ttk.Button(frame_botones, text="❌ Cancelar", command=self.root.quit).pack(side="right")

        # Estado
        self.estado = tk.Label(self.root, text="✏️ Configure los datos y click en Guardar", fg="blue")
        self.estado.pack(pady=5)

    def crear_campos_postgresql(self, parent):
        """Crea campos de PostgreSQL"""
        campos = [
            ("Host:", "postgres_host", self.config.get('postgres_host', 'localhost')),
            ("Puerto:", "postgres_port", self.config.get('postgres_port', '5432')),
            ("Database:", "postgres_database", self.config.get('postgres_database', '')),
            ("Usuario:", "postgres_user", self.config.get('postgres_user', 'postgres')),
            ("Password:", "postgres_password", self.config.get('postgres_password', '')),
        ]

        frame = ttk.LabelFrame(parent, text="Conexión PostgreSQL", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.entry_pg = {}

        for i, (label, key, default) in enumerate(campos):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=5, padx=5)

            entry = ttk.Entry(frame, width=40)
            entry.insert(0, default)
            if "password" in key:
                entry.config(show="*")
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.entry_pg[key] = entry

        # Botón de prueba de conexión
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(campos), column=0, columnspan=2, pady=10)

        self.btn_test_pg = ttk.Button(btn_frame, text="🔍 Probar Conexión PostgreSQL", command=self.probar_postgresql)
        self.btn_test_pg.pack()

        self.lbl_status_pg = ttk.Label(btn_frame, text="", font=("Arial", 9))
        self.lbl_status_pg.pack(pady=5)

    def crear_campos_mysql(self, parent):
        """Crea campos de MySQL"""
        campos = [
            ("Host:", "mysql_host", self.config.get('mysql_host', '')),
            ("Puerto:", "mysql_port", self.config.get('mysql_port', '3306')),
            ("Database:", "mysql_database", self.config.get('mysql_database', '')),
            ("Usuario:", "mysql_user", self.config.get('mysql_user', '')),
            ("Password:", "mysql_password", self.config.get('mysql_password', '')),
        ]

        frame = ttk.LabelFrame(parent, text="Conexión MySQL", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.entry_mysql = {}

        for i, (label, key, default) in enumerate(campos):
            ttk.Label(frame, text=label).grid(row=i, column=0, sticky="w", pady=5, padx=5)

            entry = ttk.Entry(frame, width=40)
            entry.insert(0, default)
            if "password" in key:
                entry.config(show="*")
            entry.grid(row=i, column=1, pady=5, padx=5)
            self.entry_mysql[key] = entry

        # Botón de prueba de conexión
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(campos), column=0, columnspan=2, pady=10)

        self.btn_test_mysql = ttk.Button(btn_frame, text="🔍 Probar Conexión MySQL", command=self.probar_mysql)
        self.btn_test_mysql.pack()

        self.lbl_status_mysql = ttk.Label(btn_frame, text="", font=("Arial", 9))
        self.lbl_status_mysql.pack(pady=5)

    def crear_campos_empresa(self, parent):
        """Crea campos de empresa"""
        frame = ttk.LabelFrame(parent, text="Datos de Empresa", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # RIF
        ttk.Label(frame, text="RIF:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.entry_rif = ttk.Entry(frame, width=40)
        self.entry_rif.insert(0, self.config.get('company_rif', ''))
        self.entry_rif.grid(row=0, column=1, pady=5, padx=5)

        # Email
        ttk.Label(frame, text="Email:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.entry_email = ttk.Entry(frame, width=40)
        self.entry_email.insert(0, self.config.get('company_email', ''))
        self.entry_email.grid(row=1, column=1, pady=5, padx=5)

        # Nombre de compañía
        ttk.Label(frame, text="Nombre:").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        self.entry_name = ttk.Entry(frame, width=40)
        self.entry_name.insert(0, self.config.get('company_name', ''))
        self.entry_name.grid(row=2, column=1, pady=5, padx=5)

        # Info
        info = tk.Label(frame, text="ℹ️ Estos datos se usan para identificar la empresa en la sincronización",
                       fg="gray", justify="left")
        info.grid(row=3, column=0, columnspan=2, pady=10, padx=5, sticky="w")

    def crear_campos_configuracion(self, parent):
        """Crea campos de configuración"""
        frame = ttk.LabelFrame(parent, text="Configuración de Sincronización", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Intervalo
        ttk.Label(frame, text="Intervalo de sincronización:").grid(row=0, column=0, sticky="w", pady=5, padx=5)

        self.intervalo = tk.StringVar(value=self.config.get('sync_interval_minutes', '30'))
        intervalos = ["2", "5", "15", "30", "60"]
        combo = ttk.Combobox(frame, textvariable=self.intervalo, values=intervalos, state="readonly", width=37)
        combo.grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(frame, text="minutos").grid(row=0, column=2, sticky="w", padx=5)

        # Info
        info = tk.Label(frame, text="ℹ️ El sistema se sincronizará automáticamente cada X minutos",
                       fg="gray", justify="left")
        info.grid(row=1, column=0, columnspan=3, pady=10, padx=5, sticky="w")

    def probar_postgresql(self):
        """Prueba la conexión a PostgreSQL"""
        self.lbl_status_pg.config(text="⏳ Probando...", foreground="orange")
        self.root.update()

        try:
            import psycopg2

            conn = psycopg2.connect(
                host=self.entry_pg['postgres_host'].get().strip(),
                port=self.entry_pg['postgres_port'].get().strip(),
                database=self.entry_pg['postgres_database'].get().strip(),
                user=self.entry_pg['postgres_user'].get().strip(),
                password=self.entry_pg['postgres_password'].get().strip()
            )

            # Probar una query simple
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            self.lbl_status_pg.config(text="✅ Conexión exitosa", foreground="green")
            self.estado.config(text="PostgreSQL: Conexión establecida", fg="green")

        except Exception as e:
            self.lbl_status_pg.config(text=f"❌ Error: {str(e)}", foreground="red")
            self.estado.config(text=f"PostgreSQL: Error de conexión", fg="red")

    def probar_mysql(self):
        """Prueba la conexión a MySQL"""
        self.lbl_status_mysql.config(text="⏳ Probando...", foreground="orange")
        self.root.update()

        try:
            import pymysql

            conn = pymysql.connect(
                host=self.entry_mysql['mysql_host'].get().strip(),
                port=int(self.entry_mysql['mysql_port'].get().strip()),
                database=self.entry_mysql['mysql_database'].get().strip(),
                user=self.entry_mysql['mysql_user'].get().strip(),
                password=self.entry_mysql['mysql_password'].get().strip()
            )

            # Probar una query simple
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            self.lbl_status_mysql.config(text="✅ Conexión exitosa", foreground="green")
            self.estado.config(text="MySQL: Conexión establecida", fg="green")

        except Exception as e:
            self.lbl_status_mysql.config(text=f"❌ Error: {str(e)}", foreground="red")
            self.estado.config(text=f"MySQL: Error de conexión", fg="red")

    def guardar(self):
        """Guarda la configuración"""
        # Obtener valores
        config_nuevo = {}

        # PostgreSQL (configurable por el usuario)
        for key, entry in self.entry_pg.items():
            config_nuevo[key] = entry.get().strip()

        # MySQL (HARDCODED - oculto para el usuario)
        mysql_config = obtener_config_mysql()
        config_nuevo['mysql_host'] = mysql_config['host']
        config_nuevo['mysql_port'] = mysql_config['port']
        config_nuevo['mysql_database'] = mysql_config['database']
        config_nuevo['mysql_user'] = mysql_config['user']
        config_nuevo['mysql_password'] = mysql_config['password']

        # Empresa (configurable por el usuario)
        config_nuevo['company_rif'] = self.entry_rif.get().strip()
        config_nuevo['company_email'] = self.entry_email.get().strip()
        config_nuevo['company_name'] = self.entry_name.get().strip()

        # Configuración
        config_nuevo['sync_interval_minutes'] = self.intervalo.get()

        # Validar (solo PostgreSQL y Empresa)
        if not all([
            config_nuevo.get('postgres_host'),
            config_nuevo.get('postgres_database'),
            config_nuevo.get('postgres_user'),
            config_nuevo.get('company_rif'),
            config_nuevo.get('company_email')
        ]):
            messagebox.showerror("Error", "Por favor complete todos los campos requeridos")
            return

        # Guardar
        config_nuevo['configured'] = True
        config_nuevo['first_run'] = False

        if guardar_config(config_nuevo):
            self.estado.config(text="✅ Configuración guardada exitosamente", fg="green")
            messagebox.showinfo("Éxito", "Configuración guardada correctamente\n\nEl sistema está listo para usar")
            self.root.destroy()
        else:
            messagebox.showerror("Error", "No se pudo guardar la configuración")

# ==============================================================================
# GUI DE ADMINISTRACIÓN
# ==============================================================================

class ManagerWindow:
    """Ventana de administrador"""

    def __init__(self, root):
        self.root = root
        self.root.title("Sync System Manager v2.0")
        self.root.geometry("800x600")

        # Centrar
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        self.config = cargar_config()
        self.sync_module = SyncModule(self.config)

        self.crear_gui()
        self.actualizar_estado()

    def crear_gui(self):
        """Crea interfaz"""
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=60)
        header.pack(fill="x")

        titulo = tk.Label(header, text="🔄 Sync System Manager", font=("Arial", 18, "bold"), bg="#2c3e50", fg="white")
        titulo.pack(pady=15)

        # Contenido principal
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

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

        self.lbl_stats = tk.Label(stats_frame, text="Products: 0 | Customers: 0 | Categories: 0 | Quotes: 0",
                                 font=("Arial", 10))
        self.lbl_stats.pack()

        # Botones
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(btn_frame, text="🔄 Sincronizar Ahora", command=self.sincronizar, width=20).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="⚙️ Configuración", command=self.configurar, width=20).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 Ver Logs", command=self.ver_logs, width=20).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="❌ Salir", command=self.root.quit, width=20).pack(side="right", padx=5)

        # Logs
        log_frame = tk.LabelFrame(main_frame, text="📝 Logs en Tiempo Real", font=("Arial", 12, "bold"))
        log_frame.pack(fill="both", expand=True, pady=5, padx=5)

        self.txt_logs = scrolledtext.ScrolledText(log_frame, height=10, state="disabled")
        self.txt_logs.pack(fill="both", expand=True)

        # Cargar últimos logs
        self.cargar_logs()

    def actualizar_estado(self):
        """Actualiza estado del sistema"""
        if not self.config.get('configured'):
            self.lbl_estado.config(text="🔴 NO CONFIGURADO", fg="red")
            return

        # Verificar conexiones
        if self.sync_module.verificar_conexiones():
            self.lbl_estado.config(text="🟢 ACTIVO", fg="green")
        else:
            self.lbl_estado.config(text="🟡 ERROR DE CONEXIÓN", fg="orange")

    def sincronizar(self):
        """Ejecuta sincronización"""
        self.agregar_log("Iniciando sincronización...")

        try:
            resultado = self.sync_module.sincronizar()

            if resultado:
                stats = self.sync_module.stats
                self.lbl_stats.config(
                    text=f"Products: {stats['products']['nuevos']} nuevos | "
                         f"Customers: {stats['customers']['nuevos']} nuevos | "
                         f"Categories: {stats['categories']['nuevos']} nuevos | "
                         f"Quotes: {stats['quotes']['nuevos']} nuevos"
                )
                self.lbl_ultima_sync.config(text=f"Última sync: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                self.agregar_log("✅ Sincronización completada")
            else:
                self.agregar_log("❌ Error en sincronización")

        except Exception as e:
            self.agregar_log(f"❌ Error: {str(e)}")

    def configurar(self):
        """Abre configuración"""
        ConfigWindow(tk.Toplevel(self.root))
        self.config = cargar_config()
        self.sync_module = SyncModule(self.config)
        self.actualizar_estado()

    def ver_logs(self):
        """Abre ventana de logs"""
        win = tk.Toplevel(self.root)
        win.title("Logs del Sistema")
        win.geometry("800x600")

        txt = scrolledtext.ScrolledText(win)
        txt.pack(fill="both", expand=True)

        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                txt.insert("1.0", f.read())
        except:
            txt.insert("1.0", "No hay logs disponibles")

    def cargar_logs(self):
        """Carga últimos logs"""
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lineas = f.readlines()
                ultimas = lineas[-20:] if len(lineas) > 20 else lineas
                self.txt_logs.config(state="normal")
                self.txt_logs.delete("1.0", "end")
                self.txt_logs.insert("1.0", "".join(ultimas))
                self.txt_logs.config(state="disabled")
        except:
            pass

    def agregar_log(self, mensaje):
        """Agrega log a la GUI"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.txt_logs.config(state="normal")
        self.txt_logs.insert("end", f"[{timestamp}] {mensaje}\n")
        self.txt_logs.see("end")
        self.txt_logs.config(state="disabled")

    def log_message(self, mensaje: str, tipo: str = "info"):
        """
        Método compatible con SmartSyncComplete
        Muestra logs en tiempo real en la GUI
        """
        # Convertir tipos a colores/emojis
        prefijos = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'debug': '🔍'
        }

        prefijo = prefijos.get(tipo, '•')
        mensaje_formateado = f"{prefijo} {mensaje}"

        # Agregar a la GUI
        self.agregar_log(mensaje_formateado)

        # Forzar actualización de la GUI para mostrar en tiempo real
        self.root.update_idletasks()

# ==============================================================================
# SYSTEM TRAY SERVICE (Modo transparente con icono en barra de tareas)
# ==============================================================================

class SystemTrayService:
    """
    Servicio en segundo plano con icono en la barra de tareas
    El usuario no ve ventana, solo el icono
    """

    def __init__(self, config):
        self.config = config
        self.sync_running = True
        self.is_syncing = False  # Nuevo flag para saber si está sincronizando ahora
        self.last_sync_time = None
        self.last_sync_status = "Esperando..."
        self.root = None
        self.icon = None

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
            log("ERROR: PIL no está instalado. Ejecute: pip install Pillow", "ERROR")
            return None
        except Exception as e:
            log(f"Error creando icono: {e}", "ERROR")
            return None

    def log_message(self, mensaje: str, tipo: str = "info"):
        """Método compatible con SmartSyncComplete"""
        # Guardar en log pero no mostrar nada (servicio transparente)
        log(f"[TRAY] {mensaje}", tipo.upper())

    def ejecutar_sincronizacion(self):
        """Ejecuta una sincronización"""
        self.is_syncing = True

        try:
            # Importar módulo de sincronización
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "smart_sync_complete",
                os.path.join(BASE_DIR, "smart_sync_complete.py")
            )
            sync_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sync_module)

            postgresql_config = {
                'host': self.config['postgres_host'],
                'port': self.config['postgres_port'],
                'database': self.config['postgres_database'],
                'user': self.config['postgres_user'],
                'password': self.config['postgres_password']
            }

            mysql_config = {
                'host': self.config['mysql_host'],
                'port': self.config['mysql_port'],
                'database': self.config['mysql_database'],
                'user': self.config['mysql_user'],
                'password': self.config['mysql_password']
            }

            sync_system = sync_module.SmartSyncComplete(
                app=self,
                postgresql_config=postgresql_config,
                mysql_config=mysql_config,
                company_rif=self.config['company_rif'],
                company_email=self.config['company_email']
            )

            sync_system.inicializar_tabla_hashes()
            resultado = sync_system.ejecutar_sync_completa()

            if resultado:
                self.last_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.last_sync_status = "✅ Exitosa"
                self._mostrar_notificacion_windows("Sincronización Exitosa", f"Última sync: {self.last_sync_time}")
            else:
                self.last_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.last_sync_status = "❌ Error"
                self._mostrar_notificacion_windows("Error en Sincronización", "Revisa los logs para más detalles")

        except Exception as e:
            log(f"Error en sincronización: {e}", "ERROR")
            self.last_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.last_sync_status = f"❌ Error: {str(e)[:30]}"
            self._mostrar_notificacion_windows("Error en Sincronización", str(e)[:50])
        finally:
            self.is_syncing = False

    def _mostrar_notificacion_windows(self, titulo: str, mensaje: str):
        """Muestra notificación de Windows"""
        try:
            from win10toast import ToastNotifier
            toast = ToastNotifier()
            toast.show_toast(
                title=f"🔄 {titulo}",
                message=mensaje,
                duration=5,
                threaded=True
            )
        except Exception:
            pass  # Si falla la notificación, continuar sin problema

    def actualizar_tooltip(self):
        """Actualiza el tooltip del icono"""
        # pystray NO permite cambiar el tooltip dinámicamente
        # El tooltip se establece al crear el icono y no se puede modificar
        # En su lugar, mostramos el estado en:
        # - Notificaciones de Windows
        # - Ventana de logs en tiempo real
        pass

    def ver_logs(self):
        """Abre ventana de logs en tiempo real"""
        import tkinter as tk
        from tkinter import scrolledtext
        import threading
        import time

        # Crear ventana raíz ya que no hay una
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana principal

        log_window = tk.Toplevel(root)
        log_window.title("📊 Logs de Sincronización - Tiempo Real")
        log_window.geometry("900x700")

        # Frame principal
        main_frame = tk.Frame(log_window)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Frame de información
        info_frame = tk.Frame(main_frame)
        info_frame.pack(fill="x", pady=(0, 5))

        lbl_info = tk.Label(
            info_frame,
            text="📁 Logs: windows_package/logs/  |  🔄 Actualización automática cada 2 segundos",
            font=("Arial", 9),
            anchor="w"
        )
        lbl_info.pack(fill="x")

        # Frame de botones
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(0, 5))

        # Variables de control
        log_running = [True]  # Usar lista para mutable en closure
        current_log_file = [None]

        def buscar_log_mas_reciente():
            """Busca el archivo de log más reciente"""
            try:
                log_dir = os.path.join(BASE_DIR, "logs")
                if not os.path.exists(log_dir):
                    return None

                # Buscar todos los archivos de log (.txt y .log)
                all_files = []
                for f in os.listdir(log_dir):
                    if f.endswith('.txt') or f.endswith('.log'):
                        full_path = os.path.join(log_dir, f)
                        # Obtener fecha de modificación
                        mtime = os.path.getmtime(full_path)
                        all_files.append((mtime, full_path))

                if all_files:
                    # Ordenar por fecha de modificación (más reciente primero)
                    all_files.sort(reverse=True)
                    return all_files[0][1]  # Retornar el archivo más reciente
                return None
            except Exception:
                return None

        def actualizar_logs():
            """Actualiza el contenido de logs periódicamente"""
            last_size = [0]  # Tamaño del archivo la última vez

            def update_loop():
                while log_running[0]:
                    try:
                        log_file = buscar_log_mas_reciente()

                        if log_file:
                            if current_log_file[0] != log_file:
                                # Nuevo archivo de log
                                current_log_file[0] = log_file
                                last_size[0] = 0
                                txt.config(state="normal")
                                txt.delete("1.0", "end")
                                txt.insert("1.0", f"📄 Archivo: {os.path.basename(log_file)}\n" + "="*80 + "\n\n")
                                last_size[0] = os.path.getsize(log_file)

                            # Leer solo el contenido nuevo
                            try:
                                current_size = os.path.getsize(log_file)
                                if current_size > last_size[0]:
                                    with open(log_file, 'r', encoding='utf-8') as f:
                                        f.seek(last_size[0])
                                        new_content = f.read()
                                        if new_content:
                                            txt.config(state="normal")
                                            txt.insert("end", new_content)
                                            txt.see("end")  # Auto-scroll al final
                                            txt.config(state="disabled")
                                    last_size[0] = current_size
                            except Exception:
                                pass

                        lbl_status.config(text=f"📄 {os.path.basename(current_log_file[0]) if current_log_file[0] else 'Esperando logs...'} | {'🔄 Monitoreando' if log_running[0] else '⏸️ Pausado'}")

                        time.sleep(2)  # Actualizar cada 2 segundos

                    except Exception:
                        time.sleep(2)

            # Iniciar thread de actualización
            thread = threading.Thread(target=update_loop, daemon=True)
            thread.start()

        # Área de texto
        txt = scrolledtext.ScrolledText(main_frame, state="normal", font=("Consolas", 9))
        txt.pack(fill="both", expand=True)

        # Etiqueta de estado
        lbl_status = tk.Label(main_frame, text="🔄 Iniciando...", font=("Arial", 9), anchor="w")
        lbl_status.pack(fill="x", pady=(5, 0))

        # Botones
        btn_cerrar = tk.Button(btn_frame, text="❌ Cerrar", command=lambda: cerrar_ventana(), bg="#ff6b6b", fg="white")
        btn_cerrar.pack(side="right", padx=5)

        btn_limpiar = tk.Button(btn_frame, text="🧹 Limpiar Vista", command=lambda: limpiar_vista())
        btn_limpiar.pack(side="right", padx=5)

        btn_refresh = tk.Button(btn_frame, text="🔄 Forzar Refresh", command=lambda: force_refresh())
        btn_refresh.pack(side="right", padx=5)

        def limpiar_vista():
            """Limpia la vista pero sigue monitoreando"""
            txt.config(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", "📋 Vista limpiada. Monitoreando...\n" + "="*80 + "\n\n")
            txt.config(state="disabled")

        def force_refresh():
            """Fuerza la recarga completa del archivo"""
            if current_log_file[0]:
                try:
                    with open(current_log_file[0], 'r', encoding='utf-8') as f:
                        content = f.read()
                        txt.config(state="normal")
                        txt.delete("1.0", "end")
                        txt.insert("1.0", f"📄 Archivo: {os.path.basename(current_log_file[0])}\n" + "="*80 + "\n\n")
                        txt.insert("end", content)
                        txt.see("end")
                        txt.config(state="disabled")
                except Exception as e:
                    txt.config(state="normal")
                    txt.insert("end", f"\n❌ Error: {e}\n")
                    txt.config(state="disabled")

        def cerrar_ventana():
            """Cierra la ventana y detiene el monitoreo"""
            log_running[0] = False
            root.destroy()

        # Iniciar actualización automática
        actualizar_logs()

        # Cargar contenido inicial
        log_file = buscar_log_mas_reciente()
        if log_file:
            current_log_file[0] = log_file
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    txt.insert("1.0", f"📄 Archivo: {os.path.basename(log_file)}\n" + "="*80 + "\n\n")
                    txt.insert("end", content)
                    txt.see("end")
            except Exception as e:
                txt.insert("1.0", f"❌ Error cargando log: {e}")
        else:
            txt.insert("1.0", "⏳ Esperando logs...\n\n")
            txt.insert("end", "El sistema creará logs en:\n")
            txt.insert("end", f"  {LOGS_DIR}\n\n")
            txt.insert("end", "Logs que se crearán:\n")
            txt.insert("end", "  • sync_system.log - Logs del sistema (arranque, errores)\n")
            txt.insert("end", "  • sync_YYYYMMDD_HHMMSS.txt - Logs de sincronización\n\n")
            txt.insert("end", "💡 Si el icono está en la barra de tareas, la sincronización\n")
            txt.insert("end", "   se ejecutará automáticamente en segundo plano.\n\n")
            txt.insert("end", "💡 Puedes forzar una sincronización desde:\n")
            txt.insert("end", "   Clic derecho en el icono → Sincronizar Ahora\n")

        txt.config(state="disabled")

        # Manejar cierre de ventana
        log_window.protocol("WM_DELETE_WINDOW", cerrar_ventana)

        # Ejecutar
        root.mainloop()

    def sincronizar_ahora(self):
        """Sincronización manual desde el menú"""
        import threading
        thread = threading.Thread(target=self.ejecutar_sincronizacion)
        thread.daemon = True
        thread.start()

    def salir(self):
        """Salir del servicio"""
        self.sync_running = False
        if self.icon:
            self.icon.stop()
        sys.exit(0)

    def iniciar(self):
        """Inicia el servicio en la bandeja del sistema"""
        try:
            log("=" * 70, "INFO")
            log("INICIANDO SYSTEM TRAY SERVICE", "INFO")
            log("=" * 70, "INFO")
            log(f"RIF: {self.config['company_rif']}", "INFO")
            log(f"Email: {self.config['company_email']}", "INFO")
            log(f"Intervalo: {self.config.get('sync_interval_minutes', 30)} minutos", "INFO")
            log("", "INFO")

            import pystray

            # Crear icono
            log("Creando icono de la bandeja del sistema...", "INFO")
            icon_image = self.crear_icono()
            if not icon_image:
                log("No se pudo crear el icono. Saliendo.", "ERROR")
                return

            log("✅ Icono creado correctamente", "SUCCESS")

            # Crear menú contextual
            menu = pystray.Menu(
                pystray.MenuItem('📊 Ver Logs', self.ver_logs),
                pystray.MenuItem('🔄 Sincronizar Ahora', self.sincronizar_ahora),
                pystray.MenuItem('⚙️ Configuración', lambda: self.abrir_config()),
                pystray.MenuItem('❌ Salir', self.salir)
            )

            # Crear icono en la bandeja
            # Nota: El tooltip no se puede cambiar dinámicamente en pystray
            tooltip_text = f"""Sync System v2.0
RIF: {self.config['company_rif']}

Clic derecho → Ver Logs (tiempo real)"""
            self.icon = pystray.Icon("Sync System", icon_image, tooltip_text, menu)

            # Iniciar sincronización automática en thread
            log("Iniciando thread de sincronización automática...", "INFO")
            import threading
            sync_thread = threading.Thread(target=self.bucle_sincronizacion)
            sync_thread.daemon = True
            sync_thread.start()

            # Ejecutar icono (bloqueante)
            log("✅ Servicio iniciado en la bandeja del sistema", "INFO")
            log("💡 El icono está en la barra de tareas (junto al reloj)", "INFO")
            log("💡 Clic derecho para ver opciones", "INFO")
            log("", "INFO")
            self.icon.run()

        except ImportError:
            log("ERROR: pystray no está instalado", "ERROR")
            log("Ejecute: pip install pystray Pillow", "ERROR")
            log("", "INFO")
            log("Instalación:", "INFO")
            log("  pip install pystray Pillow", "INFO")
        except Exception as e:
            log(f"Error iniciando servicio: {e}", "ERROR")

    def bucle_sincronizacion(self):
        """Bucle de sincronización automática"""
        # Primera sincronización inmediata al iniciar
        if self.sync_running:
            log("🔄 Ejecutando primera sincronización al inicio...", "INFO")
            self.ejecutar_sincronizacion()

        # Bucle de sincronización periódica
        while self.sync_running:
            try:
                # Recargar configuración al inicio de cada ciclo
                self.config = cargar_config()
                intervalo_minutos = int(self.config.get('sync_interval_minutes', 30))
                intervalo_segundos = intervalo_minutos * 60

                log(f"Sincronización automática cada {intervalo_minutos} minutos", "INFO")
                log(f"Próxima sincronización en {intervalo_minutos} minutos...", "INFO")

                time.sleep(intervalo_segundos)

                if self.sync_running:
                    log(f"🔄 Iniciando sincronización programada...", "INFO")
                    self.ejecutar_sincronizacion()

            except Exception as e:
                log(f"Error en bucle de sincronización: {e}", "ERROR")

    def abrir_config(self):
        """Abre ventana de configuración"""
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.title("Configuración")
        app = ConfigWindow(root)
        root.mainloop()

        # Recargar configuración
        self.config = cargar_config()

        # Actualizar intervalo
        log("Configuración actualizada", "INFO")

# ==============================================================================
# MAIN - INICIO DEL SISTEMA
# ==============================================================================

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Sistema de Sincronización Inteligente")
    parser.add_argument("--mode", choices=["config", "manager", "service", "sync", "tray"],
                       default="auto", help="Modo de ejecución")

    args = parser.parse_args()
    config = cargar_config()

    # Auto-detectar modo
    if args.mode == "auto":
        if not config.get('configured') or config.get('first_run'):
            args.mode = "config"
        else:
            args.mode = "tray"  # Por defecto: modo tray (icono en barra de tareas)

    # Ejecutar según modo
    if args.mode == "config":
        # Modo configuración
        root = tk.Tk()
        app = ConfigWindow(root)
        root.mainloop()

    elif args.mode == "manager":
        # Modo manager
        root = tk.Tk()
        app = ManagerWindow(root)
        root.mainloop()

    elif args.mode == "tray":
        # Modo System Tray (icono en barra de tareas)
        print("=== MODO SYSTEM TRAY ===")
        print("🔵 El icono está en la barra de tareas (junto al reloj)")
        print("📊 Clic izquierdo: Ver logs")
        print("⚙️  Clic derecho: Menú de opciones")
        print("❌ Para salir: Clic derecho → Salir")
        print("")

        tray = SystemTrayService(config)
        tray.iniciar()

    elif args.mode == "sync":
        # Modo sincronización única
        print("=== SINCRONIZACIÓN ÚNICA ===")
        sync = SyncModule(config)
        if sync.verificar_conexiones():
            sync.sincronizar()
            sync.cerrar()
        else:
            print("Error: No se pueden establecer conexiones")
            sys.exit(1)

    elif args.mode == "service":
        # Modo servicio (loop infinito)
        print("=== MODO SERVICIO ===")
        print(f"Intervalo: {config.get('sync_interval_minutes', 30)} minutos")
        print("Presione Ctrl+C para detener")

        sync = SyncModule(config)

        try:
            while True:
                log("=== INICIANDO CICLO DE SINCRONIZACIÓN ===")
                sync.verificar_conexiones()
                sync.sincronizar()

                intervalo = int(config.get('sync_interval_minutes', 30))
                log(f"Próxima sync en {intervalo} minutos")
                log(f"=== CICLO COMPLETADO ===\n")

                time.sleep(intervalo * 60)

        except KeyboardInterrupt:
            log("\n=== SERVICIO DETENIDO ===")
            sync.cerrar()

if __name__ == "__main__":
    main()
