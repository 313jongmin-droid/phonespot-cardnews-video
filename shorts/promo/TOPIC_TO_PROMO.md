# 주제 → 타이포(promo) 변환 스펙 (2026-06-24)

> 주제 엔진(`_docs/TOPIC_ENGINE.md`)의 **주제 seed 1건**을 타이포 promo **초안 MD**로 바꾸는 다리.
> 클로드가 "N번 타이포" 명령을 받으면 이 스펙대로 `promo/review/NNN_<slug>.md`를 쓴다.
> 이후 콘텐츠 디테일(스타일 미세조정·SFX·음악)·렌더 품질은 **promo task 소유**(정본 `README.md`·`GUIDE_BEST_TYPO_AD.md`·`STYLE_CATALOG.md`). 이 문서는 **seed→초안 MD 변환까지만.**

---

## 1. 언제 타이포로 가나 (적합도)

- **1순위**: 브랜드 가치·정책·신뢰 주제 — 정찰제·호갱방지·가격투명·비대면·상담강요없음류. (뉴스 아닌 에버그린)
- **가능**: qa/pick/tip의 **수치·비교**, life의 **정책·절차** 각도. (카드와 병행 A/B 가능)
- **부적합**: 단발 속보(news)·반전 밈(meme)은 실사 viral/카드가 나음. 타이포는 "메시지·슬로건 반복 각인"에 강함.

판단 기준: **사운드오프(70~85%)에서 자막만으로 메시지가 꽂히나?** 그러면 타이포 적합.

---

## 2. 입력 (주제 seed에서 가져오는 것)

주제 풀 표 1행에서:
- **주제/소재** → 영상 한 줄 메시지(title).
- **후킹 슬로건** → 오프닝/훅 진입 문구(첫 1초).
- **핵심 수치·팩트 2~3** → 팩트 비트.
- **라인** → 프리셋 선택(§4).

수치·팩트가 부족하면 §1 적합도 재확인(타이포는 "할 말 2~3개"가 있어야 비트가 참).

---

## 3. 출력 = `promo/review/NNN_<slug>.md` (6비트 구조)

기존 promo MD 포맷 그대로(예 `review/001_jeongchalje.md`). **NNN = 기존 `promo/*.json` 최대번호+1**(중복 회피).

```
# NNN <slug>
- preset: <showcase|punchy|data|calm>     # §4
- title: <주제 한 줄>
- 후킹: <비교형|반전형|질문형|공감형>

## 오프닝   (초대형 단어로 진입, 2줄)
- line1: <후킹 슬로건 앞부분>
- line2: <뒷부분>
- 스타일: oversize
- 효과음: whoosh

## 훅       (공감/상황 한 컷)
- 화면: <토막1 | 토막2 | 토막3>           # | = 줄/컷 분리, 3토막 이내
- 스타일: kinetic
- 효과음: whoosh

## 팩트1    (문제 제기 — 불신·말바뀜·불투명)
- 화면: <문제 | 핵심 | 한방>
- 스타일: glitch
- 효과음: tick

## 팩트2    (해결 — 폰스팟 약속/핵심 수치)
- 화면: <폰스팟은 | 핵심수치 | 강조>
- 스타일: kinetic-box
- 효과음: ding

## 팩트3    (신뢰 — 비교·투명·근거)
- 화면: <근거1 | 근거2 | 한눈에>
- 스타일: swiss
- 효과음: pop

## CTA      (슬로건 마무리 + 브랜드)
- 화면: <슬로건 | 폰스팟>
- 스타일: kinetic-box
- 효과음: ding
```

비트 수는 가감 가능(팩트 1~3). **나레이션 필드는 선택**(현재 무음 렌더면 화면 자막이 본체; 향후 음성용 스크립트 참고).

---

## 4. 프리셋 선택 (라인·각도 → preset)

| preset | 결 | 어떤 주제 |
|---|---|---|
| **showcase** | 디렉터 컷(비트별 최적 스타일) — 기본 | 브랜드 가치·정책·쇼케이스(정찰제류). 잘 모르면 이거 |
| **punchy** | 빠른 공감·POV | 호갱·상황극·공감 각도(pov류) |
| **data** | 수치 강조 | 비교·계산·발품vs조회(qa/pick 수치) |
| **calm** | 차분·신뢰 | 부모님폰·신뢰·안내(life 절차) |

스타일/효과음은 preset 기본 styleMap을 따르되, **비트마다 최적 스타일 배치(디렉터 컷)**가 핵심 — 정본 = `GUIDE_BEST_TYPO_AD.md` §2(오프닝 oversize / 훅 kinetic / 문제 glitch / 해결 kinetic-box / 신뢰 swiss / CTA kinetic-box). 스타일 목록 = `STYLE_CATALOG.md`(23종).

---

## 5. 화면(자막) 작성 룰 (사운드오프 전제)

- **짧게**: 한 컷 한 메시지. `|`로 3토막 이내.
- **핵심 1단어 강조**(즉.시.조.회 같은 분절 허용).
- **첫 1초(오프닝+훅)**가 완주율 좌우 — 가장 센 후킹을 앞에.
- 브랜드 마감: CTA에 `폰스팟` + (캡션/끝컷) `litt.ly/phonespot` 일관.

---

## 6. 드롭 → 렌더

1. MD를 `promo/review/NNN_<slug>.md`에 저장.
2. **JSON 등록(중요)**: `python scripts/promo_md2json.py <NN>` → `promo/NNN_<slug>.json` 생성. **이 단계 전엔 패널 타이포 탭 목록(promo_list=*.json glob)에 안 뜸.** (또는 `run_promo.bat <num>`이 md2json을 자동 수행하므로 첫 렌더를 bat으로 하면 등록+렌더 한 번에.)
3. 렌더: 패널 타이포 탭에서 그 번호 선택 → 렌더, 또는 `run_promo.bat <num> [preset]`. 패널 연결 정본 = `shorts/promo/PANEL_INTEGRATION_HANDOFF.md`.
4. 결과 = `promo/out/NNN_<slug>_<preset>.mp4` (+ 패널 경유 시 `RESULTS/..._promo/`).

---

## 7. 경계

- 이 스펙 = **주제 seed → 초안 MD**까지(클로드/주제 트랙).
- 비트 스타일 미세조정·SFX·음악·렌더 품질·신규 스타일 = **promo task**(`README.md` 워크플로, `_LEARN.md` 학습).
- 번호 충돌: 새 NNN은 기존 `promo/*.json` 최대+1. label에 `_` 금지(패널 슬러그 인코딩 규칙, HANDOFF 참조).
