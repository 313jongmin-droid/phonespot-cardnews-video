# integrations/ — 외부 광고 플랫폼 API 통합

> 메타·구글·네이버·카카오·당근·GA4 등 **외부 서비스의 데이터를 시트로 자동 수집**하는 모듈.

---

## 원칙

1. **채널별 폴더 분리** — `integrations/<채널>/` 각 채널마다 자체 폴더
2. **표준 파일 구조** — 채널마다 동일한 4개 파일:
   - `README.md` — 이 채널의 작동 방식·계정·제한사항
   - `auth.md` — 인증 방식·토큰 발급 절차 (시크릿은 `_secrets/` 참조)
   - `fetch.py` (또는 `.gs`) — 데이터 수집 스크립트
   - `push.py` (또는 `.gs`) — Google Sheets 업로드 스크립트
3. **시크릿 분리** — API 키·토큰은 절대 코드에 하드코딩 X. `_secrets/<채널>.env` 사용
4. **idempotent** — 같은 날짜 재실행 시 중복 행 추가 X (시트의 같은 날짜 행 덮어쓰기)

---

## 새 채널 추가 가이드 (확장 시)

새 광고 플랫폼이 추가됐을 때:

```bash
cd phonespot_cardnews/ads/integrations
mkdir <new_channel>
cd <new_channel>
```

그리고 다음 4개 파일 생성:

### `<new_channel>/README.md` 템플릿
```markdown
# <채널명> 광고 통합

## 무엇을 가져오나
- 노출 / 클릭 / 지출 / 캠페인별 일별 데이터

## 시트 타겟
- 「<채널명>」 시트의 A(날짜)~H(문의수) 열

## 계정
- 광고주: ...
- 로그인: <어디서>

## 실행 빈도
- 매일 새벽 X시 cron / Task Scheduler

## 제한사항·주의
- API rate limit
- 데이터 지연 시간 (X시간 후 확정값)
```

### `<new_channel>/auth.md` 템플릿
```markdown
# 인증

## 방식
- OAuth2 / API Key / 서비스 계정 / ...

## 시크릿 위치
- `_secrets/<channel>.env`:
  - CLIENT_ID=...
  - CLIENT_SECRET=...
  - REFRESH_TOKEN=...

## 토큰 발급 절차
1. <플랫폼 개발자 콘솔> 접속
2. ...
```

### `<new_channel>/fetch.py` 템플릿 골격
```python
"""<채널명> 광고 API → CSV/dict로 데이터 수집."""
import os
from datetime import date, timedelta

def fetch_daily(target_date: date) -> list[dict]:
    """target_date 하루치 광고 데이터를 dict 리스트로 반환.
    
    리턴 스키마 (sheet 컬럼 매핑):
    {
      'date': 'YYYY-MM-DD',
      'campaign': str,
      'impressions': int,
      'clicks': int,
      'spend': int,   # 원
      'conversions': int,
    }
    """
    # TODO: <플랫폼> API 호출
    raise NotImplementedError

if __name__ == '__main__':
    yesterday = date.today() - timedelta(days=1)
    rows = fetch_daily(yesterday)
    for r in rows:
        print(r)
```

### `<new_channel>/push.py` 템플릿 골격
```python
"""fetch.py가 만든 데이터를 Google Sheets에 업로드."""
from fetch import fetch_daily
from datetime import date, timedelta
# Google Sheets API 클라이언트 (gspread 등)

SHEET_ID = '1tCGFfu2FbGo1XbigaYPptlSbD-7Tj3PLnYH0_o9g5jI'
TAB_NAME = '<채널명>'

def push_to_sheet(rows: list[dict]):
    """rows를 시트의 A~H열에 같은 날짜는 덮어쓰기, 신규는 추가."""
    raise NotImplementedError

if __name__ == '__main__':
    yesterday = date.today() - timedelta(days=1)
    rows = fetch_daily(yesterday)
    push_to_sheet(rows)
```

---

## 채널별 진행 상태

| 채널 | 폴더 생성 | API 검토 | 인증 셋업 | 코드 작성 | 운영 중 |
|------|---------|---------|---------|---------|--------|
| **GA4** | ❌ 불필요 | — | — | — | ✅ Apps Script로 처리 중 (`fetchGA4Daily`) |
| **메타 광고** | 예정 | 가능 (Marketing API) | — | — | ❌ 현재 수동 입력 |
| **구글 광고** | 예정 | 가능 (Google Ads API). 단 이전에 cost 필드 단위 이슈로 1차 시도 실패 | — | — | ❌ 현재 수동 입력 |
| **네이버 검색광고** | 예정 | 가능 (검색광고 API) | — | — | ❌ 현재 수동 입력 |
| **카카오 모먼트** | 예정 | 가능 (Moment Open API) | — | — | ❌ 미운영 (광고 자체를 안 함) |
| **당근** | 예정 | ❌ 공식 API 없음 → 수동 입력 가이드만 | — | — | ❌ 현재 수동 입력 |

→ 우선순위 1: **메타 광고 API** (운영 채널 + API 가능)

---

## GA4는 왜 integrations/에 폴더 없나

GA4 데이터 수집은 **Apps Script(`importGA4`)에서 직접 처리** 중. AnalyticsData 고급 서비스 사용.

- 진실의 원천: `ads/code/apps_script/Code.gs`의 `fetchGA4Daily()` / `fetchGA4Backfill()` / `importGA4()`
- 별도 Python 스크립트 불필요 — Apps Script에서 GA4 Data API 직접 호출
- 트리거: 매일 새벽 1시 (Asia/Seoul)

만약 나중에 GA4를 Apps Script 외부에서 처리할 필요 생기면 `integrations/ga4/` 폴더 추가.

---

## 시크릿 관리

모든 API 키·토큰은 **이 폴더 밖**의 `_secrets/`에:

```
phonespot_cardnews/_secrets/
├── meta_ads.env
├── google_ads.env
├── naver_ads.env
└── ...
```

- `.gitignore`에 의해 git에서 제외됨
- 새 PC 이식 시 재발급 필요 (PORTABILITY.md 참조)

---

## 실행 방식 (운영 중일 때)

옵션 A — 야간 batch:
```
automation/night_daemon.bat 안에서
> python ads/integrations/meta/push.py
> python ads/integrations/google_ads/push.py
> ...
```

옵션 B — 개별 수동 실행 (시작 시점):
```bash
cd phonespot_cardnews/ads/integrations/meta
python push.py
```

---

작성: 2026-05-30 (구조만, 채널별 코드는 추가 시 작성)
