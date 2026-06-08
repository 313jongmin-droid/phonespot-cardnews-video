# 노트북 개발 / 사무실 PC 실행 / GitHub 연동 워크플로

> 목적: **노트북 = 개발(Claude Code 편집)**, **사무실 PC = 실행(패널·스케줄러·렌더·카드수집)**,
> **GitHub = 코드 중간 허브**. 노트북에서 고쳐 push → 사무실에서 pull → 적용 → 실행.

репо: `https://github.com/313jongmin-droid/phonespot-cardnews-video.git` (브랜치 `main`)

---

## 0. 역할 (한 줄 요약)

| | 노트북 | 사무실 PC |
|---|---|---|
| 용도 | 개발(Claude Code로 코드/가이드/주제 편집) | 실행(패널·렌더·카드수집·ads·스케줄러) |
| git | **push**(올림) | **pull**(받음) |
| 런타임 | 불필요(편집만) | 필요(이미 셋업됨: venv·node_modules·playwright·키·Drive허브) |

GitHub로 가는 것 = **모든 소스/문서**(shorts·cardnews·ads·ads_kt·automation·CODEX_VIDEO_DESK·_docs·articles).
**안 가는 것**(= 사무실 PC 로컬 유지) = `_secrets/`(키), `node_modules/`, `.phonespot_runtime/`, 런타임 산출물,
일러스트(Drive 허브), `shorts/config/library_share_path.txt`·`concept_name_cache.json`(PC별).

---

## 1. 선행(1회): 사무실 PC → GitHub 최신화

노트북이 "전부" 받으려면 **사무실 PC가 먼저 최신 코드를 push** 해야 한다(안 그러면 노트북은 옛 코드를 받음).

사무실 PC에서:
1. (권장) `CODEX_VIDEO_DESK\런타임파일_git정리_1회.bat` — 런타임 파일 git 추적 해제(코드만 깔끔히).
2. 패널 "시스템 업로드"(= git add -A + commit + push) 또는 직접 `git push`.

---

## 2. 노트북에서 이어받기 (Claude Code)

### 처음 1회 — 저장소 가져오기
터미널(또는 Claude Code 안의 셸)에서:
```
git clone https://github.com/313jongmin-droid/phonespot-cardnews-video.git C:\dev\phonespot_cardnews
```
그다음 **Claude Code를 `C:\dev\phonespot_cardnews` 폴더에서 열기**.

Claude Code 첫 메시지(붙여넣기):
```
이 폴더(C:\dev\phonespot_cardnews)는 폰스팟 프로젝트 개발용 노트북 클론이야.
CLAUDE.md 와 _docs 가이드들을 먼저 읽고 구조를 파악해줘.
나는 여기서 코드·가이드·주제만 편집하고 push 하면, 사무실 PC가 pull 해서 실행해.
무거운 렌더/패널 실행은 사무실 PC에서만 해.
```
(Claude Code는 cwd의 `CLAUDE.md`를 자동으로 읽어 모든 룰·진입점을 파악함.)

### 이후 매번 — 최신 받기
작업 시작 전 항상:
```
git pull
```
(또는 Claude Code에 "git pull 해줘"라고).

### 편집 후 — 올리기
```
git add -A
git commit -m "변경 내용 요약"
git push
```
(또는 Claude Code에 "변경분 커밋하고 push 해줘".)

> 노트북 1회 준비: `git config --global user.name "..."`, `git config --global user.email "..."`,
> 그리고 GitHub 로그인(자격증명). private repo면 접근 권한 확인.

---

## 2-1. "상시 동기화"처럼 쓰기 (중요 — git은 실시간 동기화가 아님)

git 은 Drive 처럼 자동이 아니라 **push(올림) / pull(받음)** 스냅샷 방식이다. 두 대(노트북·사무실)를
거의 자동처럼 쓰려면:

- **사무실 = 자동 pull**: `CODEX_VIDEO_DESK\수신PC_자동업데이트_켜기.bat` 1회 → 패널 켤 때마다 자동
  `git pull`. (← 예전의 "안 해도 업데이트 되던" 그 느낌. 사무실은 손 안 댐.)
- **노트북 = 1클릭 push**: 편집 끝나면 저장소 루트의 **`노트북_올리기.bat`** 더블클릭
  (= git add -A + commit + push). 또는 Claude Code 에 "변경분 커밋하고 push 해줘" 한마디.

즉 루프 = **노트북 편집 → `노트북_올리기.bat` → 사무실 패널 켜면 자동 반영.** push 만큼은 git 특성상
생략 불가(코드 버전관리·충돌 방지를 위해 오히려 이게 안전).

## 3. 사무실 PC에서 적용 + 실행

1. **받기**: 패널 "시스템 업데이트"(git pull) — 또는 `수신PC_자동업데이트_켜기.bat` 켜두면
   `00_PHONE_SPOT_PANEL.bat` 시작 시 자동 pull(런타임 충돌은 자동 stash로 회피).
2. **적용**: server.py 버전(PANEL_VERSION)이 바뀌었으면 패널 자동 재시작. 스크립트/배치는 다음 실행부터.
   - 의존성(새 pip/npm)이 바뀐 경우만 `SETUP_FULL_PRODUCER.bat` 재실행.
3. **실행**: 패널에서 카드뉴스/영상 작업, 스케줄러(백업 등), ads 운영.

---

## 4. 정직한 경계 — git-pull 로 "자동 적용 안 되는" 것

- **ads의 Apps Script**: `ads/code/apps_script/*.gs` **소스는** GitHub로 가지만, 실제로 도는 곳은
  **Google 시트의 Apps Script(구글 클라우드)**. 노트북에서 .gs 고쳐 push·pull 해도 시트엔 자동 반영 X →
  Apps Script 편집기에 **붙여넣기(또는 clasp push)로 배포**해야 적용. (시트 데이터·GA4/메타 연동도 구글 쪽.)
- **API 키/토큰**(`_secrets/`): GitHub 안 감. 사무실 PC에만 둠. 노트북은 편집만이면 불필요.
- **일러스트 라이브러리**: Drive 허브로 공유(§ MULTI_PC 가이드). git 아님.

---

## 5. 자주 헷갈리는 점

- 노트북은 **렌더/패널을 돌릴 필요 없음**(느려도 됨) — 편집만. 무거운 셋업 불필요.
- 사무실 PC는 **개발하지 않음**(편집은 노트북). 충돌 방지: 사무실에서 코드 직접 수정하지 말 것
  (수정하면 다음 pull과 충돌). 급할 때만 예외.
- 주제(기사) 작성도 노트북 Claude Code에서 가능(`cardnews/templates/article_authoring_spec.md` 기준) →
  push → 사무실 pull. 또는 사무실 Cowork에서.

---

## 6. .env / 경로 (참고)

현재 경로는 코드가 `Path(__file__)` 기준 상대로 도출 → **어느 폴더로 clone해도 동작**(추가 설정 불필요).
환경변수 노브(선택): `PHONESPOT_LIBRARY_SHARE`, `PHONESPOT_RENDER_CONCURRENCY`, `PHONESPOT_GEMINI_TEXT_MODEL` 등
(상세: `CODEX_VIDEO_DESK/MAINTENANCE/PHONESPOT_UPDATES_2026-06_GUIDE.md`). 데이터/출력을 D:로 물리 분리하는
구조는 현재 미적용(필요 시 별도 작업).
