

## Single-folder result package V2

- Completed Codex renders are stored only in `upload_codex/RESULTS/<render-key>/`.
- Each result folder contains one MP4 whose filename matches the folder name, source captions, and one `UPLOAD_COPY.txt` publishing document.
- `shorts/out_codex/` is temporary raw-render storage only. Completed MP4 files are not kept there.
- The desk `OUT_CODEX` junction is removed. Render history lives inside `CODEX_VIDEO_DESK/RESULTS/`.
- A rerender creates a timestamp-suffixed result folder and never overwrites an earlier result.

## TTS-caption lockstep
- 화면 청크는 해당 구간 TTS 원문을 순서대로 빠짐없이 분할한 결과입니다.
- 화면 자막용 별도 요약문을 만들지 않습니다.
- 마침표 숨김 외에는 단어 추가·삭제·치환을 금지합니다.
- 기존 고정 CTA, 원본 이미지 1회 사용, 일러스트 균형, 한국어 자연스러움 규칙을 유지합니다.

## Caption display color contract
- Screen-caption text uses one readable text color only.
- Do not infer or render orange or yellow inline caption highlights.
- Orange remains available for structural brand accents, CTA elements, and infographics.

## Fixed caption font and independent visual rhythm
- Casual screen captions render at one stable 72px font size.
- Long narration is split at Korean sentence, comma, connective-ending, or safe word boundaries instead of shrinking caption text.
- Caption windows follow edge-tts WordBoundary timing. A sub-650ms caption window blocks rendering; sub-1100ms windows are reported.
- Visual windows are independent from caption windows and generally stay visible for about 2.2 to 4.2 seconds.
- CTA visuals, illustrations, logos, mascots, and infographics remain static. Existing CTA, source-image-once, Korean, and TTS lockstep contracts remain active.

## Semantic Visual Match

- `images/<slug>/prompt.md`의 `1.png~5.png` 설명을 읽어 청크 문맥과 맞는 원본 GPT 이미지를 우선 배치한다.
- 원본 GPT 이미지는 한 영상 안에서 1회만 사용한다.
- 이미지 설명 점수가 낮으면 태그 DB 기반 재사용 일러스트를 사용한다.
- CTA는 고정 전환 화면이므로 기존 CTA 일러스트/로고 계약을 유지한다.
- 결과 리포트는 `cardnews/output/<slug>/codex_semantic_visual_match_report.md`에 남긴다.

## Unique Illustration Guard

- 같은 영상 안에서 같은 `illust:<variant>` 또는 같은 마스코트를 반복 사용하지 않는다.
- `logo`는 CTA 고정 계약이므로 중복 검사에서 제외한다.
- 중복이 발견되면 청크 문맥을 기준으로 태그 DB에서 다른 일러스트를 고른다.
- 대체 후보가 부족하면 억지 교체하지 않고 `codex_unique_illustration_guard_report.md`에 남긴다.

## Illustration Scout Gap Prompts

- 약한 매핑 경고가 있으면 경고만 남기지 말고, 재사용 가능한 범용 일러스트 프롬프트를 최대 3개까지 생성한다.
- 프롬프트는 특정 기사 전용 세부사항을 피하고, 출시 일정·언팩 행사·커버 화면·카메라 제어처럼 반복 사용 가능한 개념으로 만든다.
- 이미 라이브러리에 있는 variant는 다시 요청하지 않는다.

## Network Assistant PC Optional State

- `illustration_usage_history.json`, `ILLUSTRATION_TAG_DB.md`, `illustration_tag_db.json`은 영상 렌더 필수 파일이 아니다.
- 다른 PC가 네트워크 공유에서 실행할 때 해당 파일 쓰기 권한이 없으면 실패하지 않고 `%LOCALAPPDATA%\PhoneSpotCodexVideo\codex_state`에 로컬 사본을 저장한다.
- 카드뉴스 output, CODEX_VIDEO_DESK RESULTS 같은 실제 산출물은 여전히 공유 폴더 쓰기 권한이 필요하다.

