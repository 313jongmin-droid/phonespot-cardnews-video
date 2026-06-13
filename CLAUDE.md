# 폰스팟 카드뉴스·영상 프로젝트 — 클로드 부트스트랩

> **새 클로드 세션이 이 폴더를 열면 가장 먼저 이 파일을 읽음.**
> 모든 가이드·매뉴얼·매커니즘 진입점은 여기. 다른 세션과 같은 공식으로 작업하려면 **아래 STEP 1을 반드시 먼저 실행**.
>
> **이 폴더에 들어온 모든 task는 이 하네스 구조를 그대로 이어받는다.** 임의 위치에 1회성 요약본을 만들지 않는다.
> 구조 = ① 헤드(CLAUDE.md, 진입·라우팅) → ② `_docs/SYSTEM_MAP.md`(대단원 A~J 개발 맵, 수정 인덱스)
> → ③ 각 대단원 마스터 가이드. 작업·문서화 모두 이 3층 안에서만.

---

## ★ 문서화 규약 — "가이드 박아" 명령 처리법 (최우선, 항상 적용)

사장님이 **"가이드 박아 / 가이드에 넣어 / 문서화해 / 기록해"** 라고 하면 (직전 설명을 다시 안 해도)
**아래 절차로 기존 구조에 합류시킨다. 절대 아무 데나 새 요약본·1회성 md 생성 ❌.**

1. **대상 대단원 식별** — 방금 한 작업이 `_docs/SYSTEM_MAP.md` 0번 인덱스의 어느 대단원(A~J)인지 정한다.
2. **그 대단원 섹션을 갱신** — 경로·핵심 함수·"수정 시 읽을 것"·**함정**에 이번 변경/사실을 박는다(기존 항목 옆에 추가, 통째 교체 X).
3. **SYSTEM_MAP 변경이력 1줄** — 파일 맨 끝 "변경 이력"에 날짜+요약 1줄.
4. **라우팅이 바뀌었으면 헤드(CLAUDE.md)도 갱신** — 새 진입점/명령 패턴/파일이면 STEP 1·2·4 동기화.
5. **CLAUDE.md STEP 8 변경이력 1줄** — 하네스 차원 변경(새 가이드/명령/구조)일 때만.
6. **새 대단원이 필요하면** SYSTEM_MAP에 단원을 신설하고 0번 인덱스 표에 등록(없는 분류를 억지로 끼우지 말 것).

원칙: **사실만 박는다**(추측·미사여구 X). 경로는 리포 루트 상대경로. 줄번호는 검증된 것만.
새 task·다른 task가 들어와도 이 규약과 SYSTEM_MAP만 읽으면 같은 공식으로 이어받는다.

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

> **★ 코드/기능 수정·디버깅이면 먼저 `_docs/SYSTEM_MAP.md`(클로드용 개발 맵)부터.**
> 기능이 대단원(A 패널 / B 카드뉴스 / C 영상 / D 라이브러리·멀티PC / E 의미매칭·임베딩 /
> F Git·멀티PC·리포위생 / G 광고 / H 자동화 / I 인코딩규칙 / J 기사스펙)으로 갈려 있고,
> 각 단원에 경로·핵심 함수·"수정 시 읽을 것"·함정이 박혀 있음. **해당 단원만 읽고 고치면 됨**(전체 X).
> 콘텐츠 작업(수집·발행·캡션)은 아래 마스터 가이드대로 진행.

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
- **광고 운영 자동화 (메타·인스타·네이버·인사이트)**: `ads/SNS_AUTOMATION_ROADMAP.md`(채널별 가능여부 매트릭스) + 작업 채널 가이드 (`ads/META_AUTOMATION.md` / `ads/NAVER_AUTOMATION.md` / `ads/INSTAGRAM_AUTOMATION_PENDING.md`(완료 헤더))
- **멀티 브랜드 모노레포 (KT/국민/진짜폰스팟 등 신설)**: `ads/MULTI_BRAND_ARCHITECTURE.md` — `_shared/`+`brands/<brand>/` 분리, clasp+GitHub, Phase 1~4

각 Read 결과는 다음 작업의 컨텍스트로 직접 활용. 사장님이 "수집해줘" / "발행해줘" / "매커니즘 알려줘" 같은 짧은 명령만 줘도 위 가이드로 모든 형식·룰을 자동 적용해야 함.

---

## STEP 2 — 작업 유형별 진입점

