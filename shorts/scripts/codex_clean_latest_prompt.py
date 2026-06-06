# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
DESK = ROOT / "CODEX_VIDEO_DESK"


BASE_STYLE = """한국 휴대폰/IT 쇼츠 뉴스용 재사용 일러스트를 만들어주세요.
한 기사에만 묶이는 세부 묘사는 피하고, 같은 주제의 다른 뉴스에서도 다시 쓸 수 있게 범용적으로 표현해주세요.
일러스트 자체는 완성도 있게 그려주세요. 단순 낙서나 너무 추상적인 도형만으로 처리하지 마세요.
브랜드 로고, 실제 제품명, 날짜, 가격, 매장명, 워터마크, 긴 문장은 넣지 마세요.
오렌지 #F74B0B, 검정, 흰색, 라이트 살구색 배경을 기본으로 사용해주세요.
화면 비율은 4:3, 1024x768 PNG입니다."""


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
        parts = [head + " 개념을 휴대폰/IT 뉴스에서 반복 사용 가능한 범용 일러스트로 표현."]
        if keywords:
            parts.append("핵심 요소: " + ", ".join(keywords) + ".")
        if source:
            parts.append("아래 문장의 의미를 담되 특정 브랜드/제품명/숫자/날짜는 빼고 일반화하세요: \"" + source + "\"")
        return " ".join(parts)
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
    lines = []
    lines.append(f"# Codex GPT Illustration Prompt: {data.get('slug') or slug or 'latest'}")
    lines.append("")
    lines.append("아래 순서대로 GPT Plus에서 이미지를 생성한 뒤, 그대로 다운로드하세요.")
    lines.append("다운로드가 끝나면 `02_IMPORT_DOWNLOADS_AND_RENDER.bat` 또는 웹 패널의 `2. 가져오고 렌더`를 실행하세요.")
    lines.append("")
    if requests:
        for idx, item in enumerate(requests, 1):
            variant = item.get("variant") or f"illustration_{idx}"
            filename = item.get("filename") or f"{variant}.png"
            section = item.get("section", "")
            chunk_index = int(item.get("chunk_index", 0)) + 1
            badge = " (자동 발굴)" if item.get("source") == "concept_scout" else ""
            lines.append(f"## {idx}. {filename}{badge}")
            lines.append("")
            lines.append(f"- 적용 위치: `{section}` 청크 {chunk_index}")
            lines.append(f"- 재사용 태그: {', '.join(item.get('tags', []) or [])}")
            lines.append("")
            lines.append("```text")
            lines.append(BASE_STYLE)
            lines.append("")
            lines.append("핵심 콘셉트:")
            lines.append(concept_for_item(item, variant))
            lines.append("```")
            lines.append("")
    else:
        lines.append("## 신규 GPT 이미지 요청 없음")
