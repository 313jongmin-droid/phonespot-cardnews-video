$ErrorActionPreference = "Stop"
$desk = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell

function New-Link($name, $target) {
  $path = Join-Path $desktop $name
  $shortcut = $shell.CreateShortcut($path)
  $shortcut.TargetPath = $target
  $shortcut.WorkingDirectory = $desk
  $shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
  $shortcut.Save()
  Write-Host "[shortcut] $path"
}

New-Link "PhoneSpot 영상 패널.lnk" (Join-Path $desk "00_OPEN_CONTROL_PANEL_HIDDEN.bat")
New-Link "PhoneSpot 영상 패널 종료.lnk" (Join-Path $desk "00_STOP_CONTROL_PANEL.bat")
Write-Host "[OK] Desktop shortcuts created."


function New-LinkSafe($name, $target) {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $shell = New-Object -ComObject WScript.Shell
  $path = Join-Path $desktop $name
  $shortcut = $shell.CreateShortcut($path)
  $shortcut.TargetPath = $target
  $shortcut.WorkingDirectory = Split-Path -Parent $target
  $shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
  $shortcut.Save()
  Write-Host "[shortcut] $path"
}

New-LinkSafe "PhoneSpot 영상 패널 재시작.lnk" (Join-Path $desk "00_RESTART_CONTROL_PANEL.bat")

