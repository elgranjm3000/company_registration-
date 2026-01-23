@echo off
setlocal enabledelayedexpansion
title Crear Ejecutable - CON CONSOLA

echo ========================================
echo   CREAR EJECUTABLE CON CONSOLA
echo ========================================
echo.

if not exist "venv" (
    echo ERROR: Primero ejecuta CREAR_EXE.bat para crear el entorno virtual
    pause
    exit /b 1
)

call venv\Scripts\activate

echo.
echo Limpiando builds anteriores...
if exist build rmdir /s /q build 2>nul
if exist dist rmdir /s /q dist 2>nul
if exist *.spec del *.spec 2>nul

echo.
echo Creando ejecutable CON CONSOLA...
pyinstaller ^
    --onefile ^
    --console ^
    --name "sync_system_console" ^
    --add-data "smart_sync_complete.py;." ^
    --hidden-import psycopg2 ^
    --hidden-import psycopg2.extensions ^
    --hidden-import mysql.connector ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.scrolledtext ^
    sync_system.py

if exist "dist\sync_system_console.exe" (
    echo.
    echo EXITO: Ejecutable creado con consola
    echo Ubicacion: dist\sync_system_console.exe
    echo.
    echo Para ejecutar:
    echo   dist\sync_system_console.exe --mode config
)

pause
