# -*- coding: utf-8 -*-
"""Create one copy-ready result folder for a Codex short.

V3 keeps exactly one active MP4 per render result folder.
The MP4 filename matches its parent folder:
  CODEX_VIDEO_DESK/RESULTS/<render-key>/<render-key>.mp4

Channel copy, upload checklist, source notes, and optional illustration
requests are written beside the MP4. The rendered MP4 is never re-encoded by
this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
CARDNEWS_OUTPUT = ROOT / "cardnews" / "output"
DESK = ROOT / "CODEX_VIDEO_DESK"
RESULTS = DESK / "RESULTS"
RUNTIME_SCRIPT = ROOT / "shorts" / "public" / "shorts_script.json"

# 캡션 템플릿 토큰 → 실제 링크(caption_template.md의 {LITTLY}/{PRECON_URL}) — 종민 지정 2026-06-19
LITTLY_URL = "https://litt.ly/phonespot"
PRECON_URL = "https://ictmarket.or.kr:8443/precon/pop_CertIcon.do?PRECON_REQ_ID=PRE0000194479&YN=1"


def apply_link_tokens(text: str) -> str:
    """캡션의 {LITTLY}=리틀리 허브, {PRECON_URL}=사전승낙서 토큰을 실제 URL로 치환."""
    return (text or "").replace("{LITTLY}", LITTLY_URL).replace("{PRECON_URL}", PRECON_URL)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace").replace("\r\n", "\n")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sections_from_captions(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^##\s+(\d+)\.\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:end].strip().strip("-").strip()
    return sections


def compact_text(value: str, fallback: str = "") -> str:
    value = re.sub(r"\r\n?", "\n", value or "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = value.strip()
    return value or fallback


def strip_youtube_extra_sections(text: str) -> str:
    """유튜브 설명에서 ▶타임스탬프 · ▶핵심 데이터 · ▶출처 블록을 제거한다.
    제목 + ▶영상 요약 + ▶휴대폰성지 폰스팟 + 사전승낙서 + 해시태그만 남긴다."""
    drops = ("타임스탬프", "핵심 데이터", "핵심데이터", "출처")
    out = []
    skipping = False
    for line in re.sub(r"\r\n?", "\n", text or "").split("\n"):
        st = line.strip()
        if st.startswith("▶"):
            name = st[1:].strip()
            skipping = any(name.startswith(d) for d in drops)
            if skipping:
                continue
        elif st.startswith("[사전승낙서]") or st.startswith("#"):
            skipping = False
        if skipping:
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def clean_youtube_description(value: str) -> str:
    if not value:
        return ""
    value = strip_youtube_extra_sections(value)
    value = compact_text(value)
    if "#Shorts" not in value and "#shorts" not in value:
        value = value.rstrip() + "\n\n#Shorts"
    return value


# 유튜브 제목에서 뺄 '장식' 문자: 이모지 + 장식용 괄호(【】〔〕「」『』《》〈〉 등).
# 문장부호(?! ~ . , - · 등)는 유지한다(후킹 허용).
_TITLE_EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"   # 그림 이모지(emoticons/symbols/transport 등)
    "\U00002600-\U000026FF"   # 기타 기호
    "\U00002700-\U000027BF"   # dingbats
    "\U0001F1E6-\U0001F1FF"   # 국기(지역 표시자)
    "\U00002B00-\U00002BFF"   # 기타 기호·별표
    "️‍"            # 변형 선택자 / ZWJ
    "]",
    flags=re.UNICODE,
)
_TITLE_DECOR_BRACKETS = "【】〔〕「」『』《》〈〉［］｛｝"


def clean_title(value: str, fallback: str) -> str:
    value = value or ""
    value = _TITLE_EMOJI.sub("", value)                                     # 이모지 제거
    value = value.translate({ord(c): None for c in _TITLE_DECOR_BRACKETS})  # 장식 괄호 제거(안쪽 글자 유지)
    value = re.sub(r"\s+", " ", value).strip() or fallback
    return value[:100].rstrip()


def script_data(slug: str) -> dict:
    path = CARDNEWS_OUTPUT / slug / "shorts_script.json"
    if not path.exists():
        return {}
    try:
        return json.loads(read_text(path))
    except json.JSONDecodeError:
        return {}


def article_captions(slug: str) -> str:
    """영상-only 슬러그는 output/<slug>/captions.md 가 없다(그 파일은 카드뉴스 렌더가 생성).
    그 경우 기사 JSON(cardnews/articles/<slug>.json)의 captions_md 로 폴백한다."""
    path = ROOT / "cardnews" / "articles" / f"{slug}.json"
    if not path.exists():
        return ""
    try:
        return str((json.loads(read_text(path)) or {}).get("captions_md") or "")
    except json.JSONDecodeError:
        return ""


def matching_runtime_script(slug: str) -> Path | None:
    if not RUNTIME_SCRIPT.exists():
        return None
    try:
        data = json.loads(read_text(RUNTIME_SCRIPT))
    except json.JSONDecodeError:
        return None
    return RUNTIME_SCRIPT if str(data.get("slug") or "") == slug else None


def preferred_title(slug: str, data: dict) -> str:
    return clean_title(
        str(data.get("video_title") or data.get("title_short") or data.get("title") or ""),
        slug.replace("_", " "),
    )


def source_line(path: Path) -> str:
    if not path.exists():
        return f"- missing: {path}"
    modified = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    return f"- {path} | modified={modified} | bytes={path.stat().st_size}"


def link_or_copy(src: Path, dst: Path) -> str:
    if src.resolve() == dst.resolve():
        return "in-place"
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
        return "hardlink"
    except OSError:
        shutil.copy2(src, dst)
        return "copy"


def result_video_path(package: Path) -> Path:
    return package / f"{package.name}.mp4"


def is_result_master(video: Path) -> bool:
    try:
        return video.parent.parent.resolve() == RESULTS.resolve() and video == result_video_path(video.parent)
    except OSError:
        return False


def unique_package(slug: str, date_text: str) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    key = f"{date_text}_{slug}_codex_remotion"
    package = RESULTS / key
    if not result_video_path(package).exists():
        return package
    return RESULTS / f"{key}_{datetime.now().strftime('%H%M%S')}"


def keyword_hashtags(text: str) -> list[str]:
    lowered = text.lower()
    tags = ["#폰스팟", "#휴대폰꿀팁", "#IT뉴스", "#스마트폰"]
    checks = [
        (("#아이폰", "#애플"), ["iphone", "ios", "apple", "아이폰", "애플"]),
        (("#갤럭시", "#삼성"), ["galaxy", "samsung", "갤럭시", "삼성"]),
        (("#보안", "#개인정보보호"), ["보안", "개인정보", "피싱", "사기", "도난", "분실"]),
        (("#지원금", "#휴대폰성지"), ["지원금", "보조금", "가격", "요금", "할인"]),
        (("#AI",), ["ai", "siri", "gemini", "제미나이", "시리", "인공지능"]),
        (("#업데이트",), ["업데이트", "베타", "oneui", "android"]),
    ]
    for add_tags, needles in checks:
        if any(needle in lowered or needle in text for needle in needles):
            tags.extend(add_tags)
    return list(dict.fromkeys(tags))


def one_line(value: str, limit: int = 85) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def build_title_candidates(title: str, slug: str) -> list[str]:
    base = clean_title(title, slug.replace("_", " "))
    candidates = [
        base,
        f"{base} | 휴대폰성지 폰스팟",
        one_line(f"{base} 핵심만 1분 정리", 60),
    ]
    return list(dict.fromkeys([candidate for candidate in candidates if candidate]))


def build_thumbnail_candidates(title: str, data: dict) -> list[str]:
    opening = data.get("opening") if isinstance(data.get("opening"), dict) else {}
    candidates = [
        str(opening.get("line1") or "").strip(),
        str(opening.get("line2") or "").strip(),
        title,
    ]
    cleaned = []
    for candidate in candidates:
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate:
            cleaned.append(one_line(candidate, 22))
    return list(dict.fromkeys(cleaned))[:3]


def build_upload_copy(
    *,
    slug: str,
    title: str,
    master_name: str,
    youtube_description: str,
    instagram: str,
    tiktok: str,
    data: dict,
) -> str:
    all_text = "\n".join([slug, title, youtube_description, instagram, tiktok])
    tags = keyword_hashtags(all_text)
    youtube_tags = " ".join(list(dict.fromkeys(tags + ["#Shorts"])))
    instagram_tags = " ".join(list(dict.fromkeys(tags + ["#릴스", "#Reels"])))
    tiktok_tags = " ".join(list(dict.fromkeys(tags + ["#틱톡", "#추천"])))
    title_candidates = build_title_candidates(title, slug)
    thumbnail_candidates = build_thumbnail_candidates(title, data)

    youtube_description = clean_youtube_description(youtube_description or instagram or tiktok)
    instagram = compact_text(instagram or youtube_description)
    tiktok = compact_text(tiktok or instagram)

    return f"""폰스팟 숏폼 발행 패키지

