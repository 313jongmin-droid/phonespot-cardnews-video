# -*- coding: utf-8 -*-
"""Suggest reusable GPT Plus illustrations when visual mapping is weak.

Clean V3 policy:
- Recommend only reusable editorial illustrations, not one-off article art.
- Suggest at most three new images per video.
- If weak mapping exists, do not stop at warnings; create prompt candidates
  whenever a reusable concept can cover the gap.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from codex_illustration_db import ensure_db, load_db, mark_requests, semantic_score, variant_tags, write_report


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
DESK = ROOT / "CODEX_VIDEO_DESK"
CARDNEWS = ROOT / "cardnews"
ILLUST_DIRS = [
    DESK / "ILLUSTRATION_DROP",
    SHORTS / "public" / "assets" / "illustrations",
]
MAX_REQUESTS = 3

STYLE = """한국 휴대폰·IT 뉴스 쇼츠용 고품질 에디토리얼 일러스트.
본문의 핵심 의미를 한눈에 이해할 수 있게 표현하되, 한 기사에서만 쓸 수 있는 세부 묘사는 피하세요.
특정 브랜드 로고, 제품 모델명, 날짜, 가격, 인물 이름, 매장 이름, 워터마크는 넣지 마세요.
단순 아이콘 하나가 아니라 중심 오브젝트와 1~2개의 보조 요소를 활용해 완성도 있게 구성하세요.
오렌지(#F74B0B), 검정, 흰색을 중심으로 사용하고 밝은 살구색(#FFF1EA) 배경을 적용하세요.
깔끔한 외곽선, 자연스러운 깊이감, 충분한 디테일을 갖춘 현대적인 에디토리얼 스타일.
화면 비율 4:3, 해상도 1024x768 PNG."""


RULES = [
    {
        "variant": "call_recording_notice",
        "keywords": ["통화 녹음", "녹음", "고지", "멘트", "양쪽 통화자", "상대방", "통화자"],
        "reason": "통화 녹음 기능, 고지 멘트, 상대방 알림을 설명하는 기사에 반복 활용할 수 있습니다.",
        "concept": "스마트폰 통화 화면을 중심으로, 양쪽 통화자에게 동시에 안내 알림이 전달되는 장면. 작은 음성 파형, 알림 말풍선, 녹음 표시를 보조 요소로 사용하되 실제 전화번호나 이름은 넣지 않기.",
    },
    {
        "variant": "recording_archive",
        "keywords": ["녹음본", "메모 앱", "전화 기록", "저장", "기록", "파일"],
        "reason": "녹음 파일 저장, 통화 기록, 메모 앱 보관 같은 기능 설명에 범용적으로 쓸 수 있습니다.",
        "concept": "스마트폰에서 생성된 오디오 파일 카드가 메모장과 통화 기록 보관함으로 정리되어 저장되는 장면. 폴더, 음성 파형, 체크 표시를 활용해 안전하게 보관되는 느낌을 표현.",
    },
    {
        "variant": "device_os_requirement",
        "keywords": ["iPhone XS", "이후", "모델", "버전", "iOS", "이상", "지원", "사용 가능"],
        "reason": "지원 기기, OS 버전 조건, 업데이트 호환성 안내에 재사용할 수 있습니다.",
        "concept": "여러 스마트폰 실루엣 앞에 호환성 체크리스트가 놓인 장면. 일부 기기는 체크, 일부 기기는 흐린 회색 처리로 지원 여부가 나뉘는 느낌을 표현하되 실제 모델명과 숫자는 넣지 않기.",
    },
    {
        "variant": "phone_settings_toggle",
        "keywords": ["설정", "메뉴", "자동 녹음", "켤 수", "켜", "끄", "전화 앱"],
        "reason": "전화 앱 설정, 기능 켜기/끄기, 자동화 옵션 설명에 범용적으로 활용할 수 있습니다.",
        "concept": "스마트폰 설정 화면을 추상화해 큰 토글 스위치가 켜지는 장면. 통화 아이콘, 작은 설정 톱니바퀴, 체크 표시를 보조 요소로 배치하되 실제 UI 문구는 넣지 않기.",
    },
    {
        "variant": "call_filter_rules",
        "keywords": ["모든 통화", "국제 전화", "제외", "특정 번호", "번호만", "조건", "필터"],
        "reason": "특정 번호, 예외 조건, 통화 필터 설정 안내에 반복 활용할 수 있습니다.",
        "concept": "전화번호 목록이 필터 깔때기를 통과하며 선택된 통화만 체크되는 장면. 일부 항목은 제외 표시, 일부 항목은 체크 표시로 나뉘는 구성을 사용하되 실제 번호는 넣지 않기.",
    },
    {
        "variant": "launch_event",
        "keywords": ["언팩", "키노트", "행사", "공개", "발표", "런던", "현지 시각"],
        "reason": "제품 공개 행사, 언팩, 키노트 뉴스에 반복 사용할 수 있습니다.",
        "concept": "밝은 무대 또는 발표 공간을 상징하는 장면. 중앙에는 스마트폰 실루엣과 발표 스포트라이트, 주변에는 작은 일정 카드와 관객석을 암시하는 단순 요소. 특정 브랜드 로고와 실제 장소명은 넣지 않기.",
    },
    {
        "variant": "release_calendar",
        "keywords": ["출시", "정식 출시", "사전예약", "예약", "일정", "초", "말", "D-", "날짜"],
        "reason": "출시일, 사전예약, 업데이트 일정, 행사 D-day 콘텐츠에 범용적으로 쓸 수 있습니다.",
        "concept": "스마트폰 옆에 놓인 깔끔한 캘린더와 체크 표시, 작은 알림 벨, 진행 표시를 조합한 일정 안내 장면. 숫자와 날짜를 직접 쓰지 않고 출시·예약 일정의 느낌만 표현.",
    },
    {
        "variant": "display_ratio_change",
        "keywords": ["화면 비율", "와이드", "넓어", "디스플레이", "화면이 더", "모형", "외부 화면"],
        "reason": "화면 비율 변경, 디스플레이 확장, 폴더블 변화 뉴스에 재사용할 수 있습니다.",
        "concept": "두 개의 스마트폰 화면 실루엣이 나란히 있고, 한쪽 화면이 부드럽게 더 넓게 확장되는 장면. 확장 안내선과 화면 프레임을 사용해 비율 변화를 표현하되 모델명과 숫자는 넣지 않기.",
    },
    {
        "variant": "cover_screen_widgets",
        "keywords": ["외부 디스플레이", "커버 화면", "위젯", "앱 호환", "닫은 상태", "알림"],
        "reason": "폴더블 커버 화면, 위젯, 잠금화면, 앱 호환성 주제에 재사용할 수 있습니다.",
        "concept": "접힌 형태의 스마트폰 외부 화면에 작은 위젯 카드들이 정돈되어 떠 있는 장면. 날씨, 알림, 음악 같은 범용 카드 형태만 사용하고 실제 앱 로고와 텍스트는 넣지 않기.",
    },
    {
        "variant": "health_sensor_watch",
        "keywords": ["워치", "건강", "측정", "센서", "심박", "헬스"],
        "reason": "스마트워치 건강 측정, 센서 개선, 웨어러블 헬스 뉴스에 반복 사용할 수 있습니다.",
        "concept": "둥근 스마트워치 실루엣과 심박 파형, 작은 센서 점, 건강 체크 표시를 조합한 웨어러블 건강 측정 장면. 특정 브랜드 로고와 실제 수치는 넣지 않기.",
    },
    {
        "variant": "device_data_transfer",
        "keywords": ["데이터", "사진", "동영상", "연락처", "메시지", "옮기", "이전", "Smart Switch", "iCloud", "USB 케이블"],
        "reason": "신규 기기 교체, 데이터 이전, 스마트 스위치, 클라우드 이전 가이드에 범용적으로 활용할 수 있습니다.",
        "concept": "두 대의 스마트폰 사이로 사진, 연락처, 메시지를 상징하는 작은 카드가 안전하게 이동하는 장면. 연결 케이블과 클라우드를 보조 요소로 표현.",
    },
    {
        "variant": "security_feature_lock",
        "keywords": ["보안", "잠금", "보호", "개인정보", "차단", "도난", "분실"],
        "reason": "보안 기능, 개인정보 보호, 잠금 설정, 도난 방지 안내에 재사용할 수 있습니다.",
        "concept": "스마트폰 화면 위에 보호 방패와 자물쇠가 겹쳐진 장면. 주변에는 위험 신호가 막히는 선과 체크 표시를 배치해 안전 기능을 표현하되 실제 앱 화면은 넣지 않기.",
    },
    {
        "variant": "settings_steps",
        "keywords": ["사용 방법", "단순", "단계", "방법", "들어가면", "선택", "버튼"],
        "reason": "기능 사용 방법, 설정 단계, 따라하기형 팁 영상에 범용적으로 활용할 수 있습니다.",
        "concept": "스마트폰 설정 화면 옆에 1단계, 2단계, 3단계를 상징하는 카드가 계단처럼 이어지는 장면. 실제 숫자나 문구 대신 점, 체크, 화살표로 간단한 절차를 표현.",
    },
]


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def available_illustrations() -> set[str]:
    found: set[str] = set()
    for root in ILLUST_DIRS:
        if root.exists():
            found.update(path.stem for path in root.glob("*.png"))
    return found


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def chunk_source(section: dict) -> list[str]:
    chunks = section.get("caption_chunks", []) or []
    displays = section.get("display_chunks", []) or []
    if len(displays) > len(chunks):
        return [clean(x) for x in displays]
    return [clean(x) for x in chunks]


def chunk_text(section: dict, idx: int) -> str:
    chunks = section.get("caption_chunks", []) or []
    displays = section.get("display_chunks", []) or []
    parts = [
        chunks[idx] if idx < len(chunks) else "",
        displays[idx] if idx < len(displays) else "",
        section.get("topic", ""),
        section.get("tts", ""),
    ]
    return clean(" ".join(parts))


def section_text(section: dict) -> str:
    parts = [section.get("topic", ""), section.get("tts", "")]
    parts.extend(section.get("caption_chunks", []) or [])
    parts.extend(section.get("display_chunks", []) or [])
    return clean(" ".join(parts))


def visual_at(section: dict, idx: int) -> dict:
    visuals = section.get("chunk_visuals", []) or []
    if 0 <= idx < len(visuals) and isinstance(visuals[idx], dict):
        return visuals[idx]
    return {}


def rule_matches(rule: dict, text: str) -> bool:
    return any(keyword.lower() in text.lower() for keyword in rule["keywords"])


def best_chunk_for_rule(section: dict, rule: dict) -> int:
    chunks = chunk_source(section)
    if not chunks:
        return 0
    scored = []
    for idx in range(len(chunks)):
        text = chunk_text(section, idx).lower()
        score = sum(1 for keyword in rule["keywords"] if keyword.lower() in text)
        scored.append((score, idx))
    scored.sort(reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else 0


def quality_gap(db: dict, section: dict, idx: int) -> tuple[int, str]:
    visual = visual_at(section, idx)
    if visual.get("type") != "illust":
        return 0, f"current visual is {visual.get('type', 'missing')}; reusable illustration can improve this slot"
    variant = str(visual.get("value") or "")
    entry = (db.get("illustrations", {}) or {}).get(variant, {})
    score = semantic_score(chunk_text(section, idx), entry)
    return score, f"current illust:{variant} semantic score={score}; replace weak fallback with a reusable semantic asset"


def semantic_gap_rows(db: dict, data: dict) -> list[dict]:
    rows = []
    for section_name, section in sections(data):
        if section_name == "cta":
            continue
        chunks = chunk_source(section)
        visuals = section.get("chunk_visuals", []) or []
        for idx, visual in enumerate(visuals):
            if idx >= len(chunks):
                continue
            if not isinstance(visual, dict):
                continue
            if visual.get("type") == "image":
                continue
            variant = str(visual.get("value") or "")
            if visual.get("type") != "illust":
                score = 0
            else:
                entry = (db.get("illustrations", {}) or {}).get(variant, {})
                score = semantic_score(chunk_text(section, idx), entry)
            if score <= 0:
                rows.append({
                    "section": section_name,
                    "chunk_index": idx,
                    "variant": variant or visual.get("type", "missing"),
                    "text": chunks[idx],
                })
    return rows


def make_request(rule: dict, section_name: str, chunk_idx: int, gap: str) -> dict:
    variant = rule["variant"]
    return {
        "variant": variant,
        "filename": f"{variant}.png",
        "section": section_name,
        "chunk_index": chunk_idx,
        "reason": rule["reason"],
        "quality_gap": gap,
        "tags": variant_tags(variant),
        "prompt": STYLE + "\n\n핵심 콘셉트:\n" + rule["concept"],
        "status": "requested",
    }


def request_candidates(db: dict, data: dict, existing: set[str]) -> tuple[list[dict], list[dict]]:
    requests: list[dict] = []
    seen: set[str] = set()
    reserved_slots: set[tuple[str, int]] = set()

    for section_name, section in sections(data):
        if section_name == "cta":
            continue
        text = section_text(section)
        for rule in RULES:
            variant = rule["variant"]
            if variant in existing or variant in seen or not rule_matches(rule, text):
                continue
            chunk_idx = best_chunk_for_rule(section, rule)
            if section_name == "hook" and chunk_idx == 0 and len(chunk_source(section)) > 1:
                chunk_idx = 1
            slot = (section_name, chunk_idx)
            if slot in reserved_slots:
                continue
            score, gap = quality_gap(db, section, chunk_idx)
            if score >= 12:
                continue
            requests.append(make_request(rule, section_name, chunk_idx, gap))
            seen.add(variant)
            reserved_slots.add(slot)
            if len(requests) >= MAX_REQUESTS:
                break
        if len(requests) >= MAX_REQUESTS:
            break

    uncovered = semantic_gap_rows(db, data)
    if len(requests) < MAX_REQUESTS:
        for gap in uncovered:
            text = clean(gap.get("text", ""))
            for rule in RULES:
                variant = rule["variant"]
                if variant in existing or variant in seen or not rule_matches(rule, text):
                    continue
                section_name = str(gap.get("section") or "")
                chunk_idx = int(gap.get("chunk_index") or 0)
                requests.append(
                    make_request(
                        rule,
                        section_name,
                        chunk_idx,
                        f"weak fallback `{gap.get('variant')}` for: {text}",
                    )
                )
                seen.add(variant)
                if len(requests) >= MAX_REQUESTS:
                    break
            if len(requests) >= MAX_REQUESTS:
                break

    return requests, uncovered


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_illustration_scout.py <slug>")
        return 2
    slug = sys.argv[1]
    ensure_db()
    output_dir = CARDNEWS / "output" / slug
    script_path = output_dir / "shorts_script.json"
    if not script_path.exists():
        print(f"[illustration_scout_v3] skip, missing: {script_path}")
        return 0

    data = json.loads(script_path.read_text(encoding="utf-8-sig"))
    db = load_db()
    existing = available_illustrations()
    requests, uncovered_gaps = request_candidates(db, data, existing)

    payload = {
        "version": 3,
        "slug": slug,
        "policy": "suggest reusable GPT Plus assets when existing semantic coverage is weak; max three requests per video",
        "upload_dir": str(DESK / "ILLUSTRATION_DROP"),
        "requests": requests,
        "uncovered_gaps": uncovered_gaps,
    }
    json_path = output_dir / "codex_illustration_requests.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Codex Illustration Requests V3: {slug}",
        "",
        "현재 시각 매핑의 문맥 품질을 검사해, 다른 기사에서도 재사용할 수 있는 일러스트만 추천합니다.",
        "영상 한 편당 최대 3개만 제안합니다.",
        "",
    ]
    if not requests:
        if uncovered_gaps:
            lines.append("문맥 적합도가 낮은 폴백 일러스트가 남아 있지만, 이미 같은 범용 일러스트가 라이브러리에 있거나 이번 기사에서 새로 만들 만큼 반복 가치가 낮습니다.")
        else:
            lines.append("추가로 만들 범용 일러스트가 없습니다. 바로 렌더링해도 됩니다.")
        lines.append("")

    for idx, item in enumerate(requests, 1):
        lines.extend([
            f"## {idx}. `{item['filename']}`",
            "",
            f"- 적용 위치: `{item['section']}` 청크 {item['chunk_index'] + 1}",
            f"- 추천 이유: {item['reason']}",
            f"- 교체 근거: {item['quality_gap']}",
            "",
            "```text",
            item["prompt"],
            "```",
            "",
        ])

    if uncovered_gaps:
        lines.extend(["", "## 남아 있는 문맥 커버리지 경고", ""])
        for gap in uncovered_gaps[:8]:
            lines.append(f"- `{gap['section']}` 청크 {gap['chunk_index'] + 1}: `{gap['variant']}` -> {gap['text']}")
        lines.append("- 위 항목은 렌더링을 막지 않지만, 반복되면 범용 일러스트 규칙을 추가해야 합니다.")

    md_path = output_dir / "codex_illustration_requests.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mark_requests(slug, requests)
    write_report()
    print(f"[illustration_scout_v3] report: {md_path}")
    print(f"[illustration_scout_v3] requests: {len(requests)}, uncovered_gaps: {len(uncovered_gaps)}")
    for item in requests:
        print(f"  - {item['filename']} -> {item['section']} chunk {item['chunk_index'] + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
