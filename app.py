import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import mysql.connector
import psycopg2
from mysql.connector import Error as MySQLError
from psycopg2 import Error as PostgreSQLError
import re
import sys
import os
from datetime import datetime
import threading

def resource_path(relative_path):
    """Obtener ruta de recurso para PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
            'password': ''
        }
        
        self.mysql_config = {
            'host': '',
            'database': 'chrystal_movil',
            'user': 'chrystal_app',
            'password': ''
        }
        
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
        
        # Configuración MySQL
        mysql_frame = ttk.LabelFrame(scrollable_frame, text="MySQL (Destino)", padding="10")
        mysql_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        mysql_frame.columnconfigure(1, weight=1)
        
        ttk.Label(mysql_frame, text="Host:").grid(row=0, column=0, sticky=tk.W)
        self.mysql_host_var = tk.StringVar(value=self.mysql_config['host'])
        ttk.Entry(mysql_frame, textvariable=self.mysql_host_var, width=25).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(mysql_frame, text="Database:").grid(row=1, column=0, sticky=tk.W)
        self.mysql_db_var = tk.StringVar(value=self.mysql_config['database'])
        ttk.Entry(mysql_frame, textvariable=self.mysql_db_var, width=25).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(mysql_frame, text="Usuario:").grid(row=2, column=0, sticky=tk.W)
        self.mysql_user_var = tk.StringVar(value=self.mysql_config['user'])
        ttk.Entry(mysql_frame, textvariable=self.mysql_user_var, width=25).grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(mysql_frame, text="Password:").grid(row=3, column=0, sticky=tk.W)
        self.mysql_pass_var = tk.StringVar(value=self.mysql_config['password'])
        ttk.Entry(mysql_frame, textvariable=self.mysql_pass_var, show="*", width=25).grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
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
        
        self.mysql_config = {
            'host': self.mysql_host_var.get(),
            'database': self.mysql_db_var.get(),
            'user': self.mysql_user_var.get(),
            'password': self.mysql_pass_var.get()
        }
    
    def test_connections(self):
        """Probar conexiones a ambas bases de datos"""
        self.update_config()
        self.log_message("=== PROBANDO CONEXIONES ===", "info")
        
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
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            if mysql_conn.is_connected():
                db_info = mysql_conn.get_server_info()
                self.log_message(f"MySQL conectado: Server {db_info}", "success")
                mysql_conn.close()
        except Exception as e:
            self.log_message(f"Error conectando MySQL: {str(e)}", "error")
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
                self.sync_sellers_var.get()
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
            WHERE c.address IS NOT NULL 
               OR c.phone IS NOT NULL 
               OR c.description IS NOT NULL
            ORDER BY c.id
            LIMIT 1
            """
            
            pg_cursor.execute(query)
            company_data = pg_cursor.fetchone()
            
            # Usar datos de PostgreSQL si existen
            if company_data:
                address, phone, rif_data, pg_email = company_data
                self.log_message("Datos adicionales obtenidos de PostgreSQL", "info")
            else:
                address, phone = None, None
                self.log_message("No se encontraron datos adicionales en PostgreSQL", "warning")
            
            # Conectar MySQL
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            # Verificar si ya existe la compañía por RIF
            mysql_cursor.execute("SELECT id, name FROM companies WHERE rif = %s", (company_rif,))
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
                insert_query = """
                INSERT INTO categories (
                    company_id, name, description, status, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, 'active', NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    description = VALUES(description),
                    updated_at = NOW()
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
                    WHEN c.stock IS NULL OR c.stock < 0 OR c.stock > 2147483647 
                    THEN 0 
                    ELSE c.stock 
                END as stock,
                CASE 
                    WHEN a.minimal_stock IS NULL OR a.minimal_stock < 0 OR a.minimal_stock > 2147483647 
                    THEN 0 
                    ELSE a.minimal_stock 
                END as min_stock,
                CASE WHEN a.status = 'A' THEN 'active' ELSE 'inactive' END as status
            FROM products a
            LEFT JOIN PRODUCTS_UNITS b ON a.code = b.product_code
            LEFT JOIN products_stock c ON a.code = c.product_code
            WHERE a.code IS NOT NULL 
              AND a.code != ''
              AND LENGTH(a.code) <= 255
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
                    
                code, description, short_name, department, price, cost, stock, min_stock, status = product_data
                product_count += 1
                
                # Obtener category_id
                category_id = category_mapping.get(department, 1)
                
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
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
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
                    updated_at = NOW()
                """
                
                mysql_cursor.execute(insert_query, (
                    self.company_id,
                    code,
                    short_name,
                    description if description else None,
                    float(price) if price else 0.0,
                    float(cost) if cost else 0.0,
                    stock if stock else 0,
                    int(min_stock) if min_stock else 0,
                    category_id,
                    status
                ))
                
                if product_count % 10 == 0:
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
            for client_data in clients:
                if not self.sync_running:
                    break
                    
                code, description, address, client_id, email = client_data
                customer_count += 1
                
                # Generar email temporal si no existe
                if not email or email.strip() == '':
                    email = f"customer_{code}@temp.local"
                
                insert_query = """
                INSERT INTO customers (
                    company_id,
                    name,
                    email,
                    document_number,
                    address,
                    status,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, 'active', NOW(), NOW()
                )
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    document_number = VALUES(document_number),
                    address = VALUES(address),
                    status = 'active',
                    updated_at = NOW()
                """
                
                mysql_cursor.execute(insert_query, (
                    self.company_id,
                    description,
                    email,
                    code,
                    address if address else None
                ))
                
                if customer_count % 10 == 0:
                    self.log_message(f"Procesados {customer_count} customers...")
            
            mysql_conn.commit()
            self.log_message(f"Customers importados: {customer_count}", "success")
            
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
                
                hashed_password = "$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi"
                
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
                    hashed_password
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