@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start.ps1" %*
if errorlevel 1 (
    echo Setup or startup failed. See the message above.
    pause
    exit /b 1
)
