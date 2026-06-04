@echo off
setlocal
chcp 65001 >nul
title PhoneSpot Codex - Setup Render PC

echo ============================================================
echo  PhoneSpot Codex - Render PC Setup
echo ============================================================
echo.
echo This setup makes this PC render videos locally.
echo It clones or updates the project from GitHub.
echo.

set "REPO_URL=https://github.com/313jongmin-droid/phonespot-cardnews-video.git"
set "DEFAULT_DIR=C:\PhoneSpot\phonespot_cardnews"
set /p "TARGET_DIR=Install folder [%DEFAULT_DIR%]: "
if "%TARGET_DIR%"=="" set "TARGET_DIR=%DEFAULT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "& {
  $ErrorActionPreference = 'Stop'
  $repo = 'https://github.com/313jongmin-droid/phonespot-cardnews-video.git'
  $target = $env:TARGET_DIR

  function Find-Git {
    $cmd = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
      'C:\Program Files\Git\cmd\git.exe',
      'C:\Program Files\Git\bin\git.exe'
    )
    $local = $env:LOCALAPPDATA
    if ($local) {
      $candidates += Get-ChildItem -Path (Join-Path $local 'GitHubDesktop') -Filter git.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like '*\resources\app\git\cmd\git.exe' } |
        Sort-Object FullName -Descending |
        ForEach-Object { $_.FullName }
    }
    foreach ($p in $candidates) {
      if (Test-Path $p) { return $p }
    }
    return $null
  }

  function Ensure-WingetPackage($name, $id) {
    if (Get-Command $name -ErrorAction SilentlyContinue) { return }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
      throw "$name is missing, and winget is not available. Install it manually first."
    }
    Write-Host "[install] $name via winget ($id)"
    winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements
  }

  Ensure-WingetPackage 'node.exe' 'OpenJS.NodeJS.LTS'
  Ensure-WingetPackage 'python.exe' 'Python.Python.3.12'

  $git = Find-Git
  if (-not $git) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
      Write-Host "[install] Git for Windows via winget"
      winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
      $git = Find-Git
    }
  }
  if (-not $git) { throw 'Git is missing. Install Git for Windows or GitHub Desktop first.' }
  Write-Host "[git] $git"

  if (Test-Path (Join-Path $target '.git')) {
    Write-Host "[update] existing project"
    & $git -C $target pull --ff-only
  } elseif (Test-Path $target) {
    $children = Get-ChildItem -LiteralPath $target -Force -ErrorAction SilentlyContinue
    if ($children.Count -gt 0) {
      throw "Target folder exists and is not empty: $target"
    }
    & $git clone $repo $target
  } else {
    New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
    & $git clone $repo $target
  }
  if ($LASTEXITCODE -ne 0) { throw 'Git clone/pull failed.' }

  $shorts = Join-Path $target 'shorts'
  if (Test-Path (Join-Path $shorts 'package.json')) {
    Write-Host "[deps] npm install"
    Push-Location $shorts
    cmd /c npm install
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
    Pop-Location
  }

  Write-Host "[deps] Python packages"
  python -m pip install -q edge-tts mutagen pillow requests

  $desk = Join-Path $target 'CODEX_VIDEO_DESK'
  $panel = Join-Path $desk '00_PHONE_SPOT_PANEL.bat'
  if (Test-Path $panel) {
    Write-Host "[OK] Setup complete."
    Write-Host "Panel: $panel"
    Start-Process -FilePath $panel -WorkingDirectory $desk
  } else {
    Write-Host "[OK] Setup complete, but panel launcher was not found."
  }
}"

if errorlevel 1 (
  echo.
  echo [ERROR] Setup failed.
  pause
  exit /b 1
)

echo.
echo [OK] Render PC setup finished.
pause
