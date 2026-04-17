# Integración PostgreSQL → n8n

Sistema de sincronización en tiempo real de PostgreSQL a n8n mediante LISTEN/NOTIFY.

## 📋 Arquitectura

```
PostgreSQL (Triggers)
    ↓ LISTEN/NOTIFY
Python Bridge
    ↓ HTTP POST
n8n Workflow
    ↓ HTTP POST
API Laravel / Otros servicios
```

## 🚀 Instalación Rápida

### 1. Crear Triggers en PostgreSQL

```bash
psql -U postgres -d tu_base_de_datos -f create_triggers_n8n_integration.sql
```

Esto creará triggers en las siguientes tablas:
- `products`
- `clients` (clientes)
- `sellers` (vendedores)
- `sales_operations` (ventas)

### 2. Configurar Python Bridge

```bash
# Copiar archivo de configuración de ejemplo
cp bridge_config.json.example bridge_config.json

# Editar configuración
nano bridge_config.json
```

Configura:
```json
{
  "postgresql": {
    "host": "localhost",
    "port": 5432,
    "database": "tu_base_de_datos",
    "user": "tu_usuario",
    "password": "tu_password"
  },
  "n8n": {
    "webhook_url": "https://tu-n8n-server.com/webhook/postgres-changes",
    "timeout": 10
  }
}
```

### 3. Instalar Dependencias Python

```bash
pip install psycopg2-binary requests
```

O desde requirements.txt:
```bash
pip install -r requirements.txt
```

### 4. Importar Workflow en n8n

1. En n8n, ve a: **Workflows** → **Import from File**
2. Selecciona: `n8n_workflow_postgresql_integration.json`
3. Actualiza las URLs de los nodos HTTP Request:
   - Cambia `https://tu-api.com/...` por tu API real
   - Configura las credenciales de autenticación

### 5. Iniciar Python Bridge

```bash
python python_bridge_n8n.py
```

Verás:
```
======================================================================
🚀 INICIANDO POSTGRESQL → n8n BRIDGE
======================================================================
✅ Configuración cargada desde bridge_config.json
✅ Conectado a PostgreSQL: tu_base_de_datos
🔊 Escuchando notificaciones 'n8n_sync'...
```

### 6. Probar

En otra terminal, ejecuta:

```sql
-- Test INSERT
INSERT INTO products (name, price) VALUES ('Test Product', 100);

-- Test UPDATE
UPDATE products SET price = 150 WHERE name = 'Test Product';

-- Test DELETE
DELETE FROM products WHERE name = 'Test Product';
```

Verás las notificaciones en el log del bridge:
```
📨 Notificación recibida:
   Tabla: products
   Operación: INSERT
   Record ID: 123
📤 Enviando a n8n...
✅ Enviado a n8n exitosamente
```

## 📁 Archivos

- **`create_triggers_n8n_integration.sql`**: Triggers PostgreSQL con LISTEN/NOTIFY
- **`python_bridge_n8n.py`**: Servicio que escucha notificaciones y envía a n8n
- **`bridge_config.json.example`**: Ejemplo de configuración del bridge
- **`bridge_config.json`**: Tu configuración real (crear desde el example)
- **`n8n_workflow_postgresql_integration.json`**: Workflow para importar en n8n
- **`bridge_n8n.log`**: Log de ejecución del bridge

## 🔄 Flujo de Datos

### PostgreSQL Trigger

Cuando ocurre INSERT/UPDATE/DELETE en una tabla monitoreada:

```sql
CREATE TRIGGER products_n8n_trigger
AFTER INSERT OR UPDATE OR DELETE ON products
FOR EACH ROW
EXECUTE FUNCTION notify_table_changes();
```

El trigger ejecuta:

```sql
PERFORM pg_notify('n8n_sync', json_build_object(
    'table_name', 'products',
    'operation', 'INSERT',
    'record_id', NEW.id,
    'timestamp', now()
)::text);
```

### Python Bridge

1. Se conecta a PostgreSQL
2. Ejecuta `LISTEN n8n_sync`
3. Espera notificaciones (sin consumir CPU)
4. Cuando llega una notificación:
   - Parsea el JSON
   - Obtiene los datos completos del registro
   - Envía al webhook de n8n

### n8n Workflow

1. **Webhook Trigger**: Recibe la notificación
2. **Log**: Registra la operación
3. **Switch**: Routea según la tabla (products, clients, sellers, sales)
4. **HTTP Request**: Llama a la API correspondiente
5. **Response**: Responde al bridge con éxito/error

## ⚙️ Configuración Avanzada

### Agregar Más Tablas

1. Agrega trigger en `create_triggers_n8n_integration.sql`:

