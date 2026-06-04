# -*- coding: utf-8 -*-
"""Install a clean UTF-8 reusable illustration scout for Codex Remotion."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
SHORTS = ROOT / "shorts"
SCOUT = SHORTS / "scripts" / "codex_illustration_scout.py"
MEMORY = SHORTS / "codex" / "CODEX_MEMORY.md"
PATCH_LOG = SHORTS / "codex" / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

SCOUT_CODE = r'''# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
SHORTS = ROOT / "shorts"
CARDNEWS = ROOT / "cardnews"
ILLUST_DIR = SHORTS / "public" / "assets" / "illustrations"

STYLE = """한국 휴대폰·IT 뉴스 쇼츠용 고품질 에디토리얼 일러스트.
본문의 핵심 의미를 한눈에 이해할 수 있게 표현하되, 한 기사에서만 쓸 수 있는 세부 묘사는 피하세요.
특정 브랜드 로고, 제품 모델명, 날짜, 가격, 인물 이름, 매장 이름, 워터마크는 넣지 마세요.
단순 아이콘 한 개처럼 성의 없이 그리지 말고, 중심 오브젝트와 1~2개의 보조 요소를 활용해 완성도 있게 구성하세요.
오렌지(#F74B0B), 검정, 흰색을 중심으로 사용하고 밝은 살구색(#FFF1EA) 배경을 적용하세요.
깔끔한 외곽선, 자연스러운 깊이감, 충분한 디테일을 갖춘 현대적인 에디토리얼 스타일.
화면 비율 4:3, 해상도 1024x768 PNG."""

RULES = [
    {
        "variant": "battery_charge_range",
        "keywords": ("20~80", "20에서 80", "과충전", "충전 범위"),
        "reason": "충전 권장 구간을 범용적으로 설명할 때 재사용할 수 있습니다.",
        "concept": "스마트폰 배터리 게이지와 안전 충전 구간. 중간 영역은 오렌지색 안전 범위로 강조하고, 양 끝은 과도한 충전을 경고하는 차분한 구성.",
    },
    {
        "variant": "optimized_charging",
        "keywords": ("최적화 충전", "적응형 보호", "자동 보호", "배터리 보호"),
        "reason": "배터리 보호 기능과 자동 최적화를 설명하는 영상에 반복 활용할 수 있습니다.",
        "concept": "스마트폰 배터리를 보호하는 작은 방패와 체크 표시. 자동으로 충전을 조절하는 흐름을 부드러운 화살표로 표현.",
    },
    {
        "variant": "battery_overheat",
        "keywords": ("고온", "과열", "차량 내 충전", "충전 중 게임"),
        "reason": "고온 환경과 과열 위험을 설명하는 범용 경고 장면입니다.",
        "concept": "열기가 올라오는 스마트폰 배터리와 충전 케이블. 작은 경고 삼각형과 온도 상승선을 활용한 에디토리얼 구성.",
    },
    {
        "variant": "battery_health_check",
        "keywords": ("배터리 건강", "배터리 상태", "교체 시기", "최대 용량"),
        "reason": "배터리 상태 확인과 교체 시기 안내에 재사용할 수 있습니다.",
        "concept": "스마트폰 배터리 상태를 점검하는 장면. 배터리 게이지, 체크리스트, 진단 표시를 균형 있게 배치.",
    },
    {
        "variant": "theft_auto_lock",
        "keywords": ("도난", "강제 탈취", "자동 잠금", "도난 기기 보호"),
        "reason": "도난 감지와 자동 잠금 기능을 설명하는 범용 보안 일러스트입니다.",
        "concept": "움직임을 감지한 스마트폰이 즉시 잠기는 장면. 작은 진동선, 자물쇠, 방패를 활용해 보호 모드 전환을 표현.",
    },
    {
        "variant": "ondevice_ai_chip",
        "keywords": ("온디바이스", "기기 내", "자체 칩", "클라우드를 거치지"),
        "reason": "기기 내부 AI 처리와 개인정보 보호를 설명할 때 활용할 수 있습니다.",
        "concept": "스마트폰 내부에서 빛나는 AI 칩과 데이터 흐름. 외부 서버로 나가지 않고 기기 안에서 처리되는 느낌을 명확하게 표현.",
    },
    {
        "variant": "nfc_open_access",
        "keywords": ("NFC 개방", "상호운용", "비접촉 결제", "경쟁 서비스"),
        "reason": "NFC 개방과 결제 서비스 연결을 설명하는 범용 장면입니다.",
        "concept": "스마트폰 NFC 신호가 여러 결제 단말과 서비스로 연결되는 장면. 중앙 스마트폰과 부드러운 무선 연결선을 활용.",
    },
    {
        "variant": "device_price_rise",
        "keywords": ("가격 인상", "비싸질", "인상 폭", "가격 조정"),
        "reason": "스마트폰 가격 상승 뉴스를 설명할 때 반복 활용할 수 있습니다.",
        "concept": "스마트폰 옆 가격표가 위로 올라가는 장면. 상승 화살표와 동전 몇 개를 보조 요소로 배치하되 실제 가격 숫자는 넣지 않기.",
    },
    {
        "variant": "repair_privacy",
        "keywords": ("수리", "사생활", "개인정보 노출", "사진 숨김", "보안 폴더"),
        "reason": "수리 과정의 개인정보 보호를 설명하는 범용 보안 일러스트입니다.",
        "concept": "수리 중인 스마트폰과 보호 방패. 잠긴 사진 폴더와 작은 공구를 보조 요소로 배치해 개인정보 보호 의미를 표현.",
    },
]


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def sections(data: dict):
    yield "hook", data.get("hook", {})
    for idx, fact in enumerate(data.get("facts", []) or [], 1):
        yield f"fact_{idx}", fact
    yield "cta", data.get("cta", {})


def section_text(section: dict) -> str:
    return clean(
        " ".join(
            [
                section.get("topic", ""),
                " ".join(section.get("caption_chunks", []) or []),
                " ".join(section.get("display_chunks", []) or []),
            ]
        )
    )


def find_chunk(section: dict, keywords: tuple[str, ...]) -> int:
    chunks = section.get("caption_chunks", []) or []
    displays = section.get("display_chunks", []) or []
    for idx in range(max(len(chunks), len(displays))):
        value = clean(
            (chunks[idx] if idx < len(chunks) else "")
            + " "
            + (displays[idx] if idx < len(displays) else "")
        )
        if any(keyword.lower() in value.lower() for keyword in keywords):
            return idx
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/codex_illustration_scout.py <slug>")
        return 2
    slug = sys.argv[1]
    output_dir = CARDNEWS / "output" / slug
    script_path = output_dir / "shorts_script.json"
    if not script_path.exists():
        print(f"[illustration_scout] skip, missing: {script_path}")
        return 0

    data = json.loads(script_path.read_text(encoding="utf-8"))
    existing = {path.stem for path in ILLUST_DIR.glob("*.png")} if ILLUST_DIR.exists() else set()
    requests = []
    seen = set()
    reserved_slots = set()

    for section_name, section in sections(data):
        text = section_text(section)
        for rule in RULES:
            variant = rule["variant"]
            if variant in seen or variant in existing:
                continue
            if not any(keyword.lower() in text.lower() for keyword in rule["keywords"]):
                continue
            chunk_idx = find_chunk(section, rule["keywords"])
            slot = (section_name, chunk_idx)
            if slot in reserved_slots:
                continue
            seen.add(variant)
            reserved_slots.add(slot)
            requests.append(
                {
                    "variant": variant,
                    "filename": f"{variant}.png",
                    "section": section_name,
                    "chunk_index": chunk_idx,
                    "reason": rule["reason"],
                    "prompt": STYLE + "\n\n핵심 콘셉트:\n" + rule["concept"],
                    "status": "requested",
                }
            )
            if len(requests) >= 3:
                break
        if len(requests) >= 3:
            break

    payload = {
        "slug": slug,
        "policy": "prepare prompts first; download approved GPT Plus PNGs; import by request order; render after import",
        "upload_dir": str(ILLUST_DIR),
        "requests": requests,
    }
    json_path = output_dir / "codex_illustration_requests.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Codex Illustration Requests: {slug}",
        "",
        "현재 라이브러리에 없는 일러스트만 추천합니다.",
        "아래 순서대로 GPT Plus에서 생성하고 다운로드하세요.",
        "파일명 변경은 데스크의 자동 가져오기 기능이 처리합니다.",
        "",
    ]
    if not requests:
        lines.append("새로 만들 일러스트가 없습니다. 바로 렌더링해도 됩니다.")
    for idx, item in enumerate(requests, 1):
        lines.extend(
            [
                f"## {idx}. `{item['filename']}`",
                "",
                f"- 적용 위치: `{item['section']}` 청크 {item['chunk_index'] + 1}",
                f"- 추천 이유: {item['reason']}",
                "",
                "```text",
                item["prompt"],
                "```",
                "",
            ]
        )
    md_path = output_dir / "codex_illustration_requests.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"[illustration_scout] report: {md_path}")
    print(f"[illustration_scout] requests: {len(requests)}")
    for item in requests:
        print(f"  - {item['filename']} -> {item['section']} chunk {item['chunk_index'] + 1}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def backup(path: Path) -> Path:
    target = path.with_name(path.name + f".bak_clean_scout_{STAMP}")
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


def main() -> int:
    if SCOUT.exists():
        backup(SCOUT)
    SCOUT.write_text(SCOUT_CODE, encoding="utf-8")
    py_compile.compile(str(SCOUT), doraise=True)
    append_once(
        MEMORY,
        "## 31. Clean UTF-8 illustration scout",
        """## 31. Clean UTF-8 illustration scout
- Codex illustration scouting uses clean UTF-8 Korean prompts.
- New prompts recommend reusable concepts with polished editorial drawing quality.
- Requests avoid article-specific brand, model, date, price, and person details.
- At most three missing illustrations are suggested per prepare run.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-01 - Clean UTF-8 illustration scout",
        """## 2026-06-01 - Clean UTF-8 illustration scout
- Replaced corrupted prompt text with readable UTF-8 Korean.
- Kept reusable concept guidance and the three-request cap.
- Prepared the scout for the two-click GPT Plus desk.""",
    )
    print("[done] Clean illustration scout installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
