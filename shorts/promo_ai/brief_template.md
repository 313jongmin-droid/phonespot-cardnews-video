# 실사 viral 제작 brief 템플릿 (패널 `ai_brief` 생성용)

> **용도**: 패널 실사AI 탭에서 주제 선택 → server.py가 이 템플릿의 `{{슬롯}}`을 `topic_pool.json` 값으로 치환 → `out_promo_ai/<slug>/_brief.md` 출력.
> **소비**: 제작 task(Claude)가 `_brief.md`를 읽고 `MEME_TO_VIRAL.md` + `WORKFLOW.md` "viral 후처리 룰"대로 제작.
> **치환 방식**: server.py는 LLM 없이 문자열 치환만(`{{HOOK}}` 등). 대본·컷 프롬프트 최종 다듬기는 Claude가 brief 받아 완성.

---

## 1. 주제 (패널이 topic_pool에서 자동 채움)
- slug: `{{SLUG}}`
- 주제: {{TOPIC}}
- 라인(line): {{LINE}}
- 후킹(hook): **{{HOOK}}**
- 골격(summary): {{SUMMARY}}
- 떡상점수(ttsan): {{TTSAN}}
- track: viral

## 2. 7비트 골격에 매핑 (Claude가 대본화)
`{{SUMMARY}}`의 흐름을 아래 7비트에 끼우고, `{{HOOK}}`을 B1 첫 1초로.

| 비트 | 역할 | 메모 |
|---|---|---|
| B1 | 후킹(1초) | {{HOOK}} — 어그로/공감, 브랜드 0 |
| B2 | 상황 | 문제 진입 |
| B3 | 빌드업(수법) | 호구 메커니즘 |
| B4 | 전환(트리거) | 친구/커뮤니티 한마디 |
| B5 | 반전 | 0원·정찰제(폰스팟 암시) |
| B6 | 현타 | 댓글 유발("너넨 얼마 주고 샀어?") |
| B7 | CTA 자막 | 브랜드 0.5초만 |

## 3. 컷 제작 지시 (고정 룰 — WORKFLOW 5·6 연동)
- **인물**: 글래머 모델 reference `media_id = 82abdf0f-ac89-4b3f-b614-1cb2ff650996` (머리~힙, 깊은 U넥, **입 다물고**=보이스오버, 몸매 유지)
- **각 컷**: 이미지 먼저(`nano_banana_pro` 2cr)로 글래머 확정 → 영상화(`kling3_0`, **`sound:"off"` 필수**)
- 배경 매장 통일 / `NO readable Korean text` / background blurred
- **B5 반전 = 002 `clerk_tablet.mp4` 재활용(0cr)**
- 컷 영문 프롬프트 패턴:
  `The same Korean woman with a glamorous figure in a phone store, <행동/표정>, lips closed (not speaking). Framing head to hip, deep U-neck fitted white top, figure visible, camera does NOT crop. Warm store light, background blurred, no readable Korean text.`

## 4. 나레이션
- 7비트 대본(★ 전문용어 X, 1인칭 썰톤) → TTS **Quinn** `voice_id=80914268-dfae-4f76-8306-36f2d55f58f8` → ffmpeg `atempo=1.35`
- 문장당 0.15cr

## 5. 자막 (WORKFLOW viral 룰)
- **나레이션 전문 일치** + **청크 순차 등장**(콩트 리듬)
- 효과는 **핵심 4곳만**: punch / glitch(혼란·외계어) / pop(반전) / shake(현타). 나머지 페이드. **슬라이드 금지·연속 금지**
- 강조어 오렌지 `{\c&H0B4BF7&}`. Alignment 5 중앙, 104~116pt

## 6. 영상 모션
- 켄번스 줌(후킹·반전 강, 나머지 약) + 컷 fade 0.12s + 엔딩 페이드. ★ `zoompan` 전 `fps=30` 먼저

## 7. 비용 예상
- 신규 컷 N개 × (이미지 2 + 영상 ~6) + 나레이션 6×0.15 ≈ **40~45cr** (재활용 시 25~30)
- `sound:"off"` 누락 시 컷당 +2cr 낭비

## 8. 산출 (WORKFLOW 7 위생)
- `out_promo_ai/<slug>/` : 최종 영상 `<slug>_v*_<날짜>.mp4` + `<slug>_captions.md`(틱톡·유튜브·인스타+사전승낙서)
- `concepts/INDEX.md` 표A·표B 1줄, status `published`
- 검증 프레임 `_chk*`/`_insp*`는 발행 전 삭제

---

## [예시] 004로 채운 brief (참고)
- slug: `004_viral_hogu` / 후킹: "나 어제 폰 바꾸다가 호구될 뻔한 썰 푼다" / 골격: 견적호구→친구→0원반전→현타
- 결과: Quinn 1.35x / 청크자막+효과4(호구punch·외계어glitch·공짜pop·너넨얼마shake) / 켄번스줌 / ~50cr(시행착오 포함, 정상 재현 시 ~40cr)
