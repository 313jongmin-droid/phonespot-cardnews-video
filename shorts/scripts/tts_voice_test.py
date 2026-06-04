"""
Create short voice samples for choosing the free edge-tts voice.

Usage:
  python scripts\tts_voice_test.py
"""
import asyncio
from pathlib import Path

import edge_tts

ROOT = Path(__file__).parent.parent
OUT = ROOT / "out_codex" / "tts_voice_tests"
OUT.mkdir(parents=True, exist_ok=True)

TEXT = (
    "??????????? ???????????????????? ??????????????. "
    "??? ????? ???????????????????"
)

VOICES = [
    ("sunhi_38", "ko-KR-SunHiNeural", "+38%", "+0Hz"),
    ("sunhi_45", "ko-KR-SunHiNeural", "+45%", "+0Hz"),
    ("injoon_38", "ko-KR-InJoonNeural", "+38%", "+0Hz"),
    ("hyunsu_38", "ko-KR-HyunsuNeural", "+38%", "+0Hz"),
]


async def main():
    for name, voice, rate, pitch in VOICES:
        path = OUT / f"{name}.mp3"
        print(f"[TTS] {name} -> {path}")
        await edge_tts.Communicate(TEXT, voice=voice, rate=rate, pitch=pitch).save(str(path))
    print(f"Done. Open folder: {OUT}")


if __name__ == "__main__":
    asyncio.run(main())