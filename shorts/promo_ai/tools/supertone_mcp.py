#!/usr/bin/env python3
"""
슈퍼톤 TTS — 커스텀 MCP 래퍼 (폰스팟 promo_ai 나레이션용)

목적: 슈퍼톤 REST API를 MCP 도구로 감싸서 Claude(Cowork)와 직접 연동.
      Claude가 supertone_tts를 호출 → mp3가 나레이션 폴더에 바로 저장 → 곧장 ffmpeg 합성.
      (Higgsfield처럼 CDN 다운로드→투입 과정이 사라짐.)

── 셋업 (종민 로컬 PC, 1회) ────────────────────────────────
  1) pip install mcp requests
  2) console.supertoneapi.com 에서 API 키 발급 (계정당 3개)
  3) 환경변수 설정:
       set SUPERTONE_API_KEY=발급받은키
       (선택) set SUPERTONE_OUT=C:\\backup\\phonespot_cardnews\\shorts\\promo_ai\\assets\\audio\\narration
  4) Cowork/Claude에 MCP 등록 (stdio):
       claude mcp add supertone -- python "C:\\backup\\phonespot_cardnews\\shorts\\promo_ai\\tools\\supertone_mcp.py"
     또는 Cowork MCP 설정에 command=python, args=[이 파일 경로]

  → 등록 후 Claude 세션에서 supertone_tts / supertone_list_voices 도구가 뜸.

── 주의 ────────────────────────────────────────────────
  - 클론 보이스는 슈퍼톤 Play 웹에서 1회 등록해야 API로 호출 가능(API는 재생만).
  - text는 호출당 300자 제한 → 긴 문장은 문장별로 나눠 호출(청크 자막 싱크에도 유리).
  - API 키는 절대 git에 올리지 말 것(환경변수만 사용).
"""
import os
import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("supertone")

API_KEY = os.environ.get("SUPERTONE_API_KEY", "")
OUT_DIR = os.environ.get(
    "SUPERTONE_OUT",
    r"C:\backup\phonespot_cardnews\shorts\promo_ai\assets\audio\narration",
)
BASE = "https://supertoneapi.com/v1"


@mcp.tool()
def supertone_tts(
    text: str,
    voice_id: str,
    filename: str,
    language: str = "ko",
    model: str = "sona_speech_1",
    output_format: str = "mp3",
    speed: float | None = None,
    pitch_shift: float | None = None,
) -> str:
    """슈퍼톤 한국어 TTS 생성 → mp3(또는 wav)를 나레이션 폴더에 저장하고 경로를 반환.

    Args:
        text: 합성할 대사 (★ 300자 이하 / 긴 문장은 문장별로 호출).
        voice_id: 슈퍼톤 보이스 ID (preset 또는 Play에서 등록한 클론).
        filename: 저장 파일명 (예: '005_n1.mp3').
        language: 'ko' | 'en' | 'ja'.
        model: 'sona_speech_1'(기본) | 'sona_speech_2' | 'sona_speech_2_flash' | 'supertonic_api_3' | 'supertonic_api_1'.
        output_format: 'mp3' | 'wav'.
        speed: 말 속도 (선택, 예 1.0~1.4). None이면 기본.
        pitch_shift: 피치 조절 (선택).
    """
    if not API_KEY:
        return "ERROR: SUPERTONE_API_KEY 환경변수 미설정"
    body: dict = {"text": text, "language": language, "model": model, "output_format": output_format}
    vs: dict = {}
    if speed is not None:
        vs["speed"] = speed
    if pitch_shift is not None:
        vs["pitch_shift"] = pitch_shift
    if vs:
        body["voice_settings"] = vs
    try:
        r = requests.post(
            f"{BASE}/text-to-speech/{voice_id}",
            headers={"x-sup-api-key": API_KEY, "Content-Type": "application/json"},
            json=body,
            timeout=60,
        )
        r.raise_for_status()
    except requests.HTTPError as e:
        return f"ERROR {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return f"ERROR: {e}"
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(r.content)
    dur = r.headers.get("X-Audio-Length", "?")
    return f"saved: {path} (len={dur}s, {len(r.content)} bytes)"


@mcp.tool()
def supertone_list_voices(language: str = "ko") -> str:
    """사용 가능한 보이스 목록 조회 (한국어 캐주얼 톤 고르기용). 실패 시 에러 문자열 반환."""
    if not API_KEY:
        return "ERROR: SUPERTONE_API_KEY 환경변수 미설정"
    # 엔드포인트는 docs.supertoneapi.com/en/docs/core-concepts/voices 기준(변동 가능).
    for ep in ("/voices", "/voices/search"):
        try:
            r = requests.get(
                f"{BASE}{ep}",
                headers={"x-sup-api-key": API_KEY},
                params={"language": language},
                timeout=30,
            )
            if r.status_code == 200:
                return r.text[:4000]
        except Exception:
            continue
    return "ERROR: voice 목록 엔드포인트 확인 필요 (docs/core-concepts/voices). 우선 Play 웹에서 voice_id 복사해 supertone_tts에 직접 넣어도 됨."


if __name__ == "__main__":
    mcp.run()
