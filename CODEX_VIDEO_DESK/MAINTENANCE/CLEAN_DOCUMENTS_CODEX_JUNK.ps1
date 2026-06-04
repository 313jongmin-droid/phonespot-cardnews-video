$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$prefix = $root + [IO.Path]::DirectorySeparatorChar

function Assert-ChildPath {
    param([string]$Path)

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (-not $resolved.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to delete a path outside the Codex workspace: $resolved"
    }
    return $resolved
}

Write-Host "============================================================"
Write-Host " PhoneSpot Codex - Delete Confirmed Test Junk"
Write-Host "============================================================"
Write-Host ""
Write-Host "Preserves installers, rollback tools, guides, and the latest baseline backup."
Write-Host ""

$generatedDirs = @(
    Get-ChildItem -LiteralPath $root -Directory -Force |
        Where-Object {
            $_.Name -eq "__pycache__" -or
            $_.Name -match "^_(caption|desk|fixed|fixture|lockstep|master|review|rollback|shared|test|tmp|verify)"
        }
)

$deletedDirs = 0
foreach ($dir in $generatedDirs) {
    $safePath = Assert-ChildPath $dir.FullName
    Write-Host "[delete dir] $safePath"
    Remove-Item -LiteralPath $safePath -Recurse -Force
    $deletedDirs++
}

$backupDir = Join-Path $root "backups"
$backups = @(
    Get-ChildItem -LiteralPath $backupDir -File -Filter "CODEX_CURRENT_BASELINE_*.zip" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending
)

$deletedBackups = 0
if ($backups.Count -gt 0) {
    Write-Host "[keep backup] $($backups[0].FullName)"
    foreach ($backup in ($backups | Select-Object -Skip 1)) {
        $safePath = Assert-ChildPath $backup.FullName
        Write-Host "[delete backup] $safePath"
        Remove-Item -LiteralPath $safePath -Force
        $deletedBackups++
    }
}

$remainingBytes = (
    Get-ChildItem -LiteralPath $root -Force -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object Length -Sum
).Sum

Write-Host ""
Write-Host "[OK] Deleted generated folders: $deletedDirs"
Write-Host "[OK] Deleted old backups: $deletedBackups"
Write-Host "[OK] Remaining workspace MB: $([math]::Round($remainingBytes / 1MB, 2))"
Write-Host ""

