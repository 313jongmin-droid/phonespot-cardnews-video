# -*- coding: utf-8 -*-
"""Install a desk-only Codex video workflow.

The desk-only layout keeps daily video work under CODEX_VIDEO_DESK:
  CODEX_VIDEO_DESK/RESULTS/<render-key>/
  CODEX_VIDEO_DESK/TEMP/_raw/
  CODEX_VIDEO_DESK/ILLUSTRATION_DROP/

Legacy upload_codex and shorts/out_codex contents are moved to a timestamped
backup folder. The Remotion public illustration path becomes an internal
junction to the desk illustration library.
"""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"
RUNNER = SHORTS / "run_codex_casual.bat"
PUBLISH = SCRIPTS / "publish_codex_package.py"
REFRESH = SCRIPTS / "codex_refresh_workbench.py"
SYNC = SCRIPTS / "sync_codex_illustrations.py"
BASELINE = SHORTS / "codex" / "CODEX_BASELINE.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


PUBLISH_CODE = r'''# -*- coding: utf-8 -*-
"""Create one copy-ready result folder for a Codex short.

V2 keeps exactly one active MP4 per render result folder.
The MP4 filename matches its parent folder:
  CODEX_VIDEO_DESK/RESULTS/<render-key>/<render-key>.mp4

Channel copy, checklist, source notes, and optional illustration requests are
written beside the MP4. The rendered MP4 is never re-encoded by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
CARDNEWS_OUTPUT = ROOT / "cardnews" / "output"
SHORTS = ROOT / "shorts"
DESK = ROOT / "CODEX_VIDEO_DESK"
RESULTS = DESK / "RESULTS"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sections_from_captions(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^##\s+(\d+)\.\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip().strip("-").strip()
    return sections


def clean_youtube_description(value: str) -> str:
    if not value:
        return ""
    value = re.sub(r"(?ms)^▶\s*타임스탬프\s*$.*?(?=^▶\s*|\Z)", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    if "#Shorts" not in value and "#shorts" not in value:
        value = value.rstrip() + "\n\n#Shorts"
    return value


def clean_title(value: str, fallback: str) -> str:
    value = re.sub(r"\s+", " ", value or "").strip() or fallback
    return value[:100].rstrip()


def script_data(slug: str) -> dict:
    path = CARDNEWS_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def preferred_title(slug: str, data: dict) -> str:
    return clean_title(
        str(data.get("video_title") or data.get("title_short") or data.get("title") or ""),
        slug.replace("_", " "),
    )


def source_line(path: Path) -> str:
    if not path.exists():
        return f"- missing: {path}"
    modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    return f"- {path} | modified={modified} | bytes={path.stat().st_size}"


def link_or_copy(src: Path, dst: Path) -> str:
    if src.resolve() == dst.resolve():
        return "in-place"
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def result_video_path(package: Path) -> Path:
    return package / f"{package.name}.mp4"


def is_result_master(video: Path) -> bool:
    try:
        return video.parent.parent.resolve() == RESULTS.resolve() and video == result_video_path(video.parent)
    except OSError:
        return False


def unique_package(slug: str, date_text: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    key = f"{date_text}_{slug}_codex_remotion"
    package = RESULTS / key
    if not result_video_path(package).exists():
        return package
    return RESULTS / f"{key}_{datetime.now().strftime('%H%M%S')}"


def package_for(video: Path, slug: str, date_text: str | None = None) -> Path:
    video = video.resolve()
    if not video.exists():
        raise FileNotFoundError(f"video missing: {video}")

    date_text = date_text or datetime.now().strftime("%Y%m%d")
    package = video.parent if is_result_master(video) else unique_package(slug, date_text)
    package.mkdir(parents=True, exist_ok=True)

    captions_path = CARDNEWS_OUTPUT / slug / "captions.md"
    script_path = CARDNEWS_OUTPUT / slug / "shorts_script.json"
    captions = read_text(captions_path)
    sections = sections_from_captions(captions)
    data = script_data(slug)
    title = preferred_title(slug, data)
    instagram = sections.get("3") or captions
    youtube_description = clean_youtube_description(sections.get("4") or captions)
    tiktok = sections.get("5") or instagram
    master = result_video_path(package)
    master_mode = link_or_copy(video, master)

    for obsolete in (
        "youtube_title.txt",
        "youtube_description.txt",
        "youtube.txt",
        "instagram.txt",
        "tiktok.txt",
        "publish_checklist.txt",
        "README_FIRST.txt",
    ):
        path = package / obsolete
        if path.exists():
            path.unlink()

    write_text(
        package / "UPLOAD_COPY.txt",
        f"""폰스팟 SNS 업로드 문구

사용 순서
1. 결과 폴더와 이름이 같은 MP4를 한 번 확인합니다.
2. 업로드할 채널 구역만 복사합니다.
3. 첫 2초, 날짜, 숫자, 고정 CTA를 확인합니다.

============================================================
YOUTUBE SHORTS
============================================================

[제목]
{title}

[설명]
{youtube_description}

============================================================
INSTAGRAM REELS
============================================================

{instagram}

============================================================
TIKTOK
============================================================

{tiktok}
""",
    )

    illustration_md = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.md"
    illustration_json = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.json"
    for source in (captions_path, script_path, illustration_md, illustration_json):
        if source.exists():
            shutil.copy2(source, package / source.name)

    write_text(
        package / "source_manifest.txt",
        "\n".join(
            [
                "PhoneSpot Codex source manifest",
                f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
                f"- slug: {slug}",
                f"- package: {package}",
                f"- video_sha256: {sha256(master)}",
                f"- master_mode: {master_mode}",
                "",
                "[Sources]",
                source_line(video),
                source_line(captions_path),
                source_line(script_path),
                source_line(illustration_md),
                source_line(illustration_json),
            ]
        ),
    )
    write_json(
        package / "publish.json",
        {
            "version": 2,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "slug": slug,
            "title": title,
            "master_video": master.name,
            "upload_copy": "UPLOAD_COPY.txt",
            "master_mode": master_mode,
            "master_video_sha256": sha256(master),
            "channels": {
                "youtube_shorts": {
                    "video": master.name,
                    "copy_source": "UPLOAD_COPY.txt#YOUTUBE SHORTS",
                },
                "instagram_reels": {"video": master.name, "copy_source": "UPLOAD_COPY.txt#INSTAGRAM REELS"},
                "tiktok": {"video": master.name, "copy_source": "UPLOAD_COPY.txt#TIKTOK"},
            },
        },
    )
    print(f"[result-package-v2] folder: {package}")
    print(f"[result-package-v2] master: {master.name} ({master_mode})")
    return package


def latest_video() -> Path | None:
    current = [
        path
        for path in RESULTS.glob("*/*.mp4")
        if path == result_video_path(path.parent)
    ]
    if current:
        return max(current, key=lambda path: path.stat().st_mtime)
    return None


def infer_slug(video: Path) -> str:
    if video.parent.parent.resolve() == RESULTS.resolve():
        name = video.parent.name
    else:
        name = video.stem
    match = re.match(r"\d{8}_(.+)_codex_remotion(?:_\d{6})?$", name)
    if match:
        return match.group(1)
    match = re.match(r"(.+)_\d{8}_codex_remotion(?:_\d{6})?$", name)
    if match:
        return match.group(1)
    raise ValueError(f"could not infer slug from: {video}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("date", nargs="?")
    parser.add_argument("--latest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.latest:
        video = latest_video()
        if not video:
            print("[ERROR] No Codex Remotion result found.")
            return 1
        package_for(video, args.slug or infer_slug(video))
        return 0
    if not args.video or not args.slug:
        print("[ERROR] Usage: publish_codex_package.py VIDEO SLUG [YYYYMMDD]")
        print("        publish_codex_package.py --latest")
        return 1
    package_for(Path(args.video), args.slug, args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


REFRESH_CODE = r'''# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
DESK = ROOT / "CODEX_VIDEO_DESK"
ILLUST = DESK / "ILLUSTRATION_DROP"
RESULTS = DESK / "RESULTS"


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def remove_link_only(path: Path) -> None:
    if not path.exists():
        return
    if is_junction(path):
        path.rmdir()
        return
    if path.is_symlink():
        path.unlink()
        return
    print(f"[WARN] Keeping real folder instead of removing it: {path}")