| 사장님 명령 패턴 | 첫 행동 |
|---|---|
| **"수정" / "고쳐줘" / "디버깅" / "기능 추가" / "왜 안돼" / 코드 작업** | `_docs/SYSTEM_MAP.md` 0번 인덱스에서 대단원(A~J) 찾기 → 그 단원 "수정 시 읽을 것"만 Read → 수정 → "함정" 체크 → 검증. 전체 파일 통독 ❌ |
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
| **"광고 생성기" / "카피 생성기" / "변주" / "후킹 구조" / "신규 컨셉" / "이미지 프롬프트" / generator.html·meta-sync 생성기 함수 작업** | `ads/IMPLEMENTATION_GUIDE_2026-06-09.md` (생성기 단일 정본: §0 상단 "최신 아키텍처" 먼저 → §5 함수인덱스 · §6 프롬프트). 변경 상세 = `CLAUDE.md` STEP 8 "2026-06-12 (세션 2)" |
| "KT다이렉트샵" / "KT 관리대장" | `ads_kt/README_FOR_AI.md` |
| "전체 새로고침" / "통합대시보드 갱신" / "매트릭스 갱신" / "KPI 갱신" | `Code.gs` `refreshAll()` 호출. GA4+메타+유튜브 sync → 인사이트 MD → 매트릭스/KPI/추세 차트(메타_통합 H·네이버_통합 H 자동 합산). 시트 매핑 정본 = SYSTEM_MAP G 단원 "2026-06-11 세션" |
| "네이버 동기화" / "네이버 광고그룹" / "네이버 UTM 매핑" | `ads/NAVER_AUTOMATION.md`. `syncNaverIntegrated` 매일 02:15. HMAC-SHA256 + `/stats` 호출 시 `statType` 빼기 + `ids`는 콤마 구분(JSON 배열 X). KT 자동 제외 필터 |
| "인스타 동기화" | `ads/INSTAGRAM_AUTOMATION_PENDING.md`(완료 헤더). `syncInstagramDaily` 매일 02:00. INSTAGRAM_BUSINESS_ID 등록 + 토큰 신규 발급(scopes는 발급 시점 확정) |
| "SNS 자동화" / "스레드 자동화" / "카카오 채널 자동화" / "틱톡 자동화" / "네이버 블로그 자동화" | `ads/SNS_AUTOMATION_ROADMAP.md` 매트릭스 확인. 카카오 채널·당근·네이버 블로그 = API 없음 확정 |
| "멀티 브랜드" / "KT 시트" / "국민인터넷 시트" / "진짜 폰스팟" / "브랜드 분리" / "공용 코드 배포" / "clasp" / "push-all" | `ads/MULTI_BRAND_ARCHITECTURE.md`. `_shared/` 공용 + `brands/<brand>/` 분리. Phase 1(Apps Script만) → 다른 task `generator.html` 종료 후 시작 |
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
| **메타 API 자동화** | `ads/code/apps_script/meta-sync.gs` + `ads/META_AUTOMATION.md` | 메타 광고 + GA4 통합 + 인스타(syncInstagramDaily 매일 02:00) |
| **네이버 검색광고 자동화** | `ads/code/apps_script/naver-sync.gs` + `ads/NAVER_AUTOMATION.md` | 광고그룹 단위, HMAC-SHA256, KT 자동 제외, 매일 02:15 |
| **SNS 자동화 가능성 매트릭스** | `ads/SNS_AUTOMATION_ROADMAP.md` | 콘텐츠/광고 채널별 가능여부 + 권장 순서 |
| **멀티 브랜드 아키텍처 (제안)** | `ads/MULTI_BRAND_ARCHITECTURE.md` | `_shared/`(공용 코드) + `brands/<brand>/`(데이터·설정) + clasp+GitHub. Phase 1~4. KT/국민/진짜폰스팟 확장 대비 |
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
- 2026-06-11: **`generateMetaInsightsMarkdown` 함수 누락 사고 + 복구 + 운영 룰.** 사용자가 메타_통합 광고그룹 단위 전환 시 `meta-sync.gs` 전체 코드 통째 교체 → 인사이트 MD 패치 함수 사라짐. 동기화_로그에 6/10 10:21 마지막 ✅ 이후 매일 01:45 트리거가 함수 없어서 catch 안 되고 빠짐 (로그 미기록). 사용자가 전체새로고침 시 `generateMetaInsightsMarkdown is not defined` 에러로 노출됨. 복구: `outputs/meta_insights_patch.js`(루트 `meta_insights_patch.js` 동일) 통째 `meta-sync.gs` 끝에 박기 + `setupTriggers` 재실행. **운영 룰: 코드는 함수 단위로 박을 것. 통째 교체 ❌.**
- 2026-06-11: **GA4 자동수집 확정 — `syncAll` 01:30 내장.** `fetchGA4Daily`는 `syncAll`(매일 01:30) 안에서 자동 호출. 6/11 01:34:57 ✅ 성공 확인. 별도 트리거 등록 불필요. (질문 자주 나와서 박음)
- 2026-06-11: **SNS 자동화 가능성 매트릭스 신설** `ads/SNS_AUTOMATION_ROADMAP.md`. 콘텐츠 채널(유튜브 완료/인스타·스레드=메타토큰 권한추가/틱톡=별도앱/네이버블로그·카페=API없음) + 광고 채널(메타 완료/구글·카카오·네이버 가능/당근 API없음). **권장 순서**: 인스타(1) → 스레드(2) → 틱톡(3).
- 2026-06-11: **인스타 시트 자동화 완료.** `meta-sync.gs` 내 `syncInstagramDaily()` + 매일 02:00 자동 트리거. INSTAGRAM_BUSINESS_ID=`17841474706647015` (@phonespot.kr) PropertiesService 등록. 매칭 키 D열 permalink — 신규 append / 기존 E·F·G만 갱신. 정렬: timestamp 오름차순(최신 하단). 메뉴 `📷 인스타 동기화` 수동 테스트. **중요 학습**: 메타 시스템 사용자 토큰 권한은 **토큰 발급 시점에 확정** — 기존 토큰에 자산 추가만으로는 scopes 안 늘어남, **새 토큰 발급 필요.** 가이드: `ads/INSTAGRAM_AUTOMATION_PENDING.md` 완료 헤더로 갱신, `ads/SNS_AUTOMATION_ROADMAP.md` 인스타 ✅.
- 2026-06-11: **스레드 자동화 보류 결정.** 메타 비즈매니저 시스템 사용자 `phonespot-sync` 자산 추가 화면에 Threads 옵션 없음 확인 → Threads API가 시스템 사용자 토큰 모델 미지원 추정. 대안: 별도 앱 + 개인 OAuth (별도 검토) 또는 메타 정책 변경 대기. `ads/SNS_AUTOMATION_ROADMAP.md` 2순위 상태에 박음.
- 2026-06-11: **카카오톡 채널 자동화 불가 확인.** developers.kakao.com 도구 페이지에 채널 통계 조회 API 없음 (로그인/메시지/채널 인터랙션만). 카카오톡 채널 통계 API는 대규모 비즈니스 파트너 한정 정책으로 추정. 일반 비즈니스 채널 인증으로 자동수집 불가. `ads/SNS_AUTOMATION_ROADMAP.md` ❌ 불가 박음. 수기 입력 유지.
- 2026-06-11: **네이버 검색광고 자동화 완료 (메타_통합 패턴 그대로).** 신규 파일 `naver-sync.gs` + 시트 `네이버_통합` (19컬럼, 메타_통합 동일) + `네이버_UTM_매핑` (메타와 분리). 별도 메뉴 `🔍 네이버 자동화` + 별도 트리거 `setupNaverTriggers` (매일 02:15). PropertiesService: `NAVER_API_LICENSE` / `NAVER_SECRET_KEY` / `NAVER_CUSTOMER_ID=1559128`. **HMAC-SHA256 인증**. KT 캠페인 자동 제외 (`['KT', '다이렉트샵']` 필터). **API 디버깅 학습**: `/stats` 광고그룹 통계는 ① `statType` 파라미터 자체를 **빼야 함** (ADGROUP/AD/AD_DETAIL 등 다 400 거부), ② `ids`는 **콤마 구분 문자열** (`adgroupIds.join(',')`), JSON 배열은 거부. 30일 백필로 광고그룹×일자 정상 입력 확인. 가이드 `ads/NAVER_AUTOMATION.md` 신설.
- 2026-06-11: **통합대시보드 자동 합산 패치.** `Code.gs` `updateChannelMatrixWithGA4` + `updateKPISummary` + `addTimeSeriesChart` 시트 매핑 변경. `channels`/`ADS`/`trendChannels` 배열에 `adSheet`/`impCol`/`clkCol`/`spdCol` 분리 → 메타→`메타_통합`(H 지출), 네이버→`네이버_통합`(H 지출). 구글/카카오/당근은 기존 E/F/G 그대로 = **다운그레이드 없음**. 메뉴 ⚡ 전체 새로고침 1회로 매트릭스/KPI/추세 차트 모두 광고그룹 단위 자동 합산. SYSTEM_MAP G 단원에 6/11 세션 블록 박음 (정본 = `ads/` 가이드 5종).
- 2026-06-11: **멀티 브랜드 모노레포 아키텍처 제안.** `ads/MULTI_BRAND_ARCHITECTURE.md` 신설. `_shared/`(공용 코드 = `apps_script/`+`cardnews/`+`shorts/`+`automation/`) + `brands/<brand>/`(데이터·설정 분리, `config.json`+`.clasp.json`+`articles/`+`images/`+`output/`) + clasp+GitHub 단일 진실 원천. **공용 업데이트** = 1곳 수정 → `./push-all-apps-script.sh` 1줄 → N개 브랜드 동시 반영. **브랜드 전체 통합** = 한 폴더에 광고/카드뉴스/영상 모든 모듈. **Phase 1**(Apps Script만 멀티 배포) 다른 task `generator.html` 작업 종료 후 시작. Phase 2/3/4 = 카드뉴스/영상/자동화 순차 확장. KT/국민인터넷/진짜 폰스팟(판매점 가입형) 등 확장 대비. **충돌 방지 = 책임 분담 표** (gen.html=다른 task / Code.gs·meta-sync·naver-sync=광고운영 task / cardnews·shorts=영상 task). 자산은 git 비전파 (STEP 0/7 룰 그대로 = `images/`·`output/`·`node_modules/`·`_secrets/`). STEP 1·2·4 동기화 (조건부 Read + 명령 패턴 + 진입점 추가).
- 2026-06-11: **Phase 1 셋업 완료 (clasp + GitHub Actions 자동 배포).** 로컬 `apps_script/` clasp clone(9파일) + `.gitignore` 보안(`.clasp.json` 제외) + Git for Windows 2.54.0 + GitHub repo `313jongmin-droid/phonespot-cardnews-video`(commit 5e0a776) + Actions workflow `.github/workflows/deploy-apps-script.yml`(Node 20 + clasp 3.3.0 + clasp push --force) + Secrets `CLASPRC_JSON`/`CLASP_JSON`. **동작 검증**: workflow_dispatch 수동 실행 27초 성공. git push 시 Apps Script 콘솔 자동 배포. **함정**: `CLASP_JSON` Secret은 **한 줄 압축 JSON 필수** (12줄 multiline은 `JSON5: invalid character 'P' at 12:1` 에러로 실패). `rootDir`은 `"."` 권장. PowerShell `%USERPROFILE%` 대신 직접 경로 `C:\Users\<user>\.clasprc.json`. **2026-06-16부터 Node 20 deprecation** → workflow `node-version` 20→24 1줄 수정 필요. **clasp push --force는 콘솔 변경 무시 강제 덮어쓰기** → 다른 task가 콘솔 직접 수정 중이면 작업 사라짐, 책임 분담 표 엄수. 멀티 브랜드 활성화(KT/국민/진짜폰스팟)는 신설 시점에 workflow step 추가 + `CLASP_JSON_<BRAND>` Secret 추가로 1줄씩 확장. 정본 = `ads/MULTI_BRAND_ARCHITECTURE.md` "Phase 1 셋업 완료" 섹션.

