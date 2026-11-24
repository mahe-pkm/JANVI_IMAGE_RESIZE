@echo off
setlocal
title Stop Janvi Image Studio Local Server
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Stop.ps1"
if errorlevel 1 (
    echo.
    echo Janvi could not be stopped. Read the message above, then press any key to close.
    pause >nul
)
