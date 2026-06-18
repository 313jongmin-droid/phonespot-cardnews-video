# Windows 로컬 세팅 가이드

> 이 문서를 따라 하면 종민님 Windows PC 에서 `cardnews_renderer_v2.py` 가 PNG 18장을 자동으로 찍어내게 됩니다.
> 예상 소요시간: 30~45분 (다운로드 속도에 따라)

---

## 설치 필요 목록

| 항목 | 용도 | 필수 여부 |
|---|---|---|
| Python 3.11+ | 렌더러 스크립트 실행 | 필수 |
| wkhtmltopdf | HTML → PNG 변환 엔진 | 필수 |
| Pretendard 폰트 (9종) | 카드뉴스 폰트 | 필수 |

---

## 1단계: Python 설치 확인

### 이미 설치됐는지 체크

PowerShell 을 열고 (시작 메뉴에서 "PowerShell" 검색 → 실행):

```powershell
python --version
```

### 출력별 대응

- **`Python 3.11.x` 또는 그 이상** → 2단계로 건너뛰기
- **`Python 3.10.x` 이하** → 아래 설치 진행 (버전 너무 낮으면 문제 생길 수 있음)
- **`python is not recognized...`** → 아래 설치 진행

### 설치 방법

1. https://www.python.org/downloads/windows/ 접속
2. "Latest Python 3 Release" 클릭 → "Windows installer (64-bit)" 다운로드
3. 설치 실행할 때 **반드시 맨 아래 "Add python.exe to PATH" 체크** (이거 안 하면 명령어 못 찾음)
4. "Install Now" 클릭
5. 설치 후 PowerShell 새 창 열고 `python --version` 다시 확인

---

## 2단계: wkhtmltopdf 설치

카드뉴스 엔진의 핵심. HTML 파일을 PNG 로 구워주는 프로그램.

### 다운로드

1. https://wkhtmltopdf.org/downloads.html 접속
2. "Windows" 섹션에서 **"Windows 10 and up (64-bit)"** 의 `.exe` 다운로드
   - 파일명 예: `wkhtmltox-0.12.6.1-2.msvc2015-win64.exe`

### 설치

1. 다운받은 .exe 더블클릭
2. 기본값 그대로 Next, Next → Install
3. 설치 경로 확인 (기본): `C:\Program Files\wkhtmltopdf\`

### PATH 등록 (중요)

설치 마법사가 자동으로 PATH 에 넣어주지 않을 수 있습니다. 수동으로:

1. 시작 메뉴에서 **"환경 변수"** 검색 → "시스템 환경 변수 편집" 클릭
2. 하단 **"환경 변수(N)..."** 버튼
3. 상단 "사용자 변수" 또는 하단 "시스템 변수" 에서 **`Path`** 선택 → "편집"
4. "새로 만들기" → `C:\Program Files\wkhtmltopdf\bin` 추가
5. 확인 → 확인 → 확인
6. PowerShell **새 창** 열고 테스트:

```powershell
wkhtmltoimage --version
```

`wkhtmltoimage 0.12.6.1` 이런 식으로 나오면 성공.

### 실패 시

`'wkhtmltoimage'은(는) 내부 또는 외부 명령, 실행할 수 있는 프로그램...` 이 뜨면 PATH 등록 안 된 것. 위 절차 다시.

---

## 3단계: Pretendard 폰트 9종 설치

카드뉴스의 한글 폰트.

### 다운로드

1. https://github.com/orioncactus/pretendard/releases/latest 접속
2. 맨 아래 "Assets" 섹션에서 `Pretendard-1.3.9.zip` (버전 다를 수 있음) 다운로드

### 설치

1. 받은 zip 을 임의 폴더에 압축 해제
2. 풀린 폴더 안에서 `public/static/` 경로로 이동
3. 그 안의 **`.otf` 파일 9개** 전체 선택 (Pretendard-Thin.otf ~ Pretendard-Black.otf)
4. 선택된 파일들에서 **우클릭 → "모든 사용자용으로 설치(A)"** 클릭
   - 관리자 권한 요구 시 "예"

### 확인

PowerShell 에서:

```powershell
[System.Drawing.FontFamily]::Families | Where-Object { $_.Name -like "*Pretendard*" }
```

`Pretendard` 라는 항목이 뜨면 성공.

안 뜨면 자주 실패하는 원인:
- `.otf` 파일 9개 중 일부만 설치됨 → 다시 전체 선택 후 설치
- "현재 사용자용으로만 설치" 선택 → 다른 프로그램이 못 찾음. "모든 사용자용" 으로 재설치

---

## 4단계: 원본 스크립트 경로 수정

원본 `scripts/cardnews_renderer_v2.py` 는 Claude.ai 웹 환경 경로(`/mnt/user-data/outputs/...`)가 하드코딩돼 있습니다. 이걸 Windows 경로로 바꿉니다.

### 방법 A: 스크립트 직접 수정 (1회성)

`scripts/cardnews_renderer_v2.py` 를 메모장이나 VS Code 로 열고, 상단의:

```python
BASE = Path('/mnt/user-data/outputs/cardnews_tool')
OUT = Path('/mnt/user-data/outputs/iphone18_spec_downgrade_v2')
```

를 이렇게 바꿉니다:

```python
BASE = Path(r'C:\backup\phonespot_cardnews')
OUT = Path(r'C:\backup\phonespot_cardnews\output\iphone18_spec_downgrade_v2')
```

**주의**: `r'...'` 의 `r` 을 빼먹으면 `\U` 같은 데서 에러. 꼭 앞에 `r` 붙이기.

### 방법 B: 런처 스크립트 사용 (권장)

매 기사마다 경로 수정하는 건 번거로우니, 래퍼 스크립트 하나 만들어두면 편합니다. 아래 내용을 `scripts/run_windows.py` 로 저장:

```python
#!/usr/bin/env python3
"""Windows 런처 - 원본 스크립트 경로를 현재 폴더 기준으로 자동 치환"""
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent  # phonespot_cardnews/
OUT = BASE / 'output' / 'iphone18_spec_downgrade_v2'

