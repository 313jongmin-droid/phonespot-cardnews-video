param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"

$installerRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$phoneRoot = "C:\Users\di898\Documents\phonespot_cardnews"
$shortsRoot = Join-Path $phoneRoot "shorts"
$scriptsRoot = Join-Path $shortsRoot "scripts"
$codexDocs = Join-Path $shortsRoot "codex"
$backupsRoot = Join-Path $installerRoot "backups"

function Assert-InRoot {
    param(
        [string]$Path,
        [string]$Root
    )

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
    $prefix = $resolvedRoot + [IO.Path]::DirectorySeparatorChar
    if (-not $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify a path outside the approved root: $resolved"
    }
    return $resolved
}

function Add-ExistingFile {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Path,
        [string]$Root
    )

    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $List.Add((Assert-InRoot -Path $Path -Root $Root))
    }
}

function Add-ExistingDirectory {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Path,
        [string]$Root
    )

    if (Test-Path -LiteralPath $Path -PathType Container) {
        $List.Add((Assert-InRoot -Path $Path -Root $Root))
    }
}

$files = [System.Collections.Generic.List[string]]::new()
$directories = [System.Collections.Generic.List[string]]::new()

Add-ExistingDirectory -List $directories -Path (Join-Path $installerRoot "__pycache__") -Root $installerRoot
Add-ExistingDirectory -List $directories -Path (Join-Path $scriptsRoot "__pycache__") -Root $phoneRoot
Add-ExistingDirectory -List $directories -Path (Join-Path $shortsRoot "out_codex\_raw") -Root $phoneRoot

Get-ChildItem -LiteralPath $scriptsRoot -File -Force |
    Where-Object {
        (
            $_.Name -like "codex_*.bak*" -or
            $_.Name -like "codex_*.syncpackbak*" -or
            $_.Name -like "codex_*.contextoverwritebak*" -or
            $_.Name -like "finalize_sns_video.py.bak*"
        )
    } |
    ForEach-Object { Add-ExistingFile -List $files -Path $_.FullName -Root $phoneRoot }

Get-ChildItem -LiteralPath $shortsRoot -File -Force |
    Where-Object { $_.Name -like "run_codex_casual.bat.bak*" } |
    ForEach-Object { Add-ExistingFile -List $files -Path $_.FullName -Root $phoneRoot }

Get-ChildItem -LiteralPath $codexDocs -File -Force |
    Where-Object { $_.Name -like "*.bak*" } |
    ForEach-Object { Add-ExistingFile -List $files -Path $_.FullName -Root $phoneRoot }

$baselineZips = @(
    Get-ChildItem -LiteralPath $backupsRoot -File -Filter "CODEX_CURRENT_BASELINE_*.zip" |
        Sort-Object LastWriteTime -Descending
)
if ($baselineZips.Count -gt 1) {
    $baselineZips |
        Select-Object -Skip 1 |
        ForEach-Object { Add-ExistingFile -List $files -Path $_.FullName -Root $installerRoot }
}

Add-ExistingFile `
    -List $files `
    -Path (Join-Path $installerRoot "APPLY_CODEX_REUSABLE_ILLUSTRATION_PROMPTS.py") `
    -Root $installerRoot

$fileBytes = 0
foreach ($file in $files) {
    $fileBytes += (Get-Item -LiteralPath $file).Length
}
$directoryBytes = 0
foreach ($directory in $directories) {
    $directoryBytes += (
        Get-ChildItem -LiteralPath $directory -File -Recurse -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum
    ).Sum
}

Write-Host "============================================================"
Write-Host " PhoneSpot Codex - Confirmed Junk Cleanup"
Write-Host "============================================================"
Write-Host ""
Write-Host "Mode: $(if ($Apply) { 'DELETE' } else { 'PREVIEW ONLY' })"
Write-Host ""
Write-Host "Files: $($files.Count)"
foreach ($file in $files) {
    Write-Host "  [FILE] $file"
}
Write-Host ""
Write-Host "Directories: $($directories.Count)"
foreach ($directory in $directories) {
    Write-Host "  [DIR ] $directory"
}
Write-Host ""
Write-Host ("Estimated cleanup: {0:N2} MB" -f (($fileBytes + $directoryBytes) / 1MB))

if (-not $Apply) {
    Write-Host ""
    Write-Host "[PREVIEW] Nothing was deleted."
    exit 0
}

foreach ($file in $files) {
    Remove-Item -LiteralPath $file -Force
}
foreach ($directory in $directories) {
    Remove-Item -LiteralPath $directory -Recurse -Force
}

Write-Host ""
Write-Host "[OK] Confirmed junk deleted."

