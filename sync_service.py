"""
SERVICIO DE WINDOWS: Sincronizador PostgreSQL → MySQL
Se ejecuta en segundo plano y sincroniza periódicamente

Instalación:
    python sync_service.py install
    python sync_service.py start

Desinstalación:
    python sync_service.py stop
    python sync_service.py remove

Autor: Sistema de Sincronización
Fecha: 2025-01-22
Versión: 1.0
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import sys
import os
from dotenv import load_dotenv
import mysql.connector
import logging

# Importar módulo de sincronización
from smart_sync_complete import SmartSyncComplete, ServiceApp

# Configurar logging
logging.basicConfig(
    filename='sync_service.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)


class PostgreSQLMySQLSyncService(win32serviceutil.ServiceFramework):
    """
    Servicio de Windows para sincronización PostgreSQL → MySQL
    """

    _svc_name_ = "PostgreSQLMySQLSync"
    _svc_display_name_ = "Sincronizador PostgreSQL a MySQL"
    _svc_description_ = "Sincroniza automáticamente datos de PostgreSQL a MySQL cada X minutos"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)

        # Evento de parada
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        # Configuración del servicio
        self.sync_interval = 3600  # 1 hora en segundos (configurable)
        self.app = None
        self.sync_module = None

        # Flags
        self.is_running = True

        # Configurar logging
        self.logger = logging.getLogger(__name__)

    def SvcStop(self):
        """
        Detener el servicio
        """
        try:
            self.logger.info("Recibida señal de detención del servicio...")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPING,
                ('Deteniendo servicio de sincronización...', '')
            )

            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

            # Detener sincronización si está corriendo
            if self.app:
                self.app.sync_running = False
            if self.sync_module:
                self.sync_module.sync_running = False

            self.is_running = False

            # Señalizar evento de parada
            win32event.SetEvent(self.hWaitStop)

            self.logger.info("Servicio detenido correctamente")
            servicemanager.LogInfoMsg("Servicio detenido")

        except Exception as e:
            self.logger.error(f"Error deteniendo servicio: {str(e)}")

    def SvcDoRun(self):
        """
        Punto principal de ejecución del servicio
        """
        try:
            self.logger.info("=== INICIANDO SERVICIO DE SINCRONIZACIÓN ===")
            servicemanager.LogInfoMsg("Iniciando servicio de sincronización PostgreSQL → MySQL")

            # Cargar configuración
            self.load_configuration()

            # Obtener company_id
            self.logger.info("Obteniendo company_id desde MySQL...")
            company_id = self.get_company_id()

            if not company_id:
                self.logger.error("No se pudo obtener company_id. Deteniendo servicio.")
                servicemanager.LogErrorMsg("Error: No se pudo obtener company_id")
                return

            self.logger.info(f"Company ID: {company_id}")

            # Crear app del servicio
            self.app = ServiceApp(
                self.postgresql_config,
                self.mysql_config,
                company_id
            )

            # Crear módulo de sincronización
            self.sync_module = SmartSyncComplete(
                self.app,
                self.postgresql_config,
                self.mysql_config,
                company_id
            )

            # Inicializar tabla de hashes (primera vez)
            self.logger.info("Inicializando tabla sync_hashes...")
            if not self.sync_module.inicializar_tabla_hashes():
                self.logger.error("Error inicializando tabla sync_hashes")
                return

            # Ejecutar primera sincronización completa
            self.logger.info("Ejecutando primera sincronización completa...")
            self.app.log_message("=== PRIMERA SINCRONIZACIÓN ===", "info")
            self.sync_module.ejecutar_sync_completa()

            # Loop principal del servicio
            self.logger.info(f"Iniciando loop principal (intervalo: {self.sync_interval}s)...")
            self.main()

        except Exception as e:
            self.logger.error(f"Error en SvcDoRun: {str(e)}", exc_info=True)
            servicemanager.LogErrorMsg(f"Error: {str(e)}")

    def load_configuration(self):
        """
        Cargar configuración desde .env
        """
        try:
            load_dotenv()

            # Configuración PostgreSQL
            self.postgresql_config = {
                'host': os.getenv('DB_HOST'),
                'database': os.getenv('DB_DATABASE'),
                'user': os.getenv('DB_USER'),
                'password': os.getenv('DB_PASSWORD')
            }

            # Configuración MySQL
            self.mysql_config = {
                'host': os.getenv('DB_HOST_MYSQL'),
                'database': os.getenv('DB_PORT_DATABASE_MYSQL'),
                'user': os.getenv('DB_USER_MYSQL'),
                'password': os.getenv('DB_PASSWORD_MYSQL')
            }

            # Leer intervalo desde variable de entorno o usar default
            interval_env = os.getenv('SYNC_INTERVAL_SECONDS')
            if interval_env:
                try:
                    self.sync_interval = int(interval_env)
                except ValueError:
                    self.sync_interval = 3600

            self.logger.info(f"Configuración cargada. Intervalo: {self.sync_interval}s")

        except Exception as e:
            self.logger.error(f"Error cargando configuración: {str(e)}")
            raise

    def get_company_id(self) -> int:
        """
        Obtener company_id desde MySQL (tabla acceso)
        """
        try:
            conn = mysql.connector.connect(**self.mysql_config)
            cursor = conn.cursor()

            rif = os.getenv('RIF')
            email = os.getenv('EMAIL')

            if not rif or not email:
                self.logger.error("RIF y EMAIL deben estar definidos en .env")
                return None

            cursor.execute(
                "SELECT company_id FROM acceso WHERE codigo = %s AND LOWER(correo_electronico) = LOWER(%s)",
                (rif, email)
            )
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
                company_id = result[0]
                self.logger.info(f"Company ID detectado: {company_id}")
                return company_id
            else:
                self.logger.error(f"No se encontró company_id para RIF={rif}, EMAIL={email}")
                return None

        except Exception as e:
            self.logger.error(f"Error obteniendo company_id: {str(e)}")
            return None

    def main(self):
        """
        Loop principal del servicio
        """
        while self.is_running:
            try:
                self.logger.info("Iniciando ciclo de sincronización...")

                # Ejecutar sincronización
                if self.sync_module:
                    self.sync_module.sync_running = True
                    resultado = self.sync_module.ejecutar_sync_completa()

                    if resultado:
                        self.logger.info("✅ Sincronización completada exitosamente")
                        servicemanager.LogInfoMsg("Sincronización completada")
                    else:
                        self.logger.warning("⚠️ Sincronización completada con errores")
                        servicemanager.LogWarningMsg("Sincronización con errores")
                else:
                    self.logger.error("sync_module no está inicializado")

                # Esperar hasta la próxima sincronización O recibir señal de parada
                self.logger.info(f"Esperando {self.sync_interval} segundos hasta próxima sincronización...")

                wait_result = win32event.WaitForSingleObject(
                    self.hWaitStop,
                    self.sync_interval * 1000  # Convertir a milisegundos
                )

                # Si se recibió señal de parada, salir del loop
                if wait_result == win32event.WAIT_OBJECT_0:
                    self.logger.info("Señal de parada recibida. Saliendo del loop.")
                    break

            except Exception as e:
                self.logger.error(f"Error en ciclo de sincronización: {str(e)}", exc_info=True)

                # Esperar antes de reintentar
                wait_result = win32event.WaitForSingleObject(
                    self.hWaitStop,
                    60000  # Esperar 1 minuto antes de reintentar
                )

                if wait_result == win32event.WAIT_OBJECT_0:
                    break

        self.logger.info("Loop principal finalizado")


# ====================================================================
# MANEJO DE LÍNEA DE COMANDOS
# ====================================================================

def ctrl_handler(ctrl_type):
    """
    Manejar señales de control (Ctrl+C, etc.)
    """
    if ctrl_type == 0:  # CTRL_C_EVENT
        logging.info("Recibida señal Ctrl+C. Saliendo...")
        return True
    return False


if __name__ == '__main__':
    # Configurar manejador de Ctrl+C
    if sys.version_info[0] < 3:
        import win32api
        win32api.SetConsoleCtrlHandler(ctrl_handler, True)

    try:
        win32serviceutil.HandleCommandLine(PostgreSQLMySQLSyncService)
    except Exception as e:
        logging.error(f"Error: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        sys.exit(1)
