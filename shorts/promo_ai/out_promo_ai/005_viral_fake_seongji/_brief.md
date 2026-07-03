# 실사 viral 제작 brief — 005_viral_fake_seongji

> ⚙ 패널 `ai_brief`가 `brief_template.md` + `topic_pool.json`(id C01)으로 자동 생성한 작업지시서 (시뮬레이션).
> 제작 task(Claude)는 이 brief를 읽고 `MEME_TO_VIRAL.md` + `WORKFLOW.md` "viral 후처리 룰"대로 제작.

---

## 1. 주제 (topic_pool C01)
- slug: `005_viral_fake_seongji`
- 주제: 가짜 성지 구분법
- 라인(line): meme
- 후킹(hook): **이런 매장은 100% 호구됩니다**
- 골격(summary): 가격 공개 거부·방문 유도 등 가짜성지 신호 → 정찰제 매장
- 떡상점수(ttsan): ★인스타릴스 208만 실증·호구meme 최고
- track: viral

## 2. 7비트 골격 매핑 (Claude가 대본화 — summary 흐름 끼움)

| 비트 | 역할 | 이 주제 적용(초안) |
|---|---|---|
| B1 | 후킹(1초) | "이런 매장은 100% 호구됩니다" — 경계형 어그로 |
| B2 | 상황 | 폰 사러 가서 가격 물었더니… |
| B3 | 빌드업(수법) | 가짜성지 신호 ①가격 공개 거부 ②"오시면 알려드려요" 방문 유도 |
| B4 | 전환(트리거) | 친구/댓글 "그거 호구 매장이야" |
| B5 | 반전 | 진짜 성지 = 가격 딱 공개·정찰제(폰스팟) |
| B6 | 현타+댓글유발 | "나 그 매장 갈 뻔… 너넨 가격 물어보면 알려줘?" |
| B7 | CTA 자막 | 가격 공개하는 곳, 폰스팟 |

## 3. 컷 제작 지시 (고정 룰)
- 인물: 글래머 모델 `media_id=82abdf0f-ac89-4b3f-b614-1cb2ff650996` (머리~힙·깊은 U넥·입 다물고 보이스오버·몸매 유지)
- 각 컷: 이미지 먼저(`nano_banana_pro` 2cr) 글래머 확정 → 영상화(`kling3_0`, `sound:"off"`)
- 배경 매장 통일 / NO readable Korean text / background blurred
- B5 반전 = 002 `clerk_tablet.mp4` 재활용 가능(0cr)
- 컷 영문 프롬프트 패턴: `The same Korean woman with a glamorous figure in a phone store, <행동/표정>, lips closed. Framing head to hip, deep U-neck fitted white top, figure visible, camera does NOT crop. Warm store light, background blurred, no readable Korean text.`

## 4. 나레이션
- 7비트 대본(전문용어 X·1인칭 썰톤) → TTS Quinn `80914268-dfae-4f76-8306-36f2d55f58f8` → ffmpeg `atempo=1.35` / 문장당 0.15cr

## 5. 자막 (WORKFLOW viral 룰)
- 나레이션 전문 일치 + 청크 순차(콩트 리듬)
- 효과 핵심 4곳만(punch/glitch/pop/shake), 나머지 페이드. 슬라이드 금지·연속 금지. 강조어 오렌지. Alignment 5 중앙 104~116pt

## 6. 영상 모션
- 켄번스 줌(후킹·반전 강) + 컷 fade 0.12s + 엔딩 페이드. zoompan 전 fps=30

## 7. 비용 예상
- 신규 컷 ~5개 × (이미지 2 + 영상 6) + 나레이션 ~6×0.15 ≈ **40~45cr** (clerk·배경 재활용 시 30 이하). sound off 필수

## 8. 산출 (WORKFLOW 7 위생)
- `out_promo_ai/005_viral_fake_seongji/` : 영상 `005_viral_fake_seongji_v*_<날짜>.mp4` + `005_viral_fake_seongji_captions.md`
- `concepts/INDEX.md` 표A·표B 1줄, status `published`. 검증 프레임 `_chk*`/`_insp*`는 발행 전 삭제
