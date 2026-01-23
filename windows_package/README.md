# Sistema de Sincronización PostgreSQL ↔ MySQL

## INSTALACIÓN Y USO

### Requisitos:
- Windows 7 o superior
- Python 3.8+ instalado
- Internet para instalar dependencias

### Pasos:

1. **Ejecutar el instalador:**
   ```
   INSTALAR_Y_EJECUTAR.bat
   ```

2. **Seleccionar opción 1** para configurar el sistema por primera vez
   - Ingresa credenciales de PostgreSQL
   - Ingresa credenciales de MySQL
   - Configura intervalo de sincronización

3. **Para sincronizar manualmente:**
   - Ejecuta `INSTALAR_Y_EJECUTAR.bat` nuevamente
   - Selecciona opción 2

## ARCHIVOS INCLUIDOS:

- `sync_system.py` - Ejecutable principal
- `smart_sync_complete.py` - Módulo de sincronización
- `INSTALAR_Y_EJECUTAR.bat` - Instala dependencias y ejecuta el sistema
- `README.md` - Este archivo
- `logs/` - Carpeta donde se guardan los logs de sincronización

## CARPETA DE LOGS:

El sistema crea automáticamente una carpeta `logs/` donde guarda un archivo `.txt` por cada ejecución:

**Formato del archivo:** `logs/sync_YYYYMMDD_HHMMSS.txt`

**Contenido del log:**
- 📅 Fecha y hora de inicio y fin
- 🏢 Datos de la empresa (RIF, email)
- ✅ Éxitos y ⚠️ Advertencias
- ❌ Errores detallados
- 📊 Estadísticas finales (cuántos registros se sincronizaron)

**Ejemplo:**
```
[2025-01-23 10:30:45] ✅ SUCCESS: Conectado a PostgreSQL
[2025-01-23 10:30:46] ✅ SUCCESS: Empresa encontrada: Mi Empresa (ID: 27)
[2025-01-23 10:30:47] ℹ️  INFO: Detectando cambios en products...
[2025-01-23 10:31:15] ✅ SUCCESS: 595 productos sincronizados
...
```

## MODOS DE EJECUCIÓN:

1. **Config** - Configuración inicial (GUI)
2. **Sync** - Sincronización única
3. **Service** - Modo servicio continuo (consola)
4. **Manager** - Interfaz de administración
5. **System Tray** ⭐ - Icono en barra de tareas (Transparente)

## MODO SYSTEM TRAY (Recomendado para producción):

**Características:**
- 🔵 Icono en la barra de tareas (junto al reloj)
- 👤 Usuario normal no ve ventanas (transparente)
- 📊 Clic izquierdo: Ver logs de sincronización
- ⚙️ Clic derecho: Menú de opciones
  - Ver Logs
  - Sincronizar Ahora
  - Configuración
  - Salir
- 💡 Tooltip dinámico al pasar el mouse
  - Estado actual
  - Última sincronización
  - RIF de la empresa

**Instalación de dependencias:**
```bash
pip install pystray Pillow
```

**Uso:**
```
INSTALAR_Y_EJECUTAR.bat → Opción 5
```

El sistema se iniciará automáticamente y sincronizará según el intervalo configurado.

## QUÉ HACE EL SISTEMA:

✅ Detecta cambios automáticamente usando hashes
✅ Sincroniza PostgreSQL → MySQL (products, customers, categories)
✅ Sincroniza MySQL → PostgreSQL (quotes como sales_operation)
✅ Se ejecuta cada X minutos (configurable)
✅ Maneja errores y reintentos automáticos
✅ **Guarda todos los logs en archivos .txt para auditoría**
