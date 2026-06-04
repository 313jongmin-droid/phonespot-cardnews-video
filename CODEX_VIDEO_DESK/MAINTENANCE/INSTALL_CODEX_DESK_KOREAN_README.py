# -*- coding: utf-8 -*-
"""Write a Korean operational README for the PhoneSpot Codex video desk."""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_ROOT = Path(r"C:\Users\di898\Documents\phonespot_cardnews")
ROOT = Path(os.environ.get("PHONESPOT_ROOT", str(DEFAULT_ROOT)))
DESK = ROOT / "CODEX_VIDEO_DESK"
README = DESK / "README.txt"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


README_TEXT = r'''폰스팟 코덱스 영상 데스크 사용 안내

이 폴더만 열어두면 영상 준비, 일러스트 추가, 렌더링, 결과 확인까지 진행할 수 있습니다.

■ 가장 자주 쓰는 작업 흐름

[새 카드뉴스를 처음 영상으로 만들 때]
1. 01_PREPARE_GPT_PROMPTS.bat 실행
2. 목록에서 영상으로 만들 뉴스 번호 선택
3. LATEST_PROMPT.md가 열리면 필요한 일러스트를 GPT Plus에서 생성
4. 생성 이미지를 평소처럼 다운로드
5. 02_IMPORT_DOWNLOADS_AND_RENDER.bat 실행
6. 다운로드 이미지가 자동으로 정리되고 Remotion 영상이 생성됨

[새 일러스트 없이 마지막 선택 영상을 다시 만들 때]
- 03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat 실행

[과거 영상이나 원하는 영상을 직접 골라 다시 만들 때]
- 15_SELECT_AND_RENDER_EXISTING.bat 실행

■ 버튼별 설명

01_PREPARE_GPT_PROMPTS.bat
- 만들 뉴스를 번호로 선택합니다.
- 영상 청크와 비주얼을 준비하고, 새 GPT 일러스트가 필요하면 요청 문서를 엽니다.
- 아직 TTS 생성이나 영상 렌더링은 하지 않습니다.

02_IMPORT_DOWNLOADS_AND_RENDER.bat
- GPT Plus에서 새 일러스트를 내려받은 뒤 실행합니다.
- 다운로드한 이미지를 알맞은 파일명으로 가져오고, 마지막으로 선택한 영상을 렌더링합니다.

03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat
- 새 일러스트를 추가하지 않고 마지막으로 선택한 영상을 다시 렌더링합니다.
- 문구나 공통 로직을 수정한 뒤 재확인할 때 사용합니다.

04_OPEN_LATEST_PROMPT.bat
- 가장 최근 GPT 일러스트 생성 요청 문서 LATEST_PROMPT.md를 다시 엽니다.

05_OPEN_RESULTS.bat
- 업로드용 결과 폴더 RESULTS를 엽니다.
- 완성 MP4와 캡션 파일을 확인할 때 사용합니다.

06_OPEN_ILLUSTRATION_LIBRARY.bat
- 재사용 일러스트 라이브러리 폴더를 엽니다.
- 새 PNG를 직접 확인하거나 교체할 때 사용합니다.

07_OPEN_RESULTS_HISTORY.bat
- RESULTS 폴더를 엽니다.
- 재렌더 이력도 RESULTS 하위 폴더에 함께 쌓입니다.

08_APPLY_TTS_PRONUNCIATION_TIMING.bat
- TTS 발음사전과 단어 경계 기반 타이밍 보정 기능을 설치합니다.
- 한 번만 적용하면 이후 일반 렌더에도 자동으로 반영됩니다.

09_EDIT_TTS_PRONUNCIATION_DICTIONARY.bat
- WWDC, iOS, NFC 같은 용어가 어색하게 읽힐 때 발음사전을 편집합니다.
- 화면 자막은 바꾸지 않고 음성 발음만 조정합니다.

10_ROLLBACK_TTS_PRONUNCIATION_TIMING.bat
- TTS 실험 결과가 더 나쁠 때 발음사전과 타이밍 보정 기능을 원복합니다.

11_OPEN_ILLUSTRATION_TAG_DB.bat
- 일러스트별 태그와 최근 사용 기록을 확인합니다.
- 같은 그림이 반복되는지 점검할 때 사용합니다.

12_REFRESH_ILLUSTRATION_TAG_DB.bat
- 일러스트 PNG를 추가하거나 이름을 변경한 뒤 태그 DB를 다시 읽습니다.

13_REFRESH_LATEST_PUBLISH_PACKAGE.bat
- 가장 최근 결과 폴더를 기준으로 유튜브 쇼츠, 인스타그램 릴스, 틱톡 발행 문구를 다시 만듭니다.
- 영상을 다시 렌더링하지 않고 업로드 문구 묶음만 갱신합니다.

14_OPEN_PUBLISH_PACKAGES.bat
- RESULTS 폴더를 엽니다.
- V2에서는 통합 문서 UPLOAD_COPY.txt와 최종 MP4가 같은 하위 폴더에 있습니다.

15_SELECT_AND_RENDER_EXISTING.bat
- 원하는 뉴스를 번호로 골라 바로 렌더링합니다.
- 01번에서 프롬프트를 준비하지 않고도 기존 영상이나 과거 영상을 다시 만들 수 있습니다.

■ 결과 폴더

- RESULTS/<렌더 이름>/: 최종 MP4, 캡션, 통합 업로드 문서 UPLOAD_COPY.txt
- ILLUSTRATION_DROP/: 재사용 GPT Plus 일러스트
'''


def main() -> int:
    print("============================================================")
    print(" PhoneSpot Codex - Korean Desk README")
    print("============================================================")
    DESK.mkdir(parents=True, exist_ok=True)
    if README.exists():
        backup = README.with_name(f"README.txt.bak_korean_guide_{STAMP}")
        shutil.copy2(README, backup)
        print(f"[backup] {backup}")
    README.write_text(README_TEXT.rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"[write] {README}")
    print("[OK] Korean guide installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
