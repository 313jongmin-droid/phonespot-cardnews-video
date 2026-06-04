# 폰스팟 promo — 인포그래픽 샘플 가이드라인

> 보존용 레퍼런스. 숫자·구조가 주인공인 스타일 모음(타이포 가이드와 짝).
> 프리뷰: `promo/preview/NN_<id>.mp4` (540×960·무음·Noto 샘플러) · 개념 6종: `preview/info6_contact.png`.
> 실제 사용: PC `npx remotion studio` → `Promo-<id>`. 소스: `src/components/promo/styles/<id>.tsx`.

## 인포그래픽 스타일 (총 12)

| # | id | 특징 | 추천 용도 | 수치 의존 |
|---|----|------|-----------|:---:|
| 12 | counter | 0→값 롤업 숫자 | 절약·건수 강조 | ◎ |
| 13 | barcompare | 두 막대 비교(조회가=개통가) | "그대로 개통" 증명 | ○ |
| 14 | timeline | 노드형 시간/단계 | 예전 방식→폰스팟 | △ |
| 15 | steps | 번호 스텝(1·2·3) | "조회→확정→개통" | △ |
| 16 | checklist | ✓/X 대조 | "이런 거 없어요" | ✗ |
| 17 | pictogram | 아이콘+문구 | 개념 보조 | ✗ |
| 18 | donut | 퍼센트 링 | 만족도·점유 등 비율 | ◎ |
| 19 | linegraph | 추세 라인 | 성장·변화 추이 | ◎ |
| 20 | statgrid | KPI 카드 그리드 | 강점 3~4개 나열 | ○ |
| 21 | ranking | Top-N 막대 랭킹 | 비교 우위/순위 | ◎ |
| 22 | gauge | 반원 게이지+바늘 | 점수·수준 한 지표 | ◎ |
| 23 | table | 2열 대조표(일반/폰스팟) | 항목별 우위 비교 | ✗ |

수치 의존: ◎ 숫자 필수 · ○ 일부 · △ 라벨 위주 · ✗ 텍스트만으로 충분

## ⚠ 규제 (인포그래픽 특히 중요)

- ◎/○ 스타일(counter·donut·linegraph·ranking·gauge·barcompare)은 **숫자가 핵심**이라, 반드시 **근거 있는 실제 수치**로 채울 것. 현재 프리뷰는 **샘플 플레이스홀더**(예: 100%, 임의 추세선)임.
- 경쟁사 직접 비교/순위는 비방·표시광고법 리스크 → table·ranking·barcompare는 "우리 항목" 또는 "업계 일반" 기준으로만(특정 업체 지목 금지). table의 "일반 매장"은 업계 일반을 뜻하는 일반명이며 특정 업체 아님.

## 폰스팟 적합 추천
- 신뢰·명료 우선: **16 checklist · 23 table · 15 steps**(숫자 없이 강력) → 1순위.
- 데이터가 확보되면: **21 ranking · 13 barcompare · 19 linegraph**.
- 단일 지표 강조: **18 donut · 22 gauge · 12 counter**.

## 공통 구조
타이포와 동일 디스패처(`PromoShort.tsx`). 섹션의 `caption_chunks`를 라벨/항목으로 사용하고, 수치는 스타일이 샘플로 생성(실데이터 연결 시 교체). 색 변주는 섹션별 자동.

→ 타이포 계열은 `GUIDE_TYPOGRAPHY.md` 참조.
