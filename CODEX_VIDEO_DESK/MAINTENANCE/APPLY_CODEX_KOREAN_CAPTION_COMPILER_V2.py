# -*- coding: utf-8 -*-
"""Install the experimental Korean caption compiler V2 for PhoneSpot Remotion."""
from __future__ import annotations

import importlib.util
import os
import py_compile
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path(os.environ.get("PHONESPOT_ROOT", r"C:\Users\di898\Documents\phonespot_cardnews"))
SHORTS = ROOT / "shorts"
LOCKSTEP = SHORTS / "scripts" / "codex_caption_lockstep.py"
CHUNK_UTIL = SHORTS / "src" / "components" / "casual" / "chunkUtil.ts"
RUNNER = SHORTS / "run_codex_casual.bat"
VALIDATOR = SHORTS / "scripts" / "validate_caption_compiler_v2.py"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LABEL = f"bak_caption_compiler_v2_{STAMP}"
BACKED_UP: set[Path] = set()


PY_SEMANTIC_HELPERS = r'''

# CODEX_CAPTION_COMPILER_V2
# Protect high-value Korean bundles before selecting a display chunk boundary.
NUMBERISH_END_RE = re.compile(r"\d+(?:[,.]\d+)?(?:\ub9cc|\uc5b5|\uc870)?$")
DEPENDENT_BUNDLE_RE = re.compile(
    r"^(?:\uc6d0(?:\ub300)?|\ub9cc\uc6d0|\uc5b5\uc6d0|\uc870\uc6d0|\ub2ec\ub7ec|\uc720\ub85c|\uac1c|\uac74|\uba85|\ubc30|%|GB|TB|MB|W|mAh)"
    r"(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4\uc73c\ub85c\uc5d0\uc11c\uae4c\uc9c0\ubd80\ud130]*)$",
    re.I,
)
LAW_HEAD_RE = re.compile(r"(?:\uc2dc\ud589\ub839|\uc2dc\ud589\uaddc\uce59|\ubc95\ub960|\ubc95|\uace0\uc2dc|\uc870\ub840|\uaddc\uce59)$")
LAW_ARTICLE_RE = re.compile(r"^\uc81c?\d+\uc870(?:\uc758\d+)?(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4\uc73c\ub85c\uc5d0\uc11c]*)?$")
PRODUCT_HEAD_RE = re.compile(r"^(?:\uc544\uc774\ud3f0|\uac24\ub7ed\uc2dc|\ud53d\uc140|\uc544\uc774\ud328\ub4dc|\uac24\ub7ed\uc2dc\ud0ed|\uac24\ub7ed\uc2dc\ud3f4\ub4dc|\uac24\ub7ed\uc2dc\ud50c\ub9bd)$", re.I)
PRODUCT_MODEL_RE = re.compile(r"^(?:[A-Z]?\d+[A-Za-z+.-]*|S\d+|Z\d+)$", re.I)
MODEL_NUMBER_RE = re.compile(r"^(?:[A-Z]?\d+[A-Za-z+.-]*|S\d+|Z\d+)$", re.I)
MODEL_SUFFIX_RE = re.compile(r"^(?:\ud504\ub85c|\ud50c\ub7ec\uc2a4|\uc6b8\ud2b8\ub77c|\uc5d0\uc5b4|FE|\ud3f4\ub4dc|\ud50c\ub9bd)(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4\uc73c\ub85c]*)?$", re.I)


def compact_token(token: str) -> str:
    return re.sub(r"[\s,.;:!?\u3002\uff01\uff1f\"'\u201d\u2019()]+", "", str(token or ""))


def forbidden_boundary(token: str, next_token: str) -> bool:
    current = compact_token(token)
    following = compact_token(next_token)
    if not current or not following:
        return False
    if NUMBERISH_END_RE.search(current) and DEPENDENT_BUNDLE_RE.search(following):
        return True
    if LAW_HEAD_RE.search(current) and LAW_ARTICLE_RE.search(following):
        return True
    if PRODUCT_HEAD_RE.search(current) and PRODUCT_MODEL_RE.search(following):
        return True
    if MODEL_NUMBER_RE.search(current) and MODEL_SUFFIX_RE.search(following):
        return True
    return False
'''


