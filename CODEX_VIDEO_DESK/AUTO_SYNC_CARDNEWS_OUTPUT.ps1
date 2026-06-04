$ErrorActionPreference = "Continue"

$source = "\\192.168.0.7\phonespot_cardnews\cardnews\output"
$desk = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Resolve-Path (Join-Path $desk "..")
$target = Join-Path $root "cardnews\output"

Write-Host "[sync] cardnews output"
Write-Host "       source: $source"
Write-Host "       target: $target"

if (-not (Test-Path $source)) {
  Write-Host "[sync][skip] source not reachable"
  exit 0
}

New-Item -ItemType Directory -Force -Path $target | Out-Null

$robocopy = Get-Command robocopy.exe -ErrorAction SilentlyContinue
if ($robocopy) {
  robocopy $source $target /E /XO /FFT /R:1 /W:1 /XD __pycache__ /XF *.tmp | Out-Host
  $code = $LASTEXITCODE
  if ($code -le 7) {
    Write-Host "[sync][ok] robocopy code=$code"
    exit 0
  }
  Write-Host "[sync][warn] robocopy code=$code"
  exit 0
}

try {
  Copy-Item -Path (Join-Path $source "*") -Destination $target -Recurse -Force
  Write-Host "[sync][ok] Copy-Item complete"
} catch {
  Write-Host "[sync][warn]" $_.Exception.Message
}
exit 0
