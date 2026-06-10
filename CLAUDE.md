# 폰스팟 카드뉴스·영상 프로젝트 — 클로드 부트스트랩

> **새 클로드 세션이 이 폴더를 열면 가장 먼저 이 파일을 읽음.**
> 모든 가이드·매뉴얼·매커니즘 진입점은 여기. 다른 세션과 같은 공식으로 작업하려면 **아래 STEP 1을 반드시 먼저 실행**.

---

## STEP 0 — 머신 역할 & 업데이트 적용 (★ 최우선 전제, 2026-06-08)

세 역할로 고정. **모든 해결책은 이 구조 안에서만** 준다.

| 머신 | 역할 | git |
|---|---|---|
| **노트북** | 개발/편집 전용(Claude 작업). 코드·가이드·articles·.bat 수정 → commit → push | **push only** |
| **실행 PC** (부사수=사무실, `C:\PhoneSpot\phonespot_cardnews`) | 단독 생산기. 카드뉴스·영상·패널 전부 실행 | **pull only** |
| 메인 PC (`192.168.0.7`) | 카드 이미지 원본 자산 소스(git 비공유 자산 LAN sync 출처) | — |

### 원칙
1. 해결 = **노트북 수정 → push → 실행 PC pull → 실행 PC에서 실행.** 노트북 실행 결과 신뢰 ❌(검증은 실행 PC 로그).
2. **실행 PC는 pull only.** 패널 "GitHub 업로드"(`codex_github_upload`)·자동커밋을 실행 PC에서 쓰면 origin/main 분기 → pull 충돌. **push는 노트북에서만.** ※ `_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md`의 "사무실도 push" 모델은 **폐기**(이 STEP 0이 우선).
3. **git 전파 vs 비전파**(STEP 7 위생 연동): 전파=코드·`.bat/.ps1/.mjs`·`cardnews/articles/*.json`·가이드·`.gitattributes` / 비전파(셋업·LAN sync·Drive로 따로)=`cardnews/images`·`output`·`_secrets`·`node_modules`·`.playwright`·임베딩 1GB·`library_share_path.txt`.
4. 진단은 실행 PC 로그 기준(노트북에서 못 봄).

### 노트북 업데이트를 실행 PC에 적용 (브랜치 `main`, 원격 origin)
- **자동(권장,1회)**: 실행 PC `CODEX_VIDEO_DESK\수신PC_자동업데이트_켜기.bat` → 이후 패널 켤 때마다 `git pull --ff-only` 자동.
- **수동**: `cd C:\PhoneSpot\phonespot_cardnews` → `git pull --ff-only`.
- **막히면(드리프트)**: `git fetch origin && git reset --hard origin/main` (gitignore 자산은 안 건드림).
- 코드·.bat·.mjs는 pull 즉시 반영. 의존성(pip/npm/임베딩) 변경 시에만 `SETUP_FULL_PRODUCER.bat`/패널 "시스템 업데이트" 재실행.

---

## STEP 1 — 작업 시작 전 가이드 일괄 Read (필수)

**공통 (항상 Read, 6개):**

1. `_docs/INSTRUCTIONS_CARDNEWS.md` — 시스템·자동화·후보 수집·발행 룰 마스터
2. `cardnews/templates/caption_template.md` — 5채널 + 나레이션 카피·캡션·후킹 룰
3. `_docs/CARDNEWS_BUILD.md` — 카드뉴스 1건 빌드 전체 워크플로 (수집→발행)
4. `_docs/AUTOMATION_OVERVIEW.md` — webui·telegram listener·outbox·run_pngs 매커니즘
5. `_docs/INSTRUCTIONS_SHORTS.md` — 영상(shorts) 빌드 매뉴얼
6. `cardnews/_state/content_guide.md` — 매 사이클 학습되는 시즌·트렌드 메모 (존재 시)

**인사이트 시트 (★ 매 수집·캡션 사이클 시작 시 무조건 Read, sync_sources 자동 전달):**

