param(
  [switch]$NoBrowser,
  [switch]$NoWorker,
  [int]$Port = 4901
)

$ErrorActionPreference = "Stop"
$desk = Split-Path -Parent $PSScriptRoot
$root = Split-Path -Parent $desk
$port = $Port
$url = "http://127.0.0.1:$port"

# (2026-06-07) 옵트인 자동 업데이트: 수신(부사수) PC에서만.
# 마커 파일이 있으면 git pull 을 별도 cmd 로 먼저 수행한다(출력은 cmd 가 로그 파일로만 기록,
# 항상 exit 0 → 패널 시작에 절대 영향 없음). 버전 읽기 전에 실행해야 pull 로 바뀐
# PANEL_VERSION 이 곧바로 재시작 트리거가 된다. 대표 PC 는 마커를 켜지 않으면 아무 일도 안 함.
$autoUpdateMarker = Join-Path $desk "TEMP\panel\auto_update.on"
$autoUpdateCmd = Join-Path $PSScriptRoot "auto_update.cmd"
if ((Test-Path $autoUpdateMarker) -and (Test-Path $autoUpdateCmd)) {
  try { cmd.exe /c call "$autoUpdateCmd" | Out-Null } catch {}
}

# 버전은 server.py(PANEL_VERSION)를 단일 출처로 읽는다. 파싱 실패 시 아래 폴백 사용.
$expectedVersion = "phonespot-web-v21"
try {
  $serverPy = Join-Path $PSScriptRoot "server.py"
  $verMatch = Select-String -Path $serverPy -Pattern 'PANEL_VERSION\s*=\s*"([^"]+)"' -ErrorAction Stop | Select-Object -First 1
  if ($verMatch) { $expectedVersion = $verMatch.Matches[0].Groups[1].Value }
} catch {}
$tempRoot = Join-Path $desk "TEMP\panel"
$pidFile = Join-Path $tempRoot "panel_server_$port.pid"
$logDir = Join-Path $tempRoot "panel_logs"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-PanelHealth {
  try {
    $response = Invoke-RestMethod -Uri "$url/api/health" -TimeoutSec 2
    return [bool]$response.ok -and $response.version -eq $expectedVersion
  } catch {
    return $false
  }
}

if (-not (Test-PanelHealth)) {
  try {
    Invoke-RestMethod -Method Post -Uri "$url/api/shutdown" -ContentType "application/json" -Body "{}" -TimeoutSec 2 | Out-Null
    Start-Sleep -Milliseconds 700
  } catch {}
  if (Test-Path $pidFile) {
    try {
      $oldPid = [int](Get-Content $pidFile -Raw)
      if ($oldPid -gt 0) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
      }
    } catch {}
  }

  try {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
      Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
    }
  } catch {}
  try {
    $raw = cmd.exe /c "netstat -ano | findstr LISTENING | findstr :$port"
    foreach ($line in ($raw -split "`r?`n")) {
      $parts = $line.Trim() -split "\s+"
      if ($parts.Count -ge 5 -and $parts[-1] -match "^\d+$") {
        cmd.exe /c "taskkill /PID $($parts[-1]) /F" | Out-Null
      }
    }
  } catch {}
  Start-Sleep -Milliseconds 500

  $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
  $stdoutLog = Join-Path $logDir "panel_${stamp}.out.log"
  $stderrLog = Join-Path $logDir "panel_${stamp}.err.log"
  $server = Join-Path $PSScriptRoot "server.py"
  $runtimePython = Join-Path $root ".phonespot_runtime\Scripts\python.exe"
  $python = if (Test-Path $runtimePython) { $runtimePython } else { "python" }
  $launcher = Join-Path $tempRoot "launch_panel.cmd"
  @"
@echo off
set "PHONESPOT_PANEL_PORT=$port"
set "PHONESPOT_PANEL_NO_BROWSER=1"
set "PHONESPOT_PANEL_HOST=0.0.0.0"
set "PHONESPOT_AUTO_WORKER=$(if ($NoWorker) { '0' } else { '1' })"
set "PLAYWRIGHT_BROWSERS_PATH=$root\.playwright"
cd /d "$desk"
start "" /b "$python" "$server" 1>>"$stdoutLog" 2>>"$stderrLog"
"@ | Set-Content -Path $launcher -Encoding ascii
  cmd.exe /c call "$launcher"

  $healthy = $false
  for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-PanelHealth) {
      $healthy = $true
      break
    }
  }

  if (-not $healthy) {
    Write-Host "[ERROR] Panel server did not start."
    Write-Host "[log] $stderrLog"
    if (Test-Path $stderrLog) {
      Get-Content $stderrLog -Tail 40
    }
    exit 1
  }

  try {
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop | Select-Object -First 1
    if ($listener) {
      $listener.OwningProcess | Set-Content -Path $pidFile -Encoding ascii
    }
  } catch {}
}

Write-Host "[OK] PhoneSpot panel is running."
Write-Host "[local] http://localhost:$port/"
if (-not $NoWorker) { Write-Host "[worker] managed by the panel server." }

if (-not $NoBrowser) {
  cmd.exe /c "start `"`" `"http://localhost:$port/`""
}
