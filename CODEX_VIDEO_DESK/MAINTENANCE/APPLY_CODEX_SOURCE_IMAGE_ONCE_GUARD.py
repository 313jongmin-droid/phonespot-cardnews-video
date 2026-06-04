# -*- coding: utf-8 -*-
"""Install a global once-per-video contract for non-illustration image visuals."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
SHORTS = ROOT / "shorts"
ENHANCER = SHORTS / "scripts" / "codex_enhance_script.py"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

FUNCTION_BLOCK = '''def enforce_unique_source_images(data: dict, slug: str) -> bool:
    """Use each non-illustration image at most once across the whole video."""
    source_images = list_source_images(slug)
    illustrations = list_illustrations()
    sections = section_list(data)
    used_images = set()
    used_visuals = {
        visual_key(visual)
        for _, section in sections
        for visual in (section.get("chunk_visuals", []) or [])
        if isinstance(visual, dict) and visual.get("type") != "image"
    }
    replacements = []

    for section_name, section in sections:
        visuals = [dict(v) for v in section.get("chunk_visuals", []) or [] if isinstance(v, dict)]
        if not visuals:
            continue
        for idx, visual in enumerate(visuals):
            if visual.get("type") != "image":
                continue
            value = str(visual.get("value") or "")
            if value and value not in used_images:
                used_images.add(value)
                continue

            replacement = None
            context = _section_visual_text(section, idx)
            for variant in _illustration_candidates(context, section_name):
                key = f"illust:{variant}"
                if variant in illustrations and key not in used_visuals:
                    replacement = {"type": "illust", "value": variant}
                    break

            if replacement is None:
                for image in source_images:
                    if image not in used_images:
                        replacement = {"type": "image", "value": image}
                        break

            if replacement is None:
                for variant in illustrations:
                    key = f"illust:{variant}"
                    if key not in used_visuals:
                        replacement = {"type": "illust", "value": variant}
                        break

            if replacement is None:
                continue

            visuals[idx] = replacement
            if replacement.get("type") == "image":
                used_images.add(str(replacement.get("value") or ""))
            else:
                used_visuals.add(visual_key(replacement))
            replacements.append(
                {
                    "section": section_name,
                    "chunk": idx + 1,
                    "from": visual,
                    "to": replacement,
                }
            )
        section["chunk_visuals"] = visuals

    if replacements:
        data["_codex_unique_source_images"] = {
            "version": 1,
            "policy": "non-illustration image visuals are used at most once across one video",
            "replacements": replacements,
        }
        print(f"[codex_enhance] unique source images: {len(replacements)} replaced")
    return bool(replacements)


def validate_unique_source_images(data: dict) -> None:
    seen = {}
    errors = []
    for section_name, section in section_list(data):
        for idx, visual in enumerate(section.get("chunk_visuals", []) or [], 1):
            if not isinstance(visual, dict) or visual.get("type") != "image":
                continue
            value = str(visual.get("value") or "")
            if not value:
                errors.append(f"{section_name}.chunk_visuals[{idx}]: empty image value")
                continue
            if value in seen:
                errors.append(
                    f"{section_name}.chunk_visuals[{idx}]: duplicated image `{value}`; "
                    f"first used at {seen[value]}"
                )
            else:
                seen[value] = f"{section_name}.chunk_visuals[{idx}]"
    if errors:
        raise ValueError("Source image once contract failed\\n- " + "\\n- ".join(errors))


'''


def backup(path: Path) -> Path:
    target = path.with_name(path.name + f".bak_source_image_once_{STAMP}")
    shutil.copy2(path, target)
    print(f"[backup] {target}")
    return target


def append_once(path: Path, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + body.rstrip() + "\n", encoding="utf-8")
    print(f"[note] {path}")


def patch_enhancer() -> None:
    text = ENHANCER.read_text(encoding="utf-8")
    original = text

    if "def enforce_unique_source_images(data: dict, slug: str) -> bool:" not in text:
        anchor = "def ensure_visual_contract(section: dict, slug: str, name: str) -> None:"
        if anchor not in text:
            raise RuntimeError("source image guard function anchor missing")
        text = text.replace(anchor, FUNCTION_BLOCK + anchor, 1)
        print("[patch] global source-image guard functions")

    if "    enforce_unique_source_images(data, slug)\n    enforce_fixed_cta(data)" not in text:
        anchor = "    auto_balance_illustrations(data, slug)\n    enforce_fixed_cta(data)"
        replacement = (
            "    auto_balance_illustrations(data, slug)\n"
            "    enforce_unique_source_images(data, slug)\n"
            "    enforce_fixed_cta(data)"
        )
        if anchor not in text:
            raise RuntimeError("source image guard render anchor missing")
        text = text.replace(anchor, replacement, 1)
        print("[patch] global source-image guard render boundary")

    if "    validate_unique_source_images(data)\n    if errors:" not in text:
        anchor = "    if errors:\n        raise ValueError(\"Korean caption contract failed\\n- \" + \"\\n- \".join(errors))"
        replacement = (
            "    validate_unique_source_images(data)\n"
            "    if errors:\n"
            "        raise ValueError(\"Korean caption contract failed\\n- \" + \"\\n- \".join(errors))"
        )
        if anchor not in text:
            raise RuntimeError("source image guard validation anchor missing")
        text = text.replace(anchor, replacement, 1)
        print("[patch] global source-image validation")

    if text == original:
        print("[skip] source-image once guard already installed")
        return
    backup(ENHANCER)
    ENHANCER.write_text(text, encoding="utf-8")
    print(f"[write] {ENHANCER}")


def main() -> int:
    if not ENHANCER.exists():
        raise RuntimeError("PhoneSpot Codex enhancer not found")
    patch_enhancer()
    py_compile.compile(str(ENHANCER), doraise=True)
    append_once(
        MEMORY,
        "## 26. Global source-image once contract",
        """## 26. Global source-image once contract
- Every non-illustration `image` visual may appear at most once inside one video.
- This is a whole-video contract, not a section-local preference.
- When a duplicate image is found, prefer a contextually relevant unused illustration, then an unused source image, then another unused illustration.
- CTA logo remains separate and fixed.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-01 - Global source-image once contract",
        """## 2026-06-01 - Global source-image once contract
- Added a whole-video duplicate-image guard to Codex Remotion.
- Every non-illustration image is now used at most once per video.
- Duplicate image slots are replaced without changing caption chunks, TTS, or fixed CTA copy.""",
    )
    print("[done] global source-image once guard installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
