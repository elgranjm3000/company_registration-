# 🚀 Inicio Rápido - Sync API System Windows

## Primera vez que usas el sistema

### Paso 1: Instalar dependencias
Doble clic en:
```
INSTALAR_Y_EJECUTAR.bat
```
o
```
VERIFICAR_DEPENDENCIAS.bat
```

### Paso 2: Configurar el sistema
Doble clic en:
```
CONFIGURAR.bat
```

Completa los datos de:
- API REST (URL, email)
- Empresa (RIF, email)
- PostgreSQL (host, puerto, base de datos, usuario, contraseña)

### Paso 3: Ejecutar

**✨ AUTOMÁTICO (Después de Configurar)**

Cuando guardas la configuración por primera vez, el sistema **automáticamente**:

1. **Verifica la conexión** con PostgreSQL (3 pasos de verificación)
2. **Ejecuta la primera sincronización** completa (muestra progreso)
3. **Inicia el modo System Tray** en la barra de tareas

**No necesitas hacer nada más** - el sistema se inicia automáticamente.

---

**Opciones Manuales (Solo si necesitas):**

**Opción A: Modo Administrador**
```
Doble clic en: MANAGER.bat
```

**Opción B: Modo System Tray**
```
Doble clic en: TRAY.bat
```
El icono aparecerá en la barra de tareas (junto al reloj)

**Opción C: Sincronización única**
```
Doble clic en: EJECUTAR.bat
```

## Modos de ejecución disponibles

| Archivo .bat | Descripción |
|--------------|-------------|
| **INSTALAR_Y_EJECUTAR.bat** | Instala dependencias y muestra menú |
| **VERIFICAR_DEPENDENCIAS.bat** | Verifica/instala dependencias |
| **CONFIGURAR.bat** | Configura el sistema (primera vez) |
| **MANAGER.bat** | Abre ventana del administrador |
| **TRAY.bat** | Inicia en modo System Tray (transparente) |
| **EJECUTAR.bat** | Sincroniza una vez (consola) |
| **DEBUG.bat** | Modo debug con logs detallados |

## Archivos importantes

- **sync_system_api.py** - Archivo principal
- **sync_config_api.json** - Configuración (se crea automáticamente)
- **logs/sync_api_{email}.log** - Logs del sistema
- **README.md** - Documentación completa

## Si algo falla

1. **Revisa los logs**: Abre `logs/sync_api_{email}.log`
2. **Ejecuta en modo debug**: Doble clic en `DEBUG.bat`
3. **Verifica dependencias**: Doble clic en `VERIFICAR_DEPENDENCIAS.bat`
4. **Reconfigura**: Doble clic en `CONFIGURAR.bat` nuevamente

## Auto-inicio

Al ejecutar **TRAY.bat** por primera vez, el sistema se configura automáticamente para iniciarse al encender Windows.
