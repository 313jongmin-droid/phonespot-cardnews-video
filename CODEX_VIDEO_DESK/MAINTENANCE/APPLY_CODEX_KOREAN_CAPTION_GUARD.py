# -*- coding: utf-8 -*-
"""Install a conservative Korean caption guard into the shared PhoneSpot shorts track.

This patch deliberately stops generative suffix decoration at runtime. The source
caption chunks are already written Korean; runtime code should preserve them and
fail closed if malformed Korean somehow reaches the render boundary.
"""
from __future__ import annotations

import importlib.util
import json
import py_compile
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
SHORTS = ROOT / "shorts"
ENHANCER = SHORTS / "scripts" / "codex_enhance_script.py"
VALIDATOR = SHORTS / "scripts" / "validate_codex_korean.py"
RUNNER = SHORTS / "run_codex_casual.bat"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
OUTPUT = ROOT / "cardnews" / "output"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
FIXED_CTA_CHUNKS = ["휴대폰 구매할 땐?", "지원금부터 무료로 조회해보세요"]
FIXED_CTA_TTS = "휴대폰 구매할 땐? 지원금부터 무료로 조회해보세요."


OLD_CONSTANTS = '''SOURCE_WORDS = ["보도", "외신", "매체", "팁스터", "기자", "ZDNet", "9to5Mac", "블룸버그", "맥루머스"]
FINAL_ENDINGS = ("습니다", "합니다", "입니다", "됩니다", "했습니다", "전망입니다", "가능합니다", "밝혔습니다", "전했습니다")
CONNECTIVE_ENDINGS = ("고", "며", "면서", "지만", "는데", "라며", "라고", "하면", "되면", "기준", "이후", "함께", "통해", "위해", "반면")
BAD_PHRASES = [
    "에 따르면에 따르면",
    "와 관련해와 관련해",
    "반면와 관련해",
    "기기에서와 관련해",
    "기종별와 관련해",
    "기준으로기준으로",
    "입니다입니다",
    "합니다합니다",
]'''


NEW_CONSTANTS = '''SOURCE_WORDS = ["보도", "외신", "매체", "팁스터", "기자", "ZDNet", "9to5Mac", "블룸버그", "맥루머스"]
BAD_PHRASES = [
    "에 따르면에 따르면",
    "와 관련해와 관련해",
    "반면와 관련해",
    "기기에서와 관련해",
    "기종별와 관련해",
    "기준으로기준으로",
    "입니다입니다",
    "합니다합니다",
    "됩니다입니다",
    "습니다입니다",
]

# PhoneSpot CTA is a channel-level contract, not article copy.
FIXED_CTA_CHUNKS = ["휴대폰 구매할 땐?", "지원금부터 무료로 조회해보세요"]
FIXED_CTA_TTS = "휴대폰 구매할 땐? 지원금부터 무료로 조회해보세요."

# Runtime caption handling is intentionally conservative. Caption chunks are
# authored Korean. Never invent a predicate or connective suffix here.
MALFORMED_KOREAN_PATTERNS = [
    re.compile(r"(?:다|니다)(?:입니다|합니다|됩니다|습니다)(?=[.!?,]|$)"),
    re.compile(r"(?:입니다|합니다|됩니다|습니다){2,}"),
    re.compile(r"(?:에 따르면){2,}"),
    re.compile(r"(?:와 관련해){2,}"),
]'''


