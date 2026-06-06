param(
  [string]$TargetDir = "C:\PhoneSpot\phonespot_cardnews",
  [Parameter(Mandatory=$true)]
  [string]$PanelUrl
)

$ErrorActionPreference = "Stop"
$repo = "https://github.com/313jongmin-droid/phonespot-cardnews-video.git"

if ([string]::IsNullOrWhiteSpace($TargetDir)) {
  $TargetDir = "C:\PhoneSpot\phonespot_cardnews"
}

Write-Host "[target] $TargetDir"

function Find-Git {
  $cmd = Get-Command git.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }

  $candidates = @(
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files\Git\bin\git.exe"
  )

  $local = $env:LOCALAPPDATA
  if ($local) {
    $desktop = Join-Path $local "GitHubDesktop"
    if (Test-Path $desktop) {
      $candidates += Get-ChildItem -Path $desktop -Filter git.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like "*\resources\app\git\cmd\git.exe" } |
        Sort-Object FullName -Descending |
        ForEach-Object { $_.FullName }
    }
  }

  foreach ($p in $candidates) {
    if (Test-Path $p) { return $p }
  }
  return $null
}

function Ensure-WingetPackage($exe, $id, $label) {
  if (Get-Command $exe -ErrorAction SilentlyContinue) {
    Write-Host "[OK] $label found"
    return
  }
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "$label is missing, and winget is not available. Install it manually first."
  }
  Write-Host "[install] $label via winget"
  winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements
}

Ensure-WingetPackage "node.exe" "OpenJS.NodeJS.LTS" "Node.js"
Ensure-WingetPackage "python.exe" "Python.Python.3.12" "Python"

$git = Find-Git
if (-not $git) {
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Host "[install] Git for Windows via winget"
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    $git = Find-Git
  }
}
if (-not $git) {
  throw "Git is missing. Install Git for Windows or GitHub Desktop first."
}
Write-Host "[git] $git"

$targetPath = [System.IO.Path]::GetFullPath($TargetDir)
$parent = Split-Path $targetPath
if (-not (Test-Path $parent)) {
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
}

if (Test-Path (Join-Path $targetPath ".git")) {
  Write-Host "[update] Existing Git workspace found. Pull latest."
  & $git -C $targetPath pull --ff-only
  if ($LASTEXITCODE -ne 0) { throw "Git pull failed." }
} elseif (Test-Path $targetPath) {
  $children = @(Get-ChildItem -LiteralPath $targetPath -Force -ErrorAction SilentlyContinue)
  if ($children.Count -gt 0) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backup = "${targetPath}_OLD_${stamp}"
    Write-Host "[backup] Target folder is not empty and is not Git."
    Write-Host "         Moving it to: $backup"
    Move-Item -LiteralPath $targetPath -Destination $backup
  }
  Write-Host "[clone] $repo"
  & $git clone $repo $targetPath
  if ($LASTEXITCODE -ne 0) { throw "Git clone failed." }
} else {
  Write-Host "[clone] $repo"
  & $git clone $repo $targetPath
  if ($LASTEXITCODE -ne 0) { throw "Git clone failed." }
}

$shorts = Join-Path $targetPath "shorts"
if (Test-Path (Join-Path $shorts "package.json")) {
  Write-Host "[deps] npm install"
  Push-Location $shorts
  cmd /c npm install
  if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
  Pop-Location
}

Write-Host "[deps] Project Python runtime"
$runtime = Join-Path $targetPath ".phonespot_runtime"
$runtimePython = Join-Path $runtime "Scripts\python.exe"
if (-not (Test-Path $runtimePython)) {
  python -m venv $runtime
  if ($LASTEXITCODE -ne 0) { throw "Python runtime creation failed." }
}
& $runtimePython -m pip install -q edge-tts mutagen pillow requests playwright
if ($LASTEXITCODE -ne 0) { throw "Python package install failed." }
& $runtimePython -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Playwright Chromium install failed." }

$desk = Join-Path $targetPath "CODEX_VIDEO_DESK"
$workerDir = Join-Path $desk "RENDER_WORKER"
$worker = Join-Path $desk "01_START_RENDER_WORKER.bat"
if ((Test-Path $workerDir) -and (Test-Path $worker)) {
  $PanelUrl.TrimEnd("/") | Set-Content -Path (Join-Path $workerDir "panel_url.txt") -Encoding utf8
  Write-Host "[OK] Setup complete."
  Write-Host "[panel] $PanelUrl"
  Write-Host "[worker] $worker"
  Start-Process -FilePath $worker -WorkingDirectory $desk
} else {
  throw "Render worker launcher was not found after clone."
}
