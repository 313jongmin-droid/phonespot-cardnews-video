# GitHub + 로컬 렌더 운영 가이드

목표:

- GitHub는 코드 업데이트 저장소로만 사용합니다.
- 영상 렌더는 각 PC의 로컬 폴더에서 실행합니다.
- 카드뉴스/영상 결과물, GPT 이미지, 오디오, node_modules는 GitHub에 올리지 않습니다.

권장 구조:

```text
내 PC
C:\Users\di898\Documents\phonespot_cardnews
  - 개발
  - 카드뉴스 생성
  - 필요 시 GitHub push

부사수 PC
C:\PhoneSpot\phonespot_cardnews
  - GitHub에서 코드 clone
  - 로컬 패널 실행
  - 로컬 Remotion 렌더
  - 로컬 RESULTS 저장
```

초기 세팅:

1. GitHub에 코드 저장소를 만듭니다.
2. 무거운 결과물과 비밀키는 `.gitignore`로 제외합니다.
3. 부사수 PC에서 `SETUP_RENDER_PC_FROM_GITHUB.bat`를 실행합니다.
4. GitHub 저장소 URL과 설치 폴더를 입력합니다.

업데이트:

- 패널의 `시스템 업데이트` 버튼을 누르거나
- `CODEX_VIDEO_DESK\MAINTENANCE\codex_github_update.py`를 실행합니다.

주의:

- GitHub에는 코드만 올립니다.
- `CODEX_VIDEO_DESK\RESULTS`, `ILLUSTRATION_DROP`, `TEMP`, `shorts\public\audio`, `cardnews\output`은 PC별 로컬 데이터입니다.
- 로컬 변경이 남아 있으면 업데이트가 중단됩니다. 이건 작업물 덮어쓰기를 막기 위한 안전장치입니다.
