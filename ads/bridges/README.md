# bridges/ — 폰스팟 폴더 내부 모듈 간 정보 교환

> `ads/`가 같은 폴더의 다른 모듈(`cardnews/`, `shorts/`, `automation/`)에서 데이터를 **읽기만** 하는 인터페이스 모음.

---

## 원칙

1. **단방향**: bridges는 다른 모듈의 출력을 읽기만 함. 변경 X
2. **명시적 경로**: 어디서 뭘 읽는지 from_*.md 파일에 단일 출처로 적음
3. **다른 모듈 구조 변경 격리**: cardnews/ 구조가 바뀌면 `from_cardnews.md`만 수정하면 ads/는 안 깨짐
4. **출력 = SNS 시트로 sync**: 카드뉴스/쇼츠 발행 → 자동으로 「폰스팟 광고운영 관리대장」의 해당 SNS 시트에 행 추가

---

## 파일 목록 (계획)

| 파일 | 역할 | 상태 |
|------|------|------|
| `from_cardnews.md` | 카드뉴스 발행 결과 위치/스키마 정의 | 작성 예정 |
| `from_shorts.md` | 쇼츠 발행 결과 위치/스키마 정의 | 작성 예정 |
| `from_upload.md` | upload/ 폴더의 SNS 업로드 패키지 메타데이터 | 작성 예정 |
| `sync_sns_sheet.py` | 위 데이터를 Google Sheets SNS 시트에 자동 입력하는 스크립트 | 작성 예정 |

---

## 데이터 흐름 (목표)

```
cardnews/output/2026-MM-DD-slug.png    (카드뉴스 이미지)
cardnews/output/2026-MM-DD-slug.json   (메타: 주제·텍스트·해시태그)
        ↓ bridges/from_cardnews.md 가 경로·스키마 명시
        ↓ bridges/sync_sns_sheet.py 가 읽음
        ↓
Google Sheets 「인스타」 시트 / 「스레드」 시트
  · A: 날짜 (발행일)
  · B: 포맷 (네이티브_피드/네이티브_릴스 등)
  · C: 주제
  · D: 링크 (SNS URL — 업로드 후 채워짐)
  · E: 조회수 (수동 또는 별도 수집)

shorts/out/B_casual/2026-MM-DD-slug.mp4   (쇼츠 영상)
shorts/upload/2026-MM-DD-slug/meta.json   (메타데이터)
        ↓ bridges/from_shorts.md 가 명시
        ↓ bridges/sync_sns_sheet.py
        ↓
Google Sheets 「유튜브」 시트 / 「틱톡」 시트
  · 동일 컬럼 구조
```

---

## SNS 시트 구조 (sync 타겟)

각 SNS 시트는 동일 컬럼 구조:

| 컬럼 | 의미 |
|------|------|
| A | 날짜 (발행일) |
| B | 포맷/구분 (예: 네이티브_피드, 네이티브_쇼츠) |
| C | 주제 |
| D | 링크 (발행 SNS URL) |
| E | 조회수 |
| F | 좋아요 |
| G | 팔로워 수 (월말 시점) |
| H | 운영 메모 |
| I | 비고 |

→ `ads/data/sheet_structure.md`에 상세

> **이게 채워지면 통합대시보드 SNS 보고표(updateSNSReport)가 자동으로 집계**

---

## 인증·시크릿

- Google Sheets API 접근에는 서비스 계정 또는 OAuth 토큰 필요
- 시크릿은 부모 폴더의 `_secrets/`에 보관
- 이 폴더 안에 토큰/키 직접 저장 ❌

---

## 다음 작업 (스크립트 작성 전 필요한 정보)

스크립트를 만들기 전에 다음 확인:
1. `cardnews/output/` 의 파일 명명 규칙 (날짜-슬러그?) → cardnews 가이드 읽기
2. `shorts/out/` 의 결과물 위치·메타 파일 형식 → shorts/harness/README_FOR_AI.md
3. 사용자가 발행 직후 sync 실행할지, 야간 daemon이 일괄 실행할지 (`automation/night_daemon.bat`)

---

작성: 2026-05-30 (구조만, 스크립트 작성 보류)
