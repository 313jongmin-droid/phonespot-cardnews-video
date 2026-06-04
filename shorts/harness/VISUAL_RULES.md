# VISUAL_RULES

> 이미지·일러스트·마스코트·동적 컴포넌트 사용 규칙.

---

## 큰 원칙

1. **한 영상 안에서 같은 visual은 2번 이상 쓰지 말 것** — 청크마다 가능한 다른 visual.
2. **카드뉴스 GPT 원본 이미지(1.png~5.png)는 적절히 활용** — 영상 인트로·전환·강조 장면에 자연스럽게 삽입.
3. **마스코트는 최소화** — 문맥상 적합한 다른 이미지가 정말 없을 때만 사용.
4. **브랜드·통신사 로고는 기존 PNG 우선** — `public/assets/logos/` 또는 `logos/`에서 매칭되는 파일 활용.
5. **값이 바뀌는 정보는 PNG에 박지 말 것** — 날짜·금액·가격 변화 등은 React 동적 컴포넌트로 처리.

---

## 자산 카테고리

### 1. 카드뉴스 원본 카드 (1.png~5.png)
- 경로: `public/assets/1.png` ~ `public/assets/5.png` (slug별 카드뉴스 빌드 산출물)
- 용도: 인트로 슬라이드, 청크 전환 배경, 강조 카드 등
- ⚠ 절대 스캔하지 말 것 (블랙리스트). 빌드 스크립트가 자동 매핑.

### 2. 로고 (`public/assets/logos/`, `logos/`)
- 폰스팟 로고, 통신사 로고(SKT·KT·LGU+), 제조사 로고(Samsung·Apple) 등 PNG
- 영상 컴포넌트에서 직접 참조
- 신규 로고 필요 시: 사용자에게 PNG 업로드 요청 → 같은 폴더에 동일 파일명으로 저장

### 3. 정적 일러스트 (`public/assets/illustrations/<name>.png`)
- 청크 visual 매핑용 일반 일러스트 (예: `phone.png`, `calendar.png`, `coffee.png`, `kiosk.png`)
- 빌드 스크립트가 청크 본문 키워드 → 매칭되는 일러스트로 자동 매핑
- 신규 일러스트는 **AI가 SVG 직접 그리지 말 것** — 사용자에게 ChatGPT 생성 프롬프트만 제공 → 사용자가 PNG 받아서 동일 파일명으로 업로드

### 4. 마스코트
- 폰스팟 마스코트가 있다면 `public/assets/mascot/` 또는 별도 위치
- 사용 빈도 최소화. 영상당 1~2회면 충분.
- 마스코트 + 텍스트 조합으로 어색하면 마스코트 빼고 다른 visual로 대체.

### 5. 동적 컴포넌트 (React) — `src/components/casual/Infographics.tsx`
값이 바뀌는 정보는 PNG 일러스트로 박지 말고 다음 컴포넌트 사용:

| 컴포넌트 | 용도 | 예시 |
|---|---|---|
| `stat` | 큰 숫자 강조 | "5조 달러", "385달러" |
| `compare` | 두 값 비교 | "전년 대비 +14%" |
| `timeline` | 시간 흐름 | "5/27 → 6/14 → 6/21" |
| `pricebar` | 가격 변화 | "125만원 → 55만원 → 0원" |
| `calendar` | 날짜 강조 | "5월 31일 마감" |
| `bankaccount` | 입금 표현 | "10만원 추가보상" |

---

## 신규 일러스트 요청 절차

청크에 적합한 일러스트가 없을 때:

1. AI가 사용자에게 **ChatGPT 이미지 생성 프롬프트** 제공
   - 양식: `harness/VISUAL_RULES.md` 하단의 "일러스트 프롬프트 템플릿" 참조
2. 사용자가 ChatGPT에서 PNG 생성·다운로드
3. 사용자가 PNG를 `public/assets/illustrations/<name>.png`로 업로드
4. AI가 `Illustrations.tsx`에 매핑 추가 (키워드 → 파일명)

⚠ **AI가 SVG를 직접 그리지 말 것** — 일관성·품질 문제. ChatGPT 이미지로 통일.

### 일러스트 프롬프트 템플릿

```
1080x1080 PNG, transparent background, photorealistic editorial illustration style.
Subject: [구체 묘사]
Style: Light cream / warm white palette, soft natural daylight, no dramatic shadow.
No text, no brand logos, no real human faces.
Phonespot orange #F74B0B subtle accent if appropriate.
```

---

## Visual 매핑 우선순위 (build_script.py 룰)

청크 본문 → visual 자동 매핑 시 다음 순으로 시도:

1. **명시적 키워드 매칭** — 본문에 "달력"·"calendar" 있으면 → `calendar.png` 또는 `calendar` 동적 컴포넌트
2. **카테고리 매칭** — 본문이 "가격·금액·할인"이면 → `pricebar` 또는 `bankaccount`
3. **카드뉴스 원본 활용** — 매칭 없으면 1.png~5.png 중 청크 순서에 맞는 것
4. **fallback: 마스코트 또는 로고** — 위 모두 안 되면 (마지막 옵션)

---

## 시각 일관성 체크

빌드 후 영상 미리보기에서 다음 확인:

- [ ] 같은 visual이 영상 내 2번 이상 나오지 않음
- [ ] 마스코트가 너무 자주 등장하지 않음 (영상당 0~2회)
- [ ] 동적 데이터(숫자·날짜)가 PNG에 박혀 있지 않음
- [ ] 로고가 정상 표시됨 (잘리거나 비율 깨짐 없음)
- [ ] 카드뉴스 원본 이미지가 자연스럽게 녹아듦
