# 002 — 정찰제 콩트 [광고용 / PAID] (~15s)

> 트랙 분리: 이 파일 = **광고용(paid)**. 바이럴용은 `003_viral_jeongchalje.md`.
> 같은 메시지(타이포 영상 `001_jeongchalje_showcase`)를 실사 AI 콩트로.
> 키 메시지: "세상 모든 건 가격표가 있는데, 왜 휴대폰만 없을까? → 폰스팟은 정찰제."

---

## 이게 광고용인 이유 (제작 문법 고정)

| 축 | 광고용 = 이 파일 |
|---|---|
| 목적 | 전환·도달 (카톡 상담·링크 클릭) |
| 노출 | 피드/릴스 **유료 강제 노출** (스킵 전제) |
| 첫 3초 | 즉시 후킹 + 브랜드 빠르게 |
| 길이 | 15초 고정 |
| CTA | 강함·명시 (지금 조회/카톡) |
| 측정 | 3초 시청률 · CTR · 카톡 전환 · CPA |
| 광고 티 | 나도 됨 (광고인 거 전제) |

→ "조회수 터트리기"가 목적이면 이 파일이 아니라 `003`(바이럴용)을 쓸 것. 광고용으로 조회수 노리면 예산만 소모.

## 메타

- **slug:** `002_ad_jeongchalje`
- **duration:** 15초 (4 shot)
- **aspect:** 9:16 (1080×1920)
- **format:** 실사형 콩트(가벼운 코미디)
- **인물:** 익명 배우 톤 (사장님 미등장)
- **제품 컷:** 종민 별도 영상 = ffmpeg 인서트 (Shot 3 [INSERT] 지점)
- **model:** Kling 3.0 / fallback Seedance 2.0
- **대사:** 최소, 자막+SFX+BGM 중심 (한국어 audio sync 불안정)

## 콩트 구조 (4 shot)

```
[Shot 1 0~3s]  HOOK   부조리 콜드오픈 — "얼마예요?" 묻는데 가격을 안 알려줌
[Shot 2 3~7s]  공감   마트는 다 가격표 있는데… (대조)
[Shot 3 7~12s] 해결   폰스팟, 가격이 그냥 떡하니 (사이다) [INSERT 가능]
[Shot 4 12~15s] CTA   정찰제 + 폰스팟 연락처
```

> ★ 보강점(재점검): 광고는 **첫 0.5~3초 정지**가 생명. 기존안은 마트(잔잔)로 시작했으나,
> 광고용은 **부조리 장면을 콜드오픈으로 먼저** 던져 "어 내 얘기네?" 정지 유도 → 그다음 마트 대조.

## Shot 1 (HOOK, 0~3s) — 부조리 콜드오픈

**콩트:** 남자가 휴대폰 매장에서 최신폰 들고 "이거 얼마예요?" 점원이 능청 "아~ 어디서 오셨어요? 번호이동이세요?" 가격은 안 말함. 남자 표정 굳음.

**카메라:** 남자 얼굴 클로즈업에서 시작(정지 유도) → 점원 능청.

**자막(0.5초 박힘):** "휴대폰만 왜 가격을 안 알려줘?"

**SFX:** 띵! + 어색한 정적

**Kling prompt (EN):**
```
Vertical 9:16, photorealistic, comedic. Close-up on a Korean man in his 30s holding a new smartphone in a typical phone shop, asking the price. The salesperson smiles slyly and dodges with questions instead of giving a price. The man's face freezes in disbelief. Exaggerated comedic acting, slightly dim cluttered shop, start on the man's face then cut to the sly salesperson. 3 seconds.
```

## Shot 2 (공감/대조, 3~7s) — "마트는 다 있는데"

**콩트:** 같은 남자가 밝은 마트에서 과자·음료를 집는다. 상품마다 가격표가 또렷. 가볍게 끄덕이며 담는다.

**자막:** "세상 모든 건 가격표가 있어요"

**SFX:** 밝은 띵 + 경쾌 BGM

**Kling prompt (EN):**
```
Vertical 9:16, photorealistic, cheerful. The same Korean man picks up snacks and a drink in a bright convenience store; clear price tags on every product. He nods casually, satisfied. Soft daylight, close-up on price tags then his content face. 4 seconds.
```

