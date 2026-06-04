"""
captions.md 를 채널별 dict 로 파싱하는 유틸.

문서 PROJECT_INSTRUCTIONS_UPLOAD.md 의 captions.md 파싱 규칙:
  - "## 1. 네이버 블로그" / "## 2. 스레드" / "## 3. 인스타그램"
    "## 4. 유튜브" / "## 5. 틱톡" 헤더 기준으로 분리
  - 헤더에 부가 설명(예: "(장문 · SEO)") 이 붙어도 substring 매칭으로 식별
  - 본문 내 {LITTLY} {PRECON_URL} 토큰은 환경변수 값으로 치환

이 파일은 외부 API 호출 없음. 다른 모듈이 import 해 사용.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Dict


HEADER_TO_CHANNEL = {
    "네이버 블로그": "naver_blog",
    "스레드": "threads",
    "인스타그램": "instagram",
    "유튜브": "youtube",
    "틱톡": "tiktok",
}

HEADER_RE = re.compile(r"^##\s+(?:\d+\.\s+)?(.+?)\s*$", re.MULTILINE)


def parse_captions_file(path):
    """captions.md 파일을 읽어 채널 키 -> 본문 dict 로 반환."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_captions_text(text)


def parse_captions_text(text):
    """captions.md 문자열을 채널별 dict 로 분리."""
    matches = list(HEADER_RE.finditer(text))
    if not matches:
        return {}

    result = {}
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        channel = None
        for keyword, ch in HEADER_TO_CHANNEL.items():
            if keyword in header:
                channel = ch
                break
        if not channel:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[channel] = text[start:end].strip()
    return result


def substitute_tokens(caption, env=None):
    """{LITTLY} {PRECON_URL} 같은 토큰을 환경변수 값으로 치환."""
    if env is None:
        env = dict(os.environ)

    def _replace(match):
        key = match.group(1)
        return env.get(key, match.group(0))

    return re.sub(r"\{([A-Z_][A-Z0-9_]*)\}", _replace, caption)


def load_channel_caption(captions_md_path, channel, env=None):
    """편의 함수: 파일 -> 채널 본문 추출 -> 토큰 치환까지 한번에."""
    all_captions = parse_captions_file(captions_md_path)
    if channel not in all_captions:
        raise KeyError(
            "채널 '{}' 섹션을 captions.md 에서 찾지 못함. 존재: {}".format(
                channel, list(all_captions.keys())
            )
        )
    return substitute_tokens(all_captions[channel], env)


def _main():
    if len(sys.argv) < 2:
        print("Usage: python caption_parser.py <captions.md path> [channel]")
        sys.exit(1)

    md_path = sys.argv[1]
    captions = parse_captions_file(md_path)
    print("발견된 채널:", list(captions.keys()))

    if len(sys.argv) >= 3:
        ch = sys.argv[2]
        body = captions.get(ch)
        if body is None:
            print("\n채널 '{}' 섹션 없음.".format(ch))
            return
        print("\n----- 본문 (토큰 치환 전) -----")
        print(body)
        print("\n----- 본문 (토큰 치환 후) -----")
        print(substitute_tokens(body))


if __name__ == "__main__":
    _main()
