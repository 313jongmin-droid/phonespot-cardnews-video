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

$statusDir = Join-Path $desk "TEMP"
New-Item -ItemType Directory -Force -Path $statusDir | Out-Null
$statusFile = Join-Path $statusDir "cardnews_sync_status.json"
$syncStart = Get-Date
$syncOk = $true
$syncMessage = "동기화 완료"

if (-not (Test-Path $sourceRoot)) {
  Write-Host "[sync][skip] source not reachable"
  $syncOk = $false
  $syncMessage = "대표 PC 공유폴더에 접근할 수 없습니다."
  $status = [ordered]@{
    ok = $syncOk
    message = $syncMessage
    startedAt = $syncStart.ToString("yyyy-MM-dd HH:mm:ss")
    endedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    source = $sourceRoot
    target = $targetRoot
    articles = 0
    images = 0
    output = 0
  }
  try { $status | ConvertTo-Json -Depth 4 | Set-Content -Path $statusFile -Encoding utf8 } catch {}
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


$counts = @{}
foreach ($name in @("articles", "images", "output")) {
  $folder = Join-Path $targetRoot $name
  if (Test-Path $folder) {
    $counts[$name] = @(Get-ChildItem -LiteralPath $folder -Force -ErrorAction SilentlyContinue).Count
  } else {
    $counts[$name] = 0
  }
}

$status = [ordered]@{
  ok = $syncOk
  message = $syncMessage
  startedAt = $syncStart.ToString("yyyy-MM-dd HH:mm:ss")
  endedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  source = $sourceRoot
  target = $targetRoot
  articles = $counts["articles"]
  images = $counts["images"]
  output = $counts["output"]
}
try {
  $status | ConvertTo-Json -Depth 4 | Set-Content -Path $statusFile -Encoding utf8
} catch {
  Write-Host "[sync][warn] could not write status:" $_.Exception.Message
}

Write-Host ""
Write-Host "[OK] Cardnews workspace sync finished."
exit 0
