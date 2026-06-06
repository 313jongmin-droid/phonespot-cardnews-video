$ErrorActionPreference = "SilentlyContinue"
$port = 4901
$desk = Split-Path -Parent $PSScriptRoot
$workerPidFile = Join-Path $desk "TEMP\worker\local_worker.pid"
if (Test-Path $workerPidFile) {
  try {
    $workerPid = [int](Get-Content $workerPidFile -Raw)
    if ($workerPid -gt 0) {
      Write-Host "[stop worker] pid=$workerPid"
      Stop-Process -Id $workerPid -Force -ErrorAction SilentlyContinue
    }
  } catch {}
  Remove-Item -LiteralPath $workerPidFile -Force -ErrorAction SilentlyContinue
}
$lines = cmd /c "netstat -ano | findstr :$port"
if (-not $lines) {
  Write-Host "[OK] Control panel server is not running on 4901."
  Start-Sleep -Seconds 1
  exit 0
}
$processIds = @()
foreach ($line in $lines) {
  if ($line -match "LISTENING\s+(\d+)$") { $processIds += [int]$Matches[1] }
}
$processIds = $processIds | Select-Object -Unique
foreach ($processId in $processIds) {
  Write-Host "[stop] pid=$processId"
  taskkill /PID $processId /F | Out-Host
}
Write-Host "[OK] Control panel server stopped."
Start-Sleep -Seconds 1
