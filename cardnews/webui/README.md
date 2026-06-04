# Phonespot 카드뉴스 webui (Phase 2)

브라우저 기반 운영 패널. 직원이 CLI 모르고도 사용 가능. LAN 공유로 다른 PC·모바일 접근.

## 실행

```cmd
cd C:\Users\di898\Documents\phonespot_cardnews\cardnews
webui\start.bat
```

→ Flask 자동 설치 + `http://localhost:8080` 열림.

## 직원·다른 PC 접근 (LAN)

1. 사무실 PC IP 확인:
   ```cmd
   ipconfig
   ```
   → 무선/이더넷 IPv4 주소 (예: `192.168.0.10`)

2. 윈도우 방화벽 8080 inbound 허용 (1회):
   - 제어판 → Windows Defender 방화벽 → 고급 설정 → 인바운드 규칙 → 새 규칙 → 포트 → TCP 8080 → 허용

3. 직원 PC·모바일 브라우저:
   - `http://192.168.0.10:8080`

## Basic Auth (선택 — 켜는 법)

`_secrets/webui_auth.txt` 파일 1줄 작성:
```
admin:strong_password_here
```

→ 다음 실행부터 모든 페이지에 브라우저 로그인 창. 파일 없으면 인증 비활성화 (LAN 안에서만 사용 권장).

## 기능 (Phase 2)

| 페이지 | 기능 |
|---|---|
| `/` 슬러그 목록 | 전체 슬러그 + 상태 마커 + 검색/필터 + 카운트 요약 |
| `/slug/<id>` 상세 | 카드 6장 미리보기 / prompt.md 복사 / 이미지 5장 드래그&드롭 업로드 / 렌더 트리거 / **실시간 SSE 로그** |
| `/result/<id>` 결과 | 사이즈별 (1x1/4x5/9x16) 탭 + 18 JPG 그리드 미리보기 / captions.md 보기·복사 / **ZIP 다운로드** |
| `/output/<id>/<f>` | 결과 JPG·captions.md 단일 다운로드 |

## 사장님·직원 워크플로

1. 사장님: AI가 작성한 슬러그 폴더에 prompt.md 보관됨 (자동)
2. 직원: 브라우저로 `/` 진입 → "렌더 준비" 또는 "이미지 대기" 슬러그 선택
3. 직원: 상세 페이지에서 prompt.md 복사 → GPT/Gemini 이미지 받기 → 페이지에 드래그&드롭
4. 직원: [렌더링 시작] → 실시간 로그 확인 (30~60초)
5. 완료 시 [결과 페이지] 버튼 → 18 JPG 그리드 + ZIP 다운로드

## Phase 3 예정

- 신규 슬러그 작성 폼 (AI 호출 없이 수동 입력 모드)
- 발행 일정 캘린더
- 시트 sync 자동 read (관리대장 성과 데이터)
- 모바일 PWA (홈 화면 추가)

## 보안

- Basic Auth 안 켜면 LAN 내 누구나 접속 가능 → **외부 인터넷 노출 금지**
- 방화벽 8080 inbound 허용 후 직원 PC 접속
- `_secrets/webui_auth.txt` 는 git ignore (이미 `_secrets/`는 ignore 설정)

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| `flask not found` | pip 설치 실패 | `py -3 -m pip install flask` 수동 |
| 직원 PC 접속 X | 방화벽 차단 | 8080 TCP inbound 허용 |
| 렌더 SSE 끊김 | 600초 timeout | 다시 시작 또는 CLI로 디버그 |
| 모바일 업로드 X | iOS 사파리 캐시 | 페이지 새로고침 |
