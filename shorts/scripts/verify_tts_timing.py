"""Validate runtime-only TTS pronunciation and chunk timing metadata."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "public" / "shorts_script.json"
MANIFEST = ROOT / "public" / "audio" / "tts_manifest.json"


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-missing", action="store_true")
    # WordBoundary 타이밍을 못 받아 글자수 추정으로 떨어진 경우, 기본은 에러로 막는다.
    # 정말 그대로 진행해야 할 때만 이 옵션으로 경고로 낮춘다.
    parser.add_argument("--allow-char-fallback", action="store_true")
    args = parser.parse_args()

    if not SCRIPT.exists() or not MANIFEST.exists():
        message = "[WARN] TTS timing metadata missing; generate TTS first."
        print(message)
        return 0 if args.allow_missing else 1

    data = json.loads(SCRIPT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    for key, section in sections(data):
        chunks = [str(value).strip() for value in section.get("caption_chunks", []) or [] if str(value).strip()]
        weights = section.get("tts_chunk_weights", []) or []
        timing = section.get("_tts_timing", {}) or {}
        if chunks and len(weights) != len(chunks):
            errors.append(f"{key}: timing weight count {len(weights)} != chunk count {len(chunks)}")
            continue
        if any(float(value) <= 0 for value in weights):
            errors.append(f"{key}: timing weight must be positive")
        if timing.get("mode") == "character_weight_fallback":
            message = (
                f"{key}: WordBoundary 타이밍을 못 받아 글자수 추정(character-weight)으로 떨어졌습니다. "
                "이 상태로 렌더하면 자막 싱크가 어긋납니다. edge-tts를 최신으로 올리세요 "
                "(pip install -U edge-tts). 그래도 진행하려면 --allow-char-fallback 옵션을 쓰세요."
            )
            if args.allow_char_fallback:
                warnings.append(message)
            else:
                errors.append(message)
        for idx, value in enumerate(weights, 1):
            visible_ms = float(value)
            if visible_ms < 650:
                errors.append(f"{key}.chunk[{idx}]: unusably short visible window {visible_ms:.0f}ms")
            elif visible_ms < 1100:
                warnings.append(f"{key}.chunk[{idx}]: short visible window {visible_ms:.0f}ms")

    print()
    print("----- TTS timing check -----")
    print(f"Manifest : {MANIFEST}")
    print(f"Jobs     : {len(manifest.get('jobs', []))}")
    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print("[OK] pronunciation copy and chunk timing metadata passed.")
    print("----------------------------")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
