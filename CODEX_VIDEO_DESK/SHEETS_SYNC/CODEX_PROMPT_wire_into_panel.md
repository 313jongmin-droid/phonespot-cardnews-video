# 코덱스에게 줄 프롬프트 (선택: 패널에 시트 동기화 버튼 연결)

아래 내용을 그대로 코덱스에게 붙여넣으세요.
이 변경은 `dashboard/server.py` 를 수정하므로, **코덱스의 다른 작업이 끝난 뒤** 적용하는 것을 권장합니다.
새 파일 쪽(SHEETS_SYNC/*)은 이미 만들어져 있으니 server.py 연결만 하면 됩니다.

---

## 프롬프트 (복사해서 사용)

> `dashboard/server.py` 에 작업 큐 ↔ Google Sheets 동기화 기능을 **추가만** 해줘. 기존 동작은 절대 바꾸지 말 것.
>
> 배경: 이미 `CODEX_VIDEO_DESK/SHEETS_SYNC/sheets_sync.py` 라는 독립 스크립트가 있다.
> 이 스크립트는 인자로 `sync` / `push` / `pull` / `migrate` 를 받고, `SHEETS_SYNC/sheets_endpoint.txt`
> 가 없으면 아무것도 하지 않고 0으로 종료한다(무해).
>
> 요구사항:
> 1. POST 액션 핸들러에 `work_queue_sheets_sync` 액션을 새로 추가한다.
>    - 동작: `run_job("작업대장 시트 동기화", [[sys.executable, str(DESK / "SHEETS_SYNC" / "sheets_sync.py"), "sync"]], DESK)` 호출.
>    - 다른 액션들과 동일한 busy 처리/JSON 응답 패턴을 따른다.
> 2. 기존 `work_queue_refresh` 액션은 그대로 두되, 로컬 새로고침이 성공한 "뒤에"
>    위 시트 동기화를 이어서 호출한다. 단, `sheets_endpoint.txt` 가 없으면 시트 동기화는
>    스크립트가 알아서 no-op 하므로 추가 분기 없이 그냥 호출해도 안전하다.
>    (동기화 호출은 try/except 로 감싸 실패해도 새로고침 응답에는 영향 없게 한다.)
> 3. 작업 큐 영역 패널 HTML 에 버튼 하나를 추가한다:
>    - 라벨: "구글 시트 동기화"
>    - onclick: POST `/` 로 `{action:"work_queue_sheets_sync"}` 전송 후 결과 토스트/알림 표시.
>    - 기존 버튼들과 같은 스타일/헬퍼(api 함수)를 재사용한다.
> 4. import 추가가 필요하면 최소한으로. `sys`, `subprocess`, `DESK`, `run_job` 는 이미 있으니 재사용.
> 5. 변경 전 server.py 를 타임스탬프 백업(.bak_sheets_sync_YYYYMMDD_HHMMSS)으로 남긴다.
>
> 제약: 새 외부 패키지 설치 금지(stdlib 만). 포트/실행 방식/기존 액션 이름은 바꾸지 말 것.

---

## 적용 후 확인

1. 패널을 재시작(`00_PHONE_SPOT_PANEL.bat`)한다.
2. 작업 큐 영역의 "구글 시트 동기화" 버튼을 누른다.
3. `sheets_endpoint.txt` 미설정이면 조용히 통과(에러 없음), 설정돼 있으면 시트에 반영된다.
4. 다른 PC 에서 같은 버튼을 눌러 담당자/검수 값이 서로 보이는지 확인한다.
