# 폰스팟 카드뉴스·영상 프로젝트 — 클로드 부트스트랩

> **새 클로드 세션이 이 폴더를 열면 가장 먼저 이 파일을 읽음.**
> 모든 가이드·매뉴얼·매커니즘 진입점은 여기. 다른 세션과 같은 공식으로 작업하려면 **아래 STEP 1을 반드시 먼저 실행**.

---

## STEP 1 — 작업 시작 전 가이드 일괄 Read (필수)

다음 6개 파일을 **순서대로 Read**. 어떤 작업이든 이 6개 다 읽기 전 코드·JSON·이미지 생성 금지.

1. `_docs/INSTRUCTIONS_CARDNEWS.md` — 시스템·자동화·후보 수집·발행 룰 마스터
2. `cardnews/templates/caption_template.md` — 5채널 + 나레이션 카피·캡션·후킹 룰
3. `_docs/CARDNEWS_BUILD.md` — 카드뉴스 1건 빌드 전체 워크플로 (수집→발행)
4. `_docs/AUTOMATION_OVERVIEW.md` — webui·telegram listener·outbox·run_pngs 매커니즘
5. `_docs/INSTRUCTIONS_SHORTS.md` — 영상(shorts) 빌드 매뉴얼
6. `cardnews/_state/content_guide.md` — 매 사이클 학습되는 시즌·트렌드 메모 (존재 시)

각 Read 결과는 다음 작업의 컨텍스트로 직접 활용. 사장님이 "수집해줘" / "발행해줘" / "매커니즘 알려줘" 같은 짧은 명령만 줘도 위 6개 가이드로 모든 형식·룰을 자동 적용해야 함.

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
| "매커니즘 알려줘" / "이게 어떻게 돌아가" | `AUTOMATION_OVERVIEW.md` 직참조 |

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
| 영상 빌드 | `shorts/` 디렉터리 + Remotion | 60초 영상 |
| 코덱스 영상 데스크 | `CODEX_VIDEO_DESK/` | 별도 task |

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
├── shorts/                       영상 (Remotion)
├── automation/                   listener·자동화 스크립트
├── CODEX_VIDEO_DESK/             코덱스 영상 task (별도)
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

이 파일이 업그레이드되면 변경 이력 1줄 추가. 가이드 추가·제거 시 STEP 1 리스트 동기화.
