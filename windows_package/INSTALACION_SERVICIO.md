# INSTALACION COMO SERVICIO DE WINDOWS (OPCION 2)

## QUE ES ESTA OPCION?

Esta opcion instala el sistema como un **servicio de Windows** que:
- ✅ Se **INICIA AUTOMATICAMENTE** al prender la PC
- ✅ Corre en segundo plano (no molesta)
- ✅ Se reinicia solo si falla
- ✅ No requiere que el usuario haya iniciado sesion

---

## PASO A PASO

### REQUISITOS PREVIOS:

1. **Windows 7 o superior**
2. **Permisos de Administrador**
3. **Python 3.8+ instalado**
4. **Ejecutable creado** (`dist\sync_system.exe`)

---

### PASO 1: Crear el ejecutable

Si ya tienes el ejecutable, ve al **PASO 2**.

```batch
# Abre una terminal en la carpeta windows_package
CREAR_EXE.bat
```

Espera 3-5 minutos. El ejecutable se creará en `dist\sync_system.exe`

---

### PASO 2: Configurar el sistema

Solo la **PRIMERA VEZ** necesitas configurar:

```batch
# Ejecuta el modo configuracion
dist\sync_system.exe --mode config
```

Se abrirá una ventana donde debes ingresar:
- Host, puerto, usuario, password de **PostgreSQL**
- Host, puerto, usuario, password de **MySQL**
- RIF de la empresa
- Email de contacto
- Intervalo de sincronización (ej: 30 minutos)

Esto crea el archivo `sync_config.json`.

---

### PASO 3: Instalar el servicio

**IMPORTANTE: Ejecuta como ADMINISTRADOR**

```batch
# Click derecho en INSTALAR_SERVICIO.bat
# Seleccionar "Ejecutar como administrador"
INSTALAR_SERVICIO.bat
```

El script hará:
1. ✅ Verificar permisos de administrador
2. ✅ Verificar que existe el ejecutable
3. ✅ Descargar NSSM (herramienta para manejar servicios)
4. ✅ Verificar configuración
5. ✅ Instalar el servicio "SyncSystemService"
6. ✅ Configurar inicio automático
7. ✅ Configurar reinicio automático si falla

Al final te preguntará si quieres **iniciar el servicio ahora**. Di que **SÍ**.

---

### PASO 4: Verificar que funciona

Abre una terminal y ejecuta:

```batch
# Ver estado del servicio
sc query SyncSystemService
```

Debería decir:
```
STATE: RUNNING
```

O revisa el log:
```batch
# Ver log de sincronización
type sync_system.log
```

---

## COMANDOS UTILES

### Ver estado del servicio:
```batch
sc query SyncSystemService
```

### Iniciar servicio manualmente:
```batch
nssm start SyncSystemService
```

### Detener servicio:
```batch
nssm stop SyncSystemService
```

### Ver logs de sincronización:
```batch
type sync_system.log
```

### Ver logs del servicio de Windows:
```batch
# Abre el Visor de Eventos
eventvwr.msc
# Busca en "Windows Logs" -> "Application"
# Filtra por "SyncSystemService"
```

---

## DESINSTALAR SERVICIO

Si ya no quieres el servicio:

**Ejecuta como ADMINISTRADOR:**

```batch
# Click derecho en DESINSTALAR_SERVICIO.bat
# Seleccionar "Ejecutar como administrador"
DESINSTALAR_SERVICIO.bat
```

Esto:
- ❌ Detiene el servicio
- ❌ Elimina el servicio del sistema
- ✅ NO elimina el ejecutable
- ✅ NO elimina la configuración

---

## ARCHIVOS CREADOS

Después de la instalación tendrás:

```
windows_package/
├── dist/
│   └── sync_system.exe          ← El ejecutable
├── sync_config.json              ← Configuración (creado al configurar)
├── sync_system.log               ← Log de sincronización
├── nssm.exe                      ← Herramienta de servicio (descargado auto)
├── INSTALAR_SERVICIO.bat         ← Instalar servicio
├── DESINSTALAR_SERVICIO.bat      ← Desinstalar servicio
└── CREAR_EXE.bat                 ← Crear ejecutable
```

---

## SOLUCION DE PROBLEMAS

### El servicio no se inicia:

1. **Revisa el log:**
   ```batch
   type sync_system.log
   ```

2. **Revisa configuración:**
   - ¿Existe `sync_config.json`?
   - ¿Las credenciales son correctas?

3. **Prueba ejecutar manualmente:**
   ```batch
   dist\sync_system.exe --mode service
   ```
   Si funciona manualmente, el problema es el servicio.

4. **Revisa permisos:**
   - El servicio necesita acceso a la red
   - Las bases de datos deben ser accesibles

### El servicio se detiene solo:

1. **Revisa el visor de eventos:**
   ```
   eventvwr.msc
   ```

2. **Configura reinicio automático:**
   ```batch
   nssm set SyncSystemService AppExit Default Restart
   nssm set SyncSystemService AppRestartDelay 10000
   ```

### No puedo instalar el servicio:

- ¿Ejecutaste como **ADMINISTRADOR**?
- ¿Existe `dist\sync_system.exe`?
- ¿Tienes conexión a Internet (para descargar NSSM)?

---

## VENTAJAS DE ESTA OPCION

✅ **Automatico** - Se inicia solo al prender la PC
✅ **Segundo plano** - No interfiere con el trabajo
✅ **Robusto** - Se reinicia si falla
✅ **Sin usuario** - Funciona aunque nadie haya iniciado sesion

---

## SIGUIENTE PASO

Una vez instalado:
1. El servicio sincronizará automáticamente cada X minutos
2. Puedes olvidarte de el
3. Si necesitas cambiar configuración:
   - Detén el servicio: `nssm stop SyncSystemService`
   - Reconfigura: `dist\sync_system.exe --mode config`
   - Inicia el servicio: `nssm start SyncSystemService`
