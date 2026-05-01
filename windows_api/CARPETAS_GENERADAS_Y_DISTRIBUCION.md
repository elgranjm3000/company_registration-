# 📂 Carpetas que Genera PyInstaller al Compilar

## 📁 Estructura de Carpetas DESPUÉS de Compilar

Cuando ejecutas `COMPILAR_SIN_CONSOLA.bat` o `COMPILAR_CON_VERIFICACION.bat`, se generan estas carpetas:

```
windows_api/
├── build/                    # ❌ NO entregar (archivos temporales de compilación)
│   └── sync_system_api/
│       ├── Analysis-00.toc
│       ├── COLLECT-00.toc
│       ├── EXE-00.toc
│       ├── PYZ-00.pyz
│       ├── PKG-00.pkg
│       ├── PYZ-00.toc
│       ├── SUPPORT-00.toc
│       ├── warn-sync_system_api.txt
│       └── xref-sync_system_api.html
│
├── dist/                     # ✅ ESTA ES LA CARPETA QUE SE ENTREGA AL CLIENTE
│   ├── SyncAPISystem.exe    # ← EJECUTABLE PRINCIPAL
│   ├── api_client/           # ← Módulos de la API (Python compilado)
│   │   ├── __pycache__/
│   │   ├── base.py
│   │   ├── categories.py
│   │   ├── company.py
│   │   ├── customers.py
│   │   ├── products.py
│   │   ├── quotes.py
│   │   └── sellers.py
│   ├── sync/                 # ← Módulos de sincronización
│   │   ├── __pycache__/
│   │   ├── base.py
│   │   ├── categories_sync.py
│   │   ├── customers_sync.py
│   │   ├── products_sync.py
│   │   ├── quotes_sync.py
│   │   └── sellers_sync.py
│   ├── _internal/           # ← Archivos internos de PyInstaller
│   │   ├── pylib/
│   │   └── Python/
│   ├── config_encryption.py  # ← Configuración encriptada
│   ├── *.dll                 # ← Bibliotecas de Windows
│   ├── *.pyd                 # ← Extensiones de Python compiladas
│   └── [otros archivos]
│
└── dist_protected/           # ❌ NO entregar (solo si se usó ofuscación con PyArmor)
    └── [archivos ofuscados temporales]
```

---

## ✅ CARPETA QUE LE ENTREGAS AL CLIENTE

### 📦 **La carpeta `dist/` COMPLETA**

```
dist/
└── SyncAPISystem.exe  ← Este es el archivo principal
```

### Cómo preparar la carpeta para el cliente:

#### Opción 1: **Comprimir la carpeta completa** (RECOMENDADO)

```bash
# En Windows, clic derecho en carpeta dist/
# → "Enviar a" → "Carpeta comprimida (en zip)"

# Resultado:
dist.zip  # ← Este archivo .zip es lo que le envías al cliente
```

#### Opción 2: **Renombrar la carpeta**

```bash
# Renombrar "dist" a "SyncAPISystem"
dist/ → SyncAPISystem/

# Luego comprimir:
SyncAPISystem.zip  # ← Este .zip se entrega al cliente
```

---

## 🚫 Carpetas que NO se entregan al cliente

| Carpeta | Por qué NO se entrega |
|---------|---------------------|
| `build/` | Son archivos temporales de compilación |
| `dist_protected/` | Código intermedio ofuscado (temporal) |
| `__pycache__/` | Código Python pre-compilado (interno) |
| `*.spec` | Archivos de configuración de PyInstaller |
| `*.bat` | Scripts de compilación (tuyos, no del cliente) |
| `logs/` | Tus logs de desarrollo |
| `test_*.py` | Scripts de prueba (tuyos) |

---

## 📊 Contenido típico de `dist/`

