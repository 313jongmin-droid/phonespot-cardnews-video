#!/usr/bin/env python3
"""기사 JSON 스키마 검증 + 다음 발행 번호(NNN) 자동 산출.

사용:
  py -3 scripts/validate_article.py            # 모든 정규번호 기사 검증 (ERROR 있으면 exit 1)
  py -3 scripts/validate_article.py --all      # 위와 동일
  py -3 scripts/validate_article.py --next     # 다음 NNN 출력 (예: 026)
  py -3 scripts/validate_article.py 025         # 한 슬러그/번호 검증
  py -3 scripts/validate_article.py 025_tip_galaxy_ai_call_screening

정규번호 기사 = articles/NNN_*.json (3자리 prefix). 레거시 무번호는 검증 제외.

2단 검증:
  ERROR = 렌더 치명 (없으면 렌더/발행 불가) -> exit 1로 게이트
  WARN  = 스펙/품질 (발행은 되나 룰 위반) -> 보고만
"""
import sys, json, re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARTICLES = SCRIPT_DIR.parent / 'articles'

# 렌더 치명 키 (없으면 run_pngs 사전검사도 실패)
REQUIRED_ERROR = ['slug', 'title', 'cards', 'captions_md']
# 스펙/품질 키 (CARDNEWS_BUILD D-2 권장 스키마)
REQUIRED_WARN = ['content_type', 'publication_date', 'source_line', 'narration_md']
VALID_TYPES = {'news', 'scam', 'tip', 'qa', 'pick', 'meme', 'life'}
NUM_RE = re.compile(r'^(\d{3})_')
# 해시태그 = # 뒤에 공백/# 아닌 글자가 바로 옴 (마크다운 '## 헤더'는 제외)
HASHTAG_RE = re.compile(r'#[^\s#]')


def numbered_files():
    return sorted(p for p in ARTICLES.glob('*.json') if NUM_RE.match(p.stem))


def next_number():
    nums = [int(NUM_RE.match(p.stem).group(1)) for p in numbered_files()]
    return f"{(max(nums) + 1) if nums else 1:03d}"


def _empty(v):
    return v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v)


def validate_one(path):
    """반환: (errors: list[str], warns: list[str])"""
    try:
        d = json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return [f"JSON 파싱 실패: {e}"], []

    errors, warns = [], []

    for k in REQUIRED_ERROR:
        if _empty(d.get(k)):
            errors.append(f"[필수] 누락/빈값: {k}")
    for k in REQUIRED_WARN:
        if _empty(d.get(k)):
            warns.append(f"누락: {k}")

    ct = d.get('content_type')
    if ct and ct not in VALID_TYPES:
        warns.append(f"content_type 비표준: {ct} (허용: {sorted(VALID_TYPES)})")

    cards = d.get('cards')
    if isinstance(cards, list) and len(cards) != 6:
        warns.append(f"cards 6장 아님: {len(cards)}장")

    slug = d.get('slug', '')
    if slug and slug != path.stem:
        errors.append(f"[필수] slug 불일치: json='{slug}' != 파일명='{path.stem}'")

    nar = d.get('narration_md', '')
    if isinstance(nar, str) and nar:
        if 'http://' in nar or 'https://' in nar:
            warns.append("narration_md에 URL (음성합성용 X)")
        if HASHTAG_RE.search(nar):
            warns.append("narration_md에 해시태그(#태그) (마크다운 '## '는 허용)")

    return errors, warns


def resolve(arg):
    """번호/슬러그/파일명 -> Path"""
    arg = arg.strip()
    if arg.isdigit():
        m = sorted(ARTICLES.glob(f"{arg}_*.json"))
        if m:
            return m[0]
    p = ARTICLES / (arg if arg.endswith('.json') else arg + '.json')
    return p if p.exists() else None


def main():
    args = sys.argv[1:]

    if args and args[0] == '--next':
        print(next_number())
        return 0

    if not args or args[0] == '--all':
        files = numbered_files()
        print(f"=== 정규번호 기사 {len(files)}건 검증 ===")
        n_err, n_warn = 0, 0
        for p in files:
            errors, warns = validate_one(p)
            if errors:
                n_err += 1
                print(f"  ERROR {p.stem}")
                for i in errors:
                    print(f"        - {i}")
                for i in warns:
                    print(f"        ~ (warn) {i}")
            elif warns:
                n_warn += 1
                print(f"  WARN  {p.stem}")
                for i in warns:
                    print(f"        ~ {i}")
            else:
                print(f"  OK    {p.stem}")
        clean = len(files) - n_err - n_warn
        print(f"=== 결과: {clean} OK / {n_warn} WARN / {n_err} ERROR ===")
        print(f"다음 발행 번호: {next_number()}")
        return 1 if n_err else 0

    # 단일 검증
    p = resolve(args[0])
    if not p:
        print(f"ERROR: 기사 없음 '{args[0]}'", file=sys.stderr)
        return 1
    errors, warns = validate_one(p)
    if not errors and not warns:
        print(f"OK {p.stem}")
        return 0
    print(("ERROR " if errors else "WARN ") + p.stem)
    for i in errors:
        print(f"  - {i}")
    for i in warns:
        print(f"  ~ {i}")
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
