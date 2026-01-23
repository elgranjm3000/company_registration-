# 🚀 GUÍA DE COMPILACIÓN E INSTALACIÓN
## Sistema de Sincronización PostgreSQL → MySQL

---

## 📋 REQUISITOS PREVIOS

### En la máquina de desarrollo:
- ✅ Python 3.9+
- ✅ PyInstaller
- ✅ Inno Setup (para crear instalador)
- ✅ pywin32

```bash
pip install pyinstaller pywin32 python-dotenv psycopg2-binary mysql-connector-python
```

### En el servidor Windows:
- ✅ Windows 10/11 o Windows Server 2016+
- ✅ PostgreSQL accesible
- ✅ MySQL accesible
- ✅ Permisos de Administrador

---

## 🔨 PASO 1: COMPILAR A .EXE

### 1.1 Instalar dependencias

```bash
pip install pyinstaller pywin32 python-dotenv
pip install psycopg2-binary mysql-connector-python bcrypt
```

### 1.2 Crear archivo .env

Crea un archivo `.env` en la raíz del proyecto:

```env
# PostgreSQL
DB_HOST=localhost
DB_DATABASE=logmobil
DB_USER=postgres
DB_PASSWORD=tu_password_postgresql

# MySQL
DB_HOST_MYSQL=localhost
DB_PORT_DATABASE_MYSQL=sistema_ventas
DB_USER_MYSQL=root
DB_PASSWORD_MYSQL=tu_password_mysql

# Empresa
RIF=V123456789
EMAIL=empresa@ejemplo.com
COMPANY_NOMBRE=Mi Empresa C.A.

# Intervalo (opcional)
SYNC_INTERVAL_SECONDS=3600
```

### 1.3 Compilar

**Opción A: Usar el script (Recomendado)**
```bash
build.bat
```

**Opción B: Manualmente**
```bash
# Servicio Windows
pyinstaller --onefile --noconsole ^
    --hidden-import=win32timezone ^
    --hidden-import=win32service ^
    --hidden-import=win32serviceutil ^
    --name="PostgreSQLMySQLSyncService" ^
    sync_service.py

# Interfaz de administración
pyinstaller --onefile --windowed ^
    --name="SyncManager" ^
    sync_manager.py
```

### 1.4 Verificar compilación

Deberías ver estos archivos:
```
dist/
├── PostgreSQLMySQLSyncService.exe  ← Servicio Windows (~15 MB)
└── SyncManager.exe                   ← Interfaz (~12 MB)
```

---

## 📦 PASO 2: CREAR INSTALADOR (OPCIONAL)

### 2.1 Instalar Inno Setup

Descargar e instalar desde: https://jrsoftware.org/isdl.php

### 2.3 Crear instalador

**Opción A: Usar el script**
```bash
create_installer.bat
```

**Opción B: Manualmente**
```bash
iscc setup.iss
```

### 2.4 Resultado

```
output/
└── setup_sync_service.exe  ← Instalador completo (~30 MB)
```

---

## 💻 PASO 3: INSTALAR EN SERVIDOR

### Opción A: Usar el instalador (Recomendado)

1. **Copiar `setup_sync_service.exe` al servidor**
2. **Ejecutar como Administrador**
3. **Seguir el asistente:**
   - Aceptar licencia
   - Configurar conexiones a bases de datos
   - Seleccionar intervalo de sincronización
   - Finalizar instalación

4. **Verificar instalación:**
   - Abrir Sync Manager desde el escritorio
   - Verificar que el servicio está "En ejecución"

### Opción B: Instalación manual

1. **Crear carpeta de instalación:**
   ```
   C:\Program Files\PostgreSQLMySQLSync\
   ```