```
dist/
├── SyncAPISystem.exe          (80-110 MB) ← Ejecutable principal
├── api_client/                 (carpeta)
│   ├── __pycache__/            (carpeta oculta)
│   ├── base.py                 (1-2 KB)
│   ├── categories.py           (8-10 KB)
│   ├── company.py              (2-3 KB)
│   ├── customers.py            (10-12 KB)
│   ├── products.py             (12-15 KB)
│   ├── quotes.py               (3-4 KB)
│   └── sellers.py              (10-12 KB)
├── sync/                       (carpeta)
│   ├── __pycache__/            (carpeta oculta)
│   ├── base.py                 (8-10 KB)
│   ├── categories_sync.py      (12-15 KB)
│   ├── customers_sync.py       (15-18 KB)
│   ├── products_sync.py        (20-25 KB)
│   ├── quotes_sync.py          (30-35 KB)
│   └── sellers_sync.py         (12-15 KB)
├── _internal/                  (carpeta)
│   ├── pylib/                  (50-100 archivos)
│   └── Python/                 (librerías Python)
├── config_encryption.py        (1-2 KB)
├── python3XX.dll              (5-10 archivos DLL)
├── psycopg2.dll               (1-2 DLL)
├── cryptography DLLs          (3-5 DLL)
└── [otros archivos DLL y .pyd]

Tamaño total: 120-160 MB
```

---

## 🎯 Instrucciones para el Cliente Final

### Qué recibe el cliente:

**Archivo:** `SyncAPISystem.zip` (o el nombre que le pongas)

**Contenido:**
```
SyncAPISystem.zip
└── dist/
    └── SyncAPISystem.exe
    └── [todos los archivos necesarios]
```

### Cómo lo instala el cliente:

1. **Descomprimir el .zip:**
   ```
   C:\Program Files\SyncAPISystem\
   o
   C:\Users\Usuario\AppData\Local\SyncAPISystem\
   o
   C:\SyncAPISystem\
   ```

2. **Ejecutar el .exe:**
   ```
   Doble clic en SyncAPISystem.exe
   ```

3. **Configurar (primera vez):**
   - Ingresa email
   - Ingresa password de la API
   - Configura PostgreSQL
   - Guarda configuración

4. **Listo para usar:**
   - System Tray aparece en la barra de tareas
   - Sincronización automática funciona

---

## 💡 Tips de Distribución

### ✅ BUENAS PRÁCTICAS:

1. **Comprimir la carpeta `dist/` en un .zip**
   ```
   SyncAPISystem_v1.0.zip  ← Incluir versión
   ```

2. **Incluir un README.txt dentro:**
   ```
   dist/
   ├── SyncAPISystem.exe
   ├── LEEME.txt  ← Instrucciones de instalación
   └── [archivos]
   ```

3. **Renombrar la carpeta con versión:**
   ```
   dist/ → SyncAPISystem_v1.0/
   ```

4. **Crear instalador (NSIS, InnoSetup):**
   ```
   Instalador.exe  ← Extrae dist/ en Program Files
   ```

### ❌ EVITAR:

1. ❌ NO entregar solo el .exe (necesita las carpetas api_client/ y sync/)
2. ❌ NO entregar la carpeta `build/`
3. ❌ NO entregar archivos .py (solo el .exe y carpetas compiladas)
4. ❌ NO entregar logs o archivos de desarrollo

---

## 📦 Ejemplo de Distribución Profesional

```
SyncAPISystem_Setup_v1.0.zip
├── SyncAPISystem.exe        (Extrae en Program Files)
├── README.txt               (Instrucciones)
├── REQUISITOS.txt           (Requisitos del sistema)
└── LICENCIA.txt             (Términos de uso)
```

**El instalador extrae:**
```
C:\Program Files\SyncAPISystem\
├── SyncAPISystem.exe
├── api_client/
├── sync/
└── [demás archivos]
```

---

## 📊 Tamaños Típicos

### Carpeta `dist/` completa:
- **Sin ofuscación:** 120-140 MB
- **Con ofuscación:** 130-160 MB

### .zip comprimido:
- **Sin ofuscación:** 40-60 MB
- **Con ofuscación:** 45-70 MB

---

## ✅ Resumen

**Carpetas generadas:**
- ✅ `build/` - Temporal, NO entregar
- ✅ `dist/` - **ESTA ES LA QUE SE ENTREGA**
- ✅ `dist_protected/` - Temporal, NO entregar (solo si se usó PyArmor)

**Al cliente se le entrega:**
1. La carpeta `dist/` COMPLETA
2. Comprimida en un .zip
3. O dentro de un instalador profesional

**El cliente solo necesita:**
1. Descomprimir
2. Ejecutar `SyncAPISystem.exe`
3. Configurar credentials (primera vez)
