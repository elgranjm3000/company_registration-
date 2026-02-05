#!/usr/bin/env python3
"""
MÓDULO DE SINCRONIZACIÓN DE SELLERS
====================================
Sincroniza vendedores desde PostgreSQL a MySQL usando sistema de hashes

Autor: Sistema de Sincronización
Versión: 2.0 (con sync_hashes)
"""

import pymysql
import psycopg2
import hashlib
from typing import Dict, Any, Tuple


def safe_float(value):
    """Convertir valor a float de forma segura"""
    try:
        return float(value) if value is not None else 0.0
    except:
        return 0.0


class SmartSellersSyncModule:
    """Módulo de sincronización inteligente de sellers con sync_hashes"""

    def __init__(self, app):
        """
        Inicializar módulo de sellers

        Args:
            app: Instancia de SmartSyncComplete o similar con método log_message
        """
        self.app = app
        self.pg_conn = None
        self.pg_cursor = None
        self.mysql_conn = None
        self.mysql_cursor = None

        # Obtener company_id del app
        self.company_id = getattr(app, 'company_id', 27)

    def log(self, mensaje: str, nivel: str = "info"):
        """Enviar log al app"""
        if hasattr(self.app, 'log_message'):
            self.app.log_message(mensaje, nivel)

    def conectar_postgresql(self, postgresql_config: Dict[str, Any]) -> bool:
        """Conectar a PostgreSQL"""
        try:
            self.pg_conn = psycopg2.connect(**postgresql_config)
            self.pg_cursor = self.pg_conn.cursor()
            self.log("✅ Conectado a PostgreSQL (sellers)", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error conectando PostgreSQL: {e}", "error")
            return False

    def conectar_mysql(self, mysql_config: Dict[str, Any]) -> bool:
        """Conectar a MySQL"""
        try:
            self.mysql_conn = pymysql.connect(**mysql_config)
            self.mysql_cursor = self.mysql_cursor.cursor()
            self.log("✅ Conectado a MySQL (sellers)", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error conectando MySQL: {e}", "error")
            return False

    def _generar_hash_seller(self, seller: tuple) -> str:
        """Generar hash MD5 para un vendedor"""
        try:
            campos = (
                str(seller[0]) if seller[0] else '',  # seller_code
                str(seller[1]) if seller[1] else '',  # description
                str(seller[2]) if seller[2] else '',  # status
                str(safe_float(seller[3])),           # percent_sales
                str(safe_float(seller[4])),           # percent_receivable
                str(seller[5]) if seller[5] else '',  # inkeeper
                str(seller[6]) if seller[6] else '',  # user_code
                str(safe_float(seller[7])),           # percent_gerencial_debit_note
                str(safe_float(seller[8])),           # percent_gerencial_credit_note
                str(safe_float(seller[9])),           # percent_returned_check
                str(seller[10]) if seller[10] else '', # email
                str(seller[11]) if seller[11] else ''  # password
            )
            datos = "|".join(campos)
            return hashlib.md5(datos.encode('utf-8')).hexdigest()
        except Exception as e:
            self.log(f"Error generando hash de seller: {str(e)}", "error")
            return hashlib.md5(str(seller[0]).encode()).hexdigest()

    def _cargar_hashes_existentes(self) -> Dict[str, str]:
        """Cargar hashes existentes desde sync_hashes"""
        try:
            self.pg_cursor.execute("""
                SELECT record_key, record_hash
                FROM sync_hashes
                WHERE table_name = 'sellers'
                  AND company_id = %s
            """, (self.company_id,))

            hashes = {}
            for row in self.pg_cursor.fetchall():
                hashes[row[0]] = row[1]
            return hashes
        except Exception as e:
            self.log(f"Error cargando hashes existentes: {e}", "error")
            return {}

    def _guardar_hash(self, record_key: str, record_hash: str):
        """Guardar o actualizar hash en sync_hashes"""
        try:
            # Primero intentar UPDATE
            update_query = """
            UPDATE sync_hashes
            SET record_hash = %s,
                updated_at = NOW()
            WHERE table_name = %s
              AND record_key = %s
              AND company_id = %s
            """
            self.pg_cursor.execute(update_query,
                                 (record_hash, 'sellers', record_key, self.company_id))

            # Si el UPDATE no afectó ninguna fila, hacer INSERT
            if self.pg_cursor.rowcount == 0:
                insert_query = """
                INSERT INTO sync_hashes (table_name, record_key, record_hash, company_id, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                """
                self.pg_cursor.execute(insert_query,
                                     ('sellers', record_key, record_hash, self.company_id))
        except Exception as e:
            self.log(f"Error guardando hash: {e}", "error")

    def ejecutar_sync(self) -> dict:
        """
        Ejecutar sincronización de sellers usando sync_hashes

        Returns:
            Dict con estadísticas: {'nuevos': int, 'modificados': int, 'errores': int, 'exito': bool}
        """
        try:
            self.log("=== SINCRONIZANDO SELLERS (con sync_hashes) ===", "info")

            # Cargar hashes existentes
            hashes_existentes = self._cargar_hashes_existentes()
            self.log(f"📊 Hashes cargados: {len(hashes_existentes)} sellers previos", "info")

            # Obtener sellers desde PostgreSQL
            self.pg_cursor.execute("""
                SELECT
                    s.code as seller_code,
                    s.description,
                    s.status,
                    s.percent_sales,
                    s.percent_receivable,
                    s.inkeeper,
                    s.user_code,
                    s.percent_gerencial_debit_note,
                    s.percent_gerencial_credit_note,
                    s.percent_returned_check,
                    u.email,
                    u.user_password as password
                FROM sellers s
                LEFT JOIN users u ON s.user_code = u.code
                WHERE s.user_code IS NOT NULL
                  AND u.email IS NOT NULL
                  AND u.email != ''
                  AND u.email != '@'
                ORDER BY s.code
            """)

            sellers = self.pg_cursor.fetchall()

            if not sellers:
                self.log("ℹ️  No se encontraron sellers para sincronizar", "warning")
                return {'nuevos': 0, 'modificados': 0, 'errores': 0, 'exito': True}

            self.log(f"📊 Se encontraron {len(sellers)} sellers en PostgreSQL", "info")

            sellers_nuevos = 0
            sellers_modificados = 0
            sellers_omitidos = 0
            errores = 0

            for idx, seller in enumerate(sellers):
                try:
                    (seller_code, description, status, percent_sales,
                     percent_receivable, inkeeper, user_code,
                     percent_gerencial_debit_note, percent_gerencial_credit_note,
                     percent_returned_check, email, password) = seller

                    # Generar hash actual
                    hash_actual = self._generar_hash_seller(seller)
                    hash_anterior = hashes_existentes.get(seller_code, '')

                    # Si el hash no cambió, omitir
                    if hash_anterior and hash_actual == hash_anterior:
                        sellers_omitidos += 1
                        continue

                    # Buscar si ya existe en MySQL
                    self.mysql_cursor.execute(
                        "SELECT id FROM sellers WHERE code = %s LIMIT 1",
                        (seller_code,)
                    )
                    existente = self.mysql_cursor.fetchone()

                    if existente:
                        # Actualizar seller existente
                        seller_id = existente[0]
                        self.mysql_cursor.execute("""
                            UPDATE sellers SET
                                description = %s,
                                status = %s,
                                percent_sales = %s,
                                percent_receivable = %s,
                                inkeeper = %s,
                                user_code = %s,
                                percent_gerencial_debit_note = %s,
                                percent_gerencial_credit_note = %s,
                                percent_returned_check = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (
                            description, status, percent_sales, percent_receivable,
                            inkeeper, user_code, percent_gerencial_debit_note,
                            percent_gerencial_credit_note, percent_returned_check,
                            seller_id
                        ))
                        sellers_modificados += 1
                    else:
                        # Buscar user_id por email
                        self.mysql_cursor.execute(
                            "SELECT id FROM users WHERE email = %s AND role = 'seller' LIMIT 1",
                            (email,)
                        )
                        user_result = self.mysql_cursor.fetchone()

                        if not user_result:
                            # Usuario no existe, crearlo en users
                            self.log(f"   Creando usuario en MySQL.users para: {email}", "debug")

                            # Generar un nombre basado en la descripción del seller
                            nombre_parts = description.split(' ')
                            first_name = nombre_parts[0] if nombre_parts else seller_code
                            last_name = ' '.join(nombre_parts[1:]) if len(nombre_parts) > 1 else ''

                            self.mysql_cursor.execute("""
                                INSERT INTO users (
                                    company_id, email, password, role, first_name, last_name,
                                    status, created_at, updated_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s,
                                    'active', NOW(), NOW()
                                )
                            """, (
                                self.company_id, email, password, 'seller', first_name, last_name
                            ))

                            user_id = self.mysql_cursor.lastrowid
                            self.log(f"   ✅ Usuario creado con ID: {user_id}", "debug")
                        else:
                            user_id = user_result[0]

                        # Insertar nuevo seller
                        self.mysql_cursor.execute("""
                            INSERT INTO sellers (
                                user_id, company_id, code, description, status,
                                percent_sales, percent_receivable, inkeeper,
                                user_code, percent_gerencial_debit_note, percent_gerencial_credit_note,
                                percent_returned_check, created_at, updated_at
                            ) VALUES (
                                %s, %s, %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, NOW(), NOW()
                            )
                        """, (
                            user_id, self.company_id, seller_code, description, status,
                            percent_sales, percent_receivable, inkeeper,
                            user_code, percent_gerencial_debit_note, percent_gerencial_credit_note,
                            percent_returned_check
                        ))
                        sellers_nuevos += 1

                    # Guardar hash en sync_hashes
                    self._guardar_hash(seller_code, hash_actual)

                    # Reportar progreso cada 10 sellers
                    if (sellers_nuevos + sellers_modificados) % 10 == 0:
                        self.log(f"   Procesados: {sellers_nuevos} nuevos, {sellers_modificados} modificados, {sellers_omitidos} omitidos (sin cambios)", "info")

                except Exception as e:
                    self.log(f"❌ Error procesando seller {seller[0] if seller else 'unknown'}: {e}", "error")
                    errores += 1

            # Commit cambios en ambas bases de datos
            self.mysql_conn.commit()
            self.pg_conn.commit()

            self.log("", "info")
            self.log("=== RESUMEN DE SINCRONIZACIÓN DE SELLERS ===", "info")
            self.log(f"✅ Sellers nuevos: {sellers_nuevos}", "success")
            self.log(f"🔄 Sellers modificados: {sellers_modificados}", "info")
            self.log(f"⏭️  Sellers omitidos (sin cambios): {sellers_omitidos}", "info")
            if errores > 0:
                self.log(f"❌ Errores: {errores}", "error")
            self.log("=== SINCRONIZACIÓN DE SELLERS COMPLETADA ===", "info")

            return {
                'nuevos': sellers_nuevos,
                'actualizados': sellers_modificados,
                'errores': errores,
                'exito': errores == 0
            }

        except Exception as e:
            self.log(f"❌ Error en sincronización de sellers: {e}", "error")
            return {
                'nuevos': 0,
                'actualizados': 0,
                'errores': 1,
                'exito': False
            }

    def cerrar(self):
        """Cerrar conexiones"""
        if self.pg_cursor:
            self.pg_cursor.close()
        if self.pg_conn:
            self.pg_conn.close()
        if self.mysql_cursor:
            self.mysql_cursor.close()
        if self.mysql_conn:
            self.mysql_conn.close()
