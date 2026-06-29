# 폰스팟 전역 PREFLIGHT — 가이드 준수 강제 규약

> **왜 있나**: 가이드는 "읽기로 되어 있다"(honor-system)에만 의존했고, LLM은 룰을
> 확률적으로 따르지 강제되지 않아 누락이 반복됨(함수 유실·Edit truncation·컬럼 시프트·news D-7 누락).
> **원리**: self-read 강제도 결국 LLM 의존이라 샌다. **결정론적으로 강제되는 건 코드 게이트(부수효과 직전 검증)뿐.**
> 이 문서 = ① 명령 트리거 시 첫 행동(준-강제) + ② 부수효과 관문의 코드 게이트(진짜 강제).

---

## 1. 모든 명령의 첫 행동 (트랙 무관, 순서 고정)

1. **트랙 식별** — 명령이 어느 트랙인가(카드뉴스 / 영상 / 광고 / 멀티PC / 문서).
2. **필수 Read** — 아래 §2 표의 그 트랙 "필수 Read"를 **실제로 Read**(기억·추론으로 대체 ❌).
3. **절대 룰 복창** — 응답 첫머리에 그 트랙 "절대 룰"을 1줄 복창(자기 확인 + 사장님 검수용).
4. **작업 수행.**
5. **산출 게이트 통과** — 부수효과(commit/push/배포/렌더/시트쓰기/outbox) 전 §3 게이트 실행. 통과 못 하면 산출 ❌.

> 2·3을 건너뛰면 이번 같은 룰 누락이 재발한다. 빠뜨렸다고 판단되면 멈추고 Read부터.

---

## 2. 트랙별 필수 Read + 절대 룰

| 트랙 | 트리거 | 필수 Read | 절대 룰(복창 대상) |
|---|---|---|---|
| 주제 생성(★격상 2026-06-23) | "주제 생성"/"주제 뽑아"/"수집"/"신규 카드뉴스" | `TOPIC_ENGINE.md`(정본) + `INSTRUCTIONS_CARDNEWS.md` + `caption_template.md` + `content_guide.md` + 성과(`유튜브_인사이트` + `인스타` 시트) | **클로드=주제 생성만(구현=카드·영상·실사 별개)**, 소스 5갈래(뉴스·성과·트렌드밈·시즌·carryover), 주제마다 **추천트랙+떡상점수** 태깅, **news = D-7 strict**(`:382`), **D-7은 KST 기준**(`news_d7_filter.py` 게이트), **성과 판단은 클로드 자율**(시트 직접 읽고 가중치), 회피키워드, dup 제외 |

> **★ 날짜 규칙 (수집·발행 공통, 2026-06-22 박음 — 2회 오인 사고 방지)**: 오늘 날짜는 **오직 env 'Today's date'만 사용**. ❌ `bash date`(샌드박스 드리프트)·`currentDate`(stale) 금지. env가 "더 정밀하면 bash" 안내해도 **날짜엔 bash 쓰지 말 것**. **수집/발행 첫 응답 맨 위에 `오늘(env): YYYY-MM-DD / D-7: YYYY-MM-DD` 복창**(사장님 즉시 검증용) → `news_d7_filter.py --today <env날짜>`로 실행.

> **★ 후보 리스트업 규칙 (2026-06-22)**: ① **모든 후보는 사실검색·검증 완료 후에만 표에 올린다** — "사실확인 필요"·제목만 본 미검증 항목 등재 금지(특정 사건/뉴스는 WebSearch로 실체·시점·매장정합 확인, 부적합이면 제외 근거 1줄). ② **각 후보에 한 줄 요약 병기** — 토픽 옆에 "무슨 청크/스크립트가 될지"(핵심 메시지 + 카드 흐름) 1줄 미리보기. ③ **보류 후보(carryover) 합치기** — `content_guide.md §3.5` 풀을 신규와 합쳐 제시(미선택 좋은 후보 재등판), 발행 시 삭제·시점만료 제거, 수집 끝에 이번 미선택분 적재.

> **★ "수집" = 통합 소스 자동 합침(2026-06-23)**: ① RSS `_state/news_feed.json`(있으면) ② WebSearch(한국매체 allowed_domains) ③ 유튜브·인스타 성과 가중 ④ carryover ⑤ dup회피 → 검증완료·쇼츠포맷·한줄요약. 사장님 URL 주면 WebFetch 최우선. 정본 = INSTRUCTIONS "수집 통합 소스".
| 카드뉴스 발행 | "N번 발행" | `CARDNEWS_BUILD.md` + `caption_template.md` | 5채널 첫줄 후킹 상이, 사전승낙서, 카드6 source, narration URL/이모지 ❌, **★발행 완료 시 `_state/outbox/<slug>_ready.txt` 자동 생성=텔레그램 발행 신호(묻지 않고 무조건, 종민 standing 허락 2026-06-23)** |
| 영상 | "영상"/"promo"/"실사" | `INSTRUCTIONS_SHORTS.md` 또는 `shorts/promo*/README.md` | 트랙별 결(나레이션 유무) 구분 |
| 광고 운영 | "관리대장"/"메타"/"네이버"/"당근" | `ads/README_FOR_AI.md` + 해당 채널 가이드 | **콘솔 직접 수정 ❌**(clasp가 덮어씀), 컬럼 변경 마이그레이션 후 sync 재호출 |
| 코드 수정(전 트랙) | "수정"/"디버깅"/"기능추가" | `_docs/SYSTEM_MAP.md` 해당 대단원 | **26KB+ 파일 Edit 금지**(truncation) → bash-python/전체 Write, 검증=호스트 Read |
| Git/배포(전 트랙) | "push"/"전파"/"배포" | STEP 0 + SYSTEM_MAP F단원 | **push는 로컬 PC만**, 부사수=pull only |

---

## 3. 부수효과 관문 코드 게이트 (결정론적 강제)

| 관문 | 게이트 | 막는 것 |
|---|---|---|
| **commit** | `.githooks/pre-commit` (활성화: `git config core.hooksPath .githooks`) | .js/.py 문법, 한글 .bat BOM, 카드뉴스 기사 스키마 ERROR. 우회=`--no-verify` |
| **배포(push 후)** | `.github/workflows/deploy-apps-script.yml` "Syntax gate" step | 깨진 .js가 clasp push 도달 못 함. 실패=텔레그램 알림 |
| **카드뉴스 발행** | `cardnews/scripts/validate_article.py <slug>` | 필수 키 ERROR(slug/title/cards/captions_md) |
| **카드뉴스 수집(news)** | `cardnews/scripts/news_d7_filter.py` | 보도일 D-7 초과/불명 후보를 news 라인에서 거부(눈대중 대신 계산) |
| **다음 번호** | `validate_article.py --next` | NNN 수동 산출 실수 |

> 코드 게이트가 1차 방어선. §1 self-read는 보조(누락률↓). 새 부수효과가 생기면 여기 게이트를 추가한다.

---

## 4. 한계 (정직)

- self-read/복창(§1 2·3)은 LLM 의존이라 100% 강제 아님 — 누락률을 낮출 뿐.
- 수집 단계 news D-7은 `news_d7_filter.py`로 계산은 강제하지만, 그 필터를 "돌리는" 것 자체는 아직 self(파이프 구조화 전). 발행/commit/배포 관문은 코드로 진짜 강제됨.
- 강제의 끝단은 **사장님 검수** — §1 3의 룰 복창이 검수 포인트.

---

## 이력
- 2026-06-18: 신설. 전역 preflight + 부수효과 코드 게이트 4종(pre-commit·Actions·validate_article·news_d7_filter).
