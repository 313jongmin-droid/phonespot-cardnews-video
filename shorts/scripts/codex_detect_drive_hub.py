# -*- coding: utf-8 -*-
"""
구글 드라이브 데스크톱이 동기화하는 일러스트 공유 허브 폴더의 '로컬 경로'를 자동 탐지해
shorts/config/library_share_path.txt 에 기입한다. (PC별 1회, git 제외 파일)

- 드라이브 문자(D:~Z:)에서 "내 드라이브\\<HUB>" / "My Drive\\<HUB>" / "<HUB>" 를 찾는다.
- %USERPROFILE%\\Google Drive\\<HUB> 같은 옛 경로도 본다.
- 못 찾으면 안내만 하고 종료(코드 2). 찾으면 기입(코드 0).

HUB 폴더명 기본 "PhoneSpot_Library" (인자 또는 env PHONESPOT_LIBRARY_HUB_NAME 으로 변경).
"""
from __future__ import annotations

import os
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "shorts" / "config" / "library_share_path.txt"

HUB = (
    (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    or os.environ.get("PHONESPOT_LIBRARY_HUB_NAME", "").strip()
    or "PhoneSpot_Library"
)

# Drive 데스크톱 루트 후보 (드라이브 문자 + 내 드라이브/ My Drive)
SUBROOTS = ["내 드라이브", "My Drive", ""]


def candidates() -> list[Path]:
    out: list[Path] = []
    # 드라이브 문자 A~Z (보통 G:)
    for letter in string.ascii_uppercase:
        base = Path(f"{letter}:\\")
        for sub in SUBROOTS:
            out.append(base / sub / HUB if sub else base / HUB)
    # 사용자 프로필 안의 Google Drive (옛 버전/미러 모드)
    up = os.environ.get("USERPROFILE", "")
    if up:
        for name in ("Google Drive", "GoogleDrive"):
            for sub in SUBROOTS:
                p = Path(up) / name
                out.append((p / sub / HUB) if sub else (p / HUB))
    return out


def main() -> int:
    found = None
    for c in candidates():
        try:
            if c.is_dir():
                found = c
                break
        except OSError:
            continue

    if not found:
        print("[drive-hub] 허브 폴더를 못 찾았습니다: '" + HUB + "'")
        print("  - Google Drive 데스크톱 로그인 + 공유폴더 '내 드라이브에 바로가기 추가' 후 다시 실행하거나,")
        print("  - 일러스트_공유허브_경로설정.bat 으로 경로를 직접 넣으세요.")
        return 2

    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(str(found) + "\n", encoding="utf-8")
    print("[drive-hub] 허브 경로 자동 설정 완료:")
    print("  " + str(found))
    print("  -> " + str(CFG))
    print("이제 패널 '관리 > 라이브러리 동기화' 로 합치면 됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
