@echo off
title Sync API System - Reconfigurar

cd /d "%~dp0"

echo ========================================
echo   SYNC API SYSTEM - RECONFIGURAR
echo ========================================
echo.
echo ADVERTENCIA: Esto borrara la configuracion actual
echo.
pause

echo.
echo Borrando configuracion...
echo.

SyncAPISystem.exe --mode reconfig

echo.
pause
