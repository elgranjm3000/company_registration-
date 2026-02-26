#!/usr/bin/env python3
"""
Script de prueba para notificaciones de Windows
Ejecuta esto en Windows para verificar que las notificaciones funcionen
"""
import time

def probar_notificaciones():
    """Prueba las notificaciones de Windows 10/11"""
    try:
        from win10toast import ToastNotifier
        toast = ToastNotifier()

        print("=" * 70)
        print("PRUEBA DE NOTIFICACIONES DE WINDOWS 10/11")
        print("=" * 70)
        print("\nDeberías ver notificaciones en la esquina INFERIOR DERECHA")
        print("(arriba de la barra de tareas, junto al reloj)\n")

        # Prueba 1: Notificación simple
        print("1. Enviando notificación simple (3 segundos)...")
        result1 = toast.show_toast(
            "🔄 Sync System - Prueba 1",
            "Esta es una notificación de prueba",
            duration=3,
            threaded=True
        )
        print(f"   Resultado: {'✅ ÉXITO' if result1 else '❌ FALLÓ'}")
        time.sleep(4)

        # Prueba 2: Notificación con duración larga
        print("\n2. Enviando notificación larga (8 segundos)...")
        result2 = toast.show_toast(
            "✅ Sincronización Completada",
            "Products: 5 nuevos/modificados | Duration: 15.3s",
            duration=8,
            threaded=True
        )
        print(f"   Resultado: {'✅ ÉXITO' if result2 else '❌ FALLÓ'}")
        time.sleep(9)

        # Prueba 3: Notificación de error
        print("\n3. Enviando notificación de error...")
        result3 = toast.show_toast(
            "⚠️ Error de Sincronización",
            "No se pudo conectar a PostgreSQL",
            duration=5,
            threaded=True
        )
        print(f"   Resultado: {'✅ ÉXITO' if result3 else '❌ FALLÓ'}")
        time.sleep(6)

        print("\n" + "=" * 70)
        print("PRUEBA COMPLETADA")
        print("=" * 70)
        print("\nSi NO viste las notificaciones:")
        print("1. Verifica que win10toast esté instalado:")
        print("   pip install win10toast")
        print("\n2. Verifica que las notificaciones estén habilitadas:")
        print("   Configuración de Windows → Sistema → Notificaciones y acciones")
        print("\n3. Verifica que el modo 'No molestar' esté desactivado")
        print("\n4. Revisa el Centro de Acción (icono de cuadro de mensaje)")
        print("   - Las notificaciones se guardan ahí")
        print("=" * 70)

    except ImportError:
        print("\n❌ ERROR: win10toast NO está instalado")
        print("\nPara instalar:")
        print("   pip install win10toast")
        print("\nO usando conda:")
        print("   conda install -c conda-forge win10toast")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    probar_notificaciones()
