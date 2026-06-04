# -*- coding: utf-8 -*-
"""Install a two-click GPT Plus illustration workflow for Codex Remotion."""
from __future__ import annotations

import py_compile
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"
RUNNER = SHORTS / "run_codex_casual.bat"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

PREPARE = SCRIPTS / "codex_prepare_illustrations.py"
IMPORT = SCRIPTS / "codex_import_downloads.py"
REFRESH = SCRIPTS / "codex_refresh_workbench.py"

PREPARE_CODE = r'''# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"


def run(script: str, *args: str) -> None:
    command = [sys.executable, str(SCRIPTS / script), *args]
    result = subprocess.run(command)
    if result.returncode:
        raise SystemExit(result.returncode)


def select_slug() -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "list_slugs.py")],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    )
    print("")
    print("Select a news folder by number:")
    print("------------------------------------------------------------")
    print(result.stdout.rstrip())
    print("------------------------------------------------------------")
    number = input("Enter number: ").strip()
    if not number:
        raise SystemExit("No number entered.")
    slug = subprocess.run(
        [sys.executable, str(SCRIPTS / "get_slug.py"), number],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=True,
    ).stdout.strip()
    if not slug:
        raise SystemExit("Invalid number.")
    return slug


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else select_slug()
    print("")
    print(f"[prepare] slug: {slug}")
    run("build_script.py", slug)
    run("codex_enhance_script.py", slug)
    run("codex_apply_uploaded_illustrations.py", slug)
    run("codex_illustration_scout.py", slug)
    run("codex_refresh_workbench.py", slug)
    prompt = DESK / "LATEST_PROMPT.md"
    if prompt.exists():
        os.startfile(prompt)
    print("")
    print("[OK] Prompt report is ready.")
    print("[NEXT] Generate GPT Plus illustrations in report order and download them.")
    print("[NEXT] Then run 02_IMPORT_DOWNLOADS_AND_RENDER.bat.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

IMPORT_CODE = r'''# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
DESK = ROOT / "CODEX_VIDEO_DESK"
DOWNLOADS = Path.home() / "Downloads"
ILLUST = DESK / "ILLUSTRATION_DROP"
ALLOWED = {".png", ".jpg", ".jpeg", ".webp"}


def run(script: str, *args: str) -> None:
    result = subprocess.run([sys.executable, str(SCRIPTS / script), *args])
    if result.returncode:
        raise SystemExit(result.returncode)


def main() -> int:
    slug_path = DESK / "LATEST_SLUG.txt"
    report_path = DESK / "LATEST_PROMPT.json"
    if not slug_path.exists() or not report_path.exists():
        print("[ERROR] Run 01_PREPARE_GPT_PROMPTS.bat first.")
        return 2
    slug = slug_path.read_text(encoding="utf-8").strip()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    requests = [
        item for item in payload.get("requests", [])
        if item.get("filename") and not (ILLUST / item["filename"]).exists()
    ]
    if not requests:
        print("[OK] No missing requested illustration. Render can start.")
        return 0

    threshold = report_path.stat().st_mtime - 2
    downloads = sorted(
        (
            item for item in DOWNLOADS.iterdir()
            if item.is_file()
            and item.suffix.lower() in ALLOWED
            and item.stat().st_size >= 10_000
            and item.stat().st_mtime >= threshold
        ),
        key=lambda item: item.stat().st_mtime,
    )
    if len(downloads) < len(requests):
        print(f"[ERROR] Need {len(requests)} new downloads, found {len(downloads)}.")
        print("[NEXT] Download GPT Plus images in prompt order and retry.")
        return 3

    selected = downloads[-len(requests):]
    print("")
    print(f"Slug: {slug}")
    print("Import mapping:")
    for source, request in zip(selected, requests):
        print(f"  {source.name}")
        print(f"    -> {request['filename']}")
    print("")
    answer = input("Import these files and continue? [Y/N]: ").strip().lower()
    if answer not in {"y", "yes"}:
        print("[STOP] Nothing imported.")
        return 4

    ILLUST.mkdir(parents=True, exist_ok=True)
    for source, request in zip(selected, requests):
        target = ILLUST / request["filename"]
        shutil.copy2(source, target)
        print(f"[COPY] {target.name}")

    run("codex_apply_uploaded_illustrations.py", slug)
    run("codex_refresh_workbench.py", slug)
    print("")
    print("[OK] Downloads imported and mapped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

REFRESH_CODE = r'''# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
DESK = ROOT / "CODEX_VIDEO_DESK"
ILLUST = DESK / "ILLUSTRATION_DROP"
RESULTS = DESK / "RESULTS"


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def make_junction(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if link.exists():
        try:
            if link.resolve() == target.resolve():
                return
        except OSError:
            pass
        remove_link_only(link)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=False)


def is_junction(path: Path) -> bool:
    checker = getattr(path, "is_junction", None)
    return bool(checker and checker())


def remove_link_only(path: Path) -> None:
    if not path.exists():
        return
    if is_junction(path):
        path.rmdir()
    elif path.is_symlink():
        path.unlink()
    else:
        print(f"[WARN] Keeping real folder instead of removing it: {path}")


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


if __name__ == "__main__":
    refresh(sys.argv[1] if len(sys.argv) > 1 else None)
'''


def backup(path: Path) -> Path:
    target = path.with_name(path.name + f".bak_fast_desk_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")
    return target


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + body.rstrip() + "\n", encoding="utf-8")


