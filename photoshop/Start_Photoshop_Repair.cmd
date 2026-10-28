@echo off
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File "%~dp0Start_Photoshop_Repair.ps1"
if errorlevel 1 pause
