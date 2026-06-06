# -*- coding: utf-8 -*-
"""
의미 임베딩 매칭 '미리보기' (읽기 전용)

라이브 매처(codex_semantic_visual_match.py)는 전혀 건드리지 않고,
한 슬러그의 각 청크에 대해 [현재 비주얼] vs [임베딩 의미매칭 1순위]를 비교만 출력한다.
임베딩이 실제로 더 맞는 그림을 고르는지 눈으로 확인하는 용도.

사용:
    python scripts/codex_illust_match_preview.py <slug>

모델이 없으면 자동으로 lexical 폴백으로 동작하며, 그 경우 "임베딩 미사용"이라고 표시한다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import codex_illust_embed as ce
import codex_illustration_db as db_mod
import codex_semantic_visual_match as svm  # 컨텍스트 산출 로직 재사용(부작용 없음)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/codex_illust_match_preview.py <slug>")
        return 2
    slug = sys.argv[1].strip()
    path = svm.CARD_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        print(f"[preview] missing: {path}")
        return 1

    data = svm.read_json(path)
    db = db_mod.load_db()
    using = ce.available()
    print(f"[preview] slug={slug}")
    print(f"[preview] 임베딩 모델 사용: {using}  ({'의미매칭' if using else 'lexical 폴백 — SETUP_EMBED.bat로 설치 권장'})")
    print("-" * 72)

    changed = 0
    total = 0
    for section_name, section in svm.section_items(data):
        if section_name == "cta":
            continue
        chunks = svm.section_chunks(section)
        visuals = section.get("chunk_visuals", []) or []
        for idx, _ in enumerate(chunks):
            if idx >= len(visuals) or not isinstance(visuals[idx], dict):
                continue
            current = visuals[idx]
            if current.get("type") in {"image", "logo", "mascot"}:
                continue  # 소스 이미지/로고/마스코트는 비교 대상 아님
            context = svm.context_for(section, idx)
            ranked = ce.rank(context, available_only=True, top_k=1, db=db)
            best = ranked[0] if ranked else ("", 0.0)
            cur_val = str(current.get("value") or "")
            mark = "  " if best[0] == cur_val else "->"
            total += 1
            if best[0] != cur_val:
                changed += 1
            text = chunks[idx][:24]
            print(f"{section_name} C{idx+1} [{text}]")
            print(f"   현재 : illust:{cur_val}")
            print(f"   제안 {mark} illust:{best[0]}  (score {best[1]:.3f})")

    print("-" * 72)
    print(f"[preview] 일러스트 슬롯 {total}개 중 {changed}개가 임베딩 제안과 다릅니다.")
    print("[preview] 이 도구는 미리보기만 합니다. 실제 적용은 다음 단계(매처 교체)에서 진행합니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