OLD_FUNCTIONS = '''def needs_display_repair(section: dict) -> bool:
    chunks = section_texts(section)
    display = [clean_text(x) for x in section.get("display_chunks", []) or [] if clean_text(x)]
    if not chunks:
        return False
    if len(display) != len(chunks):
        return True
    joined = " ".join(display)
    if any(bad in joined for bad in BAD_PHRASES):
        return True
    endings = [re.sub(r"[\\s.,!?]+$", "", x)[-5:] for x in display if x]
    if len(endings) >= 3 and len(set(endings)) == 1:
        return True
    if any(no_space_len(x) > 42 for x in display):
        return True
    return False


def is_final_sentence(text: str) -> bool:
    s = text.rstrip(" .,!?:;")
    return s.endswith(FINAL_ENDINGS)


def make_display_sentence(chunk: str, idx: int, total: int) -> str:
    s = normalize_tts(chunk).rstrip(" .,!?:;")
    if not s:
        return s
    if is_final_sentence(s):
        return s + "."

    is_last = idx == total - 1
    if not is_last:
        if "에 따르면" in s or "보도에 따르면" in s:
            return s + ","
        if any(word in s for word in SOURCE_WORDS):
            return s + "에 따르면,"
        if s.endswith(CONNECTIVE_ENDINGS):
            return s + ","
        return s + ","

    if "전망" in s or "가능성" in s:
        return s + "으로 보입니다."
    if "보도" in s:
        return s + "했습니다."
    if "개발 중" in s:
        return s + "인 기능으로 알려졌습니다."
    if "지원" in s or "적용" in s or "설정" in s:
        return s + "됩니다."
    if s.endswith(("예정", "계획")):
        return s + "입니다."
    return s + "입니다."


def repair_display(section: dict) -> None:
    chunks = section_texts(section)
    if not chunks:
        return
    display = [make_display_sentence(chunk, idx, len(chunks)) for idx, chunk in enumerate(chunks)]
    # Final polish for duplicated connective artifacts.
    fixed = []
    for item in display:
        item = clean_text(item)
        for bad in BAD_PHRASES:
            item = item.replace(bad, bad[: max(1, len(bad) // 2)])
        item = item.replace("에 따르면에 따르면", "에 따르면")
        item = item.replace("와 관련해와 관련해", "와 관련해")
        item = item.replace("입니다.", "입니다.").replace("합니다.", "합니다.")
        fixed.append(item)
    section["display_chunks"] = fixed'''


NEW_FUNCTIONS = '''def malformed_korean_reason(text: str) -> str | None:
    value = clean_text(text)
    for bad in BAD_PHRASES:
        if bad in value:
            return f"duplicated phrase: {bad}"
    for pattern in MALFORMED_KOREAN_PATTERNS:
        match = pattern.search(value)
        if match:
            return f"duplicated Korean ending: {match.group(0)}"
    return None


def needs_display_repair(section: dict) -> bool:
    chunks = section_texts(section)
    display = [clean_text(x) for x in section.get("display_chunks", []) or [] if clean_text(x)]
    if not chunks:
        return False
    if len(display) != len(chunks):
        return True
    if any(malformed_korean_reason(item) for item in display):
        return True
    # A prior runtime pass used to turn complete source sentences into comma
    # fragments. Restore those from the authored caption chunks.
    for source, shown in zip(chunks, display):
        if re.search(r"[.!?。！？]$", source) and shown.rstrip().endswith(","):
            return True
    if any(no_space_len(x) > 42 for x in display):
        return True
    return False


def make_display_sentence(chunk: str, idx: int, total: int) -> str:
    # Kept as a public helper for compatibility with earlier patches.
    # Do not append guessed Korean particles or endings at runtime.
    return normalize_tts(chunk)


def repair_display(section: dict) -> None:
    chunks = section_texts(section)
    if not chunks:
        return
    section["display_chunks"] = [make_display_sentence(chunk, idx, len(chunks)) for idx, chunk in enumerate(chunks)]


def enforce_fixed_cta(data: dict) -> None:
    cta = data.setdefault("cta", {})
    cta["tts"] = FIXED_CTA_TTS
    cta["caption_body"] = list(FIXED_CTA_CHUNKS)
    cta["caption_emphasis"] = [FIXED_CTA_CHUNKS[1]]
    cta["headline_lines"] = [
        {"text": FIXED_CTA_CHUNKS[0]},
        {"text": FIXED_CTA_CHUNKS[1], "accent": True},
    ]
    cta["caption_chunks"] = list(FIXED_CTA_CHUNKS)
    cta["display_chunks"] = list(FIXED_CTA_CHUNKS)
    cta["chunk_visuals"] = [
        {"type": "illust", "value": "smartphone"},
        {"type": "logo", "value": None},
    ]
    cta["_codex_fixed_cta"] = True
    cta["_codex_narration_source"] = "fixed_cta_contract"


def validate_korean_contract(data: dict) -> None:
    errors = []
    for section_name, section in section_list(data):
        chunks = section_texts(section)
        display = [clean_text(x) for x in section.get("display_chunks", []) or [] if clean_text(x)]
        if chunks and len(display) != len(chunks):
            errors.append(f"{section_name}: caption/display count mismatch {len(chunks)} != {len(display)}")
        for field_name, values in (("caption_chunks", chunks), ("display_chunks", display)):
            for idx, item in enumerate(values, 1):
                reason = malformed_korean_reason(item)
                if reason:
                    errors.append(f"{section_name}.{field_name}[{idx}]: {reason}: {item}")
        for idx, (source, shown) in enumerate(zip(chunks, display), 1):
            if re.search(r"[.!?。！？]$", source) and shown.rstrip().endswith(","):
                errors.append(f"{section_name}.display_chunks[{idx}]: complete sentence became comma fragment: {shown}")
        formal_endings = []
        for item in display:
            match = re.search(r"(합니다|입니다|됩니다|했습니다|있습니다|없습니다)[.!?。！？]?$", item)
            formal_endings.append(match.group(1) if match else None)
        for idx in range(max(0, len(formal_endings) - 2)):
            run = formal_endings[idx : idx + 3]
            if run[0] and len(set(run)) == 1:
                errors.append(
                    f"{section_name}.display_chunks[{idx + 1}:{idx + 3}]: "
                    f"robotic repeated ending `{run[0]}`; author a contextual Korean flow"
                )
    cta = data.get("cta", {})
    if cta.get("tts") != FIXED_CTA_TTS:
        errors.append("cta.tts: fixed CTA contract changed")
    if cta.get("caption_chunks") != FIXED_CTA_CHUNKS:
        errors.append("cta.caption_chunks: fixed CTA contract changed")
    if cta.get("display_chunks") != FIXED_CTA_CHUNKS:
        errors.append("cta.display_chunks: fixed CTA contract changed")
    cta_visuals = cta.get("chunk_visuals", []) or []
    if len(cta_visuals) != 2 or cta_visuals[-1].get("type") != "logo":
        errors.append("cta.chunk_visuals: fixed CTA must end with the PhoneSpot logo")
    if errors:
        raise ValueError("Korean caption contract failed\\n- " + "\\n- ".join(errors))'''


