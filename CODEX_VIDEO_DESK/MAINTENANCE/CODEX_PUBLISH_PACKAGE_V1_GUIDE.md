# Codex Publish Package V1

V1은 영상 렌더 결과를 수정하지 않고, 업로드 직전 필요한 파일을 한 폴더로 묶습니다.

## 설치

`RUN_APPLY_CODEX_PUBLISH_PACKAGE_V1.bat`를 한 번 실행합니다.

## 자동 결과

정상 렌더가 끝나면 아래 폴더가 추가됩니다.

```text
upload_codex/PUBLISH_PACKAGES/YYYYMMDD_<slug>/
├─ video_master_9x16.mp4
├─ youtube.txt
├─ youtube_title.txt
├─ youtube_description.txt
├─ instagram.txt
├─ tiktok.txt
├─ publish.json
├─ publish_checklist.txt
├─ cover_frame_guide.txt
├─ README_FIRST.txt
└─ source_manifest.txt
```

기존 `upload_codex/*.mp4` 파일도 그대로 유지합니다.

## 데스크 버튼

- `13_REFRESH_LATEST_PUBLISH_PACKAGE.bat`: 가장 최근 영상 패키지를 다시 생성합니다.
- `14_OPEN_PUBLISH_PACKAGES.bat`: 패키지 폴더를 엽니다.

## V1 범위

- YouTube Shorts, Instagram Reels, TikTok용 문구 분리
- YouTube Shorts 문구에서 장편 영상용 타임스탬프 제거
- 한 개의 1080x1920 H.264 MP4를 세 채널에서 공통 사용
- 영상, TTS, 청크, CTA, Remotion 화면 구성은 변경하지 않음

커버 이미지는 V2 실험으로 분리합니다.
