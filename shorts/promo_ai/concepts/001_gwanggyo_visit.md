# 001 — 광교점 방문 안내 (Gwanggyo Visit, 15s)

> 첫 번째 promo_ai 견본. 매장 방문을 자연스럽게 유도하는 실사 광고.
> 키 메시지: "휴대폰 구매할 땐? 지원금부터 무료로 조회해보세요."

---

## 메타

- **slug:** `001_gwanggyo_visit`
- **duration:** 15초
- **aspect:** 9:16 (1080×1920)
- **target:** 인스타 릴스 / 틱톡
- **tone:** 따뜻 + 신뢰 + 정찰제 강조
- **model:** Kling 3.0 (멀티샷 + audio sync) — 1순위
- **fallback:** Seedance 2.0 (cut 별 분할, 정체성 일관)

## 스토리보드 (3 시퀀스 × 5초)

```
[Shot 1 — 0~5s] HOOK — 흔한 휴대폰 매장의 답답함
[Shot 2 — 5~10s] BODY — 폰스팟 광교점 실내, 명확한 가격표 + 상담
[Shot 3 — 10~15s] CTA — 카카오톡 / 링크 / 위치 노출
```

## Shot 1 (HOOK, 0~5s) — "다른 매장은…"

**비주얼:** 흐릿한 배경의 일반 휴대폰 매장. 손님이 직원에게 "얼마예요?" 라고 묻는데 직원이 어색한 표정. 가격표가 안 보이거나 가려져 있음. 답답한 분위기.

**카메라:** 어깨 너머 슬로우 zoom in. 직원 표정에 포커스.

**자막:** "휴대폰 구매할 땐?"

**SFX:** 어두운 톤의 짧은 hum

**Kling 3.0 prompt:**
```
Vertical 9:16 commercial, slow motion. Inside a typical Korean phone shop, slightly dim lighting. A customer asks a salesperson "How much?" The salesperson hesitates, looks awkward. No clear price tag visible. Slow zoom-in to the salesperson's hesitant expression. Cinematic, photorealistic, Korean retail setting, 5 seconds.
```

## Shot 2 (BODY, 5~10s) — "폰스팟 광교점은…"

**비주얼:** 폰스팟 광교점 실내. 밝고 정돈된 공간. 큰 디지털 가격표 (실시간 지원금 표시). 사장님 + 손님이 마주 앉아 태블릿/모니터로 함께 확인. 따뜻한 자연광.

**카메라:** wide → 가격 모니터 close-up → 손님 미소 close-up.

**자막:** "정찰제 그대로"

**SFX:** 밝은 ding + 부드러운 BGM swell

**Kling 3.0 prompt:**
```
Vertical 9:16 commercial, bright clean Korean phone shop interior. Phonespot Gwanggyo branch. Large digital price board showing transparent subsidies. Owner and customer sitting together at a counter, looking at a tablet screen showing prices. Warm natural daylight. Camera: wide shot → close-up on the price screen → close-up on customer's satisfied smile. Cinematic, photorealistic, 5 seconds.
```

## Shot 3 (CTA, 10~15s) — "지원금 무료 조회"

**비주얼:** 핸드폰 화면 풀샷 (9:16). 카카오톡 채팅 "@폰스팟광교점" + litt.ly/phonespot 링크 + 광교호수공원 B1-47 위치. 부드럽게 슬라이드인.

**카메라:** 스마트폰 over-the-shoulder, 화면 줌인.

**자막:** "지원금부터 무료로 조회해보세요"

**SFX:** 카카오톡 알림음 + 마무리 ding

**Kling 3.0 prompt:**
```
Vertical 9:16 close-up of a smartphone screen showing KakaoTalk chat with "@폰스팟광교점" handle. Smooth slide-in animation of contact info: phone number, location "광교호수공원 B1-47", website "litt.ly/phonespot". Clean modern UI overlay with brand orange accent #F74B0B. Photorealistic, 5 seconds.
```

## 자막 처리 (post)

- Shot 1: "휴대폰 구매할 땐?" (큰 폰트, 흰색, 검정 stroke)
- Shot 2: "정찰제 그대로" (오렌지 강조)
- Shot 3: "지원금부터 무료로 조회해보세요" + 채널 정보 자동 오버레이

## 비용 추정

- Shot 1 (Kling 3.0, 5s, 9:16): ~15 credits
- Shot 2: ~15 credits
- Shot 3: ~10 credits (정적 UI 중심)
- **합계: ~40 credits**
- 재생성 1-2회 가정 시 **80~120 credits** 확보 필요

**preflight 권장:** 실제 호출 전 `get_cost: true` 로 정확한 cost 확인.

## 리스크 & 미해결

1. **폰스팟 사장님(종민님) 실제 등장 여부** — 등장하면 Soul Character 학습 필요 (사진 5-20장)
2. **카카오톡 UI 저작권** — 실제 카톡 UI 모방 위험. 일반 메신저 UI 로 추상화 권장
3. **"정찰제" 표현** — 단통법 표시 광고법 점검 필요 (실제 매장 가격 보장 가능 범위 내)
4. **5초 cut 합치기 시 화면 흐름 부자연** — Kling 멀티샷 (한 호출에 3 cut) 사용 시 더 자연스러울 수도

## 다음 행동

1. 종민님 컨펌 후 첫 cut (Shot 1) 만 generate_image + generate_video 시도 (preflight cost 확인 → 결제 판단)
2. 결과 톤 만족 시 Shot 2, 3 진행
3. ffmpeg 합치기 → 최종 mp4
4. 검토 후 promo_ai SOP 정착
