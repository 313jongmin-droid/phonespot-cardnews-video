# TTS 싱크 & 이미지-텍스트 매칭 수정 가이드

작성: 2026-06-06 / 대상 버그: ① TTS·자막 싱크 어긋남 ② 이미지가 본문과 무관(거의 랜덤)

이 문서는 두 버그의 **근본 원인 / 수정 내용 / 다시 깨뜨리지 않기 위한 불변조건 / 검증법**을 기록합니다.
같은 실수가 반복되지 않도록, 관련 코드에는 이 파일을 가리키는 주석을 달아 두었습니다.

---

## 버그 1 — TTS·자막 싱크

### 근본 원인
- 섹션(hook/fact/cta) 단위 오디오↔영상은 정상입니다. `shorts/src/Root.tsx`가 실제 mp3 길이(`getAudioDurationInSeconds`)로 섹션 길이를 잡습니다.
- 문제는 **섹션 내부에서 자막 청크가 넘어가는 타이밍**이었습니다.
- `shorts/src/components/casual/chunkUtil.ts`의 `getChunkWindows`가 모든 청크에 **1.1초(33프레임)** 짜리 균등 바닥(`IDEAL_MIN_CHUNK_FRAMES`)을 먼저 깔고 남는 프레임만 발화 가중치로 나눴습니다.
- 청크가 많은 섹션일수록 균등 바닥이 타임라인의 70~80%를 차지 → 자막이 거의 등간격으로 넘어가 실제 발화와 어긋나고 누적 드리프트가 생겼습니다. (예: fact 9청크 13초 → 균등 76%)

### 수정 내용
- 균등 바닥을 **0.5초(`CAPTION_MIN_READABLE_FRAMES`)** 로 낮추고, 추가로 **그 바닥이 청크 평균 길이의 절반을 넘지 못하게** 제한했습니다.
- 효과: 어떤 청크 수에서도 **타임라인의 최소 50% 이상이 실제 발화 가중치를 따릅니다.** (fact 예시 기준 균등 76%→34%, 가중치 반영 24%→66%)
- 변경 위치: `chunkUtil.ts` 의 `CAPTION_MIN_READABLE_FRAMES` 정의와 `getChunkWindows` 내부 `minFrames` 계산.

### 불변조건 (다시 깨지 않게)
1. **자막 바닥(`CAPTION_MIN_READABLE_FRAMES`)을 평균 청크 길이 근처로 키우지 말 것.** 키우면 다시 등간격이 되어 싱크가 깨집니다. 0.4~0.6초 범위 유지.
2. `getChunkWindows`는 항상 `sum(windows.duration) == durFrames`, 연속(빈틈/겹침 없음)이어야 합니다.
3. 가중치(`tts_chunk_weights`)는 가능하면 **WordBoundary 기반(`word_boundary_snap`)** 이어야 정확합니다.

### WordBoundary 폴백 차단 (적용됨)
- 구버전 edge-tts면 `generate_tts.py`가 WordBoundary 없이 `character_weight_fallback`(글자수 비례)로 떨어져 싱크가 어긋납니다.
- 이제 `verify_tts_timing.py`가 이 상태를 **에러로 처리해 렌더를 막습니다**(종전엔 경고만 했음). 메시지에서 `pip install -U edge-tts`로 업그레이드하라고 안내합니다.
- 정말 그대로 진행해야 하면 `--allow-char-fallback` 옵션으로 경고로 낮출 수 있습니다.
- **게이트 확인됨:** `shorts/run_codex_casual.bat`가 Step 4에서 `verify_tts_timing.py`를 호출하고 바로 `if errorlevel 1 goto :fail`로 체크합니다(줄 93-94). 따라서 폴백이면 Step 5 Remotion 렌더 전에 실제로 중단됩니다.
- 참고: 같은 배치 Step 2(줄 59)가 매 실행마다 `pip install --upgrade edge-tts`를 돌려 edge-tts를 최신화합니다. 그래서 인터넷 되는 PC면 폴백이 잘 안 납니다. 이 에러 게이트는 **그 업그레이드가 실패하는 PC(오프라인/망분리)** 를 잡는 안전망입니다.
- 모든 PC의 edge-tts 버전을 최신으로 통일하는 것이 근본책입니다. (글자수 폴백도 이번 버그1 수정으로 50%+ 비중이 반영돼 종전보단 낫지만, WordBoundary가 정답입니다.)
- 백업: `shorts/scripts/verify_tts_timing.py.bak_wordboundary_strict_*`
- `loudnorm` 재인코딩은 윈도우 계산(정규화 전) 이후라 미세 오차가 남습니다. 큰 문제는 아니나 인지해 둘 것.

---

## 버그 2 — 이미지-텍스트 매칭(거의 랜덤)

