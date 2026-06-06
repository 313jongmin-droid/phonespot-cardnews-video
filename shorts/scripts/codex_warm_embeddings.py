# -*- coding: utf-8 -*-
"""
임베딩 캐시 사전계산(워밍).

목적: 버튼2(제안)·렌더가 '처음' 실행될 때 라이브러리 전체를 임베딩하느라 기다리는 일을
      없앤다. 백그라운드에서 미리 인덱스를 만들어 디스크 캐시에 채워두면, 이후 호출은
      캐시를 읽어 즉시 끝난다(바뀐 그림만 재계산).

안전: 모델이 없으면 아무것도 안 한다(폴백). 실패해도 조용히 종료(파이프라인 영향 없음).
사용: python scripts/codex_warm_embeddings.py
"""
from __future__ import annotations

import sys


def main() -> int:
    # 텍스트(개념) 인덱스
    try:
        import codex_illust_embed as ce
        if ce.available():
            idx = ce.build_index(available_only=True)
            print(f"[warm] text concept index: {len(idx)}")
        else:
            print("[warm] text embedding unavailable - skip")
    except Exception as exc:  # noqa: BLE001
        print(f"[warm] text index skipped ({exc})")

    # 이미지(그림 내용) 지문 인덱스
    try:
        import codex_image_embed as ie
        if ie.available():
            idx = ie.library_image_index()
            print(f"[warm] image fingerprint index: {len(idx)}")
        else:
            print("[warm] image embedding unavailable - skip")
    except Exception as exc:  # noqa: BLE001
        print(f"[warm] image index skipped ({exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
