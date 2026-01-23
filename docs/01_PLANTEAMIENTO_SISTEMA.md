# SISTEMA DE SINCRONIZACIÓN INTELIGENTE
## PostgreSQL → MySQL con Servicio de Windows

---

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema](#arquitectura)
3. [Componentes](#componentes)
4. [Flujo de Sincronización](#flujo)
5. [Instalación](#instalación)
6. [Uso](#uso)
7. [Mantenimiento](#mantenimiento)

---

## 1. RESUMEN EJECUTIVO

### Objetivo
Sistema automático que sincroniza datos de PostgreSQL a MySQL detectando cambios mediante **hash comparison** y almacenando el estado en una tabla de PostgreSQL.

### Entidades Sincronizadas
- ✅ Companies
- ✅ Categories (Departments)
- ✅ Products
- ✅ Customers (Clients)
- ✅ Sellers
- ✅ Users
- ✅ Quotes (MySQL → PostgreSQL, bidireccional)

### Características Principales
- 🔁 **Sincronización Automática**: Servicio de Windows con intervalo configurable
- 🎯 **Detección de Cambios**: Solo sincroniza lo modificado
- 🗄️ **Tabla de Hashes**: Estado guardado en PostgreSQL (tabla `sync_hashes`)
- 🖥️ **Interfaz de Administración**: SyncManager.exe para gestión visual
- 📊 **Logs Completos**: Registro de todas las operaciones
- ⚙️ **Reconfigurable**: Cambiar conexiones, intervalos, etc. sin reinstalar

---

## 2. ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────────────────┐
│                     Windows Server                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Servicio de Windows                                  │  │
│  │  PostgreSQLMySQLSyncService.exe                       │  │
│  │                                                        │  │
│  │  • Se inicia automáticamente al arrancar               │  │
│  │  • Ejecuta sync cada X tiempo (configurable)          │  │
│  │  • Reconexión automática si falla                     │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│                         ▼                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Módulo de Sincronización Inteligente                 │  │
│  │  smart_sync_complete.py                               │  │
│  │                                                        │  │
│  │  • Conecta a PostgreSQL y MySQL                       │  │
│  │  • Lee datos de PostgreSQL                            │  │
│  │  • Compara hashes en sync_hashes                      │  │
│  │  • Detecta: nuevos, modificados, eliminados           │  │
│  │  • Aplica cambios en MySQL                            │  │
│  │  • Actualiza sync_hashes                              │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                   │
│            ┌────────────┴────────────┐                    │
│            ▼                         ▼                    │
│  ┌─────────────────┐      ┌─────────────────┐            │
│  │   PostgreSQL    │      │      MySQL       │            │
│  │   (Origen)      │      │   (Destino)     │            │
│  │                 │      │                 │            │
│  │ • products      │      │ • products      │            │
│  │ • clients       │ ───► │ • customers     │            │
│  │ • department    │      │ • categories    │            │
│  │ • sellers       │      │ • sellers       │            │
│  │ • users         │      │ • users         │            │
│  │                 │      │ • companies     │            │
│  │ • sync_hashes   │ ◄─── │                 │            │
│  └─────────────────┘      └─────────────────┘            │
│                                                           │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  Interfaz de Administración (SyncManager.exe)         │ │
│  │                                                        │ │
│  │  • Estado del servicio (en ejecución/detenido)        │ │
│  │  • Iniciar/Detener/Reiniciar servicio                 │ │
│  │  • Ver logs en tiempo real                            │ │
│  │  • Forzar sincronización manual                        │ │
│  │  • Configurar intervalo                               │ │
│  │  • Reconfigurar conexiones                             │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 3. COMPONENTES

### 3.1 Base de Datos PostgreSQL

#### Tabla `sync_hashes` (Nueva)
```sql
CREATE TABLE sync_hashes (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_key VARCHAR(100) NOT NULL,
    record_hash VARCHAR(32) NOT NULL,
    last_sync_data JSONB,
    synced_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    company_id INTEGER,
    UNIQUE(table_name, record_key, company_id)
);

CREATE INDEX idx_sync_hashes_lookup ON sync_hashes(table_name, record_key, company_id);
```

**Propósito**: Guardar el hash MD5 de cada registro sincronizado para detectar cambios.

### 3.2 Módulos Python

#### smart_sync_complete.py
Módulo principal que:
- Crea tabla `sync_hashes` si no existe
- Implementa detección de cambios por hash
- Sincroniza: products, customers, sellers, categories
- Maneja logs

#### sync_service.py
Servicio de Windows que:
- Se registra como servicio del sistema
- Se ejecuta en segundo plano
- Llama a `smart_sync_complete.py` periódicamente
- Maneja inicio/parada del servicio

#### sync_manager.py
Interfaz Tkinter que:
- Muestra estado del servicio
- Permite iniciar/detener servicio
- Muestra logs en tiempo real
- Permite reconfigurar

#### sync_config.json
Archivo de configuración:
```json
{
  "postgresql": {
    "host": "localhost",
    "database": "logmobil",
    "user": "postgres",
    "password": "encrypted"
  },
  "mysql": {
    "host": "localhost",
    "database": "sistema_ventas",
    "user": "root",
    "password": "encrypted"
  },
  "company": {
    "rif": "V123456789",
    "email": "empresa@ejemplo.com"
  },
  "sync": {
    "interval_seconds": 3600,
    "autostart": true,
    "entities": {
      "products": true,
      "customers": true,
      "sellers": true,
      "categories": true
    }
  }
}
```

### 3.3 Instalador

#### setup.exe
Creado con Inno Setup que:
- Compila todos los archivos
- Crea servicio de Windows
- Configura conexiones
- Ejecuta primera sincronización
- Instala interfaz de administración

---

## 4. FLUJO DE SINCRONIZACIÓN

### 4.1 Primera Ejecución

```
┌─────────────────────────────────────┐
│  Instalador setup.exe se ejecuta    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Usuario ingresa credenciales       │
│  • PostgreSQL                       │
│  • MySQL                            │
│  • Empresa (RIF, Email)             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Crear tabla sync_hashes en PG      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  MIGRACIÓN COMPLETA INICIAL         │
│  • Sincronizar TODOS los datos      │
│  • Generar hash de cada registro    │
│  • Guardar en sync_hashes           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Iniciar servicio de Windows        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  ✅ Sistema listo y funcionando     │
└─────────────────────────────────────┘
```

### 4.2 Ejecuciones Posteriores (Ciclo de Sync)

```
┌─────────────────────────────────────────────────────────────┐
│  Servicio se ejecuta cada X minutos                        │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Para cada entidad (products, customers, etc):             │
│                                                             │
│  1. Leer TODOS los registros de PostgreSQL                 │
│     SELECT * FROM products                                  │
│                                                             │
│  2. Para cada registro:                                    │
│     • Calcular hash MD5 con campos clave                   │
│     • Buscar en sync_hashes:                                │
│       - Si NO existe → NUEVO                                │
│       - Si existe y hash ≠ → MODIFICADO                     │
│       - Si existe y hash = → Sin cambios                    │
│                                                             │
│  3. Detectar eliminados:                                   │
│     SELECT FROM sync_hashes                                │
│     WHERE record_key NOT IN (registros actuales)           │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Aplicar cambios en MySQL:                                 │
│  • INSERT nuevos                                           │
│  • UPDATE modificados                                      │
│  • DELETE eliminados (opcional)                            │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Actualizar sync_hashes:                                   │
│  • INSERT/UPDATE hash de cada registro procesado           │
│  • DELETE hashes de eliminados                             │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  Guardar log y esperar próximo ciclo                       │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Ejemplo: Detección de Cambios en Products

**PostgreSQL.products (10:00 AM)**:
```
code    | description   | price
---------|---------------|-------
PROD001  | Laptop HP     | 500
PROD002  | Mouse         | 20
```

**sync_hashes después de sync (10:00 AM)**:
```
table_name | record_key | record_hash
-----------|------------|-------------
products   | PROD001    | abc123...
products   | PROD002    | def456...
```

**PostgreSQL.products (11:00 AM - CAMBIOS)**:
```
code    | description   | price
---------|---------------|-------
PROD001  | Laptop HP     | 550  ← MODIFICADO (precio cambió)
PROD002  | Mouse         | 20
PROD003  | Keyboard      | 80   ← NUEVO
PROD004  | (borrado)           ← ELIMINADO
```

**Detección (11:00 AM)**:
```
PROD001:
  Hash actual: xyz789... (con precio 550)
  Hash guardado: abc123... (con precio 500)
  → ¡DIFERENTE! → MODIFICADO

PROD002:
  Hash actual: def456...
  Hash guardado: def456...
  → IGUAL → Sin cambios

PROD003:
  Hash actual: ghi012...
  Buscar en sync_hashes: NO EXISTE
  → ¡NUEVO!

PROD004:
  Existe en sync_hashes pero NO en PostgreSQL
  → ¡ELIMINADO!
```

**Resultado**:
- Nuevos: 1 (PROD003)
- Modificados: 1 (PROD001)
- Eliminados: 1 (PROD004)
- Sin cambios: 1 (PROD002)

**Sincronización a MySQL**:
```sql
INSERT INTO products ... PROD003
UPDATE products SET price = 550 WHERE code = 'PROD001'
DELETE FROM products WHERE code = 'PROD004'

UPDATE sync_hashes SET record_hash = 'xyz789...' WHERE record_key = 'PROD001'
INSERT INTO sync_hashes ... PROD003
DELETE FROM sync_hashes WHERE record_key = 'PROD004'
```

---

## 5. INSTALACIÓN

### 5.1 Requisitos Previos

- Windows 10/11 o Windows Server 2016+
- Python 3.9+ con pywin32
- PostgreSQL accesible
- MySQL accesible
- Permisos de Administrador

### 5.2 Pasos de Instalación

1. **Ejecutar setup.exe**
2. **Configurar conexiones**
   - Host PostgreSQL
   - Database PostgreSQL
   - User/Pass PostgreSQL
   - Host MySQL
   - Database MySQL
   - User/Pass MySQL
3. **Configurar empresa**
   - RIF
   - Email
   - Nombre
4. **Configurar sincronización**
   - Intervalo (5 min, 15 min, 30 min, 1 hora, 2 horas)
   - Entidades a sincronizar
5. **Instalar**
   - El instalador:
     - Crea tabla `sync_hashes`
     - Ejecuta migración completa
     - Registra servicio de Windows
     - Inicia servicio
6. **Finalizar**

### 5.3 Verificación

```
1. Abrir services.msc
2. Buscar "Sincronizador PostgreSQL a MySQL"
3. Verificar estado: "En ejecución"
4. Abrir SyncManager.exe
5. Ver logs en tiempo real
```

---

## 6. USO

### 6.1 SyncManager.exe - Interfaz de Administración

**Pestaña "Estado"**
- Estado del servicio (🟢 En ejecución / 🔴 Detenido)
- Última sincronización
- Próxima sincronización
- Total de registros por entidad

**Pestaña "Controles"**
- ▶️ Iniciar servicio
- ⏸️ Detener servicio
- 🔄 Reiniciar servicio
- ⚡ Sincronizar ahora
- 📋 Ver logs

**Pestaña "Configuración"**
- Cambiar credenciales
- Cambiar intervalo
- Activar/desactivar entidades
- Guardar y reiniciar

**Pestaña "Logs"**
- Ver logs en tiempo real
- Filtrar por tipo/nivel
- Exportar a archivo
- Limpiar logs

### 6.2 Reconfiguración

**Sin reinstalar**:
1. Abrir SyncManager.exe
2. Ir a "Configuración"
3. Modificar valores
4. Probar conexiones
5. Guardar
6. Reiniciar servicio (opcional, se aplica en próximo ciclo)

---

## 7. MANTENIMIENTO

### 7.1 Logs

**Ubicación**:
```
C:\Program Files\PostgreSQLMySQLSync\logs\
├── sync_service_2025_01_22.log
├── sync_service_2025_01_21.log
└── ...
```

**Rotación**: Automatic creationhouse, se crea nuevo archivo cada día.

### 7.2 Backup de sync_hashes

**Opción 1: SQL**
```sql
-- Backup completo
COPY sync_hashes TO '/tmp/sync_hashes_backup.csv' CSV HEADER;

-- Restore
COPY sync_hashes FROM '/tmp/sync_hashes_backup.csv' CSV HEADER;
```

**Opción 2: Desde SyncManager**
- Botón "Exportar hashes"
- Guarda archivo JSON con todos los hashes

### 7.3 Forzar Resincronización Completa

**Método 1: Desde SyncManager**
```
1. Ir a "Mantenimiento"
2. Click en "Resetear hashes"
3. Confirmar
4. Reiniciar servicio
```

**Método 2: SQL**
```sql
DELETE FROM sync_hashes WHERE company_id = 1;
```

**Resultado**: Próxima sincronización migrará TODO desde cero.

### 7.4 Monitoreo

**Métricas a monitorear**:
- Tiempo de sincronización (debería ser < 5 min)
- Cantidad de cambios por ciclo
- Errores de conexión
- Espacio en disco (logs)

**Alertas recomendadas**:
- Si sync falla más de 3 veces consecutivas
- Si tiempo de sync > 15 minutos
- Si logs ocupan > 1GB

### 7.5 Solución de Problemas

**Problema: Servicio no inicia**
```
Solución:
1. Verificar logs en: sync_service.log
2. Verificar credenciales en sync_config.json
3. Probar conexiones manualmente
4. Reinstalar servicio: sync_service.py reinstall
```

**Problema: No sincroniza**
```
Solución:
1. Verificar que sync_hashes existe
2. Verificar company_id correcto
3. Forzar sync manual desde SyncManager
4. Revisar logs para ver errores
```

**Problema: Excesivo consumo de memoria**
```
Solución:
1. Reducir frecuencia de sync
2. Optimizar queries (agregar índices)
3. Aumentar RAM del servidor
```

---

## 8. ESTRUCTURA DE ARCHIVOS

```
PostgreSQLMySQL_Sync/
│
├── setup.exe                          ← Instalador principal
│
├── 📁 Servicios/
│   ├── PostgreSQLMySQLSyncService.exe ← Servicio Windows
│   └── sync_service.log               ← Logs del servicio
│
├── 📁 Aplicación/
│   ├── SyncManager.exe                ← Interfaz gráfica
│   ├── smart_sync_complete.py         ← Módulo de sync
│   └── sync_service.py               ← Servicio Windows
│
├── 📁 Configuración/
│   ├── sync_config.json              ← Config principal
│   ├── .env                          ← Credenciales (encriptadas)
│   └── sync_hashes_backup.json       ← Backup hashes
│
├── 📁 Logs/
│   ├── sync_service_2025_01_22.log
│   └── ...
│
├── 📁 SQL/
│   ├── 01_create_sync_hashes.sql     ← Crear tabla
│   ├── 02_view_sync_status.sql       ← Consultas útiles
│   └── 03_reset_sync_hashes.sql      ← Resetear sync
│
└── 📁 Documentación/
    ├── Manual_de_Instalacion.pdf
    ├── Manual_de_Usuario.pdf
    └── Solucion_de_Problemas.pdf
```

---

## 9. SCRIPTS SQL

### 9.1 Crear Tabla sync_hashes

```sql
-- Archivo: SQL/01_create_sync_hashes.sql

CREATE TABLE IF NOT EXISTS sync_hashes (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_key VARCHAR(100) NOT NULL,
    record_hash VARCHAR(32) NOT NULL,
    last_sync_data JSONB,
    synced_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    company_id INTEGER,
    UNIQUE(table_name, record_key, company_id)
);

CREATE INDEX IF NOT EXISTS idx_sync_hashes_lookup
    ON sync_hashes(table_name, record_key, company_id);

CREATE INDEX IF NOT EXISTS idx_sync_hashes_table
    ON sync_hashes(table_name, company_id);

COMMENT ON TABLE sync_hashes IS 'Almacena hashes MD5 para detectar cambios en sincronización';
COMMENT ON COLUMN sync_hashes.table_name IS 'Nombre de la tabla (products, customers, etc.)';
COMMENT ON COLUMN sync_hashes.record_key IS 'Clave única del registro (code, etc.)';
COMMENT ON COLUMN sync_hashes.record_hash IS 'Hash MD5 para detectar cambios';
COMMENT ON COLUMN sync_hashes.last_sync_data IS 'Datos completos del registro (opcional)';
```

### 9.2 Consultar Estado de Sincronización

```sql
-- Archivo: SQL/02_view_sync_status.sql

-- Resumen de sincronización
SELECT
    table_name,
    COUNT(*) as total_registros,
    MAX(updated_at) as ultima_sync,
    MIN(updated_at) as primera_sync
FROM sync_hashes
WHERE company_id = 1
GROUP BY table_name
ORDER BY table_name;

-- Productos no sincronizados
SELECT
    p.code,
    p.description,
    p.price
FROM products p
LEFT JOIN sync_hashes sh
    ON sh.record_key = p.code
    AND sh.table_name = 'products'
    AND sh.company_id = 1
WHERE sh.id IS NULL
LIMIT 10;

-- Últimos cambios sincronizados
SELECT
    table_name,
    record_key,
    updated_at
FROM sync_hashes
WHERE company_id = 1
ORDER BY updated_at DESC
LIMIT 20;
```

### 9.3 Resetear Sincronización

```sql
-- Archivo: SQL/03_reset_sync_hashes.sql

-- ⚠️ CUIDADO: Esto borrará todos los hashes
-- La próxima sync será completa desde cero

DELETE FROM sync_hashes
WHERE company_id = 1;

-- Verificar que se borró
SELECT COUNT(*) FROM sync_hashes WHERE company_id = 1;
-- Resultado: 0
```

---

## 10. PRÓXIMOS PASOS

1. ✅ Crear estructura de directorios
2. ✅ Implementar `smart_sync_complete.py`
3. ✅ Implementar `sync_service.py`
4. ✅ Implementar `sync_manager.py`
5. ✅ Crear scripts SQL
6. ✅ Crear instalador Inno Setup
7. ⏳ Probar instalación completa
8. ⏳ Documentación de usuario
9. ⏳ Deploy a producción

---

**Versión**: 1.0
**Fecha**: 2025-01-22
**Autor**: Sistema de Sincronización PostgreSQL → MySQL
