# 폰스팟 카드뉴스·영상 프로젝트 — 클로드 부트스트랩

> **새 클로드 세션이 이 폴더를 열면 가장 먼저 이 파일을 읽음.**
> 모든 가이드·매뉴얼·매커니즘 진입점은 여기. 다른 세션과 같은 공식으로 작업하려면 **아래 STEP 1을 반드시 먼저 실행**.

---

## STEP 1 — 작업 시작 전 가이드 일괄 Read (필수)

**공통 (항상 Read, 6개):**

1. `_docs/INSTRUCTIONS_CARDNEWS.md` — 시스템·자동화·후보 수집·발행 룰 마스터
2. `cardnews/templates/caption_template.md` — 5채널 + 나레이션 카피·캡션·후킹 룰
3. `_docs/CARDNEWS_BUILD.md` — 카드뉴스 1건 빌드 전체 워크플로 (수집→발행)
4. `_docs/AUTOMATION_OVERVIEW.md` — webui·telegram listener·outbox·run_pngs 매커니즘
5. `_docs/INSTRUCTIONS_SHORTS.md` — 영상(shorts) 빌드 매뉴얼
6. `cardnews/_state/content_guide.md` — 매 사이클 학습되는 시즌·트렌드 메모 (존재 시)

**조건부 (작업 유형 따라 추가 Read):**

- 실사 AI 광고 영상 (Higgsfield, Claude 담당): `shorts/promo_ai/README.md` + `shorts/promo_ai/WORKFLOW.md`
- 타이포 광고 영상 (Remotion, 수동/코덱스): `shorts/promo/README.md` + `shorts/promo/GUIDE_TYPOGRAPHY.md`
- 카드뉴스 → 캐주얼 숏폼 (코덱스 담당): `CODEX_VIDEO_DESK/README.txt`

각 Read 결과는 다음 작업의 컨텍스트로 직접 활용. 사장님이 "수집해줘" / "발행해줘" / "매커니즘 알려줘" 같은 짧은 명령만 줘도 위 가이드로 모든 형식·룰을 자동 적용해야 함.

---

## STEP 2 — 작업 유형별 진입점

| 사장님 명령 패턴 | 첫 행동 |
|---|---|
| "신규 수집" / "news 수집" / "신규 카드뉴스" | `INSTRUCTIONS_CARDNEWS.md` Step 1 룰 + 4 라인 병렬 WebSearch + 풀 후보 표 (라인별 모두 노출, 통합 번호) |
| "N번 발행" / "N+M 발행" / 숫자 회신 | `CARDNEWS_BUILD.md` 워크플로 따라 JSON + prompt.md + outbox 신호 |
| "프롬프트 다듬어줘" / "청크 다듬어줘" | `INSTRUCTIONS_CARDNEWS.md` 자막 청크 룰 + 매장 정합 |
| "텔레그램으로 쏴줘" | `AUTOMATION_OVERVIEW.md` outbox watcher 룰 → `_state/outbox/<날짜>_<주제>.txt` 떨굼 |
| "렌더 돌려줘" / "run_pngs" | `AUTOMATION_OVERVIEW.md` run_pngs 흐름 + 슬러그 NNN 셀렉트 |
| "영상 만들어줘" | `INSTRUCTIONS_SHORTS.md` Read 후 shorts 측 빌드 |
| "홍보영상" / "promo" / "타이포 영상" / "광고소재" | `shorts/promo/README.md` Read 후 promo 트랙 빌드 (`run_promo.bat`). 카드뉴스 영상과 다른 결(타이포/모션그래픽, 나레이션 없음·효과음+음악) |
| "실사 광고" / "AI 광고" / "Higgsfield" / "promo_ai" / "광교점 실사" | `shorts/promo_ai/README.md` + `WORKFLOW.md` Read → Higgsfield MCP (Kling 3.0 우선) 호출 → ffmpeg 합치기. **결제 상태 + balance 점검 필수**. 15초 9:16 광고 |
| "매커니즘 알려줘" / "이게 어떻게 돌아가" | `AUTOMATION_OVERVIEW.md` 직참조 |
| "관리대장" / "광고운영" / "광고 시트" / "KPI" | `ads/README_FOR_AI.md` → `ads/MANUAL.md` |
| "메타 자동화" / "캠페인별 통합" / "UTM 매핑" / "GA4 매핑" | `ads/META_AUTOMATION.md` |
| "유튜브 학습" / "인사이트" / **스크립트·카피 작성 시** | `ads/YOUTUBE_LEARNING.md` + 시트 "유튜브_인사이트" 탭 Read → 키워드/후킹 자동 반영 |
| "KT다이렉트샵" / "KT 관리대장" | `ads_kt/README_FOR_AI.md` |

