#!/usr/bin/env python3
"""content_guide.md §2 발행 인덱스 자동 재생성 (학습 루프 강제용).

run_windows.py 렌더 성공 후 best-effort로 호출됨. 수동 실행도 가능:
  py -3 scripts/update_content_guide.py

동작: articles/*.json 을 스캔해 §2(발행 토픽 인덱스)만 통째 재생성.
§1·§3·§4·이력 등 사람이 쓴 섹션은 보존(§2 헤더 '## 2.' ~ 다음 '## 3.' 사이만 교체).
파일이 없으면 전체 템플릿으로 신규 생성. idempotent — 여러 번 돌려도 안전.
"""
import json, re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
ARTICLES = BASE / 'articles'
GUIDE = BASE / '_state' / 'content_guide.md'
NUM_RE = re.compile(r'^(\d{3})_')


def _load(p):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _classify():
    numbered, legacy, cleanup = [], [], []
    for p in sorted(ARTICLES.glob('*.json')):
        d = _load(p)
        title = (d.get('title') or '').replace('\n', ' ').strip()
        date = (d.get('publication_date') or '').strip()
        ctype = (d.get('content_type') or '-')
        stem = p.stem
        # 정리 대상: 테스트 잔재 / 빈 스텁
        if ('테스트' in title) or ('실제 발행' in title):
            cleanup.append((stem, '테스트 잔재 (실제 발행 X)'))
        elif not title and not date:
            cleanup.append((stem, '빈 스텁 (title·발행일 없음)'))
        elif NUM_RE.match(stem):
            numbered.append((NUM_RE.match(stem).group(1), ctype, date or '-', title or '-'))
        else:
            legacy.append((stem, date or '-', title or '-'))
    numbered.sort(key=lambda r: r[0])
    legacy.sort(key=lambda r: r[0])
    return numbered, legacy, cleanup


def _next_num(numbered):
    nums = [int(n) for n, *_ in numbered]
    return f"{(max(nums) + 1) if nums else 1:03d}"


def build_section2():
    numbered, legacy, cleanup = _classify()
    nxt = _next_num(numbered)
    L = []
    L.append("## 2. 발행 토픽 인덱스 (중복 회피 정본)")
    L.append("")
    L.append(f"> 자동 생성(update_content_guide.py). 다음 발행 번호: **{nxt}**. 직접 수정 금지 — 재렌더 시 덮어씀.")
    L.append("")
    L.append("### 정규 번호 (NNN_type_topic)")
    L.append("")
    L.append("| NNN | type | 발행일 | 토픽 |")
    L.append("|---|---|---|---|")
    for n, t, d, title in numbered:
        L.append(f"| {n} | {t} | {d} | {title} |")
    L.append("")
    L.append("### 레거시 무번호 (001 이전, 재제안 회피용)")
    L.append("")
    L.append("| 파일 | 발행일 | 토픽 |")
    L.append("|---|---|---|")
    for stem, d, title in legacy:
        L.append(f"| {stem} | {d} | {title} |")
    L.append("")
    L.append("### 정리 대상 (발행 아님 — 제거 권고)")
    L.append("")
    if cleanup:
        L.append("| 파일 | 사유 |")
        L.append("|---|---|")
        for stem, reason in cleanup:
            L.append(f"| {stem} | {reason} |")
    else:
        L.append("(없음)")
    L.append("")
    return "\n".join(L)


TEMPLATE_HEAD = """# 카드뉴스 콘텐츠 가이드 — 발행 인덱스 + 사이클 학습 메모

> STEP 1 #6 / CARDNEWS_BUILD STEP I 정본. 매 수집·발행 사이클마다 Read → 갱신.
> §2는 자동 생성(update_content_guide.py). §3·§4는 수동(사실만).

---

## 1. 사용법 (매 사이클)

- 신규 수집 전: §2 발행 인덱스 = 중복 회피 정본. `articles/*.json`과 교차 확인.
- 발행 후: §3에 시즌/트렌드 관찰 1줄 추가. §2는 렌더 시 자동 갱신.

---

"""

TEMPLATE_TAIL = """---

## 3. 시즌 / 트렌드 학습 메모 (매 사이클 append, 사실만)

> 관찰된 사실만 1줄씩 누적. 추측 금지.

- (발행 시마다 여기에 1줄)

---

## 4. 자동화 메모

- §2 자동 갱신: run_windows.py 렌더 성공 시 update_content_guide.py 호출.
- 다음 NNN / 스키마 검증: scripts/validate_article.py.

---

## 이력

- 2026-06-18: content_guide 신설 + §2 자동화.
"""


def main():
    section2 = build_section2()
    GUIDE.parent.mkdir(parents=True, exist_ok=True)

    if GUIDE.exists():
        text = GUIDE.read_text(encoding='utf-8')
        # '## 2.' ~ 다음 '## 3.' 사이를 교체 (앞뒤 보존)
        m2 = re.search(r'(?m)^## 2\.', text)
        m3 = re.search(r'(?m)^## 3\.', text)
        if m2 and m3 and m2.start() < m3.start():
            new = text[:m2.start()] + section2 + "\n" + text[m3.start():]
        elif m2:  # §3 없으면 §2부터 끝까지 교체
            new = text[:m2.start()] + section2 + "\n"
        else:  # §2 없으면 §1 뒤에 삽입 (단순 append)
            new = text.rstrip() + "\n\n---\n\n" + section2 + "\n"
    else:
        new = TEMPLATE_HEAD + section2 + "\n" + TEMPLATE_TAIL

    GUIDE.write_text(new, encoding='utf-8')
    print(f"[content_guide] {GUIDE} 갱신 완료")


if __name__ == '__main__':
    main()
