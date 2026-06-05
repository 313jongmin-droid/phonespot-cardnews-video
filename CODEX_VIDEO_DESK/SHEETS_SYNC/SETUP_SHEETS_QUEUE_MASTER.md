# 작업 큐 → Google Sheets "마스터" 만들기 (설정 가이드)

목표: 원격에 있는 여러 PC 가 **같은 작업 큐**를 공유한다.
방법: 협업 필드(담당자·검수·발행·메모)는 **시트가 마스터**, 파생 상태는 각 PC 가 계산해 시트로 올린다.

이 작업은 **기존 파일(server.py, codex_work_queue.py, Code.gs)을 전혀 수정하지 않습니다.**
전부 새 파일로만 동작하며, `sheets_endpoint.txt` 를 만들기 전에는 동기화가 꺼져 있어 기존 패널에 영향이 없습니다.

---

## 0. 필드 소유권 (왜 충돌이 없는가)

| 필드 | 누가 쓰는가 | 마스터 |
|---|---|---|
| 담당자, 검수, 유튜브/인스타/틱톡, 메모 | 사람이 시트에서 편집 | **시트** |
| 날짜, 제목, 카드뉴스/영상 상태, 필요 일러스트, 결과 | 각 PC 가 로컬 파일 스캔으로 계산 | **로컬(→시트로 표시용 PUSH)** |

필드마다 쓰는 주체가 하나뿐이라 두 사람이 동시에 작업해도 같은 칸이 겹치지 않습니다.
(같은 칸을 동시에 고치는 경우만 "나중 저장 우선"이며, 그 결과는 시트에 그대로 보입니다.)

---

## 1. Apps Script 에 웹앱 API 추가

1. 공유할 Google Sheets 파일을 연다 (기존 `PhoneSpot 작업대장` 시트가 있는 파일).
2. `확장 프로그램` > `Apps Script`.
3. 왼쪽 `+` > `스크립트`로 **새 파일** 을 만들고 이름을 `Api` 로 한다.
   - `GOOGLE_SHEETS_PANEL/Api.gs` 내용을 그대로 붙여넣는다.
   - ⚠️ 기존 `Code.gs` 는 건드리지 않는다. (Api.gs 는 추가 파일)
4. (보안) 왼쪽 톱니 `프로젝트 설정` > `스크립트 속성` > 속성 추가
   - 이름: `PHONESPOT_TOKEN`
   - 값: 임의의 긴 무작위 문자열 (예: 32자 이상). 이 값을 메모해 둔다.
5. `배포` > `새 배포` > 유형 `웹 앱`
   - 설명: 아무거나
   - 실행: **나**
   - 액세스 권한: **링크가 있는 모든 사용자**
   - `배포` 클릭 → 권한 승인.
6. 나오는 **웹 앱 URL** (`https://script.google.com/macros/s/.../exec`) 을 복사.

> 코드를 고쳐 재배포할 때는 `배포 관리` > 기존 배포 `편집`(연필) > 버전 `새 버전` 으로 올려야
> 같은 URL 이 유지됩니다. "새 배포"를 또 만들면 URL 이 바뀝니다.

---

## 2. 각 PC 에 엔드포인트 등록

`CODEX_VIDEO_DESK\SHEETS_SYNC\` 에서:

1. `sheets_endpoint.example.txt` 를 복사해 같은 폴더에 `sheets_endpoint.txt` 로 저장.
2. 내용을 채운다:
   - 1번째 줄: 1단계에서 복사한 `.../exec` URL
   - 2번째 줄: `PHONESPOT_TOKEN` 과 똑같은 토큰
3. 함께 작업하는 모든 PC 에서 같은 URL/토큰으로 이 파일을 만든다.

> `sheets_endpoint.txt` 는 토큰이 들어가므로 GitHub 에 올리지 마세요.
> (`.gitignore` 에 `CODEX_VIDEO_DESK/SHEETS_SYNC/sheets_endpoint.txt` 추가 권장)

---

## 3. 최초 1회 씨딩 (대표 PC 에서만)

대표 PC 에서 한 번만:

```
12_MIGRATE_WORK_QUEUE_TO_SHEETS.bat
```

현재 로컬 작업 큐의 모든 필드(담당자·메모 포함)를 시트에 채웁니다.
이미 시트에 손으로 입력한 값이 있으면 같은 슬러그의 해당 칸은 덮어쓰니 주의.

---

## 4. 평소 사용

각 PC 에서:

```
11_SYNC_WORK_QUEUE_WITH_SHEETS.bat
```

- 먼저 로컬 파생 상태를 시트로 올리고(PUSH),
- 시트의 협업 필드를 로컬 큐로 내려받습니다(PULL).

순서 추천: 카드뉴스/렌더 작업 → `08_REFRESH_WORK_QUEUE.bat`(로컬 상태 재계산) → `11_..._SHEETS.bat`(동기화).

명령을 직접 쓰고 싶으면:

```
python SHEETS_SYNC\sheets_sync.py status   # 연결만 확인(쓰기 없음)
python SHEETS_SYNC\sheets_sync.py push
python SHEETS_SYNC\sheets_sync.py pull
python SHEETS_SYNC\sheets_sync.py sync
```

---

## 5. (선택) 패널 버튼/자동화로 연결

지금은 별도 `.bat` 실행 방식이라 `server.py` 를 안 건드립니다.
패널 새로고침 버튼에 자동으로 물리고 싶으면, 코덱스에게
`SHEETS_SYNC/CODEX_PROMPT_wire_into_panel.md` 의 프롬프트를 주면 됩니다.
(그 변경은 server.py 를 수정하므로 코덱스 작업과 겹치지 않게 따로 적용)

또는 Windows 작업 스케줄러로 `11_SYNC_WORK_QUEUE_WITH_SHEETS.bat` 를
N분마다 실행하면 사실상 자동 동기화가 됩니다.

---

## 6. 문제 해결

- **JSON 이 아닌 응답**: 웹앱 액세스 권한이 "링크가 있는 모든 사용자"인지, URL 이 `/exec` 인지 확인.
- **invalid token**: `sheets_endpoint.txt` 2번째 줄 토큰과 스크립트 속성 `PHONESPOT_TOKEN` 이 같은지 확인.
- **행이 안 올라감**: 대상 슬러그가 로컬 큐(`WORK_QUEUE/phonespot_work_queue.json`)에 있는지,
  `08_REFRESH_WORK_QUEUE.bat` 를 먼저 돌렸는지 확인.
- **권한 재요청 루프**: Apps Script 에서 재배포 시 새 버전으로 올렸는지 확인.
