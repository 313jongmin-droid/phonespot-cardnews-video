# 폰스팟 타이포 포맷 뱅크 (바이럴 훅 → 폰스팟 응용)

> 아이디어: 검증된 숏폼 훅 포맷을 모아두고 → 폰스팟 메시지로 치환 → promo 스크립트로 → 파이프라인 렌더. **포맷은 반영구적, 트렌드만 주기 갱신.**
> 원칙(리서치): 첫 3초 훅이 70%↑ 영상의 공통점 · 무음 시청 85% → 자막 가독성 · 완주율 70%↑ = 알고리즘 부스트. (출처 하단)
> ⚠ "조회수 터짐"은 보장 불가. 아래는 "확률 높이는 검증된 패턴"이며, 폰스팟 응용은 규제-안전(숫자·경쟁사 지목 없음) 기준.

## 포맷 × 폰스팟 응용 (훅 = opening/hook 비트)

| # | 포맷(패턴) | 왜 통함 | 폰스팟 응용 훅(예) | 추천 프리셋 |
|---|-----------|--------|-------------------|-----------|
| 1 | 역설(Contradiction) | 통념을 깨 긴장 | "휴대폰 싸게 사려 발품 파는 게, 오히려 손해" | punchy |
| 2 | Stop X / Do this | 행동 교정 긴급함 | "휴대폰 살 때 '일단 상담' 그만. 가격부터 보세요" | showcase |
| 3 | 안 알려주는(No one talks) | 독점 정보감 | "휴대폰 업계가 안 알려주는 것 — 가격도 정찰제가 된다" | showcase |
| 4 | 약속(Promise) | 시청 보상 명시 | "이 영상 끝나면, 휴대폰 호갱 안 당하는 법 안다" | calm |
| 5 | 질문/왜 | 호기심 갭 | "세상 다 정찰제인데, 왜 휴대폰만 상담부터?" | showcase |
| 6 | N가지 리스트 | 구조적·완주 유도 | "호갱 안 되는 3가지 체크" | data |
| 7 | 공감 POV | "내 얘기" 몰입 | "휴대폰 사러 가서 3시간 상담받아본 사람?" | punchy |
| 8 | 오해 깨기(Myth) | 반전 | "휴대폰은 원래 깎는 거다? 아니요, 정찰제" | showcase |
| 9 | 전/후(Before·After) | 변화 시각화 | "예전엔 발품, 이제 비대면 조회" | data |
| 10 | 호기심 갭 | 답 궁금 | "공개된 그 가격, 진짜일까?" | showcase |
| 11 | 방법(How in 30s) | 즉시 실용 | "휴대폰 호갱 안 당하는 법, 30초 정리" | data |
| 12 | 대상 지목(Callout) | 자기 관련성 | "이번에 휴대폰 바꿀 사람만 보세요" | punchy |

## 반자동 루프 (운영)
1. **포맷 선택** — 위 표에서 1개(또는 트렌드 갱신분).
2. **치환** — 폰스팟 강점(정찰제·즉시조회·비대면·호갱방지)으로 opening/hook/fact×3/cta 채움 → `promo/<slug>.json` (템플릿 사용).
3. **프리셋 지정** — 표의 추천 프리셋.
4. **배치 렌더** — `run_promo_batch.bat <preset>` → `out/promo/`.
5. **게시 + 관찰** — 잘 된 포맷은 변형 재생산, 안 되는 건 폐기.

## "소재 수집" 자동화 — 현실 옵션 (솔직)
- **A. 포맷 뱅크 주기 갱신(권장·저비용)**: 분기 1회 트렌드 훅 리서치 → 이 표에 행 추가. 포맷은 잘 안 변해서 이걸로 대부분 커버.
- **B. 실데이터 수집(고급)**: 기존 `phonespot_scraping`(Apify) 확장 — 해시태그별 숏폼을 긁어 **조회수·완주 지표로 정렬** → 잘 터진 훅 패턴 추출. 단, 플랫폼 ToS·비용·유지보수 부담. 별도 빌드 필요.
- **C. 경쟁/벤치 모니터링**: 휴대폰·짠테크 계정 상위 영상 훅만 수동 캡처 → 표에 반영. 가장 가볍게 시작 가능.
- ⚠ 어떤 방식도 "터짐 보장"은 아님. 포맷은 확률을 올릴 뿐, 최종은 게시 후 데이터로 검증.

## 즉시 활용 (이 뱅크로 만든 신규 스크립트)
`promo/promo_stopsangdam.json`(포맷2) · `promo/promo_3check.json`(포맷6) · `promo/promo_myth.json`(포맷8). → `run_promo_batch.bat showcase`.

## 출처
- [18 Viral Hooks for YouTube Shorts (vidIQ)](https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/)
- [7 Viral Hook Frameworks (CreatorsJet)](https://www.creatorsjet.com/blog/7-viral-hook-frameworks-for-short-form-video-creators)
- [47 Best Hooks for Short-Form (FluxNote)](https://fluxnote.io/blog/best-hooks-for-viral-short-form-video)
- [How to Go Viral 2026 (Miraflow)](https://miraflow.ai/blog/how-to-go-viral-2026-what-actually-works-across-platforms)
