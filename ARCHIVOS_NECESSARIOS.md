# 📦 ARCHIVOS NECESARIOS - Guía de Instalación

---

## 1️⃣ PARA PROBAR EN TU MÁQUINA ACTUAL

### Archivos Requeridos:
```
/home/muentes/company_registration/
├── .env                      (405 bytes)  - Configuración de BD y empresa
├── smart_sync_complete.py    (60 KB)      - Módulo principal de sincronización
└── test_sync.py              (4 KB)       - Script de prueba
```

### Dependencias Python:
```bash
pip install python-dotenv psycopg2-binary mysql-connector-python
```

### Para Ejecutar la Prueba:
```bash
cd /home/muentes/company_registration
python3 test_sync.py
```

---

## 2️⃣ PARA WINDOWS SERVIDOR (Producción)

### Opción A: Instalador Recomendada
**Solo necesitas 1 archivo:**
```
setup_sync_service.exe     (Instalador completo - ~50 MB)
```

**Qué incluye el instalador:**
- ✅ Ejecutable del servicio (sync_service.exe)
- ✅ Interfaz gráfica de administración (Sync Manager)
- ✅ Módulo de sincronización
- ✅ Todas las dependencias
- ✅ Configuración automática
- ✅ Instalación como servicio de Windows

**Pasos de instalación:**
1. Copiar `setup_sync_service.exe` al servidor Windows
2. Ejecutar como Administrator
3. Configurar conexiones a BD
4. Seleccionar intervalo de sincronización
5. ¡Listo!

---

### Opción B: Instalación Manual

**Archivos necesarios:**
```
C:\Program Files\SyncService\
├── sync_service.exe              (Servicio de Windows)
├── sync_manager.exe              (Interfaz gráfica)
├── config.ini                    (Archivo de configuración)
└── logs\
    └── sync_service.log          (Log de eventos)
```

**Pasos de instalación manual:**
1. Crear carpeta: `C:\Program Files\SyncService\`
2. Copiar archivos `.exe`
3. Ejecutar como administrador:
   ```cmd
   sync_service.exe --install
   ```
4. Configurar con `sync_manager.exe`
5. Iniciar servicio:
   ```cmd
   net start SyncService
   ```

---

## 3️⃣ PARA COMPILAR EJECUTABLES (Desarrollo)

**Archivos fuente necesarios:**
```
/home/muentes/company_registration/
├── smart_sync_complete.py    - Módulo de sincronización
├── sync_service.py           - Wrapper del servicio Windows
├── sync_manager.py           - Interfaz gráfica
├── build.bat                 - Script para compilar .exe
├── create_installer.bat      - Script para crear instalador
├── setup.iss                 - Configuración Inno Setup
└── icon.ico                  (opcional) Ícono del ejecutable
```

### Pasos para compilar:

**1. Instalar dependencias:**
```cmd
pip install pywin32 python-dotenv psycopg2-binary mysql-connector-python
pip install pyinstaller
```

**2. Compilar ejecutables:**
```cmd
build.bat
```

Esto crea:
- `dist/sync_service.exe`
- `dist/sync_manager.exe`

**3. Crear instalador:**
```cmd
create_installer.bat
```

Esto crea:
- `output/setup_sync_service.exe`

---

## 4️⃣ ESTRUCTURA DE ARCHIVOS COMPLETA

```
company_registration/
│
├── 📁 Archivos Principales
│   ├── smart_sync_complete.py      - Módulo de sincronización
│   ├── sync_service.py             - Servicio Windows
│   └── sync_manager.py             - Interfaz gráfica
│
├── 📁 Configuración
│   ├── .env                        - Variables de entorno (desarrollo)
│   └── config.ini                  - Configuración Windows
│
├── 📁 Scripts
│   ├── test_sync.py                - Script de prueba
│   ├── build.bat                   - Compilar .exe
│   └── create_installer.bat        - Crear instalador
│
├── 📁 SQL
│   ├── 01_create_sync_hashes.sql   - Crear tabla sync_hashes
│   └── 02_queries_utilidades.sql   - Consultas útiles
│
├── 📁 Documentación
│   ├── ARCHIVOS_NECESSARIOS.md     - Este archivo
│   ├── INSTRUCCIONES_DESPLIEGUE.md - Instrucciones de despliegue
│   ├── README_SYNC_SISTEMA.md      - Documentación del sistema
│   └── SINCRONIZACION_QUOTES_AGREGADA.md - Documentación de quotes
│
└── 📁 Instalador
    └── setup.iss                   - Configuración Inno Setup
