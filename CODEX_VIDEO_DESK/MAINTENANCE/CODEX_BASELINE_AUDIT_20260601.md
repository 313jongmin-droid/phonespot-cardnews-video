# PhoneSpot Codex Remotion Baseline Audit

점검일: 2026-06-01

## 결론

현재 Codex Remotion 기준선 설치 도구는 정상입니다.

최신 설치 파일을 한 번 다시 실행하면:

- UTF-8 한국어 기준선 문서가 공용 `shorts\codex` 폴더에 설치됩니다.
- 깨진 한글 프롬프트를 사용하던 이전 일러스트 추천기가 교체됩니다.
- `CODEX_VIDEO_DESK`는 신규 두 클릭 흐름 버튼만 남도록 정리됩니다.
- `CODEX_VIDEO_DESK\OUT_CODEX`에서 렌더 이력을 바로 확인할 수 있습니다.
- 새로고침을 실행해도 예전 버튼이 다시 생기지 않습니다.

실행:

`RUN_APPLY_CODEX_CURRENT_BASELINE.bat`

## 완료된 검사

### Codex 설치 도구

- 활성 Python 설치 파일 구문 검사 통과
- 설치 파일 내부에 포함된 Python 도우미 코드 구문 검사 통과
- 기준선 배치 파일의 6개 설치 파일 참조 검사 통과
- 정리 PowerShell 파일 구문 검사 통과
- 정리 파일이 신규 기준선 파일을 보존하는지 확인

### 공용 PhoneSpot Shorts

- 활성 Python 스크립트 15개 구문 검사 통과
- TypeScript 검사 통과: `npx tsc --noEmit`
- 백업 ZIP 생성 및 매니페스트 검증 통과
- 백업 안에 운영 가이드, Codex 렌더 실행 파일, 일러스트 라이브러리가 포함됨

## 기존 JSON 회귀 점검

최근 10개 `shorts_script.json`을 검사했습니다.

정상:

- `005_scam_voice_phishing_peak`
- `006_scam_oilfund_smishing`
- `phone_repair_security_2026`
- `iphone_nfc_open_2026`
- `iphone18_aluminum_2026`
- `ios_26_6_beta_2026`
- `galaxy_price_hike_europe_2026`
- `galaxy_ai_club_may_2026`

기존 데이터 보정 필요:

- `004_qa_subsidy_vs_contract`
- `oneui85_q2_2026`

두 JSON은 “GPT 원본 이미지 한 영상당 1회 사용” 계약을 넣기 전에 만든 예전 데이터입니다.
현재 엔진 오류가 아닙니다. 해당 영상을 다시 렌더할 때 최신 보정 로직이 적용됩니다.

## 알려진 운영 상태

- Remotion이 현재 기준 영상 엔진입니다.
- HyperFrames는 비교용으로만 남아 있습니다.
- 예약 자동화는 카드뉴스 자동화가 안정화될 때까지 보류합니다.
- GPT Plus 일러스트 생성은 수동이지만, 폴더 이동과 파일 이름 변경은 두 클릭 데스크가 자동화합니다.

## 일상 실행

작업 폴더:

`C:\Users\di898\Documents\phonespot_cardnews\CODEX_VIDEO_DESK`

새 영상:

1. `01_PREPARE_GPT_PROMPTS.bat`
2. GPT Plus에서 순서대로 생성 후 다운로드
3. `02_IMPORT_DOWNLOADS_AND_RENDER.bat`

재렌더:

`03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat`