---

## STEP 3 — 사장님 사용 패턴 메모리

- **사장님(종민) 선호**: 모르는 거 아는 척 ❌, 듣고 싶어 할 얘기 ❌, **팩트만 + 수학적·논리적**.
- 응답 톤 짧게. 미사여구·과한 보고 ❌. "방금 한 일" 요약 ❌.
- 매뉴얼 인용 시 줄 번호로 직접 가리키기 (예: `INSTRUCTIONS_CARDNEWS.md:329-352`).
- 옵션 제시는 정직한 한계 동봉. **클로드가 권장 강요 ❌**. 사장님이 직접 선택.

---

## STEP 4 — 시스템 진입점 파일 (작업 시작용)

| 항목 | 경로 | 용도 |
|---|---|---|
| webui | `cardnews/webui/app.py` (`webui/start.bat`) | Flask 컨트롤 패널 |
| 셀렉트 렌더 | `cardnews/run_pngs.bat` | 슬러그 셀렉트 + 18 JPG 생성 |
| 텔레그램 listener | `automation/scripts/telegram_listener.py` | 폰 → PC 명령 + outbox 푸시 |
| 텔레그램 송신 헬퍼 | `automation/scripts/tg_send.py` | 1회 송신 CLI |
| 영상 빌드 | `shorts/` 디렉터리 + Remotion | 카드뉴스 기반 영상(casual/newsroom) |
| **홍보영상(promo)** | `shorts/promo/README.md` → `run_promo.bat` | 타이포/모션그래픽 홍보 쇼츠 (Remotion 기생, 나레이션 없음·효과음+음악·스타일별 SFX·무드 음악풀) |
| **실사 AI 광고(promo_ai)** | `shorts/promo_ai/README.md` + `WORKFLOW.md` | 15초 9:16 실사 광고. Higgsfield MCP (Kling 3.0 1순위 / Seedance 2순위) → ffmpeg 합치기. Claude 담당 |
| 코덱스 영상 데스크 | `CODEX_VIDEO_DESK/` | 별도 task |
| **광고운영 관리대장** | `ads/README_FOR_AI.md` → `ads/MANUAL.md` | 폰스팟 시트·KPI·메타·GA4 자동화 |
| **메타 API 자동화** | `ads/code/apps_script/meta-sync.gs` + `ads/META_AUTOMATION.md` | 메타 광고 + GA4 통합 |
| **KT다이렉트샵 관리대장** | `ads_kt/README_FOR_AI.md` | KT 별도 시트 |

---

## STEP 5 — 폴더 구조 (높은 수준)

```
phonespot_cardnews/
├── CLAUDE.md                     ← 이 파일 (부트스트랩)
├── _docs/                        ← 가이드 모음 (반드시 모두 Read)
│   ├── INSTRUCTIONS_CARDNEWS.md  마스터 매뉴얼
│   ├── CARDNEWS_BUILD.md         빌드 워크플로
│   ├── AUTOMATION_OVERVIEW.md    매커니즘
│   ├── INSTRUCTIONS_SHORTS.md    영상 매뉴얼
│   ├── SETUP_GUIDE.md            초기 셋업
│   ├── SETUP_WINDOWS.md          Windows 환경
│   └── PORTABILITY.md            이식 가이드
├── _secrets/                     ← .gitignore (API 키·토큰)
├── _state/                       ← 런타임 상태
│   ├── outbox/                   클로드가 떨궈둔 텔레그램 송신 큐
│   └── outbox_sent/              송신 완료 보관
├── cardnews/
│   ├── articles/                 NNN_<type>_<topic>.json
│   ├── images/                   NNN_<type>_<topic>/prompt.md + 1~5.png
│   ├── output/                   18 JPG + captions.md (렌더 결과)
│   ├── templates/                
│   │   └── caption_template.md   카피·캡션 룰
│   ├── webui/                    Flask 패널
│   ├── scripts/                  렌더·도구
│   └── _state/                   카드뉴스 사이클 메모
├── shorts/                       영상 (Remotion: casual/newsroom 카드뉴스영상)
│   ├── promo/                    ★ 타이포/모션그래픽 홍보영상 (진입점 README.md, run_promo.bat)
│   └── promo_ai/                 ★ 실사 AI 광고영상 (진입점 README.md + WORKFLOW.md, Higgsfield Kling 3.0/Seedance, ffmpeg 합치기, Claude 담당)
├── automation/                   listener·자동화 스크립트
├── CODEX_VIDEO_DESK/             코덱스 영상 task (별도)
├── ads/                          ★ 광고운영 관리대장 (폰스팟)
│   ├── README_FOR_AI.md          AI 진입점 — Sheet ID + 자동화 흐름
│   ├── MANUAL.md                 매일/주간/월간 운영 매뉴얼
│   ├── META_AUTOMATION.md        메타 API + GA4 + UTM 매핑 통합 가이드
│   ├── code/apps_script/
│   │   ├── Code.gs               시트 자동화 (KPI/매트릭스/SNS)
│   │   └── meta-sync.gs          메타 API 자동 동기화 (campaign/소재/UTM)
│   └── data/
│       ├── sheet_structure.md    시트 컬럼 구조
│       └── utm_mapping_design.md UTM_매핑 시트 설계
├── ads_kt/                       ★ KT다이렉트샵 관리대장 (별도 시트)
└── upload/                       SNS 업로드 자료
```