def patch_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    original = text
    if 'set "SLUG=%~1"' not in text:
        anchor = "setlocal enabledelayedexpansion\n"
        replacement = (
            "setlocal enabledelayedexpansion\n"
            'set "SLUG=%~1"\n'
            'if not "!SLUG!"=="" goto :slug_selected\n'
        )
        if anchor not in text:
            raise RuntimeError("Runner argument anchor missing")
        text = text.replace(anchor, replacement, 1)
    if "\n:slug_selected\n" not in text:
        anchor = "where node >nul 2>nul"
        if anchor not in text:
            raise RuntimeError("Runner slug label anchor missing")
        text = text.replace(anchor, ":slug_selected\n" + anchor, 1)
    refresh = (
        "python scripts\\codex_refresh_workbench.py !SLUG!\n"
        "if errorlevel 1 goto :fail"
    )
    scout = (
        "python scripts\\codex_illustration_scout.py !SLUG!\n"
        "if errorlevel 1 goto :fail"
    )
    if refresh not in text:
        if scout not in text:
            raise RuntimeError("Runner scout anchor missing")
        text = text.replace(scout, scout + "\n" + refresh, 1)
    if text != original:
        backup(RUNNER)
        RUNNER.write_text(text, encoding="utf-8")
        print(f"[write] {RUNNER}")


def desk_button(name: str, text: str) -> None:
    write(DESK / name, text)


