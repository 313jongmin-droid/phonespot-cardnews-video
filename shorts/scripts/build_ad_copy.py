# -*- coding: utf-8 -*-
"""
배너광고 전용 캡션 빌더 (STEP3, 2026-06-19).
메타·당근 광고 등록용 AD_COPY.txt — 카드뉴스 5채널 오가닉 캡션과 별개.
링크 상수(LITTLY_URL·PRECON_URL)는 publish_codex_package 정본 재사용.

입력:  cardnews/output/<slug>/banner_input.json (선택 ad 필드) + banner_script.json
        ad 필드(선택): {"headline": "...", "body": "...", "titles": ["...", ...]}
출력:  cardnews/output/<slug>/AD_COPY.txt  (+ RESULTS/<slug>_banner/AD_COPY.txt 있으면)

사용:  python scripts/build_ad_copy.py <slug>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
try:
    from publish_codex_package import LITTLY_URL, PRECON_URL  # 링크 정본
except Exception:
    LITTLY_URL = "https://litt.ly/phonespot"
    PRECON_URL = "https://ictmarket.or.kr:8443/precon/pop_CertIcon.do?PRECON_REQ_ID=PRE0000194479&YN=1"

ROOT = _HERE.parent.parent
CARD_OUTPUT = ROOT / "cardnews" / "output"
RESULTS = ROOT / "CODEX_VIDEO_DESK" / "RESULTS"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/build_ad_copy.py <slug>")
        return 2
    slug = sys.argv[1]
    base = CARD_OUTPUT / slug
    inp = base / "banner_input.json"
    if not inp.exists():
        print(f"[adcopy] 입력 없음: {inp}")
        return 1
    data = json.loads(inp.read_text(encoding="utf-8"))
    ad = data.get("ad", {}) or {}
    banners = data.get("banners", []) or []
    cta = data.get("cta", {}) or {}

    lines = [str(b.get("tts", "")).strip() for b in banners if str(b.get("tts", "")).strip()]
    headline = str(ad.get("headline") or (lines[0] if lines else "휴대폰성지 폰스팟")).strip()
    body = str(ad.get("body") or " ".join(lines)).strip()
    hook = str(cta.get("hook", "휴대폰 구매할 땐?")).strip()
    punch = str(cta.get("punch", "지원금부터 무료 조회")).strip()
    titles = ad.get("titles") or [headline, f"{headline} | 휴대폰성지 폰스팟"]

    txt = (
        "휴대폰성지 폰스팟 — 배너 광고 카피\n"
        "(메타·당근 광고 등록용 / 유튜브·IG 오가닉 캡션 아님)\n\n"
        "============================================================\n"
        "[광고 제목 후보]\n"
        "============================================================\n"
        + "\n".join(f"- {t}" for t in titles)
        + "\n\n"
        "============================================================\n"
        "[본문]\n"
        "============================================================\n"
        f"{body}\n\n"
        f"{hook} {punch}\n\n"
        "============================================================\n"
        "[CTA / 연락]\n"
        "============================================================\n"
        "휴대폰성지 폰스팟 — 전국 온라인 구매 가능\n"
        "카카오톡 @휴대폰성지폰스팟\n"
        f"링크 {LITTLY_URL}\n\n"
        "============================================================\n"
        "[사전승낙서]\n"
        "============================================================\n"
        f"{PRECON_URL}\n\n"
        "============================================================\n"
        "[등록 체크]\n"
        "============================================================\n"
        "- 영상 소재 = RESULTS/<slug>_banner/<slug>_banner.mp4\n"
        "- 광고 헤드라인/본문은 위에서 복사. 사전승낙서·링크 자동 포함.\n"
        "- 메타: 광고 만들기 > 동영상 > 본문/제목 붙여넣기. 당근: 비즈니스 광고 등록.\n"
    )

    out = base / "AD_COPY.txt"
    out.write_text(txt, encoding="utf-8")
    print(f"[adcopy] {out}")
    rdir = RESULTS / f"{slug}_banner"
    if rdir.exists():
        (rdir / "AD_COPY.txt").write_text(txt, encoding="utf-8")
        print(f"[adcopy] {rdir / 'AD_COPY.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
