import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BRAND = "\ud3f0\uc2a4\ud31f"
TAGLINE = "\ub0b4 \uc190 \uc548\uc758 \ud734\ub300\ud3f0 \uc131\uc9c0"
TODAY_NEWS = "\uc624\ub298\uc758 IT \ub274\uc2a4"
CTA_TEXT = "\uc9c0\uc6d0\uae08\ubd80\ud130 \ubb34\ub8cc\ub85c \uc870\ud68c\ud574\ubcf4\uc138\uc694"
PHONE_CHECK = "\ud3f0\uc2a4\ud31f \uccb4\ud06c"

if len(sys.argv) < 2:
    print("Usage: python scripts/prepare_hyperframes.py <slug>")
    sys.exit(1)

slug = sys.argv[1]
project_root = Path(__file__).parent.parent
public_dir = project_root / "public"
script_path = public_dir / "shorts_script.json"
audio_dir = public_dir / "audio"
assets_dir = public_dir / "assets"
hf_dir = project_root / "hyperframes_codex"

if not script_path.exists():
    print(f"[ERROR] Missing {script_path}. Run copy_assets.py first.")
    sys.exit(1)

with open(script_path, encoding="utf-8") as f:
    script = json.load(f)


def media_duration(path: Path, fallback: float = 4.0) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if result.returncode == 0:
            value = float(result.stdout.strip())
            if value > 0:
                return value
    except Exception:
        pass
    return fallback


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def emphasize(text: str) -> str:
    out = esc(text)
    for token in ["\ub9cc\uc6d0", "\uc720\ub85c", "\ub2ec\ub7ec", "%", "WWDC", "iOS", "Siri", "Gemini"]:
        out = out.replace(esc(token), f"<span>{esc(token)}</span>")
    return out


def render_visual(cv: dict) -> str:
    t = cv.get("type", "image")
    v = cv.get("value")
    if t == "image":
        return f'<div class="visual-card image-card"><img src="assets/{esc(v)}" /></div>'
    if t == "illust":
        return f'<div class="visual-card image-card"><img src="assets/illustrations/{esc(v)}.png" /></div>'
    if t == "logo":
        return f'<div class="visual-card logo-card"><div class="phone-logo">{esc(BRAND)}</div><div class="logo-sub">{esc(TAGLINE)}</div></div>'
    if t == "mascot":
        return f'<div class="visual-card mascot-card"><div class="mascot-face">{esc(v or "spot")}</div><div class="mascot-title">{esc(PHONE_CHECK)}</div></div>'
    if t == "stat":
        val = v or {}
        return (
            '<div class="visual-card stat-card">'
            f'<div class="stat-number">{esc(val.get("number", ""))}</div>'
            f'<div class="stat-unit">{esc(val.get("unit", ""))}</div>'
            f'<div class="stat-label">{esc(val.get("label", ""))}</div>'
            "</div>"
        )
    if t == "compare":
        val = v or {}
        left = val.get("left", {})
        right = val.get("right", {})
        return (
            '<div class="visual-card compare-card">'
            f'<div><b>{esc(left.get("label", "Before"))}</b><strong>{esc(left.get("value", ""))}</strong></div>'
            '<em>VS</em>'
            f'<div><b>{esc(right.get("label", "After"))}</b><strong>{esc(right.get("value", ""))}</strong></div>'
            "</div>"
        )
    if t == "timeline":
        items = (v or {}).get("items", [])
        lis = "".join(
            f'<li><b>{esc(it.get("date", ""))}</b><span>{esc(it.get("label", ""))}</span></li>'
            for it in items[:4]
        )
        return f'<div class="visual-card timeline-card"><ul>{lis}</ul></div>'
    return f'<div class="visual-card fallback-card">{esc(t)}</div>'


hf_dir.mkdir(parents=True, exist_ok=True)
for child in ["assets", "audio"]:
    target = hf_dir / child
    if target.exists():
        shutil.rmtree(target)

if assets_dir.exists():
    shutil.copytree(assets_dir, hf_dir / "assets")
else:
    (hf_dir / "assets").mkdir(parents=True, exist_ok=True)

if audio_dir.exists():
    shutil.copytree(audio_dir, hf_dir / "audio")
else:
    (hf_dir / "audio").mkdir(parents=True, exist_ok=True)

opening_sec = 1.5
gap_sec = 0.05
outro_sec = 1.2
now = 0.0
clips = []

opening = script.get("opening", {})
opening_title = opening.get("line2") or script.get("video_title") or BRAND
opening_kicker = opening.get("line1") or TODAY_NEWS
clips.append(
    f'''
  <section class="clip opening" data-start="{now:.3f}" data-duration="{opening_sec:.3f}" data-track-index="0">
    <div class="opening-kicker">{esc(opening_kicker)}</div>
    <div class="opening-title">{esc(opening_title)}</div>
  </section>'''
)
now += opening_sec

sections = [("hook", script["hook"])]
sections += [(f"fact_{i}", fact) for i, fact in enumerate(script.get("facts", []), 1)]
sections += [("cta", script["cta"])]

