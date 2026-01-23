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

## MODOS DE EJECUCIÓN:

1. **Config** - Configuración inicial (GUI)
2. **Sync** - Sincronización única
3. **Service** - Modo servicio continuo
4. **Manager** - Interfaz de administración

## QUÉ HACE EL SISTEMA:

✅ Detecta cambios automáticamente usando hashes
✅ Sincroniza PostgreSQL → MySQL (products, customers, categories)
✅ Sincroniza MySQL → PostgreSQL (quotes como sales_operation)
✅ Se ejecuta cada X minutos (configurable)
✅ Maneja errores y reintentos automáticos
