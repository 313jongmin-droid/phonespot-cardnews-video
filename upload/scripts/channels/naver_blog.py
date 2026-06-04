"""
네이버 블로그 반자동 게시 모듈 — STUB.

가이드: PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 5-5.

공식 API 가 없으므로 두 가지 옵션:
  A) Cowork 의 mcp__claude-in-chrome__* 로 브라우저 자동화
  B) Playwright 로 자동화 (계정 정지 리스크 큼 — 비권장)

원칙:
  - 자동 로그인 절대 금지 (이상 트래픽 탐지 → 정지)
  - 이미 로그인된 세션만 활용
  - 본문 입력까지 자동, "발행" 버튼은 사용자가 수동 클릭

이 파일은 stub. 실제 자동화 코드는 채널 모듈 작성 단계에서
A) 옵션 (Chrome MCP) 우선 시도, 한계 시 B) 옵션 검토.
"""
from __future__ import annotations

from pathlib import Path


def prepare_post(
    title: str,
    body_markdown: str,
    image_paths: list[str | Path],
    tags: list[str] | None = None,
) -> None:
    """에디터에 제목/본문/이미지 입력까지 자동화. 발행 버튼은 누르지 않음.

    Chrome MCP 사용을 권장 — 이 함수는 그 호출을 감싸는 형태로 구현 예정.
    """
    raise NotImplementedError(
        "naver_blog.prepare_post 미구현. "
        "PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 5-5 참고. "
        "Chrome MCP (mcp__claude-in-chrome__*) 사용 권장."
    )


def publish_from_slug(slug: str, assets_root: str | Path) -> None:
    raise NotImplementedError("naver_blog.publish_from_slug 미구현.")
