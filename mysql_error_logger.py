#!/usr/bin/env python3
"""
Módulo para logging de errores de MySQL en archivos separados
Los errores se guardan en logs/mysql_errors/ y NO se muestran al usuario
"""

import os
import datetime
from pathlib import Path


class MySQLErrorLogger:
    """Logger para errores de MySQL"""

    def __init__(self, base_dir=None):
        """
        Inicializa el logger de errores de MySQL

        Args:
            base_dir: Directorio base. Si es None, usa el directorio del script
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.absolute()
        else:
            base_dir = Path(base_dir)

        # Crear directorio para logs de errores de MySQL
        self.error_log_dir = base_dir / 'logs' / 'mysql_errors'
        self.error_log_dir.mkdir(parents=True, exist_ok=True)

        # Archivo de log actual (con timestamp)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_log_file = self.error_log_dir / f'mysql_errors_{timestamp}.log'

        # Contador de errores en esta sesión
        self.error_count = 0

    def log_error(self, operation, error, query=None, params=None, context=None):
        """
        Guarda un error de MySQL en el archivo de log

        Args:
            operation: Operación que se estaba ejecutando (ej: 'INSERT products')
            error: Exception o string con el error
            query: Query SQL que falló (opcional)
            params: Parámetros del query (opcional)
            context: Información adicional del contexto (opcional)
        """
        self.error_count += 1

        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"ERROR #{self.error_count} - {timestamp}\n")
                f.write("=" * 80 + "\n\n")

                # Operación
                f.write(f"Operación: {operation}\n\n")

                # Contexto
                if context:
                    f.write(f"Contexto: {context}\n\n")

                # Error
                if isinstance(error, Exception):
                    f.write(f"Tipo de Error: {type(error).__name__}\n")
                    f.write(f"Mensaje: {str(error)}\n\n")
                else:
                    f.write(f"Error: {error}\n\n")

                # Query SQL
                if query:
                    f.write("Query SQL:\n")
                    f.write("-" * 40 + "\n")
                    # Formatear query para que sea más legible
                    formatted_query = query.strip()
                    f.write(formatted_query + "\n")
                    f.write("-" * 40 + "\n\n")

                # Parámetros
                if params:
                    f.write(f"Parámetros: {params}\n\n")

                # Stack trace (si es una excepción)
                if isinstance(error, Exception):
                    import traceback
                    f.write("Stack Trace:\n")
                    f.write("-" * 40 + "\n")
                    traceback.print_exc(file=f)
                    f.write("-" * 40 + "\n\n")

                f.write("\n")

            # Mantener solo los últimos 10 archivos de log
            self._cleanup_old_logs()

        except Exception as e:
            # Si falla el logging, al menos imprimir en stderr
            import sys
            print(f"Error logging MySQL error: {e}", file=sys.stderr)

    def log_query_error(self, operation, query, params, error, context=None):
        """
        Método conveniente para loggear errores de queries

        Args:
            operation: Operación que se estaba ejecutando
            query: Query SQL que falló
            params: Parámetros del query
            error: Exception o string con el error
            context: Información adicional
        """
        self.log_error(
            operation=operation,
            error=error,
            query=query,
            params=params,
            context=context
        )

    def log_connection_error(self, error, host=None, port=None, database=None):
        """
        Loggea errores de conexión a MySQL

        Args:
            error: Exception con el error de conexión
            host: Host al que se intentó conectar
            port: Puerto
            database: Base de datos
        """
        context = f"Conexión a MySQL: {host}:{port}/{database}" if host else "Conexión a MySQL"
        self.log_error(
            operation="CONEXIÓN",
            error=error,
            context=context
        )

    def log_batch_error(self, operation, batch_data, error, failed_index=None):
        """
        Loggea errores en operaciones batch (executemany)

        Args:
            operation: Operación batch (ej: 'BATCH INSERT products')
            batch_data: Datos del batch (primeros 10 elementos)
            error: Exception con el error
            failed_index: Índice del elemento que falló (si se conoce)
        """
        context = f"Batch size: {len(batch_data)} elementos"
        if failed_index is not None:
            context += f"\nElemento que falló: índice {failed_index}"

        # Mostrar primeros elementos del batch (no todos para no saturar)
        batch_preview = []
        for i, item in enumerate(batch_data[:10]):
            batch_preview.append(f"  [{i}]: {str(item)[:100]}...")
        if len(batch_data) > 10:
            batch_preview.append(f"  ... y {len(batch_data) - 10} elementos más")

        self.log_error(
            operation=operation,
            error=error,
            context=context + "\n\nBatch data (primeros 10 elementos):\n" + "\n".join(batch_preview)
        )

    def _cleanup_old_logs(self):
        """Mantiene solo los últimos 10 archivos de log"""
        try:
            log_files = sorted(self.error_log_dir.glob('mysql_errors_*.log'),
                             key=lambda p: p.stat().st_mtime,
                             reverse=True)

            # Mantener solo los 10 más recientes
            for old_log in log_files[10:]:
                old_log.unlink()
                # print(f"Eliminado log antiguo: {old_log.name}")  # Debug

        except Exception as e:
            # Si falla la limpieza, no es crítico
            pass

    def get_error_count(self):
        """Retorna el número de errores loggeados en esta sesión"""
        return self.error_count

    def get_log_file_path(self):
        """Retorna la ruta del archivo de log actual"""
        return str(self.current_log_file)

    def has_errors(self):
        """Retorna True si hay errores en esta sesión"""
        return self.error_count > 0

    def get_summary(self):
        """Retorna un resumen de los errores de esta sesión"""
        if not self.has_errors():
            return "✅ No hay errores de MySQL en esta sesión"

        return (
            f"⚠️ Se detectaron {self.error_count} error(es) de MySQL\n"
            f"📁 Log guardado en: {self.current_log_file}"
        )


# Instancia global del logger
_global_logger = None


def get_mysql_error_logger(base_dir=None):
    """
    Retorna la instancia global del logger de errores de MySQL

    Args:
        base_dir: Directorio base (opcional)

    Returns:
        Instancia de MySQLErrorLogger
    """
    global _global_logger

    if _global_logger is None:
        _global_logger = MySQLErrorLogger(base_dir)

    return _global_logger


def log_mysql_error(operation, error, query=None, params=None, context=None):
    """
    Función conveniente para loggear errores de MySQL

    Args:
        operation: Operación que se estaba ejecutando
        error: Exception o string con el error
        query: Query SQL que falló (opcional)
        params: Parámetros del query (opcional)
        context: Información adicional (opcional)
    """
    logger = get_mysql_error_logger()
    logger.log_error(operation, error, query, params, context)


def log_mysql_connection_error(error, host=None, port=None, database=None):
    """Función conveniente para loggear errores de conexión"""
    logger = get_mysql_error_logger()
    logger.log_connection_error(error, host, port, database)


def log_mysql_batch_error(operation, batch_data, error, failed_index=None):
    """Función conveniente para loggear errores de batch operations"""
    logger = get_mysql_error_logger()
    logger.log_batch_error(operation, batch_data, error, failed_index)
