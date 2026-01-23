"""
MÓDULO: Smart Sellers Sync
Sincronización inteligente de sellers con detección de cambios
Se integra en la aplicación Tkinter principal
"""

import psycopg2
import mysql.connector
from datetime import datetime
import hashlib
import bcrypt


def laravel_hash_make(password):
    """
    Generar hash compatible con Laravel Hash::make()
    Usa bcrypt con cost=10 (Laravel default)
    
    Args:
        password (str): Contraseña a hashear
    
    Returns:
        str: Hash bcrypt compatible con Laravel (formato $2y$)
    """
    # Convertir password a bytes si es string
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Laravel usa cost=10 por defecto
    salt = bcrypt.gensalt(rounds=10)
    hashed = bcrypt.hashpw(password, salt)
    
    # Laravel espera $2y$ en lugar de $2b$ (compatibilidad PHP)
    laravel_hash = hashed.decode('utf-8').replace('$2b$', '$2y$')
    
    return laravel_hash


class SmartSellersSyncModule:
    """Módulo de sincronización inteligente de sellers para integrar en CompleteSyncApp"""
    
    def __init__(self, app):
        """
        Inicializar el módulo con referencia a la app principal
        
        Args:
            app: Referencia a CompleteSyncApp para acceder a log_message, etc.
        """
        self.app = app
        self.postgresql_config = app.postgresql_config
        self.mysql_config = app.mysql_config
        self.company_id = app.company_id
        self.sync_running = app.sync_running
        
        # Estadísticas
        self.stats = {
            'nuevos': 0,
            'actualizados': 0,
            'eliminados': 0,
            'sin_cambios': 0,
            'errores': 0
        }
    
    def _log(self, mensaje, tipo='info'):
        """Usar el logger de la aplicación principal"""
        self.app.log_message(mensaje, tipo)
    
    def obtener_sellers_postgresql(self):
        """Obtiene sellers de PostgreSQL con hash de control"""
        self._log("Obteniendo sellers de PostgreSQL...", "info")
        
        try:
            pg_conn = psycopg2.connect(**self.postgresql_config)
            pg_cursor = pg_conn.cursor()
            
            query = """
            SELECT 
                a.code as seller_code,
                a.code as pg_seller_id,
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
            
            # Convertir a diccionario con email como clave
            sellers_dict = {}
            for seller in sellers_data:
                seller_code, pg_id, user_name, email, password, user_code = seller
                
                sellers_dict[email] = {
                    'seller_code': seller_code,
                    'pg_seller_id': pg_id,
                    'user_name': user_name,
                    'email': email,
                    'user_password': password,
                    'user_code': user_code,
                   
                    'hash': self._generar_hash(seller_code, user_name, user_code)
                }
            
            self._log(f"Sellers en PostgreSQL: {len(sellers_dict)}", "success")
            
            pg_cursor.close()
            pg_conn.close()
            
            return sellers_dict
        
        except Exception as e:
            self._log(f"Error obteniendo sellers de PostgreSQL: {str(e)}", "error")
            raise
    
    def obtener_sellers_mysql(self):
        """Obtiene sellers de MySQL con hash de control"""
        self._log("Obteniendo sellers de MySQL...", "info")
        
        try:
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor(dictionary=True)
            
            query = """
            SELECT 
                s.id as mysql_seller_id,
                s.code as seller_code,
                s.user_code,
                s.description,
                u.id as user_id,
                u.email,
                u.password as user_password,
                s.updated_at as mysql_updated_at
            FROM sellers s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.company_id = %s
            ORDER BY s.code
            """
            
            mysql_cursor.execute(query, (self.company_id,))
            sellers_data = mysql_cursor.fetchall()
            
            # Convertir a diccionario con email como clave
            sellers_dict = {}
            for seller in sellers_data:
                email = seller['email']
                
                if email:
                    sellers_dict[email] = {
                        'mysql_seller_id': seller['mysql_seller_id'],
                        'seller_code': seller['seller_code'],
                        'user_id': seller['user_id'],
                        'description': seller['description'],
                        'email': email,
                        'user_password': seller['user_password'],
                        'user_code': seller['user_code'],
                        'mysql_updated_at': seller['mysql_updated_at'],
                        'hash': self._generar_hash(
                            seller['seller_code'],
                            seller['description'],
                            seller['user_code']
                        )
                    }
            
            self._log(f"Sellers en MySQL: {len(sellers_dict)}", "success")
            
            mysql_cursor.close()
            mysql_conn.close()
            
            return sellers_dict
        
        except Exception as e:
            self._log(f"Error obteniendo sellers de MySQL: {str(e)}", "error")
            raise
    
    def _generar_hash(self, seller_code, description, user_code):
        """Genera hash para detectar cambios"""
        datos = f"{seller_code}|{description}|{user_code}"
        return hashlib.md5(datos.encode()).hexdigest()
    
    def detectar_cambios(self, sellers_pg, sellers_mysql):
        """Detecta cambios: NUEVOS, ELIMINADOS, MODIFICADOS"""
        self._log("Analizando cambios en sellers...", "info")
        
        cambios = {
            'nuevos': [],
            'eliminados': [],
            'modificados': [],
            'sin_cambios': []
        }
        
        # Detectar NUEVOS y MODIFICADOS
        for email, datos_pg in sellers_pg.items():
            if email not in sellers_mysql:
                cambios['nuevos'].append(datos_pg)
                self._log(f"✓ NUEVO: {datos_pg['seller_code']} ({email})", "debug")
            else:
                datos_mysql = sellers_mysql[email]
                
                if datos_pg['hash'] != datos_mysql['hash']:
                    datos_pg['mysql_seller_id'] = datos_mysql['mysql_seller_id']
                    datos_pg['user_id'] = datos_mysql['user_id']
                    cambios['modificados'].append(datos_pg)
                    self._log(f"⚠ MODIFICADO: {datos_pg['seller_code']} ({email})", "debug")
                else:
                    cambios['sin_cambios'].append(datos_pg)
                    self._log(f"✓ SIN CAMBIOS: {datos_pg['seller_code']} ({email})", "debug")
        
        # Detectar ELIMINADOS
        for email, datos_mysql in sellers_mysql.items():
            if email not in sellers_pg:
                cambios['eliminados'].append(datos_mysql)
                self._log(f"✗ ELIMINADO: {datos_mysql['seller_code']} ({email})", "warning")
        
        # Resumen
        self._log("", "info")
        self._log("=== RESUMEN DE CAMBIOS ===", "info")
        self._log(f"Nuevos: {len(cambios['nuevos'])}", "info")
        self._log(f"Modificados: {len(cambios['modificados'])}", "info")
        self._log(f"Eliminados: {len(cambios['eliminados'])}", "info")
        self._log(f"Sin cambios: {len(cambios['sin_cambios'])}", "info")
        self._log("", "info")
        
        return cambios
    
    def procesar_nuevos(self, mysql_cursor, mysql_conn, cambios_nuevos):
        """Procesa sellers NUEVOS - Verifica si user existe y hace UPDATE si aplica"""
        if not cambios_nuevos:
            return 0
        
        self._log(f"Procesando {len(cambios_nuevos)} sellers NUEVOS...", "info")
        
        insertados = 0
        actualizados = 0
        
        for seller in cambios_nuevos:
            if not self.app.sync_running:
                break
            
            try:
                email = seller['email']
                laravel_password_hash = laravel_hash_make(seller['user_password'])
                
                # 1. VERIFICAR si el user ya existe por email
                check_user_query = """
                SELECT id FROM users WHERE email = %s AND role = 'seller' LIMIT 1
                """
                
                mysql_cursor.execute(check_user_query, (email,))
                existing_user = mysql_cursor.fetchone()
                
                if existing_user:
                    # El user existe - HACER UPDATE
                    user_id = existing_user[0]
                    
                    update_user_query = """
                    UPDATE users 
                    SET 
                        name = %s,
                        password = %s,
                        role = 'seller',
                        status = 'active',
                        updated_at = NOW()
                    WHERE id = %s
                    """
                    
                    mysql_cursor.execute(update_user_query, (
                        seller['user_name'],
                        laravel_password_hash,
                        user_id
                    ))
                    
                    self._log(f"  ⚠️ User existente actualizado: {email} (ID: {user_id})", "info")
                    actualizados += 1
                
                else:
                    # El user NO existe - HACER INSERT
                    insert_user_query = """
                    INSERT INTO users (
                        name, email, password, role, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, 'seller', 'active', NOW(), NOW())
                    """
                    
                    mysql_cursor.execute(insert_user_query, (
                        seller['user_name'],
                        seller['email'],
                        laravel_password_hash
                    ))
                    
                    user_id = mysql_cursor.lastrowid
                    self._log(f"  ✓ User creado: {email} (ID: {user_id})", "debug")
                    insertados += 1
                
                # 2. CREAR O ACTUALIZAR SELLER
                # Verificar si el seller ya existe para esta company
                check_seller_query = """
                SELECT id FROM sellers 
                WHERE user_id = %s AND company_id = %s 
                LIMIT 1
                """
                
                mysql_cursor.execute(check_seller_query, (user_id, self.company_id))
                existing_seller = mysql_cursor.fetchone()
                
                if existing_seller:
                    # Seller existe - UPDATE
                    seller_id = existing_seller[0]
                    
                    update_seller_query = """
                    UPDATE sellers 
                    SET 
                        code = %s,
                        description = %s,
                        status = 'active',
                        user_code = %s,
                        seller_status = 'active',
                        updated_at = NOW()
                    WHERE id = %s AND company_id = %s
                    """
                    
                    mysql_cursor.execute(update_seller_query, (
                        seller['seller_code'],
                        seller['user_name'],
                        seller['user_code'],
                        seller_id,
                        self.company_id
                    ))
                    
                    self._log(
                        f"  ⚠️ Seller actualizado: {seller['seller_code']} (ID: {seller_id})",
                        "info"
                    )
                
                else:
                    # Seller NO existe - INSERT
                    insert_seller_query = """
                    INSERT INTO sellers (
                        user_id, company_id, code, description, status, 
                        percent_sales, percent_receivable, inkeeper, user_code,
                        percent_gerencial_debit_note, percent_gerencial_credit_note,
                        percent_returned_check, seller_status, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, 'active', 0.0, 0.0, 0, %s, 0.0, 0.0, 0.0, 'active', NOW(), NOW()
                    )
                    """
                    
                    mysql_cursor.execute(insert_seller_query, (
                        user_id,
                        self.company_id,
                        seller['seller_code'],
                        seller['user_name'],
                        seller['user_code']
                    ))
                    
                    self._log(
                        f"  ✓ Seller creado: {seller['seller_code']} → User ID {user_id}",
                        "success"
                    )
                
            except mysql.connector.Error as e:
                self._log(f"  ❌ Error procesando seller {seller['seller_code']}: {str(e)}", "error")
                self.stats['errores'] += 1
        
        mysql_conn.commit()
        self.stats['nuevos'] = insertados
        self.stats['actualizados'] += actualizados
        return insertados + actualizados
    
    def procesar_modificados(self, mysql_cursor, mysql_conn, cambios_modificados):
        """Procesa sellers MODIFICADOS"""
        if not cambios_modificados:
            return 0
        
        self._log(f"Procesando {len(cambios_modificados)} sellers MODIFICADOS...", "info")
        
        actualizados = 0
        for seller in cambios_modificados:
            if not self.app.sync_running:
                break
            
            try:
                mysql_seller_id = seller.get('mysql_seller_id')
                user_id = seller.get('user_id')
                
                if not mysql_seller_id or not user_id:
                    self._log(
                        f"  ⚠️ Datos incompletos para {seller['seller_code']}",
                        "warning"
                    )
                    continue
                
                # Hashear la contraseña usando bcrypt compatible con Laravel
                laravel_password_hash = laravel_hash_make(seller['user_password'])
                
                # Actualizar seller
                update_seller_query = """
                UPDATE sellers 
                SET 
                    code = %s,
                    description = %s,
                    user_code = %s,
                    updated_at = NOW()
                WHERE id = %s AND company_id = %s
                """
                
                mysql_cursor.execute(update_seller_query, (
                    seller['seller_code'],
                    seller['user_name'],
                    seller['user_code'],
                    mysql_seller_id,
                    self.company_id
                ))
                
                # Actualizar user
                update_user_query = """
                UPDATE users 
                SET 
                    name = %s,
                    password = %s,
                    updated_at = NOW()
                WHERE id = %s
                """
                
                mysql_cursor.execute(update_user_query, (
                    seller['user_name'],
                    laravel_password_hash,
                    user_id
                ))
                
                self._log(
                    f"  ✓ Seller actualizado: {seller['seller_code']}",
                    "success"
                )
                actualizados += 1
                
            except mysql.connector.Error as e:
                self._log(
                    f"  ❌ Error actualizando seller {seller['seller_code']}: {str(e)}",
                    "error"
                )
                self.stats['errores'] += 1
        
        mysql_conn.commit()
        self.stats['actualizados'] = actualizados
        return actualizados
    
    def procesar_eliminados(self, mysql_cursor, mysql_conn, cambios_eliminados):
        """Procesa sellers ELIMINADOS"""
        if not cambios_eliminados:
            return 0
        
        self._log(f"Procesando {len(cambios_eliminados)} sellers ELIMINADOS...", "info")
        
        eliminados = 0
        for seller in cambios_eliminados:
            if not self.app.sync_running:
                break
            
            try:
                mysql_seller_id = seller.get('mysql_seller_id')
                user_id = seller.get('user_id')
                
                if not mysql_seller_id:
                    self._log(
                        f"  ⚠️ No se puede eliminar {seller['seller_code']} - ID faltante",
                        "warning"
                    )
                    continue
                
                # Eliminar relaciones de seller primero
                tablas_seller = [
                    'seller_commission',
                    'seller_documents',
                    'seller_transactions',
                ]
                
                for tabla in tablas_seller:
                    try:
                        mysql_cursor.execute(
                            f"DELETE FROM {tabla} WHERE seller_id = %s",
                            (mysql_seller_id,)
                        )
                    except:
                        pass  # Tabla podría no existir
                
                # Eliminar seller
                mysql_cursor.execute(
                    "DELETE FROM sellers WHERE id = %s AND company_id = %s",
                    (mysql_seller_id, self.company_id)
                )
                
                # Eliminar user si no tiene otros sellers
                if user_id:
                    mysql_cursor.execute(
                        "SELECT COUNT(*) as count FROM sellers WHERE user_id = %s",
                        (user_id,)
                    )
                    result = mysql_cursor.fetchone()
                    
                    if result[0] == 0:  # No hay más sellers para este user
                        mysql_cursor.execute(
                            "DELETE FROM users WHERE id = %s AND role = 'seller'",
                            (user_id,)
                        )
                        self._log(
                            f"  ✓ Seller y User eliminados: {seller['seller_code']}",
                            "success"
                        )
                    else:
                        self._log(
                            f"  ✓ Seller eliminado (User mantiene otros sellers): {seller['seller_code']}",
                            "success"
                        )
                
                eliminados += 1
                
            except mysql.connector.Error as e:
                self._log(
                    f"  ❌ Error eliminando seller {seller['seller_code']}: {str(e)}",
                    "error"
                )
                self.stats['errores'] += 1
        
        mysql_conn.commit()
        self.stats['eliminados'] = eliminados
        return eliminados
    
    def ejecutar_sync(self):
        """Ejecuta sincronización completa con detección de cambios"""
        inicio = datetime.now()
        
        self._log("", "info")
        self._log("╔════════════════════════════════════════════════════════════════╗", "info")
        self._log("║          INICIANDO SYNC INTELIGENTE DE SELLERS                  ║", "info")
        self._log("╚════════════════════════════════════════════════════════════════╝", "info")
        self._log("", "info")
        
        try:
            # 1. Obtener datos de ambas bases de datos
            sellers_pg = self.obtener_sellers_postgresql()
            sellers_mysql = self.obtener_sellers_mysql()
            
            # 2. Detectar cambios
            cambios = self.detectar_cambios(sellers_pg, sellers_mysql)
            
            # 3. Si no hay cambios, finalizar
            if not any([
                cambios['nuevos'],
                cambios['eliminados'],
                cambios['modificados']
            ]):
                self._log("No hay cambios que sincronizar", "info")
                self.stats['sin_cambios'] = len(cambios['sin_cambios'])
                return self._mostrar_resumen(inicio)
            
            # 4. Conectar MySQL para procesar cambios
            mysql_conn = mysql.connector.connect(**self.mysql_config)
            mysql_cursor = mysql_conn.cursor()
            
            # 5. Procesar cambios
            self._log("", "info")
            self.procesar_nuevos(mysql_cursor, mysql_conn, cambios['nuevos'])
            self.procesar_modificados(mysql_cursor, mysql_conn, cambios['modificados'])
            self.procesar_eliminados(mysql_cursor, mysql_conn, cambios['eliminados'])
            
            self.stats['sin_cambios'] = len(cambios['sin_cambios'])
            
            mysql_cursor.close()
            mysql_conn.close()
            
            return self._mostrar_resumen(inicio)
            
        except Exception as e:
            self._log(f"Error durante sincronización: {str(e)}", "error")
            return False
    
    def _mostrar_resumen(self, inicio):
        """Muestra resumen de la sincronización"""
        duracion = (datetime.now() - inicio).total_seconds()
        
        self._log("", "info")
        self._log("╔════════════════════════════════════════════════════════════════╗", "info")
        self._log("║                    RESUMEN DE SINCRONIZACIÓN                    ║", "info")
        self._log("╚════════════════════════════════════════════════════════════════╝", "info")
        self._log(f"Nuevos:        {self.stats['nuevos']} ✓", "success")
        self._log(f"Modificados:   {self.stats['actualizados']} ⚠", "info")
        self._log(f"Eliminados:    {self.stats['eliminados']} ✗", "warning")
        self._log(f"Sin cambios:   {self.stats['sin_cambios']} ◆", "info")
        self._log(f"Errores:       {self.stats['errores']} ✘", "error" if self.stats['errores'] > 0 else "info")
        self._log(f"Duración:      {duracion:.2f} segundos", "info")
        self._log("", "info")
        
        if self.stats['errores'] == 0:
            self._log("✅ SINCRONIZACIÓN COMPLETADA CON ÉXITO", "success")
        else:
            self._log(f"⚠️ SINCRONIZACIÓN COMPLETADA CON {self.stats['errores']} ERRORES", "warning")
        
        self._log("", "info")
        return self.stats['errores'] == 0