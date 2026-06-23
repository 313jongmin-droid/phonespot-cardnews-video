"""
Phonespot 카드뉴스 webui (Phase 2)
- 슬러그 목록 + 상태 마커
- 단일 슬러그 상세 (prompt.md 미리보기 + 이미지 업로드 + 렌더 트리거)
- 실시간 렌더 로그 (SSE)
- 결과 페이지 (18 JPG 그리드 + 사이즈별 탭 + ZIP 다운로드)
- Basic Auth (선택, _secrets/webui_auth.txt 있으면 활성화)

실행:
    cd cardnews
    py -3 -u webui/app.py
    또는: webui/start.bat
"""
import os
import sys
import io
import json
import zipfile
import subprocess
import threading
import queue
import time
from pathlib import Path
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, jsonify,
    send_from_directory, send_file, abort, Response, stream_with_context,
)

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent  # cardnews/
ARTICLES_DIR = BASE / 'articles'
IMAGES_DIR = BASE / 'images'
OUTPUT_DIR = BASE / 'output'
PROJECT_ROOT = BASE.parent  # phonespot_cardnews/
AUTH_FILE = PROJECT_ROOT / '_secrets' / 'webui_auth.txt'  # "user:pass" 한 줄

app = Flask(__name__, template_folder=str(SCRIPT_DIR / 'templates'))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 업로드 한도

# ============================================================
# Basic Auth (선택)
# ============================================================
def _load_auth():
    if not AUTH_FILE.exists():
        return None
    line = AUTH_FILE.read_text(encoding='utf-8').strip()
    if ':' not in line:
        return None
    u, p = line.split(':', 1)
    return (u.strip(), p.strip())

_AUTH = _load_auth()

def require_auth(f):
    @wraps(f)
    def wrap(*a, **kw):
        if _AUTH is None:
            return f(*a, **kw)
        auth = request.authorization
        if not auth or (auth.username, auth.password) != _AUTH:
            return Response(
                'Phonespot Cardnews', 401,
                {'WWW-Authenticate': 'Basic realm="Phonespot"'}
            )
        return f(*a, **kw)
    return wrap

# ============================================================
# Helpers
# ============================================================
def _is_done(slug):
    out = OUTPUT_DIR / slug
    if not out.exists():
        return False
    jpgs = list(out.rglob('card_*.jpg'))
    if len(jpgs) < 18:
        return False
    if not (out / 'captions.md').exists():
        return False
    if any(p.stat().st_size < 30 * 1024 for p in jpgs):
        return False
    return True

def _img_count(slug):
    img = IMAGES_DIR / slug
    if not img.exists():
        return 0
    n = 0
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        for p in img.glob(f'*.{ext}'):
            if p.name.startswith(('card_', 'logo_')) or p.name == 'cover.png':
                continue
            n += 1
    return n

def _list_slugs(filter_q=None, filter_status=None):
    if not ARTICLES_DIR.exists():
        return []
    out = []
    for jf in sorted(ARTICLES_DIR.glob('*.json')):
        slug = jf.stem
        try:
            data = json.loads(jf.read_text(encoding='utf-8'))
        except Exception:
            continue
        done = _is_done(slug)
        nimg = _img_count(slug)
        status = 'done' if done else ('ready' if nimg >= 5 else 'waiting')
        item = {
            'slug': slug,
            'title': data.get('title', ''),
            'content_type': data.get('content_type', '-'),
            'publication_date': data.get('publication_date', ''),
            'is_done': done,
            'img_count': nimg,
            'status': status,
        }
        if filter_q and (filter_q.lower() not in slug.lower() and filter_q.lower() not in item['title'].lower()):
            continue
        if filter_status and filter_status != 'all' and status != filter_status:
            continue
        out.append(item)
    return out

# ============================================================
# Routes — 목록 / 상세
# ============================================================
@app.route('/')
@require_auth
def index():
    q = (request.args.get('q') or '').strip()
    st = (request.args.get('status') or 'all').strip()
    slugs = _list_slugs(filter_q=q, filter_status=st)
    all_slugs = _list_slugs()
    counts = {
        'total': len(all_slugs),
        'done': sum(1 for s in all_slugs if s['is_done']),
        'ready': sum(1 for s in all_slugs if not s['is_done'] and s['img_count'] >= 5),
        'waiting': sum(1 for s in all_slugs if not s['is_done'] and s['img_count'] < 5),
    }
    return render_template('index.html', slugs=slugs, counts=counts, q=q, status=st)

@app.route('/slug/<slug>')
@require_auth
def slug_detail(slug):
    jf = ARTICLES_DIR / f'{slug}.json'
    if not jf.exists():
        abort(404)
    try:
        data = json.loads(jf.read_text(encoding='utf-8'))
    except Exception as e:
        return f"JSON parse error: {e}", 500
    prompt_md = ''
    pmd_path = IMAGES_DIR / slug / 'prompt.md'
    if pmd_path.exists():
        prompt_md = pmd_path.read_text(encoding='utf-8')
    img_files = []
    img_dir = IMAGES_DIR / slug
    if img_dir.exists():
        for ext in ('png', 'jpg', 'jpeg', 'webp'):
            for p in sorted(img_dir.glob(f'*.{ext}')):
                if p.name.startswith('logo_'):
                    continue
                img_files.append(p.name)
    return render_template(
        'slug.html',
        slug=slug,
        data=data,
        prompt_md=prompt_md,
        img_files=img_files,
        img_count=_img_count(slug),
        is_done=_is_done(slug),
    )

