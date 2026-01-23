# SISTEMA DE SINCRONIZACIÓN INTELIGENTE
## PostgreSQL → MySQL - Servicio de Windows

---

## 📦 ARCHIVOS CREADOS

### ✅ Documentación
- `docs/01_PLANTEAMIENTO_SISTEMA.md` - Documento completo del sistema

### ✅ Scripts SQL
- `sql/01_create_sync_hashes.sql` - Crear tabla de hashes
- `sql/02_queries_utilidades.sql` - Consultas de monitoreo

### ✅ Módulos Python
- `smart_sync_complete.py` - **Módulo principal** de sincronización inteligente
  - Detecta cambios usando hash comparison
  - Sincroniza: products, customers, sellers, categories
  - Compatible con app Tkinter y servicio Windows

---

## 📋 RESUMEN DE LA ESTRATEGIA IMPLEMENTADA

### Detección de Cambios

**Sin timestamps en PostgreSQL**, usamos:

1. **Hash MD5** de cada registro (campos clave)
2. **Tabla sync_hashes** en PostgreSQL
3. **Comparación**:
   - Si NO existe en sync_hashes → **NUEVO**
   - Si existe y hash ≠ → **MODIFICADO**
   - Si existe en hash pero no en PG → **ELIMINADO**

### Flujo Completo

```
┌─────────────────────────────────────┐
│ 1. Leer products de PostgreSQL      │
│    SELECT * FROM products            │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 2. Para cada producto:              │
│    • Calcular hash MD5               │
│    • Buscar en sync_hashes           │
│    • Clasificar: nuevo/modificado/igual│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 3. Detectar eliminados:             │
│    SELECT FROM sync_hashes          │
│    WHERE NOT IN (products actuales) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 4. Sincronizar a MySQL:             │
│    • INSERT nuevos                  │
│    • UPDATE modificados             │
│    • (opcional) DELETE eliminados   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ 5. Actualizar sync_hashes:         │
│    • INSERT/UPDATE hash nuevos      │
│    • DELETE hash eliminados         │
└─────────────────────────────────────┘
```

---

## 🎯 PRÓXIMOS PASOS

Ahora necesito crear:

### 1. Servicio de Windows (`sync_service.py`)
- Se registra como servicio del sistema
- Se inicia automáticamente
- Ejecuta sync cada X tiempo
- Maneja inicio/parada

### 2. Interfaz de Administración (`SyncManager.py`)
- Ver estado del servicio
- Iniciar/detener/reiniciar
- Ver logs en tiempo real
- Reconfigurar sin reinstalar

### 3. Instalador (`setup.iss`)
- Inno Setup script
- Compila todo
- Crea servicio
- Configura todo

---

## 💡 ¿PROSEGUIR?

**¿Quieres que cree los archivos restantes?**

1. **Servicio de Windows** (sync_service.py) - ~300 líneas
2. **Interfaz SyncManager** (SyncManager.py) - ~500 líneas
3. **Instalador Inno Setup** (setup.iss) - ~200 líneas

O puedo **probar primero** el módulo `smart_sync_complete.py` que ya creé.

¿Cuál prefieres?