- 2026-06-12: **광고 소재 생성기(generator.html) 대규모 리팩 + Apify 벤치마크 합류 (34 task).** 진입점: `ads/IMPLEMENTATION_GUIDE_2026-06-09.md` (단일 클로드 참조 문서, §6 함수 인덱스 + §11~12 디자인 토큰 + §14 다음 작업 후보). 핵심 변경:
  - **카피 생성 2모드**: 📚 라이브러리·벤치마크 기반 (템플릿 + 검증 카피) + 🤖 LLM 프롬프트 (Claude/GPT 챗용). 신규 컨셉 자유 입력바, 옵션 C 컬럼 시스템은 폐기.
  - **buildCopyPrompt 강화**: brand voice 5가지 + 단어 반복 ≤3회 + 길이 분포 강제 (5/7/8/5) + 라이브러리 우수 사례 박힘 + 벤치마크 후킹 reference + 출력 마크다운 표 + 자가검증.
  - **buildImagePrompt 강화**: `analyzeWinningDesigns_` (광고명 색상 키워드 추출) + `buildLibraryDesignBlock_` + `buildBenchmarkDesignBlock_` 자동 박힘.
  - **벤치마크 (Apify Meta Ad Library)**: `curious_coder/facebook-ads-library-scraper` ($0.00075/광고). meta-sync.gs 신규 함수 11개. generator.html 🎯 벤치마크 탭 (검색·시트 저장·자동 import·삭제 UI·디자인 패턴 분석). 시트 `벤치마크_경쟁사_광고` 19컬럼. 운영일수+채널수+변형수 기반 자동 ★등급.
  - **메타 비율 변환**: 1:1 → 4:5/9:16/1.91:1 한글 재구성 프롬프트 (`RESIZE_PROMPTS`).
  - **카테고리 9개**: 휴대폰 / 유심만 / 알뜰폰 / 중고폰 / 키즈폰 / 효도폰 / 공짜폰 / 인터넷 / 인터넷+TV.
  - **폼 통합**: 추가 키워드 폐기 + 강조 감정 + 톤 통합 = 다중 체크박스 9개. 4 form-group 구분선.
  - **디자인 리팩 (Apple HIG)**: Pretendard 폰트, CSS 변수, segmented control 탭, chip 체크박스, subtle shadow, 마이크로 인터랙션 (fadeIn stagger).
  - **styles.html 분리 (C-4)**: Apps Script HtmlService `include` 패턴. Code.gs `createTemplateFromFile + evaluate()`. 다른 브랜드 페이지(generator_internet 등) 만들 때 동일 톤 재사용.
  - **시트 메뉴 정리**: 사용자 도구(벤치마크 수집·JSON Export 등)는 generator.html로 이동. 시트 메뉴 = 자동화·백엔드만.
  - **파일 손상 16회 + 백업본 복구 패턴** — 큰 Edit 누적 시 generator.html 끝부분 잘림. 백업: `ads/code/apps_script/generator.v_2026-06-09_pre-design-refactor.html`. **다음 큰 변경은 통째 Write 권장**.
  - 신규 파일: `ads/IMPLEMENTATION_GUIDE_2026-06-09.md` / `ads/code/apps_script/styles.html` / `_docs/APIFY_INTEGRATION_GUIDE.md` / `ads/data/seed_concept_tags.md`(폐기 마커).
  - **다음 세션 진입**: `ads/IMPLEMENTATION_GUIDE_2026-06-09.md` 먼저 → `ads/README_FOR_AI.md` → 종민 명령.
  - **⚠️ styles.html include 패턴 폐기 (2026-06-12)**: `<?!= include('styles') ?>` 가 styles 파일 없을 때 `Exception: styles 파일을 찾을 수 없습니다` 에러 발생. 종민 결정으로 generator.html에서 include 라인 제거 + 옛 `<style>` 블록 유지. `styles.html` 파일은 참고용으로 남음, 사용 X. Apps Script `<?!= ?>` scriptlet 패턴 사용 시 ① HTML 파일 ② `include()` 함수 ③ `createTemplateFromFile + evaluate()` 셋 다 동시 필요 — 단일 페이지 운영 시 권장 X.

