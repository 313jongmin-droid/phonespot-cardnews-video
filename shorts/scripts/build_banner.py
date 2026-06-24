# -*- coding: utf-8 -*-
"""
배너광고 트랙 빌더 (STEP2, 2026-06-19) — casual build_script/generate_tts 무수정 독립 스크립트.

입력:  cardnews/output/<slug>/banner_input.json
       { "slug", "format"(9x16|1x1|4x5), "captionsOn"(bool),
         "banners": [ {"image": "b1.png", "tts": "배너1 나레이션"}, ... ],
         "cta": {"hook": "...", "punch": "...", "tts": "CTA 나레이션"} }
출력:  cardnews/output/<slug>/banner_script.json  (+ shorts/public/shorts_script.json 복사)
       shorts/public/audio/<slug>_b{N}.mp3 / <slug>_cta.mp3  (edge-tts, 있을 때만)

BannerAdShort.tsx 가 읽는 shape:
  { banners:[{image,audioKey,caption}], cta:{kakao,location,litt,caption_chunks,audioKey}, captionsOn, format }

사용:  python scripts/build_banner.py <slug>
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARD_OUTPUT = ROOT / "cardnews" / "output"
PUBLIC = SHORTS / "public"
AUDIO = PUBLIC / "audio"
VOICE = os.getenv("PHONESPOT_TTS_VOICE", "ko-KR-SunHiNeural")

# 브랜드 CTA 기본값 (build_script.py 와 동일 — 휴대폰성지 폰스팟)
DEFAULT_CTA = {
    "kakao": "@휴대폰성지폰스팟",
    "location": "내 손 안의 성지찾기, 폰스팟",
    "litt": "litt.ly/phonespot",
}


def find_ffmpeg() -> str | None:
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


async def _synth(text: str, out: Path) -> None:
    import edge_tts  # type: ignore
    com = edge_tts.Communicate(text, VOICE)
    await com.save(str(out))


def normalize(path: Path) -> None:
    """라우드니스 -14 LUFS (카드뉴스 finalize 와 동일 타깃)."""
    ff = find_ffmpeg()
    if not ff or not path.exists():
        return
    tmp = path.with_suffix(".raw.mp3")
    try:
        path.replace(tmp)
        subprocess.run(
            [ff, "-y", "-i", str(tmp), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", str(path)],
            capture_output=True,
        )
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/build_banner.py <slug>")
        return 2
    slug = sys.argv[1]
    inp = CARD_OUTPUT / slug / "banner_input.json"
    if not inp.exists():
        print(f"[banner] 입력 없음: {inp}\n  (패널 배너탭이 banner_input.json 을 먼저 써야 함 — STEP4)")
        return 1

    data = json.loads(inp.read_text(encoding="utf-8"))
    fmt = data.get("format", "9x16")
    cap_on = bool(data.get("captionsOn", False))
    banners_in = data.get("banners", []) or []
    cta_in = data.get("cta", {}) or {}
    AUDIO.mkdir(parents=True, exist_ok=True)

    try:
        import edge_tts  # noqa: F401
        have_tts = True
    except Exception:
        have_tts = False
        print("[banner] edge-tts 미설치 → 오디오 생략(스크립트 JSON만 작성). 렌더PC에서 재실행 필요.")

    banners = []
    jobs: list[tuple[str, str]] = []
    for i, b in enumerate(banners_in, 1):
        key = f"{slug}_b{i}"
        text = str(b.get("tts", "")).strip()
        banners.append({"image": b.get("image", ""), "audioKey": key, "caption": text})
        jobs.append((key, text))

    cta_key = f"{slug}_cta"
    jobs.append((cta_key, str(cta_in.get("tts", "")).strip()))
    cta = dict(DEFAULT_CTA)
    cta["caption_chunks"] = [
        str(cta_in.get("hook", "휴대폰 구매할 땐?")),
        str(cta_in.get("punch", "지원금부터 무료 조회")),
    ]
    cta["audioKey"] = cta_key

    if have_tts:
        for key, text in jobs:
            if not text:
                continue
            out = AUDIO / f"{key}.mp3"
            try:
                asyncio.run(_synth(text, out))
                normalize(out)
                print(f"[tts] {key} <- {text[:24]}")
            except Exception as exc:
                print(f"[tts] 실패 {key}: {exc}")

    script = {
        "slug": slug,
        "_track": "banner_ad",
        "format": fmt,
        "captionsOn": cap_on,
        "banners": banners,
        "cta": cta,
    }
    out_json = CARD_OUTPUT / slug / "banner_script.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy2(out_json, PUBLIC / "shorts_script.json")
    print(f"[banner] script: {out_json}")
    print(f"[banner] 배너 {len(banners)}장 + cta / format={fmt} / captions={cap_on}")
    print("[banner] public/shorts_script.json 갱신 → 컴포지션 'BannerAd' 렌더 가능")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