PY_VALIDATE_BOUNDARIES = r'''
    for idx in range(len(chunks) - 1):
        left = chunks[idx].split()[-1] if chunks[idx].split() else ""
        right = chunks[idx + 1].split()[0] if chunks[idx + 1].split() else ""
        if forbidden_boundary(left, right):
            errors.append(f"{section_name}.caption_chunks[{idx + 1}:{idx + 3}]: protected phrase was split")
'''


VALIDATOR_V2 = r'''# -*- coding: utf-8 -*-
"""Block renders that violate Korean caption compiler V2 contracts."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from codex_caption_lockstep import ABSOLUTE_MAX_UNITS, forbidden_boundary, units


ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT = ROOT / "cardnews" / "output"


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts\\validate_caption_compiler_v2.py <slug>")
        return 2
    slug = sys.argv[1]
    path = OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[caption_v2] missing: {path}")
        return 2
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    errors: list[str] = []
    for name, section in sections(data):
        chunks = [str(x or "").strip() for x in section.get("caption_chunks", []) or [] if str(x or "").strip()]
        if name != "cta":
            for idx, chunk in enumerate(chunks, 1):
                if units(chunk) > ABSOLUTE_MAX_UNITS:
                    errors.append(f"{name}.caption_chunks[{idx}]: {units(chunk)} > {ABSOLUTE_MAX_UNITS}")
        for idx in range(len(chunks) - 1):
            left = chunks[idx].split()[-1] if chunks[idx].split() else ""
            right = chunks[idx + 1].split()[0] if chunks[idx + 1].split() else ""
            if forbidden_boundary(left, right):
                errors.append(f"{name}.caption_chunks[{idx + 1}:{idx + 3}]: protected phrase split")
    if errors:
        print("[caption_v2] ERROR")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"[caption_v2] OK: {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


TS_LAYOUT_HELPERS = r'''

// CODEX_CAPTION_COMPILER_V2
// Keep the 72px type contract. Use the browser's real Pretendard metrics to
// select line breaks instead of shrinking the type when a caption is long.
const CAPTION_FONT_SIZE = 72;
const CAPTION_FONT_WEIGHT = 900;
const CAPTION_MAX_LINE_PIXELS = 920;
let captionMeasureContext: CanvasRenderingContext2D | null | undefined;

const getCaptionMeasureContext = () => {
  if (captionMeasureContext !== undefined) {
    return captionMeasureContext;
  }
  if (typeof document === "undefined") {
    captionMeasureContext = null;
    return captionMeasureContext;
  }
  const canvas = document.createElement("canvas");
  captionMeasureContext = canvas.getContext("2d");
  return captionMeasureContext;
};

const measureCaptionPixels = (value: string) => {
  const context = getCaptionMeasureContext();
  if (!context) {
    return estimateDisplayUnits(value) * CAPTION_FONT_SIZE;
  }
  context.font = `${CAPTION_FONT_WEIGHT} ${CAPTION_FONT_SIZE}px Pretendard, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`;
  return context.measureText(value).width;
};

