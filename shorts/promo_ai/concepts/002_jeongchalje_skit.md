# 002 — 정찰제 콩트 (Jeongchalje Skit, 실사형 상황극, ~16s)

> 타이포 영상 `001_jeongchalje_showcase`(검정+오렌지 모션그래픽)와 **같은 메시지**를
> 실사 AI 콩트(상황극)로 옮긴 버전.
> 키 메시지: "세상 모든 건 가격표가 있는데, 왜 휴대폰만 없을까? → 폰스팟은 정찰제."

---

## 메타

- **slug:** `002_jeongchalje_skit`
- **duration:** ~16초 (4 shot × 4초)
- **aspect:** 9:16 (1080×1920)
- **target:** 인스타 릴스 / 틱톡
- **format:** 실사형 콩트(가벼운 코미디) — 과장된 표정·상황 개그
- **tone:** 공감개그 → 사이다(해결) → CTA
- **인물:** 익명 배우 톤 (사장님 미등장, 사진 학습 불필요)
- **제품 컷:** 종민님 별도 제공 영상 = ffmpeg 인서트로 끼움(아래 [INSERT] 표시 지점)
- **model:** Kling 3.0 (멀티샷/모션) — 1순위 / fallback Seedance 2.0
- **대사:** Kling audio 불안정 → **대사는 최소, 자막+SFX+BGM 중심**으로 안전하게

## 콩트 한 줄 구조

```
[Shot 1] 일상: 마트에선 다 가격표가 보임 (당연함)        → "세상 모든 건 가격표가 있어요"
[Shot 2] 부조리: 휴대폰 가게선 가격을 안 알려줌 (답답 개그) → "그런데 왜 휴대폰만?"
[Shot 3] 해결: 폰스팟, 가격이 그냥 떡하니 (사이다)        → "그 가격 그대로 · 즉.시.조.회"
[Shot 4] CTA: 정찰제 + 폰스팟 연락처                     → "휴대폰도 이제 정찰제"
```

---

## Shot 1 (HOOK, 0~4s) — "마트에선 당연한데"

**콩트:** 30대 남자 손님이 편의점/마트에서 과자·음료를 집어 든다. 상품마다 가격표가 또렷이 보이고, 남자는 가볍게 고개를 끄덕이며 장바구니에 담는다. 경쾌하고 일상적인 분위기.

**카메라:** 손에 든 상품 가격표 클로즈업 → 남자의 만족스러운 표정.

**자막:** "세상 모든 건 가격표가 있어요"

**SFX:** 밝은 '띵' + 경쾌한 마트 BGM

**Kling 3.0 prompt (EN):**
```
Vertical 9:16, photorealistic, lighthearted commercial. A Korean man in his 30s picks up snacks and a drink in a bright convenience store. Clear price tags visible on every product. He nods casually, satisfied, and puts them in a basket. Cheerful everyday mood, soft daylight, handheld camera, close-up on the price tags then his content face. 4 seconds.
```

## Shot 2 (CONFLICT, 4~8s) — "그런데 휴대폰만…"

**콩트:** 같은 남자가 일반 휴대폰 매장에서 최신 스마트폰을 들고 "이거 얼마예요?" 묻는다. 점원이 능청스럽게 "아~ 그게… 번호이동이세요? 카드 있으세요?" 하며 질문만 쏟아내고 가격은 안 말한다. 남자의 표정이 점점 굳고 황당해진다. (가격표 부재 = 콩트 포인트, 과장된 코믹 연기)

**카메라:** 남자 어깨 너머 → 점원의 능청 표정 → 남자의 당황 클로즈업.

**자막:** "그런데 왜 휴대폰만?" → (점멸) "얼마인지를 안 알려줘…"

**SFX:** '뚝' 끊기는 효과음 + 어색한 정적 + 물음표 띵

**Kling 3.0 prompt (EN):**
```
Vertical 9:16, photorealistic, comedic tone. The same Korean man holds a new smartphone in a typical phone shop and asks the price. The salesperson smiles slyly and keeps asking questions ("number transfer? do you have a card?") without ever saying the price. The man's face slowly turns confused and exasperated. Exaggerated comedic acting, slightly dim cluttered shop, over-the-shoulder then close-up on the man's puzzled face. 4 seconds.
```

