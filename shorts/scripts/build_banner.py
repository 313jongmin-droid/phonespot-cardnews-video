# -*- coding: utf-8 -*-
"""
배너광고 트랙 빌더 (2026-06-19, 나레이션 제거판) — 이미지 N장이 위로 넘어가는 영상 + 선택 BGM.
casual build_script/generate_tts 무수정 독립 스크립트.

입력:  cardnews/output/<slug>/banner_input.json
       { "slug", "format"(9x16|1x1|4x5), "secPerBanner"(float),
         "bgm"(파일명, 선택), "bgmVol"(float),
         "banners": [ {"image": "b1.png"}, ... ] }
출력:  cardnews/output/<slug>/banner_script.json  (+ shorts/public/shorts_script.json 복사)

BannerAdShort.tsx 가 읽는 shape:
  { slug, _track, format, secPerBanner, bgm, bgmVol, banners:[{image,audioKey:"",caption:""}] }
  - 나레이션 없음(audioKey 비움). BGM 은 public/assets/banners/<bgm> 에서 staticFile 로 로드.
  - CTA = public/assets/banners/_cta.png 있으면 banners 끝에 자동첨부.

사용:  python scripts/build_banner.py <slug>
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARD_OUTPUT = ROOT / "cardnews" / "output"
PUBLIC = SHORTS / "public"
BANNERS_DIR = PUBLIC / "assets" / "banners"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/build_banner.py <slug>")
        return 2
    slug = sys.argv[1]
    inp = CARD_OUTPUT / slug / "banner_input.json"
    if not inp.exists():
        print(f"[banner] 입력 없음: {inp}\n  (패널 배너탭이 banner_input.json 을 먼저 써야 함)")
        return 1

    data = json.loads(inp.read_text(encoding="utf-8"))
    fmt = data.get("format", "9x16")
    sec = float(data.get("secPerBanner") or 2.8)
    bgm_vol = float(data.get("bgmVol") or 0.6)
    banners_in = data.get("banners", []) or []

    def _valid_image(rel: str) -> bool:
        # imgSrc 규칙과 동일: 경로 포함이면 assets/<rel>, 아니면 assets/banners/<rel>
        fp = (PUBLIC / "assets" / rel) if "/" in rel else (BANNERS_DIR / rel)
        try:
            head = fp.read_bytes()[:16]
        except Exception:
            return False
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return True
        if head[:3] == b"\xff\xd8\xff":
            return True
        if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
            return True
        return False

    banners = []
    for b in banners_in:
        img = str(b.get("image", "")).strip()
        if not img:
            continue
        if not _valid_image(img):
            print(f"[banner] 이미지 없음/손상 -> 건너뜀: {img}")
            continue
        banners.append({"image": img, "audioKey": "", "caption": ""})

    # CTA = 재사용 _cta.png 자동첨부 (유효한 이미지일 때만)
    cta = BANNERS_DIR / "_cta.png"
    if cta.exists() and _valid_image("_cta.png"):
        banners.append({"image": "_cta.png", "audioKey": "", "caption": ""})
    elif cta.exists():
        print(f"[banner] _cta.png 손상/비이미지({cta.stat().st_size}B) -> CTA 생략. 실제 PNG로 교체하세요.")
    else:
        print("[banner] _cta.png 없음 -> CTA 생략 (public/assets/banners/_cta.png 두면 자동첨부)")

    if not banners:
        print("[banner] 유효한 배너 이미지가 없습니다. 업로드/파일명을 확인하세요.")
        return 1

    # BGM 검증: 파일명만 받음. 실제로 assets/banners/ 에 있어야 적용
    bgm_name = str(data.get("bgm") or "").strip()
    bgm_rel = ""
    if bgm_name:
        if (BANNERS_DIR / bgm_name).exists():
            bgm_rel = "assets/banners/" + bgm_name
        else:
            print(f"[banner] BGM 파일 없음: {BANNERS_DIR / bgm_name} -> BGM 생략")

    script = {
        "slug": slug,
        "_track": "banner_ad",
        "format": fmt,
        "secPerBanner": sec,
        "bgm": bgm_rel,
        "bgmVol": bgm_vol,
        "banners": banners,
    }
    out_json = CARD_OUTPUT / slug / "banner_script.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(out_json, PUBLIC / "shorts_script.json")
    print(f"[banner] script: {out_json}")
    print(f"[banner] 배너 {len(banners)}장 / {sec}s each / format={fmt} / bgm={bgm_rel or '(없음)'}")
    print("[banner] public/shorts_script.json 갱신 -> 컴포지션 'BannerAd' 렌더 가능")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
