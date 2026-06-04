"""
폰스팟 카드뉴스 - Gemini 이미지 생성 스크립트

지원 모델:
  - gemini-2.5-flash-image (Gemini 네이티브, 일명 nano-banana, 한글 프롬프트 OK)
  - imagen-4.0-fast-generate-001 / imagen-4.0-generate-001 / imagen-4.0-ultra-generate-001

사용법:
  py scripts\\generate_image.py --prompt "..." --output images/iphone18/cover.png
  py scripts\\generate_image.py --prompt "..." --output ... --aspect 9:16 --model imagen-4.0-fast-generate-001
"""
import argparse
import base64
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
KEY_FILE = PROJECT_ROOT.parent / "_secrets" / "gemini_key.txt"

# 폴백 순서: nano-banana 먼저 (한글 프롬프트 잘 이해 + 톤 자연스러움)
DEFAULT_MODELS = [
    "gemini-2.5-flash-image",          # nano-banana
    "imagen-4.0-fast-generate-001",    # Imagen 4 Fast (저렴)
    "imagen-4.0-generate-001",         # Imagen 4 Standard
]


def load_api_key() -> str:
    if not KEY_FILE.exists():
        sys.exit(
            f"[오류] API 키 파일이 없습니다: {KEY_FILE}\n"
            "Cowork에 'API 키 등록 다시 해줘'라고 말씀하세요."
        )
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key.startswith("AIza"):
        sys.exit(f"[오류] 키 형식 비정상. 'AIza'로 시작해야 합니다. 현재: {key[:10]}...")
    return key


def post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body[:600]}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"네트워크 오류: {e}") from None


def call_imagen(prompt: str, api_key: str, model: str, aspect_ratio: str) -> bytes:
    """Imagen 4 계열 (predict 엔드포인트)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:predict?key={api_key}"
    )
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            "personGeneration": "dont_allow",
        },
    }
    data = post_json(url, payload)
    preds = data.get("predictions", [])
    if not preds or "bytesBase64Encoded" not in preds[0]:
        raise RuntimeError(f"응답에 이미지 없음: {str(data)[:400]}")
    return base64.b64decode(preds[0]["bytesBase64Encoded"])


def call_gemini_image(prompt: str, api_key: str, model: str, aspect_ratio: str) -> bytes:
    """Gemini Flash Image 계열 (generateContent 엔드포인트, 멀티모달)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    # Gemini는 직접 aspectRatio 파라미터 없음 → 프롬프트에 비율 힌트 추가
    aspect_hint = {
        "1:1": "square 1:1 composition",
        "9:16": "vertical 9:16 portrait composition, tall format",
        "16:9": "horizontal 16:9 landscape composition, wide format",
        "4:5": "vertical 4:5 portrait composition",
        "3:4": "vertical 3:4 portrait composition",
        "4:3": "horizontal 4:3 landscape composition",
    }.get(aspect_ratio, "")
    full_prompt = f"{prompt}\n\nFormat: {aspect_hint}" if aspect_hint else prompt

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
        },
    }
    data = post_json(url, payload)
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"응답에 candidates 없음: {str(data)[:400]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part and "data" in part["inlineData"]:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError(f"응답에 이미지 데이터 없음. parts: {str(parts)[:400]}")


def call_model(prompt: str, api_key: str, model: str, aspect_ratio: str) -> bytes:
    """모델 이름 기반으로 적절한 호출 함수 분기."""
    if "imagen" in model.lower():
        return call_imagen(prompt, api_key, model, aspect_ratio)
    elif "gemini" in model.lower():
        return call_gemini_image(prompt, api_key, model, aspect_ratio)
    else:
        # 기본: predict 시도
        return call_imagen(prompt, api_key, model, aspect_ratio)


def generate(prompt: str, output: Path, aspect_ratio: str, models: list) -> None:
    api_key = load_api_key()
    print(f"프롬프트: {prompt[:120]}{'...' if len(prompt) > 120 else ''}")
    print(f"비율: {aspect_ratio} / 출력: {output}")

    last_err = None
    for model in models:
        print(f"  → 모델 시도: {model}")
        try:
            image_bytes = call_model(prompt, api_key, model, aspect_ratio)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(image_bytes)
            kb = len(image_bytes) // 1024
            print(f"  ✓ 성공: {output} ({kb} KB) [모델: {model}]")
            return
        except RuntimeError as e:
            print(f"  ✗ 실패: {e}")
            last_err = e
            continue

    sys.exit(f"\n[최종 실패] 모든 모델 시도 실패. 마지막 오류:\n{last_err}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gemini 이미지 생성")
    parser.add_argument("--prompt", required=True, help="이미지 프롬프트 (한글 OK)")
    parser.add_argument("--output", required=True, help="저장 경로 (프로젝트 루트 기준 또는 절대 경로)")
    parser.add_argument(
        "--aspect",
        default="1:1",
        choices=["1:1", "3:4", "4:3", "4:5", "9:16", "16:9"],
        help="가로:세로 비율 (기본 1:1)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="특정 모델 강제 지정 (미지정 시 폴백 자동)",
    )
    args = parser.parse_args()

    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output

    models = [args.model] if args.model else DEFAULT_MODELS
    generate(args.prompt, output, args.aspect, models)


if __name__ == "__main__":
    main()