```sql
DROP TRIGGER IF EXISTS nueva_tabla_n8n_trigger ON nueva_tabla;

CREATE TRIGGER nueva_tabla_n8n_trigger
AFTER INSERT OR UPDATE OR DELETE ON nueva_tabla
FOR EACH ROW
EXECUTE FUNCTION notify_table_changes();
```

2. Agrega mapeo en `python_bridge_n8n.py`:

```python
self.table_mappings = {
    # ... tablas existentes ...
    'nueva_tabla': {
        'primary_key': 'id',
        'columns': ['id', 'campo1', 'campo2', 'company_id']
    }
}
```

3. Agrega rama en workflow n8n:
   - Agregar opción al Switch
   - Agregar nodo Set para preparar datos
   - Agregar nodo HTTP Request

### Ejecutar como Servicio en Windows

Crear archivo `install_service.bat`:

```batch
@echo off
echo Instalando Python Bridge como servicio de Windows...

sc create PostgreSQLN8nBridge ^
  binPath= "C:\Python39\python.exe C:\ruta\python_bridge_n8n.py" ^
  DisplayName= "PostgreSQL to n8n Bridge" ^
  start= auto

sc start PostgreSQLN8nBridge

echo Servicio instalado e iniciado.
pause
```

### Ejecutar como Servicio en Linux

Crear `/etc/systemd/system/postgresql-n8n-bridge.service`:

```ini
[Unit]
Description=PostgreSQL to n8n Bridge
After=network.target postgresql.service

[Service]
Type=simple
User=tu_usuario
WorkingDirectory=/ruta/al/proyecto
ExecStart=/usr/bin/python3 /ruta/al/proyecto/python_bridge_n8n.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Instalar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable postgresql-n8n-bridge
sudo systemctl start postgresql-n8n-bridge
```

## 🐛 Troubleshooting

### El bridge no recibe notificaciones

1. **Verifica que los triggers estén creados**:
   ```sql
   SELECT tgname, tgrelid::regclass
   FROM pg_trigger
   WHERE tgname LIKE '%_n8n_trigger';
   ```

2. **Verifica la conexión a PostgreSQL**:
   - Revisa `bridge_config.json`
   - Prueba conectar manualmente con `psql`

3. **Verifica el log**:
   ```bash
   tail -f bridge_n8n.log
   ```

### n8n no recibe los webhooks

1. **Verifica la URL del webhook**:
   - En n8n, haz clic en el nodo Webhook
   - Copia "Test URL" o "Production URL"
   - Actualiza `bridge_config.json`

2. **Prueba el webhook con curl**:
   ```bash
   curl -X POST https://tu-n8n.com/webhook/postgres-changes \
     -H "Content-Type: application/json" \
     -d '{"table_name":"test","operation":"INSERT","record_id":1}'
   ```

3. **Verifica logs de n8n**:
   - Revisa la ejecución del workflow
   - Verifica que no haya errores en los nodos HTTP Request

### Error: "Table not mapped"

1. **Agrega la tabla a `table_mappings`** en `python_bridge_n8n.py`
2. **Reinicia el bridge**

### Performance

El bridge consume muy poca CPU:
- Usa `select()` con timeout de 5 segundos
- Solo se activa cuando hay notificaciones
- No hace polling

Memoria típica: ~30-50 MB

## 📊 Monitoreo

### Ver Estadísticas

El bridge imprime estadísticas al detenerse:

```
======================================================================
📊 ESTADÍSTICAS:
   Tiempo ejecutando: 2:34:56
   Notificaciones recibidas: 1,234
   Notificaciones enviadas: 1,230
   Notificaciones fallidas: 4
======================================================================
```

### Logs

- **Bridge**: `bridge_n8n.log`
- **n8n**: Ver logs de ejecución del workflow

## 🔐 Seguridad

### HTTPS

Si tu n8n usa HTTPS con certificado autofirmado, el bridge puede fallar. Soluciones:

1. **Usar certificado válido** (recomendado)
2. **Desactivar verificación** (solo para desarrollo):

   En `python_bridge_n8n.py`, modifica:

   ```python
   response = requests.post(
       webhook_url,
       json=payload,
       verify=False  # ⚠️ Solo para desarrollo
   )
   ```

### Autenticación

Agrega headers de autenticación en `python_bridge_n8n.py`:

```python
response = requests.post(
    webhook_url,
    json=payload,
    headers={
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_TOKEN',
        'X-API-Key': 'your-api-key'
    }
)
```

## 🚀 Próximos Pasos

1. **Ejecutar como servicio** en producción
2. **Agregar más tablas** según necesites
3. **Implementar reintentos** en caso de fallo
4. **Agregar buffer/cola** si hay muchos cambios
5. **Monitor** con Grafana/Prometheus

## 📝 Licencia

Este código es parte del proyecto Sincronizador Chrystal.
