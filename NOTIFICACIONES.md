# Notificaciones Multiplataforma

El sistema de sincronización soporta notificaciones nativas en múltiples sistemas operativos.

## Instalación de Dependencias

### Windows
```bash
pip install win10toast pywin32
```

Las notificaciones aparecerán en el **Action Center** de Windows 10/11.

### Linux
```bash
pip install notify2
```

Las notificaciones aparecerán en el sistema de **Desktop Notifications** de tu entorno de escritorio (GNOME, KDE, XFCE, etc).

**Requisitos previos en Ubuntu/Debian:**
```bash
sudo apt-get install libnotify-bin
```

### macOS
```bash
brew install terminal-notifier
```

Las notificaciones aparecerán en el **Notification Center** de macOS.

## Solución de Problemas

### Las notificaciones no se muestran

1. **Verifica que la dependencia esté instalada:**
   ```bash
   # Linux/Mac
   pip list | grep notify2

   # Windows
   pip list | grep win10toast
   ```

2. **En Linux, verifica que el servicio de notificaciones esté corriendo:**
   ```bash
   # Verificar si dbus está funcionando
   echo "org.freedesktop.Notifications" | gdbus call
   ```

3. **En macOS, verifica que terminal-notifier esté instalado:**
   ```bash
   which terminal-notifier
   ```

### Errores en Windows

Si ves el error `pkg_resources.DistributionNotFound`, instala pywin32:
```bash
pip install pywin32
```

### El programa funciona pero no veo notificaciones

Las notificaciones son opcionales. El programa funcionará perfectamente sin ellas.
Puedes ver el estado de sincronización en:
- Tooltip del icono del System Tray
- Botón "Ver Logs"
- Archivos de log en `logs/sync_api_{email}.log`

## Comportamiento por Sistema

| Sistema | Librería | Ubicación | Duración |
|---------|----------|-----------|----------|
| Windows | win10toast | Action Center | Configurable |
| Linux | notify2/dbus | Desktop Notifications | Configurable |
| macOS | terminal-notifier | Notification Center | Configurable |

Todas las notificaciones son:
- **No bloqueantes**: No interrumpen la sincronización
- **Silenciosas en caso de error**: Si fallan, el programa continúa normalmente
- **Con icono personalizado**: Si existe icon.png o icon.ico
