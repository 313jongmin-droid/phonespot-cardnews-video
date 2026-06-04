# Codex Token Diet

PhoneSpot Shorts 작업을 다시 열 때 아래 순서만 읽습니다.

1. `CODEX_CURRENT_BASELINE_GUIDE.md`
2. `C:\Users\di898\Documents\phonespot_cardnews\shorts\harness\ACTIVE_TASK.md`
3. 필요한 경우에만 공용 규칙 파일 1개
   - 자막: `shorts\harness\CAPTION_RULES.md`
   - 비주얼: `shorts\harness\VISUAL_RULES.md`
   - 출력 품질: `shorts\harness\QUALITY_RULES.md`
4. 회귀나 과거 결정 확인이 필요할 때만:
   - `shorts\codex\CODEX_MEMORY.md`
   - `shorts\codex\codex_patch_log.md`

재귀 탐색하지 않는 폴더:

- `node_modules\`
- `CODEX_VIDEO_DESK\RESULTS\`, `CODEX_VIDEO_DESK\TEMP\`, `CODEX_VIDEO_DESK\ILLUSTRATION_DROP\`
- `out\`, legacy `out_codex\`, legacy `upload_codex\`
- `public\audio\`
- `public\assets\`
- `hyperframes_codex\`
- 백업 파일과 바이너리 파일 (`*.bak*`, `*.mp4`, `*.mp3`, `*.png`, `*.zip`)

현재 Codex 기준선 적용:

`RUN_APPLY_CODEX_CURRENT_BASELINE.bat`

실험 중인 TTS 발음사전 + 타이밍 레이어:

`RUN_APPLY_CODEX_TTS_PRONUNCIATION_TIMING.bat`

실험 중인 일러스트 태그 DB + 최근 사용 이력:

`RUN_APPLY_CODEX_ILLUSTRATION_TAG_DB.bat`

실험 중인 3채널 발행 패키지 V1:

`RUN_APPLY_CODEX_PUBLISH_PACKAGE_V1.bat`

실험 중인 목록형 자막 줄바꿈 보정:

`RUN_APPLY_CODEX_LIST_CAPTION_LAYOUT.bat`

샘플 확인 전에는 현재 기준선 설치 BAT에 합치지 않습니다.

일상 영상 작업:

`C:\Users\di898\Documents\phonespot_cardnews\CODEX_VIDEO_DESK`
