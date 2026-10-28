$ErrorActionPreference = 'Stop'
$taskState = Join-Path $PSScriptRoot 'data\server.json'
if (Test-Path -LiteralPath $taskState) {
    $taskServer = Get-Content -Raw -LiteralPath $taskState | ConvertFrom-Json
    $taskProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($taskServer.pid)"
    $taskExpected = Join-Path $PSScriptRoot '.runtime\python.exe'
    if ($taskProcess -and $taskProcess.ExecutablePath -eq $taskExpected -and $taskProcess.CommandLine -like '*launch.py*') {
        $taskStatus = Invoke-RestMethod "$($taskServer.url)/api/status"
        if ($taskStatus.active) { throw 'Cancel the active job in the dashboard and wait for it to finish before stopping.' }
        Stop-Process -Id $taskServer.pid
        Remove-Item -LiteralPath $taskState -ErrorAction SilentlyContinue
        Write-Host 'Dashboard stopped.'
    } else { Write-Host 'No matching app process found.' }
}
