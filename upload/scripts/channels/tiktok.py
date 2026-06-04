"""
틱톡 (Content Posting API) 업로드 모듈 — STUB.

가이드: PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 5-4.

흐름:
  1) /v2/post/publish/inbox/video/init/  (upload_url 획득)
  2) PUT upload_url  (video bytes)
  3) (Direct Post 권한 있을 때만) /v2/post/publish/video/init/

권한:
  - video.upload: 기본. 업로드만 되고 사용자가 앱에서 최종 게시
  - video.publish: Direct Post. 별도 심사 필요 (대부분 첫 신청 거절)

토큰 만료:
  - access_token 24시간 / refresh_token 365일 (섹션 9)
"""
from __future__ import annotations

from pathlib import Path


def upload_inbox(
    video_path: str | Path,
    access_token: str,
) -> str:
    """Upload 만. 사용자가 TikTok 앱에서 최종 게시.

    반환: publish_id (TikTok 측 추적용)
    """
    raise NotImplementedError(
        "tiktok.upload_inbox 미구현. "
        "PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 5-4 참고."
    )


def direct_post(
    video_path: str | Path,
    title: str,
    access_token: str,
    privacy_level: str = "PUBLIC_TO_EVERYONE",
) -> str:
    """Direct Post (video.publish 권한 필요)."""
    raise NotImplementedError("tiktok.direct_post 미구현. Direct Post 권한 심사 필요.")


def publish_from_slug(slug: str, assets_root: str | Path) -> str:
    raise NotImplementedError("tiktok.publish_from_slug 미구현.")
