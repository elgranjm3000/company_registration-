# 📦 Cómo Compilar el .exe

## Opciones de Compilación

Tienes 4 formas de compilar el .exe:

### 0. **COMPILAR_DEBUG.bat** ⚠️ PARA DIAGNÓSTICO DE ERRORES

**USO SOLO CUANDO EL .EXE NO FUNCIONA**

```batch
cd windows_package
COMPILAR_DEBUG.bat
```

**¿Para qué sirve?**
- El .exe muestra una CONSOLA con todos los mensajes
- Puedes ver EXACTAMENTE qué error está ocurriendo
- Sirve para diagnosticar problemas

**Procedimiento:**
1. Ejecuta `COMPILAR_DEBUG.bat`
2. Ejecuta el .exe resultante: `dist\SyncSystem_DEBUG\SyncSystem_DEBUG.exe --mode config`
3. Ingresa los datos y click en Guardar
4. **MIRA LA CONSOLA** - aparecerá el error exacto
5. Toma una captura de pantalla de la consola
6. Reporta el error

**No uses este .exe para producción** - muestra una ventana de consola que no es profesional.

---

### 1. **COMPILAR_COMPLETO.bat** (Recomendado)

Este script te **PREGUNTA** qué modo quieres:

```
Selecciona el modo de compilacion:

  1. CON Consola (DEBUG) - Muestra terminal para ver errores
  2. SIN Consola (PRODUCCION) - Solo GUI, sin terminal

Selecciona 1 o 2:
```

**Usa opción 1 (CON Consola) si:**
- El .exe no funciona
- Necesitas ver errores
- Estás haciendo debug

**Usa opción 2 (SIN Consola) si:**
- Todo funciona bien
- Quieres distribuir el .exe a usuarios finales
- No quieres que vean la terminal

---

### 2. **COMPILAR_CON_CONSOILA.bat** (Debug)

Crea el .exe **CON terminal visible**.

```batch
cd windows_package
COMPILAR_CON_CONSOILA.bat
```

**Ventajas:**
- ✅ Puedes ver todos los mensajes en la consola
- ✅ Ves los errores inmediatamente
- ✅ Útil para desarrollo y debug

**Desventajas:**
- ❌ Se ve una ventana negra de consola
- ❌ No es profesional para usuarios finales

---

### 3. **COMPILAR_SIN_CONSOILA.bat** (Producción)

Crea el .exe **SIN terminal** (solo GUI).

```batch
cd windows_package
COMPILAR_SIN_CONSOILA.bat
```

**Ventajas:**
- ✅ Solo se ve la ventana de la aplicación
- ✅ Más profesional para usuarios finales
- ✅ Sin consola molesta

**Desventajas:**
- ❌ Si hay errores, no se ven
- ❌ Difícil de debugear

---

## Comandos Manuales

También puedes ejecutar directamente:

```batch
# Con consola (debug)
python build_exe.py --console

# Sin consola (producción)
python build_exe.py
```

---

## Solución de Problemas

### El .exe no se abre o se cierra inmediatamente

**CAUSA:** Probablemente hay un error que no se ve porque está en modo SIN CONSOLA.

**SOLUCIÓN:**
1. Compila con **CONSOLA**:
   ```batch
   COMPILAR_CON_CONSOILA.bat
   ```
2. Ejecuta el .exe
3. Lee el error en la consola
4. Arregla el problema
5. Vuelve a compilar **SIN CONSOLA** para producción

### Errores comunes en la consola

**Error: "No module named 'X'"**
- Falta una dependencia en `build_exe.py`
- Agrégala a `hiddenimports`

**Error: "Cannot connect to MySQL"**
- Problema de configuración de la base de datos
- Revisa `sync_config.json`

**Error: "config_encryption not found"**
- Falta incluir `config_encryption.py`
- Debería estar en `datas` del .spec

---

### Botón "Guardar" no hace nada en modo Config

**SÍNTOMA:** Al hacer click en el botón Guardar de la ventana de configuración, no ocurre nada.

**CAUSA:** Hay un error silencioso que no se ve porque el .exe está en modo windowed.

**SOLUCIÓN:**
1. Usa **COMPILAR_DEBUG.bat** para crear un .exe con consola
2. Ejecuta el .exe resultante: `dist\SyncSystem_DEBUG\SyncSystem_DEBUG.exe --mode config`
3. Ingresa los datos y click en Guardar
4. **MIRA LA CONSOLA** - aparecerá el error exacto
5. Errores comunes:
   - **"No module named 'X'"**: Falta dependencia en `build_exe.py`
   - **"Cannot connect to PostgreSQL"**: Problema de conexión a BD
   - **"Cannot connect to MySQL"**: Problema de conexión a BD
   - **"Permission denied"**: No se puede escribir `sync_config.json`

---

## Recomendación

**Para desarrollo:**
- Usa `COMPILAR_CON_CONSOILA.bat`
- Ve los errores en tiempo real

**Para producción:**
- Usa `COMPILAR_SIN_CONSOILA.bat`
- Distribuye un .exe profesional sin consola

**Para decidir:**
- Usa `COMPILAR_COMPLETO.bat`
- Elige en el momento según lo que necesites

---

**Última actualización:** 2026-02-27
