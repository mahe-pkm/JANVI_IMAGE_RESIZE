param(
    [string]$SourceRoot = "D:\Logo Process Janvi_resized\lOGO_PLACEMENT\Half saree lehenga_resized",
    [string]$TargetDir = "C:\Users\rough\Desktop\Logo Processing\May-20261\Re-sized\Final For Shopify\Half-saree"
)

# 1. Scan for all original product folders to build the mapping
$Mapping = @{}

# Add the source root itself to the mapping
$RootItem = Get-Item -Path $SourceRoot
$RootFolderName = $RootItem.Name
$RootClean = $RootFolderName -replace "_(selected_images|selected_image|selected|images_resized|images|resized)(\s*\(\d+\))?$", ""
$RootClean = $RootClean.Trim().Trim('_').Trim('-').Trim()
$Mapping[$RootClean.ToLower()] = $RootFolderName

# Add all subdirectories to the mapping
Get-ChildItem -Path $SourceRoot -Directory -Recurse | ForEach-Object {
    $FolderName = $_.Name
    # Skip export folders and date folders (which don't represent products)
    if ($FolderName -notmatch "^(25 may|26 may|untitled export|export)" -and $FolderName.Length -gt 3) {
        $CleanName = $FolderName -replace "_(selected_images|selected_image|selected|images_resized|images|resized)(\s*\(\d+\))?$", ""
        $CleanName = $CleanName.Trim().Trim('_').Trim('-').Trim()
        
        $Mapping[$CleanName.ToLower()] = $FolderName
    }
}

Write-Host "Built mapping for $($Mapping.Count) product folders."

# 2. Rename files in the target directory
$RenameCount = 0
Get-ChildItem -Path $TargetDir -File | ForEach-Object {
    $FileName = $_.Name
    $Extension = $_.Extension
    
    # Match pattern e.g., "Aavya Aura_1.jpg"
    if ($FileName -match "^(.+)_(\d+)\.[^.]+$") {
        $Prefix = $Matches[1]
        $Counter = $Matches[2]
        
        $Key = $Prefix.ToLower()
        if ($Mapping.ContainsKey($Key)) {
            $OriginalFolderName = $Mapping[$Key]
            $NewFileName = "${OriginalFolderName}_${Counter}${Extension}"
            
            # Avoid renaming if already named correctly
            if ($FileName -ne $NewFileName) {
                Write-Host "Renaming: $FileName -> $NewFileName"
                Rename-Item -Path $_.FullName -NewName $NewFileName -Force
                $RenameCount++
            }
        } else {
            Write-Host "Warning: No original folder match found for prefix '$Prefix' (file: $FileName)" -ForegroundColor Yellow
        }
    }
}

Write-Host "Completed. Renamed $RenameCount files."