source = (SCRIPT_DIR / 'cardnews_renderer_v2.py').read_text(encoding='utf-8')
source = source.replace(
    "Path('/mnt/user-data/outputs/cardnews_tool')",
    "Path(r'" + str(BASE) + "')"
)
source = source.replace(
    "Path('/mnt/user-data/outputs/iphone18_spec_downgrade_v2')",
    "Path(r'" + str(OUT) + "')"
)
exec(compile(source, 'cardnews_renderer_v2.py', 'exec'),
     {'__name__': '__main__', '__file__': str(SCRIPT_DIR / 'cardnews_renderer_v2.py')})
```

---

## 5단계: 실행 테스트

PowerShell 에서:

```powershell
cd C:\backup\phonespot_cardnews
python scripts\cardnews_renderer_v2.py
```

래퍼 사용 시:

```powershell
python scripts\run_windows.py
```

### 성공 시 출력

```
=== 1x1 (1080x1080) ===
  ✓ card_1.png
  ✓ card_2.png
  ...
=== 4x5 (1080x1350) ===
  ...
=== 9x16 (1080x1920) ===
  ...
완료: C:\backup\phonespot_cardnews\output\iphone18_spec_downgrade_v2
```

### 결과 확인

`output\iphone18_spec_downgrade_v2\` 폴더 안에:
- `1x1/card_1.png` ~ `card_6.png` (1080x1080)
- `4x5/card_1.png` ~ `card_6.png` (1080x1350)
- `9x16/card_1.png` ~ `card_6.png` (1080x1920)

총 18장 PNG.

---

## 6단계 (검증): 기존 샘플 PNG 와 비교

이미 `samples/sample_iphone18/` 에 Claude.ai 웹에서 생성한 참고용 PNG 가 있습니다.
방금 만든 `output/iphone18_spec_downgrade_v2/` 와 육안 비교해서:

- 폰트가 Pretendard 로 나오는지 (샘플과 자간/굵기 비슷한지)
- 색상이 오렌지 #F74B0B 인지
- 로고가 하단 중앙인지

차이가 크게 난다면 9단계 트러블슈팅.

---

## 설치 완료 후 사용 흐름

이제 Cowork 에 이렇게 요청하시면 됩니다:

```
https://www.etnews.com/20260423000169
이 기사로 카드뉴스 만들어줘
```

그러면:

1. Cowork(Claude) 가 기사 본문 읽고 분석
2. `scripts/cardnews_renderer_v2.py` 의 render_card_N 함수들을 **이번 기사에 맞게** 새로 작성해서 덮어씀
3. Cowork 가 알려주는 명령 종민님이 PowerShell 에서 실행:

```powershell
cd C:\backup\phonespot_cardnews
python scripts\cardnews_renderer_v2.py
```

4. `output/[기사명]/` 폴더에 PNG 18장 + `captions.md` 생성

### 주의

- 매 기사마다 Claude 가 스크립트를 새로 작성하는 구조. 원본을 보존하고 싶으면 `cardnews_renderer_v2_backup.py` 로 사본 먼저 만들어두기.
- 자동 실행(Cowork 가 Windows 에서 직접 python 실행) 은 현재 샌드박스가 리눅스라 불가. 종민님이 PowerShell 명령 한 줄 실행하는 절차 필요.

---

## 트러블슈팅

### `OSError: No wkhtmltopdf executable found`

→ 2단계 PATH 등록 다시 확인. PowerShell 새 창에서 `wkhtmltoimage --version` 성공해야 함.

### PNG 가 생성되는데 한글이 네모(豆腐) 로 나옴

→ Pretendard 설치 안 됨. 3단계 다시.

### PNG 가 생성되는데 Pretendard 가 아닌 다른 폰트로 나옴

→ 3단계에서 "현재 사용자용" 으로만 설치된 것. "모든 사용자용" 으로 재설치.

### 한글이 나오긴 하는데 잘림/깨짐

→ wkhtmltopdf 0.12.6 이 아닌 옛날 버전일 수 있음. 0.12.6.1 이상 설치 권장.

### `UnicodeDecodeError` 또는 `cp949` 에러

→ Python 으로 실행할 때 인코딩 문제. PowerShell 에서:
```powershell
$env:PYTHONIOENCODING = "utf-8"
python scripts\cardnews_renderer_v2.py
```

---

## 체크리스트

설치 완료 기준:

- [ ] `python --version` → 3.11+ 출력
- [ ] `wkhtmltoimage --version` → 0.12.6.1+ 출력
- [ ] Pretendard 폰트 9종 설치 확인
- [ ] `python scripts\cardnews_renderer_v2.py` 실행 시 에러 없음
- [ ] `output/` 폴더에 PNG 18장 생성됨
- [ ] 생성된 PNG 의 한글이 Pretendard 로 표시됨

전부 체크되면 Windows 세팅 완료. 이후 Cowork 에 URL 만 던지면 됩니다.
