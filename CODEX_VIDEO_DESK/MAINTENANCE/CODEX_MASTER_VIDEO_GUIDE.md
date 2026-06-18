# PhoneSpot Codex Remotion Master Guide

## Caption display color contract

- Screen-caption text uses one readable text color only.
- Do not infer or render orange or yellow inline caption highlights.
- Orange remains available for structural brand accents, CTA elements, headers, and infographics.
- Do not restore automatic inline caption coloring while adding another feature.

## Fixed caption font and independent visual rhythm

- Casual screen captions use one stable `72px` font size.
- Long narration is split conservatively at Korean grammar boundaries instead of shrinking caption text.
- Caption changes follow edge-tts word boundaries. Visual changes use an independent, calmer timeline.
- Source images normally stay visible for about `2.2~4.2s`.
- CTA visuals, illustrations, logos, mascots, and infographics remain static.
- Existing Korean, fixed CTA, TTS-caption lockstep, source-image-once, and illustration contracts remain active.

기준일: 2026-06-01

이 문서는 PhoneSpot 쇼츠 영상 출력기의 보존 기준입니다.  
새 기능을 추가하거나 오류를 수정하기 전에 반드시 먼저 읽습니다.

## 1. 역할과 경계

- Claude는 카드뉴스 원본을 생성합니다.
- Codex는 카드뉴스 결과물을 입력으로 받아 Remotion 쇼츠 영상을 만듭니다.
- Codex 작업은 `shorts/`와 `CODEX_VIDEO_DESK/` 안에서만 진행합니다.
- Claude 카드뉴스 실행 파일과 Claude 결과물의 기본 구조를 임의로 바꾸지 않습니다.
- 특정 슬러그 번호에만 맞춘 하드코딩은 금지합니다. 앞으로 생성될 모든 영상에 동일한 공통 로직을 적용합니다.

## 2. 폴더 구조

```text
C:\backup\phonespot_cardnews\
├─ cardnews\
│  ├─ images\<slug>\             카드뉴스 GPT 원본 이미지 1.png ~ 5.png
│  └─ output\<slug>\
│     ├─ captions.md             카드뉴스 본문, 채널별 업로드 문구, 영상 나레이션
│     ├─ shorts_script.json      영상 청크와 비주얼 매핑
│     └─ codex_illustration_requests.*
├─ shorts\                       Codex Remotion 엔진
│  ├─ src\
│  ├─ scripts\
│  ├─ config\
│  └─ public\                    렌더용 내부 캐시
└─ CODEX_VIDEO_DESK\             사용자가 매일 여는 작업 폴더
   ├─ RESULTS\                   최종 영상과 발행 문서
   ├─ TEMP\_raw\                 렌더 중간 파일
   └─ ILLUSTRATION_DROP\         재사용 일러스트 실제 저장소
```

`shorts/public/assets/illustrations/`는 Remotion 내부 캐시입니다.  
사용자가 관리하는 실제 일러스트 저장소는 `CODEX_VIDEO_DESK/ILLUSTRATION_DROP/`입니다.

## 3. 일상 실행

작업 시작 폴더:

`C:\backup\phonespot_cardnews\CODEX_VIDEO_DESK`

### 새 카드뉴스를 영상으로 만들 때

1. `01_PREPARE_GPT_PROMPTS.bat`
2. 목록에서 슬러그 선택
3. `LATEST_PROMPT.md`에 요청이 있으면 GPT Plus에서 일러스트 생성
4. 생성 이미지는 브라우저 다운로드 폴더에 저장
5. `02_IMPORT_DOWNLOADS_AND_RENDER.bat`
6. `RESULTS/<렌더 이름>/`에서 영상과 업로드 문구 확인

### 새 일러스트 없이 마지막 영상을 다시 만들 때

`03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat`

### 과거 슬러그를 직접 골라 다시 만들 때

`15_SELECT_AND_RENDER_EXISTING.bat`

## 4. 렌더 파이프라인

`shorts/run_codex_casual.bat`은 아래 순서를 유지합니다.