### 근본 원인
`shorts/scripts/codex_semantic_visual_match.py`:
1. **소스 이미지는 영상 1편당 5장(1~5.png)뿐**인데 청크는 ~30개 → 나머지는 전부 재사용 일러스트 라이브러리로 채워야 함.
2. 매칭이 **부분 문자열 일치**(키워드가 캡션에 그대로 있어야 점수)이고 **임계값이 높아(18/14)** 대부분 청크가 미달 → fallback.
3. 기존 fallback이 점수 0이어도 **라이브러리에서 아무거나** 골랐음 → 피싱 대본에 `battery_overheat`/`appliance`/`foldable` 같은 무관 일러스트가 박힘.
4. 소스 이미지 설명(prompt.md 본문)이 **영어**, 캡션은 **한국어** → 어휘가 안 겹쳐 이미지가 의미로는 거의 안 붙음.

### 수정 내용
- 임계값 하향: `MIN_IMAGE_SCORE 18→16`, `MIN_ILLUST_SCORE 14→12` (진짜 단일 강키워드 매칭이 채택되도록).
- **fallback 정책 교체** (핵심): 확신 매칭이 없을 때
  1) 이번 기사용 **소스 이미지를 우선**(현재 것 유지 또는 미사용 소스 이미지),
  2) 그다음 **마스코트 보존**(감정 포즈라 어디든 안전),
  3) 둘 다 없으면 **주제 중립 필러**(`NEUTRAL_FILLERS` = smartphone/newspaper/microphone/shield/meeting_room/forecast)에서 선택.
  → 더 이상 무관한 라이브러리 일러스트를 던지지 않습니다.
- `pick_neutral()` 추가: 라이브러리에 실제 존재(png)하는 중립 일러스트만, 이번 영상에서 안 쓴 것 우선.

### 불변조건
1. **무매칭 fallback에서 임계값 미만의 라이브러리 일러스트를 그대로 채택하지 말 것.** 반드시 소스 이미지 → 마스코트 → 중립 필러 순으로.
2. `NEUTRAL_FILLERS`의 항목은 `shorts/public/assets/illustrations/`에 실제 png가 있어야 효과가 있습니다. 없으면 다른 중립 이미지로 교체.
3. `_codex_manual_visuals`(수동 지정)는 절대 건드리지 않습니다(기존 정책 유지).

### 남은 구조적 한계 (코드만으로는 못 고침 — 자산/프롬프트 작업 필요)
- **소스 이미지를 5장→더 늘리면** 무관 매칭이 근본적으로 줄어듭니다.
- **태그 DB의 일러스트 중 png가 없는 항목**(예: `emergency_account_freeze`, `smishing_fake_link` 등 스카우트 자산)은 `available`에서 빠져 매칭 후보가 못 됩니다. 의미상 맞는데도 안 붙으면 우선 **png를 라이브러리에 추가**하세요.
- prompt.md 이미지 설명에 **한국어 키워드**를 함께 적으면 이미지 매칭률이 올라갑니다(현재 본문이 영어라 매칭 0이 많음).
- 더 근본적으로는 부분일치 대신 **의미 임베딩 매칭**으로 가면 가장 좋지만 별도 작업입니다.

---

## 검증 체크리스트 (수정 후 / 회귀 점검)

1. 자막 분배 단위검증(순수 함수): 청크 수별로 `getChunkWindows`의 균등 비중이 50% 이하, 합=durFrames, 연속성 OK.
2. 매칭 단위검증: 무매칭 시 결과에 무관 일러스트(battery/foldable/appliance 등) 없음 + 마스코트 보존 + 중립 필러 사용. 강한 매칭(≥12)은 정상 채택.
3. 실제 1편 렌더해서 육안 확인: 말과 자막이 같이 넘어가는지, 이미지가 본문과 어긋나지 않는지.
4. `RESULTS/<slug>/codex_semantic_visual_match_report.md`의 `약한 매칭` 목록이 줄었는지 확인.

## 백업 / 복구
수정 전 원본은 같은 폴더의 타임스탬프 백업으로 보존됩니다.
- `shorts/src/components/casual/chunkUtil.ts.bak_caption_sync_fix_*`
- `shorts/scripts/codex_semantic_visual_match.py.bak_visual_fallback_fix_*`
문제 시 해당 백업으로 되돌리면 됩니다.


---

## 이미지 의미매칭 로드맵 (임베딩 기반, 진행 중)

### 목표
콘텐츠마다 1회용 그림을 새로 만드는 대신, **범용 개념 일러스트**를 쌓아 라이브러리만으로
대부분을 커버(생성 요청이 0에 수렴)하고 중복 느낌도 제거한다.

### 토대 (적용됨)
- `shorts/scripts/codex_illust_embed.py` — **무료 로컬 임베딩 엔진**.
  - 기본 모델: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (fastembed/ONNX, 한국어 포함, ~220MB, CPU).
  - 라이브러리 개념 임베딩을 디스크 캐시(`shorts/codex/illust_embed_cache.json`), 새 개념만 계산.
  - API: `rank(text)`(의미 매칭), `cover(concept)`(중복 판정), `similarity(a,b)`.
  - **graceful 폴백:** 모델/패키지 없으면 기존 lexical 점수로 자동 폴백 → 파이프라인 안 깨짐.
