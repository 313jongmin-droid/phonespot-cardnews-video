$ErrorActionPreference = "Stop"

$legacyRoot = "C:\Users\di898\Documents\Codex"
$desk = "C:\Users\di898\Documents\phonespot_cardnews\CODEX_VIDEO_DESK"
$maintenance = Join-Path $desk "MAINTENANCE"

Write-Host "============================================================"
Write-Host " PhoneSpot Codex - Delete Old Documents Codex Folder"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath $legacyRoot)) {
    Write-Host "[INFO] Old Documents\Codex folder is already absent."
    exit 0
}

if (-not (Test-Path -LiteralPath (Join-Path $maintenance "RUN_APPLY_CODEX_CURRENT_BASELINE.bat"))) {
    throw "Maintenance copy is missing. Refusing to delete the old folder."
}

$resolved = (Resolve-Path -LiteralPath $legacyRoot).Path
if ($resolved -ne "C:\Users\di898\Documents\Codex") {
    throw "Unexpected legacy path: $resolved"
}

Write-Host "This removes only:"
Write-Host "  $resolved"
Write-Host ""
Write-Host "The CODEX_VIDEO_DESK folder is preserved."
Write-Host ""
$answer = Read-Host "Type DELETE to continue"
if ($answer -ne "DELETE") {
    Write-Host "[INFO] Cancelled."
    exit 0
}

Remove-Item -LiteralPath $resolved -Recurse -Force
Write-Host ""
Write-Host "[OK] Deleted old Documents\Codex folder."
