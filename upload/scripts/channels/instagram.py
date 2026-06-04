"""
인스타그램 (Instagram Graph API) 캐러셀 업로드 모듈 — STUB.

가이드: PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 5-2.

선행 조건:
  - 인스타그램 계정이 프로페셔널(비즈니스) 로 전환
  - Facebook 페이지와 연동
  - 권한: instagram_basic, instagram_content_publish, pages_read_engagement

캐러셀 흐름 (3단계):
  1) 각 이미지마다 자식 컨테이너 생성 (is_carousel_item=true)
  2) 부모 캐러셀 컨테이너 생성 (media_type=CAROUSEL, children=...)
  3) /{ig-user-id}/media_publish 로 게시

제약:
  - 캡션 ≤ 2,200자
  - 해시태그 ≤ 30개
  - 캐러셀 컨테이너는 4시간 내 publish (만료)
  - 이미지 비율 1:1 권장 → output/<slug>/1x1/card_*.jpg 사용
"""
from __future__ import annotations

from pathlib import Path


def publish_carousel(
    ig_business_account_id: str,
    access_token: str,
    image_urls: list[str],
    caption: str,
) -> str:
    """카드 6장 캐러셀 게시. 반환: media ID."""
    raise NotImplementedError(
        "instagram.publish_carousel 미구현. "
        "PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 5-2 참고."
    )


def publish_from_slug(slug: str, assets_root: str | Path) -> str:
    raise NotImplementedError("instagram.publish_from_slug 미구현.")
