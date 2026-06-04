# -*- coding: utf-8 -*-
"""Install a global TTS-caption lockstep contract for Codex Remotion shorts."""
from __future__ import annotations

import os
import py_compile
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
SHORTS = ROOT / "shorts"
SCRIPTS = SHORTS / "scripts"
ENHANCER = SCRIPTS / "codex_enhance_script.py"
LOCKSTEP = SCRIPTS / "codex_caption_lockstep.py"
CHUNK_UTIL = SHORTS / "src" / "components" / "casual" / "chunkUtil.ts"
CAPTION_RULES = SHORTS / "harness" / "CAPTION_RULES.md"
BASELINE = SHORTS / "codex" / "CODEX_BASELINE.md"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


LOCKSTEP_CODE = r'''# -*- coding: utf-8 -*-
"""Build readable Korean display chunks directly from each TTS narration."""
from __future__ import annotations

import re
from typing import Callable


MIN_UNITS = 9
TARGET_UNITS = 17
MAX_UNITS = 24
ABSOLUTE_MAX_UNITS = 30

SENTENCE_END_RE = re.compile(r"[.!?。！？][\"'”’)]*$")
COMMA_END_RE = re.compile(r"[,;:][\"'”’)]*$")
CONNECTIVE_END_RE = re.compile(
    r"(?:고|며|면서|면|다면|지만|는데|으며|라며|하고|하거나|되며|되어|해서|하며|때문에|반면|이후|전후|경우)[,;:]?$"
)
DEPENDENT_NEXT_RE = re.compile(
    r"^(?:원|원으로|원을|원에|만원|억원|조원|달러|유로|개|건|명|배|퍼센트|%|년|월|일|시간|분|초|GB|TB|MB|기가|테라|와트|W|mAh)(?:[은는이가을를에도으로]*)$",
    re.I,
)
COHESIVE_NEXT_RE = re.compile(
    r"^(?:[A-Z][A-Z0-9+.-]{1,}|[0-9][0-9A-Za-z+.,/-]*|마시|하시|않|못|되|있|없|같|위한|통해|대해|위해|부터|까지|및|또는|모바일)",
    re.I,
)
NO_BREAK_AFTER_RE = re.compile(r"^(?:약|최대|최소|총|한|두|세|몇|바로|직접|한\s*번|두\s*번|세\s*번|번)$")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def units(text: str) -> int:
    return len(re.sub(r"\s+", "", text or ""))


def compare_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", clean_text(text), flags=re.UNICODE).lower()


def strip_display_periods(text: str) -> str:
    return re.sub(r"\.(?=(?:[\"'”’)]*)?(?:\s|$))", "", clean_text(text))


def boundary_score(token: str, next_token: str, current_units: int, remaining_units: int) -> int:
    distance = abs(TARGET_UNITS - current_units)
    score = 100 - distance
    sentence_end = bool(SENTENCE_END_RE.search(token))
    if sentence_end:
        score += 1000
    elif COMMA_END_RE.search(token):
        score += 500
    elif CONNECTIVE_END_RE.search(token):
        score += 280
    if remaining_units and remaining_units < MIN_UNITS:
        score -= 700
    if not sentence_end and next_token and (DEPENDENT_NEXT_RE.search(next_token) or COHESIVE_NEXT_RE.search(next_token)):
        score -= 900
    if NO_BREAK_AFTER_RE.search(token):
        score -= 900
    return score


def choose_break(tokens: list[str], start: int) -> int:
    total = len(tokens)
    candidates: list[tuple[int, int]] = []
    consumed = ""
    for end in range(start + 1, total + 1):
        consumed = " ".join(tokens[start:end])
        current_units = units(consumed)
        if current_units > ABSOLUTE_MAX_UNITS:
            break
        remaining = " ".join(tokens[end:])
        remaining_units = units(remaining)
        if current_units >= MIN_UNITS or end == total:
            next_token = tokens[end] if end < total else ""
            candidates.append((boundary_score(tokens[end - 1], next_token, current_units, remaining_units), end))
        if current_units >= MAX_UNITS:
            break
    if not candidates:
        return min(total, start + 1)
    return max(candidates, key=lambda item: (item[0], item[1]))[1]


def merge_short_chunks(chunks: list[str]) -> list[str]:
    output: list[str] = []
    for chunk in chunks:
        chunk = clean_text(chunk)
        if not chunk:
            continue
        if output and units(chunk) < MIN_UNITS and units(output[-1] + " " + chunk) <= ABSOLUTE_MAX_UNITS:
            output[-1] = clean_text(output[-1] + " " + chunk)
        else:
            output.append(chunk)
    if len(output) >= 2 and units(output[0]) < MIN_UNITS and units(output[0] + " " + output[1]) <= ABSOLUTE_MAX_UNITS:
        output[:2] = [clean_text(output[0] + " " + output[1])]
    return output


def split_tts_caption(text: str) -> list[str]:
    narration = clean_text(text)
    if not narration:
        return []
    tokens = narration.split()
    chunks: list[str] = []
    cursor = 0
    while cursor < len(tokens):
        end = choose_break(tokens, cursor)
        chunks.append(clean_text(" ".join(tokens[cursor:end])))
        cursor = end
    chunks = merge_short_chunks(chunks)
    if compare_text(" ".join(chunks)) != compare_text(narration):
        raise ValueError("caption splitter changed narration content")
    return chunks


def sync_section_to_tts(section: dict) -> None:
    narration = clean_text(section.get("tts", ""))
    if not narration:
        return
    chunks = split_tts_caption(narration)
    section["caption_chunks"] = chunks
    section["display_chunks"] = [strip_display_periods(chunk) for chunk in chunks]
    section["_codex_caption_lockstep"] = {
        "version": 1,
        "policy": "display chunks are an ordered, lossless partition of section TTS",
        "chunk_count": len(chunks),
    }


def validate_section_lockstep(section_name: str, section: dict, no_space_len: Callable[[str], int]) -> list[str]:
    errors: list[str] = []
    narration = clean_text(section.get("tts", ""))
    chunks = [clean_text(value) for value in section.get("caption_chunks", []) or [] if clean_text(value)]
    display = [clean_text(value) for value in section.get("display_chunks", []) or [] if clean_text(value)]
    if narration and compare_text(" ".join(chunks)) != compare_text(narration):
        errors.append(f"{section_name}: caption chunks do not match TTS narration")
    if chunks and compare_text(" ".join(display)) != compare_text(" ".join(chunks)):
        errors.append(f"{section_name}: display chunks do not match caption chunks")
    if len(chunks) != len(display):
        errors.append(f"{section_name}: caption/display count mismatch {len(chunks)} != {len(display)}")
    for idx, chunk in enumerate(chunks, 1):
        length = no_space_len(chunk)
        if length > ABSOLUTE_MAX_UNITS:
            errors.append(f"{section_name}.caption_chunks[{idx}]: too long ({length} > {ABSOLUTE_MAX_UNITS})")
        if len(chunks) > 1 and length < 4:
            errors.append(f"{section_name}.caption_chunks[{idx}]: orphan short chunk ({length})")
    return errors
'''


