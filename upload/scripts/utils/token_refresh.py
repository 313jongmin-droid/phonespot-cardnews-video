"""
OAuth 토큰 갱신 공통 유틸 (stub).

각 채널의 토큰 만료 정책 (문서 섹션 9 기준):
  - Meta (Threads/Instagram): long-lived 60일
  - Google (YouTube): refresh_token 이용해 access_token 무기한 갱신
  - TikTok: access 24시간 + refresh 365일

향후 구현 시 다음 형태 권장:
    def refresh_meta_long_lived(short_lived_token: str) -> str: ...
    def refresh_google_creds(client_secrets_path: str, token_cache: str): ...
    def refresh_tiktok(refresh_token: str) -> dict: ...

지금은 stub. 실제 호출 코드는 채널별 모듈 작성 시점에 채워넣음.
"""
from __future__ import annotations


def _not_implemented(name: str) -> None:
    raise NotImplementedError(
        f"{name} 은 아직 구현되지 않았습니다. "
        "PROJECT_INSTRUCTIONS_UPLOAD.md 섹션 5 의 채널별 가이드를 참고하여 구현하세요."
    )


def refresh_meta_long_lived(short_lived_token: str) -> str:
    """short-lived → long-lived (60일) 교환.

    엔드포인트: https://graph.facebook.com/v19.0/oauth/access_token
      ?grant_type=fb_exchange_token
      &client_id=META_APP_ID
      &client_secret=META_APP_SECRET
      &fb_exchange_token={short_lived_token}
    """
    _not_implemented("refresh_meta_long_lived")
    return ""  # unreachable


def refresh_google_creds(client_secrets_path: str, token_cache_path: str):
    """google-auth 의 Credentials.from_authorized_user_file + creds.refresh(Request())."""
    _not_implemented("refresh_google_creds")


def refresh_tiktok(refresh_token: str) -> dict:
    """엔드포인트: https://open.tiktokapis.com/v2/oauth/token/ (grant_type=refresh_token)."""
    _not_implemented("refresh_tiktok")
    return {}  # unreachable