const AWKWARD_LINE_END_RE = /(?:\uc2dc\ud589\ub839|\uc2dc\ud589\uaddc\uce59|\ubc95\ub960|\ubc95|\uc81c?\d+\uc870(?:\uc758\d+)?|\d+(?:[,.]\d+)?(?:\ub9cc|\uc5b5|\uc870)?)$/;
'''


TS_PROTECTED_INSERT = r'''  /(?:\uc2dc\ud589\ub839|\uc2dc\ud589\uaddc\uce59|\ubc95\ub960|\ubc95|\uace0\uc2dc|\uc870\ub840|\uaddc\uce59)\s+\uc81c?\s*\d+\s*\uc870(?:\uc758\s*\d+)?(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4]|\uc73c\ub85c|\uc5d0\uc11c)?/g,
  /\d+\s*\ub9cc\s*\uc6d0(?:\ub300(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4]|\uc73c\ub85c|\uc5d0\uc11c|\ubd80\ud130|\uae4c\uc9c0)?|\uc5d0\uc11c|\ubd80\ud130|\uae4c\uc9c0)?/g,
  /\d+(?:[,.]\d+)?\s*(?:\uc6d0|\ub9cc\uc6d0|\uc5b5\uc6d0|\uc870\uc6d0|\ud37c\uc13c\ud2b8|%|\uc720\ub85c|\ub2ec\ub7ec|\uac1c|\uba85|\uac1c\uc6d4)(?:[\uc740\ub294\uc774\uac00\uc744\ub97c\uc5d0\ub3c4]|\uc73c\ub85c|\uc5d0\uc11c|\uae4c\uc9c0)?/g,
  /(?:\uc544\uc774\ud3f0|\uac24\ub7ed\uc2dc|\ud53d\uc140|\uc544\uc774\ud328\ub4dc|\uac24\ub7ed\uc2dc\ud0ed)\s*[A-Za-z0-9+.-]+(?:\s*(?:\ud504\ub85c|\ud50c\ub7ec\uc2a4|\uc6b8\ud2b8\ub77c|\uc5d0\uc5b4|FE|\ud3f4\ub4dc|\ud50c\ub9bd))?/gi,
