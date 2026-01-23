# 🖥️ FUNCIONAMIENTO EN WINDOWS - Guía Paso a Paso

---

## 📋 ÍNDICE
1. [Proceso de Instalación](#1-proceso-de-instalación)
2. [Configuración Inicial](#2-configuración-inicial)
3. [Funcionamiento del Servicio](#3-funcionamiento-del-servicio)
4. [Monitoreo y Administración](#4-monitoreo-y-administración)
5. [Sincronización Automática](#5-sincronización-automática)
6. [Solución de Problemas](#6-solución-de-problemas)

---

## 1. PROCESO DE INSTALACIÓN

### Paso 1: Ejecutar el Instalador

```
📁 setup_sync_service.exe
   │
   ▼
┌─────────────────────────────────────────┐
│     Bienvenido al Instalador           │
│     Sistema de Sincronización v1.1     │
│                                         │
│  Este programa instalará:              │
│  ✓ Servicio de Windows                 │
│  ✓ Interfaz de Administración          │
│  ✓ Módulo de Sincronización            │
│                                         │
│  Siguiente >                           │
└─────────────────────────────────────────┘
```

### Paso 2: Seleccionar Carpeta de Instalación

```
┌─────────────────────────────────────────┐
│     Carpeta de Destino                  │
│                                         │
│  El programa se instalará en:          │
│  C:\Program Files\SyncService\         │
│                                         │
│  Examinar...  Siguiente >              │
└─────────────────────────────────────────┘
```

### Paso 3: Confirmar Instalación

```
┌─────────────────────────────────────────┐
│     Listo para instalar                 │
│                                         │
│  Instalar en:                           │
│  C:\Program Files\SyncService\         │
│                                         │
│  < Instalar >                           │
└─────────────────────────────────────────┘
```

### Paso 4: Progreso de Instalación

```
┌─────────────────────────────────────────┐
│     Instalando...                       │
│                                         │
│  Copiando archivos...                   ████████░░ 80% │
│  Registrando servicio...                │
│  Configurando permisos...               │
│                                         │
│  Archivos instalados:                   │
│  ✓ sync_service.exe                     │
│  ✓ sync_manager.exe                     │
│  ✓ config.ini                           │
│  ✓ logs\                               │
└─────────────────────────────────────────┘
```

### Paso 5: Instalación Completada

```
┌─────────────────────────────────────────┐
│     ¡Instalación Completada!            │
│                                         │
│  ✓ Servicio instalado                   │
│  ✓ Archivos copiados                    │
│                                         │
│  [ ] Ejecutar Sync Manager              │
│  [ ] Iniciar servicio ahora             │
│                                         │
│  Finalizar >                            │
└─────────────────────────────────────────┘
```

---

## 2. CONFIGURACIÓN INICIAL

### Paso 1: Abrir Sync Manager

Al finalizar la instalación, se abre **Sync Manager**:

```
┌────────────────────────────────────────────────────────────┐
│  🔧 Sync Service Manager v1.1                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  📊 Estado del Servicio                               │ │
│  │                                                      │ │
│  │    Estado:  🟢 DETENIDO                              │ │
│  │    Última sync:  Nunca                                │ │
│  │    Próxima sync:  --                                  │ │
│  │                                                      │ │
│  │    [  INICIAR SERVICIO  ]  [  CONFIGURAR  ]         │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  📈 Estadísticas                                      │ │
│  │                                                      │ │
│  │    Products:   0 nuevos, 0 modificados               │ │
│  │    Customers:  0 nuevos, 0 modificados               │ │
│  │    Categories: 0 nuevos, 0 modificados               │ │
│  │    Quotes:     0 nuevos                              │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│                        [  VER LOGS  ]  [  SALIR  ]        │
└────────────────────────────────────────────────────────────┘
```

### Paso 2: Configurar Conexiones

Click en **[ CONFIGURAR ]**:

```
┌────────────────────────────────────────────────────────────┐
│  ⚙️ Configuración de Conexiones                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  🐘 PostgreSQL (Origen)                              │ │
│  │                                                      │ │
│  │  Host:          [localhost           ]               │ │
│  │  Puerto:        [5432                 ]               │ │
│  │  Database:      [dataaa               ]               │ │
│  │  Usuario:       [postgres             ]               │ │
│  │  Password:      [••••••••             ]               │ │
│  │                                                      │ │
│  │  [  PROBAR CONEXIÓN  ]                               │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  🐬 MySQL (Destino)                                  │ │
│  │                                                      │ │
│  │  Host:          [91.238.160.176        ]             │ │
│  │  Puerto:        [3306                 ]               │ │
│  │  Database:      [chrystal_movil        ]             │ │
│  │  Usuario:       [chrystal_app          ]             │ │
│  │  Password:      [••••••••             ]               │ │
│  │                                                      │ │
│  │  [  PROBAR CONEXIÓN  ]                               │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  🏢 Empresa                                           │ │
│  │                                                      │ │
│  │  RIF:           [J502741283           ]              │ │
│  │  Email:         [multiservicios...     ]              │ │
│  │  Nombre:        [Multiservicios Leblanc]              │ │
│  │                                                      │ │
│  │  [  VERIFICAR EMPRESA  ]                             │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  ⏰ Programación                                      │ │
│  │                                                      │ │
│  │  Intervalo de sincronización:                         │ │
│  │    ○ Cada 5 minutos                                   │ │
│  │    ○ Cada 15 minutos                                  │ │
│  │    ● Cada 30 minutos  ← Seleccionado                  │ │
│  │    ○ Cada 1 hora                                      │ │
│  │    ○ Manual (solo cuando se solicite)                 │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│            [  GUARDAR  ]  [  CANCELAR  ]                  │
└────────────────────────────────────────────────────────────┘
```

### Paso 3: Verificar Empresa

Click en **[ VERIFICAR EMPRESA ]**:

```
┌─────────────────────────────────────────┐
│  ✅ Empresa Encontrada                  │
│                                         │
│  ID:      23                            │
│  RIF:     J502741283                    │
│  Nombre:  Multiservicios Leblanc C.A.   │
│  Email:   multiserviciosleblanc@...     │
│                                         │
│              [  ACEPTAR  ]              │
└─────────────────────────────────────────┘
```

### Paso 4: Guardar Configuración

Click en **[ GUARDAR ]**:

```
┌─────────────────────────────────────────┐
│  ✅ Configuración Guardada              │
│                                         │
│  La configuración ha sido guardada      │
│  exitosamente en:                       │
│  C:\Program Files\SyncService\config.ini│
│                                         │
│  Ahora puedes iniciar el servicio.      │
│                                         │
│              [  ACEPTAR  ]              │
└─────────────────────────────────────────┘
```

---

## 3. FUNCIONAMIENTO DEL SERVICIO

### Paso 1: Iniciar el Servicio

Click en **[ INICIAR SERVICIO ]**:

```
┌────────────────────────────────────────────────────────────┐
│  🔧 Sync Service Manager v1.1                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  📊 Estado del Servicio                               │ │
│  │                                                      │ │
│  │    Estado:  🟢 INICIANDO...                          │ │
│  │    Iniciando servicio de Windows...                  │ │
│  │                                                      │ │
│  │    ████████░░░░░░░░░░░░░░                           │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Paso 2: Servicio Activo

```
┌────────────────────────────────────────────────────────────┐
│  🔧 Sync Service Manager v1.1                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  📊 Estado del Servicio                               │ │
│  │                                                      │ │
│  │    Estado:  🟢 ACTIVO                               │ │
│  │    Última sync:  2025-01-22 10:30:15                │ │
│  │    Próxima sync:  2025-01-22 11:00:15 (en 29 min)   │ │
│  │                                                      │ │
│  │    [  DETENER SERVICIO  ]  [  SINCRONIZAR AHORA  ]  │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │  📈 Estadísticas de Última Sincronización            │ │
│  │                                                      │ │
│  │    Products:   5 nuevos, 2 modificados               │ │
│  │    Customers:  0 nuevos, 1 modificado                │ │
│  │    Categories: 0 nuevos, 0 modificados               │ │
│  │    Quotes:     3 nuevos                              │ │
│  │    Duración:   45.3 segundos                         │ │
│  │    Errores:    0                                     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│                        [  VER LOGS  ]  [  SALIR  ]        │
└────────────────────────────────────────────────────────────┘
```

### Paso 3: Servicio en Segundo Plano

El servicio corre en segundo plano como un **Servicio de Windows**:

```
Windows Services (services.msc)
┌─────────────────────────────────────────────────────────┐
│  Nombre:                    Sync Service               │
│  Descripción:               Servicio de Sincronización  │
│  Estado:                    🟢 En ejecución            │
│  Tipo de inicio:            Automático                 │
│  Iniciado:                  22/01/2025 10:00:00        │
│  Iniciado como:             Sistema                    │
└─────────────────────────────────────────────────────────┘
```

**Esto significa:**
- ✅ Se inicia automáticamente al encender Windows
- ✅ No necesita que nadie esté logueado
- ✅ Corre en segundo plano sin interrumpir
- ✅ Sincroniza automáticamente cada X tiempo

---

## 4. MONITOREO Y ADMINISTRACIÓN

### Ver Logs en Tiempo Real

Click en **[ VER LOGS ]**:

```
┌────────────────────────────────────────────────────────────┐
│  📋 Logs del Servicio - Tiempo Real                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  [  Actualizando automáticamente...  ]                    │
│                                                            │
│  [2025-01-22 10:30:15] ℹ️ INFO: === INICIANDO SERVICIO ===│
│  [2025-01-22 10:30:16] ℹ️ INFO: Conectando a PostgreSQL...│
│  [2025-01-22 10:30:17] ✅ ÉXITO: PostgreSQL conectado     │
│  [2025-01-22 10:30:18] ℹ️ INFO: Conectando a MySQL...     │
│  [2025-01-22 10:30:19] ✅ ÉXITO: MySQL conectado          │
│  [2025-01-22 10:30:20] ℹ️ INFO: Detectando cambios...     │
│  [2025-01-22 10:30:21] ℹ️ INFO:   ✨ NUEVO: PROD1249      │
│  [2025-01-22 10:30:22] ℹ️ INFO:   ✨ NUEVO: PROD1250      │
│  [2025-01-22 10:30:23] ℹ️ INFO: Products: 2 nuevos        │
│  [2025-01-22 10:30:24] ℹ️ INFO: Customers: 0 nuevos       │
│  [2025-01-22 10:30:25] ℹ️ INFO: Detectando quotes...      │
│  [2025-01-22 10:30:26] ℹ️ INFO:   ✨ NUEVO: Quote #125     │
│  [2025-01-22 10:30:27] ℹ️ INFO:   🔄 MODIFICADO: Quote #100│
│  [2025-01-22 10:30:28] ℹ️ INFO: Quotes: 1 nuevo, 1 mod     │
│  [2025-01-22 10:30:45] ✅ ÉXITO: Sincronización completada│
│  [2025-01-22 10:30:46] ℹ️ INFO: Próxima sync: 11:00:15     │
│                                                            │
│  Filtros: [Todos ▼] [Última hora ▼]                        │
│  Exportar: [TXT] [CSV]  [  LIMPIAR LOGS  ]  [  CERRAR  ]  │
└────────────────────────────────────────────────────────────┘
```

### Sincronización Manual

Click en **[ SINCRONIZAR AHORA ]**:

```
┌────────────────────────────────────────────────────────────┐
│  ⏳ Sincronizando...                                      │
│                                                            │
│  Detectando cambios en products...                         │
│  Sincronizando products a MySQL...                         │
│  Detectando cambios en customers...                        │
│  Sincronizando customers a MySQL...                        │
│  Detectando cambios en categories...                       │
│  Sincronizando categories a MySQL...                       │
│  Detectando cambios en quotes (MySQL → PostgreSQL)...      │
│  Sincronizando quotes a PostgreSQL...                      │
│                                                            │
│  ████████████████░░░░░░░ 60%                               │
│                                                            │
│  Esta ventana se cerrará automáticamente...                │
└────────────────────────────────────────────────────────────┘
```

---

## 5. SINCRONIZACIÓN AUTOMÁTICA

### Flujo de Sincronización

```
┌─────────────────────────────────────────────────────────────┐
│              🔄 CICLO DE SINCRONIZACIÓN                    │
│              (cada 30 minutos configurado)                 │
└─────────────────────────────────────────────────────────────┘

  🕐 10:00:15 AM
     │
     ▼
  ┌─────────────────────────────────────────────┐
  │  1. Conectar a PostgreSQL y MySQL           │
  └──────────────┬──────────────────────────────┘
                 │ ✅ Conectado
                 ▼
  ┌─────────────────────────────────────────────┐
  │  2. Detectar cambios en products           │
  │     PostgreSQL → MySQL                     │
  │                                             │
  │  • Leer products de PostgreSQL             │
  │  • Generar hash MD5                         │
  │  • Comparar con sync_hashes                 │
  │  • Detectar: 5 nuevos, 2 modificados        │
  └──────────────┬──────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────┐
  │  3. Sincronizar products a MySQL            │
  │     (5 nuevos + 2 modificados)              │
  └──────────────┬──────────────────────────────┘
                 │ ✅ 7 products sincronizados
                 ▼
  ┌─────────────────────────────────────────────┐
  │  4. Detectar cambios en customers          │
  │     PostgreSQL → MySQL                     │
  │                                             │
  │  • 0 nuevos, 1 modificado                   │
  └──────────────┬──────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────┐
  │  5. Sincronizar customers a MySQL           │
  └──────────────┬──────────────────────────────┘
                 │ ✅ 1 customer sincronizado
                 ▼
  ┌─────────────────────────────────────────────┐
  │  6. Detectar cambios en categories          │
  │     PostgreSQL → MySQL                     │
  │                                             │
  │  • 0 nuevos, 0 modificados                  │
  └──────────────┬──────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────┐
  │  7. Detectar cambios en quotes             │
  │     MySQL → PostgreSQL (dirección opuesta)  │
  │                                             │
  │  • Leer quotes de MySQL                     │
  │  • Generar hash MD5                         │
  │  • Comparar con sync_hashes                 │
  │  • Detectar: 3 nuevos, 1 modificado         │
  └──────────────┬──────────────────────────────┘
                 │
                 ▼
  ┌─────────────────────────────────────────────┐
  │  8. Sincronizar quotes a PostgreSQL         │
  │     (como sales_operation BUDGET)           │
  │                                             │
  │  • Insertar sales_operation                 │
  │  • Insertar monedas (USD y VES)             │
  │  • Insertar items                           │
  │  • Insertar impuestos                       │
  │  • Actualizar estados                       │
  └──────────────┬──────────────────────────────┘
                 │ ✅ 4 quotes sincronizados
                 ▼
  ┌─────────────────────────────────────────────┐
  │  9. Guardar hashes en sync_hashes          │
  │     (para detectar cambios futuros)         │
  └──────────────┬──────────────────────────────┘
                 │ ✅ Hashes guardados
                 ▼
  ┌─────────────────────────────────────────────┐
  │  10. Generar reporte final                  │
  │                                             │
  │      Products:   5 nuevos, 2 modificados    │
  │      Customers:  0 nuevos, 1 modificado     │
  │      Categories: 0 nuevos, 0 modificados    │
  │      Quotes:     3 nuevos (MySQL→PG)       │
  │      Duración:   45.3 segundos              │
  └──────────────┬──────────────────────────────┘
                 │ ✅ Sincronización completada
                 ▼
  🕐 10:00:60 AM (45 segundos después)
     │
     ▼
  ┌─────────────────────────────────────────────┐
  │  Próxima sincronización: 10:30:15 AM        │
  │  (dentro de 29.5 minutos)                   │
  └─────────────────────────────────────────────┘
```

### Qué Sucede Durante la Sincronización

```
PostgreSQL                          MySQL
┌──────────────┐                   ┌──────────────┐
│              │  Products ───────►│              │
│              │  Customers ──────►│              │
│   PostgreSQL │  Categories ─────►│    MySQL     │
│              │                   │              │
│              │◄────── Quotes     │              │
│              │   (sales_operation)              │
└──────────────┘                   └──────────────┘
      │                                 │
      │                                 │
      ▼                                 ▼
┌──────────────────────────────────────────────┐
│         sync_hashes (PostgreSQL)             │
│                                              │
│  • Guarda hash de cada registro sincronizado │
│  • Permite detectar cambios futuros          │
│  • Evita sincronizar datos ya procesados     │
└──────────────────────────────────────────────┘
```

---

## 6. SOLUCIÓN DE PROBLEMAS

### Problema 1: Servicio No Inicia

**Síntoma:**
```
Estado: 🔴 DETENIDO
Error: "No se puede iniciar el servicio"
```

**Solución:**
```
1. Verificar logs en Sync Manager
2. Verificar conexiones a BD
3. Ejecutar como administrador
4. Reinstalar servicio:
   sync_service.exe --install
```

### Problema 2: Error de Conexión

**Síntoma:**
```
Error: "No se puede conectar a PostgreSQL"
```

**Solución:**
```
1. Verificar host y puerto
2. Verificar credenciales
3. Probar conexión con:
   - psql -h localhost -U postgres
4. Verificar firewall
```

### Problema 3: Sincronización Lenta

**Síntoma:**
```
Duración: > 5 minutos
```

**Solución:**
```
1. Verificar velocidad de red
2. Optimizar índices en BD
3. Ajustar intervalo de sync
4. Revisar registros muy grandes
```

### Problema 4: Errores en Quotes

**Síntoma:**
```
Quotes: 3 nuevos, 5 errores
```

**Solución:**
```
1. Verificar logs para detalles
2. Verificar referencias (customers, products)
3. Verificar estaciones en stations
4. Reintentar sync manual
```

---

## 📊 VISUALIZACIÓN DEL FLUJO COMPLETO

```
┌─────────────────────────────────────────────────────────────────┐
│                    Windows Servidor                             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Servicio de Windows (SyncService.exe)                   │  │
│  │                                                           │  │
│  │  • Se inicia automáticamente al arrancar Windows         │  │
│  │  • Corre en segundo plano                                │  │
│  │  • Se ejecuta como usuario "Sistema"                    │  │
│  │  • No necesita login de usuario                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Módulo de Sincronización (smart_sync_complete.py)       │  │
│  │                                                           │  │
│  │  • Se ejecuta cada X minutos (configurable)             │  │
│  │  • Detecta cambios usando hashes                         │  │
│  │  • Sincroniza bidireccionalmente                        │  │
│  │  • Guarda logs de cada operación                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
│          ┌───────────────┴───────────────┐                     │
│          ▼                               ▼                     │
│  ┌──────────────────┐         ┌──────────────────┐            │
│  │   PostgreSQL     │         │      MySQL       │            │
│  │   (localhost)    │         │  (91.238.160.176) │            │
│  │                  │         │                  │            │
│  │  • products ◄───┼─────────┼──► products      │            │
│  │  • clients  ◄───┼─────────┼──► customers     │            │
│  │  • department◄──┼─────────┼──► categories     │            │
│  │  • sales_ope◄────┼─────────┼─── quotes        │            │
│  │  • sync_hashes  │         │                  │            │
│  └──────────────────┘         └──────────────────┘            │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Sync Manager (sync_manager.exe)                         │  │
│  │                                                           │  │
│  │  • Interfaz gráfica de administración                    │  │
│  │  • Configurar conexiones                                 │  │
│  │  • Ver logs en tiempo real                               │  │
│  │  • Iniciar/Detener servicio                              │  │
│  │  • Sincronización manual                                 │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Ubicación de archivos:
• C:\Program Files\SyncService\
  - sync_service.exe (Servicio)
  - sync_manager.exe (Interfaz)
  - config.ini (Configuración)
  - logs\sync_service.log (Logs)
```

---

## 🎯 RESUMEN DE FUNCIONAMIENTO

### Instalación
1. Ejecutar `setup_sync_service.exe`
2. Seguir asistente de instalación
3. Configurar conexiones a BD
4. Verificar empresa
5. Iniciar servicio

### Operación
1. Servicio corre automáticamente
2. Cada 30 minutos (configurable):
   - Detecta cambios en PostgreSQL → MySQL
   - Detecta cambios en MySQL → PostgreSQL
   - Sincroniza datos automáticamente
   - Guarda logs

### Administración
1. Abrir Sync Manager
2. Ver estado del servicio
3. Ver logs en tiempo real
4. Sincronización manual (opcional)
5. Configurar intervalos

### Ventajas
- ✅ Automático: No requiere intervención
- ✅ Seguro: Solo sincroniza cambios
- ✅ Confiable: Manejo de errores por registro
- ✅ Monitoreable: Logs detallados
- ✅ Bidireccional: PostgreSQL ↔ MySQL

---

**Versión:** 1.1
**Fecha:** 2025-01-22
**Estado:** ✅ Completo
