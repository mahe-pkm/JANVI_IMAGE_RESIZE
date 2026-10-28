@echo off
setlocal
set "JANVI_FOLDER=%CD%"
if not "%~1"=="" set "JANVI_FOLDER=%~f1"
start "" "%~dp0Janvi Image Studio.exe" --folder "%JANVI_FOLDER%"
