# IGNORE_RULES

> AI와 사람이 모두 참고할 **제외 규칙**. 작업 시 절대 재귀 탐색·전체 읽기 금지 항목.

---

## 절대 재귀 탐색하지 말 것 (대용량·바이너리)

```
node_modules/
out/
out_codex/
hyperframes_codex/
codex/   # Claude default work ignores this. Codex may read codex/*.md.
public/audio/
public/assets/1.png ~ 5.png
public/assets/logos/*.png
public/assets/illustrations/*.png
*.mp4
*.mp3
*.zip
*.codexbak_*
*.codexfixbak_*
```

이유:
- **node_modules**: 수만 개 파일. 컨텍스트 폭증.
- **out / out_codex**: 완성된 mp4. 텍스트 추출 무의미.
- **hyperframes_codex**: 실험 빌드 산출물.
- **public/audio**: TTS 결과 mp3. 바이너리.
- **public/assets/*.png**: 이미지 바이너리.
- **logos / illustrations**: PNG. 텍스트 없음.
- **\*.mp4 / \*.mp3 / \*.zip**: 바이너리.
- **\*.codexbak_\* / \*.codexfixbak_\***: Codex 자동 백업. 옛 코드라 혼동 위험.

---

## 작업 지시 있을 때만 직접 지정해서 읽기

위 항목들도 다음 조건이면 OK (재귀 ❌, 단일 파일만):

- 사용자가 명시적으로 "이 파일 봐줘"라고 한 경우
- 영상 미리보기 등 시각 분석이 명시적으로 요청된 경우 (이때도 프레임 추출 등으로 제한)
- 백업 파일 비교가 명시적으로 요청된 경우

예시 (OK):
- "out/galaxy_price_hike.mp4 첫 프레임 확인해줘"
- "codex_casual_v2.codexbak_20260527의 import 부분만 봐줘"

예시 (NG):
- "out 폴더 안 다 살펴봐"
- "node_modules에서 react 관련 찾아봐"

---

## Grep / 검색 시 제외 패턴

`scripts/`, `src/`, `harness/`, `articles/`, `output/` 위주로 검색. 기본 무시할 패턴:

```
**/node_modules/**
**/out/**
**/out_codex/**
**/hyperframes_codex/**
**/codex/**   # Claude default work ignores this. Codex reads codex/*.md only when acting as Codex.
**/public/audio/**
**/public/assets/**
**/*.mp4
**/*.mp3
**/*.zip
**/*.codexbak_*
**/*.codexfixbak_*
```

---

## 이미지·영상 시각 분석 룰

- AI가 이미지를 직접 보는 건 **사용자가 명시 요청할 때만**
- 영상 전체를 한 번에 못 봄 → 프레임 추출 후 일부만 확인:
  ```cmd
  ffmpeg -i out/<slug>.mp4 -vf "select=eq(n\,0)" -frames:v 1 frame_0.png
  ```
- 자동 검증은 `verify_video_quality.py`가 메타데이터(픽셀포맷·비트레이트 등)만 봄. 시각 콘텐츠는 검사 안 함.

---

## 디스크 용량 점검 시

전체 폴더 크기 확인 명령은 가능. 단 결과 출력 시 위 제외 항목은 별도 표시:

```cmd
du -sh phonespot-news-shorts/*
```

- 보통 `node_modules`가 가장 크고, 다음 `out`, `out_codex` 순
- 이게 정상. 줄이고 싶으면 사용자 명시 요청 시에만 정리

---

## 한 줄 요약

> **AI는 `harness/`, `scripts/`, `src/`, `articles/`, `output/<slug>/captions.md` 정도만 자유롭게. 그 외는 사용자 지정 시에만.**
