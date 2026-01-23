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
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

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
    import mysql.connector
except ImportError as e:
    print(f"Error: Falta dependencia: {e}")
    print("Ejecute: pip install psycopg2-binary mysql-connector-python")
    sys.exit(1)

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

CONFIG_FILE = "sync_config.json"
LOG_FILE = "sync_system.log"

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
        "postgres_host": "localhost",
        "postgres_port": "5432",
        "postgres_database": "dataaa",
        "postgres_user": "postgres",
        "postgres_password": "",

        "mysql_host": "",
        "mysql_port": "3306",
        "mysql_database": "",
        "mysql_user": "",
        "mysql_password": "",

        "company_rif": "",
        "company_email": "",

        "sync_interval_minutes": "30",

        "configured": False,
        "first_run": True
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
            self.mysql_conn = mysql.connector.connect(
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
                company_id=27  # Company ID para Multiservicios Leblanc
            )

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

        # Pestaña MySQL
        frame_mysql = ttk.Frame(notebook)
        notebook.add(frame_mysql, text="🐬 MySQL")

        self.crear_campos_mysql(frame_mysql)

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

        # Info
        info = tk.Label(frame, text="ℹ️ Estos datos se usan para identificar la empresa en la sincronización",
                       fg="gray", justify="left")
        info.grid(row=2, column=0, columnspan=2, pady=10, padx=5, sticky="w")

    def crear_campos_configuracion(self, parent):
        """Crea campos de configuración"""
        frame = ttk.LabelFrame(parent, text="Configuración de Sincronización", padding=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Intervalo
        ttk.Label(frame, text="Intervalo de sincronización:").grid(row=0, column=0, sticky="w", pady=5, padx=5)

        self.intervalo = tk.StringVar(value=self.config.get('sync_interval_minutes', '30'))
        intervalos = ["5", "15", "30", "60"]
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
            import mysql.connector

            conn = mysql.connector.connect(
                host=self.entry_mysql['mysql_host'].get().strip(),
                port=self.entry_mysql['mysql_port'].get().strip(),
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

        # PostgreSQL
        for key, entry in self.entry_pg.items():
            config_nuevo[key] = entry.get().strip()

        # MySQL
        for key, entry in self.entry_mysql.items():
            config_nuevo[key] = entry.get().strip()

        # Empresa
        config_nuevo['company_rif'] = self.entry_rif.get().strip()
        config_nuevo['company_email'] = self.entry_email.get().strip()

        # Configuración
        config_nuevo['sync_interval_minutes'] = self.intervalo.get()

        # Validar (postgres_password puede ser blanco)
        if not all([
            config_nuevo.get('postgres_host'),
            config_nuevo.get('postgres_database'),
            config_nuevo.get('postgres_user'),
            config_nuevo.get('mysql_host'),
            config_nuevo.get('mysql_database'),
            config_nuevo.get('mysql_user'),
            config_nuevo.get('mysql_password'),
            config_nuevo.get('company_rif'),
            config_nuevo.get('company_email')
        ]):
            messagebox.showerror("Error", "Por favor complete todos los campos")
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
        status_frame = tk.LabelFrame(main_frame, text="📊 Estado del Sistema", font=("Arial", 12, "bold"), padding=10)
        status_frame.pack(fill="x", pady=5)

        self.lbl_estado = tk.Label(status_frame, text="🟢 ACTIVO", font=("Arial", 14), fg="green")
        self.lbl_estado.pack()

        self.lbl_ultima_sync = tk.Label(status_frame, text="Última sync: --", font=("Arial", 10))
        self.lbl_ultima_sync.pack(pady=5)

        # Panel de estadísticas
        stats_frame = tk.LabelFrame(main_frame, text="📈 Estadísticas", font=("Arial", 12, "bold"), padding=10)
        stats_frame.pack(fill="x", pady=5)

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
        log_frame = tk.LabelFrame(main_frame, text="📝 Logs en Tiempo Real", font=("Arial", 12, "bold"), padding=10)
        log_frame.pack(fill="both", expand=True, pady=5)

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

# ==============================================================================
# MAIN - INICIO DEL SISTEMA
# ==============================================================================

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description="Sistema de Sincronización Inteligente")
    parser.add_argument("--mode", choices=["config", "manager", "service", "sync"],
                       default="auto", help="Modo de ejecución")

    args = parser.parse_args()
    config = cargar_config()

    # Auto-detectar modo
    if args.mode == "auto":
        if not config.get('configured') or config.get('first_run'):
            args.mode = "config"
        else:
            args.mode = "manager"

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
