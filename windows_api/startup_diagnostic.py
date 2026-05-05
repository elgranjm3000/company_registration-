"""
Wrapper de diagnóstico para sync_system_api.exe
Ejecuta el .exe y captura TODA la salida y errores
"""

import subprocess
import sys
import os
from datetime import datetime

def main():
    exe_path = r"dist\SyncAPISystem\SyncAPISystem.exe"

    if not os.path.exists(exe_path):
        print(f"ERROR: No existe {exe_path}")
        print("Primero ejecuta CREAR_EXE_OK.bat")
        input("Presiona Enter para salir...")
        return

    print("="*70)
    print("  DIAGNÓSTICO DEL EJECUTABLE")
    print("="*70)
    print(f"Executable: {exe_path}")
    print(f"Fecha: {datetime.now()}")
    print()

    # Crear archivo de log
    log_file = "diagnostico_exe.log"

    # Ejecutar con --mode help primero
    print("Ejecutando: SyncAPISystem.exe --mode help")
    print("-"*70)

    try:
        process = subprocess.Popen(
            [exe_path, "--mode", "help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(timeout=30)

        print("STDOUT:")
        print(stdout)
        print()

        if stderr:
            print("STDERR:")
            print(stderr)
            print()

        print(f"Exit Code: {process.returncode}")
        print()

        # Guardar en log
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"DIAGNÓSTICO - {datetime.now()}\n")
            f.write("="*70 + "\n")
            f.write(f"Exit Code: {process.returncode}\n")
            f.write("\nSTDOUT:\n")
            f.write(stdout)
            f.write("\nSTDERR:\n")
            f.write(stderr if stderr else "(vacío)")

        print(f"Log guardado en: {log_file}")

    except subprocess.TimeoutExpired:
        print("ERROR: TIMEOUT - El ejecutable tardó más de 30 segundos")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("="*70)
    input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()