## Shot 3 (해결, 7~12s) — "폰스팟은 그 가격 그대로"

**콩트:** 남자가 폰스팟 광교점에 들어선다. 밝고 깔끔. 대형 디지털 보드/태블릿에 기종별 가격·지원금이 그대로. 점원이 화면을 탁 돌려 보여주며 엄지척. 남자 "오~" 미소.

**[INSERT 지점]** 종민 별도 제품/매장 실촬 영상 있으면 가격 보드 클로즈업 자리에 1~2초 끼움.

**자막:** "그 가격 그대로" → "즉. 시. 조. 회!"

**SFX:** 밝은 ding + BGM 상승

**Kling prompt (EN):**
```
Vertical 9:16, photorealistic, bright clean modern Korean phone shop (Phonespot). A large digital price board clearly shows phone models with transparent prices and subsidies. A friendly staff turns a tablet to show the man the prices openly, thumbs up. The man smiles brightly, relieved. Warm daylight, wide then close-up on the board and his happy face. 4 seconds.
```

## Shot 4 (CTA, 12~15s) — "휴대폰도 이제 정찰제"

**처리:** 실사보다 **타이포 엔딩(promo 트랙 에셋 재활용)** 권장 — 정확·저렴.
오렌지(#F74B0B) "휴대폰도 이제 정찰제 / 폰스팟" + 카톡 @폰스팟광교점 / litt.ly/phonespot / 광교호수공원 B1-47.

**자막:** "휴대폰도 이제 정찰제" + 채널 정보 오버레이

**SFX:** 카톡 알림음 + 마무리 ding

## 자막 (post, 오렌지 강조)

| Shot | 자막 |
|---|---|
| 1 | 휴대폰만 왜 가격을 안 알려줘? |
| 2 | 세상 모든 건 가격표가 있어요 |
| 3 | 그 가격 그대로 · 즉.시.조.회! |
| 4 | 휴대폰도 이제 정찰제 — 폰스팟 |

## 비용 추정 (Kling 3.0, 9:16)

| Shot | 길이 | credits |
|---|---|---|
| 1 부조리 | 3s | ~10 |
| 2 마트 | 4s | ~12 |
| 3 해결 | 4s | ~12 |
| 4 CTA | — | 0 (타이포 재활용) |
| **합계** | | **~34** (재생성 1~2회 시 70~100) |

**preflight 필수:** `get_cost: true`.

## 리스크 (광고용)

1. **Shot 1 능청→당황 코믹 연기** = 최대 리스크. 먼저 1컷 생성해 톤 확인.
2. **인물 일관성** (Shot 1·2·3 같은 남자) — 멀티샷 또는 끝프레임 start_image.
3. 대사 음성 불안정 → 무음+자막 권장.

## 다음 행동 (충전 후)

1. Shot 1(핵심 리스크)부터 preflight cost → 1컷 생성 → 톤 OK면 2·3.
2. [INSERT] 영상 있으면 Shot 3 합치기.
3. ffmpeg: concat → 자막(.srt) → BGM/SFX → 1080×1920 yuv420p.
4. 결과·cost·만족도 하단 기록.

---

## 최종 빌드 기록

- **2026-06-22 — v2 완주.** cost: **16.5 credits** (Shot1 4.5 + Shot2 6 + Shot3 6, kling3_0 std 무음). 만족도: 종민 "너무 좋다".
- 결과물: `shorts/promo_ai/out_promo_ai/002_ad_jeongchalje_15s.mp4` (15.1s, 1080x1920, 30fps, 무음).
- 컷 순서 = 마트(s2) → 부조리(s1) → 폰스팟(s3) → 정찰제 엔딩. 자막 = ffmpeg ass 후처리(중앙 Alignment 5, Fontsize 136, Noto Sans CJK KR).
- 자막 카피: "세상 모든 건\\N가격표가 있는데" → "휴대폰만, 왜\\N가격을 안 알려줘?" → "폰스팟은\\N그 가격 그대로" → "즉·시·조·회!".
- 트랙 SOP/함정 = `WORKFLOW.md` "실증 검증 (2026-06-22)".
