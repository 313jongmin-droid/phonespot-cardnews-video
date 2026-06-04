"""
.env 파일 로더 + 필수 키 검증.

python-dotenv 가 설치되어 있으면 그걸 사용,
없으면 매우 단순한 KEY=VALUE 파서로 fallback.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def load_env(env_path: str | Path | None = None) -> None:
    """upload/.env 를 os.environ 에 로드.

    env_path 가 None 이면 이 파일 기준으로 upload/.env 를 탐색.
    """
    if env_path is None:
        # 이 파일: upload/scripts/utils/env_loader.py
        # → upload/.env
        env_path = Path(__file__).resolve().parents[2] / ".env"

    env_path = Path(env_path)
    if not env_path.exists():
        return  # .env 없으면 silently skip (CI 등 환경변수 직접 주입 케이스 허용)

    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(env_path, override=False)
        return
    except ImportError:
        pass

    # fallback: 매우 단순한 파서
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def require_keys(keys: Iterable[str]) -> dict[str, str]:
    """필수 환경변수 검증. 누락 시 RuntimeError.

    Returns:
        {key: value} dict
    """
    missing: list[str] = []
    result: dict[str, str] = {}
    for k in keys:
        v = os.environ.get(k, "").strip()
        if not v:
            missing.append(k)
        else:
            result[k] = v
    if missing:
        raise RuntimeError(
            f".env 에 누락된 필수 키: {missing}. "
            "upload/.env.example 참고하여 채워주세요."
        )
    return result
