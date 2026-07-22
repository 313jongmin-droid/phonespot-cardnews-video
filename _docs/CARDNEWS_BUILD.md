# 카드뉴스 1건 빌드 전체 워크플로 (★ 2026-06-04 기준)

> 카드뉴스 1건을 신규 수집부터 SNS 발행 직전까지 어떤 순서로 작업하는지의 단일 진입 가이드.
> 모든 룰의 출처는 `_docs/INSTRUCTIONS_CARDNEWS.md` + `cardnews/templates/caption_template.md`.

---

## 0. 사이클 한눈에

```
[STEP A] 신규 수집 (WebSearch 4 라인 병렬)
   ↓
[STEP B] 풀 후보 표 → 텔레그램 outbox 자동 송신
   ↓
[STEP C] 사장님 숫자 회신 (예: "10", "1+17+10")
   ↓
[STEP D] articles JSON + prompt.md 작성 (각 선택 건마다)
   ↓
[STEP E] _state/outbox/<NNN>_ready.txt 떨굼 → 폰 알림
   ↓
[STEP F] 사장님이 GPT/Gemini에 prompt.md 던져 1~5.png 생성
   ↓
[STEP G] images/<slug>/ 에 1~5.png 업로드
   ↓
[STEP H] webui 또는 run_pngs.bat 으로 NNN 렌더 → output/<slug>/ 18 JPG + captions.md
   ↓
[STEP I] 사장님이 captions.md 5채널 + 영상 나레이션 + JPG 들고 SNS 업로드
```

---

## STEP A — 신규 수집

### A-1. 사전 점검
- 오늘 날짜 확인 → D-7 = (오늘 - 7일)
- 기존 발행 슬러그 전체 (001~NNN) 토픽 목록 추출 (중복 회피용)
- 다음 번호 = NNN + 1

### A-2. 4 라인 병렬 WebSearch
- `news` (D-7 strict) / `scam` (D-7 우선, 정책 D-14) / `tip` (D-7) / `qa` (시점 무관)
- 매뉴얼 회피 키워드 (통합요금제·요금 인하·알뜰폰 등) 자동 인지
- 매장 정합 = 고가 단말 + 고가 요금제 친화

### A-3. 후보 풀 표 생성
- **라인별 가능한 모든 후보 노출** (라인당 최소 5건). 클로드가 추리지 X
- 통합 번호 (라인 무관 1, 2, 3... 연속). 같은 숫자 중복 ❌
- 각 후보 라벨: `발행일 / D-N / 매장정합 / 비고 (중복·회피·시즌)`
- 회피·중복도 숨기지 말고 라벨 부착
- 정직한 한계 (D-7 통과 0건 등) 명시

### A-4. 텔레그램 자동 송신
- `_state/outbox/<YYYY-MM-DD>_collect_numbered.txt` 떨굼
- listener 살아있으면 ≤30초 내 폰 도착

---

## STEP B/C — 사장님 회신 받기

- 회신 형식: 숫자만 (예: `10`, `10+27`, `1,3,7`)
- 회신 수신 즉시 STEP D 진행
- 라인 다양성 권고는 1줄만 (강요 X)

---

## STEP D — articles JSON + prompt.md 작성

### D-1. 슬러그 부여
- 형식: `NNN_<type>_<topic_kebab>` (예: `014_scam_voicephishing_zero_relief`)
- NNN = 3자리 (001부터 연속, 발행 시점 결정)

### D-2. JSON 필드 (필수)

```json
{
  "slug": "NNN_<type>_<topic>",
  "content_type": "news|scam|tip|qa",
  "title": "[Hook]·핵심 1·매장 후크 묶음",
  "publication_date": "YYYY.MM.DD",
  "source_line": "출처: [매체 1] + [매체 2] + 폰스팟 광교점 자료",
  "cards": [ ... 6장 ... ],
  "captions_md": "...5채널 통째...",
  "narration_md": "...60초 나레이션..."
}
```

### D-3. 카드 6장 구조

| 카드 # | 역할 | 헤드라인 패턴 | body 길이 |
|---|---|---|---|
| 1 | 후크 | 질문·놀라움·시즌 | 100~140자 |
| 2 | 핵심 사실 1 | 출시일·통계·정의 | 100~140자 |
| 3 | 핵심 사실 2 | 수법·기능·예시 | 100~140자 |
| 4 | 체크/차단/기능 N | "받을 N가지" 등 | 100~140자 |
| 5 | 행동·신청 채널 | 신고·신청·골든타임 | 100~140자 |
| 6 | 매장 CTA | "광교점 1:1 지원" | 100~140자 (source = `Phonespot 광교점`) |

