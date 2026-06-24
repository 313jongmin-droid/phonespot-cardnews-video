# meme → 실사 viral 구현 가이드 (promo_ai)

> **주제는 클로드(`_docs/TOPIC_ENGINE.md`)가 생성, 구현은 이 가이드대로.** meme 라인 주제/카드뉴스를 promo_ai 실사 viral 영상으로 변환하는 실행 정본.
> 기반: `WORKFLOW.md`(실측 cost·자막·CDN) + viral 7비트 골격(README §viral). 이 문서는 **meme 전용 변환 규칙**만 추가한다.
> 전략·비용·리스크 근거 = `기획안_meme_실사영상_분담`(검토 문서). 트랙 분담 = `TOPIC_ENGINE.md §4`.

---

## 0. 언제 이 가이드를 쓰나

- 클로드 주제 풀에서 **라인=meme, 추천트랙=실사 viral**로 태깅된 주제.
- 명령: "N번 실사" / "N번 viral" (주제 번호 + 실사 지정).
- 정보형(news/scam/qa/tip/pick)은 **이 가이드 대상 아님** → 카드/카드뉴스영상.

---

## 1. 골격 매핑 — meme 카드뉴스 6장 → viral 7비트

meme 카드뉴스(있으면)나 meme 주제를 아래 7비트로 재구성한다. **정보 나열이 아니라 1인칭 썰·반말·공감**이 viral 핵심(ad와 반대, README viral 표).

| viral 비트 | 길이 | meme 카드 대응 | 역할 |
|---|---|---|---|
| ① 후킹 | ~1초 | 카드1 (후크) | "이 말 들으면 호구" 류, 스크롤 멈춤 |
| ② 상황 | 2~3초 | 카드2 | 1인칭 썰 ("나도 그랬지") |
| ③ 빌드업 | 3~4초 | 카드2~3 (수법) | 함정·수법을 보여줌 |
| ④ 전환 | 2초 | 카드4 (진실) | "근데 계산해보니…" 트리거 |
| ⑤ 반전 | 3초 | 카드4~5 | 충격 사실(총액·숨은비용) |
| ⑥ 현타 | 2초 | 카드5 | "호구였네" 감정 |
| ⑦ 댓글유발 + 브랜드 | 2초 | 카드6 | 질문("너넨 얼마야?") + 폰스팟 자막 1줄 |

> **브랜드는 끝 1줄만**(viral은 광고 냄새 나면 조회수 죽음). 강한 CTA·반복 노출은 ad 트랙에서.

**예시 — 033 할부의 함정:**
① "한 달에 이것밖에 안 해요? 나도 그 말 믿었어" → ② 48개월 할부 계약 → ③ 월 납부금만 싸 보임 → ④ 총액 계산해보니 → ⑤ 이자까지 수십만원 더 → ⑥ "이게 호구였네" → ⑦ "너넨 몇 개월 할부야?" + `정찰제 폰스팟` 자막.

---

## 2. 제작 단계 (WORKFLOW.md 실측 준수)

### Step 1 — 컨셉 기획서
`shorts/promo_ai/concepts/NNN_viral_<theme>.md` 작성. 7비트별 컷 분할 + shot별 {비주얼 / 카메라 / 자막(한글) / SFX / Kling 영문 prompt}.
- 슬러그 = `NNN_viral_<theme>` (예 `005_viral_halbu_hogu`).

### Step 2 — 비주얼 선확정 (★크레딧 절약 핵심)
인물·의상·톤·구도는 **`generate_image`(nano_banana_pro = 2cr)로 먼저 이미지 확정.** 마음에 들 때까지 이미지만 재생성(2cr씩). **컨셉 확인용으로 영상(6cr) 재생성 ❌.**

### Step 3 — preflight cost
각 shot `generate_video(..., get_cost:True)`로 cost 합산 → 종민 보고.

### Step 4 — 영상화
확정 이미지를 `start_image`(medias role)로 → `kling3_0`(std, 무음 `sound:off`, 9:16). start_image로 **컷 간 인물 일관성** 확보. **호출 직후 `balance` 조회 → 잔액 종민 보고**(WORKFLOW §2 룰).

### Step 5 — 한글 자막 (ffmpeg .ass burn)
영상 in-image 한글은 깨짐 → 프롬프트에 한글 X. **정확해야 하는 자막(후킹·반전 수치·댓글유발·브랜드)은 `.ass`로 burn.** 폰트 `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc`. 배경 한글은 `background signage blurred, no readable Korean text`.

### Step 6 — 합치기·SFX·CTA
ffmpeg 정규화(1080x1920/30fps) → concat → SFX/BGM(종민 수급) → CTA 엔딩(브랜드 오렌지 #F74B0B). bash 45초 타임아웃 → 단계 쪼개 실행, `-preset veryfast`.

### Step 7 — CDN 다운로드 (수동 개입)
Higgsfield cloudfront = 샌드박스 403 → **종민이 위젯/`rawUrl`에서 다운로드해 전달**해야 ffmpeg 가능.

### Step 8 — 결과·캡션·인덱스
`out_promo_ai/<slug>/`에 영상(타임스탬프) + `<slug>_captions.md`(틱톡·유튜브·인스타, caption_template + 사전승낙서 `_brand.json precon_url`). `concepts/INDEX.md` 1줄 추가.

---

## 3. 안전 룰 (meme 풍자 특성상 필수)

1. **실제 얼굴 금지** — Soul Character/추상 연출. 실존 인물 X.
2. **경쟁사 실명·비방 금지** — "다른 매장" 정도로 추상화, 상황으로 풍자.
3. **배경 텍스트 흐리게** — 간판·견적서 깨져도 안 보이게 blur.
4. **핵심 수치는 자막** — 실사만으론 정보 약함(meme도 숫자가 핵심). 할부율·체크리스트 등은 .ass 자막 병행.

---

## 4. 비용·양산 룰

- STARTER $19/270cr ≈ 월 18편. meme = **주 1~2건**(월 4~8편) 권장 → 여유.
- 편당 ~16cr(11초) ≈ $1.2. 이미지 선확정으로 재생성 낭비 차단.
- **호출마다 balance 보고**(종민 룰). 결제는 자동 ❌, 막히면 `balance`+`show_plans_and_credits` 보고.

---

## 5. 검증 (발행 전)

- 영상 1080x1920 / 20~60초 / 오디오 트랙 유무
- 자막 가독성(중앙·외곽선), 브랜드 끝 1줄, 댓글유발 질문 존재
- 안전 룰 4종 통과(얼굴·비방·배경텍스트·핵심자막)
- 파일럿 단계: 같은 주제 카드뉴스영상과 성과 A/B → 유튜브_인사이트 교차

---

## 6. 트랙 경계 재확인

| 트랙 | 용도 | 비용 | 비고 |
|---|---|---|---|
| 카드뉴스영상(shorts) | news·scam·qa·tip·pick 정보형 | 무료 | 정보 정확·양산 |
| **실사 viral(promo_ai)** | **meme 후킹·반전·풍자** | 크레딧 | 이 가이드 |
| 실사 ad(promo_ai) | 매장 홍보·전환 | 크레딧 | README ad 골격 |
| 타이포(promo) | 데이터·정보 강조 광고 | 무료 | **유지**(2026-06-23, 폐기 안 함) |

---

## 이력
- 2026-06-23: 신설. meme→실사 viral 변환 정본(7비트 매핑·8단계·안전·비용·검증). 타이포(promo) 유지 확정. 주제 생성 분리 = `TOPIC_ENGINE.md`.
