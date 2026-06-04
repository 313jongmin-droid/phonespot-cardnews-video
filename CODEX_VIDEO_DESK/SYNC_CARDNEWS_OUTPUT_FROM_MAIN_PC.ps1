param(
  [string]$Source = "\\192.168.0.7\phonespot_cardnews\cardnews\output",
  [string]$TargetRoot = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($TargetRoot)) {
  $TargetRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$target = Join-Path $TargetRoot "cardnews\output"

Write-Host "============================================================"
Write-Host " PhoneSpot Codex - Sync Cardnews Output"
Write-Host "============================================================"
Write-Host "[source] $Source"
Write-Host "[target] $target"

if (-not (Test-Path $Source)) {
  throw "Source folder not found: $Source"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null

$robocopy = Get-Command robocopy.exe -ErrorAction SilentlyContinue
if ($robocopy) {
  Write-Host "[copy] robocopy mirror-lite"
  robocopy $Source $target /E /XO /FFT /R:2 /W:2 /XD __pycache__ /XF *.tmp
  $code = $LASTEXITCODE
  if ($code -le 7) {
    Write-Host "[OK] Sync complete. robocopy code=$code"
    exit 0
  }
  throw "robocopy failed. code=$code"
}

Write-Host "[copy] Copy-Item fallback"
Copy-Item -Path (Join-Path $Source "*") -Destination $target -Recurse -Force
Write-Host "[OK] Sync complete."
