# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
DESK = ROOT / "CODEX_VIDEO_DESK"


BASE_STYLE = """재사용 가능한 한국 휴대폰/IT 뉴스 쇼츠용 에디토리얼 일러스트(완성도 있게, 낙서·단순도형 금지). 한 기사 전용 세부(모델명·날짜·가격·수치) 없이 범용 개념으로 표현.
브랜드 로고·제품명·매장명·워터마크·긴 문장 금지. 색: 오렌지 #F74B0B, 검정, 흰색, 라이트 살구색 배경. 비율 4:3, 1024x768 PNG."""


CONCEPTS = {
    "device_data_transfer": "두 스마트폰 사이로 사진, 연락처, 메시지 카드가 안전하게 이동하는 장면. 케이블과 클라우드를 보조 요소로만 표현.",
    "chat_backup_restore": "채팅 말풍선이 구름 백업을 거쳐 다른 스마트폰으로 복원되는 흐름. 특정 메신저 로고는 사용하지 않기.",
    "secure_app_reregistration": "스마트폰 화면 안에서 인증 카드와 결제 카드가 순서대로 다시 등록되는 장면. 체크 표시로 안전한 재설정 흐름 표현.",
    "telecom_discount_compare": "요금 할인과 지원금 선택지를 비교하는 범용 상담 카드. 두 개의 카드와 저울/비교 화살표로 표현.",
    "plan_price_tier_compare": "낮은 요금제와 높은 요금제를 비교하는 범용 가격 단계 일러스트. 막대 2~3개와 스마트폰 아이콘 사용.",
    "smishing_fake_link": "스마트폰 메시지 안의 수상한 링크와 경고 표시. 특정 서비스명 없이 보안 주의 느낌.",
    "impersonation_call": "가짜 상담 전화나 사칭 전화를 받는 장면. 스마트폰 통화 아이콘과 경고 삼각형.",
    "emergency_account_freeze": "계좌 보호나 지급정지를 상징하는 잠금된 지갑/계좌 카드. 은행 로고 없이 표현.",
    "fake_government_page": "공식 사이트처럼 보이지만 의심스러운 웹페이지를 확인하는 장면. 돋보기와 경고 표시.",
    "official_site_check": "공식 사이트 여부를 확인하는 체크리스트와 자물쇠. 범용 보안 확인 일러스트.",
    "personal_data_leak": "개인정보 카드가 밖으로 새어나가는 위험을 표현. 이름/번호 같은 실제 텍스트는 사용하지 않기.",
}


def concept_for(variant: str) -> str:
    return CONCEPTS.get(variant, f"{variant.replace('_', ' ')} 개념을 휴대폰/IT 뉴스에서 반복 사용 가능한 범용 일러스트로 표현.")


def concept_for_item(item: dict, variant: str) -> str:
    """요청 항목 기준 핵심 콘셉트. 알려진 variant 는 사전 사용,
    개념 스카우트(cpt_*)는 라벨/키워드로 의미 있는 문구를 만든다."""
    if variant in CONCEPTS:
        return CONCEPTS[variant]
    label = str(item.get("concept_label") or "").strip()
    keywords = [str(k) for k in (item.get("keywords") or []) if str(k).strip()]
    source = str(item.get("source_text") or "").strip()
    if source or label or keywords:
        head = label or variant.replace("_", " ")
        detail = []
        if keywords:
            detail.append("핵심 요소: " + ", ".join(keywords[:4]))
        if source:
            detail.append("맥락: \"" + source + "\"")
        return head + (" — " + " / ".join(detail) if detail else "")
    return concept_for(variant)


def main() -> int:
    slug = sys.argv[1] if len(sys.argv) > 1 else ""
    path = DESK / "LATEST_PROMPT.json"
    if not path.exists():
        print("[clean_prompt] no LATEST_PROMPT.json")
        return 0
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if slug and not data.get("slug"):
        data["slug"] = slug
    requests = data.get("requests", []) or []
    gaps = data.get("uncovered_gaps", []) or []
    n = len(requests)
    lines = []
    lines.append(f"# 이미지 생성 프롬프트: {data.get('slug') or slug or 'latest'}")
    lines.append("")
    lines.append(f"아래 {n}개를 각각 별도 이미지로 생성. 격자·콜라주·분할 화면 금지(한 이미지에 한 개념만).")
    lines.append("1 -> 2 -> ... 순서대로 한 장씩 만들어 그대로 다운로드한 뒤, 웹 패널 `2. 가져오고 렌더`를 실행하세요.")
    lines.append("")
    lines.append("## 공통 스타일")
    lines.append(BASE_STYLE)
    lines.append("")
    if requests:
        lines.append("## 이미지 목록")
        lines.append("")
        for idx2, item in enumerate(requests, 1):
            variant = item.get("variant") or f"illustration_{idx2}"
            filename = item.get("filename") or f"{variant}.png"
            badge = " (자동 발굴)" if item.get("source") == "concept_scout" else ""
            lines.append(f"{idx2}. `{filename}`{badge}")
            lines.append(f"   {concept_for_item(item, variant)}")
            lines.append("")
    else:
        lines.append("신규로 만들 GPT 이미지 요청이 없습니다. 바로 렌더링해도 됩니다.")

    if gaps:
        lines.append("")
        lines.append(f"(참고: 문맥 커버리지 경고 {len(gaps)}건 — 렌더는 막지 않음)")

    out_md = DESK / "LATEST_PROMPT.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[clean_prompt] wrote concise prompt: {out_md} ({n} requests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
