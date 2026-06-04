"""
2026-06-03 신규 수집 결과 텔레그램 1회 전송.
실행: py -3 automation/scripts/send_collect_result.py
"""
import sys
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SECRETS = ROOT / "_secrets"

token = (SECRETS / "telegram_token.txt").read_text(encoding="utf-8").strip()
chat_id = (SECRETS / "telegram_chat_id.txt").read_text(encoding="utf-8").strip()

msg = """[신규 수집 결과 2026-06-03]
D-7 기준: 2026-05-27 / 다음 번호: 014~

[A] news / 아이폰 폴드 2026 2분기 출시설 (밍치궈)
  D-7: △ (발행일 검증 X) / 매장정합: ◎
[B] news / 갤럭시 S26 출시 일정
  D-7: ✗ (과거 발행) / 제외
[C] news / 아이폰18 라인업 변화 (Pro/Air/Fold)
  D-7: △ / 매장정합: ◎
[D] scam / 신한 보이스피싱제로 3차 9차 지원 6/1 시작
  D-7: ✓ (D-2) / 정책·통계 신호 강함
[E] scam / 이커머스 해킹 → 스미싱·피싱 KISA 권고
  D-7: △ / 일반론
[F] tip / iOS26 적응형 전원 + AOD 흐림 비활성
  D-7: ✗ (1월~ 발행) / 제외
[G] tip / iOS26 잠금화면 스와이프 비활성
  D-7: ✗ / 제외
[H] qa / 선택약정 12개월 vs 24개월 - 12개월 유리
  시점 무관 / 검색의도 ◎ / 008과 다른 각도
[I] qa / 자급제+선택약정 vs 공시지원금
  004 중복 위험

[정직한 한계]
- news 라인 D-7 strict 통과 후보 사실상 없음
- tip 라인도 D-7 통과 후보 없음
- scam = D 단독 유효
- qa = H 유력

[권장 발행]
014 / scam / 신한 보이스피싱제로 3차 9차 지원 시작
015 / qa   / 선택약정 12개월 vs 24개월 - 12개월 유리

[결정 옵션]
1. 014 + 015 발행 (안전, 권장)
2. 014 + 015 + A(news) 발행 (A 검증 필요)
3. 직접 지정

번호 또는 옵션 회신해주세요.
"""

url = f"https://api.telegram.org/bot{token}/sendMessage"
data = urllib.parse.urlencode({
    "chat_id": chat_id,
    "text": msg,
    "disable_web_page_preview": "true",
}).encode("utf-8")

req = urllib.request.Request(url, data=data, method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        print(f"HTTP {resp.status}")
        print(body[:300])
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
