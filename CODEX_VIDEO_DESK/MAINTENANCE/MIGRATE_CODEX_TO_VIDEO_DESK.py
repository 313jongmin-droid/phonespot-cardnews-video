from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_SOURCE = Path(
    r"C:\Users\di898\Documents\Codex\2026-04-30\codex-plugin-marketplace-add-heygen-com"
)
DEFAULT_DESK = Path(r"C:\Users\di898\Documents\phonespot_cardnews\CODEX_VIDEO_DESK")

COPY_EXTENSIONS = {".py", ".bat", ".ps1", ".md", ".txt", ".zip"}


def write_text(path: Path, text: str, *, bom: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig" if bom else "utf-8")
    print(f"[write] {path}")


def copy_maintenance_files(source: Path, maintenance: Path) -> int:
    maintenance.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.suffix.lower() not in COPY_EXTENSIONS:
            continue
        target = maintenance / path.name
        shutil.copy2(path, target)
        copied += 1
    return copied


def patch_copied_tools(maintenance: Path, desk: Path) -> None:
    tts_installer = maintenance / "INSTALL_CODEX_TTS_DESK_BUTTONS.py"
    if tts_installer.exists():
        text = tts_installer.read_text(encoding="utf-8")
        old = r"C:\Users\di898\Documents\Codex\2026-04-30\codex-plugin-marketplace-add-heygen-com"
        text = text.replace(old, str(maintenance))
        tts_installer.write_text(text, encoding="utf-8")
        print(f"[patch] {tts_installer}")

    backup_tool = maintenance / "BACKUP_CODEX_CURRENT_BASELINE.py"
    if backup_tool.exists():
        text = backup_tool.read_text(encoding="utf-8")
        text = text.replace('BACKUPS = HERE / "backups"', 'BACKUPS = HERE.parent / "BACKUPS"')
        backup_tool.write_text(text, encoding="utf-8")
        print(f"[patch] {backup_tool}")


def copy_latest_backup(source: Path, desk: Path) -> Path | None:
    source_backups = source / "backups"
    backups = (
        sorted(source_backups.glob("CODEX_CURRENT_BASELINE_*.zip"), key=lambda p: p.stat().st_mtime)
        if source_backups.exists()
        else []
    )
    if not backups:
        print("[warn] No baseline backup found.")
        return None

    target_dir = desk / "BACKUPS"
    target_dir.mkdir(parents=True, exist_ok=True)
    for old in target_dir.glob("CODEX_CURRENT_BASELINE_*.zip"):
        old.unlink()
    target = target_dir / backups[-1].name
    shutil.copy2(backups[-1], target)
    print(f"[copy backup] {target}")
    return target


def make_desk_buttons(desk: Path) -> None:
    buttons = {
        "08_APPLY_TTS_PRONUNCIATION_TIMING.bat": r"""@echo off
chcp 65001 > nul
call "%~dp0MAINTENANCE\RUN_APPLY_CODEX_TTS_PRONUNCIATION_TIMING.bat"
""",
        "10_ROLLBACK_TTS_PRONUNCIATION_TIMING.bat": r"""@echo off
chcp 65001 > nul
call "%~dp0MAINTENANCE\RUN_ROLLBACK_CODEX_TTS_PRONUNCIATION_TIMING.bat"
""",
        "16_APPLY_CURRENT_BASELINE.bat": r"""@echo off
chcp 65001 > nul
call "%~dp0MAINTENANCE\RUN_APPLY_CODEX_CURRENT_BASELINE.bat"
""",
        "17_APPLY_FIXED_CAPTION_RHYTHM.bat": r"""@echo off
chcp 65001 > nul
call "%~dp0MAINTENANCE\RUN_APPLY_CODEX_FIXED_CAPTION_RHYTHM.bat"
""",
        "18_ROLLBACK_FIXED_CAPTION_RHYTHM.bat": r"""@echo off
chcp 65001 > nul
call "%~dp0MAINTENANCE\RUN_ROLLBACK_CODEX_FIXED_CAPTION_RHYTHM.bat"
""",
        "19_BACKUP_CURRENT_BASELINE.bat": r"""@echo off
chcp 65001 > nul
call "%~dp0MAINTENANCE\RUN_BACKUP_CODEX_CURRENT_BASELINE.bat"
""",
        "20_OPEN_MAINTENANCE.bat": r"""@echo off
start "" explorer "%~dp0MAINTENANCE"
""",
        "21_DELETE_OLD_DOCUMENTS_CODEX.bat": r"""@echo off
chcp 65001 > nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0MAINTENANCE\DELETE_OLD_DOCUMENTS_CODEX.ps1"
pause
""",
    }
    for name, content in buttons.items():
        write_text(desk / name, content)


def make_delete_legacy_script(maintenance: Path) -> None:
    script = r'''$ErrorActionPreference = "Stop"

$legacyRoot = "C:\Users\di898\Documents\Codex"
$desk = "C:\Users\di898\Documents\phonespot_cardnews\CODEX_VIDEO_DESK"
$maintenance = Join-Path $desk "MAINTENANCE"

Write-Host "============================================================"
Write-Host " PhoneSpot Codex - Delete Old Documents Codex Folder"
Write-Host "============================================================"
Write-Host ""

if (-not (Test-Path -LiteralPath $legacyRoot)) {
    Write-Host "[INFO] Old Documents\Codex folder is already absent."
    exit 0
}

if (-not (Test-Path -LiteralPath (Join-Path $maintenance "RUN_APPLY_CODEX_CURRENT_BASELINE.bat"))) {
    throw "Maintenance copy is missing. Refusing to delete the old folder."
}

$resolved = (Resolve-Path -LiteralPath $legacyRoot).Path
if ($resolved -ne "C:\Users\di898\Documents\Codex") {
    throw "Unexpected legacy path: $resolved"
}

Write-Host "This removes only:"
Write-Host "  $resolved"
Write-Host ""
Write-Host "The CODEX_VIDEO_DESK folder is preserved."
Write-Host ""
$answer = Read-Host "Type DELETE to continue"
if ($answer -ne "DELETE") {
    Write-Host "[INFO] Cancelled."
    exit 0
}

Remove-Item -LiteralPath $resolved -Recurse -Force
Write-Host ""
Write-Host "[OK] Deleted old Documents\Codex folder."
'''
    write_text(maintenance / "DELETE_OLD_DOCUMENTS_CODEX.ps1", script, bom=True)


def make_readme(desk: Path) -> None:
    readme = """PhoneSpot CODEX_VIDEO_DESK 유지보수 안내

이제 영상 관련 일상 작업과 유지보수 도구는 이 폴더 안에서 관리합니다.

[기존 일상 작업]
01_PREPARE_GPT_PROMPTS.bat
- 신규 카드뉴스를 선택하고 필요한 GPT 일러스트 프롬프트를 준비합니다.

02_IMPORT_DOWNLOADS_AND_RENDER.bat
- 다운로드한 일러스트를 가져오고 최신 영상을 렌더링합니다.

03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat
- 새 일러스트 없이 최근 선택 영상을 다시 렌더링합니다.

15_SELECT_AND_RENDER_EXISTING.bat
- 원하는 기존 영상을 번호로 골라 다시 렌더링합니다.

[유지보수]
16_APPLY_CURRENT_BASELINE.bat
- 현재 합의된 Codex 영상 기준 기능을 다시 설치합니다.

17_APPLY_FIXED_CAPTION_RHYTHM.bat
- 고정 자막 크기와 개선된 화면 리듬 실험을 적용합니다.

18_ROLLBACK_FIXED_CAPTION_RHYTHM.bat
- 위 실험 결과가 좋지 않을 때 되돌립니다.

19_BACKUP_CURRENT_BASELINE.bat
- 현재 기준 파일을 백업합니다.

20_OPEN_MAINTENANCE.bat
- 세부 유지보수 도구 폴더를 엽니다.

21_DELETE_OLD_DOCUMENTS_CODEX.bat
- 이전 도구를 확인한 뒤 C:\\Users\\di898\\Documents\\Codex 폴더를 삭제합니다.
- 이전 완료 후 한 번만 사용합니다.

[보관 폴더]
RESULTS
- 최종 MP4와 업로드 문서를 보관합니다.

ILLUSTRATION_DROP
- 재사용 일러스트 라이브러리입니다.

BACKUPS
- 최신 기준 백업을 보관합니다.

MAINTENANCE
- 설치, 롤백, 점검 도구 모음입니다.
"""
    write_text(desk / "README_MAINTENANCE.txt", readme, bom=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--desk", type=Path, default=DEFAULT_DESK)
    args = parser.parse_args()

    source = args.source.resolve()
    desk = args.desk.resolve()
    if not source.exists():
        raise RuntimeError(f"Source workspace missing: {source}")
    desk.mkdir(parents=True, exist_ok=True)

    maintenance = desk / "MAINTENANCE"
    copied = copy_maintenance_files(source, maintenance)
    patch_copied_tools(maintenance, desk)
    backup = copy_latest_backup(source, desk)
    make_desk_buttons(desk)
    make_delete_legacy_script(maintenance)
    make_readme(desk)

    print("")
    print(f"[OK] Maintenance files copied: {copied}")
    print(f"[OK] Desk: {desk}")
    print(f"[OK] Latest backup: {backup or 'not found'}")
    print("[NEXT] Open CODEX_VIDEO_DESK and verify buttons 16-20.")
    print("[NEXT] Then use button 21 once to delete the old Documents\\Codex folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
