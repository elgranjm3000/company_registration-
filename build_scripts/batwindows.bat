@echo off
setlocal enabledelayedexpansion
title Creador de Ejecutable - Registro de Companias

echo ========================================
echo   CREACION AUTOMATICA DE EJECUTABLE
echo ========================================
echo.

REM Verificar Python
echo [1/8] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo.
    echo Descarga Python desde: https://www.python.org/downloads/
    echo IMPORTANTE: Marca "Add Python to PATH" durante la instalacion
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% encontrado!

REM Verificar app.py
echo [2/8] Verificando archivos...
if not exist "app.py" (
    echo ERROR: app.py no encontrado en el directorio actual
    echo.
    echo Asegurate de que este script este en la misma carpeta que app.py
    echo.
    pause
    exit /b 1
)
echo app.py encontrado

REM Crear requirements.txt si no existe
if not exist "requirements.txt" (
    echo Creando requirements.txt...
    echo mysql-connector-python==8.2.0> requirements.txt
    echo pyinstaller==6.1.0>> requirements.txt
)

REM Crear entorno virtual si no existe
echo [3/8] Configurando entorno virtual...
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ERROR: No se pudo crear entorno virtual
        pause
        exit /b 1
    )
) else (
    echo Entorno virtual ya existe
)

REM Activar entorno virtual
echo [4/8] Activando entorno virtual...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo ERROR: No se pudo activar entorno virtual
    pause
    exit /b 1
)

REM Actualizar pip
echo [5/8] Actualizando pip...
python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo WARNING: No se pudo actualizar pip, continuando...
)

REM Instalar dependencias
echo [6/8] Instalando dependencias...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias
    echo.
    echo Intentando instalacion manual...
    pip install mysql-connector-python pyinstaller
    if %errorlevel% neq 0 (
        echo ERROR: Instalacion manual fallida
        pause
        exit /b 1
    )
)

REM Verificar instalacion
python -c "import mysql.connector; import tkinter; print('Dependencias OK')" 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Las dependencias no se instalaron correctamente
    pause
    exit /b 1
)

echo Dependencias instaladas correctamente

REM Limpiar builds anteriores
echo [7/8] Limpiando builds anteriores...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist *.spec del *.spec 2>nul

REM Crear ejecutable
echo [8/8] Creando ejecutable...
echo.
echo Esto puede tomar entre 2-10 minutos dependiendo de tu PC...
echo Por favor espera...
echo.

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "CompanyRegistration" ^
    --hidden-import mysql.connector ^
    --hidden-import mysql.connector.pooling ^
    --hidden-import mysql.connector.constants ^
    --hidden-import mysql.connector.abstracts ^
    --hidden-import mysql.connector.conversion ^
    --hidden-import mysql.connector.cursor ^
    --hidden-import mysql.connector.errorcode ^
    --hidden-import mysql.connector.errors ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.messagebox ^
    --hidden-import tkinter.scrolledtext ^
    --hidden-import tkinter.filedialog ^
    --hidden-import tkinter.font ^
    --hidden-import tkinter.constants ^
    --exclude-module matplotlib ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module test ^
    --exclude-module unittest ^
    app.py

REM Verificar resultado
if exist "dist\CompanyRegistration.exe" (
    echo.
    echo ========================================
    echo   EXITO: EJECUTABLE CREADO
    echo ========================================
    echo.
    echo Ubicacion: %cd%\dist\CompanyRegistration.exe
    
    REM Obtener tamaño del archivo
    for %%A in (dist\CompanyRegistration.exe) do (
        set /a size_mb=%%~zA/1024/1024
        echo Tamaño: !size_mb! MB
    )
    
    REM Crear estructura de distribucion
    if not exist "ejecutable_final" mkdir ejecutable_final
    copy "dist\CompanyRegistration.exe" "ejecutable_final\" >nul
    
    REM Crear instrucciones
    echo EJECUTABLE PARA WINDOWS> ejecutable_final\INSTRUCCIONES.txt
    echo ======================>> ejecutable_final\INSTRUCCIONES.txt
    echo.>> ejecutable_final\INSTRUCCIONES.txt
    echo Archivo: CompanyRegistration.exe>> ejecutable_final\INSTRUCCIONES.txt
    echo Creado: %date% %time%>> ejecutable_final\INSTRUCCIONES.txt
    echo Tamaño: !size_mb! MB>> ejecutable_final\INSTRUCCIONES.txt
    echo.>> ejecutable_final\INSTRUCCIONES.txt
    echo COMO USAR:>> ejecutable_final\INSTRUCCIONES.txt
    echo 1. Hacer doble clic en CompanyRegistration.exe>> ejecutable_final\INSTRUCCIONES.txt
    echo 2. No requiere instalacion adicional>> ejecutable_final\INSTRUCCIONES.txt
    echo 3. Funciona en Windows 7 o superior>> ejecutable_final\INSTRUCCIONES.txt
    echo.>> ejecutable_final\INSTRUCCIONES.txt
    echo CONFIGURACION:>> ejecutable_final\INSTRUCCIONES.txt
    echo - Se conecta automaticamente a la base de datos>> ejecutable_final\INSTRUCCIONES.txt
    echo - No requiere configuracion manual>> ejecutable_final\INSTRUCCIONES.txt
    echo.>> ejecutable_final\INSTRUCCIONES.txt
    echo DISTRIBUCION:>> ejecutable_final\INSTRUCCIONES.txt
    echo - Copiar solo el archivo .exe>> ejecutable_final\INSTRUCCIONES.txt
    echo - O comprimir toda la carpeta ejecutable_final>> ejecutable_final\INSTRUCCIONES.txt
    echo - Enviar por email, USB, red, etc.>> ejecutable_final\INSTRUCCIONES.txt
    
    echo.
    echo ARCHIVOS CREADOS:
    echo   ejecutable_final\CompanyRegistration.exe
    echo   ejecutable_final\INSTRUCCIONES.txt
    echo.
    echo PARA DISTRIBUIR:
    echo   1. Copia la carpeta 'ejecutable_final' completa
    echo   2. O solo el archivo CompanyRegistration.exe
    echo   3. Funciona sin instalacion en cualquier Windows
    echo.
    
    REM Preguntar si probar
    set /p test="¿Probar el ejecutable ahora? (s/n): "
    if /i "!test!"=="s" (
        echo Abriendo ejecutable...
        start ejecutable_final\CompanyRegistration.exe
    )
    
    echo.
    echo PROCESO COMPLETADO EXITOSAMENTE!
    
) else (
    echo.
    echo ========================================
    echo   ERROR: NO SE PUDO CREAR EJECUTABLE
    echo ========================================
    echo.
    echo Posibles causas:
    echo - Dependencias faltantes
    echo - Antivirus bloqueando PyInstaller
    echo - Espacio insuficiente en disco
    echo - Permisos insuficientes
    echo.
    echo Revisa los mensajes de error arriba
    echo.
)

echo.
echo Presiona cualquier tecla para cerrar...
pause >nul