1. Node.js, Python, `edge-tts` 확인
2. `shorts_script.json` 준비
3. Codex 공통 품질 보정
4. 업로드된 신규 일러스트 적용
5. 문맥에 맞는 신규 일러스트 최대 3개 추천
6. 한국어, 고정 CTA, TTS-화면 청크 일치, 원본 이미지 중복 계약 검증
7. 일러스트 캐시 동기화와 렌더 자산 복사
8. TTS 생성과 단어 경계 기반 타이밍 검증
9. Remotion H.264 렌더
10. SNS용 MP4 마무리와 영상 품질 검사
11. 결과 폴더에 MP4와 발행 문서 생성

## 5. TTS와 화면 청크 계약

이 규칙은 가장 중요합니다.

- `captions.md`의 영상 나레이션을 TTS 우선 입력으로 사용합니다.
- 화면 청크는 해당 구간 TTS 원문을 순서대로 빠짐없이 나눈 결과입니다.
- 화면용 요약문을 별도로 만들지 않습니다.
- 마침표 숨김 외에는 단어를 추가, 삭제, 치환하지 않습니다.
- 문장 종결, 쉼표, 자연스러운 연결어미를 우선하여 화면을 넘깁니다.
- 숫자와 단위를 분리하지 않습니다. 예: `8,545억 원으로`
- 결합 표현을 함부로 분리하지 않습니다. 예: `V3 모바일`, `단축 URL`, `누르지 마시고`
- 도메인과 버전 내부의 점을 보존합니다. 예: `mygov.kr`, `iOS 26.6`
- 화면에서는 문장 끝의 마침표만 숨깁니다.
- 1초 미만으로 지나갈 가능성이 높은 짧은 고아 청크를 만들지 않습니다.

TTS 발음 사전은 음성 합성에만 적용합니다. 화면 자막의 원문을 바꾸지 않습니다.

## 6. 한국어 품질 계약

- 화면 청크를 단어 나열로 만들지 않습니다.
- 이미 자연스럽게 작성된 문장에 조사나 종결어미를 런타임에서 추측하여 덧붙이지 않습니다.
- `줄어듭니다입니다`, `합니다합니다`, `에 따르면에 따르면` 같은 표현은 렌더 전에 차단합니다.
- 잘못된 표현을 무조건 자동 치환하지 않습니다. 원문과 분할 규칙을 고치는 것이 우선입니다.
- 세 청크 이상 같은 종결어미가 반복되면 기계적인 문장 흐름으로 보고 점검합니다.

## 7. 고정 CTA

CTA는 채널 공통 계약입니다.

1. `휴대폰 구매할 땐?`
2. `지원금부터 무료로 조회해보세요`

마지막 비주얼은 PhoneSpot 로고입니다. 기사별 CTA로 임의 변경하지 않습니다.

## 8. 비주얼 계약

- 카드뉴스 GPT 원본 이미지 `1.png` ~ `5.png`를 문맥에 맞게 사용합니다.
- 원본 이미지는 한 영상 안에서 각각 최대 1회만 사용합니다.
- GPT 원본 이미지에만 노출 시간 비례 모션을 적용합니다.
- 노출 시간이 길면 천천히, 짧으면 빠르게 움직입니다.
- 확대, 좌우 이동, 우좌 이동 등 모션 패턴을 섞어 반복감을 줄입니다.
- CTA, 로고, 마스코트, 인포그래픽, 일러스트 자체는 고정합니다.
- 일러스트 배경에는 약한 빛 번짐, 진행 라인, 소프트 그리드, 종이 질감 정도만 허용합니다.
- 새 일러스트 요청은 기사 하나당 최대 3개입니다.
- 새 일러스트는 현재 기사에만 쓸 세부 묘사보다 재사용 가능한 의미를 우선합니다.
- 재사용 가능성은 그림을 단순하게 만들라는 뜻이 아닙니다. 완성도 높은 에디토리얼 일러스트를 요구합니다.

## 9. TTS 기준

