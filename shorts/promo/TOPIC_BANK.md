# 폰스팟 promo 토픽 뱅크 (테스트 초안)

> 종민님이 주신 강점(가격 투명성 · 비대면 견적 · 즉시조회→그대로 개통 · 정찰제 vs 상담유도 · 광교점)으로 만든 초안.
> 숫자·경쟁사 지목 없이 규제-안전 일반 표현. 각 파일은 `promo/<slug>.json`. 브랜드값(카카오·litt·위치)은 비워뒀고 렌더 시 `_brand.json`에서 자동 병합.

| # | slug | 앵글 | 한 줄 |
|---|------|------|------|
| 1 | promo_jeongchalje | 정찰제 | 세상 모든 건 가격표, 휴대폰만 상담 → 즉시조회 |
| 2 | promo_bidaemyeon | 비대면 견적 | 매장 안 가도 집에서 비대면 조회 |
| 3 | promo_hogaeng | 호갱 방지 | 공개해놔도 막상 가면 말 바뀜 → 그대로 |
| 4 | promo_geugadaero | 조회가=개통가 | 조회한 가격, 즉시 그대로 개통 |
| 5 | promo_nosangdam | 상담 강요 없음 | "일단 오세요" 없이 가격부터 |
| 6 | promo_gwanggyo | 광교 동네 | 광교호수공원 옆, 정찰제 |

## 한 번에 렌더 (PC)
```cmd
run_promo_batch.bat showcase
```
→ `promo/*.json` 6편 전부를 showcase 프리셋으로 → `out/promo/<slug>_showcase.mp4`.
프리셋 바꾸려면: `run_promo_batch.bat punchy` (showcase/punchy/calm/data).
한 편만: `run_promo.bat` → slug는 현재 `promo_jeongchalje` 고정(다른 slug는 배치 사용 권장).

## 주의(규제)
- 전부 숫자·금액 없음. 게시 전 실제 수치 넣을 땐 근거 필수.
- "호갱·허위매물"은 업계 일반 경험 표현 — 특정 업체 지목 금지.
- 톤/문구는 초안이니 자유롭게 다듬으세요(caption_chunks=화면, tts=나레이션).

## 프리뷰(샌드박스 샘플)
`preview/topic_hogaeng.mp4`, `preview/topic_geugadaero.mp4` (540×960·무음·Noto). 최종은 PC Studio/배치 렌더.
