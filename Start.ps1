param([switch]$SetupOnly, [switch]$Offline, [switch]$Repair, [switch]$NoBrowser, [int]$Port = 0)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$taskRoot = $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not [Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
    throw 'This package supports x64 Intel/AMD Windows PCs. ARM64 needs a separate package.'
}
$taskRuntime = Join-Path $taskRoot '.runtime'
$taskPython = Join-Path $taskRuntime 'python.exe'
$taskData = Join-Path $taskRoot 'data'
New-Item -ItemType Directory -Force -Path $taskRuntime, $taskData | Out-Null
try {
    $taskSetupLock = [IO.File]::Open((Join-Path $taskRuntime 'setup.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
} catch { throw 'Another installer or launcher is active for this folder. Wait for it to finish.' }
try {
$taskServerFile = Join-Path $taskData 'server.json'
if (Test-Path -LiteralPath $taskServerFile) {
    $taskRunning = $null
    try {
        $taskServer = Get-Content -Raw -LiteralPath $taskServerFile | ConvertFrom-Json
        $taskRunning = Invoke-RestMethod -Uri "$($taskServer.url)/api/health" -TimeoutSec 2
    } catch { }
    if ($null -ne $taskRunning -and $taskRunning.app -eq 'janvi-image-resize') {
        if ($Repair) { throw 'Stop the running dashboard before repairing its runtime.' }
        if (-not $NoBrowser -and -not $SetupOnly) { Start-Process $taskServer.url }
        Write-Host "Already running: $($taskServer.url)"
        exit 0
    }
}
$taskRequirements = Join-Path $taskRoot 'requirements.txt'
$taskFingerprint = (Get-FileHash -LiteralPath $taskRequirements -Algorithm SHA256).Hash
$taskStamp = Join-Path $taskRuntime 'installed.sha256'
if (-not (Test-Path -LiteralPath $taskPython)) {
    $taskArchive = Join-Path $taskRoot 'runtime-python.zip'
    $taskCachedArchive = Join-Path $taskRoot '.build\runtime-python.zip'
    if (-not (Test-Path -LiteralPath $taskArchive) -and (Test-Path -LiteralPath $taskCachedArchive)) {
        $taskArchive = $taskCachedArchive
    }
    if (-not (Test-Path -LiteralPath $taskArchive)) {
        if ($Offline) { throw 'Offline runtime archive missing. Use the complete offline ZIP.' }
        Write-Host 'Downloading private Python 3.11.9 runtime...'
        # The package manifest pins the redistributable and verifies it before extraction.
        $taskManifest = Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'runtime-manifest.json') | ConvertFrom-Json
        Invoke-WebRequest -UseBasicParsing -Uri $taskManifest.url -OutFile "$taskArchive.partial"
        if ((Get-FileHash -LiteralPath "$taskArchive.partial" -Algorithm SHA256).Hash -ne $taskManifest.sha256) {
            throw 'Python download checksum mismatch.'
        }
        Move-Item -LiteralPath "$taskArchive.partial" -Destination $taskArchive -Force
    }
    $taskManifest = Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'runtime-manifest.json') | ConvertFrom-Json
    if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash -ne $taskManifest.sha256) {
        throw 'Python archive checksum mismatch.'
    }
    Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskRuntime -Force
    $taskPth = Join-Path $taskRuntime 'python311._pth'
    Set-Content -LiteralPath $taskPth -Encoding ascii -Value @('python311.zip', '.', 'Lib\site-packages', '..', 'import site')
}
$taskRedist = Join-Path $taskRoot 'redist'
if (-not (Test-Path -LiteralPath $taskRedist)) { $taskRedist = Join-Path $taskRoot '.build\redist' }
if (Test-Path -LiteralPath $taskRedist) {
    foreach ($taskDll in (Get-ChildItem -LiteralPath $taskRedist -Filter '*.dll')) {
        $taskDllTarget = Join-Path $taskRuntime $taskDll.Name
        if (-not (Test-Path -LiteralPath $taskDllTarget) -or (Get-FileHash -LiteralPath $taskDll.FullName).Hash -ne (Get-FileHash -LiteralPath $taskDllTarget).Hash) {
            Copy-Item -LiteralPath $taskDll.FullName -Destination $taskDllTarget -Force
        }
    }
}
if ($Repair -or -not (Test-Path -LiteralPath $taskStamp) -or (Get-Content -Raw -LiteralPath $taskStamp).Trim() -ne $taskFingerprint) {
    Write-Host 'Installing verified application dependencies into the private runtime...'
    $taskWheels = Join-Path $taskRoot 'wheels'
    $taskCachedWheels = Join-Path $taskRoot '.build\wheels'
    if (-not (Test-Path -LiteralPath $taskWheels) -and (Test-Path -LiteralPath $taskCachedWheels)) {
        $taskWheels = $taskCachedWheels
    }
    if (-not (Test-Path -LiteralPath $taskWheels)) {
        if ($Offline) { throw 'Dependency wheels missing. Use the prepared offline ZIP.' }
        New-Item -ItemType Directory -Force -Path $taskWheels | Out-Null
    }
    $taskRelease = Get-Content -Raw -LiteralPath (Join-Path $taskRoot 'package-manifest.json') | ConvertFrom-Json
    foreach ($taskWheel in $taskRelease.wheels) {
        $taskWheelPath = Join-Path $taskWheels $taskWheel.file
        if (-not (Test-Path -LiteralPath $taskWheelPath)) {
            if ($Offline) { throw "Missing offline wheel: $($taskWheel.file)" }
            Write-Host "Downloading $($taskWheel.file)..."
            Invoke-WebRequest -UseBasicParsing -Uri $taskWheel.url -OutFile "$taskWheelPath.partial"
            Move-Item -LiteralPath "$taskWheelPath.partial" -Destination $taskWheelPath -Force
        }
        if ((Get-FileHash -LiteralPath $taskWheelPath -Algorithm SHA256).Hash -ne $taskWheel.sha256) {
            throw "Dependency checksum mismatch: $($taskWheel.file)"
        }
    }
    # pip is bundled as a wheel and invoked without installing anything globally.
    $taskPipWheel = Get-ChildItem -LiteralPath $taskWheels -Filter 'pip-*.whl' | Select-Object -First 1
    if ($null -eq $taskPipWheel) { throw 'Installer wheel missing from release.' }
    $taskOldPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = $taskPipWheel.FullName
    # The embedded runtime ignores PYTHONPATH: invoke the wheel through explicit sys.path.
    & $taskPython -c "import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')" $taskPipWheel.FullName install --no-index --no-deps --find-links $taskWheels --target (Join-Path $taskRuntime 'Lib\site-packages') --upgrade -r $taskRequirements
    $env:PYTHONPATH = $taskOldPythonPath
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Run Start.cmd -Repair after correcting the error.' }
    Set-Content -LiteralPath $taskStamp -Value $taskFingerprint -Encoding ascii
}
& $taskPython -c "import flask, PIL, numpy, onnxruntime, psutil, waitress"
if ($LASTEXITCODE -ne 0) { throw 'Runtime validation failed. Run Start.cmd -Repair.' }
if ($SetupOnly) { Write-Host 'Setup complete.'; exit 0 }
$taskServerFile = Join-Path $taskData 'server.json'
if (Test-Path -LiteralPath $taskServerFile) {
    try {
        $taskServer = Get-Content -Raw -LiteralPath $taskServerFile | ConvertFrom-Json
        $taskHealth = Invoke-RestMethod -Uri "$($taskServer.url)/api/health" -TimeoutSec 2
        if ($taskHealth.app -eq 'janvi-image-resize') {
            if (-not $NoBrowser) { Start-Process $taskServer.url }
            Write-Host "Already running: $($taskServer.url)"
            exit 0
        }
    } catch { }
}
$taskArguments = @('"' + (Join-Path $taskRoot 'launch.py') + '"', '--port', "$Port")
if ($NoBrowser) { $taskArguments += '--no-browser' }
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArguments -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskData 'server.log') -RedirectStandardError (Join-Path $taskData 'server-error.log')
for ($taskAttempt = 0; $taskAttempt -lt 40; $taskAttempt++) {
    Start-Sleep -Milliseconds 250
    $taskProcess.Refresh()
    if ($taskProcess.HasExited) { throw "Server exited. Read data\server-error.log." }
    if (Test-Path -LiteralPath $taskServerFile) {
        $taskServer = Get-Content -Raw -LiteralPath $taskServerFile | ConvertFrom-Json
        if ($taskServer.pid -eq $taskProcess.Id) {
            Write-Host "Dashboard running: $($taskServer.url)"
            exit 0
        }
    }
}
throw 'Startup timed out. Read data\server-error.log.'

} finally { $taskSetupLock.Dispose() }
