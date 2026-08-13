# Compilación con Nuitka (protección de código + sin error multi-instancia)

## Ventajas sobre PyInstaller

1. **Código protegido**: Nuitka compila tu `.py` a C y luego a código máquina nativo.
   No quedan `.pyc` descompilables como con PyInstaller.
2. **Sin error `failed to start embedded python interpreter`**: Nuitka no usa el
   bootloader de PyInstaller, así que ese error es imposible.
3. **Mejor rendimiento**: el código compilado a C corre más rápido.

## Requisitos previos (una sola vez)

### 1. Instalar Nuitka
```bash
pip install nuitka
```

### 2. Instalar un compilador de C (obligatorio)

**Opción A — MinGW64 (más fácil):**
1. Descargar: https://winlibs.com/ (elegir "Win64 - UCRT runtime")
2. Descomprimir en `C:\mingw64`
3. Agregar `C:\mingw64\bin` al PATH del sistema

**Opción B — MSVC (recomendado por Nuitka):**
1. Descargar: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Instalar "Desarrollo para escritorio con C++"

### 3. Verificar
```bash
nuitka --version
gcc --version    # o cl.exe si usas MSVC
```

## Compilar

### Doble clic en:
```
COMPILAR_NUITKA.bat
```

O desde línea de comandos:
```bash
cd windows_api
COMPILAR_NUITKA.bat
```

## Resultado

```
dist_nuitka/
└── SyncAPISystem.exe    ← UN SOLO archivo, código compilado a C
```

Distribuye **solo el .exe**.

## Si quieres máxima confiabilidad (alternativa sin --onefile)

Si el modo `--onefile` te da algún problema de arranque, usa `--standalone` sin `--onefile`.
Esto genera una carpeta con el .exe + DLLs (como el `--onedir` de PyInstaller) que es
100% confiable para la multi-instancia (Manager/Config/Logs).

Edita el `.bat` y **quita** la línea `--onefile`. El resultado será:
```
dist_nuitka/
└── SyncAPISystem.dist/
    ├── SyncAPISystem.exe
    └── (DLLs y datos)
```

En ese caso distribuye **toda la carpeta**, no solo el .exe.

## Notas importantes

- La primera compilación tarda 10-30 minutos (compila todo a C).
- Nuitka descargará automáticamente dependencias la primera vez (`--assume-yes-for-downloads`).
- El `.exe` resultante es más grande que el de PyInstaller (todo compilado), pero más rápido.
- El antivirus detectará MUCHO menos falsos positivos con Nuitka que con PyInstaller.
