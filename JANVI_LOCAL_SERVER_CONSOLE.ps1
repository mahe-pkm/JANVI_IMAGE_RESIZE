param([int]$Port = 0)

$ErrorActionPreference = 'Stop'
$Host.UI.RawUI.WindowTitle = 'Janvi Image Studio | Local Server'
$Host.UI.RawUI.BackgroundColor = 'Black'
$Host.UI.RawUI.ForegroundColor = 'Gray'
Clear-Host

function Write-Rule {
    Write-Host ('=' * 70) -ForegroundColor DarkGray
}

function Write-Header {
    Clear-Host
    Write-Host ''
    Write-Host '  J  JANVI' -ForegroundColor White -BackgroundColor DarkGray
    Write-Host '     IMAGE STUDIO  /  LOCAL SERVER' -ForegroundColor DarkYellow
    Write-Host '     Built for Buzl' -ForegroundColor DarkGray
    Write-Host ''
    Write-Rule
}

function Read-Server {
    $state = Join-Path $PSScriptRoot 'data\server.json'
    if (-not (Test-Path -LiteralPath $state)) { return $null }
    try { return Get-Content -Raw -LiteralPath $state | ConvertFrom-Json } catch { return $null }
}

Write-Header
Write-Host '  Preparing your local workspace...' -ForegroundColor DarkYellow
Write-Host '  Images stay on this computer. Browser access is limited to 127.0.0.1.' -ForegroundColor Gray
Write-Host ''

try {
    & (Join-Path $PSScriptRoot 'Start.ps1') -Offline -Port $Port
} catch {
    Write-Host ''
    Write-Host '  Janvi could not start.' -ForegroundColor Red
    Write-Host "  $($_.Exception.Message)" -ForegroundColor Gray
    Write-Host '  Check data\server-error.log, then press any key to close.' -ForegroundColor DarkGray
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    exit 1
}

$server = Read-Server
Write-Header
Write-Host '  LOCAL WORKSPACE READY' -ForegroundColor Green
Write-Host ''
Write-Host '  Browser address' -ForegroundColor DarkGray
Write-Host "  $($server.url)" -ForegroundColor Cyan
Write-Host ''
Write-Host '  Status' -ForegroundColor DarkGray
Write-Host '  Running locally  |  image files never leave this PC' -ForegroundColor White
Write-Host ''
Write-Rule
Write-Host '  [O] Open browser again     [Q] Stop Janvi safely and close this console' -ForegroundColor DarkYellow
Write-Host '  Keep this window open while you work.' -ForegroundColor DarkGray

while ($true) {
    Start-Sleep -Milliseconds 200
    if (-not [Console]::KeyAvailable) { continue }
    $key = [Console]::ReadKey($true).Key
    if ($key -eq 'O') {
        $server = Read-Server
        if ($null -ne $server) {
            Start-Process $server.url
            Write-Host '  Opened Janvi in your default browser.' -ForegroundColor Green
        }
    }
    if ($key -eq 'Q') {
        Write-Host '  Requesting a safe stop...' -ForegroundColor DarkYellow
        try {
            & (Join-Path $PSScriptRoot 'Stop.ps1')
            Write-Host '  Janvi stopped. You can close this window.' -ForegroundColor Green
            Start-Sleep -Seconds 1
            exit 0
        } catch {
            Write-Host "  $($_.Exception.Message)" -ForegroundColor Red
            Write-Host '  Finish or cancel the active work first.' -ForegroundColor DarkGray
        }
    }
}
