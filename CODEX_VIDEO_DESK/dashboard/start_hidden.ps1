param(
  [switch]$NoBrowser
)

$ErrorActionPreference = "Continue"
$desk = Split-Path -Parent $PSScriptRoot
$port = 4901

# Keep volatile panel state beside the local project.
# CODEX_VIDEO_DESK\TEMP is already runtime-only and ignored by Git.
$localRoot = Join-Path $desk "TEMP\panel"
$pidFile = Join-Path $localRoot "panel_server.pid"
$logDir = Join-Path $localRoot "panel_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

Write-Host "[panel] desk: $desk"
Write-Host "[panel] local state: $localRoot"
Write-Host "[panel] cleanup old PhoneSpot panel servers"

# 1) Kill last known local server PID.
if (Test-Path $pidFile) {
  try {
    $oldPid = [int](Get-Content $pidFile -Raw)
    if ($oldPid -gt 0) {
      Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
      Write-Host "  stopped pid-file PID $oldPid"
    }
  } catch {}
}

# 2) Kill any Python/Powershell process that is clearly running this dashboard server.
try {
  $needle = [regex]::Escape((Join-Path $desk "dashboard\server.py"))
  $procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -match "dashboard\\server\.py" -or $_.CommandLine -match $needle)
  }
  foreach ($p in $procs) {
    try {
      Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
      Write-Host "  stopped dashboard server PID $($p.ProcessId)"
    } catch {}
  }
} catch {}

# 3) Best-effort cleanup by local port.
try {
  $raw = cmd /c "netstat -ano | findstr :$port"
  foreach ($line in ($raw -split "`r?`n")) {
    if (-not ($line -match "LISTENING")) { continue }
    $parts = $line.Trim() -split "\s+"
    if ($parts.Count -ge 5) {
      $pidText = $parts[$parts.Count - 1]
      if ($pidText -match "^\d+$") {
        Stop-Process -Id ([int]$pidText) -Force -ErrorAction SilentlyContinue
        Write-Host "  stopped port PID $pidText"
      }
    }
  }
} catch {}

Start-Sleep -Milliseconds 800

$log = Join-Path $logDir ("panel_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")
$deskEsc = $desk.Replace("'", "''")
$logEsc = $log.Replace("'", "''")
$cmd = @"
`$env:PHONESPOT_PANEL_PORT='4901'
`$env:PHONESPOT_PANEL_NO_BROWSER='1'
Set-Location -LiteralPath '$deskEsc'
python 'dashboard\server.py' *> '$logEsc'
"@

$proc = Start-Process powershell.exe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $cmd) -WindowStyle Hidden -PassThru
try {
  $proc.Id | Set-Content -Path $pidFile -Encoding ascii
} catch {
  Write-Host "  [WARN] Could not write local pid file: $($_.Exception.Message)"
}
Write-Host "[panel] started wrapper PID $($proc.Id)"
Write-Host "[panel] log: $log"

Start-Sleep -Seconds 2
if (-not $NoBrowser) {
  Start-Process "http://localhost:$port/"
}
