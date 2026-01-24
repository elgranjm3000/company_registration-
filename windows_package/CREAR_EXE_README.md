# GUÍA PARA CREAR EJECUTABLE .EXE

## PASO 1: Instalar dependencias y configurar

```
1. Doble clic → INSTALAR_Y_EJECUTAR.bat
2. Selecciona → Opción 1 (Configurar)
3. Llena datos de PostgreSQL
4. Click en Guardar
```

---

## PASO 2: Crear el .exe (OPCIONAL)

### Opción A: Automático (Recomendado)

```
Doble clic → CREAR_EXE.bat
```

El .bat hará:
1. ✅ Verificar Python
2. ✅ Instalar PyInstaller
3. ✅ Compilar el .exe
4. ✅ Ofrecer ejecutarlo

### Opción B: Manual

```bash
# 1. Instalar PyInstaller
pip install pyinstaller

# 2. Crear .exe
python build_exe.py
```

---

## PASO 3: Ejecutar el .exe

### Ubicación del .exe:
```
dist/SyncSystem/sync_system.exe
```

### Ejecutar como System Tray:
```
dist/SyncSystem/sync_system.exe --mode tray
```

---

## ¿QUÉ INCLUYE EL .EXE?

✅ Todo el código Python compilado
✅ Todas las dependencias (psycopg2, mysql-connector, pystray, Pillow, win10toast)
✅ smart_sync_complete.py integrado
✅ Interfaz gráfica de configuración
✅ System Tray (icono en barra de tareas)
✅ Notificaciones de Windows

---

## MODOS DE EJECUCIÓN DEL .EXE:

```
# Configuración (primera vez)
sync_system.exe --mode config

# Sincronización única
sync_system.exe --mode sync

# Administrador (con logs en tiempo real)
sync_system.exe --mode manager

# System Tray (recomendado - icono en barra de tareas)
sync_system.exe --mode tray

# Servicio (consola)
sync_system.exe --mode service
```

---

## NOTIFICACIONES DE WINDOWS:

Cuando haya **nuevos presupuestos** en MySQL:

```
┌─────────────────────────────────────────┐
│  🔄 Sync System - Nuevos Presupuestos   │
│                                         │
│  Tienes 3 nuevo(s) presupuesto(s)       │
│  de MySQL sincronizados                │
│                                         │
│           [Cerrar en 10s]               │
└─────────────────────────────────────────┘
```

- Aparece automáticamente en la esquina inferior derecha
- Se muestra cuando se sincronizan nuevos quotes
- No interfiere con el trabajo del usuario
- Desaparece después de 10 segundos

---

## ARCHIVOS NECESARIOS PARA COMPILAR:

```
windows_package/
├── sync_system.py              ← Código principal
├── smart_sync_complete.py      ← Módulo de sincronización
├── build_exe.py                ← Script de compilación
├── CREAR_EXE.bat               ← Ejecuta este para crear .exe
└── dist/
    └── SyncSystem/
        └── sync_system.exe    ← Resultado
```

---

## DISTRIBUCIÓN DEL .EXE:

Para distribuir el sistema a otros usuarios:

### Opción 1: Carpeta completa (Recomendado)
```
Copia toda la carpeta: dist/SyncSystem/
Incluye todos los archivos necesarios
```

### Opción 2: Solo el .exe (Si está todo compilado)
```
Solo copia: sync_system.exe
Pero asegúrate de que todas las DLL estén incluidas
```

---

## REQUISITOS PARA EL USUARIO FINAL:

- Windows 7 o superior
- No necesita Python instalado
- No necesita instalar nada

---

## PROBLEMAS COMUNES:

### Error: "Falta dependencia"
```
Solución: Ejecuta INSTALAR_Y_EJECUTAR.bat primero
```

### Error: "No se puede iniciar la aplicación"
```
Solución: Instala Visual C++ Redistributable 2015-2022
Descarga: https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### Error: "Las notificaciones no aparecen"
```
Solución 1: Verifica que las notificaciones estén activadas en Windows
          Configuración > Sistema > Notificaciones y acciones

Solución 2: Ejecuta como administrador
          Clic derecho > Ejecutar como administrador
```

---

## COMPARACIÓN: .BAT vs .EXE

| Característica | .BAT | .EXE |
|----------------|------|------|
| Requiere Python | ✅ Sí | ❌ No |
| Instalación | Copiar archivo | Copiar carpeta |
| Tamaño | ~50 KB | ~150-200 MB |
| Portabilidad | Requiere Python | Funciona solo |
| Velocidad | Igual | Igual |
| Recomendado para | Desarrollo | Producción |

---

## RESUMEN DE PASOS:

**Para desarrollo/pruebas:**
```
INSTALAR_Y_EJECUTAR.bat → Opción 1 (Configurar)
INSTALAR_Y_EJECUTAR.bat → Opción 5 (System Tray)
```

**Para producción:**
```
INSTALAR_Y_EJECUTAR.bat → Opción 1 (Configurar)
CREAR_EXE.bat
CONFIGURAR_INICIO_AUTOMATICO.bat
Ejecutar: dist/SyncSystem/sync_system.exe --mode tray
```

---

**Commit:** 2e8b197 - Sistema completo con .exe y notificaciones
