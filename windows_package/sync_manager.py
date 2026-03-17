"""
Gestor de Sincronización PostgreSQL ↔ MySQL

Este módulo orquesta la sincronización bidireccional entre PostgreSQL y MySQL.
Implementa una arquitectura escalable basada en repositorios.
"""

import psycopg2
import pymysql
import requests
from typing import Dict, List, Optional, Callable
from datetime import datetime
from sync_repositories import (
    ProductRepository,
    CustomerRepository,
    SellerRepository,
    CategoryRepository,
    SyncHashRepository
)


class SyncManager:
    """
    Gestor principal de sincronización

    Coordina la sincronización bidireccional entre PostgreSQL y MySQL
    utilizando repositorios para cada entidad.
    """

    def __init__(
        self,
        postgresql_config: dict,
        mysql_config: dict,
        company_rif: str,
        company_email: str,
        company_name: str = '',
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Inicializar gestor de sincronización

        Args:
            postgresql_config: Configuración de PostgreSQL
            mysql_config: Configuración de MySQL
            company_rif: RIF de la empresa
            company_email: Email de la empresa
            company_name: Nombre de la empresa (opcional)
            log_callback: Función callback para logs (message, type)
        """
        self.postgresql_config = postgresql_config
        self.mysql_config = mysql_config
        self.company_rif = company_rif
        self.company_email = company_email
        self.company_name = company_name
        self.log_callback = log_callback

        # Conexiones
        self.pg_conn = None
        self.pg_cursor = None
        self.mysql_conn = None
        self.mysql_cursor = None

        # Company ID (se obtiene de MySQL)
        self.company_id = None

        # Repositorios
        self.product_repo = None
        self.customer_repo = None
        self.seller_repo = None
        self.category_repo = None
        self.sync_hash_repo = None

        # Estadísticas
        self.stats = {
            'products': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'customers': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'sellers': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'categories': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0},
            'quotes': {'nuevos': 0, 'modificados': 0, 'eliminados': 0, 'errores': 0, 'estados_actualizados': 0}
        }

        # Tipo de cambio VES a USD
        self.tipo_cambio_ves_usd = None

        # Flag de control
        self.sync_running = True

    def connect(self) -> bool:
        """Establece conexiones con ambas bases de datos"""
        try:
            # Conectar PostgreSQL
            self.pg_conn = psycopg2.connect(**self.postgresql_config)
            self.pg_cursor = self.pg_conn.cursor()
            self._log("✅ Conectado a PostgreSQL", "success")

            # Conectar MySQL
            self.mysql_conn = pymysql.connect(**self.mysql_config)
            self.mysql_cursor = self.mysql_conn.cursor()
            self._log("✅ Conectado a MySQL", "success")

            return True
        except Exception as e:
            self._log(f"❌ Error conectando: {e}", "error")
            return False

    def initialize(self) -> bool:
        """Inicializa el gestor de sincronización"""
        try:
            # Obtener company_id
            if not self._get_company_id():
                return False

            # Inicializar repositorios
            self.sync_hash_repo = SyncHashRepository(
                self.pg_cursor,
                self.mysql_cursor,
                self.pg_conn,
                self.mysql_conn,
                self.company_id
            )

            # Crear tabla sync_hashes si no existe
            if not self.sync_hash_repo.initialize_table(self.log_callback):
                return False

            # Inicializar repositorios de entidades
            self.product_repo = ProductRepository(
                self.pg_cursor,
                self.mysql_cursor,
                self.pg_conn,
                self.mysql_conn,
                self.company_id
            )

            self.customer_repo = CustomerRepository(
                self.pg_cursor,
                self.mysql_cursor,
                self.pg_conn,
                self.mysql_conn,
                self.company_id
            )

            self.seller_repo = SellerRepository(
                self.pg_cursor,
                self.mysql_cursor,
                self.pg_conn,
                self.mysql_conn,
                self.company_id
            )

            self.category_repo = CategoryRepository(
                self.pg_cursor,
                self.mysql_cursor,
                self.pg_conn,
                self.mysql_conn,
                self.company_id
            )

            return True
        except Exception as e:
            self._log(f"❌ Error inicializando: {e}", "error")
            return False

    def sync_all(self) -> bool:
        """Ejecuta sincronización completa de todas las entidades"""
        try:
            inicio = datetime.now()
            self._log("", "info")
            self._log("╔════════════════════════════════════════════════════════════════╗", "info")
            self._log("║          SINCRONIZACIÓN INTELIGENTE CON TABLA DE HASHES          ║", "info")
            self.__log("╚════════════════════════════════════════════════════════════════╝", "info")
            self._log("", "info")

            # 1. Categories (primero, porque products las referencian)
            self._log("📦 SINCRONIZANDO CATEGORIES...", "info")
            self.sync_categories()

            # 2. Products PostgreSQL → MySQL
            self._log("", "info")
            self._log("📦 SINCRONIZANDO PRODUCTS...", "info")
            self.sync_products()

            # 3. Customers
            self._log("", "info")
            self._log("👥 SINCRONIZANDO CUSTOMERS...", "info")
            self.sync_customers()

            # 4. Sellers
            self._log("", "info")
            self._log("👤 SINCRONIZANDO SELLERS...", "info")
            self.sync_sellers()

            # 5. Eliminar registros marcados
            self._log("", "info")
            self._log("🗑️ ELIMINANDO REGISTROS...", "info")
            self.sync_deleted_records()

            # Reporte final
            duracion = (datetime.now() - inicio).total_seconds()
            self._print_summary(duracion)

            # Commit cambios
            self.mysql_conn.commit()

            return True
        except Exception as e:
            self._log(f"❌ Error en sincronización: {e}", "error")
            self.mysql_conn.rollback()
            return False
        finally:
            self.close()

    def sync_categories(self):
        """Sincroniza categorías (departments → categories)"""
        try:
            # Obtener departments de PostgreSQL
            departments = self.category_repo.get_from_postgresql()

            if not departments:
                self._log("   ℹ️ No hay departments para sincronizar", "info")
                return

            self._log(f"   📋 Procesando {len(departments)} departments...", "info")

            for code, description in departments:
                if not self.sync_running:
                    break

                # Verificar si existe en MySQL
                existing = self.category_repo.get_from_mysql(code)

                if existing:
                    # Actualizar
                    self.category_repo.update_in_mysql(code, {
                        'description': description
                    }, self.log_callback)
                else:
                    # Insertar
                    self.category_repo.save_in_mysql({
                        'name': code,
                        'description': description,
                        'status': 'active'
                    }, self.log_callback)
                    self.stats['categories']['nuevos'] += 1

            self.mysql_conn.commit()
            self._log(
                f"✅ Categories: {self.stats['categories']['nuevos']} nuevos, "
                f"{self.stats['categories']['modificados']} modificados",
                "success"
            )
        except Exception as e:
            self._log(f"❌ Error sincronizando categories: {e}", "error")
            self.stats['categories']['errores'] += 1

    def sync_products(self):
        """Sincroniza productos PostgreSQL → MySQL"""
        try:
            # Obtener productos de PostgreSQL
            products = self.product_repo.get_from_postgresql()

            if not products:
                self._log("   ℹ️ No hay products para sincronizar", "info")
                return

            self._log(f"   📋 Procesando {len(products)} products...", "info")

            # Verificar si hay productos en VES para obtener tipo de cambio
            has_ves_products = any(p[6] == '01' for p in products)  # coin es índice 6

            if has_ves_products:
                self._log("   💰 Detectados productos en Bolívares, obteniendo tipo de cambio...", "info")
                self.tipo_cambio_ves_usd = self._get_exchange_rate()

            for product in products:
                if not self.sync_running:
                    break

                # Desempaquetar producto
                code = product[0]
                name = product[1]  # description
                short_name = product[2]
                category_code = product[3]
                stock = product[4]
                product_type = product[5]
                coin = product[6]
                description_coin = product[7]
                price = product[8]
                cost = product[9]
                higher_price = product[10]
                min_stock = product[11]
                status = product[12]

                # Convertir VES a USD si es necesario
                if coin == '01' and self.tipo_cambio_ves_usd:
                    price = round(price / self.tipo_cambio_ves_usd, 4) if price else 0
                    cost = round(cost / self.tipo_cambio_ves_usd, 4) if cost else 0
                    higher_price = round(higher_price / self.tipo_cambio_ves_usd, 4) if higher_price else 0

                # Verificar si la categoría existe en MySQL
                category_id = self._get_category_id(category_code)

                if not category_id:
                    self._log(f"   ⚠️ Product {code} omitido: categoría '{category_code}' no existe en MySQL", "warning")
                    continue

                # Verificar si existe en MySQL
                existing = self.product_repo.get_from_mysql(code)

                product_data = {
                    'code': code,
                    'name': short_name or name,
                    'description': name,
                    'price': price,
                    'cost': cost,
                    'stock': stock,
                    'status': status,
                    'category_id': category_id,
                    'higher_price': higher_price,
                    'sale_tax': 16  # Default 16% IVA
                }

                if existing:
                    # Actualizar
                    product_id = existing[0]
                    self.product_repo.update_in_mysql(product_id, product_data, self.log_callback)
                else:
                    # Insertar
                    self.product_repo.insert_in_mysql(product_data, self.log_callback)

            self.mysql_conn.commit()
            self._log(
                f"✅ Products: {self.stats['products']['nuevos']} nuevos, "
                f"{self.stats['products']['modificados']} modificados",
                "success"
            )
        except Exception as e:
            self._log(f"❌ Error sincronizando products: {e}", "error")
            self.stats['products']['errores'] += 1

    def sync_customers(self):
        """Sincroniza clientes PostgreSQL → MySQL"""
        try:
            customers = self.customer_repo.get_from_postgresql()

            if not customers:
                self._log("   ℹ️ No hay customers para sincronizar", "info")
                return

            self._log(f"   📋 Procesando {len(customers)} customers...", "info")

            for customer in customers:
                if not self.sync_running:
                    break

                code, description, address, client_id, email, phone, contact = customer

                # Asegurar email
                if not email or email.strip() == '':
                    email = f"customer_{code}@temp.local"

                customer_data = {
                    'document_number': code,
                    'name': description,
                    'email': email,
                    'address': address,
                    'phone': phone,
                    'contact': contact
                }

                self.customer_repo.save_in_mysql(customer_data, self.log_callback)

            self.mysql_conn.commit()
            self._log(
                f"✅ Customers: {self.stats['customers']['nuevos']} nuevos, "
                f"{self.stats['customers']['modificados']} modificados",
                "success"
            )
        except Exception as e:
            self._log(f"❌ Error sincronizando customers: {e}", "error")
            self.stats['customers']['errores'] += 1

    def sync_sellers(self):
        """Sincroniza vendedores PostgreSQL → MySQL"""
        try:
            sellers = self.seller_repo.get_from_postgresql()

            if not sellers:
                self._log("   ℹ️ No hay sellers para sincronizar", "info")
                return

            self._log(f"   📋 Procesando {len(sellers)} sellers...", "info")

            for seller in sellers:
                if not self.sync_running:
                    break

                email, name, phone, status = seller

                seller_data = {
                    'email': email,
                    'name': name,
                    'phone': phone,
                    'status': status
                }

                self.seller_repo.save_in_mysql(seller_data, self.log_callback)

            self.mysql_conn.commit()
            self._log(
                f"✅ Sellers: {self.stats['sellers']['nuevos']} nuevos, "
                f"{self.stats['sellers']['modificados']} actualizados",
                "success"
            )
        except Exception as e:
            self._log(f"❌ Error sincronizando sellers: {e}", "error")
            self.stats['sellers']['errores'] += 1

    def sync_deleted_records(self):
        """Elimina registros marcados como eliminados en sync_hashes"""
        try:
            # Products
            deleted_products = self.sync_hash_repo.get_deleted('products')
            if deleted_products:
                self._log(f"   📋 {len(deleted_products)} productos eliminados en PostgreSQL", "info")

                for (product_code,) in deleted_products:
                    existing = self.product_repo.get_from_mysql(product_code)
                    if existing:
                        product_id = existing[0]
                        self.product_repo.delete_from_mysql(product_id, product_code, self.log_callback)

                # Limpiar marcas
                count = self.sync_hash_repo.clear_deleted_marks('products')
                self._log(f"   ✅ {count} registros limpiados de sync_hashes", "info")

            # Categories
            deleted_categories = self.sync_hash_repo.get_deleted('department')
            if deleted_categories:
                self._log(f"   📋 {len(deleted_categories)} categorías eliminadas en PostgreSQL", "info")

                for (category_code,) in deleted_categories:
                    existing = self.category_repo.get_from_mysql(category_code)
                    if existing:
                        category_id = existing[0]
                        self.category_repo.delete_from_mysql(category_id, category_code, self.log_callback)

                count = self.sync_hash_repo.clear_deleted_marks('department')
                self._log(f"   ✅ {count} registros limpiados de sync_hashes", "info")

        except Exception as e:
            self._log(f"❌ Error sincronizando registros eliminados: {e}", "error")

    def _get_company_id(self) -> bool:
        """Obtiene el company_id desde MySQL"""
        try:
            # Buscar por RIF y email en tabla acceso
            self.mysql_cursor.execute(
                "SELECT company_id FROM acceso WHERE id_fiscal = %s AND correo_electronico = %s LIMIT 1",
                (self.company_rif, self.company_email)
            )
            result = self.mysql_cursor.fetchone()

            if result:
                self.company_id = result[0]
                self._log(f"✅ Company ID obtenido: {self.company_id}", "success")
                return True
            else:
                self._log(f"❌ No se encontró compañía con RIF {self.company_rif} y email {self.company_email}", "error")
                return False
        except Exception as e:
            self._log(f"❌ Error obteniendo company_id: {e}", "error")
            return False

    def _get_category_id(self, category_code: str) -> Optional[int]:
        """Obtiene el ID de una categoría en MySQL"""
        try:
            self.mysql_cursor.execute(
                "SELECT id FROM categories WHERE company_id = %s AND name = %s",
                (self.company_id, category_code)
            )
            result = self.mysql_cursor.fetchone()
            return result[0] if result else None
        except Exception:
            return None

    def _get_exchange_rate(self) -> Optional[float]:
        """Obtiene tipo de cambio VES a USD desde API externa"""
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                rate = float(data['rates']['VES'])
                self._log(f"   ✅ Tipo de cambio: {rate:.2f} VES/USD", "success")
                return rate
        except Exception as e:
            self._log(f"   ⚠️ Error obteniendo tipo de cambio: {e}", "warning")
            return 417.36  # Default

    def _print_summary(self, duration: float):
        """Imprime resumen de sincronización"""
        self._log("", "info")
        self._log("╔════════════════════════════════════════════════════════════════╗", "info")
        self._log("║                    RESUMEN DE SINCRONIZACIÓN                    ║", "info")
        self._log("╚════════════════════════════════════════════════════════════════╝", "info")
        self._log(
            f"Products:   {self.stats['products']['nuevos']} nuevos, "
            f"{self.stats['products']['modificados']} modificados, "
            f"{self.stats['products']['eliminados']} eliminados",
            "success"
        )
        self._log(
            f"Customers:  {self.stats['customers']['nuevos']} nuevos, "
            f"{self.stats['customers']['modificados']} modificados, "
            f"{self.stats['customers']['eliminados']} eliminados",
            "success"
        )
        self._log(
            f"Categories: {self.stats['categories']['nuevos']} nuevos, "
            f"{self.stats['categories']['modificados']} modificados",
            "success"
        )
        self._log(
            f"Sellers:    {self.stats['sellers']['nuevos']} nuevos, "
            f"{self.stats['sellers']['modificados']} actualizados, "
            f"{self.stats['sellers']['eliminados']} eliminados",
            "success"
        )
        self._log(f"Duración:   {duration:.2f} segundos", "info")
        self._log("", "info")

        if sum(s['errores'] for s in self.stats.values()) == 0:
            self._log("✅ SINCRONIZACIÓN COMPLETADA CON ÉXITO", "success")
        else:
            self._log("⚠️ SINCRONIZACIÓN COMPLETADA CON ERRORES", "warning")

    def _log(self, message: str, log_type: str = "info"):
        """Envía mensaje al callback de log"""
        if self.log_callback:
            self.log_callback(message, log_type)

    def close(self):
        """Cierra todas las conexiones"""
        try:
            if self.pg_cursor:
                self.pg_cursor.close()
            if self.pg_conn:
                self.pg_conn.close()
            if self.mysql_cursor:
                self.mysql_cursor.close()
            if self.mysql_conn:
                self.mysql_conn.close()
        except Exception:
            pass