헤드라인 형식: `[키워드 1줄]\n<span class="hl">강조</span> [키워드 2줄]`
- `\n` = 줄바꿈 / `<span class="hl">` = 오렌지 (#F74B0B) 강조

### D-4. captions_md (5채널) + narration_md

**상세 룰은 `cardnews/templates/caption_template.md` 가 단일 소스.** 핵심만:

- 5채널: 블로그 (장문 SEO) / 스레드 (단문 질문) / 인스타 (해시태그 풍부) / 유튜브 (구조화 SEO) / 틱톡 (단문 행동)
- 5채널 **첫 줄 후킹 타입 모두 다르게**
- 모든 채널 본문에 `{LITTLY}` + 최하단 `[사전승낙서] {PRECON_URL}`
- 인스타 해시태그 15~20개 (브랜드+라인+지역+시즌)
- narration_md = 60초 분량 800~1500자 / 존댓말 / **URL·이모지·해시태그 ❌** (음성 합성용)
- narration_md 는 run_pngs 시 captions.md 채널 6 으로 자동 append

### D-5. prompt.md (이미지 생성용)

위치: `cardnews/images/<slug>/prompt.md`

표준 헤더 (★ 마커 + 공통 룰):

```
■ <slug>/1-5.png — 5장 일괄 프롬프트

★ 각각 별개 이미지 파일로 생성 ★

공통 룰 (5장 모두 적용):
1080x1080, photorealistic editorial. Bright airy mood, light cream / warm white / pale beige background. No black background, no dramatic spotlight, no deep shadow. No text on screens, no brand logos, no real human faces. Numbers/dates blurred. Phonespot orange #F74B0B accent if subtle.
각 이미지는 위 룰을 따르되, 색감·소품·구도는 카드별 독립. 시리즈 통일 톤 지시 금지.

— 1.png — <카드 1 토픽>
<영문 묘사 1~3 문장>

— 2.png — <카드 2 토픽>
<영문 묘사>

... (5장)
```

- 카드 6 (매장 CTA) 은 이미지 X (logo 또는 매장 사진 사용)
- 영문 묘사는 photorealistic editorial 톤 + 매장 정합 (smartphone·계산기·shield 같은 단순 silhouette)

### D-6. JSON 안전 박기

- **Write 도구로 전체 JSON 한 번에 박기** (Edit 으로 큰 필드 부분 수정 ❌)
- captions_md·narration_md 같은 큰 멀티라인은 `\n` 인라인 (raw 줄바꿈 X)
- 박은 직후 webui 미리보기 또는 json.load 검증 권장

---

## STEP D.5 — 카드 미리보기 게이트 (★2026-07-22 종민 필수)

사장님이 발행 번호를 지정하면 **JSON을 바로 생성하지 말고**, 각 주제의 **6카드 흐름(헤드라인 + 한 줄 요지)**을 먼저 채팅에 제시한다. 사장님이 "생성"·"OK" 하거나 수정 반영 후에만 STEP A~C(JSON+prompt.md)로 넘어간다.

- 형식: `1. 후크 — "…" / 2. … / 6. 매장 — 폰스팟 …` (카드별 1줄).
- 목적: 무슨 내용으로 만들지 사장님이 먼저 확인 → 헛발행 방지.
- 예외: 사장님이 "미리보기 없이 바로 만들어"라고 하면 생략.

---

## STEP E — 텔레그램 알림 (작성 완료) ★무조건 자동

- `_state/outbox/<NNN>_ready.txt` 떨굼 — **발행 끝나면 묻지 말고 항상 생성**(종민 standing 허락 2026-06-23). "쏠까요?" 확인 ❌
- 내용: 작성 완료 통지 + 다음 단계 안내
- listener 자동 송신 (listener 꺼져 있으면 큐에 적재 → 켜질 때 전송. 미전송 누적이면 listener 점검 안내)

---

## STEP F — 이미지 생성 (사장님)

- GPT / Gemini 에 prompt.md 내용 던져 1~5.png 생성
- 각 카드별 독립 호출 권장 (시리즈 통일 톤 자동 회피)
- 1080x1080 PNG, 매장 톤 (cream/orange) 유지

---

## STEP G — 이미지 업로드

- `cardnews/images/<slug>/` 에 `1.png`, `2.png`, `3.png`, `4.png`, `5.png` 배치
- 파일명 정확히 일치 (다른 명 ❌)

---

## STEP H — 렌더

### H-1. webui 방식

```
cd cardnews
py -3 -u webui/app.py
# 브라우저 → localhost:5000 → 슬러그 선택 → "렌더" 클릭
```

- 실시간 로그 (SSE)
- 결과 페이지에서 18 JPG 그리드 + ZIP 다운로드

### H-2. CLI 방식

```
cd cardnews
run_pngs.bat
# 셀렉트 → NNN 입력 (여러 개 가능)
```

### H-3. 산출물

- `cardnews/output/<slug>/`
  - `card_1.jpg` ~ `card_6.jpg` × 3 사이즈 = 18 JPG
  - `captions.md` (5채널 + 채널 6 narration 자동 append)
  - `manifest.json` (메타)

### H-4. 자동 검증

run_pngs.bat 은 다음 자동 검증 후 실패 시 중단:
- prompt.md 존재
- 1~5.png 모두 존재
- captions_md + cards 필드 존재
- 18 JPG 사이즈 최소 30KB 이상

---

## STEP I — 발행 (SNS 업로드)

- output/<slug>/captions.md 에서 채널별 캡션 복사
- 18 JPG 중 1080 사이즈 5장 (card_1~5) = 인스타·블로그·스레드용
- 720 = 틱톡·유튜브 썸네일
- narration_md = 영상 빌드용 (shorts 빠지면 별도 task)

발행 후:
- 시트(관리대장)에 슬러그·채널별 조회수 입력
- 다음 사이클 콘텐츠 가이드 메모 (`cardnews/_state/content_guide.md`) 업데이트

---

## 자가 검증 (★ 발행 직전)

- [ ] 5채널 첫 줄 모두 다른 후킹
- [ ] 모든 채널 최하단 사전승낙서
- [ ] 카드 6 source = `Phonespot 광교점`
- [ ] 회피 키워드 0건 / 안양 0건
- [ ] narration_md URL·이모지 0건
- [ ] 18 JPG 사이즈 + captions.md 둘 다 생성됨
- [ ] 슬러그 NNN 다음 발행과 충돌 X

---

## 이력 (이 가이드 자체)

- 2026-06-04: 신설. 014~018 사이클 정착 패턴 종합.
