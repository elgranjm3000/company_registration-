# Sistema de Sincronización PostgreSQL ↔ MySQL

## Opciones de instalación:

### Opción 1: Ejecutable simple (uso manual)
- Solo ejecutas el .exe cuando quieras sincronizar
- Ideal para testing o uso manual

### Opción 2: Servicio de Windows (recomendado)
- **Se inicia automáticamente** al prender la PC
- Corre en segundo plano
- Sincronización 24/7 sin intervención

Ver instrucciones detalladas en: **INSTALACION_SERVICIO.md**

---

## CREAR EL EJECUTABLE

### Windows:
1. Abre una terminal en la carpeta `windows_package`
2. Ejecuta: `CREAR_EXE.bat`
3. Espera 3-5 minutos
4. El ejecutable estará en: `dist\sync_system.exe`

### Linux:
1. Abre una terminal en la carpeta `windows_package`
2. Ejecuta: `chmod +x CREAR_EXE_LINUX.sh && ./CREAR_EXE_LINUX.sh`
3. Espera 3-5 minutos
4. El ejecutable estará en: `dist/sync_system`

---

## MODO DE USO

El ejecutable tiene 4 modos:

- `--mode config` - Configuración inicial (GUI)
- `--mode manager` - Interfaz de administración
- `--mode sync` - Sincronización única
- `--mode service` - Modo servicio (corre continuamente)

Ejemplos:
```bash
# Windows
sync_system.exe --mode config

# Linux
./sync_system --mode config
```

---

## INSTALAR COMO SERVICIO DE WINDOWS (Opción 2)

1. **Crear ejecutable:** `CREAR_EXE.bat`
2. **Configurar:** `dist\sync_system.exe --mode config`
3. **Instalar servicio:** `INSTALAR_SERVICIO.bat` (como administrador)
4. **Listo:** El servicio se inicia automáticamente

Ver instrucciones completas en: **INSTALACION_SERVICIO.md**

---

## REQUISITOS

### Windows:
- Windows 7 o superior
- Python 3.8+ instalado
- Permisos de administrador (para servicio)

### Linux:
- Cualquier distribución moderna
- Python 3.8+ instalado
- python3-venv (`sudo apt install python3-venv`)

---

## QUE HACE EL SISTEMA

✅ Detecta cambios automáticamente usando hashes
✅ Sincroniza PostgreSQL → MySQL (products, customers, categories)
✅ Sincroniza MySQL → PostgreSQL (quotes como sales_operation)
✅ Se ejecuta cada X minutos (configurable)
✅ Maneja errores y reintentos automáticos