OLD_ENHANCE_TAIL = '''    auto_balance_illustrations(data, slug)
    data["_codex_global_999_quality"] = True'''

NEW_ENHANCE_TAIL = '''    auto_balance_illustrations(data, slug)
    enforce_fixed_cta(data)
    validate_korean_contract(data)
    data["_codex_global_999_quality"] = True'''


VALIDATOR_CODE = r'''# -*- coding: utf-8 -*-
"""Fail closed when malformed Korean captions reach the Codex render boundary."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ENHANCER = ROOT / "shorts" / "scripts" / "codex_enhance_script.py"
OUTPUT = ROOT / "cardnews" / "output"


def load_enhancer():
    spec = importlib.util.spec_from_file_location("codex_enhance_script", ENHANCER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {ENHANCER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_codex_korean.py <slug>")
        return 2
    slug = sys.argv[1]
    path = OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[korean_guard] missing: {path}")
        return 2
    data = json.loads(path.read_text(encoding="utf-8"))
    enhancer = load_enhancer()
    try:
        enhancer.validate_korean_contract(data)
    except ValueError as exc:
        print(f"[korean_guard] FAIL: {slug}")
        print(exc)
        return 2
    print(f"[korean_guard] OK: {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> None:
    target = path.with_name(path.name + f".bak_korean_guard_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"[skip] already patched: {label}")
        return text
    if old not in text:
        raise RuntimeError(f"patch anchor missing: {label}")
    print(f"[patch] {label}")
    return text.replace(old, new, 1)


def ensure_fixed_cta_patch(text: str) -> str:
    if "FIXED_CTA_CHUNKS =" not in text:
        anchor = "# Runtime caption handling is intentionally conservative."
        addition = (
            '# PhoneSpot CTA is a channel-level contract, not article copy.\n'
            'FIXED_CTA_CHUNKS = ["휴대폰 구매할 땐?", "지원금부터 무료로 조회해보세요"]\n'
            'FIXED_CTA_TTS = "휴대폰 구매할 땐? 지원금부터 무료로 조회해보세요."\n\n'
        )
        if anchor not in text:
            raise RuntimeError("CTA constants anchor missing")
        text = text.replace(anchor, addition + anchor, 1)
        print("[patch] fixed CTA constants")

    if "def enforce_fixed_cta(data: dict) -> None:" not in text:
        anchor = "def validate_korean_contract(data: dict) -> None:"
        addition = '''def enforce_fixed_cta(data: dict) -> None:
    cta = data.setdefault("cta", {})
    cta["tts"] = FIXED_CTA_TTS
    cta["caption_body"] = list(FIXED_CTA_CHUNKS)
    cta["caption_emphasis"] = [FIXED_CTA_CHUNKS[1]]
    cta["headline_lines"] = [
        {"text": FIXED_CTA_CHUNKS[0]},
        {"text": FIXED_CTA_CHUNKS[1], "accent": True},
    ]
    cta["caption_chunks"] = list(FIXED_CTA_CHUNKS)
    cta["display_chunks"] = list(FIXED_CTA_CHUNKS)
    cta["chunk_visuals"] = [
        {"type": "illust", "value": "smartphone"},
        {"type": "logo", "value": None},
    ]
    cta["_codex_fixed_cta"] = True
    cta["_codex_narration_source"] = "fixed_cta_contract"


