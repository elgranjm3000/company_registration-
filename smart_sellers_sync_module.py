#!/usr/bin/env python3
"""
MÓDULO DE SINCRONIZACIÓN DE SELLERS
====================================
Sincroniza vendedores desde PostgreSQL a MySQL

Autor: Sistema de Sincronización
Versión: 1.0
"""

import pymysql
import psycopg2
from typing import Dict, Any


class SmartSellersSyncModule:
    """Módulo de sincronización inteligente de sellers"""

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
            self.mysql_cursor = self.mysql_conn.cursor()
            self.log("✅ Conectado a MySQL (sellers)", "success")
            return True
        except Exception as e:
            self.log(f"❌ Error conectando MySQL: {e}", "error")
            return False

    def ejecutar_sync(self) -> dict:
        """
        Ejecutar sincronización de sellers

        Returns:
            Dict con estadísticas: {'nuevos': int, 'actualizados': int, 'errores': int, 'exito': bool}
        """
        try:
            self.log("=== SINCRONIZANDO SELLERS ===", "info")

            # Obtener sellers desde PostgreSQL (solo campos que existen)
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
                    u.email
                FROM sellers s
                LEFT JOIN users u ON s.user_code = u.code
                WHERE s.user_code IS NOT NULL
                ORDER BY s.code
            """)

            sellers = self.pg_cursor.fetchall()

            if not sellers:
                self.log("ℹ️  No se encontraron sellers para sincronizar", "warning")
                return True

            self.log(f"📊 Se encontraron {len(sellers)} sellers en PostgreSQL", "info")

            sellers_importados = 0
            sellers_actualizados = 0
            errores = 0

            for seller in sellers:
                try:
                    (seller_code, description, status, percent_sales,
                     percent_receivable, inkeeper, user_code,
                     percent_gerencial_debit_note, percent_gerencial_credit_note,
                     percent_returned_check, email) = seller

                    # Buscar si ya existe en MySQL
                    self.mysql_cursor.execute(
                        "SELECT id FROM sellers WHERE code = %s LIMIT 1",
                        (seller_code,)
                    )
                    existente = self.mysql_cursor.fetchone()

                    # Obtener company_id desde el app si está disponible
                    company_id = getattr(self.app, 'company_id', 27)

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
                        sellers_actualizados += 1
                    else:
                        # Buscar user_id por email
                        self.mysql_cursor.execute(
                            "SELECT id FROM users WHERE email = %s AND role = 'seller' LIMIT 1",
                            (email,)
                        )
                        user_result = self.mysql_cursor.fetchone()

                        if not user_result:
                            self.log(f"⚠️  No se encontró user para email: {email}", "warning")
                            errores += 1
                            continue

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
                            user_id, company_id, seller_code, description, status,
                            percent_sales, percent_receivable, inkeeper,
                            user_code, percent_gerencial_debit_note, percent_gerencial_credit_note,
                            percent_returned_check
                        ))
                        sellers_importados += 1

                    if (sellers_importados + sellers_actualizados) % 10 == 0:
                        self.log(f"   Procesados: {sellers_importados} nuevos, {sellers_actualizados} actualizados", "info")

                except Exception as e:
                    self.log(f"❌ Error procesando seller {seller[0] if seller else 'unknown'}: {e}", "error")
                    errores += 1

            # Commit cambios
            self.mysql_conn.commit()

            self.log("", "info")
            self.log("=== RESUMEN DE SINCRONIZACIÓN DE SELLERS ===", "info")
            self.log(f"✅ Sellers importados: {sellers_importados}", "success")
            self.log(f"🔄 Sellers actualizados: {sellers_actualizados}", "info")
            if errores > 0:
                self.log(f"❌ Errores: {errores}", "error")
            self.log("=== SINCRONIZACIÓN DE SELLERS COMPLETADA ===", "info")

            return {
                'nuevos': sellers_importados,
                'actualizados': sellers_actualizados,
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
