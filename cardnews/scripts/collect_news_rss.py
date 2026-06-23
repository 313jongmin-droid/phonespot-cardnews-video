#!/usr/bin/env python3
"""한국 IT매체 RSS 자동 수집 → _state/news_feed.json (사장님 수기 URL 추가 불필요).

배경: WebSearch가 US 기준이라 한국 매체 속보를 못 잡음(2026-06-23 사장님 지적).
RSS(서버 XML)는 JS렌더·차단 문제 없이 당일 기사 목록(제목·날짜·링크)을 통째로 줌.
→ 매 수집 때 클로드가 이 json을 읽어 후보화(D-7·매장정합·dup 필터). 사람 개입 0.

실행(로컬 PC, 네트워크 필요): py -3 scripts/collect_news_rss.py
매일 자동: Windows 작업 스케줄러에 등록(아침 1회).
※ 샌드박스(클로드)에선 외부 네트워크 규칙상 실행 불가 — 로컬 PC에서만 동작.
"""
import json, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
D7 = 7
OUT = Path(__file__).resolve().parent.parent.parent / '_state' / 'news_feed.json'

# 검증: 디지털투데이 OK(2026-06-23 web_fetch XML 확인). 나머지는 종민이 URL 검증 후 주석 해제.
FEEDS = {
    '디지털투데이': 'https://www.digitaltoday.co.kr/rss/allArticle.xml',
    # 'ZDNet코리아': 'https://zdnet.co.kr/news/news_xml.asp?type=news',  # URL 검증 필요
    # '전자신문':   'https://rss.etnews.com/Section901.xml',            # IT섹션, 검증 필요
    # '아시아경제IT': 'https://www.asiae.co.kr/rss/...',                # 섹션 피드 확인 필요
}

# 폰/통신 도메인 키워드 (제목 필터 — 매장 무관 기사 거름)
KW = ['갤럭시', '아이폰', '애플', '삼성', '스마트폰', '휴대폰', '통신', '요금', '유심',
      'SKT', 'KT', 'LG유플', '5G', '아이패드', '에어팟', '워치', 'One UI', 'iOS',
      '폴드', '플립', '지원금', '자급제', '단통', '통신사', '갤워치', '버즈']


def parse_date(s):
    s = (s or '').strip()
    for fmt in ('%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def main():
    today = datetime.now(KST).date()
    cutoff = today - timedelta(days=D7)
    items = []
    for media, url in FEEDS.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            raw = urllib.request.urlopen(req, timeout=15).read()
            root = ET.fromstring(raw)
        except Exception as e:
            print(f"[skip] {media}: {e}")
            continue
        for it in root.iter('item'):
            title = (it.findtext('title') or '').strip()
            link = (it.findtext('link') or '').strip()
            pd = parse_date(it.findtext('pubDate'))
            d = pd.date() if pd else None
            if not any(k in title for k in KW):
                continue                       # 폰/통신 도메인만
            if d and d < cutoff:
                continue                       # D-7(KST) 컷
            items.append({'media': media, 'title': title, 'link': link,
                          'date': str(d) if d else ''})
    items.sort(key=lambda x: x['date'], reverse=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({'collected': str(today), 'cutoff': str(cutoff),
                               'count': len(items), 'items': items},
                              ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[news_feed] {len(items)}건 (D-7 {cutoff}~{today}) → {OUT}")


if __name__ == '__main__':
    main()
