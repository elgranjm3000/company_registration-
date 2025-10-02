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
            'host': 'localhost',
            'database': 'pruebadb',
            'user': 'postgres',
            'password': 'muentes123.'
        }
        
        # Configuración MySQL con valores fijos (ocultos al usuario)
        self.mysql_config = {
            'host': '91.238.160.176',  # Valor fijo oculto
            'database': 'chrystal_movil',
            'user': 'chrystal_app',
            'password': 'muentes123.'  # Valor fijo oculto
        }
        #self.mysql_config = {
        #    'host': 'localhost',  # Valor fijo oculto
        #    'database': 'salesapi',
        #    'user': 'root',
        #    'password': 'tiger.'  # Valor fijo oculto
        #}
        
        # Variable global para company_id
        self.company_id = None
        
        # Control de sincronización
        self.sync_running = False
        
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
        
        ttk.Label(pg_frame, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.pg_host_var = tk.StringVar(value=self.postgresql_config['host'])
        ttk.Entry(pg_frame, textvariable=self.pg_host_var, width=25).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(pg_frame, text="Database:").grid(row=1, column=0, sticky=tk.W)
        self.pg_db_var = tk.StringVar(value=self.postgresql_config['database'])
        ttk.Entry(pg_frame, textvariable=self.pg_db_var, width=25).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(pg_frame, text="Usuario:").grid(row=2, column=0, sticky=tk.W)
        self.pg_user_var = tk.StringVar(value=self.postgresql_config['user'])
        ttk.Entry(pg_frame, textvariable=self.pg_user_var, width=25).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(pg_frame, text="Password:").grid(row=3, column=0, sticky=tk.W)
        self.pg_pass_var = tk.StringVar(value=self.postgresql_config['password'])
        ttk.Entry(pg_frame, textvariable=self.pg_pass_var, show="*", width=25).grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
      
        
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
        self.company_rif_var = tk.StringVar(value="J502741283")
        rif_entry = ttk.Entry(company_frame, textvariable=self.company_rif_var, width=25)
        rif_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(company_frame, text="Email:*").grid(row=1, column=0, sticky=tk.W)
        self.company_email_var = tk.StringVar(value="multiserviciosleblanc@gmail.com")
        email_entry = ttk.Entry(company_frame, textvariable=self.company_email_var, width=25)
        email_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(company_frame, text="Nombre:*").grid(row=2, column=0, sticky=tk.W)
        self.company_name_var = tk.StringVar(value="MULTISERVICIOS LEBLANC ON LINE, C.A")
        name_entry = ttk.Entry(company_frame, textvariable=self.company_name_var, width=25)
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
            'host': self.pg_host_var.get(),
            'database': self.pg_db_var.get(),
            'user': self.pg_user_var.get(),
            'password': self.pg_pass_var.get()
        }
        
        # MySQL config: mantener valores fijos para host y password, actualizar solo los campos visibles
        #self.mysql_config = {
        #    'host': '91.238.160.176',  # Valor fijo
        #    'database': 'chrystal_movil',
        #    'user': 'chrystal_app',
        #    'password': 'muentes123.'  # Valor fijo
        #}
        
        self.mysql_config = {
            'host': 'localhost',  # Valor fijo
            'database': 'salesapi',
            'user': 'root',
            'password': 'tiger'  # Valor fijo
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
    
    def complete_sync_process(self):
        """Proceso completo de sincronización"""
        start_time = datetime.now()
        self.log_message("=== INICIANDO SINCRONIZACIÓN COMPLETA ===", "info")
        self.log_message("PostgreSQL → MySQL", "info")
        
        try:
            self.update_config()
            
            # Resetear progress
            self.progress_var.set(0)
            total_steps = sum([
                self.sync_companies_var.get(),
                self.sync_categories_var.get(),
                self.sync_products_var.get(),
                self.sync_customers_var.get(),
                self.sync_users_var.get(),
                self.sync_sellers_var.get(),
                self.sync_quotes_var.get()
            ])
            current_step = 0
            
            # 1. Companies (obligatorio para obtener company_id)
            if self.sync_companies_var.get():
                if not self.sync_running:
                    return
                self.status_var.set("Sincronizando Companies...")
                self.sync_companies()
                current_step += 1
                self.progress_var.set((current_step / total_steps) * 100)
            
            # 2. Categories
            if self.sync_categories_var.get() and self.company_id:
                if not self.sync_running:
                    return
                self.status_var.set("Sincronizando Categories...")
                self.sync_categories()
                current_step += 1
                self.progress_var.set((current_step / total_steps) * 100)
            
            # 3. Products
            if self.sync_products_var.get() and self.company_id:
                if not self.sync_running:
                    return
                self.status_var.set("Sincronizando Products...")
                self.sync_products()
                current_step += 1
                self.progress_var.set((current_step / total_steps) * 100)
            
            # 4. Customers
            if self.sync_customers_var.get() and self.company_id:
                if not self.sync_running:
                    return
                self.status_var.set("Sincronizando Customers...")
                self.sync_customers()
                current_step += 1
                self.progress_var.set((current_step / total_steps) * 100)
            
            # 5. Users
            if self.sync_users_var.get():
                if not self.sync_running:
                    return
                self.status_var.set("Sincronizando Users...")
                self.sync_users()
                current_step += 1
                self.progress_var.set((current_step / total_steps) * 100)
            
            # 6. Sellers
            if self.sync_sellers_var.get() and self.company_id:
                if not self.sync_running:
                    return
                self.status_var.set("Sincronizando Sellers...")
                self.sync_sellers()
                current_step += 1
                self.progress_var.set((current_step / total_steps) * 100)
                
            if self.sync_quotes_var.get() and self.company_id:
                if not self.sync_running:
                    return
                self.status_var.set("Sincronizando Quotes...")
                self.sync_quotes()
                current_step += 1
                self.progress_var.set((current_step / total_steps) * 100)
            
            # Reporte final
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.log_message("=== SINCRONIZACIÓN COMPLETADA ===", "success")
            self.log_message(f"Tiempo total: {duration:.1f} segundos", "info")
            self.log_message(f"Company ID: {self.company_id}", "info")
            
            self.status_var.set("Sincronización completada exitosamente")
            self.progress_var.set(100)
            
            messagebox.showinfo("Éxito", f"Sincronización completada en {duration:.1f} segundos")
            
        except Exception as e:
            self.log_message(f"Error durante sincronización: {str(e)}", "error")
            self.status_var.set("Error en sincronización")
            messagebox.showerror("Error", f"Error en sincronización: {str(e)}")
        
        finally:
            self.sync_running = False
            self.sync_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
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
            SELECT                 
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
                    WHEN a.minimal_stock IS NULL OR a.minimal_stock < 0 OR a.minimal_stock > 2147483647 
                    THEN 0 
                    ELSE a.minimal_stock 
                END as min_stock,
                CASE WHEN a.status = '01' THEN 'active' ELSE 'inactive' END as status,
                d.image_type,
	            d.product_image                
            FROM products a
            LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
            LEFT JOIN products_stock c ON a.code = c.product_code
            LEFT JOIN products_image d ON  d.main_code = a.code
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
                    
                # CORREGIDO: Variables en el MISMO ORDEN que el SELECT
                code, description, short_name, department, stock, product_type, price, cost, min_stock, status, image_type,product_image = product_data
                #  1       2           3           4          5       6            7      8       9         10
                
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
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
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
                    image_json
                ))
                
                # Debug opcional
                if product_count <= 5:  # Solo mostrar los primeros 5 para debug
                    print(f"Producto {product_count}:")
                    print(f"  Code: {code}")
                    print(f"  Name: {short_name}")
                    print(f"  Description: {description}")
                    print(f"  Department: {department}")
                    print(f"  Price: {price}")
                    print(f"  Cost: {cost}")
                    print(f"  Stock: {stock}")
                    print(f"  Status: {status}")
                    print("---")
                
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
                email
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
            skipped_count = 0  # Si usas la versión con control
            for client_data in clients:
                if not self.sync_running:
                    break
                    
                code, description, address, client_id, email = client_data
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
                        SET name = %s, email = %s, address = %s, updated_at = NOW() 
                        WHERE id = %s
                        """
                        mysql_cursor.execute(update_query, (description, email, address, existing_id))
                        updated_count += 1
                    else:
                        # No hacer nada si no hay cambios
                        skipped_count += 1
                else:
                    # INSERTAR nuevo
                    insert_query = """
                    INSERT INTO customers (
                        company_id, name, email, document_number, address, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, 'active', NOW(), NOW())
                    """
                    mysql_cursor.execute(insert_query, (
                        self.company_id, description, email, code, address if address else None
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
                    %s, %s, 'seller', 'inactive', %s, NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    role = 'seller',
                    status = 'inactive',
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
                    %s, %s, %s, %s, 'inactive', 0.0, 0.0, 0, %s, 0.0, 0.0, 0.0, 'inactive', NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    description = VALUES(description),
                    status = VALUES(status),
                    seller_status = 'inactive',
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
            """Sincronizar quotes desde MySQL a PostgreSQL"""
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
                            self.log_message(f"Procesadas {migrated_count} cotizaciones...")
                        
                    except Exception as e:
                        pg_conn.rollback()
                        error_count += 1
                        self.log_message(f"Error migrando quote {quote['idQuotes']}: {str(e)}", "error")
                
                self.log_message(f"Migración completada: {migrated_count} exitosas, {error_count} errores", "success")
                
                mysql_cursor.close()
                mysql_conn.close()
                pg_conn.close()
                
            except Exception as e:
                self.log_message(f"Error sincronizando quotes: {str(e)}", "error")
                raise

    def migrate_single_quote(self, pg_conn, quote, items):
            """Migra una cotización individual a PostgreSQL"""
            pg_cursor = pg_conn.cursor()
            
            OFFSET_CORRELATIVO = 50000
            correlativo = quote['idQuotes'] + OFFSET_CORRELATIVO
            
            # 1. Insertar sales_operation
            emission_date = quote.get('created_at') or datetime.now()
            
            mac = get_mac_address()
            pg_cursor.execute("SELECT code FROM stations WHERE code = %s", (mac,))
            existing_station = pg_cursor.fetchone()
            
            if not existing_station:
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
                ON CONFLICT (code) DO NOTHING;
                """
                
                pg_cursor.execute(sql_insert_station, (
                    mac,  # código = MAC address
                    f"Estación {mac[:17]}",  # descripción
                    '00',  # sale_point
                    '00',  # bio_sale_point
                    '00',  # numeration_sales_bill
                    '00',  # numeration_sales_point_bill
                    '00'   # numeration_income
                ))

            
            sql_operation = """
            INSERT INTO public.sales_operation (
                correlative, operation_type, document_no, 
                emission_date, register_date, client_code, client_name, 
                client_id, client_address, client_phone, seller, 
                credit_days, expiration_date, description, store, locations, 
                user_code, station, total_amount, total_net_details, 
                total_tax_details, total_details, percent_discount, discount, 
                total_net, total_tax, total, credit, cash, coin_code, 
                canceled, pending,wait,total_net_cost,total_tax_cost,total_cost,freight_tax,freight_aliquot,
                document_no_internal                
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                %s, %s, %s,%s,%s,%s,%s,%s,%s,%s
            )
            """
            
            pg_cursor.execute(sql_operation, (
                correlativo, 'BUDGET',
                f"W-{correlativo:06d}",              
                emission_date, emission_date,
                quote['customer_doc'], quote['customer_name'] or 'Cliente Migrado',
                quote['customer_doc'] or f"MIG-{quote['idQuotes']}",
                quote['customer_address'] or 'Dirección migrada',
                quote['customer_phone'] or 'S-N',
                '00', 1, emission_date + timedelta(days=1),
                f"''",
                '00', '00', '00', f"{mac}",
                safe_float(quote['total']),
                safe_float(quote['subtotal']),
                safe_float(quote['tax_amount']),
                safe_float(quote['total']),
                safe_float(quote['discount']),
                safe_float(quote['discount_amount']),
                safe_float(quote['subtotal']) - safe_float(quote['discount_amount']),
                safe_float(quote['tax_amount']),
                safe_float(quote['total']),
                safe_float(quote['total']),
                0.0, '02', False, True,False,
                safe_float(quote['subtotal']),
                safe_float(quote['tax_amount']),
                safe_float(quote['total']),
                "01",
                16,
                f"W-{correlativo:06d}",  
            ))
            
            # 2. Insertar sales_operation_coins
            bcv_rate = safe_float(quote.get('bcv_rate', 170))
            
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
                safe_float(quote['subtotal']),
                safe_float(quote['tax_amount']),
                safe_float(quote['total']),
                safe_float(quote['discount_amount']),
                0.0,
                safe_float(quote['subtotal']) - safe_float(quote['discount_amount']),
                safe_float(quote['tax_amount']),
                safe_float(quote['total']),
                safe_float(quote['total']),
                0.0
            ))
            
            # 3. Insertar detalles
            for item in items:
                unit_id = self.get_unit_id(item.get('product_code'), pg_cursor)
                tax_percent = safe_float(item.get('tax_amount', 0)) / safe_float(item.get('subtotal', 1)) * 100 if item.get('subtotal') else 0
                
                sql_detail = """
                INSERT INTO public.sales_operation_details (
                    main_correlative, code_product, description_product, 
                    amount, store, locations, unit, conversion_factor, unit_type, 
                    unitary_cost, sale_tax, sale_aliquot, price, 
                    total_net_cost, total_tax_cost, total_cost, 
                    total_net_gross, total_tax_gross, total_gross, 
                    percent_discount, discount, total_net, total_tax, total, 
                    coin_code
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING line
                """
                
                pg_cursor.execute(sql_detail, (
                    correlativo,
                    item.get('product_code') or f"MIG-{item['product_id']}",
                    item['name'],
                    safe_float(item['quantity']),
                    '00', '00', unit_id, 1.0, 1,
                    safe_float(item['unit_price']) * 0.8,
                    self.get_tax_code(tax_percent),
                    tax_percent,
                    safe_float(item['unit_price']),
                    safe_float(item['quantity']) * safe_float(item['unit_price']) * 0.8,
                    safe_float(item['tax_amount']) * 0.8,
                    safe_float(item['quantity']) * safe_float(item['unit_price']) * 0.8 + safe_float(item['tax_amount']) * 0.8,
                    safe_float(item['subtotal']),
                    safe_float(item['tax_amount']),
                    safe_float(item['total']),
                    safe_float(item.get('discount_percentage', 0)),
                    safe_float(item.get('discount_amount', 0)),
                    safe_float(item['subtotal']) - safe_float(item.get('discount_amount', 0)),
                    safe_float(item['tax_amount']),
                    safe_float(item['total']),
                    '02'
                ))
                
                line = pg_cursor.fetchone()[0]
                
                # Insertar detail_coins
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
                    safe_float(item['unit_price']) * 0.8,
                    safe_float(item['unit_price']),
                    safe_float(item['quantity']) * safe_float(item['unit_price']) * 0.8,
                    safe_float(item['tax_amount']) * 0.8,
                    safe_float(item['quantity']) * safe_float(item['unit_price']) * 0.8 + safe_float(item['tax_amount']) * 0.8,
                    safe_float(item['subtotal']),
                    safe_float(item['tax_amount']),
                    safe_float(item['total']),
                    safe_float(item.get('discount_amount', 0)),
                    safe_float(item['subtotal']) - safe_float(item.get('discount_amount', 0)),
                    safe_float(item['tax_amount']),
                    safe_float(item['total']),
                    '02'
                ))
            
            # 4. Insertar impuestos agrupados
            taxes_dict = {}
            for item in items:
                tax_percent = safe_float(item.get('tax_amount', 0)) / safe_float(item.get('subtotal', 1)) * 100 if item.get('subtotal') else 0
                tax_code = self.get_tax_code(tax_percent)
                
                if tax_code not in taxes_dict:
                    taxes_dict[tax_code] = {'aliquot': tax_percent, 'taxable': 0.0, 'tax': 0.0}
                
                taxes_dict[tax_code]['taxable'] += safe_float(item['subtotal']) - safe_float(item.get('discount_amount', 0))
                taxes_dict[tax_code]['tax'] += safe_float(item.get('tax_amount', 0))
            
            for tax_code, tax_data in taxes_dict.items():
                if tax_data['tax'] == 0:
                    continue
                
                sql_tax = """
                INSERT INTO public.sales_operation_taxes (
                    main_correlative, taxe_code, aliquot, taxable, tax, tax_type
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                pg_cursor.execute(sql_tax, (
                    correlativo, tax_code, tax_data['aliquot'],
                    tax_data['taxable'], tax_data['tax'], 1
                ))
                
                sql_tax_coins = """
                INSERT INTO public.sales_operation_taxes_coins (
                    main_correlative, main_taxe_code, taxable, tax, coin_code
                ) VALUES (%s, %s, %s, %s, %s)
                """
                
                pg_cursor.execute(sql_tax_coins, (
                    correlativo, tax_code, tax_data['taxable'], tax_data['tax'], '02'
                ))
            
            pg_cursor.close()

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