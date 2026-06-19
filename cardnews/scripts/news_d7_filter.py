#!/usr/bin/env python3
"""news 라인 D-7 결정론적 필터 (수집 단계 게이트).

배경: news = D-7 strict (INSTRUCTIONS_CARDNEWS.md:134/382). 사람/LLM이 날짜를
눈대중하면 누락됨 → 보도일을 코드가 계산해 D-7 통과만 남긴다.

★ 기준일 = 한국시간(KST=UTC+9, 한국은 DST 없음) 고정.
   `date.today()`는 실행 환경 TZ(샌드박스/서버=UTC)에 의존 → 한국 00:00~09:00엔
   하루 어긋나 D-7이 밀린다. 그래서 KST로 강제. (2026-06-19 사장님 지적 반영)

사용:
  echo '[{"topic":"갤럭시 A37 출시","date":"2026-06-19"}, ...]' \
    | py -3 scripts/news_d7_filter.py
  py -3 scripts/news_d7_filter.py candidates.json
  py -3 scripts/news_d7_filter.py --today 2026-06-19 candidates.json   # 기준일 수동 지정

입력: JSON 배열 [{"topic":..., "date":"YYYY-MM-DD" 또는 "YYYY.MM.DD"}]
출력: PASS / REJECT(D-N) 판정 + 통과 목록. 통과 0건이면 그 사실을 명시.
날짜 불명(빈값/파싱불가) = REJECT (:384 "발행일 불명이면 후보 제외").
"""
import sys, json, re
from datetime import datetime, timedelta, timezone

D7 = 7
KST = timezone(timedelta(hours=9))  # 한국표준시 (DST 없음)


def kst_today():
    return datetime.now(KST).date()


def _parse(s):
    if not s:
        return None
    s = str(s).strip().replace('.', '-').replace('/', '-')
    s = re.sub(r'-+', '-', s).strip('-')
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None


def main():
    args = sys.argv[1:]
    today = kst_today()
    if args and args[0] == '--today':
        today = _parse(args[1]) or today
        args = args[2:]

    raw = open(args[0], encoding='utf-8').read() if args else sys.stdin.read()
    try:
        items = json.loads(raw)
    except Exception as e:
        print(f"ERROR: 입력 JSON 파싱 실패: {e}", file=sys.stderr)
        return 2
    if isinstance(items, dict):
        items = [items]

    cutoff = today - timedelta(days=D7)
    passed = []
    print(f"=== news D-7 필터 (KST 오늘={today}, 컷오프=D-{D7} = {cutoff}) ===")
    for it in items:
        topic = (it.get('topic') or it.get('title') or '?').strip()
        d = _parse(it.get('date') or it.get('publication_date'))
        if d is None:
            print(f"  REJECT  [발행일 불명] {topic}")
            continue
        dn = (today - d).days
        if 0 <= dn <= D7:
            print(f"  PASS    [D-{dn}] {topic}")
            passed.append(topic)
        elif dn < 0:
            print(f"  REJECT  [미래 D+{-dn}] {topic}")
        else:
            print(f"  REJECT  [D-{dn} > 7] {topic}")

    print(f"=== news 통과: {len(passed)}건 ===")
    if not passed:
        print("(D-7 통과 news 0건 — 정직한 한계로 표기, 다른 라인으로 보강)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
