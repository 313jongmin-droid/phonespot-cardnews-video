@echo off
setlocal
chcp 65001 >nul
title PhoneSpot Codex - Setup Render PC

echo ============================================================
echo  PhoneSpot Codex - Render PC Setup
echo ============================================================
echo.
echo This setup installs the local render workspace on this PC.
echo Press Enter to use the default folder:
echo   C:\PhoneSpot\phonespot_cardnews
echo.

set "REPO_URL=https://github.com/313jongmin-droid/phonespot-cardnews-video.git"
set "DEFAULT_DIR=C:\PhoneSpot\phonespot_cardnews"
set /p "TARGET_DIR=Install folder [%DEFAULT_DIR%]: "
if "%TARGET_DIR%"=="" set "TARGET_DIR=%DEFAULT_DIR%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "& {
  $ErrorActionPreference = 'Stop'
  $repo = 'https://github.com/313jongmin-droid/phonespot-cardnews-video.git'
  $target = $env:TARGET_DIR
  if ([string]::IsNullOrWhiteSpace($target)) {
    $target = 'C:\PhoneSpot\phonespot_cardnews'
  }

  Write-Host '[target]' $target

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

  function Ensure-WingetPackage($exe, $id, $label) {
    if (Get-Command $exe -ErrorAction SilentlyContinue) {
      Write-Host '[OK]' $label 'found'
      return
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
      throw "$label is missing, and winget is not available. Install it manually first."
    }
    Write-Host '[install]' $label 'via winget'
    winget install --id $id -e --source winget --accept-package-agreements --accept-source-agreements
  }

  Ensure-WingetPackage 'node.exe' 'OpenJS.NodeJS.LTS' 'Node.js'
  Ensure-WingetPackage 'python.exe' 'Python.Python.3.12' 'Python'

  $git = Find-Git
  if (-not $git) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
      Write-Host '[install] Git for Windows via winget'
      winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
      $git = Find-Git
    }
  }
  if (-not $git) { throw 'Git is missing. Install Git for Windows or GitHub Desktop first.' }
  Write-Host '[git]' $git

  $targetPath = [System.IO.Path]::GetFullPath($target)
  $parent = Split-Path $targetPath
  if (-not (Test-Path $parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }

  if (Test-Path (Join-Path $targetPath '.git')) {
    Write-Host '[update] Existing Git workspace found. Pull latest.'
    & $git -C $targetPath pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'Git pull failed.' }
  } elseif (Test-Path $targetPath) {
    $children = @(Get-ChildItem -LiteralPath $targetPath -Force -ErrorAction SilentlyContinue)
    if ($children.Count -gt 0) {
      $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
      $backup = "${targetPath}_OLD_${stamp}"
      Write-Host '[backup] Target folder is not empty and is not Git.'
      Write-Host '         Moving it to:' $backup
      Move-Item -LiteralPath $targetPath -Destination $backup
    }
    Write-Host '[clone]' $repo
    & $git clone $repo $targetPath
    if ($LASTEXITCODE -ne 0) { throw 'Git clone failed.' }
  } else {
    Write-Host '[clone]' $repo
    & $git clone $repo $targetPath
    if ($LASTEXITCODE -ne 0) { throw 'Git clone failed.' }
  }

  $shorts = Join-Path $targetPath 'shorts'
  if (Test-Path (Join-Path $shorts 'package.json')) {
    Write-Host '[deps] npm install'
    Push-Location $shorts
    cmd /c npm install
    if ($LASTEXITCODE -ne 0) { throw 'npm install failed.' }
    Pop-Location
  }

  Write-Host '[deps] Python packages'
  python -m pip install -q edge-tts mutagen pillow requests
  if ($LASTEXITCODE -ne 0) { throw 'Python package install failed.' }

  $desk = Join-Path $targetPath 'CODEX_VIDEO_DESK'
  $panel = Join-Path $desk '00_PHONE_SPOT_PANEL.bat'
  if (Test-Path $panel) {
    Write-Host '[OK] Setup complete.'
    Write-Host '[panel]' $panel
    Start-Process -FilePath $panel -WorkingDirectory $desk
  } else {
    throw 'Panel launcher was not found after clone.'
  }
}"

if errorlevel 1 (
  echo.
  echo [ERROR] Setup failed.
  echo If a folder was open in Explorer, close it and run this again.
  pause
  exit /b 1
)

echo.
echo [OK] Render PC setup finished.
pause
