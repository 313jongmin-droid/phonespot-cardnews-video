# 004_viral_hogu — 폰 견적 호구썰 (viral)

> viral 트랙. 1순위 = 조회·공유·저장·댓글. 브랜드는 끝 자막 0.5초만.
> 톤 룰(종민 2026-06-24): 전문용어 X, 일반인 수준, 썰 풀듯 1인칭, 공감+유머, 캐릭터 글래머 현행.
> (구버전 = 남성 4비트, git 히스토리에 보존. 본 버전 = 여성 7비트 확정본.)

## 메타
- slug: 004_viral_hogu / track: viral / theme: 호구썰(견적)
- 길이: ~20s / 9:16 / model: kling3_0 (std, sound off)
- 인물: Higgsfield media_id `82abdf0f-ac89-4b3f-b614-1cb2ff650996` (글래머 현행, 깊은 U넥·머리~힙, 클로즈업으로 몸매 잘리지 않게)
- 학습 슬롯(INDEX 표B): 후킹타입 B(손실/썰도입), 제품 갤럭시(비특정 가능), 수법 할부+카드+부가

## 7비트 스토리보드

| 비트 | 나레이션(여성 TTS, 반말 썰톤) | 자막(.ass, 프레임1부터) | 화면 | 비용 |
|---|---|---|---|---|
| B1 후킹 | 나 어제 폰 바꾸다가 호구될 뻔한 썰 푼다 | 전문(천천히) | s1 글래머 폰가게 | 0 |
| B2 상황 | 폰 보러 갔는데 직원이 "이게 지금 제일 싼 거예요" 하면서 종이를 쫙 내미는 거야 | 요약 | s2 종이 보는 표정 | 0 |
| B3 빌드업 | 근데 무슨 숫자가 할부에 뭐에 막 외계어처럼 줄줄… 머리 핑 돌아서 그냥 "아 네…" 하고 사인할 뻔했잖아 | 요약(빠르게) | s2 뒷부분 | 0 |
| B4 전환 | 마침 친구가 "야 딴 데도 좀 보고 사" 하는 거야 | 요약 | s1/s2 재배치 | 0 |
| B5 반전 | 다른 데 가봤더니 똑같은 폰이 공짜. 깎아달라 할 것도 없어, 가격이 그냥 딱 정해져 있더라고 | "똑같은 폰이 공짜?!" (0.5s 정적) | clerk_card 켄번스 | 0 |
| B6 현타+댓글 | 와 그 자리에서 등에 식은땀… 나만 호구였나? 너넨 폰 얼마 주고 샀어? | "너넨 폰 얼마 주고 샀어?" | 신규 글래머 컷(현타) | +6cr |
| B7 CTA | (무음) | "가격 정해놓고 파는 곳, 폰스팟" | drawtext 엔딩 | 0 |

## 나레이션 TTS 입력 (Hana voice `c25f78a0-714e-42af-8da3-a399cef94968`, 6문장 ≈ 0.9cr)
1. 나 어제 폰 바꾸다가 호구될 뻔한 썰 푼다.
2. 폰 보러 갔는데 직원이 "이게 지금 제일 싼 거예요" 하면서 종이를 쫙 내미는 거야.
3. 근데 무슨 숫자가 할부에 뭐에 막 외계어처럼 줄줄. 머리 핑 돌아서 그냥 "아 네" 하고 사인할 뻔했잖아.
4. 마침 친구가 "야 딴 데도 좀 보고 사" 하는 거야.
5. 다른 데 가봤더니 똑같은 폰이 공짜. 깎아달라 할 것도 없어, 가격이 그냥 딱 정해져 있더라고.
6. 와 그 자리에서 등에 식은땀. 나만 호구였나? 너넨 폰 얼마 주고 샀어?
> B7은 자막만, 나레이션 없음.

## B6 신규컷 Kling 프롬프트 (영문)
The same Korean woman in the phone store, realizing she almost got ripped off — a dazed "oh no" expression with a slightly embarrassed awkward smile, lightly touching the back of her neck. Keep the same framing showing her full upper body and figure (head to hip), camera does NOT zoom in or crop her figure. Deep U-neck fitted white top as before. Subtle realistic motion. Slightly dim warm store light, NO readable Korean text, background signage blurred and out of focus.

## 빌드 메모
- 정규화 `scale=1080:1920,fps=30,setsar=1`. 순서 B1→B7.
- 페이싱: 후킹 천천히 / 빌드업 빠르게 / B5 반전에서 0.5s 정적(공짜 자막 멈칫) / B6 여운.
- 자막 프레임1부터(무음시청 대비). Noto Sans CJK Bold.
- 댓글유발 엔딩(B6 "너넨 얼마") = 알고리즘 부스트 장치. 브랜드는 B7 자막만(viral 룰).
- 재활용: s1(job 6f875e9d) / s2(job 5299aae2) / clerk_card(`shots/002_ad_jeongchalje/clerk_card_composite.jpeg`).
- 업로드 후 INDEX 표B에 채널별 성과(조회·완료율·공유·저장·댓글) 기입 → 학습 환류.
