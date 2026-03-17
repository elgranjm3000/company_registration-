# 🔄 Reconfiguración del Sistema

## Problema

Cuando ya existe un archivo `sync_config.json` y quieres cambiar a otra base de datos, el sistema no permite reconfigurar fácilmente.

## Soluciones Implementadas

He agregado **3 formas diferentes** de reconfigurar el sistema:

---

## 1️⃣ **Botón "🔄 Reconfigurar" en el Manager**

La forma más fácil: desde la ventana del Manager.

### Pasos:
1. Abre el sistema: `python3 sync_system.py --mode manager`
2. Haz clic en el botón **"🔄 Reconfigurar"**
3. Confirma que quieres reconfigurar
4. El sistema:
   - ✅ Hace un backup automático de tu config actual
   - ✅ Borra la configuración
   - ✅ Abre la ventana de configuración
5. Ingresa los nuevos datos de la nueva base de datos

### Backup:
El backup se guarda con fecha y hora:
```
sync_config_backup_20260227_224530.json
```

---

## 2️⃣ **Línea de Comandos: --reconfig**

Para reconfigurar desde terminal sin abrir la GUI.

### Comando:
```bash
python3 sync_system.py --reconfig
```

### O también:
```bash
python3 sync_system.py --mode reconfig
```

### Qué hace:
- ✅ Hace backup del config actual
- ✅ Borra la configuración
- ✅ Abre ventana de configuración
- ✅ Puedes ingresar nuevos datos

---

## 3️⃣ **Manual: Borrar Archivo de Configuración**

La forma manual si las otras opciones no funcionan.

### En Windows:
```cmd
del sync_config.json
del .sync_config.json
```

### En Linux/Mac:
```bash
rm sync_config.json
rm .sync_config.json
```

### Luego ejecutar:
```bash
python3 sync_system.py
```

El sistema detectará que no hay config y abrirá la ventana de configuración automáticamente.

---

## 🔒 **Archivos Ocultos (Linux/Mac)**

En Linux y Mac, el config se guarda como archivo oculto:

```bash
.sync_config.json  # Archivo oculto (con punto al inicio)
```

### Para ver archivos ocultos:
```bash
ls -la
```

### Para eliminarlo manualmente:
```bash
rm .sync_config.json
```

---

## ⚠️ **Precauciones**

### ✅ ANTES de Reconfigurar:
1. **Backup Automático**: El sistema hace backup automáticamente
2. **Datos MySQL**: No se borran datos de MySQL, solo la config local
3. **Datos PostgreSQL**: No se borran datos de PostgreSQL

### ❌ DESPUÉS de Reconfigurar:
- El sistema se conectará a las **nuevas** bases de datos
- Los logs anteriores quedan en el directorio `logs/`
- Los backups se guardan en el directorio del sistema

---

## 📋 **Campos que se Reconfiguran**

Cuando reconfiguras, puedes cambiar:

### ✅ **PostgreSQL**
- Host (ej: localhost, 192.168.1.100)
- Puerto (default: 5432)
- Database (ej: nuevaprueba, empresa2)
- User (ej: postgres, admin)
- Password

### ✅ **MySQL**
- Host (ej: 91.238.160.176, localhost)
- Puerto (default: 3306)
- Database (ej: chrystal_movil, empresa2_db)
- User (ej: chrystal_app, root)
- Password

### ✅ **Empresa**
- RIF (ej: J505261940, V123456789)
- Email (ej: admin@empresa.com)
- Nombre (ej: Mi Empresa CA)

### ✅ **Sincronización**
- Intervalo en minutos (default: 30)

---

## 🎯 **Casos de Uso**

### Caso 1: Cambiar a Producción
```bash
# Desarrollo actual → Producción
python3 sync_system.py --reconfig
```

Luego ingresa:
- PostgreSQL de producción
- MySQL de producción
- Empresa en producción

### Caso 2: Cambiar a Otra Empresa
```bash
# Empresa 1 → Empresa 2
python3 sync_system.py --reconfig
```

Luego ingresa:
- Nuevas bases de datos de la Empresa 2
- RIF de la Empresa 2
- Email de la Empresa 2

### Caso 3: Restaurar Backup
Si por error reconfiguraste y quieres volver:

```bash
# Buscar el backup más reciente
ls -lt sync_config_backup_*.json | head -1

# Restaurar
cp sync_config_backup_20260227_224530.json sync_config.json

# Volver a abrir
python3 sync_system.py
```

---

## 🔧 **Solución de Problemas**

### Problema: "No se puede eliminar sync_config.json"
**Solución**: Cierra el sincronizador primero
```bash
# En Windows: cierra todas las ventanas
taskkill /f /im python.exe

# Luego elimina
del sync_config.json
```

### Problema: "La configuración se carga igual"
**Solución**: También elimina la versión oculta
```bash
# Linux/Mac
rm .sync_config.json

# Windows
del .sync_config.json
```

### Problema: "No aparece el botón Reconfigurar"
**Solución**: Actualiza el archivo
```bash
git pull origin main
```

---

## ✅ **Resumen**

Ahora tienes **3 opciones** para reconfigurar:

1. ✅ **Botón "🔄 Reconfigurar"** - Más fácil (GUI)
2. ✅ **`--reconfig`** - Línea de comandos
3. ✅ **Borrar manual** - Si todo falla

Todos los métodos:
- ✅ Hacen backup automático
- ✅ Borran config anterior
- ✅ Permiten configurar nuevas bases de datos
- ✅ Funcionan en Windows, Linux, Mac

---

**Fecha**: 2026-02-27
**Estado**: ✅ IMPLEMENTADO
**Versión**: 2.1