def make_junction(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if link.exists():
        try:
            if link.resolve() == target.resolve():
                return
        except OSError:
            pass
        if is_junction(link) or link.is_symlink():
            remove_link_only(link)
        elif link.is_dir() and not any(link.iterdir()):
            for attempt in range(5):
                try:
                    link.rmdir()
                    break
                except OSError:
                    if attempt == 4:
                        raise
                    time.sleep(0.4)
        else:
            raise RuntimeError(f"Cannot replace non-empty real folder with junction: {link}")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=False)


def latest_slug() -> str | None:
    rows = sorted(
        CARDNEWS.glob("output/*/codex_illustration_requests.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return rows[0].parent.name if rows else None


def refresh(slug: str | None) -> None:
    DESK.mkdir(parents=True, exist_ok=True)
    ILLUST.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    (DESK / "TEMP" / "_raw").mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(SHORTS / "scripts" / "sync_codex_illustrations.py")], check=True)
    remove_link_only(DESK / "OUT_CODEX")
    selected = slug or latest_slug()
    if not selected:
        write(DESK / "LATEST_PROMPT.md", "# Codex Illustration Requests\n\nNo prompt report is available yet.\n")
        write(DESK / "LATEST_PROMPT.json", json.dumps({"requests": []}, ensure_ascii=False, indent=2))
        write(DESK / "LATEST_SLUG.txt", "none\n")
        return
    source_md = CARDNEWS / "output" / selected / "codex_illustration_requests.md"
    source_json = CARDNEWS / "output" / selected / "codex_illustration_requests.json"
    if source_md.exists():
        shutil.copy2(source_md, DESK / "LATEST_PROMPT.md")
    else:
        write(DESK / "LATEST_PROMPT.md", f"# Codex Illustration Requests: {selected}\n\nNo new illustration request was generated.\n")
    if source_json.exists():
        shutil.copy2(source_json, DESK / "LATEST_PROMPT.json")
    else:
        write(DESK / "LATEST_PROMPT.json", json.dumps({"slug": selected, "requests": []}, ensure_ascii=False, indent=2))
    write(DESK / "LATEST_SLUG.txt", selected + "\n")
    print(f"[workbench] latest slug: {selected}")
    print(f"[workbench] latest prompt: {DESK / 'LATEST_PROMPT.md'}")
    print(f"[workbench] results: {DESK / 'RESULTS'}")


