$ErrorActionPreference = "Continue"

$sourceRoot = "\\192.168.0.7\phonespot_cardnews\cardnews"
$desk = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $desk "..")
$targetRoot = Join-Path $root "cardnews"

Write-Host "============================================================"
Write-Host " PhoneSpot Codex - Sync Cardnews Workspace"
Write-Host "============================================================"
Write-Host "[source] $sourceRoot"
Write-Host "[target] $targetRoot"

if (-not (Test-Path $sourceRoot)) {
  Write-Host "[sync][skip] source not reachable"
  exit 0
}

New-Item -ItemType Directory -Force -Path $targetRoot | Out-Null

$folders = @("articles", "images", "output")
$robocopy = Get-Command robocopy.exe -ErrorAction SilentlyContinue

foreach ($name in $folders) {
  $source = Join-Path $sourceRoot $name
  $target = Join-Path $targetRoot $name
  Write-Host ""
  Write-Host "[sync] $name"
  Write-Host "       $source"
  Write-Host "       -> $target"

  if (-not (Test-Path $source)) {
    Write-Host "[sync][skip] missing source folder: $name"
    continue
  }

  New-Item -ItemType Directory -Force -Path $target | Out-Null

  if ($robocopy) {
    robocopy $source $target /E /XO /FFT /R:1 /W:1 /XD __pycache__ .git /XF *.tmp | Out-Host
    $code = $LASTEXITCODE
    if ($code -le 7) {
      Write-Host "[sync][ok] $name robocopy code=$code"
      continue
    }
    Write-Host "[sync][warn] $name robocopy code=$code"
    continue
  }

  try {
    Copy-Item -Path (Join-Path $source "*") -Destination $target -Recurse -Force
    Write-Host "[sync][ok] $name Copy-Item complete"
  } catch {
    Write-Host "[sync][warn] $name" $_.Exception.Message
  }
}

Write-Host ""
Write-Host "[OK] Cardnews workspace sync finished."
exit 0