- 2026-06-12: **시드 카드 모델 폐기 → 3종 박스 (라이브러리·벤치마크 매칭) 모델로 재설계.** 종민 결정으로 직전 Task 42의 시드 카드(20개 톤 다양화) 모델이 실사용 안 됨 확인 → 폐기. 새 구조: **버튼 1개 "광고 카피 가이드 생성"** → 결과 3종 박스 (🤖 일반 LLM 프롬프트 파란 / ✨ 라이브러리 매칭 초록 / 🎯 벤치마크 매칭 주황).
  - **매칭 메커니즘**: 폼 카테고리 == 시트 카테고리 컬럼 일치. 라이브러리 박스 = CTR ≥ 슬라이더 (기본 7%), 벤치마크 박스 = 운영일 ≥ 슬라이더 (기본 90일) + 등급 점수 ≥ 슬라이더 (기본 3).
  - **시트 라벨링 필수**: 메타_소재 시트 16열 = `카테고리` 컬럼 (드롭다운 9개: 휴대폰/유심만/알뜰폰/중고폰/키즈폰/효도폰/공짜폰/인터넷/인터넷+TV). 벤치마크_경쟁사_광고 시트 20열 = `카테고리` 컬럼 + 21열 = `후킹 구조` 컬럼 (드롭다운 8개: 질문형/단언형/비교형/한정형/가격강조/감성·공감/위협형/FOMO형). 16/20/21열에 박으면 `getMetaCreativesAsJSON_` (1~15열 setValues), `saveBenchmarkToSheet_` (1~19열 appendRow) 자동 동기화 영역과 충돌 X → **코드 보호 불필요**.
  - **백엔드 변경 (meta-sync.gs)**: `getMetaCreativesAsJSON_` row 범위 15→16열 + `category` 키 박힘. `getBenchmarkForGenerator` row 범위 19→21열 + 옛 `category: row[1]` (BM/CP 구분자) → `kind`로 변경 + 새 `category: row[19]` + `hookStructure: row[20]` 박힘.
  - **프론트 변경 (generator.html)**: `generateCopiesTemplate` / `renderCopies` 폐기. 신규 함수 `generateAdCopyGuide`, `searchLibraryMatching`, `searchBenchmarkMatching`, `buildLibraryEnrichedPrompt`, `buildBenchmarkEnrichedPrompt`, `renderAdCopyGuide`, `copyGeneralPrompt/copyLibraryPrompt/copyBenchmarkPrompt`. 옛 진입점 (`generateCopiesFromLibrary`, `generateCopiesViaLLM`, `generateCopies`) 하위 호환 폴백 유지.
  - **CSS**: 3종 박스 색상 — 일반 #007AFF 파란, 라이브러리 #34C759 초록, 벤치마크 #FF9500 주황 (Apple HIG 시스템 컬러). `.result-box` `.match-card` `.match-empty` 신설.
  - **localStorage**: `gen.minCtr` / `gen.minDays` / `gen.minGrade` 슬라이더 값 저장. 페이지 로드 시 IIFE로 복원.
  - **매칭 0건 처리**: 박스 표시 + "카테고리 라벨링 필요" 안내. 일반 LLM 프롬프트는 항상 표시.
  - **벤치마크 컨텍스트 다름 처리**: 카피 자체 복제 X, 후킹 구조(`hookStructure` 컬럼)만 빈도 집계 → LLM 프롬프트 reference. 경쟁사 가격·상품·매장 정책은 폰스팟과 다름을 명시.
  - **파일 손상 17회째**: Edit 누적으로 generator.html 끝부분 잘림 (fallbackCopy 함수 중간). 백업 `generator.v_2026-06-12_pre-task43.html` 에서 fallbackCopy~끝부분 복구 + loadGuideThresholds IIFE 재추가. 최종 3036라인 정상 (`</script></body></html>` 박힘).
  - **종민 시트 작업 필수**: 16/20/21열 라벨링 안 하면 매칭 영구 0건 (=일반 박스만). 라벨링 후 매칭 차오름. 카테고리 자동 추론 X (정확도 보장 위해).