7. **관리대장 시트 `유튜브_인사이트`** — Apps Script 03:40 자동 갱신 (Top 키워드·후킹 패턴·우수 영상). 매 수집 시 가중치 적용. 캡션 첫 줄 후킹 패턴 적용.
8. **관리대장 시트 `메타_인사이트`** ★ 시트 추가 필요 (현재 Drive MD) — Top 헤드라인 패턴·우수 광고. 매 캡션 작성 시 짧은 채널 후킹 적용.

→ 시트 sync 안 되면 "인사이트 0건, 가중치 미적용" 1줄 명시 후 진행. 매커니즘·포맷·자가 검증 = `_docs/INSIGHTS_LOOP.md`.

**조건부 (작업 유형 따라 추가 Read):**

- 실사 AI 광고 영상 (Higgsfield, Claude 담당): `shorts/promo_ai/README.md` + `shorts/promo_ai/WORKFLOW.md`
- 타이포 광고 영상 (Remotion, 수동/코덱스): `shorts/promo/README.md` + `shorts/promo/GUIDE_TYPOGRAPHY.md`
- 카드뉴스 → 캐주얼 숏폼 (코덱스 담당): `CODEX_VIDEO_DESK/README.txt`
- **카드뉴스 기사 작성 (Claude 담당, 주제선정→영상/카드뉴스 분기)**: `cardnews/templates/article_authoring_spec.md`
- **멀티PC 독립생산 + 일러스트 Drive 공유**: `CODEX_VIDEO_DESK/MAINTENANCE/MULTI_PC_STANDALONE_AND_LIBRARY_SHARING_GUIDE.md`
- **최근(2026-06) 변경 종합**: `CODEX_VIDEO_DESK/MAINTENANCE/PHONESPOT_UPDATES_2026-06_GUIDE.md`
- **노트북 개발 / 사무실 실행 / GitHub 연동**: `_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md`

각 Read 결과는 다음 작업의 컨텍스트로 직접 활용. 사장님이 "수집해줘" / "발행해줘" / "매커니즘 알려줘" 같은 짧은 명령만 줘도 위 가이드로 모든 형식·룰을 자동 적용해야 함.

---

## STEP 2 — 작업 유형별 진입점