for key, sec in sections:
    duration = media_duration(hf_dir / "audio" / f"{key}.mp3") + gap_sec
    chunks = sec.get("caption_chunks") or [sec.get("subtitle") or sec.get("tts", "")]
    visuals = sec.get("chunk_visuals") or [{"type": "image", "value": sec.get("background_image", "1.png")}]
    n = max(1, len(chunks))
    chunk_duration = duration / n
    headline = sec.get("headline") or script.get("video_title") or BRAND

    clips.append(
        f'''
  <div class="clip scene-shell" data-start="{now:.3f}" data-duration="{duration:.3f}" data-track-index="1">
    <div class="topbar"><b>{esc(BRAND)}</b><span>{esc(script.get("video_title", ""))}</span></div>
    <div class="headline">{esc(headline)}</div>
  </div>'''
    )
    clips.append(
        f'''
  <audio class="clip" data-start="{now:.3f}" data-duration="{duration:.3f}" data-track-index="20" src="audio/{key}.mp3"></audio>'''
    )

    for idx, chunk in enumerate(chunks):
        start = now + idx * chunk_duration
        visual = visuals[idx] if idx < len(visuals) else visuals[-1]
        clips.append(
            f'''
  <div class="clip visual-wrap" data-start="{start:.3f}" data-duration="{chunk_duration:.3f}" data-track-index="2">
    {render_visual(visual)}
  </div>
  <div class="clip caption" data-start="{start:.3f}" data-duration="{chunk_duration:.3f}" data-track-index="5">
    {emphasize(chunk)}
  </div>'''
        )
    now += duration

clips.append(
    f'''
  <section class="clip outro" data-start="{now:.3f}" data-duration="{outro_sec:.3f}" data-track-index="0">
    <div class="opening-title">{esc(BRAND)}</div>
    <div class="opening-kicker">{esc(CTA_TEXT)}</div>
  </section>'''
)
now += outro_sec

style = """
  :root { font-family: Pretendard, Arial, sans-serif; color: #111; background: #fff1ea; }
  * { box-sizing: border-box; }
  body { margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #fff1ea; }
  #root { position: relative; width: 1080px; height: 1920px; overflow: hidden; background: #fff1ea; }
  .clip { position: absolute; inset: 0; }
  .opening, .outro { display: grid; place-content: center; gap: 34px; padding: 90px; background: #0d0d0f; color: white; text-align: center; }
  .opening-kicker { font-size: 58px; font-weight: 900; color: #f74b0b; }
  .opening-title { font-size: 92px; line-height: 1.06; font-weight: 950; }
  .scene-shell { padding: 48px 52px 0; z-index: 1; }
  .topbar { height: 88px; display: flex; align-items: center; justify-content: space-between; border-bottom: 6px solid #111; }
  .topbar b { background: #f74b0b; color: white; font-size: 42px; padding: 12px 26px; border-radius: 18px; }
  .topbar span { font-size: 32px; font-weight: 850; max-width: 620px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .headline { margin-top: 28px; padding: 24px 30px; font-size: 56px; line-height: 1.15; font-weight: 950; background: white; border: 6px solid #111; border-radius: 28px; box-shadow: 12px 12px 0 #111; }
  .visual-wrap { top: 330px; bottom: 740px; padding: 0 58px; display: grid; place-items: center; z-index: 2; }
  .visual-card { width: 100%; height: 100%; border: 7px solid #111; border-radius: 34px; overflow: hidden; background: white; box-shadow: 16px 16px 0 #111; display: grid; place-items: center; }
  .image-card img { width: 100%; height: 100%; object-fit: cover; }
  .caption { top: auto; height: 650px; bottom: 0; padding: 120px 70px 60px; background: white; border-top: 8px solid #111; font-size: 62px; line-height: 1.26; font-weight: 950; z-index: 4; word-break: keep-all; }
  .caption span { color: #f74b0b; }
  .stat-number { font-size: 174px; font-weight: 1000; color: #f74b0b; }
  .stat-unit, .stat-label { font-size: 48px; font-weight: 950; }
  .compare-card { grid-template-columns: 1fr 110px 1fr; gap: 24px; padding: 54px; }
  .compare-card div { height: 70%; border: 5px solid #111; border-radius: 26px; display: grid; place-content: center; gap: 22px; text-align: center; }
  .compare-card b { font-size: 42px; }
  .compare-card strong { font-size: 58px; color: #f74b0b; }
  .compare-card em { font-size: 48px; font-weight: 1000; align-self: center; text-align: center; }
  .timeline-card ul { list-style: none; margin: 0; padding: 60px; width: 100%; display: grid; gap: 30px; }
  .timeline-card li { display: grid; grid-template-columns: 180px 1fr; align-items: center; gap: 26px; font-size: 42px; font-weight: 900; }
  .timeline-card b { background: #f74b0b; color: white; border-radius: 18px; padding: 18px; text-align: center; }
  .phone-logo { font-size: 110px; font-weight: 1000; color: #f74b0b; }
  .logo-sub, .mascot-title { font-size: 42px; font-weight: 900; }
  .mascot-face { width: 420px; height: 420px; border-radius: 46% 53% 48% 55%; background: #f74b0b; color: white; display: grid; place-items: center; font-size: 56px; font-weight: 1000; border: 8px solid #111; }
"""

html_doc = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=1080, height=1920" />
  <title>{esc(slug)} HyperFrames</title>
  <style>{style}</style>
</head>
<body>
<div id="root" data-composition-id="root" data-start="0" data-width="1080" data-height="1920">
{''.join(clips)}
</div>
</body>
</html>
"""

(hf_dir / "index.html").write_text(html_doc, encoding="utf-8")
print(f"[OK] HyperFrames composition: {hf_dir / 'index.html'}")
print(f"[OK] Duration estimate: {now:.2f}s")