- 기본 음성: `ko-KR-SunHiNeural`
- 기본 속도: `+42%`
- loudness normalization: 사용
- 발음사전과 단어 경계 기반 타이밍 기능은 기존 나레이션을 훼손하지 않는 범위에서만 사용합니다.

## 10. 출력 계약

- 영상: H.264, `yuv420p`, bt709, AAC, fast start
- 최종 위치: `CODEX_VIDEO_DESK/RESULTS/<렌더 이름>/`
- 중간 파일: `CODEX_VIDEO_DESK/TEMP/_raw/`
- 최종 MP4 파일명은 상위 결과 폴더명과 동일합니다.
- 결과 폴더에는 최소한 아래 파일을 둡니다.

```text
<렌더 이름>.mp4
captions.md
UPLOAD_COPY.txt
```

`UPLOAD_COPY.txt` 한 파일 안에 유튜브 쇼츠, 인스타그램 릴스, 틱톡 구역을 나누어 둡니다.

## 11. 현재 활성 검증

렌더 직전에 아래 계약을 차단 방식으로 검증합니다.

- 한국어 중복 표현
- 고정 CTA와 마지막 로고
- TTS, `caption_chunks`, `display_chunks` 내용 일치
- 청크, 화면 자막, 비주얼 개수 일치
- GPT 원본 이미지의 영상 내 중복 사용
- 참조 일러스트 파일 존재 여부
- 리스트 번호만 단독으로 남는 줄바꿈
- TTS 타이밍 가중치와 단어 경계 정보

## 12. 알려진 개선 후보

아래 항목은 현재 기준선에 포함되지 않은 후속 개선 후보입니다. 검증 없이 구현 완료로 간주하지 않습니다.

- `03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat` 실행 전 최신 슬러그명과 선택 시각 확인
- `08`, `10` TTS 실험 버튼의 외부 절대 경로 제거
- 실패한 렌더가 빈 `RESULTS` 폴더를 남기지 않도록 정리
- 일러스트 자동 선택의 의미 태그 강화
- 보조 검사인 `validate_polish.py`를 렌더 경계에 추가할지 검토

## 13. 금지 사항

- 특정 슬러그 번호만 고치는 하드코딩 금지
- 기능 하나를 추가하면서 기존 품질 계약을 제거하는 수정 금지
- 화면 청크를 TTS와 별도 요약문으로 되돌리는 수정 금지
- 모든 문장에 `입니다`를 자동 부착하는 수정 금지
- 한국어 오류를 무조건 치환하여 조용히 덮는 수정 금지
- CTA 임의 변경 금지
- GPT 원본 이미지 반복 사용 금지
- Claude 카드뉴스 실행 파일과 결과 구조 임의 변경 금지
- 결과 저장소를 다시 `out_codex` 또는 `upload_codex`로 분산하는 수정 금지

## 14. 변경 절차

새 기능은 아래 순서로 적용합니다.

1. 현재 기준 백업
2. 공통 로직으로 구현
3. Python 구문 검사
4. TypeScript 검사
5. 기존 영상 2개 이상 회귀 테스트
6. 신규 영상 1개 테스트
7. 결과가 나쁘면 즉시 롤백
8. 결과가 좋으면 이 문서와 패치 로그 갱신

기존 품질 계약을 삭제해야 하는 변경은 먼저 사용자에게 이유와 영향을 보고합니다.

## 15. 백업과 점검

백업:

`RUN_BACKUP_CODEX_CURRENT_BASELINE.bat`

회귀 점검:

`RUN_CODEX_REGRESSION_AUDIT.bat`

전체 기준 재설치:

`RUN_APPLY_CODEX_CURRENT_BASELINE.bat`

## 16. 읽기 순서

Codex 영상 작업을 시작할 때 아래 순서로 확인합니다.

1. `CODEX_MASTER_VIDEO_GUIDE.md`
2. `CODEX_BASELINE.md`
3. `README_FOR_CODEX.md`
4. `CODEX_MEMORY.md`는 과거 결정이 필요할 때만 확인
