"""
INTERFAZ DE ADMINISTRACIÓN: SyncManager
Gestor visual del servicio de sincronización PostgreSQL → MySQL

Funcionalidades:
- Ver estado del servicio
- Iniciar/Detener/Reiniciar servicio
- Ver logs en tiempo real
- Forzar sincronización manual
- Configurar intervalo
- Reconfigurar conexiones

Autor: Sistema de Sincronización
Fecha: 2025-01-22
Versión: 1.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import threading
import time
import os
import json
from datetime import datetime
import win32service
import win32con
import win32api

class SyncManager:
    """
    Interfaz gráfica para gestionar el servicio de sincronización
    """

    def __init__(self, root):
        self.root = root
        self.root.title("Sync Manager - Sincronizador PostgreSQL → MySQL")
        self.root.geometry("900x700")
        self.root.resizable(True, True)

        # Variables
        self.service_name = "PostgreSQLMySQLSync"
        self.status_var = tk.StringVar(value="Desconocido")
        self.log_content = tk.StringVar()
        self.auto_refresh = tk.BooleanVar(value=True)
        self.last_sync_var = tk.StringVar(value="Nunca")
        self.next_sync_var = tk.StringVar(value="N/A")
        self.interval_var = tk.IntVar(value=3600)

        # Configurar estilos
        self.setup_styles()

        # Crear interfaz
        self.create_widgets()

        # Iniciar verificación de estado
        self.check_status()
        self.start_auto_refresh()

    def setup_styles(self):
        """Configurar estilos personalizados"""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 11, 'bold'))
        style.configure('Status.TLabel', font=('Arial', 10))

        # Frame con colores de estado
        style.configure('Green.TFrame', background='#d4edda')
        style.configure('Red.TFrame', background='#f8d7da')
        style.configure('Yellow.TFrame', background='#fff3cd')

    def create_widgets(self):
        """Crear todos los widgets de la interfaz"""
        # Notebook principal (pestañas)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Pestaña 1: Estado
        self.create_status_tab(notebook)

        # Pestaña 2: Controles
        self.create_controls_tab(notebook)

        # Pestaña 3: Configuración
        self.create_config_tab(notebook)

        # Pestaña 4: Logs
        self.create_logs_tab(notebook)

    def create_status_tab(self, notebook):
        """Crear pestaña de estado"""
        status_frame = ttk.Frame(notebook, padding="20")
        notebook.add(status_frame, text="📊 Estado")

        # Título
        title = ttk.Label(status_frame, text="Estado del Servicio", style='Title.TLabel')
        title.pack(pady=(0, 20))

        # Estado con color
        self.status_container = tk.Frame(status_frame, relief=tk.RAISED, borderwidth=2)
        self.status_container.pack(fill=tk.X, pady=(0, 20))

        self.status_label = tk.Label(
            self.status_container,
            textvariable=self.status_var,
            font=('Arial', 16, 'bold'),
            pady=20
        )
        self.status_label.pack(fill=tk.BOTH, expand=True)

        # Información
        info_frame = ttk.LabelFrame(status_frame, text="Información", padding="15")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # Última sincronización
        ttk.Label(info_frame, text="Última Sincronización:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(info_frame, textvariable=self.last_sync_var, style='Status.TLabel').grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Próxima sincronización
        ttk.Label(info_frame, text="Próxima Sincronización:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(info_frame, textvariable=self.next_sync_var, style='Status.TLabel').grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Intervalo
        ttk.Label(info_frame, text="Intervalo:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.interval_display = ttk.Label(info_frame, text="1 hora", style='Status.TLabel')
        self.interval_display.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Estadísticas
        stats_frame = ttk.LabelFrame(status_frame, text="Estadísticas", padding="15")
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=8, font=('Consolas', 9))
        self.stats_text.pack(fill=tk.BOTH, expand=True)

        # Botón refresh
        refresh_btn = ttk.Button(status_frame, text="🔄 Refrescar Estado", command=self.check_status)
        refresh_btn.pack(fill=tk.X)

    def create_controls_tab(self, notebook):
        """Crear pestaña de controles"""
        controls_frame = ttk.Frame(notebook, padding="20")
        notebook.add(controls_frame, text="🎮 Controles")

        # Título
        title = ttk.Label(controls_frame, text="Control del Servicio", style='Title.TLabel')
        title.pack(pady=(0, 20))

        # Botones principales
        buttons_frame = ttk.LabelFrame(controls_frame, text="Acciones", padding="15")
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(buttons_frame, text="▶️ Iniciar Servicio", command=self.start_service).pack(fill=tk.X, pady=5)
        ttk.Button(buttons_frame, text="⏸️ Detener Servicio", command=self.stop_service).pack(fill=tk.X, pady=5)
        ttk.Button(buttons_frame, text="🔄 Reiniciar Servicio", command=self.restart_service).pack(fill=tk.X, pady=5)
        ttk.Button(buttons_frame, text="⚡ Sincronizar Ahora", command=self.sync_now).pack(fill=tk.X, pady=5)

        # Opciones
        options_frame = ttk.LabelFrame(controls_frame, text="Opciones", padding="15")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Checkbutton(options_frame, text="Auto-refrescar estado (cada 5s)", variable=self.auto_refresh).pack(anchor=tk.W)

        # Información
        info_frame = ttk.LabelFrame(controls_frame, text="Información del Servicio", padding="15")
        info_frame.pack(fill=tk.BOTH, expand=True)

        info_text = tk.Text(info_frame, height=10, font=('Consolas', 9), wrap=tk.WORD)
        info_text.pack(fill=tk.BOTH, expand=True)

        info_text.insert('1.0',
            "Nombre del servicio: PostgreSQLMySQLSync\n"
            "Display Name: Sincronizador PostgreSQL a MySQL\n\n"
            "El servicio se ejecuta en segundo plano y realiza\n"
            "sincronización automática de PostgreSQL a MySQL.\n\n"
            "Puede gestionar el servicio también desde:\n"
            "services.msc (Servicios de Windows)"
        )
        info_text.config(state=tk.DISABLED)

    def create_config_tab(self, notebook):
        """Crear pestaña de configuración"""
        config_frame = ttk.Frame(notebook, padding="20")
        notebook.add(config_frame, text="⚙️ Configuración")

        # Título
        title = ttk.Label(config_frame, text="Configuración de Sincronización", style='Title.TLabel')
        title.pack(pady=(0, 20))

        # Intervalo
        interval_frame = ttk.LabelFrame(config_frame, text="Intervalo de Sincronización", padding="15")
        interval_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(interval_frame, text="Seleccione la frecuencia:").pack(anchor=tk.W, pady=(0, 10))

        intervalos = [
            (300, "5 minutos"),
            (900, "15 minutos"),
            (1800, "30 minutos"),
            (3600, "1 hora"),
            (7200, "2 horas"),
            (14400, "4 horas")
        ]

        for valor, texto in intervalos:
            ttk.Radiobutton(
                interval_frame,
                text=texto,
                value=valor,
                variable=self.interval_var
            ).pack(anchor=tk.W, pady=2)

        ttk.Button(
            interval_frame,
            text="💾 Aplicar Intervalo",
            command=self.apply_interval
        ).pack(fill=tk.X, pady=(10, 0))

        # Archivo de configuración
        config_file_frame = ttk.LabelFrame(config_frame, text="Archivo de Configuración", padding="15")
        config_file_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            config_file_frame,
            text="El archivo de configuración está en:\n.env",
            font=('Consolas', 9)
        ).pack(anchor=tk.W, pady=5)

        ttk.Button(
            config_file_frame,
            text="📂 Abrir Ubicación",
            command=self.open_config_location
        ).pack(fill=tk.X, pady=5)

        ttk.Button(
            config_file_frame,
            text="🔧 Editar .env",
            command=self.edit_env_file
        ).pack(fill=tk.X, pady=5)

    def create_logs_tab(self, notebook):
        """Crear pestaña de logs"""
        logs_frame = ttk.Frame(notebook, padding="20")
        notebook.add(logs_frame, text="📋 Logs")

        # Título
        title = ttk.Label(logs_frame, text="Logs de Sincronización", style='Title.TLabel')
        title.pack(pady=(0, 10))

        # Controles de logs
        log_controls = ttk.Frame(logs_frame)
        log_controls.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(log_controls, text="🔄 Refrescar", command=self.refresh_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_controls, text="📥 Exportar", command=self.export_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_controls, text="🗑️ Limpiar", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_controls, text="📂 Abrir Archivo", command=self.open_log_file).pack(side=tk.LEFT, padx=5)

        # Área de logs
        self.log_text = scrolledtext.ScrolledText(logs_frame, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Cargar logs iniciales
        self.refresh_logs()

    # ====================================================================
    # MÉTODOS DE CONTROL DEL SERVICIO
    # ====================================================================

    def check_status(self):
        """Verificar estado del servicio"""
        try:
            # Intentar conectar con el servicio
            hscm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
            hs = win32service.OpenService(hscm, self.service_name, win32service.SERVICE_INTERROGATE)

            status = win32service.QueryServiceStatus(hs)

            win32service.CloseServiceHandle(hs)
            win32service.CloseServiceHandle(hscm)

            # Interpretar estado
            if status[1] == win32service.SERVICE_RUNNING:
                self.status_var.set("🟢 EN EJECUCIÓN")
                self.status_container.config(bg='#d4edda')
                self.status_label.config(bg='#d4edda', fg='#155724')
            elif status[1] == win32service.SERVICE_STOPPED:
                self.status_var.set("🔴 DETENIDO")
                self.status_container.config(bg='#f8d7da')
                self.status_label.config(bg='#f8d7da', fg='#721c24')
            elif status[1] == win32service.SERVICE_START_PENDING:
                self.status_var.set("🟡 INICIANDO...")
                self.status_container.config(bg='#fff3cd')
                self.status_label.config(bg='#fff3cd', fg='#856404')
            elif status[1] == win32service.SERVICE_STOP_PENDING:
                self.status_var.set("🟡 DETENIENDO...")
                self.status_container.config(bg='#fff3cd')
                self.status_label.config(bg='#fff3cd', fg='#856404')
            else:
                self.status_var.set("⚪ PAUSADO")
                self.status_container.config(bg='#e2e3e5')
                self.status_label.config(bg='#e2e3e5', fg='#383d41')

            # Actualizar información de última sincronización
            self.update_sync_info()

        except Exception as e:
            self.status_var.set("❌ NO INSTALADO")
            self.status_container.config(bg='#f8d7da')
            self.status_label.config(bg='#f8d7da', fg='#721c24')
            self.last_sync_var.set("N/A")
            self.next_sync_var.set("N/A")

    def start_service(self):
        """Iniciar el servicio"""
        try:
            result = subprocess.run(
                ['python', 'sync_service.py', 'start'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                messagebox.showinfo("Éxito", "Servicio iniciado correctamente")
                self.check_status()
            else:
                messagebox.showerror("Error", f"Error iniciando servicio:\n{result.stderr}")

        except subprocess.TimeoutExpired:
            messagebox.showerror("Error", "Timeout iniciando servicio")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")

    def stop_service(self):
        """Detener el servicio"""
        if not messagebox.askyesno("Confirmar", "¿Desea detener el servicio?"):
            return

        try:
            result = subprocess.run(
                ['python', 'sync_service.py', 'stop'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                messagebox.showinfo("Éxito", "Servicio detenido correctamente")
                self.check_status()
            else:
                messagebox.showerror("Error", f"Error deteniendo servicio:\n{result.stderr}")

        except subprocess.TimeoutExpired:
            messagebox.showerror("Error", "Timeout deteniendo servicio")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")

    def restart_service(self):
        """Reiniciar el servicio"""
        try:
            # Detener
            subprocess.run(
                ['python', 'sync_service.py', 'stop'],
                capture_output=True,
                timeout=30
            )

            time.sleep(2)

            # Iniciar
            result = subprocess.run(
                ['python', 'sync_service.py', 'start'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                messagebox.showinfo("Éxito", "Servicio reiniciado correctamente")
                self.check_status()
            else:
                messagebox.showerror("Error", f"Error reiniciando servicio:\n{result.stderr}")

        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")

    def sync_now(self):
        """Forzar sincronización inmediata"""
        if messagebox.askyesno("Confirmar", "¿Desea ejecutar una sincronización ahora?\n\nEsto puede tardar varios minutos."):
            try:
                from dotenv import load_dotenv
                load_dotenv()

                from smart_sync_complete import ServiceApp, SmartSyncComplete

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

                company_id = 1  # O obtener dinámicamente

                # Crear app y sync
                app = ServiceApp(postgresql_config, mysql_config, company_id)
                sync = SmartSyncComplete(app, postgresql_config, mysql_config, company_id)

                # Ejecutar en thread
                def run_sync():
                    sync.ejecutar_sync_completa()
                    messagebox.showinfo("Completado", "Sincronización finalizada")
                    self.check_status()

                thread = threading.Thread(target=run_sync)
                thread.daemon = True
                thread.start()

            except Exception as e:
                messagebox.showerror("Error", f"Error ejecutando sincronización:\n{str(e)}")

    # ====================================================================
    # MÉTODOS DE CONFIGURACIÓN
    # ====================================================================

    def apply_interval(self):
        """Aplicar nuevo intervalo de sincronización"""
        interval = self.interval_var.get()

        # Actualizar .env
        try:
            with open('.env', 'r') as f:
                lines = f.readlines()

            # Buscar y reemplazar SYNC_INTERVAL_SECONDS
            found = False
            for i, line in enumerate(lines):
                if line.startswith('SYNC_INTERVAL_SECONDS='):
                    lines[i] = f'SYNC_INTERVAL_SECONDS={interval}\n'
                    found = True
                    break

            if not found:
                lines.append(f'SYNC_INTERVAL_SECONDS={interval}\n')

            with open('.env', 'w') as f:
                f.writelines(lines)

            messagebox.showinfo(
                "Éxito",
                f"Intervalo actualizado a {interval} segundos.\n"
                "Reinicie el servicio para aplicar los cambios."
            )

            # Actualizar display
            minutos = interval // 60
            if minutos < 60:
                self.interval_display.config(text=f"{minutos} minutos")
            else:
                horas = minutos // 60
                self.interval_display.config(text=f"{horas} hora(s)")

        except Exception as e:
            messagebox.showerror("Error", f"Error actualizando intervalo:\n{str(e)}")

    def open_config_location(self):
        """Abrir ubicación del archivo de configuración"""
        try:
            os.startfile(os.getcwd())
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")

    def edit_env_file(self):
        """Abrir archivo .env en editor de texto"""
        try:
            os.startfile('.env')
        except Exception as e:
            messagebox.showerror("Error", f"Error abriendo archivo:\n{str(e)}")

    # ====================================================================
    # MÉTODOS DE LOGS
    # ====================================================================

    def refresh_logs(self):
        """Refrescar logs desde archivo"""
        try:
            if os.path.exists('sync_service.log'):
                with open('sync_service.log', 'r', encoding='utf-8') as f:
                    content = f.read()

                    # Mostrar últimas 100 líneas
                    lines = content.split('\n')[-100:]
                    self.log_text.delete('1.0', tk.END)
                    self.log_text.insert('1.0', '\n'.join(lines))
                    self.log_text.see(tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Error leyendo logs:\n{str(e)}")

    def export_logs(self):
        """Exportar logs a archivo"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")],
                title="Exportar Logs"
            )

            if filename:
                content = self.log_text.get('1.0', tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Éxito", f"Logs exportados a:\n{filename}")

        except Exception as e:
            messagebox.showerror("Error", f"Error exportando logs:\n{str(e)}")

    def clear_logs(self):
        """Limpiar logs de pantalla"""
        self.log_text.delete('1.0', tk.END)

    def open_log_file(self):
        """Abrir archivo de log en editor de texto"""
        try:
            if os.path.exists('sync_service.log'):
                os.startfile('sync_service.log')
            else:
                messagebox.showwarning("Advertencia", "El archivo de logs no existe aún.")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}")

    # ====================================================================
    # MÉTODOS AUXILIARES
    # ====================================================================

    def update_sync_info(self):
        """Actualizar información de sincronización"""
        try:
            if os.path.exists('sync_service.log'):
                # Leer última línea de sync
                with open('sync_service.log', 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                    if lines:
                        # Buscar última línea con timestamp
                        for line in reversed(lines[-20:]):
                            if line.strip():
                                self.last_sync_var.set(line.strip()[:50])
                                break

                        # Calcular próxima sync
                        minutos = self.interval_var.get() // 60
                        self.next_sync_var.set(f"En {minutos} minutos")
            else:
                self.last_sync_var.set("Aún no hay logs")
                self.next_sync_var.set("N/A")

        except Exception as e:
            self.last_sync_var.set("Error")
            self.next_sync_var.set("Error")

    def start_auto_refresh(self):
        """Iniciar auto-refresco de estado"""
        def refresh_loop():
            while True:
                if self.auto_refresh.get():
                    self.check_status()
                time.sleep(5)

        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()


# ====================================================================
# FUNCIÓN PRINCIPAL
# ====================================================================

def main():
    """Función principal"""
    root = tk.Tk()
    app = SyncManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