@app.route('/slug/<slug>/upload', methods=['POST'])
@require_auth
def upload_image(slug):
    if 'files' not in request.files:
        return jsonify({'ok': False, 'error': 'no files'}), 400
    img_dir = IMAGES_DIR / slug
    img_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in request.files.getlist('files'):
        if not f.filename:
            continue
        name = f.filename
        if not any(name.lower().endswith(_ext) for _ext in ('.png', '.jpg', '.jpeg', '.webp')):
            continue
        dst = img_dir / name
        f.save(str(dst))
        saved.append(name)
    return jsonify({'ok': True, 'saved': saved, 'img_count': _img_count(slug)})

# ============================================================
# Routes -- 렌더 (SSE 실시간 로그)
# ============================================================
@app.route('/slug/<slug>/render-stream')
@require_auth
def render_stream(slug):
    jf = ARTICLES_DIR / f'{slug}.json'
    if not jf.exists():
        return jsonify({'ok': False, 'error': 'JSON not found'}), 404
    prefix = slug.split('_')[0]

    def gen():
        yield f"data: [start] {slug} render begin\n\n"
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'PYTHONUNBUFFERED': '1'}
        proc = subprocess.Popen(
            [sys.executable, '-u', str(SCRIPT_DIR.parent / 'scripts' / 'run_windows.py'), prefix],
            cwd=str(BASE),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                escaped = line.rstrip('\n').replace('\r', '')
                yield f"data: {escaped}\n\n"
            proc.stdout.close()
            rc = proc.wait(timeout=600)
            done = _is_done(slug)
            yield f"data: [end] returncode={rc} is_done={done}\n\n"
            yield "event: done\ndata: complete\n\n"
        except subprocess.TimeoutExpired:
            proc.kill()
            yield "data: [timeout] 600s\n\n"
            yield "event: done\ndata: timeout\n\n"
        except Exception as e:
            yield f"data: [error] {e}\n\n"
            yield "event: done\ndata: error\n\n"

    return Response(stream_with_context(gen()), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    })

# ============================================================
# Routes -- 결과 페이지
# ============================================================
@app.route('/result/<slug>')
@require_auth
def result(slug):
    out_dir = OUTPUT_DIR / slug
    if not out_dir.exists():
        abort(404)
    sizes = {}
    for sz in ('1x1', '4x5', '9x16'):
        sz_dir = out_dir / sz
        if sz_dir.exists():
            sizes[sz] = sorted([p.name for p in sz_dir.glob('card_*.jpg')])
        else:
            sizes[sz] = []
    captions_md = ''
    cm_path = out_dir / 'captions.md'
    if cm_path.exists():
        captions_md = cm_path.read_text(encoding='utf-8')
    total_jpgs = sum(len(v) for v in sizes.values())
    total_kb = sum(p.stat().st_size for p in out_dir.rglob('card_*.jpg')) // 1024
    return render_template(
        'result.html',
        slug=slug,
        sizes=sizes,
        captions_md=captions_md,
        total_jpgs=total_jpgs,
        total_kb=total_kb,
        is_done=_is_done(slug),
    )

@app.route('/result/<slug>/zip')
@require_auth
def result_zip(slug):
    out_dir = OUTPUT_DIR / slug
    if not out_dir.exists():
        abort(404)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in out_dir.rglob('*'):
            if p.is_file() and (p.suffix.lower() in ('.jpg', '.jpeg', '.md', '.txt')):
                zf.write(p, arcname=str(p.relative_to(out_dir)))
    buf.seek(0)
    return send_file(buf, mimetype='application/zip', as_attachment=True,
                     download_name=f'{slug}.zip')

# ============================================================
# Static-ish
# ============================================================
@app.route('/output/<slug>/<path:filename>')
@require_auth
def output_file(slug, filename):
    return send_from_directory(str(OUTPUT_DIR / slug), filename)

@app.route('/images/<slug>/<path:filename>')
@require_auth
def image_file(slug, filename):
    return send_from_directory(str(IMAGES_DIR / slug), filename)

# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print(f"[webui] BASE={BASE}")
    # 패널 시작 시 한국매체 RSS 1회 수집 → _state/news_feed.json (best-effort, 실패해도 패널 정상)
    # 윈도우 스케줄러 미사용 → 패널 켤 때마다 최신 한국 IT뉴스 갱신 (2026-06-23)
    try:
        _rss = BASE / 'scripts' / 'collect_news_rss.py'
        if _rss.exists():
            subprocess.run([sys.executable, str(_rss)], timeout=40,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("[webui] news_feed RSS 갱신 완료")
    except Exception as _e_rss:
        print(f"[webui] RSS 갱신 skip: {_e_rss}")
    print(f"[webui] auth: {'ENABLED' if _AUTH else 'DISABLED (LAN only recommended)'}")
    print(f"[webui] articles={ARTICLES_DIR.exists()} / images={IMAGES_DIR.exists()} / output={OUTPUT_DIR.exists()}")
    print("[webui] starting on http://0.0.0.0:8080")
    print("[webui] local: http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
