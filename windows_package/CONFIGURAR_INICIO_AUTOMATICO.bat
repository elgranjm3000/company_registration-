@echo off
title Configurar Inicio Automatico

cd /d "%~dp0"

echo ========================================
echo   CONFIGURAR INICIO AUTOMATICO
echo ========================================
echo.
echo Esto hara que el Sync System se inicie
echo automaticamente cada vez que prendas la PC.
echo.

REM Obtener ruta absoluta del directorio actual
set "DIR=%~dp0"
set "DIR=%DIR:~0,-1%"

REM Eliminar barra final si existe
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

echo Ruta del sistema: %DIR%
echo.

REM Crear acceso directo en carpeta de inicio
echo Creando acceso directo en carpeta de Startup...

REM Usar PowerShell para crear el acceso directo
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Sync System Tray.lnk'); $s.TargetPath = '%DIR%\INICIAR_SYSTEM_TRAY.bat'; $s.WorkingDirectory = '%DIR%'; $s.Description = 'Sync System - Sincronizacion en segundo plano'; $s.Save()"

if %errorlevel% equ 0 (
    echo.
    echo ✅ EXITO: Inicio automatico configurado
    echo.
    echo El sistema se iniciara automaticamente al prender la PC.
    echo.
    echo Para desactivar el inicio automatico:
    echo   1. Presiona Win + R
    echo   2. Escribe: shell:startup
    echo   3. Elimina: Sync System Tray.lnk
    echo.
) else (
    echo.
    echo ❌ ERROR: No se pudo crear el acceso directo
    echo.
    echo Alternativa manual:
    echo   1. Presiona Win + R
    echo   2. Escribe: shell:startup
    echo   3. Copia: INICIAR_SYSTEM_TRAY.bat
    echo.
)

pause