2. **Copiar archivos:**
   - `PostgreSQLMySQLSyncService.exe`
   - `SyncManager.exe`
   - `.env`
   - `smart_sync_complete.py`
   - `smart_sellers_sync_module.py`
   - `sql\` (carpeta con scripts)

3. **Instalar el servicio:**
   ```bash
   # Abrir CMD como Administrador
   cd "C:\Program Files\PostgreSQLMySQLSync"
   PostgreSQLMySQLSyncService.exe install
   ```

4. **Iniciar el servicio:**
   ```bash
   PostgreSQLMySQLSyncService.exe start
   ```

5. **Verificar:**
   - Abrir `services.msc`
   - Buscar "Sincronizador PostgreSQL a MySQL"
   - Verificar estado: "En ejecución"

---

## ✅ PASO 4: VERIFICAR FUNCIONAMIENTO

### 4.1 Abrir Sync Manager

Ejecutar `SyncManager.exe` o desde el acceso directo en el escritorio.

**Pestaña "Estado":**
- Estado: 🟢 EN EJECUCIÓN
- Última sincronización: [fecha/hora]
- Intervalo: 1 hora

### 4.2 Ver logs

**Pestaña "Logs":**
- Click en "🔄 Refrescar"
- Deberías ver:
  ```
  [2025-01-22 10:30:15] ℹ️ INFO: === INICIANDO SERVICIO DE SINCRONIZACIÓN ===
  [2025-01-22 10:30:16] ✅ ÉXITO: Tabla sync_hashes lista
  [2025-01-22 10:30:17] ℹ️ INFO: Detectando cambios en products...
  [2025-01-22 10:30:20] ℹ️ INFO: Products: 0 nuevos, 0 modificados, 0 eliminados
  [2025-01-22 10:30:25] ✅ ÉXITO: SINCRONIZACIÓN COMPLETADA CON ÉXITO
  ```

### 4.3 Forzar sincronización manual

**Pestaña "Controles":**
- Click en "⚡ Sincronizar Ahora"
- Esperar a que finalice
- Verificar logs

### 4.4 Verificar en MySQL

```sql
-- Verificar products sincronizados
SELECT COUNT(*) FROM products WHERE company_id = 1;

-- Verificar customers sincronizados
SELECT COUNT(*) FROM customers WHERE company_id = 1;
```

---

## 🔧 PASO 5: CONFIGURACIÓN ADICIONAL

### 5.1 Cambiar intervalo de sincronización

**Desde Sync Manager:**
1. Ir a pestaña "⚙️ Configuración"
2. Seleccionar nuevo intervalo
3. Click en "💾 Aplicar Intervalo"
4. Reiniciar servicio

**O editar .env directamente:**
```env
SYNC_INTERVAL_SECONDS=1800  # 30 minutos
```

Luego reiniciar el servicio.

### 5.2 Reconfigurar conexiones

1. **Editar archivo `.env`:**
   ```
   C:\Program Files\PostgreSQLMySQLSync\.env
   ```

2. **Modificar valores:**
   ```env
   DB_HOST=nuevo_host_postgresql
   DB_PASSWORD=nuevo_password
   ```

3. **Reiniciar servicio:**
   ```bash
   PostgreSQLMySQLSyncService.exe stop
   PostgreSQLMySQLSyncService.exe start
   ```

### 5.3 Verificar tabla sync_hashes en PostgreSQL

```sql
-- Verificar que la tabla existe
SELECT COUNT(*) FROM sync_hashes;

-- Ver resumen por tabla
SELECT
    table_name,
    COUNT(*) as total_registros,
    MAX(updated_at) as ultima_sync