LOCKSTEP_GUIDE = """
## TTS와 화면 청크 — 반드시 일치

- TTS 나레이션과 화면 청크는 별도의 요약문으로 만들지 않습니다.
- 화면 청크는 해당 구간 TTS 원문을 순서대로 빠짐없이 나눈 결과여야 합니다.
- 화면에서 마침표는 숨길 수 있지만, 단어를 추가하거나 삭제하거나 바꾸지 않습니다.
- 청크 분할은 문장 끝, 쉼표, 연결 어미, 한국어 호흡 순서로 판단합니다.
- 한 청크는 공백 제외 9~27자를 우선하며, 최대 34자를 넘기지 않습니다.
- 1초 미만으로 지나가는 고아 청크를 만들지 않습니다.
- TTS 발음 사전은 음성 합성 단계에서만 적용합니다. 화면 자막 원문은 바꾸지 않습니다.
- 시각 자료 매핑, 고정 CTA, 원본 이미지 1회 사용, 일러스트 균형 규칙은 그대로 유지합니다.
"""


def backup(path: Path, label: str) -> None:
    if not path.exists():
        return
    target = path.with_name(f"{path.name}.bak_{label}_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    current = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker in current:
        print(f"[skip] already documented: {path.name}")
        return
    write(path, current.rstrip() + "\n\n" + body.strip() + "\n")


def patch_enhancer() -> None:
    if not ENHANCER.exists():
        raise RuntimeError(f"enhancer missing: {ENHANCER}")
    text = ENHANCER.read_text(encoding="utf-8")
    import_line = "from codex_caption_lockstep import sync_section_to_tts, validate_section_lockstep\n"
    if import_line not in text:
        anchor = "from codex_illustration_db import rank_variants, record_usage_snapshot\n"
        if anchor not in text:
            raise RuntimeError("enhancer import anchor missing")
        text = text.replace(anchor, anchor + import_line, 1)
    validation_anchor = '        for field_name, values in (("caption_chunks", chunks), ("display_chunks", display)):\n'
    validation_insert = "        errors.extend(validate_section_lockstep(section_name, section, no_space_len))\n"
    if validation_insert not in text:
        if validation_anchor not in text:
            raise RuntimeError("enhancer validation anchor missing")
        text = text.replace(validation_anchor, validation_insert + validation_anchor, 1)
    sync_anchor = "        fallback_tts(section)\n"
    sync_insert = "        sync_section_to_tts(section)\n"
    if sync_insert not in text:
        if sync_anchor not in text:
            raise RuntimeError("enhancer sync anchor missing")
        text = text.replace(sync_anchor, sync_anchor + sync_insert, 1)
    text = text.replace(
        'section["_codex_sync_mode"] = "global999_preserve_chunks_visuals"',
        'section["_codex_sync_mode"] = "global999_tts_caption_lockstep"',
    )
    text = text.replace(
        '"Global 001-999 rule: captions.md narration is TTS-only; "\n'
        '        "screen chunks and curated visuals are preserved unless invalid."',
        '"Global 001-999 rule: screen chunks are rebuilt as an ordered, lossless partition "\n'
        '        "of captions.md narration; curated visuals are rebalanced without discarding quality rules."',
    )
    backup(ENHANCER, "tts_caption_lockstep")
    write(ENHANCER, text)


def patch_chunk_util() -> None:
    if not CHUNK_UTIL.exists():
        print(f"[skip] chunk util not found: {CHUNK_UTIL}")
        return
    text = CHUNK_UTIL.read_text(encoding="utf-8")
    old = '''export const stripDisplaySentencePeriods = (value: string) =>
  value.replace(/\\./g, (dot, offset, source) => {
    const before = source[offset - 1] || "";
    const after = source[offset + 1] || "";
    return /\\d/.test(before) && /\\d/.test(after) ? dot : "";
  });'''
    new = '''export const stripDisplaySentencePeriods = (value: string) =>
  value.replace(/\\.(?=(?:["'”’)]*)?(?:\\s|$))/g, "");'''
    if new in text:
        print("[skip] display-period guard already preserves domains")
        return
    if old not in text:
        raise RuntimeError("chunkUtil display-period anchor missing")
    backup(CHUNK_UTIL, "tts_caption_lockstep")
    write(CHUNK_UTIL, text.replace(old, new, 1))


def patch_caption_rules() -> None:
    marker = "## TTS와 화면 청크 — 반드시 일치"
    append_once(CAPTION_RULES, marker, LOCKSTEP_GUIDE)


def patch_baseline() -> None:
    marker = "## TTS-caption lockstep"
    append_once(
        BASELINE,
        marker,
        """## TTS-caption lockstep
- 화면 청크는 해당 구간 TTS 원문을 순서대로 빠짐없이 분할한 결과입니다.
- 화면 자막용 별도 요약문을 만들지 않습니다.
- 마침표 숨김 외에는 단어 추가·삭제·치환을 금지합니다.
- 기존 고정 CTA, 원본 이미지 1회 사용, 일러스트 균형, 한국어 자연스러움 규칙을 유지합니다.""",
    )


def main() -> int:
    print("=" * 60)
    print(" PhoneSpot Codex - TTS Caption Lockstep")
    print("=" * 60)
    write(LOCKSTEP, LOCKSTEP_CODE)
    patch_enhancer()
    patch_chunk_util()
    patch_caption_rules()
    patch_baseline()
    append_once(
        MEMORY,
        "## 34. TTS-caption lockstep",
        """## 34. TTS-caption lockstep
- Display captions are no longer independent summaries.
- Every non-CTA display sequence is rebuilt from its TTS narration in order without omissions or additions.
- Sentence periods may be hidden visually. Pronunciation dictionary changes spoken copy only.
- Existing visual, CTA, Korean, and source-image-once contracts remain active.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-01 - TTS-caption lockstep",
        """## 2026-06-01 - TTS-caption lockstep
- Added a shared Korean narration splitter.
- Rebuilt display chunks from section TTS instead of preserving mismatched card-news summaries.
- Added fail-closed validation for TTS/caption/display content equality.""",
    )
    py_compile.compile(str(LOCKSTEP), doraise=True)
    py_compile.compile(str(ENHANCER), doraise=True)
    if (SHORTS / "tsconfig.json").exists():
        subprocess.run(["cmd", "/c", "npx tsc --noEmit"], cwd=SHORTS, check=True)
    print("[OK] Global TTS-caption lockstep installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