- 설치(PC당 1회, 온라인): `shorts/SETUP_EMBED.bat` (첫 실행 후 오프라인 동작).
- 미리보기(읽기전용, 라이브 매처 미수정): `python scripts/codex_illust_match_preview.py <slug>`
  → 청크별 [현재] vs [임베딩 제안]을 비교 출력.

### 핵심 불변조건 (1회용 폭증 방지 = 수렴 조건)
1. **개념 추상화:** 일러스트는 "그 기사 전용 장면"이 아니라 **재사용 가능한 개념**으로 만든다.
   날짜·금액·브랜드·모델명·인물 등 1회용 디테일 금지(`codex_illustration_scout.py`의 STYLE 유지).
2. **생성 전 의미 중복제거:** 새 일러스트를 요청하기 전에 `cover(concept)`로 기존 라이브러리와
   비교해 임계 이상 유사하면 **재사용(생성 안 함)**. 이게 라이브러리 크기를 수렴시킨다.
3. 모델 미사용 상태에서도 `rank()`는 lexical로 동작해야 한다(안전).

### 1단계 — 개념 발굴형 스카우트 (적용됨)
- `shorts/scripts/codex_concept_scout.py` (새 파일, 라이브 파이프라인 미수정).
- 동작: 라이브러리에 마땅한 그림이 없는 **갭 청크**를 찾아 →
  청크에서 **1회용 디테일(숫자/날짜/금액/모델명/브랜드)을 제거**해 범용 개념 키워드를 추출 →
  `codex_illust_embed.cover()`로 **기존 라이브러리와 의미 중복제거**(충분히 비슷하면 재사용, 생성 안 함) →
  **신규 개념만** 태그 DB에 등록(available=false)하고 재사용 가능한 GPT 프롬프트를 만든다.
- 개념 ID는 키워드 해시라, **영상이 달라도 같은 개념이면 같은 ID** → 자연 중복제거 + 수렴.
- 상한: `MAX_NEW_CONCEPTS`(기본 5)로 영상당 신규 개념 폭증 방지.
- 사용: `python scripts/codex_concept_scout.py <slug>` (미리보기는 `--dry-run`).
- 검증: 갭탐지/1회용 제거/중복제거 재사용/상한/DB 영속(라운드트립)/요청파일 생성 단위테스트 통과.

#### (함께 고친 잠복 버그) DB 영속성
- `codex_illustration_db.py`의 `write_json`/`write_report`가 파일 끝에 **literal `\n`(역슬래시+n)**을
  붙여, 같은 파일을 `read_json`이 못 읽고 매번 SEED 기본값으로 폴백하고 있었다.
  (= 태그 DB·사용기록이 저장돼도 되읽기 실패 → 사실상 영속 안 됨)
- 이를 진짜 줄바꿈(`\n`)으로 고쳐 **DB·기록이 정상 저장/로드**되게 했다. 이게 안 고쳐지면 개념이 안 쌓인다.
- 백업: `shorts/scripts/codex_illustration_db.py.bak_newline_fix_*`

### 2단계 — 패널 버튼 연결 (적용됨)
- 패널 **"1. 영상용 프롬프트 준비"** 버튼 → server.py `video_prepare` → `codex_prepare_illustrations.py` 실행.
- 그 준비 체인 끝(workbench 다음)에 `codex_concept_scout.py`를 **비차단**으로 추가했다(`run_optional`).
  실패해도 준비는 계속되고, 모델이 없으면 lexical 폴백으로 동작한다.
- 개념 요청은 패널이 읽는 `codex_illustration_requests.json/.md` 에 **멱등 병합**된다
  (`source=concept_scout` 마커로 기존 일러스트 스카우트 요청은 보존, 개념 요청만 교체).
  → 버튼 1 후 패널의 일러스트 요청 화면에 기존 + 개념 요청이 함께 뜬다.
- **server.py / 패널 / run_codex_casual.bat 은 건드리지 않았다.** 데이터 파일 병합 + prepare 체인 한 줄만 추가.
- 백업: `shorts/scripts/codex_prepare_illustrations.py.bak_concept_scout_*`
- 검증: 기존 요청 보존 + 개념 요청 병합 + md 마커 + 멱등(2회 실행 무중복) 단위테스트 통과.

### 다음 단계 (미적용)
- **3단계:** 렌더 매칭(`codex_semantic_visual_match.py`)의 lexical 점수를 `rank()` 임베딩으로 교체.
  (라이브 매처 수정이라 백업 후 원자적으로, 폴백 유지)
- 자산 루프: 등록된 신규 개념 png를 사람이 GPT로 그려 `shorts/public/assets/illustrations/`에 넣으면
  available로 승격되어 다음 영상부터 매칭 후보가 된다.