| 사장님 명령 패턴 | 첫 행동 |
|---|---|
| "신규 수집" / "news 수집" / "신규 카드뉴스" | (1) 시트 `유튜브_인사이트` + `메타_인사이트` Read + ★ **채널 운영 시트 (메타·당근·카카오·네이버·스레드·인스타) 최근 7일 진행사항 스캔 → `store-active+30%` 매장 진행 캠페인 강제 후보** (2) `cardnews/articles/*.json` Glob → 기존 발행 토픽 중복 회피 (3) `INSTRUCTIONS_CARDNEWS.md` Step 1 룰 + 4 라인 병렬 WebSearch (매장 진행 키워드 반영) (4) 풀 후보 표 + 가중치 라벨 (yt / meta / store-active / season / dup / 회피) |
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
| "유튜브 학습" / "인사이트" / **스크립트·카피 작성 시** | `ads/YOUTUBE_LEARNING.md` + Drive `phonespot_cardnews_state/youtube_insights.md` Read → 키워드/후킹 자동 반영 |
| "메타 학습" / "광고 카피" / "광고 인사이트" / **카피·후킹 작성 시** | `ads/META_LEARNING.md` + Drive `phonespot_cardnews_state/meta_insights.md` Read → Top 키워드·헤드라인 패턴·카톡전환 우수 캠페인 자동 반영 |
| "KT다이렉트샵" / "KT 관리대장" | `ads_kt/README_FOR_AI.md` |
| "카드뉴스 기사 써줘" / "주제 뽑아줘" / "기사 만들어줘" | `cardnews/templates/article_authoring_spec.md` → 주제제안(content_guide)→사실수집→기사 JSON 저장. 영상만이면 카드이미지·image_prompts 생략 |
| "부사수 셋업" / "새 PC" / "멀티PC" / "독립 셋업" | `부사수PC_원클릭_셋업.bat`(빈 PC 한 파일) + MULTI_PC 가이드 |
| "일러스트 공유" / "라이브러리 동기화" / "허브" | 패널 "관리>라이브러리 동기화" 또는 `라이브러리_공유_동기화.bat`. 허브=Drive `PhoneSpot_Library`(데스크톱 동기), 경로파일 `shorts/config/library_share_path.txt` |
| "주제(기사) 깃에 올려" / "전파" | `기사_깃에_올리기.bat`(대표 push) → 부사수 git pull |
| "노트북 개발" / "깃허브 연동" / "사무실에서 실행" / "이어받기" | `_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md` — 노트북=개발(push), 사무실=실행(pull). clone/pull/push 명령 포함 |

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
| **부사수 PC 원클릭 셋업** | `CODEX_VIDEO_DESK/부사수PC_원클릭_셋업.bat` | 빈 PC 1파일: git/node/python+clone+풀셋업 |
| **풀 생산기 셋업(클론 후)** | `CODEX_VIDEO_DESK/SETUP_FULL_PRODUCER.bat` | 카드뉴스+영상 의존성+임베딩+검증 |
| **환경 점검** | 패널 "관리>환경 점검" / `shorts/scripts/codex_producer_check.py` | 자원 PASS/FAIL |
| **기사 작성 스펙** | `cardnews/templates/article_authoring_spec.md` | Claude 기사 JSON 작성 기준 |
| **기사 git 전파** | `CODEX_VIDEO_DESK/기사_깃에_올리기.bat` | articles+.gitignore commit&push (articles는 git 추적=중복방지 DB) |
| **일러스트 공유 동기화** | 패널 "관리>라이브러리 동기화" / `CODEX_VIDEO_DESK/라이브러리_공유_동기화.bat` | Drive 허브 양방향 병합. 렌더 직전 자동 동기화도 됨 |
| **일러스트 허브 경로설정** | `CODEX_VIDEO_DESK/일러스트_공유허브_경로설정.bat` | PC별 1회, Drive 로컬경로 기입 |
| **라이브러리 백업/스케줄** | `라이브러리_백업.bat` / `라이브러리_자동백업_스케줄_등록.bat` | 스냅샷(회전10) / 매일 09:00 |
| **수신 PC 자동 코드 업데이트** | `CODEX_VIDEO_DESK/수신PC_자동업데이트_켜기.bat` | 마커 ON → 패널 시작 시 git pull(부사수만) |

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

## STEP 7 — 리포 위생: 중복 실행파일·줄끝 오염 방지 (★ 2026-06-08)

### 왜 생겼나
1. **모노레포가 겹치는 하위트리를 import로 합침** — 루트와 `CODEX_VIDEO_DESK/`가 각자 setup/sync 스크립트를 들고 들어와 사본 누적(canonical 위치 규칙 부재).
2. **MAINTENANCE의 MIGRATE/INSTALL/APPLY `.py`가 `.bat/.ps1`을 문자열 템플릿 생성·`shutil.copy2`로 복사** → byte 동일 사본 + 템플릿 복붙 본문 미수정 → "이름 다른데 내용 같은" 버그.
3. **`.gitattributes` 부재** → CRLF/LF/BOM 혼재 → 유령 diff·편집 truncation.
4. **다중 writer**(노트북 + 실행 PC 둘 다 push) → 같은 파일 병렬 수정 → diverge/충돌. STEP 0의 "push는 노트북만"으로 차단.

### 규칙
1. 실행파일 **단일 위치(SSOT)** — 루트 편의 복사 금지, 필요하면 사본 말고 얇은 래퍼.
2. 새/수정 `.bat`·`.ps1` 커밋 전 **중복 md5 점검**(아래). 동일 발견 시 통합.
3. 템플릿 복붙 시 **본문 대상명까지 교체**.
4. `.gitattributes`로 줄끝 고정 + 한글 bat BOM 유지.
5. `.bat/.ps1` 편집은 **HEAD 재구성+치환**(Edit툴 truncation 회피), 편집 후 `file`로 BOM·줄끝 검증.

