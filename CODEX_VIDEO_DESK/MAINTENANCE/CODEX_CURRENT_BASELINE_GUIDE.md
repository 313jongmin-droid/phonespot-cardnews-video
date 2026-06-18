# PhoneSpot Codex Remotion Baseline

## Caption display color contract

- Screen-caption text uses one readable text color only.
- Do not infer or render orange or yellow inline caption highlights.
- Orange remains available for structural brand accents, CTA elements, headers, and infographics.

## Fixed caption font and independent visual rhythm

- Casual screen captions use one stable `72px` font size.
- Long narration is split at Korean grammar boundaries instead of shrinking text.
- Caption windows follow TTS timing. Source-image windows normally hold for about `2.2~4.2s`.
- CTA visuals, illustrations, logos, mascots, and infographics stay static.

기준일: 2026-06-01

> 전체 품질 계약과 롤백 방지 기준은 `CODEX_MASTER_VIDEO_GUIDE.md`를 우선 확인합니다.
> 이 문서는 빠른 운영 안내이며, 충돌 시 마스터 가이드를 따릅니다.

## 1. 목적

Claude 카드뉴스 결과물을 입력으로 받아 Codex 전용 Remotion 쇼츠를 만듭니다.
Claude 카드뉴스 실행 파일과 폴더는 수정하지 않습니다.

## 2. 폴더 경계

```text
C:\backup\phonespot_cardnews\
├─ cardnews\                 Claude 카드뉴스 원본
│  ├─ articles\
│  ├─ images\<slug>\         슬러그별 GPT 원본 이미지
│  └─ output\<slug>\
│     ├─ captions.md
│     ├─ shorts_script.json
│     └─ codex_illustration_requests.*
├─ shorts\                   Codex Remotion 엔진
│  ├─ src\
│  ├─ scripts\
│  ├─ public\assets\illustrations\
│  ├─ public\audio\
├─ CODEX_VIDEO_DESK\         일상 작업 버튼
│  ├─ RESULTS\               최종 영상과 발행패키지 실제 저장소
│  ├─ TEMP\_raw\             렌더 중간 파일
│  └─ ILLUSTRATION_DROP\     일러스트 라이브러리 실제 저장소
└─ shorts\public\assets\illustrations\
                          렌더 직전 자동 갱신되는 Remotion 내부 캐시
```

Codex 설치 도구는 별도 폴더에 있습니다.

`C:\Users\di898\Documents\Codex\2026-04-30\codex-plugin-marketplace-add-heygen-com`

## 3. 최초 적용 또는 업데이트 후

아래 파일을 한 번 실행합니다.

`RUN_APPLY_CODEX_CURRENT_BASELINE.bat`

활성 설치 단계:

1. 한국어 자막·고정 CTA 검증
2. 한 영상 안에서 GPT 원본 이미지 1회 사용 검증
3. Codex 작업 데스크 설치
4. 간결한 Codex 가이드 설치
5. UTF-8 일러스트 추천기 설치
6. 롤백 방지용 마스터 영상 가이드 설치
7. GPT Plus 두 클릭 작업 흐름 설치
8. 화면 마침표 숨김 규칙 설치
9. TTS-화면 청크 일치 규칙 설치
10. 단일 결과 폴더 V2 설치

## 4. 일상 작업

작업 폴더:

`C:\backup\phonespot_cardnews\CODEX_VIDEO_DESK`

### 새 영상

1. `01_PREPARE_GPT_PROMPTS.bat`
2. 슬러그 선택
3. 열린 `LATEST_PROMPT.md`를 보고 GPT Plus에서 필요한 이미지를 순서대로 생성
4. 생성 이미지는 브라우저 다운로드만 수행
5. `02_IMPORT_DOWNLOADS_AND_RENDER.bat`
6. 자동 매칭 목록 확인 후 `Y`
7. `RESULTS`에서 최종 MP4와 캡션 확인

### 새 일러스트가 필요 없는 재렌더

`03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat`

### 보조 버튼

- `04_OPEN_LATEST_PROMPT.bat`
- `05_OPEN_RESULTS.bat`
- `06_OPEN_ILLUSTRATION_LIBRARY.bat`
- `07_OPEN_RESULTS_HISTORY.bat`

`RESULTS`는 업로드할 최종 파일과 재렌더 이력을 함께 보여줍니다.

## 5. 렌더 파이프라인

`run_codex_casual.bat`은 아래 순서로 실행됩니다.

1. Node.js, Python, `edge-tts` 확인
2. 카드뉴스 원본에서 `shorts_script.json` 준비
3. Codex 공통 품질 보정
4. 업로드된 일러스트 자동 적용
5. 신규 일러스트 최대 3개 추천
6. 한국어·CTA·원본 이미지 중복 계약 검증
7. 자산 복사
8. `edge-tts` 음성 생성: `ko-KR-SunHiNeural`, 기본 속도 `+42%`
9. Remotion H.264 렌더
10. SNS MP4 마무리와 품질 검사
11. `RESULTS/<렌더 이름>/`에 MP4, 캡션, 채널별 발행 문구 저장

## 6. 고정 품질 계약