if __name__ == "__main__":
    refresh(sys.argv[1] if len(sys.argv) > 1 else None)
'''


SYNC_CODE = r'''# -*- coding: utf-8 -*-
"""Keep the desk illustration library and Remotion render cache in sync."""
from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
DESK = ROOT / "CODEX_VIDEO_DESK"
LIBRARY = DESK / "ILLUSTRATION_DROP"
CACHE = ROOT / "shorts" / "public" / "assets" / "illustrations"


def is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def copy_tree_missing(source: Path, target: Path) -> int:
    copied = 0
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        output = target / relative
        if output.exists():
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, output)
        copied += 1
    return copied


def copy_tree_refresh(source: Path, target: Path) -> int:
    copied = 0
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(source)
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and output.stat().st_size == item.stat().st_size and output.stat().st_mtime_ns == item.stat().st_mtime_ns:
            continue
        shutil.copy2(item, output)
        copied += 1
    return copied


def main() -> int:
    LIBRARY.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        if CACHE.resolve() == LIBRARY.resolve():
            print("[illustrations] Remotion path already points to desk library.")
            return 0
    except OSError:
        pass
    recovered = copy_tree_missing(CACHE, LIBRARY)
    refreshed = copy_tree_refresh(LIBRARY, CACHE)
    print(f"[illustrations] desk library: {LIBRARY}")
    print(f"[illustrations] recovered={recovered}, cache-updated={refreshed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


RUNNER_TAIL = r'''echo.
echo ----- Step 5/7: Remotion raw render -----
if not exist "..\CODEX_VIDEO_DESK\TEMP\_raw" mkdir "..\CODEX_VIDEO_DESK\TEMP\_raw"
if not exist "..\CODEX_VIDEO_DESK\RESULTS" mkdir "..\CODEX_VIDEO_DESK\RESULTS"
for /f %%D in ('python scripts\today.py') do set "DATE=%%D"
if "%DATE%"=="" set "DATE=nodate"
set "RESULTKEY=!DATE!_!SLUG!_codex_remotion"
set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\!RESULTKEY!"
if exist "!RESULTDIR!" (
    set "RESULTKEY=!RESULTKEY!_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
    set "RESULTKEY=!RESULTKEY: =0!"
    set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\!RESULTKEY!"
)
if not exist "!RESULTDIR!" mkdir "!RESULTDIR!"
set "OUTFILE=!RESULTDIR!\!RESULTKEY!.mp4"
set "RAWFILE=..\CODEX_VIDEO_DESK\TEMP\_raw\!SLUG!_!DATE!_codex_remotion_raw.mp4"
if exist "!RAWFILE!" del /q "!RAWFILE!" >nul 2>nul
echo  Raw: !RAWFILE!
call npx remotion render src/index.ts CasualShort "!RAWFILE!" --concurrency=2 --pixel-format=yuv420p --crf=18
if errorlevel 1 goto :fail

echo.
echo ----- Step 6/7: Finalize SNS MP4 -----
echo  Output: !OUTFILE!
python scripts\finalize_sns_video.py "!RAWFILE!" "!OUTFILE!"
if errorlevel 1 goto :fail
del /q "!RAWFILE!" >nul 2>nul

echo.
echo ----- Step 7/7: Quality check + result package -----
python scripts\verify_video_quality.py "!OUTFILE!"
if errorlevel 1 goto :fail
python scripts\publish_codex_package.py "!OUTFILE!" "!SLUG!" "!DATE!"
if errorlevel 1 (
    echo  [WARN] Result metadata generation failed. Final MP4 remains available.
)
echo.
echo ============================================================
echo  DONE. Result folder: !RESULTDIR!
echo ============================================================
goto :hold
'''


RUNNER_FULL = r'''@echo off
chcp 65001 > nul
cd /d "%~dp0"
setlocal enabledelayedexpansion
set "EXITCODE=0"
set "SLUG=%~1"
if not "!SLUG!"=="" goto :slug_selected

echo.
echo ============================================================
echo  PhoneSpot News Shorts - CODEX REMOTION QUALITY
echo ============================================================
echo.
echo Select a news folder by number  (#   date        flag  slug):
echo ------------------------------------------------------------
python scripts\list_slugs.py
echo ------------------------------------------------------------
echo.
set "NUM="
set /p NUM=Enter number:

if "%NUM%"=="" (
    echo [ERROR] No number entered.
    goto :fail
)

set "SLUG="
for /f "delims=" %%S in ('python scripts\get_slug.py %NUM%') do set "SLUG=%%S"
echo  [DEBUG] NUM=%NUM%  SLUG=!SLUG!

if "!SLUG!"=="" (
    echo [ERROR] Invalid number: %NUM%.
    goto :fail
)

:slug_selected
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js not found.
    goto :fail
)
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    goto :fail
)

echo.
echo ----- Step 1/7: npm install -----
if not exist node_modules (
    call npm install --no-audit --no-fund
    if errorlevel 1 goto :fail
) else (
    echo  already installed - skip
)

echo.
echo ----- Step 2/7: edge-tts install -----
python -m pip install --quiet --upgrade edge-tts
if errorlevel 1 goto :fail

echo.
echo ----- Step 3/7: Build script + copy assets -----
python scripts\build_script.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_enhance_script.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_apply_uploaded_illustrations.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_illustration_scout.py !SLUG!
if errorlevel 1 goto :fail
python scripts\codex_refresh_workbench.py !SLUG!
if errorlevel 1 goto :fail
python scripts\validate_codex_korean.py !SLUG!
if errorlevel 1 goto :fail
python scripts\sync_codex_illustrations.py
if errorlevel 1 goto :fail
python scripts\copy_assets.py !SLUG!
if errorlevel 1 goto :fail

echo.
echo ----- Step 4/7: Generate normalized TTS -----
if "%PHONESPOT_TTS_RATE%"=="" set "PHONESPOT_TTS_RATE=+42%%"
if "%PHONESPOT_TTS_LOUDNORM%"=="" set "PHONESPOT_TTS_LOUDNORM=1"
python scripts\generate_tts.py
if errorlevel 1 goto :fail
python scripts\verify_tts_timing.py
if errorlevel 1 goto :fail

echo.
echo ----- Step 5/7: Remotion raw render -----
if not exist "..\CODEX_VIDEO_DESK\TEMP\_raw" mkdir "..\CODEX_VIDEO_DESK\TEMP\_raw"
if not exist "..\CODEX_VIDEO_DESK\RESULTS" mkdir "..\CODEX_VIDEO_DESK\RESULTS"
for /f %%D in ('python scripts\today.py') do set "DATE=%%D"
if "%DATE%"=="" set "DATE=nodate"
set "RESULTKEY=!DATE!_!SLUG!_codex_remotion"
set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\!RESULTKEY!"
if exist "!RESULTDIR!" (
    set "RESULTKEY=!RESULTKEY!_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
    set "RESULTKEY=!RESULTKEY: =0!"
    set "RESULTDIR=..\CODEX_VIDEO_DESK\RESULTS\!RESULTKEY!"
)
if not exist "!RESULTDIR!" mkdir "!RESULTDIR!"
set "OUTFILE=!RESULTDIR!\!RESULTKEY!.mp4"
set "RAWFILE=..\CODEX_VIDEO_DESK\TEMP\_raw\!SLUG!_!DATE!_codex_remotion_raw.mp4"
if exist "!RAWFILE!" del /q "!RAWFILE!" >nul 2>nul
echo  Raw: !RAWFILE!
call npx remotion render src/index.ts CasualShort "!RAWFILE!" --concurrency=2 --pixel-format=yuv420p --crf=18
if errorlevel 1 goto :fail

echo.
echo ----- Step 6/7: Finalize SNS MP4 -----
echo  Output: !OUTFILE!
python scripts\finalize_sns_video.py "!RAWFILE!" "!OUTFILE!"
if errorlevel 1 goto :fail
del /q "!RAWFILE!" >nul 2>nul

echo.
echo ----- Step 7/7: Quality check + result package -----
python scripts\verify_video_quality.py "!OUTFILE!"
if errorlevel 1 goto :fail
python scripts\publish_codex_package.py "!OUTFILE!" "!SLUG!" "!DATE!"
if errorlevel 1 (
    echo  [WARN] Result metadata generation failed. Final MP4 remains available.
)
echo.
echo ============================================================
echo  DONE. Result folder: !RESULTDIR!
echo ============================================================
goto :hold

:fail
set "EXITCODE=1"
echo.
echo [ERROR] Codex Remotion build failed.

:hold
echo.
echo Press any key to close this window...
pause >nul
exit /b !EXITCODE!
'''


BUTTON_02 = r'''@echo off
chcp 65001 > nul
cd /d "%~dp0..\shorts"
if not exist run_codex_casual.bat goto :runner_missing
python scripts\codex_import_downloads.py
if errorlevel 1 goto :fail
set /p SLUG=<"%~dp0LATEST_SLUG.txt"
call run_codex_casual.bat "%SLUG%"
if errorlevel 1 exit /b 1
exit /b 0

:runner_missing
echo.
echo [ERROR] Render runner is missing: shorts\run_codex_casual.bat
echo [NEXT] Run RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat once.
pause
exit /b 1

:fail
echo.
echo [ERROR] Import stopped.
pause
exit /b 1
'''


BUTTON_03 = r'''@echo off
chcp 65001 > nul
cd /d "%~dp0..\shorts"
if not exist run_codex_casual.bat goto :runner_missing
set /p SLUG=<"%~dp0LATEST_SLUG.txt"
call run_codex_casual.bat "%SLUG%"
exit /b %errorlevel%

:runner_missing
echo.
echo [ERROR] Render runner is missing: shorts\run_codex_casual.bat
echo [NEXT] Run RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat once.
pause
exit /b 1
'''


BUTTON_15 = r'''@echo off
chcp 65001 > nul
cd /d "%~dp0..\shorts"
if not exist run_codex_casual.bat goto :runner_missing
call run_codex_casual.bat
exit /b %errorlevel%

:runner_missing
echo.
echo [ERROR] Render runner is missing: shorts\run_codex_casual.bat
echo [NEXT] Run RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat once.
pause
exit /b 1
'''


README = r'''폰스팟 코덱스 영상 데스크 사용 안내

이 폴더만 열어두면 영상 준비, 일러스트 추가, 렌더링, 결과 확인까지 진행할 수 있습니다.

■ 가장 자주 쓰는 작업 흐름

[새 카드뉴스를 처음 영상으로 만들 때]
1. 01_PREPARE_GPT_PROMPTS.bat 실행
2. 목록에서 영상으로 만들 뉴스 번호 선택
3. LATEST_PROMPT.md가 열리면 필요한 일러스트를 GPT Plus에서 생성
4. 생성 이미지를 평소처럼 다운로드
5. 02_IMPORT_DOWNLOADS_AND_RENDER.bat 실행
6. 다운로드 이미지가 자동 정리되고 Remotion 영상이 생성됨

[새 일러스트 없이 마지막 선택 영상을 다시 만들 때]
- 03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat 실행

[과거 영상이나 원하는 영상을 직접 골라 다시 만들 때]
- 15_SELECT_AND_RENDER_EXISTING.bat 실행

■ 결과 저장 방식 V2

- RESULTS 폴더 안에 렌더 1회당 하위 폴더가 하나씩 생성됩니다.
- 최종 MP4, captions.md, 통합 업로드 문서 UPLOAD_COPY.txt가 같은 폴더에 저장됩니다.
- 최종 MP4의 파일명은 상위 결과 폴더명과 동일합니다.
- UPLOAD_COPY.txt 한 파일 안에 유튜브·인스타그램·틱톡 구역이 나뉘어 있습니다.
- OUT_CODEX 이력 폴더는 더 이상 사용하지 않습니다.
- 재렌더하면 시간 suffix가 붙은 새 결과 폴더가 생성되어 이전 결과를 덮지 않습니다.

■ 버튼별 설명

01_PREPARE_GPT_PROMPTS.bat
- 만들 뉴스를 번호로 선택합니다.
- 영상 청크와 비주얼을 준비하고, 새 GPT 일러스트가 필요하면 요청 문서를 엽니다.
- 아직 TTS 생성이나 영상 렌더링은 하지 않습니다.

02_IMPORT_DOWNLOADS_AND_RENDER.bat
- GPT Plus에서 새 일러스트를 내려받은 뒤 실행합니다.
- 다운로드 이미지를 알맞은 파일명으로 가져오고 마지막 선택 영상을 렌더링합니다.

03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat
- 새 일러스트를 추가하지 않고 마지막 선택 영상을 다시 렌더링합니다.

04_OPEN_LATEST_PROMPT.bat
- 가장 최근 GPT 일러스트 생성 요청 문서 LATEST_PROMPT.md를 다시 엽니다.

05_OPEN_RESULTS.bat
- 최종 업로드 결과 폴더 RESULTS를 엽니다.
- 각 하위 폴더 안에서 MP4와 통합 업로드 문서 UPLOAD_COPY.txt를 함께 확인합니다.

06_OPEN_ILLUSTRATION_LIBRARY.bat
- 재사용 일러스트 라이브러리 폴더를 엽니다.

07_OPEN_RESULTS_HISTORY.bat
- RESULTS 폴더를 엽니다.
- 재렌더 이력도 RESULTS 하위 폴더에 함께 쌓입니다.

08_APPLY_TTS_PRONUNCIATION_TIMING.bat
- TTS 발음사전과 단어 경계 기반 타이밍 보정 기능을 설치합니다.

09_EDIT_TTS_PRONUNCIATION_DICTIONARY.bat
- WWDC, iOS, NFC 같은 용어가 어색하게 읽힐 때 발음사전을 편집합니다.

10_ROLLBACK_TTS_PRONUNCIATION_TIMING.bat
- TTS 실험 결과가 더 나쁠 때 발음사전과 타이밍 보정 기능을 원복합니다.

11_OPEN_ILLUSTRATION_TAG_DB.bat
- 일러스트별 태그와 최근 사용 기록을 확인합니다.

12_REFRESH_ILLUSTRATION_TAG_DB.bat
- 일러스트 PNG를 추가하거나 이름을 변경한 뒤 태그 DB를 다시 읽습니다.

13_REFRESH_LATEST_PUBLISH_PACKAGE.bat
- 가장 최근 결과 폴더의 통합 문서 UPLOAD_COPY.txt를 다시 생성합니다.
- 영상을 다시 렌더링하지 않습니다.

14_OPEN_PUBLISH_PACKAGES.bat
- RESULTS 폴더를 엽니다.
- V2에서는 발행패키지와 최종 MP4가 같은 결과 폴더에 있습니다.

15_SELECT_AND_RENDER_EXISTING.bat
- 원하는 뉴스를 번호로 골라 바로 렌더링합니다.

■ 결과 폴더

- RESULTS/<렌더 이름>/: 최종 MP4와 통합 업로드 문서 UPLOAD_COPY.txt가 함께 있는 완성 묶음
- ILLUSTRATION_DROP/: GPT Plus에서 만든 재사용 일러스트를 넣는 폴더
'''


BASELINE_NOTE = r'''
## Single-folder result package V2

- Completed Codex renders are stored only in `CODEX_VIDEO_DESK/RESULTS/<render-key>/`.
- Each result folder contains one MP4 whose filename matches the folder name, source captions, and one `UPLOAD_COPY.txt` publishing document.
- Temporary raw renders live only in `CODEX_VIDEO_DESK/TEMP/_raw/`.
- Reusable illustrations live physically in `CODEX_VIDEO_DESK/ILLUSTRATION_DROP/`.
- `shorts/public/assets/illustrations/` is an automatically refreshed internal Remotion cache.
- Legacy `upload_codex/` and `shorts/out_codex/` contents are moved to a timestamped backup.
- A rerender creates a timestamp-suffixed result folder and never overwrites an earlier result.
'''


def backup(path: Path, label: str) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_{label}_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    current = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker in current:
        print(f"[skip] already documented: {marker}")
        return
    write(path, current.rstrip() + "\n\n" + body.strip() + "\n")


def replace_runner_tail() -> None:
    text = RUNNER.read_text(encoding="utf-8", errors="replace")
    marker = "echo ----- Step 5/7: Remotion raw render -----"
    start = text.find("echo.\n" + marker)
    end = text.find("\n:fail", start)
    if start < 0 or end < 0:
        raise RuntimeError("runner Step 5 tail anchor missing")
    if (
        'set "OUTFILE=!RESULTDIR!\\!RESULTKEY!.mp4"' in text
        and "DONE. Result folder: !RESULTDIR!" in text
        and "..\\CODEX_VIDEO_DESK\\TEMP\\_raw" in text
        and "..\\CODEX_VIDEO_DESK\\RESULTS" in text
    ):
        print("[skip] runner already uses desk-only result package V2")
        return
    backup(RUNNER, "results_v2")
    write(RUNNER, text[:start] + RUNNER_TAIL.rstrip() + text[end:])


def ensure_runner_illustration_sync() -> None:
    text = RUNNER.read_text(encoding="utf-8", errors="replace")
    marker = "python scripts\\sync_codex_illustrations.py"
    if marker in text:
        return
    anchor = "python scripts\\copy_assets.py !SLUG!"
    if anchor not in text:
        raise RuntimeError("runner illustration sync anchor missing")
    backup(RUNNER, "desk_illustration_sync")
    write(RUNNER, text.replace(anchor, marker + "\nif errorlevel 1 goto :fail\n" + anchor, 1))


def ensure_runner() -> None:
    if RUNNER.exists():
        return
    write(RUNNER, RUNNER_FULL)
    print(f"[repair] recreated missing runner: {RUNNER}")


def install_scripts() -> None:
    for target, value in ((PUBLISH, PUBLISH_CODE), (REFRESH, REFRESH_CODE), (SYNC, SYNC_CODE)):
        rendered = value.rstrip() + "\n"
        current = target.read_text(encoding="utf-8", errors="replace") if target.exists() else ""
        if current == rendered:
            print(f"[skip] already current: {target}")
        else:
            backup(target, "results_v2")
            write(target, value)
        compile(target.read_text(encoding="utf-8"), str(target), "exec")


def install_buttons() -> None:
    DESK.mkdir(parents=True, exist_ok=True)
    old = DESK / "07_OPEN_OUT_CODEX_HISTORY.bat"
    if old.exists():
        old.unlink()
        print(f"[remove] {old}")
    write(DESK / "07_OPEN_RESULTS_HISTORY.bat", '@echo off\r\nstart "" explorer "%~dp0RESULTS"\r\n')
    write(DESK / "02_IMPORT_DOWNLOADS_AND_RENDER.bat", BUTTON_02)
    write(DESK / "03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat", BUTTON_03)
    write(
        DESK / "13_REFRESH_LATEST_PUBLISH_PACKAGE.bat",
        '@echo off\r\nchcp 65001 > nul\r\ncd /d "%~dp0..\\shorts"\r\n'
        'python scripts\\publish_codex_package.py --latest\r\n'
        'if errorlevel 1 (\r\n  echo.\r\n  echo [ERROR] Latest result package refresh failed.\r\n'
        '  pause\r\n  exit /b 1\r\n)\r\necho.\r\necho [OK] Latest result package refreshed.\r\npause\r\n',
    )
    write(DESK / "14_OPEN_PUBLISH_PACKAGES.bat", '@echo off\r\nstart "" explorer "%~dp0RESULTS"\r\n')
    write(DESK / "15_SELECT_AND_RENDER_EXISTING.bat", BUTTON_15)
    write(DESK / "README.txt", README)


def is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def remove_desk_out_codex_link() -> None:
    link = DESK / "OUT_CODEX"
    if not link.exists():
        return
    if is_junction(link):
        link.rmdir()
        print(f"[remove-junction] {link}")
        return
    if link.is_symlink():
        link.unlink()
        print(f"[remove-link] {link}")
        return
    print(f"[WARN] Keeping real desk folder: {link}")


def move_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst = dst.with_name(f"{dst.stem}_{STAMP}{dst.suffix}")
    shutil.move(str(src), str(dst))
    print(f"[move] {src} -> {dst}")


def remove_link_only(path: Path) -> None:
    if not path.exists():
        return
    if is_junction(path):
        path.rmdir()
        print(f"[remove-junction] {path}")
        return
    if path.is_symlink():
        path.unlink()
        print(f"[remove-link] {path}")


def unique_target(dst: Path) -> Path:
    if not dst.exists():
        return dst
    return dst.with_name(f"{dst.stem}_{STAMP}{dst.suffix}")


def move_contents(src: Path, dst: Path) -> None:
    if not src.exists() or is_junction(src):
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in list(src.iterdir()):
        target = unique_target(dst / item.name)
        shutil.move(str(item), str(target))
        print(f"[move] {item} -> {target}")
    try:
        src.rmdir()
    except OSError:
        pass


def make_junction(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if link.exists():
        try:
            if link.resolve() == target.resolve() and is_junction(link):
                return
        except OSError:
            pass
        if is_junction(link) or link.is_symlink():
            remove_link_only(link)
        elif link.is_dir() and not any(link.iterdir()):
            for attempt in range(5):
                try:
                    link.rmdir()
                    break
                except OSError:
                    if attempt == 4:
                        raise
                    time.sleep(0.4)
        else:
            raise RuntimeError(f"Cannot replace non-empty real folder with junction: {link}")
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True)
    print(f"[junction] {link} -> {target}")


def migrate_legacy() -> None:
    backups = ROOT / "backups" / f"CODEX_DESK_ONLY_STORAGE_MIGRATION_{STAMP}"
    desk_results = DESK / "RESULTS"
    desk_illust = DESK / "ILLUSTRATION_DROP"
    desk_temp = DESK / "TEMP" / "_raw"
    upload = ROOT / "upload_codex"
    runtime_illust = SHORTS / "public" / "assets" / "illustrations"
    old_out = SHORTS / "out_codex"

    DESK.mkdir(parents=True, exist_ok=True)

    # RESULTS used to be a desk junction pointing to upload_codex/RESULTS.
    remove_link_only(desk_results)
    desk_results.mkdir(parents=True, exist_ok=True)
    if upload.exists():
        move_contents(upload / "RESULTS", desk_results)
        move_contents(upload / "PUBLISH_PACKAGES", desk_results)
        move_contents(upload, backups / "upload_codex")

    # ILLUSTRATION_DROP becomes the real canonical library. The Remotion path
    # stays an internal render cache because Windows may keep it locked while
    # Explorer or another process is open. The sync script recovers files that
    # exist only in the old cache and refreshes the cache from the desk.
    remove_link_only(desk_illust)
    desk_illust.mkdir(parents=True, exist_ok=True)
    if is_junction(runtime_illust):
        remove_link_only(runtime_illust)
    runtime_illust.parent.mkdir(parents=True, exist_ok=True)
    runtime_illust.mkdir(parents=True, exist_ok=True)
    subprocess.run(["python", str(SYNC)], check=True)

    # Legacy render storage is no longer active. Keep anything found there in
    # backups and render future raw files inside the desk TEMP folder.
    if old_out.exists() and not is_junction(old_out):
        move_contents(old_out, backups / "shorts_out_codex")
    elif is_junction(old_out):
        remove_link_only(old_out)
    desk_temp.mkdir(parents=True, exist_ok=True)


def result_video_path(folder: Path) -> Path:
    return folder / f"{folder.name}.mp4"


def refresh_existing_results() -> None:
    results = DESK / "RESULTS"
    if not results.exists():
        return
    for folder in sorted(results.iterdir()):
        if not folder.is_dir():
            continue
        legacy_master = folder / "video_master_9x16.mp4"
        master = result_video_path(folder)
        if legacy_master.exists() and not master.exists():
            legacy_master.rename(master)
            print(f"[rename-master] {legacy_master.name} -> {master.name}")
        metadata = folder / "publish.json"
        if not master.exists() or not metadata.exists():
            continue
        try:
            data = json.loads(metadata.read_text(encoding="utf-8-sig", errors="replace"))
        except json.JSONDecodeError:
            print(f"[WARN] Invalid publish.json, keeping existing folder: {folder}")
            continue
        slug = str(data.get("slug") or "").strip()
        if not slug:
            print(f"[WARN] Missing slug in publish.json, keeping existing folder: {folder}")
            continue
        date_text = folder.name[:8] if folder.name[:8].isdigit() else datetime.now().strftime("%Y%m%d")
        subprocess.run(["python", str(PUBLISH), str(master), slug, date_text], check=True)


def main() -> int:
    print("=" * 60)
    print(" PhoneSpot Codex - DESK-ONLY Video Storage")
    print("=" * 60)
    ensure_runner()
    install_scripts()
    replace_runner_tail()
    ensure_runner_illustration_sync()
    migrate_legacy()
    refresh_existing_results()
    remove_desk_out_codex_link()
    install_buttons()
    append_once(BASELINE, "## Single-folder result package V2", BASELINE_NOTE)
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    subprocess.run(["python", str(REFRESH)], check=True, env=env)
    print("[OK] Desk-only video storage installed.")
    print(f"[desk-results] {DESK / 'RESULTS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
