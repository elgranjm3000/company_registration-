#!/usr/bin/env python3
"""
Script de Migración: Quotes (MySQL) → Sales Operations (PostgreSQL)
Migra cotizaciones desde MySQL a la estructura de ventas en PostgreSQL
"""

import mysql.connector
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timedelta
from decimal import Decimal
import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN DE CONEXIONES
# =====================================================

MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'tiger',
    'database': 'salesapi',
    'charset': 'utf8mb4'
}

POSTGRES_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'muentes123.',
    'database': 'nueva',
    'port': 5432
}

# Configuración de mapeo
OFFSET_CORRELATIVO = 50000  # Offset para evitar conflictos con datos existentes
CODIGO_MONEDA_DEFAULT = '02'  # USD por defecto
CODIGO_CLIENTE_DEFAULT = '00'  # Cliente genérico
CODIGO_VENDEDOR_DEFAULT = '00'  # Vendedor genérico
CODIGO_ALMACEN_DEFAULT = '00'
CODIGO_UBICACION_DEFAULT = '00'
CODIGO_USUARIO_DEFAULT = '00'
CODIGO_ESTACION_DEFAULT = '00'

# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def get_tax_code(tax_percentage):
    """Mapea porcentaje de impuesto a código de impuesto PostgreSQL"""
    if tax_percentage >= 15:
        return '01'  # IVA General 16%
    elif tax_percentage >= 7:
        return '03'  # IVA Reducido 8%
    else:
        return 'EX'  # Exento

def safe_decimal(value, default=0.0):
    """Convierte valor a Decimal de forma segura"""
    try:
        return float(Decimal(str(value)))
    except:
        return default

def safe_int(value, default=0):
    """Convierte valor a int de forma segura"""
    try:
        return int(value) if value else default
    except:
        return default

# =====================================================
# CLASE PRINCIPAL DE MIGRACIÓN
# =====================================================

