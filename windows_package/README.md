# 🅲️ OPCIÓN C - Ejecutable Único

## 📦 Archivos en esta carpeta

- `sync_system.py` - Código principal (ejecutable único)
- `smart_sync_complete.py` - Módulo de sincronización
- `requirements.txt` - Dependencias
- `COMPILAR_RAPIDO.bat` - Script para compilar
- `README.md` - Este archivo

## 🚀 Cómo compilar en Windows

1. **Abrir CMD** en esta carpeta

2. **Ejecutar:**
   ```
   COMPILAR_RAPIDO.bat
   ```

   O manualmente:
   ```cmd
   pip install pyinstaller pywin32
   python -m PyInstaller --onefile --noconsole --add-data "smart_sync_complete.py;." --hidden-import=psycopg2 --hidden-import=mysql.connector --hidden-import=dotenv --hidden-import=tkinter --name="sync_system" sync_system.py
   ```

3. **Esperar 5-10 minutos**

4. **Resultado:** `dist\sync_system.exe`

## 📋 Para el usuario final

Entregar SOLO estos archivos:
- `sync_system.exe` (~30 MB)
- Guía de uso simple

El usuario:
1. Doble clic en `sync_system.exe`
2. Configura (primera vez)
3. ¡Listo!

---

**Versión:** 2.0
**Fecha:** 2025-01-23
