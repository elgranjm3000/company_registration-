import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import mysql.connector
from mysql.connector import Error
import re
import sys
import os
from datetime import datetime

def resource_path(relative_path):
    """Obtener ruta de recurso para PyInstaller"""
    try:
        # PyInstaller crea una carpeta temporal y almacena la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class CompanyRegistrationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Registro de Compañías - Sistema de Sincronización")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configurar icono si existe
        try:
            icon_path = resource_path("assets/icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass  # Continuar sin icono si hay error
        
        # Variables para la conexión MySQL
        self.mysql_config = {
            'host': '91.238.160.176',
            'database': 'chrystal_movil',
            'user': 'chrystal_app',
            'password': 'muentes123.'
        }
        
        self.setup_styles()
        self.create_widgets()
        self.center_window()
        
        # Agregar información de versión
        self.log_message("=== APLICACIÓN DE REGISTRO DE COMPAÑÍAS ===", "info")
        self.log_message(f"Versión: 1.0", "info")
        self.log_message(f"Python: {sys.version.split()[0]}", "info")
        self.log_message("Listo para conectar", "info")
        
    def setup_styles(self):
        """Configurar estilos personalizados"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground='#34495e')
        style.configure('Success.TLabel', foreground='#27ae60', font=('Arial', 10, 'bold'))
        style.configure('Error.TLabel', foreground='#e74c3c', font=('Arial', 10, 'bold'))
        
    def create_widgets(self):
        """Crear todos los widgets de la interfaz"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights para responsividad
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Título principal
        title_label = ttk.Label(main_frame, text="Registro de Nueva Compañía", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Frame para formulario
        form_frame = ttk.LabelFrame(main_frame, text="Información de la Compañía", padding="15")
        form_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        form_frame.columnconfigure(1, weight=1)
        
        # Campo RIF
        ttk.Label(form_frame, text="RIF:*", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.rif_var = tk.StringVar()
        self.rif_entry = ttk.Entry(form_frame, textvariable=self.rif_var, font=('Arial', 11))
        self.rif_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Etiqueta de ayuda para RIF
        rif_help = ttk.Label(form_frame, text="Ej: J502741283, V123456789, E123456789", 
                           foreground='#7f8c8d', font=('Arial', 9))
        rif_help.grid(row=0, column=2, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Campo Email
        ttk.Label(form_frame, text="Email:*", style='Header.TLabel').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(form_frame, textvariable=self.email_var, font=('Arial', 11))
        self.email_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Campo Nombre
        ttk.Label(form_frame, text="Nombre:*", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(form_frame, textvariable=self.name_var, font=('Arial', 11))
        self.name_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Campo Dirección (opcional)
        ttk.Label(form_frame, text="Dirección:", style='Header.TLabel').grid(row=3, column=0, sticky=tk.W, pady=5)
        self.address_var = tk.StringVar()
        self.address_entry = ttk.Entry(form_frame, textvariable=self.address_var, font=('Arial', 11))
        self.address_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Campo Teléfono (opcional)
        ttk.Label(form_frame, text="Teléfono:", style='Header.TLabel').grid(row=4, column=0, sticky=tk.W, pady=5)
        self.phone_var = tk.StringVar()
        self.phone_entry = ttk.Entry(form_frame, textvariable=self.phone_var, font=('Arial', 11))
        self.phone_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Frame para configuración de BD
        config_frame = ttk.LabelFrame(main_frame, text="Configuración de Base de Datos", padding="10")
        config_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Mostrar configuración actual
        ttk.Label(config_frame, text="Host:", font=('Arial', 9)).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(config_frame, text=self.mysql_config['host'], font=('Arial', 9, 'bold')).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(config_frame, text="BD:", font=('Arial', 9)).grid(row=1, column=0, sticky=tk.W)
        ttk.Label(config_frame, text=self.mysql_config['database'], font=('Arial', 9, 'bold')).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        # Botones
        self.register_btn = ttk.Button(button_frame, text="Registrar Compañía", 
                                     command=self.register_company)
        self.register_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.test_conn_btn = ttk.Button(button_frame, text="Probar Conexión", 
                                      command=self.test_connection)
        self.test_conn_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(button_frame, text="Limpiar Campos", 
                                  command=self.clear_fields)
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.exit_btn = ttk.Button(button_frame, text="Salir", 
                                 command=self.on_closing)
        self.exit_btn.pack(side=tk.LEFT)
        
        # Frame para resultado
        result_frame = ttk.LabelFrame(main_frame, text="Log de Actividad", padding="10")
        result_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        result_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Área de texto para mostrar resultados
        self.result_text = scrolledtext.ScrolledText(result_frame, height=15, font=('Consolas', 9))
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Frame para botones del log
        log_button_frame = ttk.Frame(result_frame)
        log_button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.clear_log_btn = ttk.Button(log_button_frame, text="Limpiar Log", 
                                      command=self.clear_log)
        self.clear_log_btn.pack(side=tk.LEFT)
        
        self.save_log_btn = ttk.Button(log_button_frame, text="Guardar Log", 
                                     command=self.save_log)
        self.save_log_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Etiqueta de estado
        self.status_var = tk.StringVar(value="Listo para registrar")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.grid(row=5, column=0, columnspan=3, pady=(10, 0))
        
        # Configurar eventos
        self.setup_events()
        
    def setup_events(self):
        """Configurar eventos y validaciones"""
        # Validación en tiempo real del RIF
        self.rif_var.trace('w', self.validate_rif)
        
        # Validación del email
        self.email_var.trace('w', self.validate_email)
        
        # Enter en los campos para registrar
        for entry in [self.rif_entry, self.email_entry, self.name_entry, 
                     self.address_entry, self.phone_entry]:
            entry.bind('<Return>', lambda e: self.register_company())
        
        # Atajos de teclado
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<F5>', lambda e: self.test_connection())
        self.root.bind('<Control-r>', lambda e: self.register_company())
        self.root.bind('<Control-l>', lambda e: self.clear_log())
            
    def validate_rif(self, *args):
        """Validar formato del RIF en tiempo real"""
        rif = self.rif_var.get().upper()
        # Permitir solo letras válidas al inicio y números
        if rif and not re.match(r'^[VEJGC]?\d*$', rif):
            # Limpiar caracteres inválidos
            cleaned = re.sub(r'[^VEJGC0-9]', '', rif)
            self.rif_var.set(cleaned)
            
    def validate_email(self, *args):
        """Validar formato básico del email"""
        email = self.email_var.get()
        if email and '@' in email:
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                self.email_entry.configure(foreground='black')
            else:
                self.email_entry.configure(foreground='red')
        else:
            self.email_entry.configure(foreground='black')
            
    def center_window(self):
        """Centrar la ventana en la pantalla"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def log_message(self, message, type="info"):
        """Agregar mensaje al área de resultado con timestamp"""
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
        """Limpiar el log de actividad"""
        self.result_text.delete(1.0, tk.END)
        self.log_message("Log limpiado")
        
    def save_log(self):
        """Guardar el log en un archivo"""
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
                title="Guardar Log"
            )
            
            if filename:
                log_content = self.result_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log_message(f"Log guardado en: {filename}", "success")
                
        except Exception as e:
            self.log_message(f"Error guardando log: {str(e)}", "error")
        
    def clear_fields(self):
        """Limpiar todos los campos del formulario"""
        self.rif_var.set("")
        self.email_var.set("")
        self.name_var.set("")
        self.address_var.set("")
        self.phone_var.set("")
        self.status_var.set("Campos limpiados")
        self.log_message("Campos del formulario limpiados")
        
    def validate_form(self):
        """Validar que los campos requeridos estén completos"""
        errors = []
        
        rif = self.rif_var.get().strip()
        email = self.email_var.get().strip()
        name = self.name_var.get().strip()
        
        if not rif:
            errors.append("El RIF es obligatorio")
        elif not re.match(r'^[VEJGC]\d{8,9}$', rif):
            errors.append("RIF debe tener formato válido (ej: J502741283)")
            
        if not email:
            errors.append("El email es obligatorio")
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append("Email debe tener formato válido")
            
        if not name:
            errors.append("El nombre de la compañía es obligatorio")
            
        return errors
        
    def test_connection(self):
        """Probar conexión a la base de datos MySQL"""
        self.status_var.set("Probando conexión...")
        self.log_message("Iniciando prueba de conexión a MySQL")
        
        try:
            connection = mysql.connector.connect(**self.mysql_config)
            if connection.is_connected():
                db_info = connection.get_server_info()
                self.log_message(f"Conexión exitosa a MySQL Server {db_info}", "success")
                self.log_message(f"Base de datos: {self.mysql_config['database']}", "info")
                
                # Probar una consulta simple
                cursor = connection.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM companies")
                result = cursor.fetchone()
                self.log_message(f"Compañías existentes en BD: {result[0]}", "info")
                
                # Verificar estructura de tabla
                cursor.execute("DESCRIBE companies")
                columns = cursor.fetchall()
                self.log_message(f"Tabla companies tiene {len(columns)} columnas", "info")
                
                cursor.close()
                connection.close()
                self.status_var.set("Conexión exitosa")
                
        except Error as e:
            self.log_message(f"Error de conexión: {str(e)}", "error")
            self.status_var.set("Error de conexión")
            
    def register_company(self):
        """Registrar la compañía en la base de datos"""
        # Validar formulario
        errors = self.validate_form()
        if errors:
            for error in errors:
                self.log_message(error, "error")
            self.status_var.set("Error en validación")
            return
            
        # Obtener valores
        rif = self.rif_var.get().strip().upper()
        email = self.email_var.get().strip()
        name = self.name_var.get().strip()
        address = self.address_var.get().strip() or None
        phone = self.phone_var.get().strip() or None
        
        self.status_var.set("Registrando compañía...")
        self.log_message(f"Iniciando registro de compañía: {name}")
        self.log_message(f"RIF: {rif}, Email: {email}")
        
        try:
            connection = mysql.connector.connect(**self.mysql_config)
            cursor = connection.cursor()
            
            # Verificar si ya existe una compañía con el mismo RIF
            cursor.execute("SELECT id, name FROM companies WHERE rif = %s", (rif,))
            existing = cursor.fetchone()
            
            if existing:
                self.log_message(f"⚠️ Ya existe una compañía con RIF {rif}: {existing[1]} (ID: {existing[0]})", "warning")
                response = messagebox.askyesno(
                    "Compañía Existente", 
                    f"Ya existe una compañía con RIF {rif}:\n{existing[1]}\n\n¿Desea actualizarla?",
                    icon='warning'
                )
                
                if response:
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
                    cursor.execute(update_query, (name, email, address, phone, rif))
                    connection.commit()
                    
                    self.log_message(f"Compañía actualizada exitosamente (ID: {existing[0]})", "success")
                    self.status_var.set("Compañía actualizada")
                else:
                    self.log_message("Operación cancelada por el usuario", "info")
                    self.status_var.set("Operación cancelada")
                    
            else:
                # Insertar nueva compañía
                insert_query = """
                INSERT INTO companies (
                    address, phone, rif, email, name, 
                    key_system_items_id, status, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, 1, 'active', NOW(), NOW()
                )
                """
                
                cursor.execute(insert_query, (address, phone, rif, email, name))
                connection.commit()
                
                company_id = cursor.lastrowid
                self.log_message(f"Nueva compañía registrada exitosamente con ID: {company_id}", "success")
                self.status_var.set(f"Compañía registrada (ID: {company_id})")
                
                # Mostrar información de la compañía registrada
                self.log_message("--- DATOS REGISTRADOS ---", "info")
                self.log_message(f"ID: {company_id}", "info")
                self.log_message(f"RIF: {rif}", "info")
                self.log_message(f"Nombre: {name}", "info")
                self.log_message(f"Email: {email}", "info")
                if address:
                    self.log_message(f"Dirección: {address}", "info")
                if phone:
                    self.log_message(f"Teléfono: {phone}", "info")
                self.log_message("--- FIN DATOS ---", "info")
                
            cursor.close()
            connection.close()
            
            messagebox.showinfo("Éxito", "Operación completada exitosamente")
            
        except Error as e:
            error_msg = f"Error de base de datos: {str(e)}"
            self.log_message(error_msg, "error")
            self.status_var.set("Error en registro")
            messagebox.showerror("Error", error_msg)
            
        except Exception as e:
            error_msg = f"Error inesperado: {str(e)}"
            self.log_message(error_msg, "error")
            self.status_var.set("Error inesperado")
            messagebox.showerror("Error", error_msg)
            
    def on_closing(self):
        """Manejar cierre de aplicación"""
        if messagebox.askokcancel("Salir", "¿Desea cerrar la aplicación?"):
            self.log_message("Cerrando aplicación...", "info")
            self.root.destroy()

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
    app = CompanyRegistrationApp(root)
    
    # Configurar cierre de aplicación
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Mostrar atajos de teclado en el log
    app.log_message("=== ATAJOS DE TECLADO ===", "info")
    app.log_message("Ctrl+R: Registrar compañía", "info")
    app.log_message("F5: Probar conexión", "info")
    app.log_message("Ctrl+L: Limpiar log", "info")
    app.log_message("Ctrl+Q: Salir", "info")
    app.log_message("Enter: Registrar (desde cualquier campo)", "info")
    app.log_message("========================", "info")
    
    # Iniciar aplicación
    try:
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error Fatal", f"Error iniciando aplicación: {str(e)}")

if __name__ == "__main__":
    main()