### 중복 점검 스니펫
```
git ls-files -z | grep -ziE '\.(bat|ps1|cmd|vbs)$' | xargs -0 md5sum | sort \
 | awk '{h=$1;$1="";a[h]=a[h]"\n  "$0;c[h]++} END{for(h in a) if(c[h]>1) print c[h]" identical:"a[h]"\n"}'
```
※ `CODEX_VIDEO_DESK/MAINTENANCE/`의 APPLY/RUN/ROLLBACK은 패치 적용/롤백 툴 — 중복 아님, 삭제 금지.

---

## STEP 8 — 변경 이력 (CLAUDE.md 자체)

- 2026-06-04: 신설. STEP 1~7 박음. 6 가이드 진입점 정렬. 하네스 시작.
- 2026-06-05: ads/ + ads_kt/ + 메타 자동화 합류. STEP 2 명령 패턴 3개 추가, STEP 4 진입점 3개 추가, STEP 5 폴더 구조에 ads/ ads_kt/ 박음.
- 2026-06-05: 유튜브 자동 학습 루프 합류. `ads/YOUTUBE_LEARNING.md` + `youtube_sync.gs`의 generateYouTubeInsights (Gemini API 분석, 매일 03:40 자동). 스크립트·카피 작성 시 "유튜브_인사이트" 시트 Read 의무화.
- 2026-06-05: 유튜브 학습 — 시트 탭 → **Drive MD 파일** 로 전환. Apps Script가 매일 03:40 `phonespot_cardnews_state/youtube_insights.md` Drive에 저장 → desktop sync로 로컬. INSTRUCTIONS_CARDNEWS.md (외부 신호 다음 자체 학습 섹션) + INSTRUCTIONS_SHORTS.md (Step 0) 룰 추가. 후보 점수 가중치 +30%/+20%/+50%/-40% 자동 적용.
- 2026-06-07: promo(홍보영상) 트랙 하네스 합류. STEP 2 명령 패턴 + STEP 4 진입점 + STEP 5 폴더에 등록. 진입점=`shorts/promo/README.md`(Remotion 기생, 나레이션 없음·효과음+음악·스타일별 SFX·무드 음악풀). ※ `_docs/INSTRUCTIONS_SHORTS.md`는 옛 MoviePy/Typecast 설계라 현행 Remotion과 불일치 — 갱신 필요(미정).
- 2026-06-08: promo_ai(실사 AI 광고) 트랙 하네스 합류. STEP 1 조건부 Read 섹션 신설 + STEP 2 명령 패턴 + STEP 4 진입점 + STEP 5 폴더에 등록. 진입점=`shorts/promo_ai/README.md` + `WORKFLOW.md`(Higgsfield MCP Kling 3.0 1순위 / Seedance 2순위 / ffmpeg 합치기, Claude 담당, 15초 9:16). 결제 상태: Higgsfield Free 3 credits (결제 검토 중, STARTER $19/월·연납 또는 PLUS $39-49/월).
- 2026-06-08: **멀티PC 독립생산 + Claude 기사작성 + Drive 일러스트 공유 합류.** 핵심:
  - **기사작성=Claude**: `article_authoring_spec.md`(주제선정→사실수집→기사 JSON). 기사 cards 텍스트=영상 대본. 출력 분기: 영상(일러스트 자동매칭, 카드이미지 불필요) vs 카드뉴스(+카드이미지). STEP1/2/4 등록.
  - **주제 git 추적**: `cardnews/articles/`를 .gitignore에서 해제 → 부사수가 git pull로 주제 수신 + 누적=중복방지 DB. `기사_깃에_올리기.bat`(대표 push).
  - **일러스트 공유**: Drive 데스크톱 공유폴더 `PhoneSpot_Library`(허브). `codex_library_sync`(양방향 비파괴 병합), 경로=`shorts/config/library_share_path.txt`(git 제외, PC별). **렌더 직전 워커가 자동 동기화**(best-effort, 렌더 안 막음). 패널 "관리>라이브러리 동기화" 버튼도 있음. ※ 대량 이미지는 MCP base64 부적합 → Drive 데스크톱이 정답.
  - **부사수 1파일 셋업**: `부사수PC_원클릭_셋업.bat`(winget+clone+`SETUP_FULL_PRODUCER`). 코드 자동전파=옵트인 `수신PC_자동업데이트_켜기.bat`(마커 방식; 옛 env `PHONESPOT_AUTO_UPDATE`는 폐기).
  - **패널 v23**: 버전 단일출처(server.py `PANEL_VERSION`만 올리면 ps1이 읽음), "환경 점검" 버튼, 렌더 취소/진행, 청크 수동분할, remote_ 폴더 제거, 유튜브 캡션(타임스탬프·출처 제거).
  - **운영 안정화**: 한글 내용 .bat은 UTF-8 BOM 필수(없으면 cmd가 한글 깨뜨려 echo가 명령으로 실행됨) — 한글 bat 전부 BOM+ASCII화. `start_hidden.ps1`은 ASCII 주석만(BOM 없는 PS는 CP949 오독). `illustration_tag_db.json` NUL 손상 복구(101개 유지).