def setup_desk() -> None:
    DESK.mkdir(parents=True, exist_ok=True)
    for obsolete in (
        "01_RUN_CODEX_REMOTION.bat",
        "02_OPEN_LATEST_PROMPT.bat",
        "03_OPEN_ILLUSTRATION_DROP.bat",
        "04_OPEN_RESULTS.bat",
        "05_REFRESH_LATEST_PROMPT.bat",
        "07_OPEN_OUT_CODEX_HISTORY.bat",
    ):
        path = DESK / obsolete
        if path.exists():
            path.unlink()
    desk_button(
        "01_PREPARE_GPT_PROMPTS.bat",
        '@echo off\r\nchcp 65001 > nul\r\ncd /d "%~dp0..\\shorts"\r\n'
        'python scripts\\codex_prepare_illustrations.py\r\npause\r\n',
    )
    desk_button(
        "02_IMPORT_DOWNLOADS_AND_RENDER.bat",
        '@echo off\r\nchcp 65001 > nul\r\ncd /d "%~dp0..\\shorts"\r\n'
        'if not exist run_codex_casual.bat goto :runner_missing\r\n'
        'python scripts\\codex_import_downloads.py\r\n'
        'if errorlevel 1 goto :fail\r\n'
        'set /p SLUG=<"%~dp0LATEST_SLUG.txt"\r\n'
        'call run_codex_casual.bat "%SLUG%"\r\n'
        'exit /b %errorlevel%\r\n'
        ':runner_missing\r\necho.\r\necho [ERROR] Render runner is missing: shorts\\run_codex_casual.bat\r\n'
        'echo [NEXT] Run RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat once.\r\npause\r\nexit /b 1\r\n'
        ':fail\r\necho.\r\necho [ERROR] Import stopped.\r\npause\r\nexit /b 1\r\n',
    )
    desk_button(
        "03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat",
        '@echo off\r\nchcp 65001 > nul\r\ncd /d "%~dp0..\\shorts"\r\n'
        'if not exist run_codex_casual.bat goto :runner_missing\r\n'
        'set /p SLUG=<"%~dp0LATEST_SLUG.txt"\r\n'
        'call run_codex_casual.bat "%SLUG%"\r\n'
        'exit /b %errorlevel%\r\n'
        ':runner_missing\r\necho.\r\necho [ERROR] Render runner is missing: shorts\\run_codex_casual.bat\r\n'
        'echo [NEXT] Run RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat once.\r\npause\r\nexit /b 1\r\n',
    )
    desk_button(
        "04_OPEN_LATEST_PROMPT.bat",
        '@echo off\r\nstart "" notepad "%~dp0LATEST_PROMPT.md"\r\n',
    )
    desk_button(
        "05_OPEN_RESULTS.bat",
        '@echo off\r\nstart "" explorer "%~dp0RESULTS"\r\n',
    )
    desk_button(
        "06_OPEN_ILLUSTRATION_LIBRARY.bat",
        '@echo off\r\nstart "" explorer "%~dp0ILLUSTRATION_DROP"\r\n',
    )
    desk_button(
        "07_OPEN_RESULTS_HISTORY.bat",
        '@echo off\r\nstart "" explorer "%~dp0RESULTS"\r\n',
    )
    desk_button(
        "15_SELECT_AND_RENDER_EXISTING.bat",
        '@echo off\r\nchcp 65001 > nul\r\ncd /d "%~dp0..\\shorts"\r\n'
        'if not exist run_codex_casual.bat goto :runner_missing\r\n'
        'call run_codex_casual.bat\r\n'
        'exit /b %errorlevel%\r\n'
        ':runner_missing\r\necho.\r\necho [ERROR] Render runner is missing: shorts\\run_codex_casual.bat\r\n'
        'echo [NEXT] Run RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat once.\r\npause\r\nexit /b 1\r\n',
    )
    write(
        DESK / "README.txt",
        """폰스팟 코덱스 영상 데스크 사용 안내

이 폴더만 열어두면 영상 준비, 일러스트 추가, 렌더링, 결과 확인까지 진행할 수 있습니다.

■ 가장 자주 쓰는 작업 흐름

[새 카드뉴스를 처음 영상으로 만들 때]
1. 01_PREPARE_GPT_PROMPTS.bat 실행
2. 목록에서 영상으로 만들 뉴스 번호 선택
3. LATEST_PROMPT.md가 열리면 필요한 일러스트를 GPT Plus에서 생성
4. 생성 이미지를 평소처럼 다운로드
5. 02_IMPORT_DOWNLOADS_AND_RENDER.bat 실행
6. 다운로드 이미지가 자동으로 정리되고 Remotion 영상이 생성됨

[새 일러스트 없이 마지막 선택 영상을 다시 만들 때]
- 03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat 실행

[과거 영상이나 원하는 영상을 직접 골라 다시 만들 때]
- 15_SELECT_AND_RENDER_EXISTING.bat 실행

■ 버튼별 설명

01_PREPARE_GPT_PROMPTS.bat
- 만들 뉴스를 번호로 선택합니다.
- 영상 청크와 비주얼을 준비하고, 새 GPT 일러스트가 필요하면 요청 문서를 엽니다.
- 아직 TTS 생성이나 영상 렌더링은 하지 않습니다.

02_IMPORT_DOWNLOADS_AND_RENDER.bat
- GPT Plus에서 새 일러스트를 내려받은 뒤 실행합니다.
- 다운로드한 이미지를 알맞은 파일명으로 가져오고, 마지막으로 선택한 영상을 렌더링합니다.

03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat
- 새 일러스트를 추가하지 않고 마지막으로 선택한 영상을 다시 렌더링합니다.
- 문구나 공통 로직을 수정한 뒤 재확인할 때 사용합니다.

04_OPEN_LATEST_PROMPT.bat
- 가장 최근 GPT 일러스트 생성 요청 문서 LATEST_PROMPT.md를 다시 엽니다.

05_OPEN_RESULTS.bat
- 업로드용 결과 폴더 RESULTS를 엽니다.
- 완성 MP4와 캡션 파일을 확인할 때 사용합니다.

06_OPEN_ILLUSTRATION_LIBRARY.bat
- 재사용 일러스트 라이브러리 폴더를 엽니다.
- 새 PNG를 직접 확인하거나 교체할 때 사용합니다.

07_OPEN_RESULTS_HISTORY.bat
- RESULTS 폴더를 엽니다.
- 재렌더 이력도 RESULTS 하위 폴더에 함께 쌓입니다.

08_APPLY_TTS_PRONUNCIATION_TIMING.bat
- TTS 발음사전과 단어 경계 기반 타이밍 보정 기능을 설치합니다.
- 한 번만 적용하면 이후 일반 렌더에도 자동으로 반영됩니다.

09_EDIT_TTS_PRONUNCIATION_DICTIONARY.bat
- WWDC, iOS, NFC 같은 용어가 어색하게 읽힐 때 발음사전을 편집합니다.
- 화면 자막은 바꾸지 않고 음성 발음만 조정합니다.

10_ROLLBACK_TTS_PRONUNCIATION_TIMING.bat
- TTS 실험 결과가 더 나쁠 때 발음사전과 타이밍 보정 기능을 원복합니다.

11_OPEN_ILLUSTRATION_TAG_DB.bat
- 일러스트별 태그와 최근 사용 기록을 확인합니다.
- 같은 그림이 반복되는지 점검할 때 사용합니다.

12_REFRESH_ILLUSTRATION_TAG_DB.bat
- 일러스트 PNG를 추가하거나 이름을 변경한 뒤 태그 DB를 다시 읽습니다.

13_REFRESH_LATEST_PUBLISH_PACKAGE.bat
- 가장 최근 결과 폴더를 기준으로 유튜브 쇼츠, 인스타그램 릴스, 틱톡 발행 문구를 다시 만듭니다.
- 영상을 다시 렌더링하지 않고 업로드 문구 묶음만 갱신합니다.

14_OPEN_PUBLISH_PACKAGES.bat
- RESULTS 폴더를 엽니다.
- V2에서는 통합 문서 UPLOAD_COPY.txt와 최종 MP4가 같은 하위 폴더에 있습니다.

15_SELECT_AND_RENDER_EXISTING.bat
- 원하는 뉴스를 번호로 골라 바로 렌더링합니다.
- 01번에서 프롬프트를 준비하지 않고도 기존 영상이나 과거 영상을 다시 만들 수 있습니다.

■ 결과 폴더

- RESULTS/<렌더 이름>/: 최종 MP4, 캡션, 통합 업로드 문서 UPLOAD_COPY.txt
- ILLUSTRATION_DROP/: 재사용 GPT Plus 일러스트
""",
    )