- 2026-06-13: **매칭 망가짐 진짜 뿌리 = `codex_unique_illustration_guard` 버그 + 포토 우선규칙 (E단원).** 매처가 cpt→중립으로 잘 바꿔도, 바로 뒤 `unique_illustration_guard`가 "중복 중립을 유니크화"하며 **cpt·무관 그림을 되살림**(매처 제외규칙 무시). 수정: 가드에 `_is_bad_variant`(cpt·blocklist 제외) + 중립 필러 반복 허용. **교훈: semantic_match 뒤 비주얼 만지는 모든 단계는 같은 제외규칙 따라야 함.** 추가로 포토는 `photo ≥ best_ill`일 때만 채택(약한 포토가 좋은 일러스트 안 굶김). 재렌더 224859 cpt=0 검증. 남은 appliance/ti_decrease=매처 약한픽/그리디(칩 일러 1개 소진) → 에셋(사진/일러) 보강이 정답, 이름 하드코딩 ❌. 정본 = SYSTEM_MAP E단원.
- 2026-06-13: **실사 포토 라이브러리 (E단원, 사장님 설계).** 일러스트와 별개 폴더 `shorts/public/assets/photos/`에 권리확보 실사를 **한글 파일명(=라벨)**으로 넣으면(예 `갤럭시Z플립8_제품_폴더블.jpg`) 매칭 **1순위**(`PHONESPOT_PHOTO_MIN` 기본 0.80, env) → 애매하면 일러스트 → 없으면 생성요청. `codex_semantic_visual_match.py`에 `build_photo_index`/`best_photo`/0순위 게이트, 선택 시 `{"type":"image","value":"photos/<file>"}`로 기존 `ImageVisual` 렌더. **텍스트 엔진만 써 CLIP 미설치여도 작동.** 폴더 README + `.gitignore`(실사=git 비추적 → **렌더 PC에 직접 있어야 함**). 0.80은 엄격 → 검증 시 0.6. 정본 = SYSTEM_MAP E단원.
- 2026-06-13: **영상 고퀄 batch (재렌더 검증 완료).** 오프닝 후킹 `OPENING_SEC` 2.0초·아웃트로 `OUTRO_SEC` 3.2초(+2), **닫기 CTA를 일러스트→디자인카드 `shorts/src/components/casual/CasualCta.tsx`**(다크+주황글로우+키커+연락처, `Composition.tsx` casual cta 분기 교체), 카드 전환 애니메이션(`CasualCard.tsx` `cardEnter`), 기사 스펙에 **호기심 갭 후킹 공식 5패턴**. 제외: ①CLIP 그림엔진 설치 ⑨실제 제품이미지(셋업/에셋 결정 필요, 대기). **★ CasualCard.tsx도 Edit 누적 truncation → git HEAD 꼬리 splice 복구**(이 파일들 큰 변경은 bash-python). 정본 = SYSTEM_MAP C·J단원.
- 2026-06-13: **SNS 영상 레이아웃·오디오 다듬기 (P2·P3).** 제목바를 첫(hook) 카드에만(`CasualCard.tsx`, 본문 반복 제거+비주얼↑), 자막 세이프영역 점검=안전(변경X), 라우드니스 −14 LUFS(`finalize_sns_video.py` `loudnorm`, env `PHONESPOT_TARGET_LUFS` off 가능), BGM 보류. 영상 길이 35~45초 목표는 코드 아닌 **기사 집필 레버**(`article_authoring_spec.md` §body: 문장 ≤35자·6카드 ≈250자) → J단원. 커버 썸네일은 이미 생성된 `<slug>_cover.jpg` 업로드 시 지정. 정본 = SYSTEM_MAP C·J단원.
- 2026-06-13: **최종 영상 SNS 품질점검 → 의미매칭 범용수정(E) + 후킹(C).** 021 렌더 다각도 점검 결과: ① 일러스트↔자막 오배치(출시일에 방패·온디바이스AI에 보이스피싱) ② 검은 오프닝 약함. 수정: **E단원 `codex_semantic_visual_match.py`** — 중립폴백 정상화(phone/device만, 방패/신문 제외)·`EMBED_MIN_ILLUST` 0.42→0.48·content-gate(CLIP 검증, **단 CLIP 그림엔진 미설치면 무력**)·**미검증 개념아트 `cpt_*` 텍스트매칭 제외**(`_is_unverified_concept`, 이름 하드코딩 대신 카테고리 규칙, env). **C단원 `OpeningHook.tsx`** — 검정→다크+주황글로우+키커 pill+빠른 큰 헤드라인, `OPENING_SEC` 1.5→1.1. **원칙(종민): 1개 케이스용 하드코딩 ❌, 항상 범용.** ti_decrease 등 비-cpt 오배치는 데이터(그림) 교체로. 검증=실행PC 재렌더(150624 양호→152335 cpt 재발=CLIP 미설치 확인→cpt_ 제외로 대응). 정본 = SYSTEM_MAP E·C단원.
- 2026-06-13: **영상 커버(9:16 표지) 자동생성 + 패널 iOS 디자인 리뉴얼.** ① 커버: `shorts/src/Cover.tsx`(CoverShort) + `Root.tsx` id=Cover(1080×1920) + `shorts/scripts/render_cover.mjs`(renderStill, 영상과 같은 번들캐시 재사용) + `run_codex_casual.bat` Step6 직후 best-effort → `RESULTDIR\<RESULTKEY>_cover.jpg`. hook 헤드라인+매칭 일러스트+폰스팟 브랜딩. 정본 = SYSTEM_MAP C단원. ② 패널 디자인: `server.py` INDEX_HTML `<style>`를 iOS/Apple HIG로(브랜드 주황 유지, 토큰+legacy alias, Pretendard Variable, 풀폭 거터, sticky 좌측리스트, 우측 페어 상태\|로그·기록\|결과, 2줄 슬러그행 idx+1, 상단 흰카드+컬러점, 그림자 단일화). `PANEL_VERSION` v24→**v30**. **★ 작업 중 Edit 누적이 INDEX_HTML 꼬리를 truncate(컴파일 깨짐) → 백업 꼬리로 복구. 교훈: server.py 대형 변경은 bash-python(assert+py_compile+태그balance), Edit 누적 금지.** 롤백 백업 `server.py.bak_pre_ios_20260613`. 정본 = SYSTEM_MAP A단원.
- 2026-06-13: **미커밋 기사 유실 사고 + 재발방지 (F 단원).** 다른 task가 만든 `cardnews/articles/021~023_*.json`이 커밋 전(untracked) 상태에서, **노트북에 auto-update 마커(`CODEX_VIDEO_DESK/TEMP/panel/auto_update.on`)가 켜져 있어** 패널 켤 때마다 `git stash --include-untracked`가 돌며 working tree에서 쓸어감 → "article not found" → 준비/렌더 exit 1. 데이터는 `stash@{0}^3`에 보존되어 개별 복원(`git show "stash@{0}^3:<path>" > <path>`). 3건은 이미 origin까지 커밋됨 확인. **재발방지**: ① 노트북 마커 제거(개발기=push only, auto-update OFF가 정상) ② `dashboard/auto_update.cmd`+`부사수PC_원클릭_셋업.bat`의 `stash --include-untracked` 직전에 기사 자동커밋(`git add cardnews/articles` → `git -c user.email=... -c user.name=... commit`, 없으면 no-op) 박음. 운영 룰: 새 기사는 즉시 `기사_깃에_올리기.bat`로 커밋. 정본 = SYSTEM_MAP F 단원 함정.
- 2026-06-13: **`_docs/SYSTEM_MAP.md` 신설 — 클로드용 개발 맵(수정 인덱스).** 기능을 대단원 A~J(패널/카드뉴스/영상/라이브러리·멀티PC/의미매칭·임베딩/Git·리포위생/광고/자동화/인코딩규칙/기사스펙)로 갈라, 각 단원에 경로·핵심함수·"수정 시 읽을 것"·함정을 박음 → 코드 수정 시 전체 통독 없이 해당 단원만 읽음. STEP 1 헤드 콜아웃 + STEP 2 "수정/디버깅" 명령행 등록. **이번 세션 실수정 반영**: ① git bat의 GitHub Desktop 내장 git 탐색을 `for /d %%D in ("%LOCALAPPDATA%\GitHubDesktop\app-*")` 패턴으로 교정(cmd `dir`는 경로 중간 `app-*` 와일드카드 못 풂 → `dir app-*\...git.exe`는 항상 빈 결과 "git not found" 오진). 적용 bat 4개: `런타임파일_git정리_1회.bat`/`기사_깃에_올리기.bat`/`노트북_깃허브_올리기.bat`/`부사수PC_원클릭_셋업.bat`. ② 이 노트북엔 Git for Windows 미설치, git은 GitHub Desktop 내장본(app-3.5.12)만 — 패널 `find_git()`은 정상. ③ 런타임 생성물 git 비추적(`런타임파일_git정리_1회.bat`)으로 "가만히 있어도 M 뜨는" 뿌리 차단.

