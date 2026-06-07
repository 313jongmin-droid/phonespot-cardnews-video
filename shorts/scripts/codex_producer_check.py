# -*- coding: utf-8 -*-
"""
풀-생산기 점검: 이 PC가 카드뉴스 생성 + 영상 렌더를 모두 독립으로 할 수 있는지 확인.
모든 항목 PASS 면 종료코드 0, 치명 항목 하나라도 빠지면 1.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"

OK = "[ OK ]"
NO = "[FAIL]"
WARN = "[WARN]"


def main() -> int:
    rows: list[tuple[str, bool, str, bool]] = []  # (label, ok, detail, critical)

    def add(label, ok, detail="", critical=True):
        rows.append((label, ok, detail, critical))

    add(f"Python {sys.version_info.major}.{sys.version_info.minor}", sys.version_info >= (3, 10),
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    add("Node.js", bool(shutil.which("node")), shutil.which("node") or "없음")
    add("npm", bool(shutil.which("npm")), shutil.which("npm") or "없음")
    remotion = SHORTS / "node_modules" / "@remotion" / "cli"
    add("Remotion (npm install)", remotion.exists(), str(remotion))
    ffmpeg = SHORTS / "node_modules" / "@remotion" / "compositor-win32-x64-msvc" / "ffmpeg.exe"
    add("FFmpeg (remotion compositor)", ffmpeg.exists(), str(ffmpeg))
    pw = ROOT / ".playwright"
    add("Playwright Chromium", bool(pw.exists() and any(pw.glob("chromium-*"))), str(pw))

    py_mods = {
        "edge_tts": ("edge-tts (TTS)", True),
        "PIL": ("Pillow (이미지)", True),
        "mutagen": ("mutagen (오디오)", True),
        "requests": ("requests", True),
        "playwright": ("playwright (py)", True),
        "flask": ("Flask (카드뉴스 webui)", True),
        "numpy": ("numpy (임베딩)", False),
        "fastembed": ("fastembed (임베딩)", False),
    }
    for mod, (label, crit) in py_mods.items():
        add(label, importlib.util.find_spec(mod) is not None, mod, crit)

    # 임베딩 실제 가용성(모델 로드까지) — 없어도 폴백 동작하므로 비치명(경고)
    sys.path.insert(0, str(SHORTS / "scripts"))
    try:
        import codex_illust_embed as ce
        add("텍스트 임베딩 사용가능", ce.available(), "lexical 폴백 가능", critical=False)
    except Exception as exc:  # noqa: BLE001
        add("텍스트 임베딩 사용가능", False, str(exc)[:40], critical=False)
    try:
        import codex_image_embed as ie
        add("그림 내용 임베딩(CLIP) 사용가능", ie.available(), "없으면 그림매칭 폴백", critical=False)
    except Exception as exc:  # noqa: BLE001
        add("그림 내용 임베딩(CLIP) 사용가능", False, str(exc)[:40], critical=False)

    add("영상 실행 파일", (SHORTS / "run_codex_casual.bat").exists(), "run_codex_casual.bat")

    # ----- 카드뉴스 렌더 자원(이게 있어야 새 PC에서 카드까지 찍힘) -----
    CN = ROOT / "cardnews"
    add("카드뉴스 webui", (CN / "webui" / "app.py").exists(), "cardnews/webui/app.py")
    add("카드 렌더 실행기", (CN / "scripts" / "run_windows.py").exists(), "cardnews/scripts/run_windows.py")
    add("카드 렌더러", (CN / "scripts" / "cardnews_renderer_v2.py").exists(), "cardnews/scripts/cardnews_renderer_v2.py")
    fonts = list((CN / "fonts").glob("*.woff")) if (CN / "fonts").exists() else []
    add("카드 폰트(Pretendard woff)", len(fonts) >= 1, f"{len(fonts)}개 in {CN / 'fonts'}")
    if 0 < len(fonts) < 9:
        add("카드 폰트 9종 완비", False, f"{len(fonts)}/9 (일부 굵기 누락 가능)", critical=False)
    add("카드 실행 배치", (CN / "run_pngs.bat").exists() or (CN / "run_all.bat").exists(), "run_pngs.bat / run_all.bat")

    print("=" * 60)
    print(" PhoneSpot 풀-생산기 점검")
    print("=" * 60)
    crit_fail = 0
    warn = 0
    for label, ok, detail, critical in rows:
        if ok:
            mark = OK
        elif critical:
            mark = NO; crit_fail += 1
        else:
            mark = WARN; warn += 1
        print(f"{mark} {label}" + (f"  ({detail})" if detail and not ok else ""))
    print("-" * 60)
    if crit_fail == 0:
        print(f"[RESULT] 생산 준비 완료 (치명 0, 경고 {warn})")
        if warn:
            print("  * 경고(임베딩)는 SETUP_EMBED 로 켜면 그림매칭 품질이 올라갑니다. 없어도 동작.")
        return 0
    print(f"[RESULT] 준비 미완료 — 치명 {crit_fail}개. 위 FAIL 항목을 설치하세요.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