def main() -> int:
    if not RUNNER.exists():
        raise RuntimeError("PhoneSpot Codex runner not found")
    write(PREPARE, PREPARE_CODE)
    write(IMPORT, IMPORT_CODE)
    write(REFRESH, REFRESH_CODE)
    py_compile.compile(str(PREPARE), doraise=True)
    py_compile.compile(str(IMPORT), doraise=True)
    py_compile.compile(str(REFRESH), doraise=True)
    patch_runner()
    setup_desk()
    subprocess.run(["python", str(REFRESH)], check=True)
    append_once(
        MEMORY,
        "## 30. Two-click GPT Plus illustration desk",
        """## 30. Two-click GPT Plus illustration desk
- Use `CODEX_VIDEO_DESK/01_PREPARE_GPT_PROMPTS.bat` before rendering.
- It performs script preparation and illustration scouting without TTS or rendering.
- Download GPT Plus images in report order, then run `02_IMPORT_DOWNLOADS_AND_RENDER.bat`.
- The importer previews filename mapping, renames downloads, imports illustrations, applies them, and renders the latest slug.
- Existing Claude folders and Claude runners remain untouched.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-01 - Two-click GPT Plus illustration desk",
        """## 2026-06-01 - Two-click GPT Plus illustration desk
- Removed the wasteful render-first illustration workflow for Codex daily use.
- Added prepare-only scouting and order-based Downloads import.
- Added a two-click workbench while keeping Claude runners isolated.""",
    )
    print("[done] Fast illustration desk installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
