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
$expectedVersion = "phonespot-web-v8"
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
