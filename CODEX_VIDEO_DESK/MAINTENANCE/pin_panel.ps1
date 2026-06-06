# 폰스팟 패널 바로가기 생성 + 작업표시줄 고정(가능하면).
# .bat 는 작업표시줄에 직접 고정이 안 되므로, cmd.exe 를 타깃으로 하는 .lnk 를 만든다(이건 고정 가능).
$ErrorActionPreference = "Stop"

$desk = Split-Path -Parent $PSScriptRoot          # MAINTENANCE -> CODEX_VIDEO_DESK
$bat  = Join-Path $desk "00_PHONE_SPOT_PANEL.bat"
if (-not (Test-Path $bat)) {
  Write-Host "[ERROR] 00_PHONE_SPOT_PANEL.bat 를 찾을 수 없습니다: $bat"
  exit 1
}

$ws         = New-Object -ComObject WScript.Shell
$desktopDir = [Environment]::GetFolderPath('Desktop')
$programs   = [Environment]::GetFolderPath('Programs')
$lnkDesktop = Join-Path $desktopDir "폰스팟 패널.lnk"
$lnkStart   = Join-Path $programs   "폰스팟 패널.lnk"

function New-PanelShortcut([string]$path) {
  $s = $ws.CreateShortcut($path)
  $s.TargetPath       = $env:ComSpec                 # cmd.exe (exe 타깃이라 작업표시줄 고정 가능)
  $s.Arguments        = '/c "' + $bat + '"'
  $s.WorkingDirectory = $desk
  $s.IconLocation     = "$env:SystemRoot\System32\imageres.dll,109"
  $s.WindowStyle      = 7                              # 최소화로 실행(콘솔 깜빡임 최소)
  $s.Description       = "폰스팟 통합 제작 패널 실행"
  $s.Save()
}

New-PanelShortcut $lnkDesktop
New-PanelShortcut $lnkStart
Write-Host "[OK] 바탕화면 + 시작메뉴에 '폰스팟 패널' 바로가기를 만들었습니다."

# 작업표시줄 자동 고정(최신 윈도우는 보안상 막을 수 있어 best-effort).
$pinned = $false
try {
  $sh     = New-Object -ComObject Shell.Application
  $folder = $sh.Namespace((Split-Path $lnkDesktop))
  $item   = $folder.ParseName((Split-Path $lnkDesktop -Leaf))
  foreach ($verb in $item.Verbs()) {
    $n = $verb.Name
    if ($n -match "표시줄" -or $n -match "Pin to taskbar") { $verb.DoIt(); $pinned = $true; break }
  }
} catch { }

Write-Host ""
if ($pinned) {
  Write-Host "[OK] 작업 표시줄에 고정했습니다."
} else {
  Write-Host "[안내] 자동 고정이 막혀 있습니다(Windows 정책). 아래 중 하나면 1초면 끝납니다:"
  Write-Host "   1) 바탕화면의 '폰스팟 패널' 아이콘을 마우스로 작업표시줄에 드래그"
  Write-Host "   2) 또는 그 아이콘 우클릭 -> '작업 표시줄에 고정'"
  Write-Host "   (윈도우11이면 우클릭 -> '추가 옵션 표시' 안에 있을 수 있습니다)"
}
