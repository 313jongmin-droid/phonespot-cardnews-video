# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

from codex_illustration_db import record_usage_snapshot


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"


def get_section(data: dict, name: str) -> dict | None:
    if name == "hook":
        return data.get("hook")
    if name == "cta":
        return data.get("cta")
    if name.startswith("fact_"):
        try:
            idx = int(name.split("_", 1)[1]) - 1
        except ValueError:
            return None
        facts = data.get("facts", []) or []
        if 0 <= idx < len(facts):
            return facts[idx]
    return None


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_apply_uploaded_illustrations.py <slug>")
        return 2
    slug = sys.argv[1]
    output_dir = CARDNEWS / "output" / slug
    script_path = output_dir / "shorts_script.json"
    requests_path = output_dir / "codex_illustration_requests.json"
    if not script_path.exists() or not requests_path.exists():
        return 0

    data = json.loads(script_path.read_text(encoding="utf-8"))
    payload = json.loads(requests_path.read_text(encoding="utf-8"))
    if data.get("_codex_manual_visuals"):
        print("[illustration_apply] manual visuals: skip")
        return 0

    applied = []
    for item in payload.get("requests", []):
        variant = item.get("variant")
        section_name = item.get("section")
        chunk_idx = int(item.get("chunk_index", 0))
        if not variant or not (ILLUST_DIR / f"{variant}.png").exists():
            continue
        section = get_section(data, section_name)
        if not section:
            continue
        visuals = [dict(v) for v in section.get("chunk_visuals", []) or [] if isinstance(v, dict)]
        if not visuals or not (0 <= chunk_idx < len(visuals)):
            continue
        current = visuals[chunk_idx]
        if current.get("type") == "logo":
            continue
        visuals[chunk_idx] = {"type": "illust", "value": variant}
        section["chunk_visuals"] = visuals
        item["status"] = "applied"
        applied.append({"section": section_name, "chunk": chunk_idx + 1, "variant": variant})

    if applied:
        data["_codex_uploaded_illustrations"] = applied
        script_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        requests_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        record_usage_snapshot(data, slug, source="uploaded_illustrations")
        print(f"[illustration_apply] applied: {len(applied)}")
        for item in applied:
            print(f"  - {item['section']} chunk {item['chunk']}: illust:{item['variant']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
