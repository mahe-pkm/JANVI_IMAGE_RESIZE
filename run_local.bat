@echo off
title Logo Processor Dashboard - Local
echo ==========================================================
echo   Starting Subject-Aware Logo Processor Dashboard Locally
echo ==========================================================
echo.

if exist .venv\Scripts\python.exe (
    echo Using virtual environment at .venv...
    .venv\Scripts\python.exe app.py
) else (
    echo WARNING: Virtual environment .venv not found.
    echo Attempting to start using system python...
    python app.py
)

echo.
echo Server has stopped.
pause
