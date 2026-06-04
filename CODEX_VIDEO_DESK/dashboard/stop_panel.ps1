$ErrorActionPreference = "SilentlyContinue"
$port = 4878
$lines = cmd /c "netstat -ano | findstr :$port"
if (-not $lines) {
  Write-Host "[OK] Control panel server is not running on 4878."
  Start-Sleep -Seconds 1
  exit 0
}
$pids = @()
foreach ($line in $lines) {
  if ($line -match "LISTENING\s+(\d+)$") { $pids += [int]$Matches[1] }
}
$pids = $pids | Select-Object -Unique
foreach ($pid in $pids) {
  Write-Host "[stop] pid=$pid"
  taskkill /PID $pid /F | Out-Host
}
Write-Host "[OK] Control panel server stopped."
Start-Sleep -Seconds 1