- 2026-06-12: **지역 컬럼 합류 (Task 44, 전국 확대 대비)** — 폼 + 시트 + 매칭 + LLM 프롬프트에 지역 차원 추가. 자유 텍스트 (드롭다운 X), 공백=전국 의미.
  - **시트 컬럼**: 메타_소재 17열 (Q) = 지역 / 벤치마크 22열 (V) = 지역. 자유 텍스트 입력 (드롭다운 부담 ↓, 매장 신설 자유). `setupLabelingDropdowns` 가 헤더만 설정 (데이터 검증 X).
  - **백엔드 (meta-sync.gs)**: `getMetaCreativesAsJSON_` row 16→17 + `region` 키. `getBenchmarkForGenerator` row 21→22 + `region` 키.
  - **프론트 폼**: `c-region` 텍스트 인풋 (LLM 강조 그룹 안). placeholder = "예: 광교점 (공백이면 지역 고려 ❌, 전국용 카피)".
  - **매칭 로직 (regionMatchScore_)**: 폼 region 공백 → 점수 2 (모든 광고). 폼 region 입력 → 시트 region 일치 또는 includes 매칭 = 점수 2 / 시트 region 공백(=전국) = 점수 1 (폴백) / 시트 region 다른 지역 = 점수 0 (제외). search* 정렬 1차 = region 점수, 2차 = CTR/score.
  - **LLM 프롬프트**: `buildCopyPrompt` 에 `regionBlock` 추가 → ctx.region 있을 때만 박힘. "매장명 박힘 / 카피 일부 40% 지역 한정 톤 / 나머지 전국용".
  - **UI 매칭 카드**: 지역 태그 배지 추가 (초록=라이브러리·주황=벤치마크 매칭 카드 헤드라인 앞). region 공백 시 회색 "전국" 배지. `_regionScore === 1` (폴백)이면 "(폴백)" 텍스트 박힘.
  - **importFromMetaJSON + fetchBenchmarkFromSheetIntoLibrary**: `region` 키 박힘 → library 합류 시 매칭 함수에서 즉시 활용.
  - **파일 손상 18회째**: Edit 누적 → fallbackCopy 함수 중간 잘림 (3009 < 정상 3036). 백업 generator.v_2026-06-12_pre-task43.html 활용 + loadGuideThresholds IIFE 재추가 → 3087라인 정상. **18번째 손상 = 다음 변경은 반드시 통째 Write**.
  - **범용 시스템 가능성 메모**: 종민 의도 = 폰스팟 전국 확대 + 다른 폰매장 SaaS 복제. L1 시트 복제 (즉시 가능) / L2 카테고리·지역 설정 시트 / L3 브랜드 본질 (buildCopyPrompt) 시트 분리 / L4 멀티 테넌트. Task 44 = L2 향한 첫 걸음.

