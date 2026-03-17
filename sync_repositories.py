"""
Módulo de repositorios para sincronización

Implementa el patrón Repository para separar la lógica de acceso a datos
de la lógica de negocio.
"""

import hashlib
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sync_queries import SyncQueries


class BaseRepository:
    """Clase base para todos los repositorios"""

    def __init__(self, pg_cursor, mysql_cursor, pg_conn, mysql_conn, company_id: str):
        self.pg_cursor = pg_cursor
        self.mysql_cursor = mysql_cursor
        self.pg_conn = pg_conn
        self.mysql_conn = mysql_conn
        self.company_id = company_id
        self.stats = {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0}

    def _generate_hash(self, data: dict) -> str:
        """Genera hash MD5 de un diccionario de datos"""
        # Ordenar claves para consistencia
        sorted_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(sorted_data.encode()).hexdigest()

    def _log(self, message: str, log_type: str = "info", log_callback=None):
        """Envía log al callback si existe"""
        if log_callback:
            log_callback(message, log_type)


class ProductRepository(BaseRepository):
    """Repositorio para productos"""

    def get_from_postgresql(self, codes: Optional[List[str]] = None) -> List[Tuple]:
        """Obtiene productos de PostgreSQL"""
        if codes:
            placeholders = ','.join(['%s'] * len(codes))
            query = SyncQueries.PG_PRODUCTS_BY_CODES % placeholders
            self.pg_cursor.execute(query, codes)
        else:
            self.pg_cursor.execute(SyncQueries.PG_PRODUCTS_ALL)
        return self.pg_cursor.fetchall()

    def get_from_mysql(self, code: str) -> Optional[Tuple]:
        """Obtiene un producto de MySQL por código"""
        self.mysql_cursor.execute(
            SyncQueries.MYSQL_PRODUCTS_GET_BY_CODE,
            (code, self.company_id)
        )
        return self.mysql_cursor.fetchone()

    def get_all_from_mysql(self) -> List[Tuple]:
        """Obtiene todos los productos de MySQL"""
        self.mysql_cursor.execute(
            SyncQueries.MYSQL_PRODUCTS_ALL_BY_COMPANY,
            (self.company_id,)
        )
        return self.mysql_cursor.fetchall()

    def insert_in_mysql(self, product_data: dict, log_callback=None) -> bool:
        """Inserta un producto en MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_PRODUCTS_INSERT,
                (
                    self.company_id,
                    product_data['code'],
                    product_data['name'],
                    product_data['description'],
                    product_data['price'],
                    product_data['cost'],
                    product_data['stock'],
                    product_data['status'],
                    product_data['category_id'],
                    product_data['higher_price'],
                    product_data.get('sale_tax', 16)  # Default 16%
                )
            )
            self.stats['nuevos'] += 1
            return True
        except Exception as e:
            self._log(f"Error insertando product {product_data.get('code')}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def update_in_mysql(self, product_id: int, product_data: dict, log_callback=None) -> bool:
        """Actualiza un producto en MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_PRODUCTS_UPDATE,
                (
                    product_data['name'],
                    product_data['description'],
                    product_data['price'],
                    product_data['cost'],
                    product_data['stock'],
                    product_data['status'],
                    product_data['category_id'],
                    product_data['higher_price'],
                    product_id,
                    self.company_id
                )
            )
            self.stats['modificados'] += 1
            return True
        except Exception as e:
            self._log(f"Error actualizando product {product_data.get('code')}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def update_status_in_mysql(self, code: str, status: str, log_callback=None) -> bool:
        """Actualiza el estado de un producto en MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_PRODUCTS_UPDATE_STATUS,
                (status, self.company_id, code)
            )
            self.stats['modificados'] += 1
            return True
        except Exception as e:
            self._log(f"Error actualizando status de product {code}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def delete_from_mysql(self, product_id: int, code: str, log_callback=None) -> bool:
        """Elimina un producto de MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_PRODUCTS_DELETE,
                (product_id, self.company_id)
            )
            self.stats['eliminados'] += 1
            self._log(f"Producto {code} eliminado de MySQL", "info", log_callback)
            return True
        except Exception as e:
            self._log(f"Error eliminando product {code}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False


class CustomerRepository(BaseRepository):
    """Repositorio para clientes"""

    def get_from_postgresql(self) -> List[Tuple]:
        """Obtiene clientes de PostgreSQL"""
        self.pg_cursor.execute(SyncQueries.PG_CUSTOMERS_ALL)
        return self.pg_cursor.fetchall()

    def get_from_mysql(self, document_number: str) -> Optional[Tuple]:
        """Obtiene un cliente de MySQL por documento"""
        self.mysql_cursor.execute(
            SyncQueries.MYSQL_CUSTOMERS_GET_BY_DOCUMENT,
            (self.company_id, document_number)
        )
        return self.mysql_cursor.fetchone()

    def save_in_mysql(self, customer_data: dict, log_callback=None) -> bool:
        """Guarda o actualiza un cliente en MySQL (upsert)"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_CUSTOMERS_INSERT,
                (
                    self.company_id,
                    customer_data['document_number'],
                    customer_data['name'],
                    customer_data['email'],
                    customer_data['address'],
                    customer_data['phone'],
                    customer_data['contact']
                )
            )
            return True
        except Exception as e:
            self._log(f"Error guardando customer {customer_data.get('document_number')}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def delete_from_mysql(self, customer_id: int, email: str, log_callback=None) -> bool:
        """Elimina un cliente de MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_CUSTOMERS_DELETE,
                (customer_id, self.company_id)
            )
            self.stats['eliminados'] += 1
            self._log(f"Customer {email} eliminado de MySQL", "info", log_callback)
            return True
        except Exception as e:
            self._log(f"Error eliminando customer {email}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False


class SellerRepository(BaseRepository):
    """Repositorio para vendedores"""

    def get_from_postgresql(self) -> List[Tuple]:
        """Obtiene vendedores de PostgreSQL"""
        self.pg_cursor.execute(SyncQueries.PG_SELLERS_ALL)
        return self.pg_cursor.fetchall()

    def get_from_mysql(self, email: str) -> Optional[Tuple]:
        """Obtiene un vendedor de MySQL por email"""
        self.mysql_cursor.execute(
            SyncQueries.MYSQL_SELLERS_GET_BY_EMAIL,
            (self.company_id, email)
        )
        return self.mysql_cursor.fetchone()

    def save_in_mysql(self, seller_data: dict, log_callback=None) -> bool:
        """Guarda o actualiza un vendedor en MySQL (upsert)"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_SELLERS_INSERT,
                (
                    self.company_id,
                    seller_data['email'],
                    seller_data['name'],
                    seller_data['phone'],
                    seller_data['status']
                )
            )
            return True
        except Exception as e:
            self._log(f"Error guardando seller {seller_data.get('email')}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def update_in_mysql(self, email: str, seller_data: dict, log_callback=None) -> bool:
        """Actualiza un vendedor en MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_SELLERS_UPDATE,
                (
                    seller_data['name'],
                    seller_data['phone'],
                    seller_data['status'],
                    self.company_id,
                    email
                )
            )
            self.stats['modificados'] += 1
            return True
        except Exception as e:
            self._log(f"Error actualizando seller {email}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def delete_from_mysql(self, seller_id: int, email: str, log_callback=None) -> bool:
        """Elimina un vendedor de MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_SELLERS_DELETE,
                (seller_id, self.company_id)
            )
            self.stats['eliminados'] += 1
            self._log(f"Seller {email} eliminado de MySQL", "info", log_callback)
            return True
        except Exception as e:
            self._log(f"Error eliminando seller {email}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False


class CategoryRepository(BaseRepository):
    """Repositorio para categorías (departments)"""

    def get_from_postgresql(self) -> List[Tuple]:
        """Obtiene departamentos de PostgreSQL"""
        self.pg_cursor.execute(SyncQueries.PG_DEPARTMENTS_ALL)
        return self.pg_cursor.fetchall()

    def get_from_mysql(self, name: str) -> Optional[Tuple]:
        """Obtiene una categoría de MySQL por nombre"""
        self.mysql_cursor.execute(
            SyncQueries.MYSQL_CATEGORIES_GET_BY_NAME,
            (self.company_id, name)
        )
        return self.mysql_cursor.fetchone()

    def save_in_mysql(self, category_data: dict, log_callback=None) -> bool:
        """Guarda o actualiza una categoría en MySQL (upsert)"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_CATEGORIES_INSERT,
                (
                    self.company_id,
                    category_data['name'],
                    category_data['description'],
                    category_data.get('status', 'active')
                )
            )
            return True
        except Exception as e:
            self._log(f"Error guardando category {category_data.get('name')}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def update_in_mysql(self, name: str, category_data: dict, log_callback=None) -> bool:
        """Actualiza una categoría en MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_CATEGORIES_UPDATE,
                (
                    category_data['description'],
                    self.company_id,
                    name
                )
            )
            self.stats['modificados'] += 1
            return True
        except Exception as e:
            self._log(f"Error actualizando category {name}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False

    def delete_from_mysql(self, category_id: int, name: str, log_callback=None) -> bool:
        """Elimina una categoría de MySQL"""
        try:
            self.mysql_cursor.execute(
                SyncQueries.MYSQL_CATEGORIES_DELETE,
                (category_id, self.company_id)
            )
            self.stats['eliminados'] += 1
            self._log(f"Category {name} eliminada de MySQL", "info", log_callback)
            return True
        except Exception as e:
            self._log(f"Error eliminando category {name}: {e}", "error", log_callback)
            self.stats['errores'] += 1
            return False


class SyncHashRepository(BaseRepository):
    """Repositorio para tabla sync_hashes"""

    def initialize_table(self, log_callback=None) -> bool:
        """Crea la tabla sync_hashes si no existe"""
        try:
            self.pg_cursor.execute(SyncQueries.SYNC_HASHES_CREATE_TABLE)
            self.pg_conn.commit()
            self._log("Tabla sync_hashes verificada/creada", "info", log_callback)
            return True
        except Exception as e:
            self._log(f"Error creando sync_hashes: {e}", "error", log_callback)
            self.pg_conn.rollback()
            return False

    def get(self, table_name: str, record_key: str) -> Optional[Tuple]:
        """Obtiene un registro de sync_hashes"""
        self.pg_cursor.execute(
            SyncQueries.SYNC_HASHES_GET,
            (table_name, record_key, self.company_id)
        )
        return self.pg_cursor.fetchone()

    def save(self, table_name: str, record_key: str, record_hash: str, record_data: dict) -> bool:
        """Guarda o actualiza un registro en sync_hashes"""
        try:
            # Intentar actualizar primero
            self.pg_cursor.execute(
                SyncQueries.SYNC_HASHES_UPDATE,
                (record_hash, json.dumps(record_data), table_name, record_key, self.company_id)
            )

            if self.pg_cursor.rowcount == 0:
                # No existía, insertar
                self.pg_cursor.execute(
                    SyncQueries.SYNC_HASHES_INSERT,
                    (table_name, record_key, record_hash, json.dumps(record_data), self.company_id)
                )

            self.pg_conn.commit()
            return True
        except Exception as e:
            self.pg_conn.rollback()
            return False

    def get_all(self, table_name: str) -> List[Tuple]:
        """Obtiene todos los registros de una tabla"""
        self.pg_cursor.execute(
            SyncQueries.SYNC_HASHES_GET_ALL_BY_TABLE,
            (table_name, self.company_id)
        )
        return self.pg_cursor.fetchall()

    def get_deleted(self, table_name: str) -> List[Tuple]:
        """Obtiene registros marcados como eliminados"""
        self.pg_cursor.execute(
            SyncQueries.SYNC_HASHES_GET_DELETED,
            (table_name,)
        )
        return self.pg_cursor.fetchall()

    def delete(self, table_name: str, record_key: str) -> bool:
        """Elimina un registro de sync_hashes"""
        try:
            self.pg_cursor.execute(
                SyncQueries.SYNC_HASHES_DELETE_BY_KEY,
                (table_name, record_key, self.company_id)
            )
            self.pg_conn.commit()
            return True
        except Exception as e:
            self.pg_conn.rollback()
            return False

    def clear_deleted_marks(self, table_name: str) -> int:
        """Limpia marcas de eliminación de una tabla"""
        try:
            self.pg_cursor.execute(
                SyncQueries.SYNC_HASHES_DELETE_DELETED_MARKS,
                (table_name,)
            )
            count = self.pg_cursor.rowcount
            self.pg_conn.commit()
            return count
        except Exception as e:
            self.pg_conn.rollback()
            return 0

    def clear_all(self) -> bool:
        """Elimina todos los registros de sync_hashes de la compañía"""
        try:
            self.pg_cursor.execute(
                SyncQueries.SYNC_HASHES_DELETE_ALL,
                (self.company_id,)
            )
            self.pg_conn.commit()
            return True
        except Exception as e:
            self.pg_conn.rollback()
            return False

    def count(self, table_name: str) -> int:
        """Cuenta registros de una tabla"""
        self.pg_cursor.execute(
            SyncQueries.SYNC_HASHES_COUNT_BY_TABLE,
            (table_name, self.company_id)
        )
        return self.pg_cursor.fetchone()[0]