'''


TS_SCORE_V2 = r'''const scoreLines = (lines: string[]) => {
  const widths = lines.map(measureCaptionPixels);
  const overflow = widths.reduce((sum, width) => sum + Math.max(0, width - CAPTION_MAX_LINE_PIXELS), 0);
  const spread = Math.max(...widths) - Math.min(...widths);
  const badStartPenalty = lines.slice(1).reduce((sum, line) => {
    const first = line.split(/\s+/)[0] || "";
    return sum + (isBadLineStart(first) ? 400 : 0);
  }, 0);
  const awkwardEndPenalty = lines.slice(0, -1).reduce((sum, line) => {
    const last = line.split(/\s+/).filter(Boolean).pop() || "";
    return sum + (AWKWARD_LINE_END_RE.test(last) ? 260 : 0);
  }, 0);
  const rhythmBonus = lines.slice(0, -1).reduce((sum, line) => {
    const words = line.split(/\s+/).filter(Boolean);
    const last = words.length ? words[words.length - 1] : "";
    return sum + (shouldBreakAfter(last) ? -18 : 0);
  }, 0);
  return overflow * 30 + spread * 0.16 + badStartPenalty + awkwardEndPenalty + rhythmBonus + (lines.length - 1) * 28;
};'''


TS_FORMAT_V2 = r'''export function formatCaptionLines(text: string, _maxLineChars = 18, maxLines = 3): string {
  const clean = stripDisplaySentencePeriods(text).replace(/\n/g, " ").trim();
  if (!clean) {
    return clean;
  }

  const protectedText = protectTokens(clean);
  const words = protectedText.text.split(/\s+/).filter(Boolean);
  if (words.length <= 1) {
    return protectedText.restore(clean);
  }

  let best = { lines: [protectedText.restore(protectedText.text)], score: Number.POSITIVE_INFINITY };

  const tryBreaks = (breaks: number[]) => {
    const lines: string[] = [];
    let start = 0;
    for (const br of breaks) {
      lines.push(words.slice(start, br).join(" "));
      start = br;
    }
    lines.push(words.slice(start).join(" "));
    const restored = lines.map((line) => protectedText.restore(line));
    const fixed = moveBadLineStarts(restored);
    const score = scoreLines(fixed);
    if (score < best.score) {
      best = { lines: fixed, score };
    }
  };

  tryBreaks([]);
  if (maxLines >= 2) {
    for (let i = 1; i < words.length; i++) {
      tryBreaks([i]);
    }
  }
  if (maxLines >= 3) {
    for (let i = 1; i < words.length - 1; i++) {
      for (let j = i + 1; j < words.length; j++) {
        tryBreaks([i, j]);
      }
    }
  }

  return best.lines.join("\n");
}'''


def backup(path: Path) -> None:
    resolved = path.resolve()
    if not path.exists() or resolved in BACKED_UP:
        return
    target = path.with_name(path.name + f".{LABEL}")
    shutil.copy2(path, target)
    BACKED_UP.add(resolved)
    print(f"[backup] {target}")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"[write] {path}")


def append_once(path: Path, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker in text:
        return
    write(path, text.rstrip() + "\n\n" + body.strip() + "\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"patch anchor missing: {label}")
    return text.replace(old, new, 1)


def replace_regex(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"patch anchor missing: {label}")
    return updated


def patch_lockstep() -> None:
    text = LOCKSTEP.read_text(encoding="utf-8")
    if "CODEX_CAPTION_COMPILER_V2" in text:
        print("[skip] lockstep V2 already installed")
        return
    backup(LOCKSTEP)
    text = text.replace("TARGET_UNITS = 17", "TARGET_UNITS = 16", 1)
    text = text.replace("MAX_UNITS = 24", "MAX_UNITS = 22", 1)
    text = text.replace("ABSOLUTE_MAX_UNITS = 30", "ABSOLUTE_MAX_UNITS = 26", 1)
    text = replace_once(text, "\ndef boundary_score(", PY_SEMANTIC_HELPERS + "\n\ndef boundary_score(", "Python semantic helpers")
    text = replace_once(
        text,
        "    if NO_BREAK_AFTER_RE.search(token):\n        score -= 900\n",
        "    if NO_BREAK_AFTER_RE.search(token):\n        score -= 900\n"
        "    if forbidden_boundary(token, next_token):\n        score -= 4000\n",
        "Python protected-boundary score",
    )
    text = replace_once(
        text,
        '        "version": 1,\n        "policy": "display chunks are an ordered, lossless partition of section TTS",',
        '        "version": 2,\n        "compiler": "korean_caption_compiler_v2",\n'
        '        "policy": "display chunks are an ordered, lossless semantic partition of section TTS",',
        "Python lockstep metadata",
    )
    text = replace_once(text, "    return errors\n", PY_VALIDATE_BOUNDARIES + "    return errors\n", "Python boundary validation")
    write(LOCKSTEP, text)


def patch_chunk_util() -> None:
    text = CHUNK_UTIL.read_text(encoding="utf-8")
    if "CODEX_CAPTION_COMPILER_V2" in text:
        print("[skip] chunkUtil V2 already installed")
        return
    backup(CHUNK_UTIL)
    text = replace_once(text, "const repairOrphanListMarkers", TS_LAYOUT_HELPERS + "\n\nconst repairOrphanListMarkers", "pixel measurement helpers")
    text = replace_once(text, "const PROTECTED_PATTERNS = [\n", "const PROTECTED_PATTERNS = [\n" + TS_PROTECTED_INSERT, "semantic protected tokens")
    text = replace_regex(text, r"const scoreLines = \(lines: string\[\], maxLineChars: number\) => \{.*?\n\};", TS_SCORE_V2, "pixel line scoring")
    text = replace_regex(
        text,
        r"export function formatCaptionLines\(text: string, maxLineChars = 18, maxLines = 3\): string \{.*?\n\}\n\nexport function getChunkWindows",
        TS_FORMAT_V2 + "\n\nexport function getChunkWindows",
        "pixel line formatter",
    )
    write(CHUNK_UTIL, text)


def patch_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    marker = "python scripts\\validate_caption_compiler_v2.py !SLUG!"
    if marker in text:
        print("[skip] runner already validates caption compiler V2")
        return
    anchor = "python scripts\\validate_codex_korean.py !SLUG!\nif errorlevel 1 goto :fail"
    if anchor not in text:
        raise RuntimeError("runner patch anchor missing")
    backup(RUNNER)
    replacement = anchor + "\n" + marker + "\nif errorlevel 1 goto :fail"
    write(RUNNER, text.replace(anchor, replacement, 1))


def run_self_test() -> None:
    spec = importlib.util.spec_from_file_location("codex_caption_lockstep_v2", LOCKSTEP)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import V2 lockstep")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    samples = {
        "law": "\uc2dc\ud589\ub839 \uc81c42\uc870\uc7582\uc5d0 \uadfc\uac70\ud574 \ub2e8\ub9d0 \uac00\uaca9\uc744 \uacc4\uc0b0\ud558\uace0 \uc694\uae08\uc81c\uc5d0\uc11c \ud560\uc778\ud574 \uc8fc\ub294 \ubc29\uc2dd\uc785\ub2c8\ub2e4.",
        "money": "\ubd80\ubaa8\ub2d8\uc6a9 \uc911\uc800\uac00 \uc694\uae08\uc81c 3\ub9cc \uc6d0\uc5d0\uc11c 5\ub9cc \uc6d0\ub300\ub294 \uacf5\uc2dc\uc9c0\uc6d0\uae08\uc774 \uac70\uc758 \ud56d\uc0c1 \uc720\ub9ac\ud569\ub2c8\ub2e4.",
        "product": "\uc544\uc774\ud3f0 18 \ud504\ub85c\uc640 \uac24\ub7ed\uc2dc S26 \uc6b8\ud2b8\ub77c\ub97c \ube44\uad50\ud569\ub2c8\ub2e4.",
    }
    expected = {
        "law": "\uc2dc\ud589\ub839 \uc81c42\uc870\uc7582\uc5d0",
        "money": "5\ub9cc \uc6d0\ub300\ub294",
        "product": "\uc544\uc774\ud3f0 18 \ud504\ub85c",
    }
    for name, sample in samples.items():
        chunks = module.split_tts_caption(sample)
        errors = module.validate_section_lockstep(name, {"tts": sample, "caption_chunks": chunks, "display_chunks": chunks}, lambda value: len(re.sub(r"\s+", "", value)))
        if errors:
            raise RuntimeError(f"self-test failed: {name}: {errors}")
        if not any(expected[name] in chunk for chunk in chunks):
            raise RuntimeError(f"self-test split protected bundle: {name}: {chunks}")
        print(f"[test] {name}: {' | '.join(chunks)}")


def typecheck() -> None:
    if os.environ.get("PHONESPOT_SKIP_TSC") == "1":
        print("[skip] TypeScript check disabled for isolated fixture")
        return
    result = subprocess.run(["cmd", "/c", "npx.cmd", "tsc", "--noEmit"], cwd=SHORTS)
    if result.returncode != 0:
        raise RuntimeError("TypeScript check failed")


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Korean Caption Compiler V2")
    print("============================================================")
    for required in (LOCKSTEP, CHUNK_UTIL, RUNNER):
        if not required.exists():
            raise RuntimeError(f"required file missing: {required}")
    patch_lockstep()
    patch_chunk_util()
    if VALIDATOR.exists():
        backup(VALIDATOR)
    write(VALIDATOR, VALIDATOR_V2)
    patch_runner()
    py_compile.compile(str(LOCKSTEP), doraise=True)
    py_compile.compile(str(VALIDATOR), doraise=True)
    run_self_test()
    typecheck()
    append_once(
        MEMORY,
        "## 37. Korean caption compiler V2",
        """## 37. Korean caption compiler V2
- Screen captions keep a fixed 72px Pretendard type size.
- Python splitting protects Korean semantic bundles: currency units, legal article references, and model names.
- Remotion line layout uses real browser font measurements instead of raw character counts.
- The runner blocks renders when protected Korean bundles are split.
- Keep V1 backups until 002, 004, 005, and 006 comparison renders are approved.""",
    )
    append_once(
        PATCH_LOG,
        "## Korean caption compiler V2",
        f"""## Korean caption compiler V2
- Applied: {STAMP}
- Experiment: semantic Korean bundles + Pretendard pixel measurements + fixed 72px captions.
- Rollback: RUN_ROLLBACK_CODEX_KOREAN_CAPTION_COMPILER_V2.bat
""",
    )
    print("[OK] Korean caption compiler V2 installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
