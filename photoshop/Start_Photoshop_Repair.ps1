param([string]$PhotoshopPath, [string]$QueueDirectory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
try {
    $scriptPath = Join-Path $QueueDirectory 'Repair_Padding.jsx'
    if (!(Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw 'Repair_Padding.jsx is missing. Keep the .janvi repair workspace beside the resized images.' }
    if (!$PhotoshopPath) {
        $adobe = Join-Path $env:ProgramFiles 'Adobe'
        $candidates = @(Get-ChildItem -LiteralPath $adobe -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like 'Adobe Photoshop *' -and $_.Name -notmatch 'Beta' } |
            Sort-Object Name -Descending |
            ForEach-Object { Join-Path $_.FullName 'Photoshop.exe' } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
        if ($candidates.Count -ne 1) { throw 'Could not choose one regular Photoshop installation. Run this PS1 with -PhotoshopPath pointing to your Photoshop.exe, or use File > Scripts > Browse.' }
        $PhotoshopPath = $candidates[0]
    }
    $PhotoshopPath = (Resolve-Path -LiteralPath $PhotoshopPath).Path
    if ([IO.Path]::GetFileName($PhotoshopPath) -ne 'Photoshop.exe') { throw 'Choose Photoshop.exe.' }
    $other = @(Get-Process -Name Photoshop -ErrorAction SilentlyContinue | Where-Object { !$_.Path -or $_.Path -ne $PhotoshopPath })
    if ($other.Count) { throw 'Another Photoshop version is open. Save your work and close it before launching the selected version. Nothing was closed automatically.' }
    Write-Output ('Opening: ' + $PhotoshopPath)
    Write-Output 'If Photoshop asks whether to run Repair_Padding.jsx, choose Yes to start the repair.'
    Start-Process -FilePath $PhotoshopPath -ArgumentList ('"' + $scriptPath + '"')
} catch { Write-Error $_; exit 1 }
