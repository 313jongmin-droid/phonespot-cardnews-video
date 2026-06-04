# -*- coding: utf-8 -*-
"""Install the concise UTF-8 Codex-only PhoneSpot Remotion baseline guide."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path


SHORTS = Path(r"C:\Users\di898\Documents\phonespot_cardnews\shorts")
CODEX = SHORTS / "codex"
BASELINE = CODEX / "CODEX_BASELINE.md"
README = CODEX / "README_FOR_CODEX.md"
MEMORY = CODEX / "CODEX_MEMORY.md"
PATCH_LOG = CODEX / "codex_patch_log.md"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

BASELINE_TEXT = """# CODEX_BASELINE

PhoneSpot Remotion 영상의 Codex 기준선입니다.

## 1. 경계

- Claude 카드뉴스 기본 파이프라인은 건드리지 않습니다.
- Codex는 Remotion 쇼츠 영상과 `CODEX_VIDEO_DESK` 작업 흐름만 담당합니다.
- 일상 작업의 시작점은 `C:\\Users\\di898\\Documents\\phonespot_cardnews\\CODEX_VIDEO_DESK`입니다.
- `upload_codex`와 `shorts\\out_codex`는 활성 작업 폴더로 사용하지 않습니다.

## 2. 입력

- 카드뉴스 본문: `cardnews/output/<slug>/captions.md`
- 카드뉴스 GPT 원본 이미지: `cardnews/images/<slug>/1.png` ~ `5.png`
- 영상 청크: `cardnews/output/<slug>/shorts_script.json`
- `captions.md`의 영상 나레이션을 TTS 우선 입력으로 사용합니다.

## 3. 한국어 자막

- 청크는 전체 문맥을 보고 자연스러운 한국어 문장으로 다듬습니다.
- 조사를 훼손하지 않고 서술어 없는 단어 나열을 피합니다.
- 연결되는 청크는 `-고`, `-며`, `-지만`, `-는데` 등 자연스러운 연결형을 사용합니다.
- 화면 자막의 마침표는 표시하지 않습니다.
- 1초 미만 청크와 과도하게 긴 청크를 방지합니다.
- 화면 청크는 해당 구간 TTS 원문을 순서대로 빠짐없이 나눈 결과여야 합니다.
- 마침표 숨김 외에는 화면 청크의 단어를 추가, 삭제, 치환하지 않습니다.
- TTS 발음 사전은 음성 합성에만 적용하고 화면 자막 원문은 바꾸지 않습니다.

## 4. 고정 CTA

1. `휴대폰 구매할 땐?`
2. `지원금부터 무료로 조회해보세요`

마지막 비주얼은 PhoneSpot 로고입니다.

## 5. 비주얼

- 카드뉴스 GPT 원본 이미지 `1.png` ~ `5.png`를 문맥에 맞게 사용합니다.
- 원본 이미지는 한 영상 안에서 각각 최대 1회만 사용합니다.
- 추가 비주얼은 문맥에 맞는 일러스트 또는 동적 인포그래픽을 우선합니다.
- GPT 원본 이미지만 노출 시간 비례 모션을 적용합니다.
- 일러스트, CTA, 로고, 마스코트, 인포그래픽 자체는 고정합니다.
- 일러스트 배경에는 약한 빛 번짐, 진행 라인, 소프트 그리드, 종이 질감만 허용합니다.
- 새 일러스트 요청은 기사 하나에 최대 3개이며 재사용 가능한 개념으로 프롬프트를 작성합니다.

## 6. 출력

- TTS 기본값: `ko-KR-SunHiNeural`, `+42%`, loudness normalization
- 영상 기본값: H.264, `yuv420p`, bt709, AAC, fast start
- 최종 저장: `CODEX_VIDEO_DESK/RESULTS/<렌더 이름>/`
- 렌더 중간 파일: `CODEX_VIDEO_DESK/TEMP/_raw/`
- 재사용 일러스트 실제 저장소: `CODEX_VIDEO_DESK/ILLUSTRATION_DROP/`
- 각 결과 폴더에는 폴더명과 같은 MP4, `captions.md`, `UPLOAD_COPY.txt`를 함께 둡니다.

