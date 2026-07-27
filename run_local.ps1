# PowerShell script to run the Logo Processor Dashboard locally
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting Subject-Aware Logo Processor Dashboard Locally" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "Using virtual environment at .venv..." -ForegroundColor Green
    & .venv\Scripts\python.exe app.py
} else {
    Write-Host "[WARNING] Virtual environment (.venv) not found." -ForegroundColor Yellow
    Write-Host "Attempting to start using system python..." -ForegroundColor Yellow
    & python app.py
}

Write-Host ""
Write-Host "Server has stopped." -ForegroundColor Cyan
Read-Host -Prompt "Press Enter to exit"