- 2026-06-12 (세션 2): **광고 생성기 대개편 — 변주엔진·프롬프트 단순화·1:1매핑·이미지 배너화·Gemini 의미매칭.** 생성기 정본 매뉴얼 최신 상태 = `ads/IMPLEMENTATION_GUIDE_2026-06-09.md` §0 상단 "최신 아키텍처" 블록. 핵심:
  - **8행 랜덤 변주 엔진** (시드카드 폐기): 결과 = 🎲 변주 8행(1순위) → ✨라이브러리 → 🎯벤치마크. 행 = 후킹×톤 1:1 조합 + 거친 샘플 + 행별 슬로건/이미지 복사 + 다시뽑기. 톤 9 × 후킹 8 = 72방향 추출, 톤≡후킹 중복(공감×공감 등) 차단(`TONE_HOOK_EQUIV`).
  - **후킹 구조 축 신설** (`c-hooks`, 8개: 질문형/단언형/비교형/한정형/가격강조/감성·공감/위협형/FOMO형): 정서 톤과 별개 축.
  - **`buildCopyPrompt` 4단 단순화**: 목적/지정값/규칙/출력. 브랜드본질벽·패턴풀·자가검증 제거. 단일조합 = 한 방향 강제 + 행별 12개(필러 방지).
  - **1:1 매핑** (슬로건·이미지 공통): 변주=참고없음 / 라이브러리=라이브러리만 / 벤치마크=벤치마크만. enrich 함수가 자기 참고만 주입. `buildImagePrompt(ctx,tone,layout,refMode)`.
  - **이미지 = 완성 배너화**: "빈 공간 남겨" 제거 → 헤드라인+서브카피+CTA+스티커 박힌 완성 배너(한글 in-image). **아트 디렉션 매 생성 랜덤**(`AD_STYLE_POOL` 12종) = 매번 다른 디자이너 느낌.
  - **지역·신규컨셉 = 모든 카피 무조건 반영**: `regionEmphasis`/`conceptEmphasis` — 키워드 삽입 ❌, 앵글을 후킹 중심으로, 빠지면 폐기, 표현만 다양화.
  - **Gemini 의미 매칭**(`getSemanticAdMatches`, meta-sync.gs): 컨셉/지역 앵글로 라이브러리·벤치마크 광고를 주제 유사도 평가 → 카테고리 달라도 추천. google.script.run, GEMINI_API_KEY 필요, 배포 웹앱에서만, 임계 55점.
  - **UI iOS 리디자인**: 입력가이드 삭제, 카드 그림자·둥근모서리·타이포 위계 강화, 박스제목 컬러, 생성버튼 그라데이션, 폼헤더 이모지.
  - **신규 상수**: ALL_TONES_V/ALL_HOOKS_V/TONE_STYLE_V/HOOK_STYLE_V/HOOK_PATTERN_HINT/TONE_HOOK_EQUIV/AD_STYLE_POOL.
  - **검증 방식**: bash 마운트가 폴더 연결 시점 frozen → 호스트 Read + outputs 마운트로 JS 떼어 `node --check`. Edit 부분일치 truncation 주의(호스트 Read 기준 풀줄 anchor만).
  - **다음 (보류)**: 1·2 경계 정리됨(USP=고정 팩트 / 신규컨셉=발전 앵글). 컨셉 시트 저장(컨셉_뱅크)·코어 완전 hard-lock 보류.
  - **후속 수정 (같은 세션)**: ① 슬로건→이미지 연결(`copyImageWithHeadline`, 변주박스 `#img-headline` 입력칸 — LLM에서 고른 헤드라인 그대로 박은 배너) ② 길이/타겟 실반영(`lengthRule`=특정 선택 시 길이 통일·자유만 분포 / `targetRule`=특정 세대·성별 선택 시 어휘·말투 밀착 강제) ③ buildCopyPrompt dead code 제거 ④ 기능점검 리스크: 제약 과적재(지역+컨셉+무조건 → 빡빡함, 실사용 다이얼 필요)·의미매칭 배포 후 런타임 확인 필요.