## 7. 일상 실행

1. `01_PREPARE_GPT_PROMPTS.bat`
2. 필요 시 GPT Plus에서 일러스트 생성 후 다운로드
3. `02_IMPORT_DOWNLOADS_AND_RENDER.bat`

신규 이미지가 필요 없으면 `03_RENDER_LATEST_WITHOUT_NEW_IMAGES.bat`를 사용합니다.
기존 슬러그를 고르려면 `15_SELECT_AND_RENDER_EXISTING.bat`를 사용합니다.

## 8. 보존

- 특정 슬러그 번호에만 맞춘 하드코딩은 금지합니다.
- 새 기능은 기존 품질 기준을 지우지 않고 추가합니다.
- Claude 실행 파일과 Claude 결과물을 임의로 수정하지 않습니다.
- 변경 전 `CODEX_MASTER_VIDEO_GUIDE.md`를 먼저 읽습니다.
- 화면 청크를 TTS와 별도 요약문으로 되돌리지 않습니다.
- 모든 문장에 조사나 종결어미를 추측하여 덧붙이지 않습니다.
- 결과 저장소를 다시 `out_codex` 또는 `upload_codex`로 분산하지 않습니다.
"""


def append_once(path: Path, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    if marker in text:
        return
    if text and not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + body.rstrip() + "\n", encoding="utf-8")


def patch_readme() -> None:
    text = README.read_text(encoding="utf-8", errors="replace") if README.exists() else "# README_FOR_CODEX\n"
    marker = "CODEX_BASELINE.md"
    if marker in text:
        return
    if README.exists():
        backup = README.with_name(README.name + f".bak_baseline_{STAMP}")
        backup.write_text(text, encoding="utf-8")
    addition = "\n## Codex read order\n\n1. `CODEX_BASELINE.md`\n2. `README_FOR_CODEX.md`\n3. `CODEX_MEMORY.md` only when historical context is needed\n"
    README.write_text(text.rstrip() + "\n" + addition, encoding="utf-8")


def main() -> int:
    CODEX.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(BASELINE_TEXT, encoding="utf-8")
    append_once(
        BASELINE,
        "## Caption display color contract",
        """## Caption display color contract
- Screen-caption text uses one readable text color only.
- Do not infer or render orange or yellow inline caption highlights.
- Orange remains available for structural brand accents, CTA elements, headers, and infographics.""",
    )
    append_once(
        BASELINE,
        "## Fixed caption font and independent visual rhythm",
        """## Fixed caption font and independent visual rhythm
- Casual screen captions use one stable `72px` font size.
- Long narration is split conservatively at Korean grammar boundaries instead of shrinking text.
- Caption windows follow edge-tts timing. Source-image windows normally hold for about `2.2~4.2s`.
- CTA visuals, illustrations, logos, mascots, and infographics remain static.""",
    )
    patch_readme()
    append_once(
        MEMORY,
        "## 33. Desk-only canonical storage",
        """## 33. Desk-only canonical storage
- Daily Codex video files live physically under `CODEX_VIDEO_DESK`.
- Results: `CODEX_VIDEO_DESK/RESULTS/`
- Raw temporary renders: `CODEX_VIDEO_DESK/TEMP/_raw/`
- Reusable illustration library: `CODEX_VIDEO_DESK/ILLUSTRATION_DROP/`
- `shorts/public/assets/illustrations/` is an automatically refreshed internal Remotion cache only.
- Do not restore active `upload_codex/` or `shorts/out_codex/` storage.""",
    )
    append_once(
        PATCH_LOG,
        "## 2026-06-01 - Desk-only canonical storage",
        """## 2026-06-01 - Desk-only canonical storage
- Replaced the Codex guide with readable UTF-8 Korean.
- Made `CODEX_VIDEO_DESK` the canonical daily video workspace.
- Kept Claude folders and Claude runners untouched.""",
    )
    print(f"[write] {BASELINE}")
    print("[done] Clean Codex baseline guide installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
