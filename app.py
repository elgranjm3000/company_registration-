import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import mysql.connector
import psycopg2
from mysql.connector import Error as MySQLError
from psycopg2 import Error as PostgreSQLError
import re
import sys
import os
from datetime import datetime,timedelta
import threading
import bcrypt
import json
import base64
import uuid
import os
from dotenv import load_dotenv
from smart_sellers_sync_module import SmartSellersSyncModule
from smart_sync_complete import SmartSyncComplete

# Importar win10toast para notificaciones (opcional)
try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False

load_dotenv()


def get_mac_address():
    # Obtiene la MAC address como un entero
    mac = uuid.getnode()
    
    # Convierte a formato legible (XX:XX:XX:XX:XX:XX)
    mac_address = ':'.join(('%012X' % mac)[i:i+2] for i in range(0, 12, 2))
    
    return mac_address

def resource_path(relative_path):
    """Obtener ruta de recurso para PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def laravel_hash_make(password):
    """Generar hash compatible con Laravel Hash::make()"""
    # Convertir password a bytes si es string
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Laravel usa cost=10 por defecto
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password, salt)
    
    # Laravel espera $2y$ en lugar de $2b$ (compatibilidad PHP)
    laravel_hash = hashed.decode('utf-8').replace('$2b$', '$2y$')
    
    return laravel_hash

def safe_float(value):
    if isinstance(value, memoryview):
        try:
            value = value.tobytes().decode('utf-8')
        except Exception:
            return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

class CompleteSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema Completo de Sincronización PostgreSQL → MySQL")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Configurar icono si existe
        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Configuración de bases de datos
        self.postgresql_config = {
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_DATABASE'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        # Configuración MySQL con valores fijos (ocultos al usuario)
        self.mysql_config = {
            'host': os.getenv('DB_HOST_MYSQL'),  # Valor fijo oculto
            'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
            'user': os.getenv('DB_USER_MYSQL'),
            'password': os.getenv('DB_PASSWORD_MYSQL')  # Valor fijo oculto
        }
        
        # Variable global para company_id
        self.company_id = None

        # Control de sincronización
        self.sync_running = False

        # Instancia de SmartSyncComplete (sistema nuevo con contadores de progreso)
        self.smart_sync = None  # Se inicializará cuando se obtenga company_rif y company_email
        self.progress_update_job = None  # Job para actualizar progreso en UI
        
        self.setup_styles()
        self.create_widgets()
        self.center_window()
        
        # Log inicial
        self.log_message("=== SISTEMA COMPLETO DE SINCRONIZACIÓN ===", "info")
        self.log_message("PostgreSQL → MySQL", "info")
        self.log_message("Versión: 1.0 - Basado en script bash completo", "info")
        self.log_message("Listo para sincronizar", "info")

    def get_tax_code(self, tax_percentage):
        """Mapea porcentaje de impuesto a código de impuesto PostgreSQL"""
        if tax_percentage >= 15:
            return '01'  # IVA General 16%
        elif tax_percentage >= 7:
            return '03'  # IVA Reducido 8%
        else:
            return 'EX'  # Exento

    def get_unit_id(self, product_code, pg_cursor):
        """Obtiene el ID de unidad para un producto"""
        if not product_code:
            return 1
        
        sql = """
        SELECT correlative 
        FROM public.products_units 
        WHERE product_code = %s AND main_unit = true
        LIMIT 1
        """
        
        try:
            pg_cursor.execute(sql, (product_code,))
            result = pg_cursor.fetchone()
            return result[0] if result else 1
        except:
            return 1
        
    def setup_styles(self):
        """Configurar estilos personalizados"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground='#34495e')
        style.configure('Success.TLabel', foreground='#27ae60', font=('Arial', 10, 'bold'))
        style.configure('Error.TLabel', foreground='#e74c3c', font=('Arial', 10, 'bold'))
        
    def create_widgets(self):
        """Crear interfaz completa"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=0)  # Panel izquierdo: ancho fijo
        main_frame.columnconfigure(1, weight=1)  # Panel derecho: expandible
        main_frame.rowconfigure(1, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text="Sistema Completo de Sincronización", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Frame izquierdo - Configuración y controles (ancho fijo)
        left_frame = ttk.Frame(main_frame, width=400)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.grid_propagate(False)  # Mantener ancho fijo
        
        # Frame derecho - Log (expandible)
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)
        
    def create_left_panel(self, parent):
        """Panel izquierdo con configuración y controles"""
        
        # Configurar el frame principal para usar scroll si es necesario
        parent.columnconfigure(0, weight=1)
        
        # Crear un canvas y scrollbar para el contenido
        canvas = tk.Canvas(parent, width=380)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configuración PostgreSQL
        pg_frame = ttk.LabelFrame(scrollable_frame, text="PostgreSQL (Origen)", padding="10")
        pg_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        pg_frame.columnconfigure(1, weight=1)
        
        info_label = ttk.Label(pg_frame, text="Nota: Host y contraseña preconfigurados", 
                              font=('Arial', 8), foreground='#666666')
        info_label.grid(row=2, column=0, columnspan=2, pady=(5, 0))
        
        # Configuración MySQL (solo campos visibles - host y password ocultos)
        mysql_frame = ttk.LabelFrame(scrollable_frame, text="MySQL (Destino)", padding="10")
        mysql_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        mysql_frame.columnconfigure(1, weight=1)
        
        
        # Nota informativa sobre la configuración
        info_label = ttk.Label(mysql_frame, text="Nota: Host y contraseña preconfigurados", 
                              font=('Arial', 8), foreground='#666666')
        info_label.grid(row=2, column=0, columnspan=2, pady=(5, 0))
        
        # Configuración de Compañía
        company_frame = ttk.LabelFrame(scrollable_frame, text="Datos de la Compañía", padding="10")
        company_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        company_frame.columnconfigure(1, weight=1)
        
        ttk.Label(company_frame, text="RIF:*").grid(row=0, column=0, sticky=tk.W)
        self.company_rif_var = tk.StringVar(value=os.getenv('RIF'))
        rif_entry = ttk.Entry(company_frame, textvariable=self.company_rif_var, width=25,state='disabled')
        rif_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(company_frame, text="Email:*").grid(row=1, column=0, sticky=tk.W)
        self.company_email_var = tk.StringVar(value=os.getenv('EMAIL'))
        email_entry = ttk.Entry(company_frame, textvariable=self.company_email_var, width=25,state='disabled')
        email_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(company_frame, text="Nombre:*").grid(row=2, column=0, sticky=tk.W)
        self.company_name_var = tk.StringVar(value=os.getenv('COMPANY_NOMBRE'))
        name_entry = ttk.Entry(company_frame, textvariable=self.company_name_var, width=25,state='disabled')
        name_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # Validación en tiempo real del RIF
        self.company_rif_var.trace('w', self.validate_company_rif)
        
        # Opciones de sincronización
        options_frame = ttk.LabelFrame(scrollable_frame, text="Opciones de Sincronización", padding="10")
        options_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.sync_companies_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="1. Companies", variable=self.sync_companies_var).grid(row=0, column=0, sticky=tk.W)
        
        self.sync_categories_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="2. Categories (Departments)", variable=self.sync_categories_var).grid(row=1, column=0, sticky=tk.W)
        
        self.sync_products_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="3. Products", variable=self.sync_products_var).grid(row=2, column=0, sticky=tk.W)
        
        self.sync_customers_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="4. Customers (Clients)", variable=self.sync_customers_var).grid(row=3, column=0, sticky=tk.W)
        
        self.sync_users_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="5. Users (Sellers)", variable=self.sync_users_var).grid(row=4, column=0, sticky=tk.W)
        
        self.sync_sellers_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="6. Sellers", variable=self.sync_sellers_var).grid(row=5, column=0, sticky=tk.W)
          # Después de self.sync_sellers_var
        self.sync_quotes_var = tk.BooleanVar(value=False)  # False por defecto
        ttk.Checkbutton(options_frame, text="7. Quotes (Presupuestos)",
        variable=self.sync_quotes_var).grid(row=6, column=0, sticky=tk.W)
        
        # Botones de control
        button_frame = ttk.LabelFrame(scrollable_frame, text="Controles", padding="10")
        button_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.test_btn = ttk.Button(button_frame, text="Probar Conexiones", command=self.test_connections)
        self.test_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.sync_btn = ttk.Button(button_frame, text="Iniciar Sincronización Completa", command=self.start_complete_sync)
        self.sync_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.stop_btn = ttk.Button(button_frame, text="Detener", command=self.stop_sync, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.clear_log_btn = ttk.Button(button_frame, text="Limpiar Log", command=self.clear_log)
        self.clear_log_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.save_log_btn = ttk.Button(button_frame, text="Guardar Log", command=self.save_log)
        self.save_log_btn.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        progress_frame = ttk.LabelFrame(scrollable_frame, text="Progreso", padding="10")
        progress_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        # Status
        self.status_var = tk.StringVar(value="Listo para sincronizar")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack()
        
        # Configurar el canvas y scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        parent.rowconfigure(0, weight=1)
        
        # Configurar el ancho del frame scrollable
        scrollable_frame.columnconfigure(0, weight=1)
        
        # Bind mouse wheel para scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def validate_company_rif(self, *args):
        """Validar formato del RIF de la compañía en tiempo real"""
        rif = self.company_rif_var.get().upper()
        if rif:
            cleaned = re.sub(r'[^VEJGC0-9]', '', rif)
            self.company_rif_var.set(cleaned)
        
    def create_right_panel(self, parent):
        """Panel derecho con log de actividad"""
        log_frame = ttk.LabelFrame(parent, text="Log de Actividad", padding="10")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        
        self.result_text = scrolledtext.ScrolledText(log_frame, height=40, font=('Consolas', 9))
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
    def center_window(self):
        """Centrar ventana en pantalla"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def log_message(self, message, type="info"):
        """Agregar mensaje al log con timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if type == "error":
            prefix = "❌ ERROR:"
        elif type == "success":
            prefix = "✅ ÉXITO:"
        elif type == "warning":
            prefix = "⚠️ ADVERTENCIA:"
        else:
            prefix = "ℹ️ INFO:"
            
        formatted_message = f"[{timestamp}] {prefix} {message}\n"
        
        self.result_text.insert(tk.END, formatted_message)
        self.result_text.see(tk.END)
        self.root.update()
        
    def clear_log(self):
        """Limpiar log"""
        self.result_text.delete(1.0, tk.END)
        self.log_message("Log limpiado")
        
    def save_log(self):
        """Guardar log en archivo"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
                title="Guardar Log de Sincronización"
            )
            
            if filename:
                log_content = self.result_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log_message(f"Log guardado en: {filename}", "success")
                
        except Exception as e:
            self.log_message(f"Error guardando log: {str(e)}", "error")
    
    def update_config(self):
        """Actualizar configuración desde los campos"""
        self.postgresql_config = {
            'host': os.getenv('DB_HOST'),  # Valor fijo oculto
            'database': os.getenv('DB_DATABASE'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')  # Valor fijo oculto
        }
        
        # MySQL config: mantener valores fijos para host y password, actualizar solo los campos visibles
        self.mysql_config = {
            'host': os.getenv('DB_HOST_MYSQL'),  # Valor fijo oculto
            'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
            'user': os.getenv('DB_USER_MYSQL'),
            'password': os.getenv('DB_PASSWORD_MYSQL')  # Valor fijo oculto
        }
    
    def test_connections(self):
        """Probar conexiones a ambas bases de datos"""
        self.update_config()
        self.log_message("=== PROBANDO CONEXIONES ===", "info")
        
        # Debug: Mostrar configuración MySQL (sin password completa)
        self.log_message(f"MySQL Config - Host: {self.mysql_config['host']}", "info")
        self.log_message(f"MySQL Config - Database: {self.mysql_config['database']}", "info")
        self.log_message(f"MySQL Config - User: {self.mysql_config['user']}", "info")
        self.log_message(f"MySQL Config - Password: {'*' * len(self.mysql_config['password'])}", "info")
        
        # Probar PostgreSQL
        try:
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            pg_cursor.execute("SELECT version()")
            pg_version = pg_cursor.fetchone()[0]
            self.log_message(f"PostgreSQL conectado: {pg_version[:50]}...", "success")
            pg_cursor.close()
            pg_conn.close()
        except Exception as e:
            self.log_message(f"Error conectando PostgreSQL: {str(e)}", "error")
            return
        
        # Probar MySQL
        try:
            self.log_message("Intentando conexión MySQL...", "info")
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            if mysql_conn.is_connected():
                db_info = mysql_conn.get_server_info()
                self.log_message(f"MySQL conectado: Server {db_info}", "success")
                self.log_message(f"Conectado a base de datos: {self.mysql_config['database']}", "success")
                mysql_conn.close()
        except Exception as e:
            self.log_message(f"Error conectando MySQL: {str(e)}", "error")
            self.log_message("Posibles causas:", "info")
            self.log_message("1. Usuario sin permisos desde esta IP", "info")
            self.log_message("2. Contraseña incorrecta", "info")
            self.log_message("3. Usuario no existe", "info")
            self.log_message("4. Firewall bloqueando conexión", "info")
            return
            
        self.log_message("Todas las conexiones exitosas", "success")
    
    def start_complete_sync(self):
        """Iniciar sincronización completa en hilo separado"""
        if self.sync_running:
            self.log_message("Sincronización ya en curso", "warning")
            return
            
        self.sync_running = True
        self.sync_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Ejecutar en hilo separado para no bloquear UI
        sync_thread = threading.Thread(target=self.complete_sync_process)
        sync_thread.daemon = True
        sync_thread.start()
    
    def stop_sync(self):
        """Detener sincronización"""
        self.sync_running = False
        self.sync_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Sincronización detenida")
        self.log_message("Sincronización detenida por el usuario", "warning")
    
    def _mostrar_notificacion_sync(self, duration, stats):
        """
        Mostrar notificación tipo toast con resumen de sincronización

        Args:
            duration: Duración de la sincronización en segundos
            stats: Diccionario con estadísticas de sincronización
        """
        if not TOAST_AVAILABLE:
            return

        try:
            toast = ToastNotifier()

            # Construir mensaje con estadísticas
            cambios = []
            if stats['products']['nuevos'] > 0 or stats['products']['modificados'] > 0:
                cambios.append(f"Products: {stats['products']['nuevos']}+ {stats['products']['modificados']}~")

            if stats['customers']['nuevos'] > 0 or stats['customers']['modificados'] > 0:
                cambios.append(f"Customers: {stats['customers']['nuevos']}+ {stats['customers']['modificados']}~")

            if stats['categories']['nuevos'] > 0 or stats['categories']['modificados'] > 0:
                cambios.append(f"Categories: {stats['categories']['nuevos']}+ {stats['categories']['modificados']}~")

            if stats['quotes']['nuevos'] > 0:
                cambios.append(f"Quotes: {stats['quotes']['nuevos']}+")

            # Si no hubo cambios
            if not cambios:
                mensaje = "Sin cambios | Duration: {:.1f}s".format(duration)
            else:
                mensaje = " | ".join(cambios) + f" | Duration: {duration:.1f}s"

            # Mostrar notificación (duracion 8 segundos)
            toast.show_toast(
                "✅ Sincronización Completada",
                mensaje,
                duration=8,
                threaded=True
            )

        except Exception as e:
            # Si falla la notificación, no interrumpir el flujo
            print(f"Error mostrando notificación: {e}")

    def complete_sync_process(self):
        """Proceso completo de sincronización usando SmartSyncComplete"""
        start_time = datetime.now()
        self.log_message("=== INICIANDO SINCRONIZACIÓN COMPLETA ===", "info")
        self.log_message("Sistema bidireccional PostgreSQL ↔ MySQL", "info")

        try:
            self.update_config()

            # Resetear progress
            self.progress_var.set(0)

            # Inicializar SmartSyncComplete
            if not self._init_smart_sync():
                raise Exception("No se pudo inicializar SmartSyncComplete")

            # Iniciar actualizaciones de progreso en UI
            self._start_progress_updates()

            # Ejecutar sincronización completa usando SmartSyncComplete
            success = self.smart_sync.ejecutar_sync_completa()

            if success:
                # Reporte final
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()

                self.log_message("=== SINCRONIZACIÓN COMPLETADA ===", "success")
                self.log_message(f"Tiempo total: {duration:.1f} segundos", "info")

                # Obtener estadísticas finales
                stats = self.smart_sync.stats
                self.log_message(f"Products: {stats['products']['nuevos']} nuevos, {stats['products']['modificados']} modificados", "info")
                self.log_message(f"Customers: {stats['customers']['nuevos']} nuevos, {stats['customers']['modificados']} modificados", "info")
                self.log_message(f"Categories: {stats['categories']['nuevos']} nuevos, {stats['categories']['modificados']} modificados", "info")
                self.log_message(f"Quotes: {stats['quotes']['nuevos']} nuevos", "info")

                self.status_var.set("Sincronización completada exitosamente")
                self.progress_var.set(100)

                # Mostrar notificación toast (no invasiva)
                self._mostrar_notificacion_sync(duration, stats)

                # Mostrar messagebox tradicional (modal)
                messagebox.showinfo("Éxito", f"Sincronización completada en {duration:.1f} segundos")
            else:
                raise Exception("La sincronización devolvió False")

        except Exception as e:
            self.log_message(f"Error durante sincronización: {str(e)}", "error")
            self.status_var.set("Error en sincronización")
            messagebox.showerror("Error", f"Error en sincronización: {str(e)}")
        
        finally:
            self.sync_running = False
            self.sync_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self._stop_progress_updates()  # Detener actualizaciones de progreso

    # ====================================================================
    # MÉTODOS PARA INTEGRACIÓN CON SmartSyncComplete
    # ====================================================================

    def _init_smart_sync(self):
        """Inicializar SmartSyncComplete con los datos de configuración"""
        try:
            company_rif = self.company_rif_var.get().strip()
            company_email = self.company_email_var.get().strip()

            if not company_rif or not company_email:
                self.log_message("Error: company_rif y company_email son requeridos", "error")
                return None

            self.smart_sync = SmartSyncComplete(
                app=self,
                postgresql_config=self.postgresql_config,
                mysql_config=self.mysql_config,
                company_rif=company_rif,
                company_email=company_email,
                company_name='',  # Opcional
                progress_callback=None,  # Usaremos polling en lugar de callback
                log_callback=self.log_message  # Conectar logs a la UI
            )

            # Inicializar tabla de hashes
            self.smart_sync.inicializar_tabla_hashes()

            return True
        except Exception as e:
            self.log_message(f"Error inicializando SmartSyncComplete: {str(e)}", "error")
            return None

    def _start_progress_updates(self):
        """Iniciar actualizaciones periódicas del progreso en la UI"""
        if self.progress_update_job is None:
            self._update_progress_from_sync()

    def _update_progress_from_sync(self):
        """Actualizar la UI con la información de progreso de SmartSyncComplete"""
        # Verificar que la ventana todavía existe
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            self.progress_update_job = None
            return

        if self.smart_sync and self.sync_running:
            try:
                progress = self.smart_sync.get_progress_info()

                if progress['entity']:
                    entity_name = progress['entity'].upper()
                    current = progress['current']
                    total = progress['total']
                    percentage = progress['percentage']

                    # Actualizar status_var con el progreso detallado
                    self.status_var.set(f"Sincronizando {entity_name}: {current}/{total} ({percentage:.1f}%)")

                    # Calcular progreso general (aproximado)
                    # Asumimos que hay 7 entidades principales
                    entities_order = ['categories', 'products', 'customers', 'sellers', 'quotes']
                    if progress['entity'] in entities_order:
                        entity_index = entities_order.index(progress['entity'])
                        base_progress = (entity_index / len(entities_order)) * 100
                        entity_progress = (percentage / len(entities_order))
                        total_progress = base_progress + entity_progress
                        self.progress_var.set(total_progress)
            except Exception as e:
                pass  # Silencioso para no interrumpir

        # Programar próxima actualización en 200ms solo si sigue corriendo
        if self.sync_running and hasattr(self, 'root') and self.root.winfo_exists():
            try:
                self.progress_update_job = self.root.after(200, self._update_progress_from_sync)
            except Exception:
                # La ventana fue destruida, ignorar
                self.progress_update_job = None

    def _stop_progress_updates(self):
        """Detener actualizaciones de progreso"""
        if self.progress_update_job:
            try:
                if hasattr(self, 'root') and self.root.winfo_exists():
                    self.root.after_cancel(self.progress_update_job)
            except Exception:
                pass  # Ignorar errores al cancelar
            finally:
                self.progress_update_job = None

    # ====================================================================
    # MÉTODOS DE SINCRONIZACIÓN ANTIGUOS (Mantenidos por compatibilidad)
    # ====================================================================

    def sync_companies(self):
        """Sincronizar companies usando valores del formulario"""
        self.log_message("=== SINCRONIZANDO COMPANIES ===", "info")
        
        # Obtener valores del formulario
        company_rif = self.company_rif_var.get().strip()
        company_email = self.company_email_var.get().strip()
        company_name = self.company_name_var.get().strip()
        
        # Validar campos requeridos
        if not company_rif or not company_email or not company_name:
            self.log_message("Error: RIF, Email y Nombre de la compañía son obligatorios", "error")
            raise Exception("Datos de compañía incompletos")
        
        # Validar formato RIF
        if not re.match(r'^[VEJGC]\d{8,9}$', company_rif):
            self.log_message(f"Error: RIF {company_rif} tiene formato inválido", "error")
            raise Exception("Formato de RIF inválido")
        
        # Validar formato email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', company_email):
            self.log_message(f"Error: Email {company_email} tiene formato inválido", "error")
            raise Exception("Formato de email inválido")
        
        self.log_message(f"Registrando compañía: {company_name}", "info")
        self.log_message(f"RIF: {company_rif}, Email: {company_email}", "info")
        
        try:
            # Conectar PostgreSQL
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            
            # Query para obtener datos adicionales si existen
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
            
            pg_cursor.execute(query, (company_email,))
            company_data = pg_cursor.fetchone()
            # Conectar MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            mysql_cursor.execute("SELECT codigo, correo_electronico FROM acceso WHERE codigo = %s AND LOWER(correo_electronico) = LOWER(%s)", (company_rif, company_email))
            acceso = mysql_cursor.fetchone()
            
            
            if acceso:
                self.log_message("Datos adicionales obtenidos de mysql acceso", "info")                
            
            else:
                self.log_message("No se encontraron datos adicionales en acceso", "warning")
                mysql_cursor.close()
                mysql_conn.close()
                
                messagebox.showerror("Proceso Detenido", 
                                    "No se encontraron datos en acceso.\n" +
                                    "Verifique que exista una compañía con el email y rif especificado.\n" +
                                    "El proceso se ha detenido.")
                
                # Detener el flag de sincronización
                self.sync_running = False
                self.sync_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.status_var.set("Proceso detenido - No hay datos en mysql")
                
                # Lanzar excepción para salir del método
                raise Exception("Datos de compañía no encontrados en mysql")
            
            # Usar datos de PostgreSQL si existen
            if company_data:
                address, phone, rif_data, pg_email = company_data
                self.log_message("Datos adicionales obtenidos de PostgreSQL", "info")
            else:
                address, phone = None, None
                self.log_message("No se encontraron datos adicionales en PostgreSQL", "warning")
                 # Cerrar conexión PostgreSQL
                pg_cursor.close()
                pg_conn.close()
                
                # Mostrar mensaje y detener
                messagebox.showerror("Proceso Detenido", 
                                    "No se encontraron datos en PostgreSQL.\n" +
                                    "Verifique que exista una compañía con el email especificado.\n" +
                                    "El proceso se ha detenido.")
                
                # Detener el flag de sincronización
                self.sync_running = False
                self.sync_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
                self.status_var.set("Proceso detenido - No hay datos en PostgreSQL")
                
                # Lanzar excepción para salir del método
                raise Exception("Datos de compañía no encontrados en PostgreSQL")
            
            
            
            # Verificar si ya existe la compañía por RIF
            mysql_cursor.execute("SELECT id, name FROM companies WHERE rif = %s AND email = %s", (company_rif, company_email))
            existing = mysql_cursor.fetchone()
            
            if existing:
                self.log_message(f"Ya existe compañía con RIF {company_rif}: {existing[1]} (ID: {existing[0]})", "warning")
                
                # Actualizar compañía existente
                update_query = """
                UPDATE companies SET 
                    name = %s, 
                    email = %s, 
                    address = %s, 
                    phone = %s,
                    updated_at = NOW()
                WHERE rif = %s
                """
                
                mysql_cursor.execute(update_query, (
                    company_name,
                    company_email,
                    address,
                    phone,
                    company_rif
                ))
                mysql_conn.commit()
                self.company_id = existing[0]
                self.log_message(f"Compañía actualizada con ID: {self.company_id}", "success")
                
            else:
                # Insertar nueva compañía
                insert_query = """
                INSERT INTO companies (
                    address, phone, rif, email, name, key_system_items_id, status, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, 1, 'active', NOW(), NOW()
                )
                """
                company_email = company_email.lower()

                mysql_cursor.execute(insert_query, (
                    address,
                    phone,
                    company_rif,
                    company_email,
                    company_name
                ))
                
                mysql_conn.commit()
                self.company_id = mysql_cursor.lastrowid
                self.log_message(f"Nueva compañía insertada con ID: {self.company_id}", "success")
            
            # Mostrar resumen
            self.log_message("--- DATOS DE COMPAÑÍA ---", "info")
            self.log_message(f"ID: {self.company_id}", "info")
            self.log_message(f"RIF: {company_rif}", "info")
            self.log_message(f"Nombre: {company_name}", "info")
            self.log_message(f"Email: {company_email}", "info")
            if address:
                self.log_message(f"Dirección: {address}", "info")
            if phone:
                self.log_message(f"Teléfono: {phone}", "info")
            self.log_message("--- FIN DATOS ---", "info")
            
            pg_cursor.close()
            pg_conn.close()
            mysql_cursor.close()
            mysql_conn.close()
            
        except Exception as e:
            self.log_message(f"Error sincronizando companies: {str(e)}", "error")
            raise
    
    def sync_categories(self):
        """Sincronizar categories (departments → categories)"""
        self.log_message("=== SINCRONIZANDO CATEGORIES ===", "info")
        
        try:
            # Conectar PostgreSQL
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            
            query = """
            SELECT 
                code,
                description
            FROM department 
            WHERE code IS NOT NULL 
              AND code != ''
            ORDER BY code
            """
            
            pg_cursor.execute(query)
            departments = pg_cursor.fetchall()
            
            if not departments:
                self.log_message("No se encontraron departments", "warning")
                return
            
            # Conectar MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            for code, description in departments:
                check_query = """
                SELECT id FROM categories WHERE name = %s AND description = %s and company_id = %s
                """
                mysql_cursor.execute(check_query, (code, description,self.company_id))
                existing = mysql_cursor.fetchone()

                if existing:
                    update_query = """
                    UPDATE categories SET
                        company_id = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """
                    mysql_cursor.execute(update_query, (self.company_id, existing[0]))
                else:
                    insert_query = """
                    INSERT INTO categories (
                        company_id, name, description, status, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, 'active', NOW(), NOW()
                    )
                    """
                    mysql_cursor.execute(insert_query, (
                        self.company_id,
                        code,
                        description if description else None
                    ))
            
            mysql_conn.commit()
            self.log_message(f"Categories importadas: {len(departments)}", "success")
            
            pg_cursor.close()
            pg_conn.close()
            mysql_cursor.close()
            mysql_conn.close()
            
        except Exception as e:
            self.log_message(f"Error sincronizando categories: {str(e)}", "error")
            raise
    
    def sync_products(self):
        """Sincronizar products con JOINs completos"""
        self.log_message("=== SINCRONIZANDO PRODUCTS ===", "info")
        
        try:
            # Conectar PostgreSQL
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            
            query = """
            SELECT DISTINCT ON (a.code)                   
                a.code,    
                a.description,
                a.short_name,				
                a.department,	
                c.stock as stock,
                a.product_type,
                CASE 
                    WHEN b.maximum_price IS NULL OR b.maximum_price < 0 OR b.maximum_price > 99999999 
                    THEN 0 
                    ELSE b.maximum_price 
                END as price,
                CASE 
                    WHEN b.offer_price IS NULL OR b.offer_price < 0 OR b.offer_price > 99999999 
                    THEN 0 
                    ELSE b.offer_price 
                END as cost, 
                CASE 
                    WHEN b.higher_price IS NULL OR b.higher_price < 0 OR b.higher_price > 99999999 
                    THEN 0 
                    ELSE b.higher_price 
                END as higher_price,               
                CASE 
                    WHEN a.minimal_stock IS NULL OR a.minimal_stock < 0 OR a.minimal_stock > 2147483647 
                    THEN 0 
                    ELSE a.minimal_stock 
                END as min_stock,
                CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END as status,
                d.image_type,
	            d.product_image,
				a.sale_tax,
				e.aliquot
            FROM products a
            LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
            LEFT JOIN products_stock c ON a.code = c.product_code
            LEFT JOIN products_image d ON  d.main_code = a.code
			LEFT JOIN taxes e ON e.code = a.sale_tax
            WHERE a.code IS NOT NULL 
            AND a.code != ''             
            AND a.status = '01'
            ORDER BY a.code
            """
            
            pg_cursor.execute(query)
            products = pg_cursor.fetchall()
            
            if not products:
                self.log_message("No se encontraron products", "warning")
                return
            
            # Conectar MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            # Crear mapeo de categorías
            mysql_cursor.execute("SELECT name, id FROM categories WHERE company_id = %s", (self.company_id,))
            category_mapping = dict(mysql_cursor.fetchall())
            
            product_count = 0
            for product_data in products:
                if not self.sync_running:
                    break
                    
                code, description, short_name, department, stock, product_type, price, cost, higher_price, min_stock, status, image_type, product_image, sale_tax, aliquot = product_data

                product_count += 1
                
                # Obtener category_id
                category_id = category_mapping.get(department, 1)
                
                image_json = self.create_image_json(image_type, product_image)
                
                insert_query = """
                INSERT INTO products (
                    company_id,
                    code,
                    name,
                    description,
                    price,
                    cost,
                    stock,
                    min_stock,
                    category_id,
                    status,
                    product_type,
                    images,
                    higher_price,
                    sale_tax,
                    aliquot,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
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
                    updated_at = NOW()
                """
                
                mysql_cursor.execute(insert_query, (
                    self.company_id,
                    code,
                    short_name,  # El nombre del producto es short_name
                    description if description else None,
                    safe_float(price),
                    safe_float(cost),
                    stock if stock else 0,
                    int(min_stock) if min_stock else 0,
                    category_id,
                    status,  # Usar el status calculado del SELECT
                    product_type,
                    image_json,
                    higher_price,
                    sale_tax,
                    aliquot
                ))
                
                if product_count % 100 == 0:
                    self.log_message(f"Procesados {product_count} products...")
            
            mysql_conn.commit()
            self.log_message(f"Products importados: {product_count}", "success")
            
            pg_cursor.close()
            pg_conn.close()
            mysql_cursor.close()
            mysql_conn.close()
            
        except Exception as e:
            self.log_message(f"Error sincronizando products: {str(e)}", "error")
            raise
        
    def create_image_json(self, image_type, product_image):
        """Crear JSON para el campo image"""
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
            self.log_message(f"Error creando JSON de imagen: {str(e)}", "warning")
            return None
    
    def sync_customers(self):
        """Sincronizar customers (clients → customers)"""
        self.log_message("=== SINCRONIZANDO CUSTOMERS ===", "info")
        
        try:
            # Conectar PostgreSQL
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            
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
            WHERE code IS NOT NULL 
              AND code != ''
              AND description IS NOT NULL
              AND description != ''
            ORDER BY code
            """
            
            pg_cursor.execute(query)
            clients = pg_cursor.fetchall()
            
            if not clients:
                self.log_message("No se encontraron clients", "warning")
                return
            
            # Conectar MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            customer_count = 0
            inserted_count = 0
            updated_count = 0
            skipped_count = 0
            for client_data in clients:
                if not self.sync_running:
                    break
                    
                code, description, address, client_id, email, phone, contact = client_data
                customer_count += 1
                # Verificar si el customer ya existe
                check_query = "SELECT id, name FROM customers WHERE document_number = %s AND company_id = %s"
                mysql_cursor.execute(check_query, (code, self.company_id))
                existing_customer = mysql_cursor.fetchone()
                
                # Generar email temporal si no existe
                if not email or email.strip() == '':
                    email = f"customer_{code}@temp.local"
                
                if existing_customer:
                    # ACTUALIZAR si el nombre cambió
                    existing_id, existing_name = existing_customer
                    if existing_name != description:
                        update_query = """
                        UPDATE customers 
                        SET name = %s, email = %s, address = %s, phone = %s, contact = %s, updated_at = NOW() 
                        WHERE id = %s
                        """
                        mysql_cursor.execute(update_query, (description, email, address, phone, contact, existing_id))
                        updated_count += 1
                    else:
                        # No hacer nada si no hay cambios
                        skipped_count += 1
                else:
                    # INSERTAR nuevo
                    insert_query = """
                    INSERT INTO customers (
                        company_id, name, email, document_number, address, phone, contact, status,  created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    mysql_cursor.execute(insert_query, (
                        self.company_id, 
                        description, 
                        email, 
                        code, 
                        address if address else None, 
                        phone if phone else None,
                        contact if contact else None,
                        'active',
                        datetime.now(),
                        datetime.now()
                    ))
                    inserted_count += 1
                
                if customer_count % 10 == 0:
                    self.log_message(f"Procesados {customer_count} customers...")            
                    
            mysql_conn.commit()
            self.log_message(f"Total: {customer_count}, Nuevos: {inserted_count}, Actualizados: {updated_count}, Sin cambios: {skipped_count}", "success")
            
            pg_cursor.close()
            pg_conn.close()
            mysql_cursor.close()
            mysql_conn.close()
            
        except Exception as e:
            self.log_message(f"Error sincronizando customers: {str(e)}", "error")
            raise
    
    def sync_users(self):
        """Sincronizar users (sellers)"""
        self.log_message("=== SINCRONIZANDO USERS (SELLERS) ===", "info")
        
        try:
            # Conectar PostgreSQL
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            
            query = """
            SELECT 
                a.code as seller_code,
                b.description as user_name,
                b.email,
                b.user_password,
                b.code as user_code
            FROM sellers a 
            JOIN users b ON a.user_code = b.code
            WHERE b.email IS NOT NULL 
              AND b.email != ''
            ORDER BY a.code
            """
            
            pg_cursor.execute(query)
            users = pg_cursor.fetchall()
            
            if not users:
                self.log_message("No se encontraron users", "warning")
                return
            
            # Conectar MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            user_count = 0
            for user_data in users:
                if not self.sync_running:
                    break
                    
                seller_code, user_name, email, user_password, user_code = user_data
                user_count += 1
                
                # Hashear la contraseña usando bcrypt                
                laravel_password_hash = laravel_hash_make(user_password)
                insert_query = """
                INSERT INTO users (
                    name,
                    email,
                    role,
                    status,
                    password,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, 'seller', 'active', %s, NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    role = 'seller',
                    status = 'active',
                    updated_at = NOW()
                """

                mysql_cursor.execute(insert_query, (
                    user_name,
                    email,
                    laravel_password_hash
                ))
                
                if user_count % 5 == 0:
                    self.log_message(f"Procesados {user_count} users...")
            
            mysql_conn.commit()
            self.log_message(f"Users importados: {user_count}", "success")
            
            pg_cursor.close()
            pg_conn.close()
            mysql_cursor.close()
            mysql_conn.close()
            
        except Exception as e:
            self.log_message(f"Error sincronizando users: {str(e)}", "error")
            raise
    
    def sync_sellers(self):
        """Sincronizar sellers con relación user_id"""
        self.log_message("=== SINCRONIZANDO SELLERS ===", "info")
        sync_module = SmartSellersSyncModule(self)
        resultado = sync_module.ejecutar_sync()
        if not resultado:
            self.log_message("Sincronización de sellers completada con errores", "warning")
        return resultado
        
        try:
            # Conectar PostgreSQL
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            
            query = """
            SELECT 
                a.code as seller_code,
                b.description as user_name,
                b.email,
                b.user_password,
                b.code as user_code
            FROM sellers a 
            JOIN users b ON a.user_code = b.code
            WHERE b.email IS NOT NULL 
              AND b.email != ''
            ORDER BY a.code
            """
            
            pg_cursor.execute(query)
            sellers_data = pg_cursor.fetchall()
            
            if not sellers_data:
                self.log_message("No se encontraron sellers", "warning")
                return
            
            # Conectar MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            seller_count = 0
            for seller_data in sellers_data:
                if not self.sync_running:
                    break
                    
                seller_code, user_name, email, user_password, user_code = seller_data
                seller_count += 1
                
                # Buscar user_id por email
                mysql_cursor.execute(
                    "SELECT id FROM users WHERE email = %s AND role = 'seller' LIMIT 1",
                    (email,)
                )
                user_result = mysql_cursor.fetchone()
                
                if not user_result:
                    self.log_message(f"No se encontró user para email {email}", "warning")
                    continue
                
                user_id = user_result[0]
                
                insert_query = """
                INSERT INTO sellers (
                    user_id,
                    company_id,
                    code,
                    description,
                    status,
                    percent_sales,
                    percent_receivable,
                    inkeeper,
                    user_code,
                    percent_gerencial_debit_note,
                    percent_gerencial_credit_note,
                    percent_returned_check,
                    seller_status,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, 'active', 0.0, 0.0, 0, %s, 0.0, 0.0, 0.0, 'active', NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    description = VALUES(description),
                    status = VALUES(status),
                    seller_status = 'active',
                    user_code = VALUES(user_code),
                    updated_at = NOW()
                """
                
                mysql_cursor.execute(insert_query, (
                    user_id,
                    self.company_id,
                    seller_code,
                    user_name,
                    user_code
                ))
                
                if seller_count % 5 == 0:
                    self.log_message(f"Procesados {seller_count} sellers...")
            
            mysql_conn.commit()
            self.log_message(f"Sellers importados: {seller_count}", "success")
            
            pg_cursor.close()
            pg_conn.close()
            mysql_cursor.close()
            mysql_conn.close()
            
        except Exception as e:
            self.log_message(f"Error sincronizando sellers: {str(e)}", "error")
            raise

    def sync_quotes(self):
        """Sincronizar quotes desde MySQL a PostgreSQL y actualizar estados"""
        self.log_message("=== SINCRONIZANDO QUOTES (PRESUPUESTOS) ===", "info")
        
        try:
            # Conectar a MySQL para obtener quotes
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor(dictionary=True)
            
            # Query para obtener quotes de esta compañía
            quotes_query = """
            SELECT 
                a.id as idQuotes,
                a.quote_number,
                a.customer_id,
                a.company_id,
                a.user_seller_id,
                a.subtotal,
                a.tax,
                a.tax_amount,
                a.discount,
                a.discount_amount,
                a.total,
                a.bcv_rate,
                a.created_at,
                a.updated_at,
                b.name as customer_name,
                b.email as customer_email,
                b.phone as customer_phone,
                b.document_number as customer_doc,
                b.address as customer_address
            FROM quotes a
            LEFT JOIN customers b ON b.id = a.customer_id
            WHERE a.company_id = %s
            ORDER BY a.id
            """
            
            mysql_cursor.execute(quotes_query, (self.company_id,))
            quotes = mysql_cursor.fetchall()
            
            if not quotes:
                self.log_message(f"No se encontraron quotes para company_id {self.company_id}", "warning")
                mysql_cursor.close()
                mysql_conn.close()
                return
            
            self.log_message(f"Encontradas {len(quotes)} cotizaciones para migrar", "info")
            
            # Conectar a PostgreSQL
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_conn.autocommit = False
            
            migrated_count = 0
            error_count = 0
            
            for quote in quotes:
                if not self.sync_running:
                    break
                
                try:
                    quote_id = quote['idQuotes']
                    self.log_message(f"Procesando cotización #{quote_id}...", "info")
                    
                    # Obtener items de la cotización
                    items_query = """
                    SELECT 
                        a.quote_id,
                        a.description,
                        a.name,
                        a.subtotal,
                        a.unit,
                        a.unit_price,
                        a.total,
                        a.tax_amount,
                        a.discount_amount,
                        a.discount_percentage,
                        a.quantity,
                        a.item_type,
                        a.product_id,
                        c.code as product_code
                    FROM quote_items a
                    LEFT JOIN products c ON c.id = a.product_id
                    WHERE a.quote_id = %s
                    ORDER BY a.id
                    """
                    
                    mysql_cursor.execute(items_query, (quote_id,))
                    items = mysql_cursor.fetchall()
                    
                    if not items:
                        self.log_message(f"Quote {quote_id} no tiene items, saltando...", "warning")
                        continue
                    
                    # Migrar la cotización completa
                    self.migrate_single_quote(pg_conn, quote, items)
                    
                    pg_conn.commit()
                    migrated_count += 1
                    
                    if migrated_count % 10 == 0:
                        self.log_message(f"Procesadas {migrated_count} cotizaciones...", "info")
                    
                except Exception as e:
                    pg_conn.rollback()
                    error_count += 1
                    self.log_message(f"Error migrando quote {quote.get('idQuotes', '?')}: {str(e)}", "error")
            
            self.log_message(f"Migración completada: {migrated_count} exitosas, {error_count} con errores", "success")
            
            # SINCRONIZAR ESTADOS: Recorrer sales_operation y actualizar status en quotes
            self.sync_quotes_status(mysql_conn, pg_conn)
            
            mysql_cursor.close()
            mysql_conn.close()
            pg_conn.close()
            
        except Exception as e:
            self.log_message(f"Error sincronizando quotes: {str(e)}", "error")
            raise
    
    def sync_quotes_status(self, mysql_conn, pg_conn):
        """Sincronizar el estado de quotes existentes en MySQL con PostgreSQL"""
        self.log_message("=== SINCRONIZANDO ESTADOS DE QUOTES ===", "info")
        
        try:
            pg_cursor = pg_conn.cursor()
            mysql_cursor = mysql_conn.cursor(dictionary=True)
            
            # PASO 1: Obtener SOLO los presupuestos que ya existen en MySQL para esta compañía
            query_mysql_quotes = """
            SELECT 
                id,
                quote_number,
                company_id
            FROM quotes
            WHERE company_id = %s
            ORDER BY id
            """
            
            self.log_message(f"Buscando presupuestos en MySQL para company_id: {self.company_id}", "info")
            mysql_cursor.execute(query_mysql_quotes, (self.company_id,))
            quotes = mysql_cursor.fetchall()
            
            if not quotes:
                self.log_message(f"No se encontraron presupuestos en MySQL para company_id {self.company_id}", "warning")
                pg_cursor.close()
                mysql_cursor.close()
                return
            
            self.log_message(f"Encontrados {len(quotes)} presupuestos en MySQL para verificar estado", "info")
            
            updated_count = 0
            not_found_in_pg = 0
            
            # PASO 2: Procesar cada presupuesto
            for quote in quotes:
                if not self.sync_running:
                    break
                
                try:
                    quote_id = quote['id']
                    quote_number = quote['quote_number']
                    
                    self.log_message(f"Procesando presupuesto #{quote_number} (ID: {quote_id})...", "info")
                    
                    # PASO 3: Buscar la operación correspondiente en PostgreSQL
                    query_find_operation = """
                    SELECT 
                        correlative,
                        pending
                    FROM public.sales_operation
                    WHERE document_no = %s
                    AND operation_type = 'BUDGET'
                    LIMIT 1
                    """
                    
                    pg_cursor.execute(query_find_operation, (quote_number,))
                    operation_result = pg_cursor.fetchone()
                    
                    if not operation_result:
                        self.log_message(f"Presupuesto #{quote_number} (ID: {quote_id}) no encontrado en PostgreSQL", "warning")
                        not_found_in_pg += 1
                        continue
                    
                    correlative, pending = operation_result
                    
                    # PASO 4: Determinar el estado basado en pending
                    # pending = false → status = 'approved'
                    # pending = true → status = 'rejected'
                    new_status = 'rejected' if pending else 'approved'
                    
                    self.log_message(f"Presupuesto #{quote_number} (correlativo {correlative}): " +
                                f"pending={pending} → status='{new_status}'", "info")
                    
                    # PASO 5: Actualizar el status en MySQL
                    query_update_quote = """
                    UPDATE quotes 
                    SET status = %s, updated_at = NOW() 
                    WHERE id = %s
                    """
                    
                    mysql_cursor.execute(query_update_quote, (new_status, quote_id))
                    mysql_conn.commit()
                    
                    updated_count += 1
                    
                    self.log_message(f"Presupuesto #{quote_number} actualizado a '{new_status}'", "success")
                    
                    if updated_count % 10 == 0:
                        self.log_message(f"Estados verificados y actualizados: {updated_count}...", "info")
                    
                except Exception as e:
                    self.log_message(f"Error verificando presupuesto {quote_number}: {str(e)}", "error")
            
            # RESUMEN FINAL
            self.log_message("" , "info")
            self.log_message("=== RESUMEN DE VERIFICACIÓN ===", "info")
            self.log_message(f"Total procesados: {len(quotes)}", "info")
            self.log_message(f"Actualizados: {updated_count}", "success")
            self.log_message(f"No encontrados en PostgreSQL: {not_found_in_pg}", "warning")
            self.log_message(f"Verificación de estados completada", "success")
            
            pg_cursor.close()
            mysql_cursor.close()
            
        except Exception as e:
            self.log_message(f"Error en sincronización de estados: {str(e)}", "error")
            raise


    def migrate_single_quote(self, pg_conn, quote, items):
        """Migra una cotización individual a PostgreSQL"""
        pg_cursor = pg_conn.cursor()
        
        try:
            OFFSET_CORRELATIVO = 50000
            correlativo = quote['idQuotes'] + OFFSET_CORRELATIVO
            
            # Validar y preparar datos
            emission_date = quote.get('created_at')
            if emission_date is None:
                emission_date = datetime.now()
            elif isinstance(emission_date, str):
                emission_date = datetime.fromisoformat(emission_date)
            
            # Obtener o crear estación de trabajo
            mac = get_mac_address()
            pg_cursor.execute("SELECT code FROM stations WHERE code = %s", (mac,))
            existing_station = pg_cursor.fetchone()
            
            if not existing_station:
                self._create_station(pg_cursor, mac)
            
            # 1. INSERTAR SALES_OPERATION
            self._insert_sales_operation(
                pg_cursor, correlativo, quote, emission_date, mac
            )
            
            # 2. INSERTAR SALES_OPERATION_COINS
            self._insert_sales_operation_coins(
                pg_cursor, correlativo, quote
            )
            
            # 3. INSERTAR DETALLES E IMPUESTOS
            for item in items:
                self._insert_operation_detail(
                    pg_cursor, correlativo, item,quote
                )
            
            # 4. INSERTAR IMPUESTOS AGRUPADOS
            self._insert_operation_taxes(
                pg_cursor, correlativo, quote
            )
            
            pg_cursor.close()
            
        except Exception as e:
            self.log_message(f"Error en migrate_single_quote: {str(e)}", "error")
            raise


    def _create_station(self, pg_cursor, mac):
        """Crear estación de trabajo en PostgreSQL"""
        sql_insert_station = """
        INSERT INTO stations (
            code, 
            description, 
            sale_point, 
            bio_sale_point,
            numeration_sales_bill,
            numeration_sales_point_bill,
            numeration_income
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        pg_cursor.execute(sql_insert_station, (
            mac,
            f"Estación {mac[:17]}",
            '00',
            '00',
            '00',
            '00',
            '00'
        ))


    def _insert_sales_operation(self, pg_cursor, correlativo, quote, emission_date, mac):
        
        """Insertar registro principal en sales_operation"""        
        sql_operation = """
        INSERT INTO public.sales_operation (
            correlative, operation_type, document_no, emission_date, 
            register_date, client_code, client_name, client_id, 
            client_address, client_phone, seller, credit_days, 
            expiration_date, description, store, locations, user_code, 
            station, total_amount, total_net_details, total_tax_details, 
            total_details, percent_discount, discount, total_net, 
            total_tax, total, credit, cash, coin_code, canceled, 
            pending, wait, total_net_cost, total_tax_cost, total_cost, 
            freight_tax, freight_aliquot, document_no_internal, 
            control_no, operation_comments
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        document_no = quote.get('quote_number')
        
        pg_cursor.execute(sql_operation, (
            correlativo,                                              # correlative
            'BUDGET',                                                 # operation_type
            document_no,                                              # document_no
            emission_date,                                            # emission_date
            emission_date,                                            # register_date
            quote.get('customer_doc', 'ND'),                          # client_code
            quote.get('customer_name') or 'Cliente Migrado',          # client_name
            quote.get('customer_doc') or f"MIG-{quote['idQuotes']}",  # client_id
            quote.get('customer_address') or 'Dirección migrada',     # client_address
            quote.get('customer_phone') or 'S-N',                     # client_phone
            '00',                                                     # seller
            1,                                                        # credit_days
            emission_date + timedelta(days=1),                        # expiration_date
            '',                                                       # description
            '00',                                                     # store
            '00',                                                     # locations
            '00',                                                     # user_code
            mac,                                                      # station
            safe_float(quote.get('total', 0)),                        # total_amount
            safe_float(quote.get('subtotal', 0)),                     # total_net_details
            safe_float(quote.get('tax_amount', 0)),                   # total_tax_details
            safe_float(quote.get('total', 0)),                        # total_details
            safe_float(quote.get('discount', 0)),                     # percent_discount
            safe_float(quote.get('discount_amount', 0)),              # discount
            safe_float(quote.get('subtotal', 0)) - safe_float(quote.get('discount_amount', 0)), # total_net
            safe_float(quote.get('tax_amount', 0)),                   # total_tax
            safe_float(quote.get('total', 0)),                        # total
            0.0,                                                      # credit
            0.0,                                                      # cash
            '02',                                                     # coin_code (Dólar)
            False,                                                    # canceled
            True,                                                     # pending
            False,                                                    # wait
            safe_float(quote.get('subtotal', 0)),                     # total_net_cost
            safe_float(quote.get('tax_amount', 0)),                   # total_tax_cost
            safe_float(quote.get('total', 0)),                        # total_cost
            '01',                                                     # freight_tax
            16,                                                       # freight_aliquot
            document_no,                                              # document_no_internal
            '',                                                       # control_no
            ''                                                        # operation_comments
        ))


    def _insert_sales_operation_coins(self, pg_cursor, correlativo, quote):
        """Insertar monedas de la operación"""
        
        bcv_rate = safe_float(quote.get('bcv_rate', 170))
        
        ##Calculo con bolivares
        subtotalBcv = safe_float(quote.get('subtotal', 0)) * bcv_rate
        taxAmountBcv = safe_float(quote.get('tax_amount', 0)) * bcv_rate
        totalBcv = safe_float(quote.get('total', 0)) * bcv_rate
        discountAmountBcv = safe_float(quote.get('discount_amount', 0)) * bcv_rate
        
        
        sql_coins = """
        INSERT INTO public.sales_operation_coins (
            main_correlative, coin_code, factor_type, buy_aliquot, 
            sales_aliquot, total_net_details, total_tax_details, 
            total_details, discount, freight, total_net, total_tax, 
            total, credit, cash
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        pg_cursor.execute(sql_coins, (
            correlativo, '02', 1, bcv_rate, bcv_rate,
            safe_float(quote.get('subtotal', 0)),
            safe_float(quote.get('tax_amount', 0)),
            safe_float(quote.get('total', 0)),
            safe_float(quote.get('discount_amount', 0)),
            0.0,
            safe_float(quote.get('subtotal', 0)) - safe_float(quote.get('discount_amount', 0)),
            safe_float(quote.get('tax_amount', 0)),
            safe_float(quote.get('total', 0)),
            0.0,
            0.0
        ))
        
        pg_cursor.execute(sql_coins, (
            correlativo, '01', 1, bcv_rate, bcv_rate,
            subtotalBcv,
            taxAmountBcv,
            totalBcv,
            discountAmountBcv,
            0.0,
            subtotalBcv - discountAmountBcv,
            taxAmountBcv,
            totalBcv,
            0.0,
            0.0
        ))


    def _insert_operation_detail(self, pg_cursor, correlativo, item,quote):
        """Insertar detalle de producto en la operación"""
        
        unit_id = self.get_unit_id(item.get('product_code'), pg_cursor)
        
        # Calcular alícuota si hay subtotal
        item_subtotal = safe_float(item.get('subtotal', 1))
        item_tax = safe_float(item.get('tax_amount', 0))
        
        if item_subtotal > 0:
            tax_percent = (item_tax / item_subtotal * 100)
        else:
            tax_percent = 0
        
        sql_detail = """
        INSERT INTO public.sales_operation_details (
            main_correlative, code_product, description_product, amount, 
            store, locations, unit, conversion_factor, unit_type, unitary_cost, 
            sale_tax, sale_aliquot, price, total_net_cost, total_tax_cost, 
            total_cost, total_net_gross, total_tax_gross, total_gross, 
            percent_discount, discount, total_net, total_tax, total, 
            coin_code, buy_aliquot, buy_tax,pending_amount
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING line
        """
        
        unit_price = safe_float(item.get('unit_price', 0))
        quantity = safe_float(item.get('quantity', 0))
        
        pg_cursor.execute(sql_detail, (
            correlativo,                                               # main_correlative
            item.get('product_code') or f"MIG-{item.get('product_id', 'ND')}", # code_product
            item.get('name', 'Producto migrado'),                     # description_product
            quantity,                                                 # amount
            '00',                                                     # store
            '00',                                                     # locations
            unit_id,                                                  # unit
            1.0,                                                      # conversion_factor
            1,                                                        # unit_type
            unit_price * 0.8,                                        # unitary_cost
            '01',                                                     # sale_tax
            tax_percent,                                              # sale_aliquot
            unit_price,                                               # price
            quantity * unit_price * 0.8,                             # total_net_cost
            item_tax * 0.8,                                          # total_tax_cost
            quantity * unit_price * 0.8 + item_tax * 0.8,           # total_cost
            safe_float(item.get('subtotal', 0)),                     # total_net_gross
            item_tax,                                                 # total_tax_gross
            safe_float(item.get('total', 0)),                        # total_gross
            safe_float(item.get('discount_percentage', 0)),          # percent_discount
            safe_float(item.get('discount_amount', 0)),              # discount
            safe_float(item.get('subtotal', 0)) - safe_float(item.get('discount_amount', 0)), # total_net
            item_tax,                                                 # total_tax
            safe_float(item.get('total', 0)),                        # total
            '02',                                                     # coin_code
            16,                                                       # buy_aliquot
            '01',                                                      # buy_tax
            quantity
        ))
        
        line = pg_cursor.fetchone()[0]
        bcv_rate = safe_float(quote.get('bcv_rate', 170))
        unit_priceBcv = unit_price * bcv_rate
        quantityBcv = quantity
        subtotalBcv = safe_float(item.get('subtotal', 0)) * bcv_rate
        item_taxBcv = safe_float(item.get('tax_amount', 0)) * bcv_rate
        totalBcv = safe_float(item.get('total', 0)) * bcv_rate
        discountAmountBcv = safe_float(item.get('discount_amount', 0)) * bcv_rate
        
        # Insertar moneda del detalle
        sql_detail_coins = """
        INSERT INTO public.sales_operation_details_coins (
            main_correlative, main_line, unitary_cost, price, 
            total_net_cost, total_tax_cost, total_cost, 
            total_net_gross, total_tax_gross, total_gross, 
            discount, total_net, total_tax, total, coin_code
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        pg_cursor.execute(sql_detail_coins, (
            correlativo, line,
            unit_price * 0.8,
            unit_price,
            quantity * unit_price * 0.8,
            item_tax * 0.8,
            quantity * unit_price * 0.8 + item_tax * 0.8,
            safe_float(item.get('subtotal', 0)),
            item_tax,
            safe_float(item.get('total', 0)),
            safe_float(item.get('discount_amount', 0)),
            safe_float(item.get('subtotal', 0)) - safe_float(item.get('discount_amount', 0)),
            item_tax,
            safe_float(item.get('total', 0)),
            '02'
        ))
        
        pg_cursor.execute(sql_detail_coins, (
            correlativo, line,
            unit_priceBcv * 0.8,
            unit_priceBcv,
            quantityBcv * unit_priceBcv * 0.8,
            item_taxBcv * 0.8,
            quantityBcv * unit_priceBcv * 0.8 + item_taxBcv * 0.8,
            subtotalBcv,
            item_tax,
            totalBcv,
            discountAmountBcv,
            subtotalBcv - discountAmountBcv,
            item_tax,
            totalBcv,
            '01'
        ))


    def _insert_operation_taxes(self, pg_cursor, correlativo, quote):
        """Insertar impuestos agrupados de la operación"""
        
        bcv = safe_float(quote.get('bcv_rate', 170))
        
        quote_tax_amount = safe_float(quote.get('tax_amount', 0))
        quote_subtotal = safe_float(quote.get('subtotal', 0))
        quote_discount = safe_float(quote.get('discount_amount', 0))
        
        quote_tax_amountBcv = quote_tax_amount * bcv
        quote_subtotalBcv = quote_subtotal * bcv
        quote_discountBcv = quote_discount * bcv
        
        if quote_tax_amount > 0 and quote_subtotal > 0:
            # Calcular la alícuota desde la cotización
            quote_aliquot = (quote_tax_amount / quote_subtotal * 100)
            quote_aliquotBcv = (quote_tax_amountBcv / quote_subtotalBcv * 100)
            
            # Base imponible (subtotal menos descuento)
            taxable_amount = quote_subtotal - quote_discount
            taxable_amountBcv = quote_subtotalBcv - quote_discountBcv
            
            tax_code = '01'  # IVA General 16%
            
            self.log_message(f"Insertando impuesto para correlativo {correlativo}", "info")
            
            # Insertar en sales_operation_taxes
            sql_tax = """
            INSERT INTO public.sales_operation_taxes (
                main_correlative, taxe_code, aliquot, taxable, tax, tax_type
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            pg_cursor.execute(sql_tax, (
                correlativo, tax_code, quote_aliquot,
                taxable_amount, quote_tax_amount, 1
            ))
            
            # Insertar en sales_operation_taxes_coins
            sql_tax_coins = """
            INSERT INTO public.sales_operation_taxes_coins (
                main_correlative, main_taxe_code, taxable, tax, coin_code
            ) VALUES (%s, %s, %s, %s, %s)
            """
            
            pg_cursor.execute(sql_tax_coins, (
                correlativo, tax_code, taxable_amount, quote_tax_amount, '02'
            ))
            
            pg_cursor.execute(sql_tax_coins, (
                correlativo, tax_code, taxable_amountBcv, quote_tax_amountBcv, '01'
            ))
            

def main():
    """Función principal"""
    root = tk.Tk()
    
    # Configurar manejo de errores
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        error_msg = f"Error no manejado: {exc_type.__name__}: {exc_value}"
        messagebox.showerror("Error Crítico", error_msg)
        
    sys.excepthook = handle_exception
    
    # Crear aplicación
    app = CompleteSyncApp(root)
    
    # Configurar cierre de aplicación
    def on_closing():
        if app.sync_running:
            if messagebox.askokcancel("Cerrar", "Hay una sincronización en curso. ¿Desea cerrar de todas formas?"):
                app.sync_running = False
                root.destroy()
        else:
            if messagebox.askokcancel("Salir", "¿Desea cerrar la aplicación?"):
                root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Mostrar atajos en el log
    app.log_message("=== ATAJOS DE TECLADO ===", "info")
    app.log_message("F5: Probar conexiones", "info")
    app.log_message("Ctrl+S: Guardar log", "info")
    app.log_message("Ctrl+L: Limpiar log", "info")
    app.log_message("========================", "info")
    
    # Configurar atajos
    root.bind('<F5>', lambda e: app.test_connections())
    root.bind('<Control-s>', lambda e: app.save_log())
    root.bind('<Control-l>', lambda e: app.clear_log())
    
    # Iniciar aplicación
    try:
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error Fatal", f"Error iniciando aplicación: {str(e)}")

if __name__ == "__main__":
    main()