- 2026-06-13: **카드뉴스 task 인사이트 누적 학습 루프 + outbox 표준 합류 (B + H 단원).** 핵심:
  - **시트 직접 Read 단일 모델** (코덱스·GitHub·Drive MD·mklink 다 폐기): 매 사이클 sync_sources로 `유튜브_인사이트` + `메타_인사이트` 시트 직접 Read → 가중치 라벨 매트릭스 적용. 정본 = `_docs/INSIGHTS_LOOP.md`. STEP 1 인사이트 시트 2개 + STEP 2 "신규 수집" 트리거(시트 + 채널 운영 시트 7일 스캔 + articles/ Glob 중복 회피 + 4 라인 WebSearch + 가중치 라벨 표) 박힘.
  - **가중치 라벨 매트릭스** (수집 단계): `yt+30%`(Top 키워드) / `yt-hook+20%`(Top 후킹 패턴) / `meta+20·30%` / `store-active+30%`(★ 시트 채널 운영 시트 7일 진행사항 메모에 박힌 매장 현재 캠페인 키워드 매칭) / `season+30%` / `freshness+10%` / `dup-100%`(articles/ 동일 토픽 즉시 제외) / 회피 키워드 표기.
  - **시트 운영 메모 7일 스캔 룰** (시트 채널 운영: 메타·당근·카카오·네이버·스레드·인스타 비고란): 매장이 현재 광고 돌리는 핫이슈를 자동 발견 → `store-active+30%` 강제 후보 추가. 빼먹으면 매장 핵심 캠페인(예: 삼성 고객감사 페스티벌) 누락 → 시트 채널 운영 시트 7일 스캔이 정답.
  - **outbox 파일명 표준** (H 단원): `<YYYY-MM-DD>_collect*.txt`(후보표) / `<NNN>_ready.txt`(작성 완료 통지) / 자동 청크 분할(3800자 + `[N/M]` 프리픽스) / 송신 후 `_state/outbox_sent/` 이동.
  - **5채널 + 영상 나레이션 표준** (`cardnews/templates/caption_template.md` §3): 첫 줄 후킹 5채널 분담(결론선언/질문던지기/이모지헤드라인/SEO/행동호출) + 영상 나레이션 채널 6 = run_pngs 시 captions.md 자동 append(별도 작성 X).
  - **신설 가이드**: `_docs/INSIGHTS_LOOP.md` / `_docs/CARDNEWS_BUILD.md`(1건 빌드 9단계) / `_docs/AUTOMATION_OVERVIEW.md`(webui·listener·outbox·run_pngs 매커니즘) / `automation/scripts/tg_send.py`.
  - **메타_인사이트 시트 셋업 대기**: 현재 `generateMetaInsightsMarkdown()` 함수가 Drive MD에 저장 중 → 시트 출력으로 함수 수정 필요(사장님 직접, Apps Script Editor). 그 전까지 메타 가중치 0건. 유튜브_인사이트 시트는 이미 동작 중.
  - **다운그레이드 없음**: 기존 성능 유지. 새 가이드는 추가만, STEP 1·2·4·8 기존 박힘은 보존.

이 파일이 업그레이드되면 변경 이력 1줄 추가. 가이드 추가·제거 시 STEP 1 리스트 동기화.