영상 파일
- {master_name}

사용 순서
1. 영상 파일을 끝까지 한 번 재생해서 자막 잘림, 음성 싱크, 마지막 CTA를 확인합니다.
2. 업로드할 채널 영역만 복사해서 붙여넣습니다.
3. 릴스와 틱톡은 앱에서 가장 읽기 좋은 프레임을 커버로 지정합니다.

============================================================
제목 후보
============================================================
{chr(10).join(f"- {candidate}" for candidate in title_candidates)}

============================================================
커버 문구 후보
============================================================
{chr(10).join(f"- {candidate}" for candidate in thumbnail_candidates) if thumbnail_candidates else "- 영상 첫 화면 제목 사용"}

============================================================
YOUTUBE SHORTS
============================================================

[제목]
{title_candidates[0]}

[설명]
{youtube_description}

[태그]
{youtube_tags}

============================================================
INSTAGRAM REELS
============================================================

[본문]
{instagram}

[태그]
{instagram_tags}

============================================================
TIKTOK
============================================================

[본문]
{tiktok}

[태그]
{tiktok_tags}

============================================================
고정 댓글 / 첫 댓글 후보
============================================================
- 더 궁금한 기능이나 가격 비교는 댓글로 남겨주세요.
- 휴대폰 구매 전 지원금 비교가 필요하면 폰스팟에서 확인해보세요.

