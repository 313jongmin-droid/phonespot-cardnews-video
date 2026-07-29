# -*- coding: utf-8 -*-
"""
단말기 누끼(투명배경) 이미지 임포트 (2026-07-16)

목적: 종민 PC의 누끼 작업 폴더(예: OneDrive\\Desktop\\누끼 작업물)에 쌓이는 단말기 PNG를
      렌더가 쓰는 photos 라이브러리(shorts/public/assets/photos/)로 복사한다.
      Remotion 은 public/assets 밑만 staticFile 로 참조 → 외부 폴더는 복사해야 매칭·렌더됨.

핵심: photo 매칭은 '파일명 토큰이 청크에 등장'(렉시컬)이라, 영문 파일명(iphone17_pro…)은
      한국어 청크와 안 맞음 → 브랜드 + 한국어 폼팩터(프로/울트라/플립/폴드/에어/플러스)로
      리네임해 복사한다. 모델 숫자(16/17/25/26)는 매처가 2자리 숫자를 비구별 처리하므로
      브랜드·폼팩터 수준 매칭(기존 photos 동작과 동일).

소스 경로 결정: ① 인자 sys.argv[1] ② shorts/config/device_photos_path.txt(1줄) ③ 기본 상수.
      경로 없거나 폴더 없으면 스킵(비파괴). git 제외(투명 png 라이브러리는 photos/처럼 로컬).

사용:  python scripts/import_device_photos.py            # 설정/기본 경로에서
       python scripts/import_device_photos.py "D:\\누끼"  # 경로 직접
캐시:  대상에 같은 크기 파일 있으면 스킵(변경분만 복사).
"""
from __future__ import annotations
import re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
PHOTO_DIR = SHORTS / "public" / "assets" / "photos"
CFG = SHORTS / "config" / "device_photos_path.txt"
DEFAULT_SRC = r"C:\Users\313jo\OneDrive\Desktop\누끼 작업물"

# 소스 파일 stem -> 대상 파일명(확장자 제외). 브랜드 + 한국어 폼팩터.
RENAME = {
    "S26_basic_nukki_shadow_transparent": "삼성_갤럭시_S26",
    "S26_plus_nukki_shadow_transparent": "삼성_갤럭시_S26_플러스",
    "S26_ultra_nukki_shadow_transparent": "삼성_갤럭시_S26_울트라",
    "S26_ultra_512_nukki_shadow_transparent": "삼성_갤럭시_S26_울트라_512",
    "galaxy_a17_nukki_shadow_transparent": "삼성_갤럭시_A17",
    "galaxy_flip7_nukki_shadow_transparent": "삼성_갤럭시_Z_플립7",
    "galaxy_fold7_nukki_shadow_transparent": "삼성_갤럭시_Z_폴드7",
    "galaxy_jump4_nukki_shadow_transparent": "삼성_갤럭시_점프4",
    "galaxy_quantum6_nukki_shadow_transparent": "삼성_갤럭시_퀀텀6",
    "iphone16_nukki_shadow_transparent": "애플_아이폰16",
    "iphone16e_nukki_shadow_transparent": "애플_아이폰16e",
    "iphone16pro_nukki_shadow_transparent": "애플_아이폰16_프로",
    "iphone17_air_nukki_shadow_transparent": "애플_아이폰17_에어",
    "iphone17_nukki_shadow_transparent": "애플_아이폰17",
    "iphone17_pro_nukki_shadow_transparent": "애플_아이폰17_프로",
    "iphone17_promax_nukki_shadow_transparent": "애플_아이폰17_프로맥스",
    "iphone17e_nukki_shadow_transparent": "애플_아이폰17e",
    "s25_edge_nukki_shadow_transparent": "삼성_갤럭시_S25_엣지",
    "s25_fe_nukki_shadow_transparent": "삼성_갤럭시_S25_FE",
    "s25_plus_nukki_shadow_transparent": "삼성_갤럭시_S25_플러스",
    "s25_ultra_nukki_shadow_transparent": "삼성_갤럭시_S25_울트라",
    "폴드8": "삼성_갤럭시_Z_폴드8",
    "폴드8_라벤더": "삼성_갤럭시_Z_폴드8_라벤더",
    "폴드8울트라": "삼성_갤럭시_Z_폴드8_울트라",
    "폴드8울트라_화이트": "삼성_갤럭시_Z_폴드8_울트라_화이트",
    "플립8": "삼성_갤럭시_Z_플립8",
    "플립8_화이트": "삼성_갤럭시_Z_플립8_화이트",
}

# 리네임 맵에 없는 신규 파일용 폴백: 노이즈 토큰 제거 + 영문 브랜드→한글.
_NOISE = ("nukki", "shadow", "transparent", "512")
_BRAND = [("iphone", "애플_아이폰"), ("galaxy", "삼성_갤럭시")]


def _fallback_name(stem: str) -> str:
    s = stem
    for br, ko in _BRAND:
        s = re.sub(br, ko + "_", s, flags=re.IGNORECASE)
    parts = [p for p in re.split(r"[\s_\-]+", s) if p and p.lower() not in _NOISE]
    return "_".join(parts) or stem


def _resolve_src() -> Path | None:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return Path(sys.argv[1].strip())
    try:
        if CFG.exists():
            line = CFG.read_text(encoding="utf-8").strip().splitlines()
            if line and line[0].strip():
                return Path(line[0].strip())
    except Exception:
        pass
    return Path(DEFAULT_SRC)


def main() -> int:
    src = _resolve_src()
    if not src or not src.exists():
        print(f"[device-import] 소스 폴더 없음 → 스킵(비파괴): {src}")
        return 0
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src.iterdir() if p.is_file() and p.suffix.lower() == ".png")
    if not files:
        print(f"[device-import] png 없음: {src}")
        return 0
    imported, skipped = 0, 0
    for p in files:
        target_stem = RENAME.get(p.stem) or _fallback_name(p.stem)
        dst = PHOTO_DIR / f"{target_stem}.png"
        try:
            if dst.exists() and dst.stat().st_size == p.stat().st_size:
                skipped += 1
                continue
            shutil.copy2(p, dst)
            imported += 1
            print(f"    [device-import] {p.name} -> {dst.name}")
        except Exception as exc:
            print(f"    [device-import] 실패 {p.name}: {exc}")
    print(f"[device-import] 복사 {imported} / 스킵(동일) {skipped} / 전체 {len(files)} -> {PHOTO_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