## Shot 3 (RESOLUTION, 8~12s) — "폰스팟은 그 가격 그대로"

**콩트:** 남자가 폰스팟 광교점에 들어선다. 밝고 깔끔한 매장. 벽 대형 디지털 보드/태블릿에 기종별 가격·지원금이 **그대로** 떠 있다. 점원이 화면을 탁 돌려 보여주며 엄지척. 남자가 "오~" 하며 환하게 미소. (사이다 해결)

**카메라:** 매장 와이드 → 가격 보드 클로즈업 → 남자 만족 미소.
**[INSERT 지점]** 종민님 별도 제품/매장 실촬 영상이 있으면 이 가격 보드 클로즈업 자리에 1~2초 끼움.

**자막:** "그 가격 그대로" → "즉. 시. 조. 회!"

**SFX:** 밝은 'ding' + BGM 상승

**Kling 3.0 prompt (EN):**
```
Vertical 9:16, photorealistic, bright clean modern Korean phone shop (Phonespot). A large digital price board on the wall clearly shows phone models with transparent prices and subsidies. A friendly staff turns a tablet to show the man the prices openly, gives a thumbs up. The man smiles brightly, relieved and impressed. Warm natural daylight, wide shot then close-up on the price board and his happy face. 4 seconds.
```

## Shot 4 (CTA, 12~16s) — "휴대폰도 이제 정찰제"

**콩트:** 깔끔한 엔딩 카드. 오렌지(#F74B0B) 브랜드 톤. "휴대폰도 이제 정찰제 / 폰스팟" 큰 타이포 + 카카오톡 @폰스팟광교점 / litt.ly/phonespot / 광교호수공원 B1-47.

**처리:** 이 컷은 실사보다 **타이포 엔딩(promo 트랙 에셋 재활용)** 이 정확/저렴. AI 생성 대신 기존 엔딩 프레임 합치기 권장.

**자막:** "휴대폰도 이제 정찰제" + 채널 정보 오버레이

**SFX:** 카톡 알림음 + 마무리 'ding'

---

## 자막 (post, 오렌지 강조)

| Shot | 자막 |
|---|---|
| 1 | 세상 모든 건 가격표가 있어요 |
| 2 | 그런데 왜 휴대폰만? |
| 3 | 그 가격 그대로 · 즉.시.조.회! |
| 4 | 휴대폰도 이제 정찰제 — 폰스팟 |

## 비용 추정 (Kling 3.0, 9:16)

| Shot | 길이 | 추정 credits |
|---|---|---|
| 1 마트 | 4s | ~12 |
| 2 부조리 | 4s | ~12 |
| 3 해결 | 4s | ~12 |
| 4 CTA | — | 0 (타이포 엔딩 재활용) |
| **합계** | | **~36** (재생성 1~2회 시 **70~110**) |

**preflight 필수:** 호출 전 `get_cost: true` 로 실제 cost 확인.

## 리스크 & 결정 대기

1. **콩트 연기/표정** — Kling이 "능청 → 당황" 미묘한 코믹 연기를 한 번에 못 뽑을 수 있음. Shot 2가 핵심 리스크 → 먼저 1컷만 생성해 톤 확인.
2. **대사 음성** — 한국어 audio sync 불안정 → 무음(자막+SFX)으로 가는 게 안전. 나레이션 원하면 별도 TTS 후 합치기.
3. **인물 일관성** — Shot 1·2·3 같은 남자여야 자연스러움. Kling 멀티샷(한 호출 3컷) 또는 Shot1 끝프레임을 다음 start_image로.
4. **카톡 UI** — Shot 4는 타이포라 무관. 실사 안에 실제 카톡 UI 넣지 않음.

## 다음 행동 (크레딧 확보 후)

1. **크레딧 게이트** — 현재 잔액 3 / free. ~36+ 필요. 충전 전 빌드 불가.
2. 충전 후 → Shot 2(핵심 리스크)부터 preflight cost 확인 → 1컷 생성 → 톤 OK면 1·3 진행.
3. 종민님 [INSERT] 영상 있으면 Shot 3에 합치기.
4. ffmpeg: shots concat → 자막(.srt) → BGM/SFX → 1080×1920 yuv420p 최종.
5. 결과·cost·만족도 이 파일 하단에 기록.