============================================================
업로드 전 체크리스트
============================================================
- 첫 2초 안에 주제가 바로 보이는지 확인
- 긴 자막이 화면 밖으로 나가지 않는지 확인
- TTS 문장 전환과 화면 전환이 크게 어긋나지 않는지 확인
- 같은 원본 이미지가 반복 사용되어 지루해 보이지 않는지 확인
- CTA 문구가 고정 문구와 어긋나지 않는지 확인
- 유튜브는 세로 영상 + 30~35초 + #Shorts 포함 확인
- 인스타/틱톡은 업로드 후 자동 자막이 원본 자막을 가리지 않는지 확인
"""


def package_for(video: Path, slug: str, date_text: str | None = None) -> Path:
    video = video.resolve()
    if not video.exists():
        raise FileNotFoundError(f"video missing: {video}")

    date_text = date_text or datetime.now().strftime("%Y%m%d")
    package = video.parent if is_result_master(video) else unique_package(slug, date_text)
    package.mkdir(parents=True, exist_ok=True)

    captions_path = CARDNEWS_OUTPUT / slug / "captions.md"
    script_path = CARDNEWS_OUTPUT / slug / "shorts_script.json"
    override_path = DESK / "CHUNK_OVERRIDES" / f"{slug}.json"
    effective_script_path = matching_runtime_script(slug)
    captions = read_text(captions_path)
    if not captions.strip():
        captions = article_captions(slug)  # 영상-only: output/captions.md 없음 → 기사 JSON 폴백
    captions = apply_link_tokens(captions)  # {LITTLY}/{PRECON_URL} → 실제 URL
    sections = sections_from_captions(captions)
    data = script_data(slug)
    title = preferred_title(slug, data)
    instagram = sections.get("3") or captions
    youtube_description = clean_youtube_description(sections.get("4") or captions)
    tiktok = sections.get("5") or instagram
    master = result_video_path(package)
    master_mode = link_or_copy(video, master)

    for obsolete in (
        "youtube_title.txt",
        "youtube_description.txt",
        "youtube.txt",
        "instagram.txt",
        "tiktok.txt",
        "publish_checklist.txt",
        "README_FIRST.txt",
    ):
        path = package / obsolete
        if path.exists():
            path.unlink()

    write_text(
        package / "UPLOAD_COPY.txt",
        build_upload_copy(
            slug=slug,
            title=title,
            master_name=master.name,
            youtube_description=youtube_description,
            instagram=instagram,
            tiktok=tiktok,
            data=data,
        ),
    )

    illustration_md = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.md"
    illustration_json = CARDNEWS_OUTPUT / slug / "codex_illustration_requests.json"
    for source in (captions_path, illustration_md, illustration_json):
        if source.exists():
            shutil.copy2(source, package / source.name)
    if script_path.exists():
        shutil.copy2(script_path, package / "shorts_script.source.json")
    if effective_script_path:
        shutil.copy2(effective_script_path, package / "shorts_script.effective.json")
    if override_path.exists():
        shutil.copy2(override_path, package / "chunk_override.json")

    write_text(
        package / "source_manifest.txt",
        "\n".join(
            [
                "PhoneSpot Codex source manifest",
                f"- generated_at: {datetime.now().isoformat(timespec='seconds')}",
                f"- slug: {slug}",
                f"- package: {package}",
                f"- video_sha256: {sha256(master)}",
                f"- master_mode: {master_mode}",
                "",
                "[Sources]",
                source_line(video),
                source_line(captions_path),
                source_line(script_path),
                source_line(override_path),
                source_line(effective_script_path) if effective_script_path else "- missing: matching effective script",
                source_line(illustration_md),
                source_line(illustration_json),
            ]
        ),
    )
    write_json(
        package / "publish.json",
        {
            "version": 4,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "slug": slug,
            "title": title,
            "title_candidates": build_title_candidates(title, slug),
            "thumbnail_candidates": build_thumbnail_candidates(title, data),
            "master_video": master.name,
            "upload_copy": "UPLOAD_COPY.txt",
            "master_mode": master_mode,
            "master_video_sha256": sha256(master),
            "source_script_sha256": sha256(script_path) if script_path.exists() else "",
            "effective_script_sha256": sha256(effective_script_path) if effective_script_path else "",
            "chunk_override_sha256": sha256(override_path) if override_path.exists() else "",
            "hashtags": keyword_hashtags("\n".join([slug, title, youtube_description, instagram, tiktok])),
            "channels": {
                "youtube_shorts": {
                    "video": master.name,
                    "copy_source": "UPLOAD_COPY.txt#YOUTUBE SHORTS",
                },
                "instagram_reels": {
                    "video": master.name,
                    "copy_source": "UPLOAD_COPY.txt#INSTAGRAM REELS",
                },
                "tiktok": {
                    "video": master.name,
                    "copy_source": "UPLOAD_COPY.txt#TIKTOK",
                },
            },
        },
    )
    print(f"[result-package-v4] folder: {package}")
    print(f"[result-package-v4] master: {master.name} ({master_mode})")
    return package


def latest_video() -> Path | None:
    current = [
        path
        for path in RESULTS.glob("*/*.mp4")
        if path == result_video_path(path.parent)
    ]
    if current:
        return max(current, key=lambda path: path.stat().st_mtime)
    return None


def infer_slug(video: Path) -> str:
    if video.parent.parent.resolve() == RESULTS.resolve():
        name = video.parent.name
    else:
        name = video.stem
    match = re.match(r"\d{8}_(.+)_codex_remotion(?:_\d{6})?$", name)
    if match:
        return match.group(1)
    match = re.match(r"(.+)_\d{8}_codex_remotion(?:_\d{6})?$", name)
    if match:
        return match.group(1)
    raise ValueError(f"could not infer slug from: {video}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("video", nargs="?")
    parser.add_argument("slug", nargs="?")
    parser.add_argument("date", nargs="?")
    parser.add_argument("--latest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.latest:
        video = latest_video()
        if not video:
            print("[ERROR] No Codex Remotion result found.")
            return 1
        package_for(video, args.slug or infer_slug(video))
        return 0
    if not args.video or not args.slug:
        print("[ERROR] Usage: publish_codex_package.py VIDEO SLUG [YYYYMMDD]")
        print("        publish_codex_package.py --latest")
        return 1
    package_for(Path(args.video), args.slug, args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