'''
        if anchor not in text:
            raise RuntimeError("CTA function anchor missing")
        text = text.replace(anchor, addition + anchor, 1)
        print("[patch] fixed CTA enforcer")

    if 'errors.append("cta.tts: fixed CTA contract changed")' not in text:
        anchor = '    if errors:\n        raise ValueError("Korean caption contract failed\\n- " + "\\n- ".join(errors))'
        addition = '''    cta = data.get("cta", {})
    if cta.get("tts") != FIXED_CTA_TTS:
        errors.append("cta.tts: fixed CTA contract changed")
    if cta.get("caption_chunks") != FIXED_CTA_CHUNKS:
        errors.append("cta.caption_chunks: fixed CTA contract changed")
    if cta.get("display_chunks") != FIXED_CTA_CHUNKS:
        errors.append("cta.display_chunks: fixed CTA contract changed")
    cta_visuals = cta.get("chunk_visuals", []) or []
    if len(cta_visuals) != 2 or cta_visuals[-1].get("type") != "logo":
        errors.append("cta.chunk_visuals: fixed CTA must end with the PhoneSpot logo")
'''
        if anchor not in text:
            raise RuntimeError("CTA validator anchor missing")
        text = text.replace(anchor, addition + anchor, 1)
        print("[patch] fixed CTA validator")

    if "    enforce_fixed_cta(data)\n    validate_korean_contract(data)" not in text:
        anchor = "    auto_balance_illustrations(data, slug)\n    validate_korean_contract(data)"
        replacement = "    auto_balance_illustrations(data, slug)\n    enforce_fixed_cta(data)\n    validate_korean_contract(data)"
        if anchor not in text:
            raise RuntimeError("CTA render-boundary anchor missing")
        text = text.replace(anchor, replacement, 1)
        print("[patch] fixed CTA render boundary")
    return text


def patch_enhancer() -> None:
    backup(ENHANCER)
    text = ENHANCER.read_text(encoding="utf-8")
    if "def malformed_korean_reason(text: str) -> str | None:" not in text:
        text = replace_once(text, OLD_CONSTANTS, NEW_CONSTANTS, "safe Korean constants")
        text = replace_once(text, OLD_FUNCTIONS, NEW_FUNCTIONS, "preserve authored captions")
        text = replace_once(text, OLD_ENHANCE_TAIL, NEW_ENHANCE_TAIL, "enhancer fail-closed validation")
    else:
        print("[skip] Korean caption guard already present")
    text = ensure_fixed_cta_patch(text)
    ENHANCER.write_text(text, encoding="utf-8")
    print(f"[write] {ENHANCER}")


def patch_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    validator = '''python scripts\\validate_codex_korean.py !SLUG!
if errorlevel 1 goto :fail'''
    if validator in text:
        print("[skip] runner already validates Korean")
        return
    anchor = '''python scripts\\copy_assets.py !SLUG!'''
    replacement = validator + "\n" + anchor
    if anchor not in text:
        raise RuntimeError("runner patch anchor missing")
    backup(RUNNER)
    RUNNER.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")
    print(f"[write] {RUNNER}")


def enforce_fixed_cta_payload(data: dict) -> bool:
    cta = data.setdefault("cta", {})
    expected = {
        "tts": FIXED_CTA_TTS,
        "caption_body": list(FIXED_CTA_CHUNKS),
        "caption_emphasis": [FIXED_CTA_CHUNKS[1]],
        "headline_lines": [
            {"text": FIXED_CTA_CHUNKS[0]},
            {"text": FIXED_CTA_CHUNKS[1], "accent": True},
        ],
        "caption_chunks": list(FIXED_CTA_CHUNKS),
        "display_chunks": list(FIXED_CTA_CHUNKS),
        "chunk_visuals": [
            {"type": "illust", "value": "smartphone"},
            {"type": "logo", "value": None},
        ],
        "_codex_fixed_cta": True,
        "_codex_narration_source": "fixed_cta_contract",
    }
    touched = False
    for key, value in expected.items():
        if cta.get(key) != value:
            cta[key] = value
            touched = True
    return touched


def repair_existing_outputs() -> int:
    repaired = 0
    for path in OUTPUT.glob("*/shorts_script.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        touched = enforce_fixed_cta_payload(data)
        sections = [data.get("hook", {})] + list(data.get("facts", []) or []) + [data.get("cta", {})]
        for section in sections:
            captions = [str(x).strip() for x in section.get("caption_chunks", []) or [] if str(x).strip()]
            displays = [str(x).strip() for x in section.get("display_chunks", []) or [] if str(x).strip()]
            malformed = any(
                bad in item
                for item in displays
                for bad in (
                    "입니다입니다", "합니다합니다", "됩니다입니다", "습니다입니다",
                    "듭니다입니다", "납니다입니다", "에 따르면에 따르면", "와 관련해와 관련해",
                )
            )
            sentence_to_comma = any(
                re.search(r"[.!?。！？]$", source) and shown.endswith(",")
                for source, shown in zip(captions, displays)
            )
            if captions and (len(captions) != len(displays) or malformed or sentence_to_comma):
                section["display_chunks"] = captions
                touched = True
        if touched:
            backup_path = path.with_name(path.name + f".bak_korean_guard_{STAMP}")
            shutil.copy2(path, backup_path)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            repaired += 1
            print(f"[repair] {path}")
    return repaired


def append_note(path: Path, heading: str, body: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if heading in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + f"\n{heading}\n{body}\n", encoding="utf-8")
    print(f"[note] {path}")


def import_enhancer():
    spec = importlib.util.spec_from_file_location("codex_enhance_script", ENHANCER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {ENHANCER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def self_test() -> None:
    py_compile.compile(str(ENHANCER), doraise=True)
    py_compile.compile(str(VALIDATOR), doraise=True)
    module = import_enhancer()
    expected = "절반 이하로 줄어듭니다."
    actual = module.make_display_sentence(expected, 0, 1)
    if actual != expected:
        raise RuntimeError(f"self-test failed: {actual!r}")
    sample = {"hook": {"caption_chunks": [expected], "display_chunks": ["절반 이하로 줄어듭니다입니다."]}, "facts": [], "cta": {}}
    module.repair_display(sample["hook"])
    module.enforce_fixed_cta(sample)
    module.validate_korean_contract(sample)
    if sample["hook"]["display_chunks"] != [expected]:
        raise RuntimeError("repair self-test failed")
    print("[test] Korean caption preservation OK")


def main() -> int:
    if not ENHANCER.exists() or not RUNNER.exists():
        raise RuntimeError("PhoneSpot shared shorts files not found")
    patch_enhancer()
    VALIDATOR.write_text(VALIDATOR_CODE, encoding="utf-8")
    print(f"[write] {VALIDATOR}")
    patch_runner()
    repaired = repair_existing_outputs()
    append_note(
        MEMORY,
        "## 23. Korean caption fail-closed guard",
        "- Runtime caption code must preserve authored caption_chunks. Never append guessed Korean endings or particles.\n"
        "- Complete source sentences must never be converted into comma fragments.\n"
        "- CTA is fixed globally: `휴대폰 구매할 땐?` / `지원금부터 무료로 조회해보세요`, ending with the PhoneSpot logo.\n"
        "- validate_codex_korean.py runs before asset copy and blocks malformed duplicated endings such as `줄어듭니다입니다.`.",
    )
    append_note(
        PATCH_LOG,
        "## 2026-05-31 — Korean caption fail-closed guard",
        "- Removed runtime suffix decoration that produced malformed Korean such as `줄어듭니다입니다.`.\n"
        "- Runtime display fallback now preserves authored caption chunks verbatim.\n"
        "- Locked the global CTA copy, CTA TTS, two-screen CTA layout, and closing logo.\n"
        "- Added pre-render Korean validator and repaired malformed existing display chunks without touching TTS or visual mappings.",
    )
    append_note(
        MEMORY,
        "## 24. Fixed PhoneSpot CTA contract",
        "- Every Codex Remotion short ends with exactly two CTA chunks: `휴대폰 구매할 땐?` / `지원금부터 무료로 조회해보세요`.\n"
        "- CTA TTS uses the same copy, the first visual is `illust:smartphone`, and the closing visual is the PhoneSpot logo.\n"
        "- captions.md article-specific CTA copy must never override this channel-level CTA.",
    )
    append_note(
        PATCH_LOG,
        "## 2026-05-31 - Fixed CTA contract",
        "- Locked CTA display copy, TTS copy, two-screen structure, and closing logo globally.\n"
        "- Added render-boundary CTA validation and repaired existing Codex shorts scripts.",
    )
    self_test()
    print(f"[done] repaired existing scripts: {repaired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
