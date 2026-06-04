# -*- coding: utf-8 -*-
"""Install the preserved master guide for the PhoneSpot Codex Remotion workflow."""
from __future__ import annotations

import shutil
import os
from datetime import datetime
from pathlib import Path


HERE = Path(__file__).resolve().parent
PHONE = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = PHONE / "shorts"
CODEX = SHORTS / "codex"
DESK = PHONE / "CODEX_VIDEO_DESK"
SOURCE = HERE / "CODEX_MASTER_VIDEO_GUIDE.md"
MASTER = CODEX / "CODEX_MASTER_VIDEO_GUIDE.md"
DESK_GUIDE = DESK / "SYSTEM_GUIDE.md"
README = CODEX / "README_FOR_CODEX.md"
DESK_README = DESK / "README.txt"
MEMORY = CODEX / "CODEX_MEMORY.md"
PATCH_LOG = CODEX / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def backup(path: Path) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_master_guide_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    current = read(path)
    if marker in current:
        print(f"[skip] already documented: {path.name}")
        return
    write(path, current.rstrip() + "\n\n" + body.strip() + "\n")


def main() -> int:
    if not SOURCE.exists():
        raise FileNotFoundError(f"master guide missing: {SOURCE}")
    content = SOURCE.read_text(encoding="utf-8")
    CODEX.mkdir(parents=True, exist_ok=True)
    DESK.mkdir(parents=True, exist_ok=True)
    if read(MASTER) != content.rstrip() + "\n":
        backup(MASTER)
        write(MASTER, content)
    else:
        print(f"[skip] already current: {MASTER}")
    if read(DESK_GUIDE) != content.rstrip() + "\n":
        backup(DESK_GUIDE)
        write(DESK_GUIDE, content)
    else:
        print(f"[skip] already current: {DESK_GUIDE}")
    append_once(
        README,
        "## Master guide read order",
        """## Master guide read order

Before changing the Codex Remotion workflow, read:

1. `CODEX_MASTER_VIDEO_GUIDE.md`
2. `CODEX_BASELINE.md`
3. `README_FOR_CODEX.md`
4. `CODEX_MEMORY.md` only when historical context is needed

Do not remove an existing quality contract while adding a new feature.""",
    )
    append_once(
        DESK_README,
        "■ 시스템 기준 문서",
        """■ 시스템 기준 문서

- `SYSTEM_GUIDE.md`: 현재 영상 출력기의 전체 품질 계약과 롤백 방지 기준입니다.
- 기능 추가나 오류 수정 전에는 이 문서를 먼저 확인합니다.""",
    )
    append_once(
        MEMORY,
        "## 35. Master video guide is the non-regression contract",
        """## 35. Master video guide is the non-regression contract
- Read `CODEX_MASTER_VIDEO_GUIDE.md` before changing the Remotion workflow.
- Preserve existing contracts while adding new features.
- Do not restore separate TTS/display summaries, guessed Korean suffixes, repeated source images, mutable CTA, or legacy output folders.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-01 - Master non-regression video guide",
        """## 2026-06-01 - Master non-regression video guide
- Added `CODEX_MASTER_VIDEO_GUIDE.md`.
- Mirrored the same guide to `CODEX_VIDEO_DESK/SYSTEM_GUIDE.md`.
- Documented active quality contracts, known follow-up items, forbidden regressions, and the safe change procedure.""",
    )
    print("[OK] Master Codex video guide installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
