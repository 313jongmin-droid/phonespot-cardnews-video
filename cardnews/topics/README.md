# 제작 task 작업 시작 안내 — topic_pool 사용법

> **이 폴더를 보는 너(영상·카드·실사 제작 task)에게.** 주제 task(클로드)가 떡상 주제를 발굴해 `topic_pool.json`에 넣어 둔다.
> **너는 주제를 새로 고민하지 않는다. 여기서 골라 만들기만 한다.** 주제↔구현 분리(정본 = `_docs/TOPIC_ENGINE.md`).

---

## 0. 한 줄 요약

`topic_pool.json` = "만들 주제 목록". 각 항목의 **status·assigned_track**을 보고 **네 트랙에 해당하는 것**을 골라, 들어 있는 **hook(후킹)·summary(골격)**를 시작점으로 제작한다.

---

## 1. 작업 시작 명령 (task 세션 첫 줄에 이렇게)

- **카드/카드영상 제작 task**:
  > "`cardnews/topics/topic_pool.json` 읽고 `status:"assigned"` + `assigned_track`이 카드/카드영상인 것 중 아직 안 만든 걸 하나 골라, `RENDER_TASK.md`/`CARDNEWS_BUILD.md`대로 제작"
- **실사 viral 제작 task(promo_ai)**:
  > "`cardnews/topics/topic_pool.json` 읽고 `assigned_track:"viral"`인 것 골라 `shorts/promo_ai/MEME_TO_VIRAL.md`대로 제작"

배정된 게 없으면 `status:"candidate"` 중 `track_suggest`가 네 트랙인 것을 골라도 된다(단 배정분 우선).

---

## 2. topic_pool.json 필드 읽는 법

| 필드 | 뜻 |
|---|---|
| `id` | 주제 식별자 (035·C01 등) |
| `line` | news/scam/tip/qa/pick/meme/life |
| `topic` | 주제 한 줄 |
| `hook` | **후킹 슬로건** (첫 1초·제목) — 시작점 |
| `summary` | **스크립트 골격(brief)** — 카드/컷 흐름 (예: 미끼→비용→확인→매장) |
| `track_suggest` | 추천 트랙 (카드/카드영상/실사 viral) |
| `assigned_track` | 패널에서 **배정된 트랙** (있으면 이게 우선) |
| `ttsan` | 떡상점수 라벨 (apple+·검증·인스타릴스208 등) |
| `status` | candidate(미배정) / assigned(배정됨) / in_progress / published(완료) |
| `slug` | 발행됐으면 articles 슬러그, 아니면 null |

---

## 3. 무엇을 고르나

1. **status로 거른다** — `published`는 끝난 것(건너뜀). `assigned` = 만들라고 배정된 것(우선). `candidate` = 아직 풀에 대기.
2. **네 트랙만** — `assigned_track`(없으면 `track_suggest`)이 네 담당인 것만:
   - 카드 / 카드영상 → 제작 task (`RENDER_TASK.md`)
   - 실사 viral → promo_ai task (`MEME_TO_VIRAL.md`)
3. **떡상점수(ttsan) 높은 것부터** — `★인스타릴스 208 실증`·`apple+` 등이 우선순위 힌트.

---

## 4. 어떻게 만드나 (트랙별 진입 문서)

| 트랙 | 진입 문서 | 산출 |
|---|---|---|
| 카드 | `_docs/CARDNEWS_BUILD.md` | `articles/<slug>.json` + `images/<slug>/prompt.md` → 렌더 18 JPG |
| 카드영상 | `_docs/INSTRUCTIONS_SHORTS.md` | TTS + MoviePy mp4 |
| 실사 viral | `shorts/promo_ai/MEME_TO_VIRAL.md` | 7비트(후킹→상황→빌드업→반전→현타→댓글) 실사 mp4 |

**brief 활용**: `hook`을 첫 1초/제목으로, `summary`를 카드·컷 흐름의 뼈대로 그대로 쓴다. 사실검증·5채널 캡션·사전승낙서·매장정합 등 디테일 룰은 각 진입 문서에 있다.

---

## 5. 끝나면

- 발행/완성되면 그 항목 `status:"published"` + `slug` 기록(패널 배정·발행 시 자동 갱신되기도 함).
- 다음 주제로. 같은 주제를 두 번 만들지 않도록 `published`/`in_progress` 체크.

---

## 6. 멀티PC 규칙 (STEP 0)

- `topic_pool.json`은 **git 추적** → 제작 PC는 `git pull`로 최신 주제를 받는다.
- **배정(assigned_track 기록)은 로컬 PC 패널 `/topics`에서만**(push 권한). 부사수·렌더 PC는 pull only.
- 계약: `run_<track>.bat <slug>` 실행 → 결과 표준 폴더(`articles/`·`output/`·`out_promo_ai/`)에 저장. 임의 위치 ❌.

---

## 한눈에

```
주제 task(클로드)  →  topic_pool.json  →  [패널 /topics 배정]  →  너(제작 task): pull → 골라 → 제작 → published
```
