# 🎯 ENTREGA AL CLIENTE - INSTRUCCIONES

## 📦 Contenido del Paquete

El cliente recibirá un archivo comprimido que contiene:

```
SyncAPISystem_v1.0.zip
├── SyncAPISystem.exe          ← ← UNICO ARCHIVO QUE EL CLIENTE NECESITA
├── _internal/                  ← Archivos internos (no tocar)
└── INSTRUCCIONES.txt           ← Este archivo
```

## 🚀 Cómo Usar (Muy Sencillo)

### Paso 1: Descomprimir
- Descomprimir el archivo `SyncAPISystem_v1.0.zip` en una carpeta
- Ejemplo: `C:\SyncAPISystem\`

### Paso 2: Ejecutar
**Doble clic en `SyncAPISystem.exe`**

### Paso 3: Seguir las instrucciones en pantalla
- **Primera vez**: Se mostrará aviso para configurar
  - Click en **"⚙️ CONFIGURAR SISTEMA"**
  - Completar los datos (API, PostgreSQL, Empresa)
  - Click en **"Guardar"**

- **Después de configurar**:
  - **"🖥️ ABRIR MANAGER"** → Para sincronizar manualmente
  - **"📬 MODO SYSTEM TRAY"** → Para ejecutar en segundo plano (icono junto al reloj)
  - **"🔄 SINCRONIZAR AHORA"** → Para sincronizar una vez

## ✨ Características

✅ **No requiere Python** ni ninguna instalación adicional
✅ **Un solo archivo .exe** - Doble clic y listo
✅ **Interfaz gráfica fácil de usar**
✅ **Se inicia automáticamente** al encender Windows (modo System Tray)
✅ **Sincronización automática** cada X minutos

## 📋 Modos de Uso

### Modo Configuración
- Primera vez que usan el sistema
- Para cambiar datos de conexión

### Modo Manager
- Ventana de administración
- Sincronización manual (click en "Sincronizar Todo")
- Ver logs y estadísticas
- Botón "Configurar" para cambiar datos

### Modo System Tray (Recomendado)
- Icono junto al reloj de Windows
- Sincronización automática cada X minutos
- Click derecho para opciones:
  - Sincronizar ahora
  - Abrir Manager
  - Ver logs
  - Salir

**⚡ Auto-inicio**: En modo System Tray, el sistema se configura automáticamente en el registro de Windows para iniciarse al encender el equipo.

## 🛠️ Soporte

Si hay problemas:
1. Revisar que el equipo tenga conexión a internet
2. Revisar que PostgreSQL esté ejecutándose
3. Revisar los logs en la carpeta `logs/`

---

**¡ES TODO! El cliente solo necesita doble clic en el .exe**