- CTA는 항상 두 화면입니다.
  - `휴대폰 구매할 땐?`
  - `지원금부터 무료로 조회해보세요`
- 마지막 화면은 PhoneSpot 로고입니다.
- 한국어 청크에 임의로 조사나 어미를 덧붙이지 않습니다.
- `줄어듭니다입니다.` 같은 중복 서술어는 렌더 전에 차단합니다.
- GPT 원본 이미지는 한 영상 안에서 각각 최대 1회만 사용합니다.
- CTA 이미지와 일러스트는 정지 상태를 유지합니다.
- GPT 원본 이미지만 노출 시간에 비례한 모션을 적용합니다.
- 신규 GPT Plus 일러스트는 최대 3개만 추천합니다.
- 신규 일러스트는 기사 전용 세부 묘사보다 재사용 가능한 의미를 우선합니다.
- 재사용 가능성은 그림을 단순하게 만들라는 뜻이 아닙니다. 완성도 높은 에디토리얼 일러스트를 요구합니다.

## 7. 백업

아래 파일을 실행합니다.

`RUN_BACKUP_CODEX_CURRENT_BASELINE.bat`

백업 위치:

`backups\CODEX_CURRENT_BASELINE_<날짜_시간>.zip`

백업에는 활성 Codex 설치 파일, Remotion 코드, Codex 스크립트, 설정, 문서, 로고, 일러스트 라이브러리가 포함됩니다.

제외:

- `node_modules`
- 렌더 결과 MP4
- TTS 오디오 캐시
- 오래된 `.bak` 파일

## 8. 점검

아래 파일을 실행합니다.

`RUN_CODEX_REGRESSION_AUDIT.bat`

점검 항목:

- 한국어 중복 어미
- CTA 고정 문구와 마지막 로고
- 청크·표시 문장·비주얼 개수
- GPT 원본 이미지의 영상 내 중복 사용
- 참조 일러스트 파일 존재 여부
- 최근 쇼츠 JSON 구조

## 9. 장애 복구

1. 작업 전 `RUN_BACKUP_CODEX_CURRENT_BASELINE.bat` 실행
2. 문제가 생기면 가장 최근 ZIP을 별도 폴더에 압축 해제
3. 활성 파일만 비교하여 복구
4. `RUN_APPLY_CODEX_CURRENT_BASELINE.bat` 재실행
5. `RUN_CODEX_REGRESSION_AUDIT.bat` 실행

Claude 카드뉴스 폴더를 통째로 덮어쓰지 않습니다.

## 10. 정크 정리

정리 전 미리보기:

`RUN_PREVIEW_CODEX_CONFIRMED_JUNK.bat`

확인 후 삭제:

`RUN_DELETE_CODEX_CONFIRMED_JUNK.bat`

삭제 대상은 Codex 캐시, 과거 Codex 패치 백업, 비어 있는 raw 렌더 폴더, 중복 기준선 ZIP입니다.
`RESULTS`, 카드뉴스 원본, 현재 일러스트, Promo, HyperFrames 비교본은 삭제하지 않습니다.

## 11. 화면 청크 마침표 표시

- 화면에 표시되는 영상 청크에서는 문장부호 마침표 `.`를 숨깁니다.
- `iOS 26.6`, `1.5배`처럼 숫자 사이의 소수점과 버전 구분점은 유지합니다.
- TTS와 작성된 나레이션 원문은 바꾸지 않습니다.
- 공통 자막 표시 로직에 적용되므로 앞으로 생성되는 모든 Remotion 영상에 반영됩니다.

## 12. 단일 결과 폴더 V2

- 완성 영상은 `CODEX_VIDEO_DESK/RESULTS/<렌더 이름>/` 아래에 저장합니다.
- 각 결과 폴더에는 폴더명과 동일한 이름의 MP4, `captions.md`, 통합 업로드 문서 `UPLOAD_COPY.txt`가 함께 있습니다.
- `UPLOAD_COPY.txt` 한 파일 안에서 유튜브 쇼츠·인스타그램 릴스·틱톡 구역을 나누어 필요한 부분만 복사합니다.
- 렌더 중간 파일은 `CODEX_VIDEO_DESK/TEMP/_raw/`에만 저장하며 완료 후 제거합니다.
- 재렌더하면 시간 suffix가 붙은 새 폴더를 만들어 이전 결과를 보존합니다.
- 기존 `upload_codex`와 과거 `shorts/out_codex` 내용은 설치 시 `backups/CODEX_DESK_ONLY_STORAGE_MIGRATION_<시각>/`으로 이동합니다.

## 13. 롤백 방지 마스터 가이드

- `CODEX_MASTER_VIDEO_GUIDE.md`는 전체 품질 계약의 기준 문서입니다.
- 설치하면 공용 `shorts/codex/CODEX_MASTER_VIDEO_GUIDE.md`와 작업 폴더 `CODEX_VIDEO_DESK/SYSTEM_GUIDE.md`에 함께 저장됩니다.
- 기능 추가 전 마스터 가이드의 금지 사항과 변경 절차를 먼저 확인합니다.
- 화면 청크를 TTS와 별도 요약문으로 되돌리거나, 모든 문장에 종결어미를 자동 부착하는 수정은 금지합니다.
