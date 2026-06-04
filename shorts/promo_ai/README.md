# 폰스팟 promo_ai 트랙 — 실사 AI 광고영상 (2026-06-01 초안)

> Higgsfield 기반 실사화 광고영상 트랙. 타이포그래픽 `promo/` 와 같은 결의 **promo 2중대**.
> 카드뉴스/숏폼 코드는 안 건드림. promo_ai 관련은 `promo_ai/` + `scripts/promo_ai_*.py` (예정) + `run_promo_ai*.bat` (예정) 에만 있음.

---

## 1. 한눈에

- **15초 9:16 세로 광고 영상** (인스타/틱톡)
- **Higgsfield MCP** 경유 (`mcp__83aadcc7-...__generate_video` 등)
- **메인 모델: Kling 3.0** — 멀티샷·audio sync·motion transfer 강점
- **서브 모델: Seedance 2.0** — 정체성 일관성 필요할 때 (시리즈 광고)
- **나레이션 가능** (Kling audio sync) — 또는 SFX/BGM 만
- 출력: `out_promo_ai/` (가칭, 미생성). 타이포 `out/promo/` 와 분리

## 2. 트랙 비교 (promo 두 진영)

| 항목 | promo (타이포) | promo_ai (실사 AI) |
|---|---|---|
| 비주얼 | Remotion 타이포그래픽 | Higgsfield 실사화 영상 |
| 비용 | 무료 (자체 렌더) | Credits 차감 (Higgsfield 결제 필요) |
| 빌드 시간 | 1-2분 | 5-15분 (외부 API 대기) |
| 수정 사이클 | 즉시 (MD 편집) | 재생성 = 추가 credits |
| 용도 | 정보 전달, 데이터 강조 | 분위기·감성·실사 어필 |
| 슬러그 수 | 12개 (001~012) | 미정 |

**선택 기준:**
- 정찰제·가격 비교·통계 → **promo (타이포)**
- 매장 분위기·실사 캐릭터·감성 광고 → **promo_ai (실사)**

## 3. 폴더 구조 (예정)

```
shorts/
├─ promo/                                ← 기존 타이포 진영
└─ promo_ai/                             ← 신규 실사 AI 진영
    ├─ README.md                         ← 이 문서
    ├─ _brand.json                       ← promo 와 공유 (또는 symlink)
    ├─ _template/                        ← 신규 컨셉 템플릿
    ├─ concepts/
    │   ├─ 001_gwanggyo_visit.json       ← shot-by-shot 기획서
    │   ├─ 001_gwanggyo_visit.md         ← 사람이 편집하는 원본
    │   └─ ...
    ├─ assets/
    │   ├─ characters/                   ← Soul Character (재사용 인물)
    │   ├─ references/                   ← 참조 이미지/영상 (모션 transfer)
    │   └─ logos/                        ← 폰스팟 로고
    ├─ shots/                            ← Higgsfield 생성 결과
    │   └─ 001_gwanggyo_visit/
    │       ├─ shot1.mp4
    │       ├─ shot2.mp4
    │       └─ shot3.mp4
    └─ out_promo_ai/                     ← ffmpeg 합치기 최종 mp4
        └─ 001_gwanggyo_visit_15s.mp4
```

## 4. 워크플로 (계획)

```
[1] 컨셉 기획
    concepts/<slug>.md 작성 (사람이 직접 또는 Claude 초안)
    → hook 3초 / body 9초 / cta 3초 분배
    → shot 별 텍스트 프롬프트 + 비주얼 컨셉

[2] 참조 이미지 준비 (선택)
    - assets/references/ 에 폰스팟 매장 사진 / 기존 광고 톤 참조
    - 또는 generate_image 로 키비주얼 1장 만들기

[3] shot 별 영상 생성
    - Kling 3.0 멀티샷 모드: 한 호출에 5-6 cut
    - 또는 Seedance 2.0 1 cut 씩 (정체성 일관 필요 시)
    - 9:16 / 3-5초 / 1080p

[4] ffmpeg 합치기
    - shots/*.mp4 → concat
    - BGM + SFX 오버레이 (선택)
    - 자막 (선택 — 광고는 자막 최소화)
    - 최종 1080×1920 mp4

[5] 검토 → 재생성 또는 발행
    - upload/ 또는 직접 SNS 업로드
```

## 5. 비용 가이드 (계획)

Higgsfield credits 기준 추정 (실제 호출 후 갱신):

| 작업 | 추정 credits |
|---|---|
| generate_image 1장 (1080×1920, marketing_studio_image) | 1-5 |
| Kling 3.0 영상 5초 1cut | 10-30 |
| Kling 3.0 멀티샷 15초 1편 | 30-80 |
| Seedance 2.0 영상 10초 1cut | 20-50 |
| 재생성 1회 (실패 시 비용 100%) | 동일 |

**실제 cost 는 호출 전 `get_cost: true` 파라미터로 preflight 가능.**

## 6. 폰스팟 광고 컨셉 풀

광고 1편당 1개씩 활용. 종민님이 우선순위 결정:

1. **광교점 방문 안내** — 매장 외관 + 상담 장면 + CTA (15초)
2. **정찰제 vs 흥정 비교** — 두 매장 대비 (다른 곳/폰스팟)
3. **단통법 폐지 후** — 가격 변화 보여주는 비포/애프터
4. **가족 단위 상담** — 따뜻한 가족 톤 + 매장 신뢰감
5. **밤늦은 시간 비대면 상담** — 카카오톡 응답 강조
6. **부모님 폰 교체** — 효도폰 컨셉
7. **첫 스마트폰** — 학생 컨셉
8. **갤럭시 vs 아이폰 비교 상담** — 양쪽 다 가능 어필

## 7. 미해결 / 결정 대기

- [ ] Higgsfield Plus/Ultra 결제
- [ ] 첫 컨셉 1개 빌드 → 실제 cost 확인
- [ ] 폰스팟 매장 실사진 확보 여부 (reference 활용 위해)
- [ ] 폰스팟 사장님 (종민님) 등장 여부 (Soul Character 학습용 사진 5-20장 필요)
- [ ] BGM/SFX 라이브러리 (저작권 무료)
- [ ] 자막 영상에 박을지 / SNS 자동 자막 사용할지

## 관련 메모리

- 영상 task: [[phonespot-video-project]] — 트랙 분리 (casual 숏폼 / promo 타이포 / promo_ai 실사)
- 광고 카피 / 브랜드: `shorts/promo/_brand.json`
- 카드뉴스 task 와 무관 (이번 트랙은 카드뉴스 source 안 씀)
