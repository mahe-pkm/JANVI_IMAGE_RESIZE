# PowerShell script to run the Logo Processor Dashboard in Docker
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting Subject-Aware Logo Processor Dashboard in Docker" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Running docker-compose up --build..." -ForegroundColor Green
Write-Host ""

& docker-compose up --build

Write-Host ""
Write-Host "Container has stopped." -ForegroundColor Cyan
Read-Host -Prompt "Press Enter to exit"
