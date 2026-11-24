@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0JANVI_LOCAL_SERVER_CONSOLE.ps1" %*
