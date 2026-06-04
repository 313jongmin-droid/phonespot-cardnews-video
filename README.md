# 폰스팟 카드뉴스 + 쇼츠 자동화

> **AI 작업자는 먼저 이 파일을 읽고, 필요한 폴더의 가이드만 직접 읽을 것.** 전체 폴더 재귀 탐색 ❌.

---

## 폴더 구조 (한눈에)

```
phonespot_cardnews/
├── README.md              ← 지금 이 파일 (전체 진입점)
├── _docs/                 📚 모든 가이드·인스트럭션·변경 이력
├── _secrets/              🔐 API 키·토큰 (gitignore)
├── _state/                📊 런타임 로그
├── _backup/               💾 zip 백업 모음
├── cardnews/              📰 카드뉴스 작업 (articles/images/output/scripts)
├── shorts/                🎬 쇼츠 영상 자동화 (Remotion+TTS)
├── upload/                📤 SNS 업로드 패키지 (mp4·md)
├── automation/            🤖 야간 daemon (Chrome 자동화·텔레그램)
├── ads/                   💰 폰스팟 광고운영 관리대장 (성지 판매점)
└── ads_kt/                🏢 KT다이렉트샵 광고운영 (KT 공식 인증 대리점)
```

---

## AI는 어디부터 읽나 (작업 종류별)

| 작업 | 첫 진입 |
|---|---|
| **카드뉴스 생성** | `_docs/INSTRUCTIONS_CARDNEWS.md` |
| **쇼츠 영상 빌드** | `shorts/harness/README_FOR_AI.md` |
| **SNS 업로드** | `_docs/INSTRUCTIONS_UPLOAD.md` |
| **폰스팟 광고운영·KPI·시트** | `ads/README_FOR_AI.md` |
| **KT다이렉트샵 광고운영** | `ads_kt/README_FOR_AI.md` |
| **변경 이력·옛 디자인** | `_docs/BACKUP_HISTORY.md` |
| **새 PC 설치** | `_docs/PORTABILITY.md` |

각 폴더 안에 자체 README 또는 가이드. 필요한 것만 직접 지정해서 읽기.

---

## 사람용 — 자주 쓰는 명령

| 시나리오 | 명령 |
|---|---|
| 카드뉴스 1건 생성 | `cardnews\run_pngs.bat` |
| 카드뉴스 여러 건 일괄 | `cardnews\run_all.bat` |
| 쇼츠 영상 빌드 | `shorts\run_B_casual.bat` |
| 야간 자동화 (Task Scheduler) | `automation\night_daemon.bat` |

---

## 절대 재귀 탐색 금지

- `node_modules/` (수만 파일)
- `cardnews/images/<slug>/` (PNG 바이너리)
- `cardnews/output/` (JPG·캡션)
- `shorts/node_modules/`, `shorts/out/`, `shorts/out_codex/`
- `shorts/public/audio/` (mp3), `shorts/public/assets/` (PNG)
- `upload/*.mp4`, `*.mp3`, `*.zip`
- `_backup/*.zip`

상세는 `shorts/harness/IGNORE_RULES.md` 참조.

---

## 새 PC 이식

이 폴더 전체를 다른 PC로 복사한 후:
1. `_secrets/` 폴더는 비어있을 것 (gitignore) → 키 재발급 필요
2. `_docs/PORTABILITY.md` 따라 30분 셋업

---

폴더 구조 변경:
- 2026-05-28: carving + portable layout
- 2026-05-30: `ads/` 추가 (폰스팟 광고운영 자산화)
- 2026-05-30: `ads_kt/` 추가 (KT다이렉트샵 광고운영 — 별개 브랜드)