class QuotesMigration:
    def __init__(self):
        self.mysql_conn = None
        self.pg_conn = None
        self.stats = {
            'quotes_migrated': 0,
            'items_migrated': 0,
            'errors': 0
        }
        
    def connect_mysql(self):
        """Conecta a MySQL"""
        try:
            self.mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
            logger.info("✓ Conectado a MySQL")
            return True
        except Exception as e:
            logger.error(f"✗ Error conectando a MySQL: {e}")
            return False
    
    def connect_postgres(self):
        """Conecta a PostgreSQL"""
        try:
            self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
            self.pg_conn.autocommit = False
            logger.info("✓ Conectado a PostgreSQL")
            return True
        except Exception as e:
            logger.error(f"✗ Error conectando a PostgreSQL: {e}")
            return False
    
    def fetch_quotes(self):
        """Obtiene cotizaciones desde MySQL"""
        query = """
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
            b.id as customer_id_full,
            b.name as customer_name,
            b.email as customer_email,
            b.phone as customer_phone,
            b.document_number as customer_doc,
            b.address as customer_address,
            c.id as seller_id,
            d.name as seller_name,
            d.email as seller_email 
        FROM salesapi.quotes a
        LEFT JOIN salesapi.customers b ON b.id = a.customer_id
        LEFT JOIN salesapi.sellers c ON a.user_seller_id = c.id
        LEFT JOIN salesapi.users d ON d.id = c.user_id
        ORDER BY a.id
        """
        
        try:
            cursor = self.mysql_conn.cursor(dictionary=True)
            cursor.execute(query)
            quotes = cursor.fetchall()
            logger.info(f"✓ Obtenidas {len(quotes)} cotizaciones de MySQL")
            return quotes
        except Exception as e:
            logger.error(f"✗ Error obteniendo cotizaciones: {e}")
            return []
    
    def fetch_quote_items(self, quote_id):
        """Obtiene items de una cotización específica"""
        query = """
        SELECT 
            a.quote_id,
            a.description,
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
        FROM salesapi.quote_items a
        LEFT JOIN salesapi.quotes b ON b.id = a.quote_id
        LEFT JOIN salesapi.products c ON c.id = a.product_id
        WHERE a.quote_id = %s
        ORDER BY a.id
        """
        
        try:
            cursor = self.mysql_conn.cursor(dictionary=True)
            cursor.execute(query, (quote_id,))
            items = cursor.fetchall()
            return items
        except Exception as e:
            logger.error(f"✗ Error obteniendo items de quote {quote_id}: {e}")
            return []
    
    def insert_sales_operation(self, quote):
        """Inserta operación de venta principal"""
        correlativo = quote['idQuotes'] + OFFSET_CORRELATIVO
        
        sql = """
        INSERT INTO public.sales_operation (
            correlative, operation_type, document_no, control_no, 
            emission_date, register_date, client_code, client_name, 
            client_id, client_address, client_phone, seller, 
            credit_days, expiration_date, description, store, locations, 
            user_code, station, total_amount, total_net_details, 
            total_tax_details, total_details, percent_discount, discount, 
            total_net, total_tax, total, credit, cash, coin_code, 
            canceled, pending
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
            %s, %s, %s
        )
        """
        
        emission_date = quote.get('created_at') or datetime.now()
        
        values = (
            correlativo,
            'COTIZACION',
            quote['quote_number'] or f"COT-{correlativo:06d}",
            f"CTRL-{correlativo:06d}",
            emission_date,
            emission_date,
            CODIGO_CLIENTE_DEFAULT,
            quote['customer_name'] or 'Cliente Migrado',
            quote['customer_doc'] or f"MIG-{quote['idQuotes']}",
            quote['customer_address'] or 'Dirección migrada',
            quote['customer_phone'] or 'S-N',
            CODIGO_VENDEDOR_DEFAULT,
            30,
            emission_date + timedelta(days=30),
            'Cotización migrada desde MySQL',
            CODIGO_ALMACEN_DEFAULT,
            CODIGO_UBICACION_DEFAULT,
            CODIGO_USUARIO_DEFAULT,
            CODIGO_ESTACION_DEFAULT,
            safe_decimal(quote['total']),
            safe_decimal(quote['subtotal']),
            safe_decimal(quote['tax_amount']),
            safe_decimal(quote['total']),
            safe_decimal(quote['discount']),
            safe_decimal(quote['discount_amount']),
            safe_decimal(quote['subtotal']) - safe_decimal(quote['discount_amount']),
            safe_decimal(quote['tax_amount']),
            safe_decimal(quote['total']),
            safe_decimal(quote['total']),
            0.0,
            CODIGO_MONEDA_DEFAULT,
            False,
            True
        )
        
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute(sql, values)
            logger.info(f"  ✓ Operación {correlativo} insertada")
            return correlativo
        except Exception as e:
            logger.error(f"  ✗ Error insertando operación {correlativo}: {e}")
            raise
    
    def insert_sales_operation_coins(self, correlativo, quote):
        """Inserta totales por moneda"""
        sql = """
        INSERT INTO public.sales_operation_coins (
            main_correlative, coin_code, factor_type, buy_aliquot, 
            sales_aliquot, total_net_details, total_tax_details, 
            total_details, discount, freight, total_net, total_tax, 
            total, credit, cash
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        bcv_rate = safe_decimal(quote.get('bcv_rate', 170))
        
        values = (
            correlativo,
            CODIGO_MONEDA_DEFAULT,
            1,
            bcv_rate,
            bcv_rate,
            safe_decimal(quote['subtotal']),
            safe_decimal(quote['tax_amount']),
            safe_decimal(quote['total']),
            safe_decimal(quote['discount_amount']),
            0.0,
            safe_decimal(quote['subtotal']) - safe_decimal(quote['discount_amount']),
            safe_decimal(quote['tax_amount']),
            safe_decimal(quote['total']),
            safe_decimal(quote['total']),
            0.0
        )
        
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute(sql, values)
        except Exception as e:
            logger.error(f"  ✗ Error insertando coins para {correlativo}: {e}")
            raise
    
    def insert_sales_operation_details(self, correlativo, items):
        """Inserta detalles de la operación"""
        for item in items:
            # Obtener unit ID desde products_units
            logger.info(f"\code: {item.get('product_code')}")
            unit_id = self.get_unit_id(item.get('product_code'))
            
            sql = """
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
            
            tax_percent = safe_decimal(item.get('tax_amount', 0)) / safe_decimal(item.get('subtotal', 1)) * 100 if item.get('subtotal') else 0
            
            values = (
                correlativo,
                item.get('product_code') or f"MIG-{item['product_id']}",
                item['description'],
                safe_decimal(item['quantity']),
                CODIGO_ALMACEN_DEFAULT,
                CODIGO_UBICACION_DEFAULT,
                unit_id,
                1.0,
                1,
                safe_decimal(item['unit_price']) * 0.8,  # Estimación del costo
                get_tax_code(tax_percent),
                tax_percent,
                safe_decimal(item['unit_price']),
                safe_decimal(item['quantity']) * safe_decimal(item['unit_price']) * 0.8,
                safe_decimal(item['tax_amount']) * 0.8,
                safe_decimal(item['quantity']) * safe_decimal(item['unit_price']) * 0.8 + safe_decimal(item['tax_amount']) * 0.8,
                safe_decimal(item['subtotal']),
                safe_decimal(item['tax_amount']),
                safe_decimal(item['total']),
                safe_decimal(item.get('discount_percentage', 0)),
                safe_decimal(item.get('discount_amount', 0)),
                safe_decimal(item['subtotal']) - safe_decimal(item.get('discount_amount', 0)),
                safe_decimal(item['tax_amount']),
                safe_decimal(item['total']),
                CODIGO_MONEDA_DEFAULT
            )
            
            try:
                cursor = self.pg_conn.cursor()
                cursor.execute(sql, values)
                line = cursor.fetchone()[0]
                
                # Insertar coins para el detalle
                self.insert_detail_coins(correlativo, line, item)
                
                self.stats['items_migrated'] += 1
            except Exception as e:
                logger.error(f"  ✗ Error insertando detalle: {e}")
                raise
    
    def get_unit_id(self, product_code):
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
            cursor = self.pg_conn.cursor()
            cursor.execute(sql, (product_code,))
            result = cursor.fetchone()
            return result[0] if result else 1
        except:
            return 1
    
    def insert_detail_coins(self, correlativo, line, item):
        """Inserta totales por moneda para el detalle"""
        sql = """
        INSERT INTO public.sales_operation_details_coins (
            main_correlative, main_line, unitary_cost, price, 
            total_net_cost, total_tax_cost, total_cost, 
            total_net_gross, total_tax_gross, total_gross, 
            discount, total_net, total_tax, total, coin_code
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        values = (
            correlativo,
            line,
            safe_decimal(item['unit_price']) * 0.8,
            safe_decimal(item['unit_price']),
            safe_decimal(item['quantity']) * safe_decimal(item['unit_price']) * 0.8,
            safe_decimal(item['tax_amount']) * 0.8,
            safe_decimal(item['quantity']) * safe_decimal(item['unit_price']) * 0.8 + safe_decimal(item['tax_amount']) * 0.8,
            safe_decimal(item['subtotal']),
            safe_decimal(item['tax_amount']),
            safe_decimal(item['total']),
            safe_decimal(item.get('discount_amount', 0)),
            safe_decimal(item['subtotal']) - safe_decimal(item.get('discount_amount', 0)),
            safe_decimal(item['tax_amount']),
            safe_decimal(item['total']),
            CODIGO_MONEDA_DEFAULT
        )
        
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute(sql, values)
        except Exception as e:
            logger.error(f"  ✗ Error insertando detail coins: {e}")
            raise
    
    def insert_sales_operation_taxes(self, correlativo, items):
        """Inserta impuestos de la operación"""
        # Agrupar impuestos por tasa
        taxes_dict = {}
        
        for item in items:
            tax_percent = safe_decimal(item.get('tax_amount', 0)) / safe_decimal(item.get('subtotal', 1)) * 100 if item.get('subtotal') else 0
            tax_code = get_tax_code(tax_percent)
            
            if tax_code not in taxes_dict:
                taxes_dict[tax_code] = {
                    'aliquot': tax_percent,
                    'taxable': 0.0,
                    'tax': 0.0
                }
            
            taxes_dict[tax_code]['taxable'] += safe_decimal(item['subtotal']) - safe_decimal(item.get('discount_amount', 0))
            taxes_dict[tax_code]['tax'] += safe_decimal(item.get('tax_amount', 0))
        
        # Insertar cada impuesto
        for tax_code, tax_data in taxes_dict.items():
            if tax_data['tax'] == 0:
                continue
                
            sql = """
            INSERT INTO public.sales_operation_taxes (
                main_correlative, taxe_code, aliquot, taxable, tax, tax_type
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            values = (
                correlativo,
                tax_code,
                tax_data['aliquot'],
                tax_data['taxable'],
                tax_data['tax'],
                1
            )
            
            try:
                cursor = self.pg_conn.cursor()
                cursor.execute(sql, values)
                
                # Insertar coins para el impuesto
                self.insert_tax_coins(correlativo, tax_code, tax_data)
            except Exception as e:
                logger.error(f"  ✗ Error insertando tax: {e}")
                raise
    
    def insert_tax_coins(self, correlativo, tax_code, tax_data):
        """Inserta totales por moneda para los impuestos"""
        sql = """
        INSERT INTO public.sales_operation_taxes_coins (
            main_correlative, main_taxe_code, taxable, tax, coin_code
        ) VALUES (%s, %s, %s, %s, %s)
        """
        
        values = (
            correlativo,
            tax_code,
            tax_data['taxable'],
            tax_data['tax'],
            CODIGO_MONEDA_DEFAULT
        )
        
        try:
            cursor = self.pg_conn.cursor()
            cursor.execute(sql, values)
        except Exception as e:
            logger.error(f"  ✗ Error insertando tax coins: {e}")
            raise
    
    def migrate_quote(self, quote):
        """Migra una cotización completa"""
        try:
            quote_id = quote['idQuotes']
            logger.info(f"\n🔄 Migrando Quote ID: {quote_id}")
            
            # 1. Obtener items de la cotización
            items = self.fetch_quote_items(quote_id)
            if not items:
                logger.warning(f"  ⚠ Quote {quote_id} no tiene items, saltando...")
                return False
            
            # 2. Insertar operación principal
            correlativo = self.insert_sales_operation(quote)
            
            # 3. Insertar totales por moneda
            self.insert_sales_operation_coins(correlativo, quote)
            
            # 4. Insertar detalles
            self.insert_sales_operation_details(correlativo, items)
            
            # 5. Insertar impuestos
            self.insert_sales_operation_taxes(correlativo, items)
            
            # Commit
            self.pg_conn.commit()
            self.stats['quotes_migrated'] += 1
            logger.info(f"  ✓ Quote {quote_id} migrado exitosamente")
            
            return True
            
        except Exception as e:
            self.pg_conn.rollback()
            self.stats['errors'] += 1
            logger.error(f"  ✗ Error migrando quote {quote['idQuotes']}: {e}")
            return False
    
    def run_migration(self):
        """Ejecuta la migración completa"""
        logger.info("\n" + "="*60)
        logger.info("INICIANDO MIGRACIÓN DE COTIZACIONES")
        logger.info("="*60 + "\n")
        
        # Conectar a bases de datos
        if not self.connect_mysql() or not self.connect_postgres():
            logger.error("No se pudo establecer conexión con las bases de datos")
            return False
        
        try:
            # Obtener cotizaciones
            quotes = self.fetch_quotes()
            if not quotes:
                logger.warning("No se encontraron cotizaciones para migrar")
                return False
            
            # Migrar cada cotización
            for quote in quotes:
                self.migrate_quote(quote)
            
            # Mostrar estadísticas
            logger.info("\n" + "="*60)
            logger.info("MIGRACIÓN COMPLETADA")
            logger.info("="*60)
            logger.info(f"✓ Cotizaciones migradas: {self.stats['quotes_migrated']}")
            logger.info(f"✓ Items migrados: {self.stats['items_migrated']}")
            logger.info(f"✗ Errores: {self.stats['errors']}")
            logger.info("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error general en la migración: {e}")
            return False
        
        finally:
            # Cerrar conexiones
            if self.mysql_conn:
                self.mysql_conn.close()
                logger.info("✓ Conexión MySQL cerrada")
            if self.pg_conn:
                self.pg_conn.close()
                logger.info("✓ Conexión PostgreSQL cerrada")

# =====================================================
# PUNTO DE ENTRADA
# =====================================================

if __name__ == "__main__":
    migration = QuotesMigration()
    success = migration.run_migration()
    
    exit(0 if success else 1)