FROM sync_hashes
WHERE company_id = 1
GROUP BY table_name;
```

---

## 📊 PASO 6: MONITOREO

### 6.1 Logs de servicio

**Ubicación:**
```
C:\Program Files\PostgreSQLMySQLSync\sync_service.log
```

**Ver en tiempo real:**
```powershell
Get-Content sync_service.log -Wait
```

### 6.2 Event Viewer de Windows

```
eventvwr.msc
→ Windows Logs → Application
→ Buscar "PostgreSQLMySQLSync"
```

### 6.3 Sync Manager

Abrir `SyncManager.exe` periodicamente para verificar:
- Estado del servicio
- Última sincronización
- Logs recientes

---

## 🛠️ SOLUCIÓN DE PROBLEMAS

### Problema: Servicio no inicia

**Síntoma:**
- Estado: 🔴 DETENIDO
- Logs muestran error de conexión

**Solución:**
1. Verificar `.env` tiene credenciales correctas
2. Probar conexiones manualmente:
   ```python
   import psycopg2
   import mysql.connector

   # PostgreSQL
   conn = psycopg2.connect(host="...", database="...", user="...", password="...")
   # MySQL
   conn = mysql.connector.connect(host="...", database="...", user="...", password="...")
   ```
3. Verificar firewalls permitan conexiones

### Problema: No sincroniza nada

**Síntoma:**
- Servicio está en ejecución
- Logs muestran "0 nuevos, 0 modificados"

**Causa posible:**
- Tabla `sync_hashes` está vacía (primera vez)
- Todavía se está ejecutando primera sincronización

**Solución:**
- Forzar sincronización manual desde Sync Manager
- Verificar logs para ver progreso

### Problema: Error "No se pudo obtener company_id"

**Síntoma:**
- Logs muestran: "No se encontró company_id"

**Solución:**
1. Verificar que `RIF` y `EMAIL` en `.env` son correctos
2. Verificar que existe en tabla `acceso` de MySQL:
   ```sql
   SELECT * FROM acceso WHERE codigo = 'V123456789';
   ```

### Problema: Excesivo consumo de CPU

**Síntoma:**
- Servicio usa más del 50% de CPU

**Causa:**
- Intervalo de sincronización muy corto (ej: 5 minutos)
- Muchos datos que sincronizar

**Solución:**
- Aumentar intervalo a 1 hora o más
- Optimizar queries (agregar índices en PostgreSQL)

---

## 📋 MANTENIMIENTO

### Rotación de logs

El archivo `sync_service.log` crece indefinidamente. Configurar rotación:

**Opción 1: Manualmente**
- Cada mes, renombrar el archivo:
  ```bash
  sync_service.log → sync_service_2025_01.log
  ```
- El servicio creará uno nuevo automáticamente

**Opción 2: Usar logrotate (Windows con Cygwin)**
```
C:\cygwin64\etc\logrotate.d\sync_service
```

### Backup de sync_hashes

```sql
-- Backup completo
COPY sync_hashes TO 'C:\backup\sync_hashes_backup.csv' CSV HEADER;

-- Restaurar
COPY sync_hashes FROM 'C:\backup\sync_hashes_backup.csv' CSV HEADER;
```

### Actualización del servicio

**Para actualizar a una nueva versión:**

1. **Detener servicio:**
   ```bash
   PostgreSQLMySQLSyncService.exe stop
   ```

2. **Reemplazar ejecutable:**
   ```
   C:\Program Files\PostgreSQLMySQLSync\PostgreSQLMySQLSyncService.exe
   ```

3. **Iniciar servicio:**
   ```bash
   PostgreSQLMySQLSyncService.exe start
   ```

---

## 📚 REFERENCIAS

### Archivos del sistema

```
C:\Program Files\PostgreSQLMySQLSync\
├── PostgreSQLMySQLSyncService.exe  ← Servicio
├── SyncManager.exe                   ← Interfaz
├── .env                              ← Configuración
├── sync_service.log                  ← Logs
├── smart_sync_complete.py            ← Módulo
└── sql\                              ← Scripts SQL
```

### Comandos del servicio

```bash
# Instalar
PostgreSQLMySQLSyncService.exe install

# Iniciar
PostgreSQLMySQLSyncService.exe start

# Detener
PostgreSQLMySQLSyncService.exe stop

# Reiniciar
PostgreSQLMySQLSyncService.exe restart

# Desinstalar
PostgreSQLMySQLSyncService.exe remove
```

### Consultas útiles

Ver scripts en `sql/02_queries_utilidades.sql`

---

## ✅ CHECKLIST FINAL

Antes de considerar el sistema en producción:

- [ ] Servicio instalado y en ejecución
- [ ] Primera sincronización completada exitosamente
- [ ] Sync Manager funciona correctamente
- [ ] Logs no muestran errores
- [ ] Intervalo configurado correctamente
- [ ] Backup de sync_hashes realizado
- [ ] Documentación entregada al cliente
- [ ] Usuario final capacitado en Sync Manager

---

**Versión:** 1.0
**Fecha:** 2025-01-22
**Soporte:** Consultar documentación en `docs/`
