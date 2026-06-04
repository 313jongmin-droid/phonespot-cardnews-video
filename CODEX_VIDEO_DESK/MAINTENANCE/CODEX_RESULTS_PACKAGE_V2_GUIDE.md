# Codex 단일 결과 폴더 V2

## 목적

완성 MP4, 캡션, 채널별 업로드 문구를 한 폴더에서 확인합니다.

## 적용

아래 파일을 한 번 실행합니다.

`RUN_APPLY_CODEX_RESULTS_PACKAGE_V2.bat`

## 적용 후 구조

```text
CODEX_VIDEO_DESK/
├─ TEMP/
│  └─ _raw/                         렌더 중간 파일
├─ ILLUSTRATION_DROP/                재사용 일러스트 실제 저장소
└─ RESULTS/
   └─ 20260601_<slug>_codex_remotion_<재렌더 시각>/
      ├─ 20260601_<slug>_codex_remotion_<재렌더 시각>.mp4
      ├─ captions.md
      ├─ shorts_script.json
      ├─ UPLOAD_COPY.txt
      ├─ publish.json
      └─ source_manifest.txt
```

## 정리되는 항목

- 데스크의 `OUT_CODEX` 바로가기를 제거합니다.
- 별도 `PUBLISH_PACKAGES` 폴더를 제거합니다.
- 기존 V1 패키지는 `RESULTS` 아래로 이동합니다.
- 과거 `upload_codex`와 `shorts/out_codex` 내용은 삭제하지 않고 `backups/CODEX_DESK_ONLY_STORAGE_MIGRATION_<시각>/`으로 이동합니다.
- 기존 결과 폴더에 채널별 텍스트 파일이 흩어져 있으면 `UPLOAD_COPY.txt` 하나로 다시 묶고 과거 분리 파일을 제거합니다.

## 보존

- Remotion 영상 인코딩 품질은 바꾸지 않습니다.
- TTS, 청크, 한국어 줄바꿈, CTA, 일러스트 로직은 바꾸지 않습니다.
- 렌더 중간 파일은 `CODEX_VIDEO_DESK/TEMP/_raw/`에만 저장됩니다.
- `shorts/public/assets/illustrations/`는 렌더 직전에 자동 갱신되는 Remotion 내부 캐시입니다. 실제 일러스트는 `CODEX_VIDEO_DESK/ILLUSTRATION_DROP/`에 있습니다.
- `UPLOAD_COPY.txt` 한 파일 안에서 유튜브 쇼츠, 인스타그램 릴스, 틱톡 구역을 나누어 필요한 부분만 복사합니다.
- 결과 MP4의 파일명은 상위 결과 폴더명과 동일합니다.
- 핵심 렌더 파일 `shorts/run_codex_casual.bat`이 누락되어 있으면 V2 설치 파일이 자동으로 복구합니다.
- 데스크의 `02`, `03`, `15` 버튼은 렌더 파일이 없을 때 조용히 닫히지 않고 복구 안내를 표시합니다.