---

## STEP 6 — 다른 세션과의 연동 (★ 하네스)

본 CLAUDE.md 가 모든 가이드의 단일 진입점. 다른 클로드 코드 세션·코덱스 등이 이 폴더에서 작업할 때:

1. **자동 Read** — Claude Code CLI 는 cwd 의 `CLAUDE.md` 를 자동 Read. Cowork mode 는 폴더 마운트 시 진입 메시지에 본 파일 포함되도록 사용자 설정 권장.
2. **가이드 업그레이드 시** — 매뉴얼·캡션템플릿·빌드가이드 어느 하나 변경됐다면 본 CLAUDE.md 의 STEP 1 리스트 갱신·버전 메모 추가
3. **다른 task와 매커니즘 공유** — 영상 task (CODEX_VIDEO_DESK) 도 자체 README 외에 본 CLAUDE.md 참조. 카드뉴스 측 자동화 (outbox·webui) 변경 시 영상 측에 영향 점검
4. **결과 저장 규약** — 모든 task 산출물은 표준 폴더 (articles/·images/·output/·shorts/) 에만 저장. 임의 위치 ❌
5. **명령 없이 자동 실행** — 사장님 짧은 명령 ("수집"·"발행"·"렌더") 으로 위 STEP 2 매트릭스 따라 즉시 동작. 가이드 추가 질문 ❌

---

## STEP 7 — 변경 이력 (CLAUDE.md 자체)

- 2026-06-04: 신설. STEP 1~7 박음. 6 가이드 진입점 정렬. 하네스 시작.
- 2026-06-05: ads/ + ads_kt/ + 메타 자동화 합류. STEP 2 명령 패턴 3개 추가, STEP 4 진입점 3개 추가, STEP 5 폴더 구조에 ads/ ads_kt/ 박음.
- 2026-06-05: 유튜브 자동 학습 루프 합류. `ads/YOUTUBE_LEARNING.md` + `youtube_sync.gs`의 generateYouTubeInsights (Gemini API 분석, 매일 03:40 자동). 스크립트·카피 작성 시 "유튜브_인사이트" 시트 Read 의무화.
- 2026-06-07: promo(홍보영상) 트랙 하네스 합류. STEP 2 명령 패턴 + STEP 4 진입점 + STEP 5 폴더에 등록. 진입점=`shorts/promo/README.md`(Remotion 기생, 나레이션 없음·효과음+음악·스타일별 SFX·무드 음악풀). ※ `_docs/INSTRUCTIONS_SHORTS.md`는 옛 MoviePy/Typecast 설계라 현행 Remotion과 불일치 — 갱신 필요(미정).
- 2026-06-08: promo_ai(실사 AI 광고) 트랙 하네스 합류. STEP 1 조건부 Read 섹션 신설 + STEP 2 명령 패턴 + STEP 4 진입점 + STEP 5 폴더에 등록. 진입점=`shorts/promo_ai/README.md` + `WORKFLOW.md`(Higgsfield MCP Kling 3.0 1순위 / Seedance 2순위 / ffmpeg 합치기, Claude 담당, 15초 9:16). 결제 상태: Higgsfield Free 3 credits (결제 검토 중, STARTER $19/월·연납 또는 PLUS $39-49/월).

이 파일이 업그레이드되면 변경 이력 1줄 추가. 가이드 추가·제거 시 STEP 1 리스트 동기화.