- 2026-06-08: **노트북 개발 / 사무실 PC 실행 / GitHub 연동** 워크플로 가이드 합류
  (`_docs/DEV_LAPTOP_OFFICE_RUN_GITHUB.md`). 노트북=개발(Claude Code 편집·push), 사무실=실행(pull·패널·
  스케줄러·렌더·카드수집). GitHub=코드 허브. clone/pull/push 명령 + git-pull로 자동적용 안 되는 예외
  (ads Apps Script 배포·_secrets·일러스트Drive허브) 명시. STEP1 조건부Read + STEP2 명령패턴 등록.

- 2026-06-08: **STEP 0 머신 역할 모델 신설(최우선).** 노트북=push only, 실행 PC=pull only, 메인 PC=이미지 자산. 적용=수신PC_자동업데이트 또는 git pull --ff-only/막히면 reset --hard origin/main. DEV_LAPTOP_OFFICE_RUN_GITHUB.md의 "사무실도 push" 모델 폐기.
- 2026-06-08: **STEP 7 리포 위생 신설.** 중복 실행파일·줄끝 오염 원인(모노레포 import 중복·자동생성 복사·.gitattributes 부재·다중 writer)+규칙. .gitattributes 추가. 루트 죽은 사본 6 + CODEX 비접두 setup 2 = 8개 삭제.
- 2026-06-08: **유튜브 시트 헤더 3행 구조 박음.** 유튜브 시트는 행 1(제목) + 행 2(네비) + 행 3(컬럼 헤더) + 행 4~ 데이터. `youtube_sync.gs` 상수 `SHEET_DATA_START_ROW = 4`(2/3 ❌). 정렬 시 행 1-3 절대 포함 금지. 깨졌을 때 복구 함수 `repairYouTubeSheetHeaders`(A열 "날짜" 행 찾아 위 1행=네비, 두 행을 행 2-3 위치로 복원). 가이드 `ads/YOUTUBE_LEARNING.md` 시트 구조 절대 룰 섹션 박음.
- 2026-06-10: **메타 자동 학습 루프 합류 (유튜브 패턴 그대로).** Apps Script `meta-sync.gs`에 `generateMetaInsightsMarkdown` 함수 추가 → 매일 01:45 자동 분석 (`메타_소재` + `메타_통합` 시트 → Gemini → Drive `phonespot_cardnews_state/meta_insights.md` 덮어쓰기). 활용처: ① 광고 카피 작성 (generator.html) ② 카드뉴스/쇼츠 후킹 reference. 신규 가이드 `ads/META_LEARNING.md` (YOUTUBE_LEARNING.md 패턴), `_docs/INSTRUCTIONS_CARDNEWS.md`에 "자체 메타 광고 학습" 섹션 (유튜브와 가중치 합산), `_docs/INSTRUCTIONS_SHORTS.md` Step 0.5 추가. 트리거: setupTriggers() 01:30 syncAll + 01:45 generateMetaInsightsMarkdown.
- 2026-06-10: **UTM_매핑 시트 + 자동 발견 합류.** 메타 API campaign_name(한글) ↔ GA4 utm_campaign(영문 슬러그) 불일치로 메타_통합 시트 GA4 컬럼 공란 문제 해결. `UTM_매핑` 시트 (A: 한글 / B: 영문 슬러그 / C: 첫 발견일 / D: 상태 / E: 메모) 자동 생성. `syncMetaCampaignIntegrated` 안에서 `autoDiscoverCampaigns_` 호출 → 새 한글 캠페인 발견 시 A열 자동 추가 (B열 비움, 상태 ⚠️ 매핑 필요). 메타_통합 GA4 매칭 수식이 VLOOKUP으로 한글 → 영문 변환 후 매칭. 사용자는 새 캠페인 추가 시 B열 1줄만 입력. 추가: `notifyUnmappedCampaigns_`, `showUnmappedCampaigns` (메뉴 "🔍 미매핑 캠페인 보기").
- 2026-06-10: **메타_통합 → 광고그룹(adset) 단위로 전환 (★ 1차 자동화 완성).** 사용자 메타 운영 단위 = 광고그룹 (BA/VA 등) + GA4 utm_campaign 에 광고그룹 식별자(한글) 박혀있음. 코드 변경: ① Meta API `level=campaign` → `level=adset` ② fields에 `adset_id, adset_name` 추가 ③ 메타_통합 시트 19컬럼 구조 (날짜/캠페인ID/캠페인명/광고그룹ID/광고그룹명/노출/클릭/지출/CTR/CPC/GA4세션/카톡클릭/전화클릭/시티마켓/카톡전환률/카톡당CPC/문의수/개통수/메모) ④ `autoDiscoverCampaigns_` → `autoDiscoverAdsets_` (광고그룹명 기준) ⑤ GA4 매칭 수식 D열(캠페인명) → E열(광고그룹명) 기준. UTM_매핑 시트 헤더 "메타 캠페인명" → "메타 광고그룹명". 메뉴 항목 "📊 캠페인별 통합" → "📊 광고그룹별 통합", "🔍 미매핑 캠페인 보기" → "🔍 미매핑 광고그룹 보기". 메타 잠금(phonespot86 비정상 활동 감지) 풀린 후 정상 작동 확인.
- 2026-06-10: **메타 phonespot86 비정상활동 잠금 사건 → 복구 + 대응 정리.** 디버거 결과 토큰 Valid(만료없음, scopes 정상) → 토큰 자체 문제 X, 광고 계정 또는 앱 권한 문제. 원인 추정: 평소 안 쓰던 디바이스/IP에서 phonespot86 로그인 + 개발자 콘솔 단시간 다중 접근. 자동화 코드 자체는 안전(rate limit 미달, 정책 위반 X). 재발 대응: 2FA + 로그인 알림 ON, 본인 계정(313jongmin)을 비즈니스 매니저 관리자로 추가(백업 플랜), 1회 더 잠기면 그때 빈도 조정.
- 2026-06-10 (예정): **인스타 시트 자동화 — 인증 안정화 후 작업.** Instagram Graph API 사용(메타 산하). 현재 META_TOKEN scopes에 `instagram_basic`, `instagram_manage_insights` 없음 → 비즈니스 매니저에서 시스템 사용자 `phonespot-sync` 에 권한 + 인스타 비즈니스 계정 자산 추가. 신규 토큰 발급 X(기존 토큰에 권한 자동 반영). 가져올 데이터: 게시물별 조회수/좋아요/리치/permalink/caption + 일별 팔로워 추이(30일 한도). 인스타 시트 컬럼: A날짜/C주제/D링크/E조회수/F좋아요/G팔로워 자동, H운영메모/I비고 수동. **메타 잠금 안정화 며칠 후 진행** (인증 직후 권한 변경하면 의심 트리거 가능).

이 파일이 업그레이드되면 변경 이력 1줄 추가. 가이드 추가·제거 시 STEP 1 리스트 동기화.
