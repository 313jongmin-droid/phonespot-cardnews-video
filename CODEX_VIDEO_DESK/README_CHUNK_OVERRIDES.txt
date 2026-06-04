# 청크 오버라이드 방식

청크 편집은 이제 원본 `cardnews/output/<slug>/shorts_script.json`을 직접 수정하지 않습니다.

저장 위치:
`CODEX_VIDEO_DESK/CHUNK_OVERRIDES/<slug>.json`

동작:
1. 패널 7번 청크 경계 편집에서 줄바꿈/합치기/나누기를 누릅니다.
2. 시스템은 TTS 원문과 청크 합계가 맞는지 검사합니다.
3. 통과하면 오버라이드 파일만 저장합니다.
4. 렌더 때 `copy_assets.py`가 원본 스크립트 + 오버라이드를 합쳐 `shorts/public/shorts_script.json`으로 넘깁니다.

원복:
`CODEX_VIDEO_DESK/CHUNK_OVERRIDES/<slug>.json` 파일을 삭제하면 원본 청크로 돌아갑니다.

주의:
일러스트/이미지 매핑 수정은 아직 원본 스크립트에 저장됩니다. 청크 경계만 오버라이드 방식입니다.