```

---

## 5️⃣ REQUERIMIENTOS DE SISTEMA

### Para Servidor Windows:
- **Sistema:** Windows 10/11 Pro, Windows Server 2016+
- **RAM:** Mínimo 2 GB (recomendado 4 GB)
- **Espacio:** 100 MB libres
- **Permisos:** Administrador (para instalar servicio)
- **Conectividad:** Acceso a PostgreSQL y MySQL

### Para Desarrollo/Pruebas:
- **Python:** 3.8+
- **Dependencias:** Ver `requirements.txt`

---

## 6️⃣ CHECKLIST DE INSTALACIÓN

### ✅ Para Probar (Desarrollo):
- [ ] Python 3.8+ instalado
- [ ] Dependencias instaladas (`pip install ...`)
- [ ] Archivo `.env` configurado
- [ ] Acceso a PostgreSQL
- [ ] Acceso a MySQL
- [ ] Ejecutar `python3 test_sync.py`

### ✅ Para Producción (Windows):
- [ ] Descargar `setup_sync_service.exe`
- [ ] Ejecutar como Administrador
- [ ] Configurar conexión PostgreSQL
- [ ] Configurar conexión MySQL
- [ ] Verificar empresa (RIF, email)
- [ ] Configurar intervalo de sincronización
- [ ] Iniciar servicio
- [ ] Verificar logs

---

## 7️⃣ CONFIGURACIÓN DE ARCHIVO .env

**Para desarrollo/pruebas:**
```env
# PostgreSQL
DB_HOST=localhost
DB_DATABASE=dataaa
DB_USER=postgres
DB_PASSWORD=tu_password

# MySQL
DB_HOST_MYSQL=tu_host_mysql
DB_PORT_DATABASE_MYSQL=tu_database
DB_USER_MYSQL=tu_usuario
DB_PASSWORD_MYSQL=tu_password

# Empresa
RIF=J123456789
EMAIL=empresa@email.com
COMPANY_NOMBRE=Nombre Empresa C.A.
```

**Para producción (Windows):**
La configuración se hace a través de la interfaz gráfica `sync_manager.exe`, no se requiere archivo `.env`.

---

## 8️⃣ ARCHIVOS DE LOG

**Ubicación de logs:**
- **Desarrollo:** `/home/muentes/company_registration/sync_service.log`
- **Producción Windows:** `C:\Program Files\SyncService\logs\sync_service.log`

**Ver log en tiempo real:**
```bash
# Linux
tail -f sync_service.log

# Windows PowerShell
Get-Content sync_service.log -Wait
```

---

## 9️⃣ SOLUCIÓN DE PROBLEMAS

### Error: "No se puede conectar a PostgreSQL"
- Verificar que PostgreSQL esté corriendo
- Verificar host y puerto en `.env`
- Verificar firewall

### Error: "No se puede conectar a MySQL"
- Verificar que MySQL esté corriendo
- Verificar host y puerto
- Verificar usuario y permisos

### Error: "No se encuentra la empresa"
- Verificar RIF y EMAIL en `.env`
- Ejecutar primero `app.py` para sincronizar companies

### Servicio no inicia en Windows:
- Verificar permisos de administrador
- Verificar logs en `C:\Program Files\SyncService\logs\`
- Reinstalar servicio con `sync_service.exe --install`

---

## 🟢 RESUMEN RÁPIDO

### Para PROBAR ahora:
```bash
# Ya tienes todo lo necesario
python3 test_sync.py
```

### Para WINDOWS SERVIDOR:
1. Compilar: `build.bat` (en Windows con Python)
2. Crear instalador: `create_installer.bat`
3. Copiar `output/setup_sync_service.exe` al servidor
4. Ejecutar instalador

---

**Última actualización:** 2025-01-22
**Versión:** 1.1
**Estado:** ✅ Completo
